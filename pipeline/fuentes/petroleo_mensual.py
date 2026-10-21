"""Petróleo mensual: promedio del mes del precio spot del Brent y del WTI, con variaciones.

Se calcula desde data/petroleo.csv. Solo meses completos: el mes en curso entra cuando ya hay
un cierre del mes siguiente. Es el promedio simple de los días con cotización.
"""

import pandas as pd

from pipeline.fuentes import petroleo
from pipeline.fuentes._indec import Columna

ID = "petroleo_mensual"
NOMBRE = "Petróleo: precio promedio mensual del Brent y del WTI (EIA)"
DERIVADA_DE = petroleo.ID
URL = "data/petroleo.csv"
PAGINA = petroleo.PAGINA
FRECUENCIA = "M"
ORGANISMO = petroleo.ORGANISMO
UNIDAD = petroleo.UNIDAD
CALENDARIO = ""
VERSION = "2026-10-21"

COLUMNAS = {}
for _cid, _n in (("brent", "Petróleo Brent"), ("wti", "Petróleo WTI")):
    COLUMNAS[_cid] = Columna("", f"{_n}, precio spot, promedio del mes")
    COLUMNAS[f"{_cid}_var_m"] = Columna("", f"{_n}, promedio del mes, var. % mensual", tipo="variacion", base=_cid, rezago=1)
    COLUMNAS[f"{_cid}_var_ia"] = Columna("", f"{_n}, promedio del mes, var. % interanual", tipo="variacion", base=_cid, rezago=12)
COLUMNAS["diferencial"] = Columna("", "Diferencial Brent - WTI, promedio del mes")


def calcular(diaria: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    d = diaria.set_index("fecha")
    mes = d.index.to_period("M")
    prom = d.groupby(mes)[["brent", "wti", "diferencial"]].mean()
    prom = prom[prom.index < d.index.max().to_period("M")]  # el mes del último dato todavía no cerró
    prom = prom[prom.index >= pd.Period("1986-01", "M")]
    out = pd.DataFrame(index=prom.index)
    for cid in ("brent", "wti"):
        out[cid] = prom[cid]
        out[f"{cid}_var_m"] = prom[cid].pct_change(fill_method=None) * 100
        out[f"{cid}_var_ia"] = (prom[cid] / prom[cid].shift(12) - 1) * 100
    out["diferencial"] = prom["diferencial"]
    out.insert(0, "fecha", out.index.to_timestamp())
    return out.reset_index(drop=True)[["fecha", *COLUMNAS]], {}


def validar(nuevo: pd.DataFrame, diaria: pd.DataFrame) -> list[str]:
    errores = []
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("los meses no son consecutivos")
    if nuevo["wti"].isna().any():
        errores.append("hay meses sin WTI")
    if nuevo.loc[nuevo["fecha"] >= "1987-06-01", "brent"].isna().any():
        errores.append("hay meses sin Brent desde junio de 1987")
    return errores
