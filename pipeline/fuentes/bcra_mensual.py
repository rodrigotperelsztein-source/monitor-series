"""BCRA mensual: las variables diarias de `bcra` llevadas a mes, con variación interanual.

Saldos de reservas, CER, UVA e ICL: último dato del mes. Factores de explicación de la base monetaria y compras de
divisas: suma del mes. Resto (base monetaria, depósitos, préstamos, tasas, tipo de cambio): promedio de los días hábiles.
Solo meses completos: el mes del último dato todavía no cerró.
"""

import pandas as pd

from pipeline.fuentes import bcra
from pipeline.fuentes._indec import Columna

ID = "bcra_mensual"
NOMBRE = "BCRA: reservas, base monetaria, depósitos, préstamos, tasas y tipo de cambio (mensual)"
DERIVADA_DE = bcra.ID
URL = "data/bcra.csv"
PAGINA = bcra.PAGINA
FRECUENCIA = "M"
ORGANISMO = "BCRA; promedio o fin de mes propio"
UNIDAD = bcra.UNIDAD
CALENDARIO = ""
VERSION = "2026-11-05"
AGREGACION = {"fin": "último dato del mes", "promedio": "promedio del mes", "suma": "suma del mes"}

COLUMNAS = {}
for _k, (_, _n, _u, _a) in bcra.VARIABLES.items():
    COLUMNAS[_k] = Columna("", f"{_n}, {AGREGACION[_a]}", unidad=_u)
    if _a != "suma":
        COLUMNAS[f"{_k}_var_ia"] = Columna("", f"{_n}, {AGREGACION[_a]}, var. % interanual", tipo="variacion", base=_k, rezago=12)


def calcular(diaria: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    d = diaria.set_index("fecha")
    mes = d.index.to_period("M")
    out = pd.DataFrame(index=sorted(set(mes)))
    for k, (_, _, _, a) in bcra.VARIABLES.items():
        g = d[k].dropna().groupby(d[k].dropna().index.to_period("M"))
        s = g.last() if a == "fin" else g.sum() if a == "suma" else g.mean()
        out[k] = s
        if a != "suma":
            # Por período (no por posición): una serie puede tener meses sin dato
            out[f"{k}_var_ia"] = [((s.get(p) / s.get(p - 12) - 1) * 100) if s.get(p - 12) not in (None, 0) and p - 12 in s.index else None
                                 for p in out.index]
    out = out[out.index < d.index.max().to_period("M")]
    out.insert(0, "fecha", out.index.to_timestamp())
    return out.reset_index(drop=True)[["fecha", *COLUMNAS]].astype({c: float for c in COLUMNAS}), {}


def validar(nuevo: pd.DataFrame, diaria: pd.DataFrame) -> list[str]:
    errores = []
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("los meses no son consecutivos")
    if nuevo["reservas"].tail(12).isna().any():
        errores.append("faltan reservas en el último año")
    return errores
