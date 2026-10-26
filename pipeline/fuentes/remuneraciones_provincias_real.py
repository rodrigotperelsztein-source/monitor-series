"""Remuneración promedio real de los asalariados registrados del sector privado, por provincia.

La remuneración por provincia (remuneraciones_provincias) deflactada por el IPC nacional de INDEC (nivel general),
expresada a precios del último IPC publicado: cada valor es lo que esa remuneración compraría hoy. Como el IPC
nacional empieza en diciembre de 2016, la serie real empieza ahí. Se reescala entera cada vez que sale un IPC nuevo.

Se usa el IPC nacional en todas las provincias (no el regional) para que sean comparables entre sí; incluye el
aguinaldo de junio y diciembre, igual que la serie nominal. Para el total país se agrega la variación interanual real.
"""

import pandas as pd

from pipeline.fuentes import ipc, remuneraciones_provincias as rp
from pipeline.fuentes._indec import Columna

ID = "remuneraciones_provincias_real"
NOMBRE = "Remuneración promedio real de los asalariados registrados del sector privado, por provincia (a precios del último IPC)"
DERIVADA_DE = (rp.ID, ipc.ID)
URL = "data/remuneraciones_provincias.csv y data/ipc.csv"
PAGINA = rp.PAGINA
FRECUENCIA = "M"
ORGANISMO = "Secretaría de Trabajo (OEDE, SIPA) e INDEC; cálculo propio"
UNIDAD = "Pesos del último IPC publicado"
CALENDARIO = ""
VERSION = "2026-10-26"

IPC = "nacional_nivel_general_indice"
COLUMNAS = {f"{cid}_real": Columna("", f"Remuneración promedio real (a precios del último IPC): {n}")
            for cid, n in rp.PROVINCIAS.values()}
COLUMNAS["total_real_var_ia"] = Columna("", "Remuneración promedio real, total país, var. % interanual", tipo="variacion",
                                        base="total_real", rezago=12)


def calcular(rem: pd.DataFrame, serie_ipc: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = rem.merge(serie_ipc[["fecha", IPC]], on="fecha", how="inner").sort_values("fecha").reset_index(drop=True)
    ultimo = serie_ipc.dropna(subset=[IPC]).iloc[-1]  # último IPC publicado
    out = pd.DataFrame({"fecha": df["fecha"]})
    for cid, _ in rp.PROVINCIAS.values():
        out[f"{cid}_real"] = df[cid] / df[IPC] * ultimo[IPC]
    out["total_real_var_ia"] = out["total_real"].pct_change(12) * 100
    detalle = {"deflactor": f"IPC nacional, nivel general (ipc.{IPC})", "precios_del_ultimo_mes": f"{ultimo['fecha']:%Y-%m}"}
    return out[["fecha", *COLUMNAS]], detalle


def validar(nuevo: pd.DataFrame, rem: pd.DataFrame, serie_ipc: pd.DataFrame) -> list[str]:
    errores = []
    if len(nuevo) < 100:
        errores.append(f"muy pocos meses en común entre las remuneraciones y el IPC ({len(nuevo)})")
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("los meses no son consecutivos")
    if nuevo["total_real"].isna().any():
        errores.append("hay meses sin total país")
    return errores
