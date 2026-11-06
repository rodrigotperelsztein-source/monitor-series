"""Clima mensual de CABA y el AMBA a partir de `clima_amba`: temperatura media, promedio de las máximas y de las mínimas,
lluvia acumulada y días con lluvia (1 mm o más). Solo meses completos.
"""

import pandas as pd

from pipeline.fuentes import _clima, clima_amba
from pipeline.fuentes._indec import Columna

ID = "clima_amba_mensual"
NOMBRE = "Temperatura y lluvia mensuales de CABA y el AMBA (reanálisis ERA5, Open-Meteo)"
DERIVADA_DE = clima_amba.ID
URL = "data/clima_amba.csv"
PAGINA = clima_amba.PAGINA
FRECUENCIA = "M"
ORGANISMO = clima_amba.ORGANISMO + "; cálculo propio"
UNIDAD = "°C, mm y días"
CALENDARIO = ""
VERSION = "2026-11-06"

COLUMNAS = {}
for _a, _A in _clima.AREAS.items():
    COLUMNAS[f"{_a}_tmed"] = Columna("", f"Temperatura media del mes ({_A})", unidad="°C")
    COLUMNAS[f"{_a}_tmax"] = Columna("", f"Promedio de las temperaturas máximas ({_A})", unidad="°C")
    COLUMNAS[f"{_a}_tmin"] = Columna("", f"Promedio de las temperaturas mínimas ({_A})", unidad="°C")
    COLUMNAS[f"{_a}_lluvia"] = Columna("", f"Lluvia acumulada en el mes ({_A})", unidad="mm")
    COLUMNAS[f"{_a}_dias_lluvia"] = Columna("", f"Días con lluvia de 1 mm o más ({_A})", unidad="días")


def calcular(diaria: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    d = diaria.set_index("fecha")
    g = d.groupby(d.index.to_period("M"))
    out = pd.DataFrame(index=g.size().index)
    for a in _clima.AREAS:
        for k in ("tmed", "tmax", "tmin"):
            out[f"{a}_{k}"] = g[f"{a}_{k}"].mean().round(2)
        out[f"{a}_lluvia"] = g[f"{a}_lluvia"].sum().round(1)
        out[f"{a}_dias_lluvia"] = g[f"{a}_lluvia"].apply(lambda s: (s >= 1).sum()).astype(float)
    completos = g.size() == g.size().index.days_in_month
    out = out[completos]
    out.insert(0, "fecha", out.index.to_timestamp())
    return out.reset_index(drop=True)[["fecha", *COLUMNAS]], {}


def validar(nuevo: pd.DataFrame, diaria: pd.DataFrame) -> list[str]:
    return [] if len(nuevo) else ["no hay ningún mes completo"]
