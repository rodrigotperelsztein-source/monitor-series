"""Índice de salarios de INDEC: sector privado registrado, público, total registrado,
no registrado e índice total. Base octubre 2016=100.

Fuente: INDEC, Índice de salarios. Datos: Catálogo API-INDEC (tabla indice_salarios), con respaldo en el archivo
indice_salarios.csv (separador ";", coma decimal) si la API no está disponible.
El sector no registrado y el índice total empiezan en octubre de 2016 (antes figuran como NA).
Las variaciones mensual e interanual se calculan desde los índices (INDEC no las trae en el CSV).
"""

import io

import pandas as pd

from pipeline.fuentes import _api_indec as api
from pipeline.fuentes._indec import Columna, validar_tabla

ID = "salarios"
NOMBRE = "Índice de salarios (INDEC)"
URL = "https://www.indec.gob.ar/ftp/cuadros/sociedad/indice_salarios.csv"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-4-31-61"
EXTENSION = "csv"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Índice base oct-2016=100"
PRIMER_PERIODO = "2015-10-01"
CALENDARIO = "Índice de salarios"

SERIES = {
    "privado_registrado": ("IS_sector_privado_registrado", "Salarios del sector privado registrado"),
    "publico": ("IS_sector_publico", "Salarios del sector público"),
    "total_registrado": ("IS_total_registrado", "Salarios del total registrado"),
    "no_registrado": ("IS_sector_no_registrado", "Salarios del sector privado no registrado"),
    "total": ("IS_indice_total", "Índice de salarios, total"),
}
DESDE_2016 = {"no_registrado", "total"}

COLUMNAS = {}
for _cid, (_orig, _nombre) in SERIES.items():
    COLUMNAS[_cid] = Columna(_orig, f"{_nombre}, índice oct-2016=100")
    COLUMNAS[f"{_cid}_var_m"] = Columna("", f"{_nombre}, var. % mensual", tipo="variacion", base=_cid, rezago=1)
    COLUMNAS[f"{_cid}_var_ia"] = Columna("", f"{_nombre}, var. % interanual", tipo="variacion", base=_cid, rezago=12)


TABLA_API = "indice_salarios"
CODIGOS_API = {"privado_registrado": "110", "publico": "120", "total_registrado": "100", "no_registrado": "200", "total": "0"}


def bajar(descargar, hoy) -> tuple[str, bytes]:
    return api.bajar(TABLA_API, descargar, lambda: (URL, descargar(URL)))


def _crudo_api(contenido: bytes) -> pd.DataFrame:
    f = api.filas(contenido)
    f = f[(f["tipo_de_indicador"] == "Indice") & f["codigo"].astype(str).isin(CODIGOS_API.values())]
    ancho = f.pivot_table(index="fecha", columns=f["codigo"].astype(str), values="valor", aggfunc="first")
    crudo = pd.DataFrame({"periodo": ancho.index.strftime("%d/%m/%Y")})
    for cid, (orig, _) in SERIES.items():
        crudo[orig] = ancho[CODIGOS_API[cid]].values if CODIGOS_API[cid] in ancho else float("nan")
    return crudo


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    if api.es_api(contenido):
        crudo = _crudo_api(contenido)
        return _armar(crudo, columnas)
    texto = contenido.decode("utf-8-sig", errors="replace")
    crudo = pd.read_csv(io.StringIO(texto), sep=";", decimal=",", na_values=["NA", ""])
    crudo.columns = [c.strip() for c in crudo.columns]
    return _armar(crudo, columnas)


def _armar(crudo: pd.DataFrame, columnas) -> pd.DataFrame:
    faltan = [o for o, _ in SERIES.values() if o not in crudo.columns]
    if faltan:
        raise ValueError(f"El CSV no tiene las columnas {faltan}; tiene {list(crudo.columns)}")
    df = pd.DataFrame({"fecha": pd.to_datetime(crudo["periodo"], format="%d/%m/%Y")})
    for cid, (orig, _) in SERIES.items():
        serie = pd.to_numeric(crudo[orig], errors="coerce")
        df[cid] = serie
        df[f"{cid}_var_m"] = serie.pct_change(fill_method=None) * 100
        df[f"{cid}_var_ia"] = serie.pct_change(12, fill_method=None) * 100
    return df.sort_values("fecha").reset_index(drop=True)[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    # El no registrado y el total solo pueden faltar antes de octubre de 2016.
    for cid in DESDE_2016:
        if nuevo.loc[nuevo["fecha"] >= "2016-10-01", cid].isna().any():
            errores.append(f"{cid}: faltan valores desde octubre de 2016")
    # Sus variaciones arrancan más tarde: se controlan solo desde que hay datos.
    v = nuevo.copy()
    for cid in DESDE_2016:
        for suf in ("_var_m", "_var_ia"):
            v[cid + suf] = v[cid + suf].fillna(0)
    return errores + validar_tabla(v, anterior, columnas, PRIMER_PERIODO, rango_nivel=(0, 1e7),
                                   max_variacion=1000, vacios_permitidos=DESDE_2016)
