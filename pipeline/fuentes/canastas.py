"""Canasta básica alimentaria (CBA) y total (CBT) del INDEC, GBA: valor por adulto equivalente y por hogar tipo.

Fuente: Catálogo API-INDEC, tabla valorizacion_canastas_cba_cbt (desde abril de 2016). La CBT es la línea de pobreza
y la CBA la de indigencia. Hogares tipo del INDEC: 1) tres personas; 2) cuatro personas (pareja con dos hijos de 6 y 8
años); 3) cinco personas. Sin la API (token vencido o servicio caído) la fuente no se actualiza.
"""

import pandas as pd

from pipeline.fuentes import _api_indec as api
from pipeline.fuentes._indec import Columna

ID = "canastas"
NOMBRE = "Canastas básicas alimentaria y total (CBA y CBT), GBA"
TABLA_API = "valorizacion_canastas_cba_cbt"
URL = "https://api.indec.gob.ar/v1/" + TABLA_API
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-4-43-149"
EXTENSION = "json"
FRECUENCIA = "M"
ORGANISMO = "INDEC (Catálogo API-INDEC)"
UNIDAD = "Pesos por mes"
PRIMER_PERIODO = "2016-04-01"
CALENDARIO = "Valorización mensual de la canasta básica alimentaria (CBA)"
GUARDAR_ORIGINAL = False

# id -> (código, tipo de indicador en la API, nombre)
SERIES = {
    "cba": ("CBA", "CBA", "CBA por adulto equivalente"),
    "cba_var_m": ("CBA", "v_m", "CBA por adulto equivalente, var. % mensual"),
    "cba_var_ia": ("CBA", "v_ia", "CBA por adulto equivalente, var. % interanual"),
    "cbt": ("CBT", "CBT", "CBT por adulto equivalente"),
    "cbt_var_m": ("CBT", "v_m", "CBT por adulto equivalente, var. % mensual"),
    "cbt_var_ia": ("CBT", "v_ia", "CBT por adulto equivalente, var. % interanual"),
    "cba_hogar_2": ("CBA H2", "Hogar 2", "CBA del hogar tipo 2 (cuatro personas): línea de indigencia"),
    "cbt_hogar_2": ("CBT H2", "Hogar 2", "CBT del hogar tipo 2 (cuatro personas): línea de pobreza"),
    "cba_hogar_1": ("CBA H1", "Hogar 1", "CBA del hogar tipo 1 (tres personas)"),
    "cbt_hogar_1": ("CBT H1", "Hogar 1", "CBT del hogar tipo 1 (tres personas)"),
    "cba_hogar_3": ("CBA H3", "Hogar 3", "CBA del hogar tipo 3 (cinco personas)"),
    "cbt_hogar_3": ("CBT H3", "Hogar 3", "CBT del hogar tipo 3 (cinco personas)"),
    "inversa_engel": ("ICE", "ICE", "Inversa del coeficiente de Engel (CBT / CBA)"),
}
COLUMNAS = {k: Columna("", n, tipo="variacion" if t in ("v_m", "v_ia") else "nivel",
                       unidad="%" if t in ("v_m", "v_ia") else ("Coeficiente" if k == "inversa_engel" else "Pesos por mes"))
            for k, (_, t, n) in SERIES.items()}


def bajar(descargar, hoy) -> tuple[str, bytes]:
    if not api.disponible(TABLA_API):
        raise ValueError("No está la tabla de la API del INDEC (¿token vencido o API caída?).")
    return api.contenido(TABLA_API)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    f = api.filas(contenido)
    f = f[f["region"] == "GBA"]
    ancho = f.pivot_table(index="fecha", columns=["codigo", "tipo_de_indicador"], values="valor", aggfunc="first")
    out = pd.DataFrame(index=ancho.index)
    for k in columnas:
        cod, tipo, _ = SERIES[k]
        if (cod, tipo) not in ancho.columns:
            raise ValueError(f"La API no trae {cod} / {tipo}.")
        out[k] = ancho[(cod, tipo)]
    out.index.name = "fecha"
    return out.sort_index().reset_index()[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if len(nuevo) < 100:
        errores.append(f"Solo {len(nuevo)} meses.")
    if not (nuevo["cbt"].dropna() > nuevo["cba"].dropna()).all():
        errores.append("La CBT no es mayor que la CBA en todos los meses.")
    calc = (nuevo["cbt"] / nuevo["cbt"].shift(1) - 1) * 100
    if ((calc - nuevo["cbt_var_m"]).abs() > 0.15).any():
        errores.append("La variación mensual de la CBT no coincide con la de los valores.")
    if (pd.Timestamp.today() - nuevo["fecha"].max()).days > 75:
        errores.append("El último mes tiene más de dos meses de atraso.")
    return errores
