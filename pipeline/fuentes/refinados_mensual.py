"""Precios internacionales de naftas y gasoil: promedio mensual (dólares por galón), con variaciones.

Se calcula desde data/refinados.csv. Solo meses cerrados y solo las series con historia (las que
salen de las planillas de la EIA). Promedio simple de los días con cotización.
"""

import pandas as pd

from pipeline.fuentes import refinados
from pipeline.fuentes._indec import Columna

ID = "refinados_mensual"
NOMBRE = "Precios internacionales de naftas y gasoil: promedio mensual (spot EE.UU., EIA)"
DERIVADA_DE = refinados.ID
URL = "data/refinados.csv"
PAGINA = refinados.PAGINA
FRECUENCIA = "M"
ORGANISMO = refinados.ORGANISMO
UNIDAD = refinados.UNIDAD
CALENDARIO = ""
VERSION = "2026-10-21"

COLUMNAS = {}
for _cid, (_, _n, _) in refinados.PLANILLAS.items():
    COLUMNAS[_cid] = Columna("", f"{_n}, promedio del mes")
    COLUMNAS[f"{_cid}_var_m"] = Columna("", f"{_n}, promedio del mes, var. % mensual", tipo="variacion", base=_cid, rezago=1)
    COLUMNAS[f"{_cid}_var_ia"] = Columna("", f"{_n}, promedio del mes, var. % interanual", tipo="variacion", base=_cid, rezago=12)


def calcular(diaria: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    d = diaria.set_index("fecha")[list(refinados.PLANILLAS)]
    prom = d.groupby(d.index.to_period("M")).mean()
    prom = prom[prom.index < d.index.max().to_period("M")]
    out = pd.DataFrame(index=prom.index)
    for cid in refinados.PLANILLAS:
        out[cid] = prom[cid]
        out[f"{cid}_var_m"] = prom[cid].pct_change(fill_method=None) * 100
        out[f"{cid}_var_ia"] = (prom[cid] / prom[cid].shift(12) - 1) * 100
    out.insert(0, "fecha", out.index.to_timestamp())
    return out.reset_index(drop=True)[["fecha", *COLUMNAS]], {}


def validar(nuevo: pd.DataFrame, diaria: pd.DataFrame) -> list[str]:
    errores = []
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("los meses no son consecutivos")
    if nuevo["nafta_usgc"].isna().any() or nuevo["ho_nyh"].isna().any():
        errores.append("hay meses sin nafta o heating oil")
    return errores
