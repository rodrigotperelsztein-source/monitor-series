"""SUBE mensual: transacciones por mes y promedio por día, con variación interanual.

Se calcula desde data/sube.csv. Solo meses completos: el mes en curso entra cuando están
todos sus días. El promedio diario compara mejor meses de distinta duración.
"""

import pandas as pd

from pipeline.fuentes import sube
from pipeline.fuentes._indec import Columna

ID = "sube_mensual"
NOMBRE = "SUBE: transacciones (usos) por mes"
DERIVADA_DE = sube.ID
URL = "data/sube.csv"
PAGINA = sube.PAGINA
FRECUENCIA = "M"
ORGANISMO = sube.ORGANISMO
UNIDAD = "Transacciones por mes"
CALENDARIO = ""
VERSION = "2026-10-19"

COLUMNAS = {}
for _cid, _col in sube.COLUMNAS.items():
    _nombre = _col.nombre.replace("SUBE, transacciones por día, ", "")
    COLUMNAS[_cid] = Columna("", f"SUBE, transacciones del mes, {_nombre}")
    COLUMNAS[f"{_cid}_prom_diario"] = Columna("", f"SUBE, promedio diario del mes, {_nombre}",
                                              unidad="Transacciones por día")
    COLUMNAS[f"{_cid}_var_ia"] = Columna("", f"SUBE, transacciones del mes, {_nombre}, var. % interanual",
                                         tipo="variacion", base=_cid, rezago=12)


def calcular(diaria: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    d = diaria.set_index("fecha")
    mes = d.index.to_period("M")
    suma = d.groupby(mes).sum()
    dias = d.groupby(mes).size()
    completos = dias == dias.index.days_in_month
    suma, dias = suma[completos], dias[completos]
    out = pd.DataFrame(index=suma.index)
    for cid in sube.COLUMNAS:
        out[cid] = suma[cid]
        out[f"{cid}_prom_diario"] = suma[cid] / dias
        anterior = suma[cid].reindex(suma.index - 12).values
        out[f"{cid}_var_ia"] = (suma[cid].values / anterior - 1) * 100
    out = out.replace([float("inf"), float("-inf")], float("nan"))
    out.insert(0, "fecha", out.index.to_timestamp())
    return out.reset_index(drop=True)[["fecha", *COLUMNAS]], {}


def validar(nuevo: pd.DataFrame, diaria: pd.DataFrame) -> list[str]:
    errores = []
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("los meses no son consecutivos")
    if abs(nuevo["total"].sum() - diaria[diaria["fecha"] < nuevo["fecha"].max() + pd.offsets.MonthBegin()]["total"].sum()) > 0:
        errores.append("la suma de los meses no coincide con la de los días")
    return errores
