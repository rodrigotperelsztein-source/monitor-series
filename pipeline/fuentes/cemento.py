"""Despacho de cemento al mercado interno (producción nacional), miles de toneladas (AFCP, publicado por el Ministerio
de Economía en la serie 38.3 de datos.gob.ar). La misma serie trae el despacho de asfalto.
"""

import pandas as pd

from pipeline.fuentes import _csv_datos as csvd
from pipeline.fuentes._indec import Columna

ID = "cemento"
NOMBRE = "Despacho de cemento al mercado interno (AFCP)"
URL = "https://infra.datos.gob.ar/catalog/sspm/dataset/38/distribution/38.3/download/ventas-al-mercado-interno-produccion-nacional-base-1994-valores-mensuales.csv"
PAGINA = "https://www.afcp.org.ar/despacho-mensual"
EXTENSION = "csv"
FRECUENCIA = "M"
ORGANISMO = "AFCP (vía Ministerio de Economía)"
UNIDAD = "Miles de toneladas"
PRIMER_PERIODO = "1994-01-01"
CALENDARIO = ""

COLUMNAS = {"despacho": Columna("", "Despacho de cemento al mercado interno"),
            "despacho_var_ia": Columna("", "Despacho de cemento, var. % interanual", unidad="%", tipo="variacion",
                                       base="despacho", rezago=12),
            "asfalto": Columna("", "Despacho de asfalto al mercado interno")}


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    df = csvd.leer(contenido, {"despacho": "cemento", "asfalto": "asfalto"}, PRIMER_PERIODO)
    df = df[df["fecha"] <= df.loc[df["despacho"].last_valid_index(), "fecha"]]
    df["despacho_var_ia"] = (df["despacho"] / df["despacho"].shift(12) - 1) * 100
    return df[["fecha", *columnas]]


def validar(nuevo, anterior, columnas=COLUMNAS):
    return csvd.validar(nuevo, anterior, columnas, PRIMER_PERIODO, obligatorias=("despacho",))
