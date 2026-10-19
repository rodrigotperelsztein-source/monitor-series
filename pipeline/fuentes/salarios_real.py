"""Índice de salarios real: cada índice de salarios de INDEC deflactado por el IPC nacional.

Índice de salarios (oct-2016=100) / IPC nivel general (dic-2016=100) × 100, igual que Monitor Argy.
Empieza en diciembre de 2016, primer mes del IPC nacional. Se recalcula cuando cambia
data/salarios.csv o data/ipc.csv.
"""

import pandas as pd

from pipeline.fuentes import ipc, salarios
from pipeline.fuentes._indec import Columna

ID = "salarios_real"
NOMBRE = "Índice de salarios real (deflactado por el IPC nacional)"
DERIVADA_DE = (salarios.ID, ipc.ID)
URL = "data/salarios.csv y data/ipc.csv"
PAGINA = salarios.PAGINA
FRECUENCIA = "M"
ORGANISMO = "INDEC; cálculo propio"
UNIDAD = "Índice real (salarios oct-2016=100 / IPC dic-2016=100)"
CALENDARIO = salarios.CALENDARIO
VERSION = "2026-10-19"

IPC = "nacional_nivel_general_indice"
COLUMNAS = {}
for _cid, (_orig, _nombre) in salarios.SERIES.items():
    COLUMNAS[f"{_cid}_real"] = Columna("", f"{_nombre}, real (deflactado por IPC)")
    COLUMNAS[f"{_cid}_real_var_m"] = Columna("", f"{_nombre}, real, var. % mensual",
                                             tipo="variacion", base=f"{_cid}_real", rezago=1)
    COLUMNAS[f"{_cid}_real_var_ia"] = Columna("", f"{_nombre}, real, var. % interanual",
                                              tipo="variacion", base=f"{_cid}_real", rezago=12)


def calcular(serie_salarios: pd.DataFrame, serie_ipc: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = serie_salarios.merge(serie_ipc[["fecha", IPC]], on="fecha", how="inner").sort_values("fecha")
    out = pd.DataFrame({"fecha": df["fecha"]})
    for cid in salarios.SERIES:
        real = df[cid] / df[IPC] * 100
        out[f"{cid}_real"] = real
        out[f"{cid}_real_var_m"] = real.pct_change(fill_method=None) * 100
        out[f"{cid}_real_var_ia"] = real.pct_change(12, fill_method=None) * 100
    return out.reset_index(drop=True), {"deflactor": f"IPC nacional, nivel general (ipc.{IPC}), base dic-2016=100"}


def validar(nuevo: pd.DataFrame, serie_salarios: pd.DataFrame, serie_ipc: pd.DataFrame) -> list[str]:
    errores = []
    if len(nuevo) < 100:
        errores.append(f"muy pocos meses en común entre salarios e IPC ({len(nuevo)})")
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("los meses no son consecutivos")
    niveles = [c for c, col in COLUMNAS.items() if col.tipo == "nivel"]
    if nuevo[niveles].isna().any().any():
        errores.append("hay meses sin valor")
    if (nuevo[[c for c in COLUMNAS if c.endswith("_var_m")]].abs() > 30).any().any():
        errores.append("variaciones mensuales reales mayores a 30%")
    return errores
