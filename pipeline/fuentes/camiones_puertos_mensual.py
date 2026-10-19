"""Entrada de camiones a puertos por mes: total del mes y variación interanual.

Se calcula desde data/camiones_puertos.csv. Solo meses completos: el mes en curso entra
cuando la serie diaria llega a su último día.
"""

import pandas as pd

from pipeline.fuentes import camiones_puertos as diaria_mod
from pipeline.fuentes._indec import Columna

ID = "camiones_puertos_mensual"
NOMBRE = "Entrada de camiones con granos a puertos, fábricas y molinos, por mes"
DERIVADA_DE = diaria_mod.ID
URL = "data/camiones_puertos.csv"
PAGINA = diaria_mod.PAGINA
FRECUENCIA = "M"
ORGANISMO = diaria_mod.ORGANISMO
UNIDAD = "Camiones por mes"
CALENDARIO = ""
VERSION = "2026-10-19"

COLUMNAS = {}
for _cid, _col in diaria_mod.COLUMNAS.items():
    _nombre = _col.nombre.replace(" por día", " en el mes")
    _unidad = "Vagones por mes" if _cid == "vagones" else None
    COLUMNAS[_cid] = Columna("", _nombre, unidad=_unidad)
    COLUMNAS[f"{_cid}_var_ia"] = Columna("", f"{_nombre}, var. % interanual", tipo="variacion", base=_cid, rezago=12)


def calcular(diaria: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    d = diaria.set_index("fecha")
    mes = d.index.to_period("M")
    suma = d.groupby(mes).sum()
    ultimo = d.index.max()
    if ultimo != ultimo + pd.offsets.MonthEnd(0):
        suma = suma.iloc[:-1]  # mes en curso incompleto
    out = pd.DataFrame(index=suma.index)
    for cid in diaria_mod.COLUMNAS:
        out[cid] = suma[cid]
        previo = suma[cid].reindex(suma.index - 12).values
        out[f"{cid}_var_ia"] = (suma[cid].values / previo - 1) * 100
    out = out.replace([float("inf"), float("-inf")], float("nan"))
    out.insert(0, "fecha", out.index.to_timestamp())
    return out.reset_index(drop=True)[["fecha", *COLUMNAS]], {}


def validar(nuevo: pd.DataFrame, diaria: pd.DataFrame) -> list[str]:
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        return ["los meses no son consecutivos"]
    return []
