"""Remuneración promedio real de los asalariados registrados del sector privado por rama de actividad, a precios del
último IPC publicado (pesos de hoy), con variación interanual real.

Se calcula desde data/salarios_ramas.csv con el IPC nacional de INDEC (nivel general), igual que
remuneraciones_provincias_real; empieza en diciembre de 2016, con el IPC nacional. Incluye el aguinaldo de junio y
diciembre: para comparar meses conviene la variación interanual (o el promedio de 12 meses).
"""

import pandas as pd

from pipeline.fuentes import ipc, salarios_ramas as sr
from pipeline.fuentes._indec import Columna

ID = "salarios_ramas_real"
NOMBRE = "Remuneración promedio real por rama de actividad (a precios del último IPC), asalariados registrados privados"
DERIVADA_DE = (sr.ID, ipc.ID)
URL = "data/salarios_ramas.csv y data/ipc.csv"
PAGINA = sr.PAGINA
FRECUENCIA = "M"
ORGANISMO = "Secretaría de Trabajo (OEDE, SIPA) e INDEC; cálculo propio"
UNIDAD = "Pesos del último IPC publicado"
CALENDARIO = ""
VERSION = "2026-10-30"
IPC = "nacional_nivel_general_indice"

COLUMNAS = {}
for _c, _col in sr.COLUMNAS.items():
    _n = _col.nombre.replace("Remuneración promedio", "Remuneración promedio real")
    COLUMNAS[f"{_c}_real"] = Columna("", f"{_n} (a precios del último IPC)")
    COLUMNAS[f"{_c}_real_var_ia"] = Columna("", f"{_n}, var. % interanual real", tipo="variacion", base=f"{_c}_real", rezago=12)


def calcular(sal: pd.DataFrame, serie_ipc: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = sal.merge(serie_ipc[["fecha", IPC]], on="fecha", how="inner").sort_values("fecha").reset_index(drop=True)
    ultimo = serie_ipc.dropna(subset=[IPC]).iloc[-1]
    out = pd.DataFrame({"fecha": df["fecha"]})
    for c in sr.COLUMNAS:
        out[f"{c}_real"] = df[c] / df[IPC] * ultimo[IPC]
        out[f"{c}_real_var_ia"] = out[f"{c}_real"].pct_change(12, fill_method=None) * 100
    return out[["fecha", *COLUMNAS]], {"deflactor": f"IPC nacional (ipc.{IPC})", "precios_del_ultimo_mes": f"{ultimo['fecha']:%Y-%m}"}


def validar(nuevo: pd.DataFrame, sal: pd.DataFrame, serie_ipc: pd.DataFrame) -> list[str]:
    errores = []
    if len(nuevo) < 100:
        errores.append(f"muy pocos meses en común con el IPC ({len(nuevo)})")
    if nuevo["total_real"].isna().any():
        errores.append("hay meses sin total")
    return errores
