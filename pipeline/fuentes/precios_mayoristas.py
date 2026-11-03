"""Precios mayoristas del INDEC (SIPM): IPIM (internos al por mayor), IPIB (internos básicos) e IPP (productor).

Fuente: Catálogo API-INDEC, tabla sipm_precios_mayoristas, total del país, base 1993 con dic-2015=100 (desde
diciembre de 2015). Para cada índice: nivel general, productos nacionales e importados, primarios, manufacturados y
energía eléctrica, petróleo crudo y gas natural (división 11 de la CIIU) y productos refinados del petróleo (división
23); el IPP no distingue nacionales e importados. Índice y variaciones mensual e interanual publicadas por el INDEC. Sin la API, la fuente no se actualiza.
"""

import pandas as pd

from pipeline.fuentes import _api_indec as api
from pipeline.fuentes._indec import Columna

ID = "precios_mayoristas"
NOMBRE = "Precios mayoristas (SIPM): IPIM, IPIB e IPP"
TABLA_API = "sipm_precios_mayoristas"
URL = "https://api.indec.gob.ar/v1/" + TABLA_API
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-5-32"
EXTENSION = "json"
FRECUENCIA = "M"
ORGANISMO = "INDEC (Catálogo API-INDEC)"
UNIDAD = "Índice dic-2015=100"
PRIMER_PERIODO = "2015-12-01"
CALENDARIO = "Sistema de índices de precios mayoristas"
GUARDAR_ORIGINAL = False

INDICES = {"ipim": ("IPIM", "Precios internos al por mayor (IPIM)"), "ipib": ("IPIB", "Precios internos básicos (IPIB)"),
           "ipp": ("IPP", "Precios al productor (IPP)")}
# id -> (clasificador, código de apertura, nombre)
APERTURAS = {"nivel_general": ("SIPM 93", "NG", "nivel general"), "nacionales": ("SIPM 93", "N", "productos nacionales"),
             "importados": ("SIPM 93", "I", "productos importados"), "primarios": ("SIPM 93", "1", "productos primarios"),
             "manufacturados_energia": ("CIIU3", "2", "manufacturados y energía eléctrica"),
             "petroleo_gas": ("CIIU3", "11", "petróleo crudo y gas natural"),
             "refinados": ("CIIU3", "23", "productos refinados del petróleo")}
# El IPP no tiene productos importados (mide precios de productores locales): ahí solo hay nivel general.
NO_APLICA = {("ipp", "nacionales"), ("ipp", "importados")}
MEDIDAS = {"": ("Indice", "índice"), "_var_m": ("v_m", "var. % mensual"), "_var_ia": ("v_ia", "var. % interanual")}

COLUMNAS = {}
for _i, (_, _ni) in INDICES.items():
    for _a, (_, _, _na) in APERTURAS.items():
        if (_i, _a) in NO_APLICA:
            continue
        for _suf, (_t, _nm) in MEDIDAS.items():
            COLUMNAS[f"{_i}_{_a}{_suf}"] = Columna("", f"{_ni}, {_na}, {_nm}", tipo="variacion" if _suf else "nivel",
                                                  unidad="%" if _suf else UNIDAD)


def bajar(descargar, hoy) -> tuple[str, bytes]:
    if not api.disponible(TABLA_API):
        raise ValueError("No está la tabla de la API del INDEC (¿token vencido o API caída?).")
    return api.contenido(TABLA_API)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    f = api.filas(contenido)
    claves = {(INDICES[i][0], c, cod) for i in INDICES for c, cod, _ in APERTURAS.values()}
    f = f[[(a, b, str(c)) in claves for a, b, c in zip(f["indicador"], f["clasificador"], f["codigo_apertura"])]]
    f = f[f["nivel"] != "Clase"]  # los códigos 11 y 23 son divisiones (en clase hay otros)
    ancho = f.pivot_table(index="fecha", columns=["indicador", "clasificador", "codigo_apertura", "tipo_de_indicador"],
                          values="valor", aggfunc="first")
    out = pd.DataFrame(index=ancho.index)
    for i, (ind, _) in INDICES.items():
        for a, (cl, cod, _) in APERTURAS.items():
            for suf, (t, _) in MEDIDAS.items():
                k = f"{i}_{a}{suf}"
                if k in columnas:
                    if (ind, cl, cod, t) not in ancho.columns:
                        raise ValueError(f"La API no trae {ind} {cl} {cod} {t}.")
                    out[k] = ancho[(ind, cl, cod, t)]
    out.index.name = "fecha"
    return out.sort_index().reset_index()[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if len(nuevo) < 100:
        errores.append(f"Solo {len(nuevo)} meses.")
    for i in INDICES:
        base = nuevo.loc[nuevo["fecha"] == "2015-12-01", f"{i}_nivel_general"]
        if len(base) != 1 or abs(float(base.iloc[0]) - 100) > 0.5:
            errores.append(f"{i}: el nivel general no vale 100 en dic-2015.")
        s = nuevo[f"{i}_nivel_general"]
        if ((s / s.shift(1) - 1) * 100 - nuevo[f"{i}_nivel_general_var_m"]).abs().max() > 0.15:
            errores.append(f"{i}: la variación mensual no coincide con el índice.")
    if (pd.Timestamp.today() - nuevo["fecha"].max()).days > 75:
        errores.append("El último mes tiene más de dos meses de atraso.")
    return errores
