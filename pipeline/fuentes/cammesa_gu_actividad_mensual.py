"""Grandes usuarios (GUMA) por actividad, por mes: demanda media de los días hábiles y de todos
los días, con variación interanual.

Se calcula desde data/cammesa_gu_actividad.csv. Solo meses completos. La media de días hábiles es
el indicador que usa CAMMESA en su informe ("INDICADORES (MW)"), que compara meses sin el efecto
de la cantidad de fines de semana y feriados.
"""

import pandas as pd

from pipeline.fuentes import cammesa_gu_actividad as diaria_mod
from pipeline.fuentes._indec import Columna

ID = "cammesa_gu_actividad_mensual"
NOMBRE = "CAMMESA: demanda de grandes usuarios (GUMA) por actividad, por mes"
DERIVADA_DE = diaria_mod.ID
URL = "data/cammesa_gu_actividad.csv"
PAGINA = diaria_mod.PAGINA
FRECUENCIA = "M"
ORGANISMO = "CAMMESA"
UNIDAD = "MW (demanda media)"
CALENDARIO = ""
VERSION = "2026-10-20"

COLUMNAS = {}
for _cid, (_r, _n) in diaria_mod.SERIES.items():
    COLUMNAS[_cid] = Columna("", f"Demanda de GUMA, {_n}, media de días hábiles")
    COLUMNAS[f"{_cid}_var_ia"] = Columna("", f"Demanda de GUMA, {_n}, media de días hábiles, var. % interanual",
                                         tipo="variacion", base=_cid, rezago=12)
    COLUMNAS[f"{_cid}_todos"] = Columna("", f"Demanda de GUMA, {_n}, media de todos los días")


def calcular(diaria: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    d = diaria.set_index("fecha")
    mes = d.index.to_period("M")
    series = list(diaria_mod.SERIES)
    habiles = d[d["dia_habil"] == 1].groupby(mes[d["dia_habil"] == 1])[series].mean()
    todos = d.groupby(mes)[series].mean()
    dias = d.groupby(mes).size()
    completos = dias.index[dias == dias.index.days_in_month]
    habiles, todos = habiles.reindex(completos), todos.reindex(completos)
    out = pd.DataFrame(index=completos)
    for cid in series:
        out[cid] = habiles[cid]
        out[f"{cid}_var_ia"] = (habiles[cid].values / habiles[cid].reindex(completos - 12).values - 1) * 100
        out[f"{cid}_todos"] = todos[cid]
    out.insert(0, "fecha", out.index.to_timestamp())
    return out.reset_index(drop=True)[["fecha", *COLUMNAS]], {}


def validar(nuevo: pd.DataFrame, diaria: pd.DataFrame) -> list[str]:
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        return ["los meses no son consecutivos"]
    return []
