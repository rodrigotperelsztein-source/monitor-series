"""Liquidación de divisas por exportaciones de oleaginosas y cereales (CIARA-CEC, publicada por el Ministerio de
Economía en la serie 349.2 de datos.gob.ar).

Es el ingreso de dólares del complejo agroexportador: el monto acumulado del mes y el promedio por día hábil.
datos.gob.ar suele ir un mes atrás de lo que CIARA-CEC publica en su propia página.
"""

import pandas as pd

from pipeline.fuentes import _csv_datos as csvd
from pipeline.fuentes._indec import Columna

ID = "liquidacion_agro"
NOMBRE = "Liquidación de divisas del agro (CIARA-CEC)"
URL = "https://infra.datos.gob.ar/catalog/sspm/dataset/349/distribution/349.2/download/liquidacion-divisas-exportaciones-oleaginosas-cereales-mensual.csv"
PAGINA = "https://www.ciaracec.com.ar/estadisticas/"
EXTENSION = "csv"
FRECUENCIA = "M"
ORGANISMO = "CIARA-CEC (vía Ministerio de Economía)"
UNIDAD = "musd"
PRIMER_PERIODO = "2003-01-01"
CALENDARIO = ""
MAX_DIAS_SIN_NOVEDAD = 75

COLUMNAS = {
    "liquidacion": Columna("", "Liquidación de divisas del agro, monto del mes"),
    "liquidacion_promedio_diario": Columna("", "Liquidación de divisas del agro, promedio por día hábil"),
    "liquidacion_var_ia": Columna("", "Liquidación de divisas del agro, var. % interanual", unidad="pct",
                                  tipo="variacion", base="liquidacion", rezago=12),
}


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    df = csvd.leer(contenido, {"liquidacion": "acum_mensual", "liquidacion_promedio_diario": "promedio_diario"},
                   PRIMER_PERIODO)
    df["liquidacion_var_ia"] = (df["liquidacion"] / df["liquidacion"].shift(12) - 1) * 100
    return df[["fecha", *columnas]]


def validar(nuevo, anterior, columnas=COLUMNAS):
    errores = csvd.validar(nuevo, anterior, columnas, PRIMER_PERIODO, max_atraso_dias=75,
                           obligatorias=("liquidacion",))
    if not nuevo["liquidacion"].dropna().tail(24).between(200, 15_000).all():
        errores.append("Liquidación mensual fuera de rango (¿cambió la unidad?).")
    return errores
