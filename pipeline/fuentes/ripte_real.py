"""RIPTE real: el RIPTE deflactado por el IPC nacional de INDEC (nivel general).

Se calcula desde data/ripte.csv y data/ipc.csv cada vez que cambia alguno de los dos.
Empieza en diciembre de 2016, primer mes del IPC nacional, y termina en el último mes que
tienen las dos series.

Dos expresiones de la misma serie:
  - a precios de diciembre de 2016 (igual que Monitor Argy): fija, no cambia con cada dato nuevo;
  - a precios del último mes con datos de las dos series (hoy, el último RIPTE publicado): el último
    valor coincide con el RIPTE nominal. Es más fácil de leer, pero se reescala toda cada mes.
"""

import pandas as pd

from pipeline.fuentes import ipc, ripte
from pipeline.fuentes._indec import Columna

ID = "ripte_real"
NOMBRE = "RIPTE real (deflactado por el IPC nacional)"
DERIVADA_DE = (ripte.ID, ipc.ID)
URL = "data/ripte.csv y data/ipc.csv"
PAGINA = ripte.PAGINA
FRECUENCIA = "M"
ORGANISMO = "Subsecretaría de Seguridad Social e INDEC; cálculo propio"
UNIDAD = "Pesos constantes"
CALENDARIO = ""
VERSION = "2026-10-19b"

IPC = "nacional_nivel_general_indice"
COLUMNAS = {
    "ripte_real": Columna("", "RIPTE real, a precios de diciembre de 2016", unidad="Pesos de dic-2016"),
    "ripte_real_ultimo_mes": Columna("", "RIPTE real, a precios del último mes disponible",
                                     unidad="Pesos del último mes disponible"),
    "ripte_real_var_m": Columna("", "RIPTE real, var. % mensual", tipo="variacion", base="ripte_real", rezago=1),
    "ripte_real_var_ia": Columna("", "RIPTE real, var. % interanual", tipo="variacion", base="ripte_real", rezago=12),
}


def calcular(serie_ripte: pd.DataFrame, serie_ipc: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = serie_ripte[["fecha", "ripte"]].merge(serie_ipc[["fecha", IPC]], on="fecha", how="inner")
    df = df.sort_values("fecha").reset_index(drop=True)
    df["ripte_real"] = df["ripte"] / df[IPC] * 100
    ultimo = df.iloc[-1]  # último mes con RIPTE e IPC
    df["ripte_real_ultimo_mes"] = df["ripte"] / df[IPC] * ultimo[IPC]
    df["ripte_real_var_m"] = df["ripte_real"].pct_change() * 100
    df["ripte_real_var_ia"] = df["ripte_real"].pct_change(12) * 100
    detalle = {"deflactor": f"IPC nacional, nivel general (ipc.{IPC}), base dic-2016=100",
               "precios_del_ultimo_mes": f"{ultimo['fecha']:%Y-%m}"}
    return df[["fecha", *COLUMNAS]], detalle


def validar(nuevo: pd.DataFrame, serie_ripte: pd.DataFrame, serie_ipc: pd.DataFrame) -> list[str]:
    errores = []
    if len(nuevo) < 100:
        errores.append(f"muy pocos meses en común entre el RIPTE y el IPC ({len(nuevo)})")
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("los meses no son consecutivos")
    if nuevo[["ripte_real", "ripte_real_ultimo_mes"]].isna().any().any():
        errores.append("hay meses sin valor")
    if (nuevo["ripte_real_var_m"].abs() > 30).any():
        errores.append("variaciones mensuales reales mayores a 30%")
    return errores
