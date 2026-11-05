"""Índice del costo de la construcción (ICC) en el Gran Buenos Aires: nivel general y capítulos (materiales, mano de obra
y gastos generales), base 1993 reexpresada ene-22=100, con variaciones (INDEC, API).
"""

import pandas as pd

from pipeline.fuentes import _api_indec as api
from pipeline.fuentes import _api_simple as simple
from pipeline.fuentes._indec import Columna

ID = "icc"
NOMBRE = "Índice del costo de la construcción, GBA (INDEC)"
TABLA_API = "icc_precios_construccion"
URL = "https://api.indec.gob.ar/v1/" + TABLA_API
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-5-33"
EXTENSION = "json"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Índice ene-22=100"
CALENDARIO = "Índice del costo de la construcción"

APERTURAS = {"nivel_general": ("0", "Nivel general"), "materiales": ("01", "Materiales"),
             "mano_de_obra": ("02", "Mano de obra"), "gastos_generales": ("03", "Gastos generales")}
COLUMNAS = {}
for _k, (_c, _n) in APERTURAS.items():
    COLUMNAS[_k] = Columna("", f"ICC: {_n.lower()}")
    COLUMNAS[f"{_k}_var_m"] = Columna("", f"ICC: {_n.lower()}, var. % mensual", unidad="%", tipo="variacion", base=_k, rezago=1)
    COLUMNAS[f"{_k}_var_ia"] = Columna("", f"ICC: {_n.lower()}, var. % interanual", unidad="%", tipo="variacion", base=_k, rezago=12)


def bajar(descargar, hoy):
    return simple.bajar(TABLA_API)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    f = api.filas(contenido)
    f = f[(f["indicador"] == "ICC") & (f["region"] == "GBA") & (f["tipo_de_indicador"] == "Indice")]
    out = {}
    for k, (cod, _) in APERTURAS.items():
        s = f[f["codigo_apertura"].astype(str) == cod].groupby("fecha")["valor"].last()
        if s.empty:
            raise ValueError(f"La API no trajo el capítulo {cod} del ICC.")
        out[k] = pd.to_numeric(s, errors="coerce")
    df = pd.DataFrame(out).sort_index()
    df = df.reindex(pd.date_range(df.index.min(), df.index.max(), freq="MS"))
    for k in APERTURAS:
        df[f"{k}_var_m"] = (df[k] / df[k].shift(1) - 1) * 100
        df[f"{k}_var_ia"] = (df[k] / df[k].shift(12) - 1) * 100
    df.index.name = "fecha"
    return df.reset_index()[["fecha", *columnas]]


def validar(nuevo, anterior, columnas=COLUMNAS):
    errores = simple.validar_basico(nuevo, anterior, columnas, "MS", 120)
    if nuevo[list(APERTURAS)].isna().any().any():
        errores.append("Hay meses sin índice.")
    return errores
