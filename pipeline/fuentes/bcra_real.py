"""BCRA en términos reales: los saldos mensuales en pesos de `bcra_mensual` (promedio del mes) deflactados por el IPC
nacional, a precios de diciembre de 2016, con variación interanual. Suma además los préstamos comerciales (adelantos en
cuenta corriente más documentos), nominales y reales.
"""

import pandas as pd

from pipeline.fuentes import bcra, bcra_mensual, ipc
from pipeline.fuentes._indec import Columna

ID = "bcra_real"
NOMBRE = "BCRA: base monetaria, depósitos y préstamos en términos reales (deflactados por el IPC)"
DERIVADA_DE = (bcra_mensual.ID, ipc.ID)
URL = "data/bcra_mensual.csv y data/ipc.csv"
PAGINA = bcra.PAGINA
FRECUENCIA = "M"
ORGANISMO = "BCRA e INDEC; cálculo propio"
UNIDAD = "Millones de $ de dic-2016"
CALENDARIO = ""
VERSION = "2026-11-05"

IPC = "nacional_nivel_general_indice"
BASES = [k for k, (_, _, u, a) in bcra.VARIABLES.items() if u == "Millones de $" and a == "promedio"]
COMERCIALES = ("prestamos_adelantos", "prestamos_documentos")
COLUMNAS = {"prestamos_comerciales": Columna("", "Préstamos comerciales (adelantos y documentos), promedio del mes",
                                            unidad="Millones de $")}
for _k in ["prestamos_comerciales", *BASES]:
    _n = "Préstamos comerciales (adelantos y documentos)" if _k == "prestamos_comerciales" else bcra.VARIABLES[_k][1]
    COLUMNAS[f"{_k}_real"] = Columna("", f"{_n}, a precios de diciembre de 2016")
    COLUMNAS[f"{_k}_real_var_ia"] = Columna("", f"{_n}, real, var. % interanual", unidad="%", tipo="variacion",
                                            base=f"{_k}_real", rezago=12)


def calcular(mensual: pd.DataFrame, serie_ipc: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = mensual.merge(serie_ipc[["fecha", IPC]], on="fecha", how="inner").sort_values("fecha").reset_index(drop=True)
    df["prestamos_comerciales"] = df[list(COMERCIALES)].sum(axis=1, min_count=2)
    nuevas = {"fecha": df["fecha"], "prestamos_comerciales": df["prestamos_comerciales"]}
    for k in ["prestamos_comerciales", *BASES]:
        real = df[k] / df[IPC] * 100
        nuevas[f"{k}_real"] = real
        nuevas[f"{k}_real_var_ia"] = (real / real.shift(12) - 1) * 100
    return pd.DataFrame(nuevas)[["fecha", *COLUMNAS]], {"deflactor": f"IPC nacional, nivel general (ipc.{IPC}), base dic-2016=100"}


def validar(nuevo: pd.DataFrame, mensual: pd.DataFrame, serie_ipc: pd.DataFrame) -> list[str]:
    errores = []
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("los meses no son consecutivos")
    if nuevo["base_monetaria_real"].tail(12).isna().any():
        errores.append("falta la base monetaria real del último año")
    return errores
