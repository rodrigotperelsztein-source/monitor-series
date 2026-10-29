"""Acciones de energía: cierre de fin de mes en Nueva York (dólares), con variaciones mensual e interanual.

Se calcula desde data/acciones_energia.csv. Toma el último cierre de cada mes; el mes en curso entra recién cuando
termina (cuando ya hay un cierre del mes siguiente).
"""

import pandas as pd

from pipeline.fuentes import acciones_energia as ae
from pipeline.fuentes._indec import Columna

ID = "acciones_energia_mensual"
NOMBRE = "Acciones de energía en Nueva York: cierre de fin de mes y variaciones (YPF, Vista, Pampa, TGS)"
DERIVADA_DE = ae.ID
URL = "data/acciones_energia.csv"
PAGINA = ae.PAGINA
FRECUENCIA = "M"
ORGANISMO = ae.ORGANISMO
UNIDAD = ae.UNIDAD
CALENDARIO = ""
VERSION = "2026-10-29"

COLUMNAS = {}
for _cid, (_tk, _n) in ae.EMPRESAS.items():
    COLUMNAS[_cid] = Columna("", f"{_n} ({_tk}), cierre de fin de mes en dólares")
    COLUMNAS[f"{_cid}_var_m"] = Columna("", f"{_n} ({_tk}), var. % mensual", tipo="variacion", base=_cid, rezago=1)
    COLUMNAS[f"{_cid}_var_ia"] = Columna("", f"{_n} ({_tk}), var. % interanual", tipo="variacion", base=_cid, rezago=12)


def calcular(diaria: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    d = diaria.set_index("fecha")
    fin = d.groupby(d.index.to_period("M")).last()
    fin = fin[fin.index < d.index.max().to_period("M")]
    out = pd.DataFrame(index=fin.index)
    for cid in ae.EMPRESAS:
        out[cid] = fin[cid]
        out[f"{cid}_var_m"] = fin[cid].pct_change(fill_method=None) * 100
        out[f"{cid}_var_ia"] = (fin[cid] / fin[cid].shift(12) - 1) * 100
    out.insert(0, "fecha", out.index.to_timestamp())
    return out.reset_index(drop=True)[["fecha", *COLUMNAS]], {}


def validar(nuevo: pd.DataFrame, diaria: pd.DataFrame) -> list[str]:
    errores = []
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("los meses no son consecutivos")
    if nuevo["ypf"].isna().any():
        errores.append("hay meses sin YPF")
    return errores
