"""Recaudación tributaria real: la recaudación de ARCA deflactada por el IPC nacional (nivel general), a precios de
diciembre de 2016, con variación interanual. Empieza en diciembre de 2016, primer mes del IPC nacional.
"""

import pandas as pd

from pipeline.fuentes import ipc, recaudacion
from pipeline.fuentes._indec import Columna

ID = "recaudacion_real"
NOMBRE = "Recaudación tributaria real (deflactada por el IPC nacional)"
DERIVADA_DE = (recaudacion.ID, ipc.ID)
URL = "data/recaudacion.csv y data/ipc.csv"
PAGINA = recaudacion.PAGINA
FRECUENCIA = "M"
ORGANISMO = "ARCA, Ministerio de Economía e INDEC; cálculo propio"
UNIDAD = "Millones de $ de dic-2016"
CALENDARIO = ""
VERSION = "2026-11-05"

IPC = "nacional_nivel_general_indice"
BASES = [k for k, c in recaudacion.COLUMNAS.items() if c.tipo == "nivel"]
COLUMNAS = {}
for _k in BASES:
    _n = recaudacion.COLUMNAS[_k].nombre
    COLUMNAS[f"{_k}_real"] = Columna("", f"{_n}, a precios de diciembre de 2016")
    COLUMNAS[f"{_k}_real_var_ia"] = Columna("", f"{_n}, real, var. % interanual", unidad="%", tipo="variacion",
                                            base=f"{_k}_real", rezago=12)


def calcular(rec: pd.DataFrame, serie_ipc: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = rec.merge(serie_ipc[["fecha", IPC]], on="fecha", how="inner").sort_values("fecha").reset_index(drop=True)
    for k in BASES:
        df[f"{k}_real"] = df[k] / df[IPC] * 100
        df[f"{k}_real_var_ia"] = (df[f"{k}_real"] / df[f"{k}_real"].shift(12) - 1) * 100
    return df[["fecha", *COLUMNAS]], {"deflactor": f"IPC nacional, nivel general (ipc.{IPC}), base dic-2016=100"}


def validar(nuevo: pd.DataFrame, rec: pd.DataFrame, serie_ipc: pd.DataFrame) -> list[str]:
    errores = []
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("los meses no son consecutivos")
    if nuevo["total_real"].isna().any():
        errores.append("hay meses sin recaudación total real")
    return errores
