"""Tipo de cambio real multilateral y bilaterales (BCRA): promedio mensual, con variación mensual e interanual.

Fuente: la misma planilla que itcrm (hoja "ITCRM y bilaterales prom. mens."), que publica el BCRA con los promedios de
cada mes. El mes en curso es un promedio parcial y los últimos meses son provisorios (inflación estimada).
"""

import pandas as pd

from pipeline.fuentes import itcrm
from pipeline.fuentes._indec import Columna

ID = "itcrm_mensual"
NOMBRE = "Tipo de cambio real multilateral y bilaterales (BCRA), promedio mensual"
PAGINA = itcrm.PAGINA
URL = itcrm.URL
EXTENSION = "xlsx"
FRECUENCIA = "M"
ORGANISMO = "BCRA"
UNIDAD = "Índice 17-12-2015=100"
PRIMER_PERIODO = "1997-01-01"
CALENDARIO = ""
GUARDAR_ORIGINAL = False
HOJA = "ITCRM y bilaterales prom. mens."

COLUMNAS = {}
for _k, (_, _n) in itcrm.SOCIOS.items():
    COLUMNAS[_k] = Columna("", f"{_n}, promedio mensual")
    COLUMNAS[f"{_k}_var_m"] = Columna("", f"{_n}, var. % mensual", tipo="variacion", base=_k, rezago=1)
    COLUMNAS[f"{_k}_var_ia"] = Columna("", f"{_n}, var. % interanual", tipo="variacion", base=_k, rezago=12)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    d = itcrm.leer_hoja(contenido, HOJA)
    d["fecha"] = d["fecha"].dt.to_period("M").dt.to_timestamp()
    for k in itcrm.SOCIOS:
        d[f"{k}_var_m"] = d[k].pct_change(1, fill_method=None) * 100
        d[f"{k}_var_ia"] = d[k].pct_change(12, fill_method=None) * 100
    return d[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    return itcrm.validar(nuevo, anterior, columnas, minimo=300, dias=45, base_diaria=False)
