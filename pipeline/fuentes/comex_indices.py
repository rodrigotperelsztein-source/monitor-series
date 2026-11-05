"""Índices de precios y cantidades del comercio exterior, mensuales, base 2004=100 (INDEC).

Archivo: serie_mensual_indices_comex.xls. Exportaciones e importaciones: valor, precio y cantidad. Los términos del
intercambio (precio de exportación / precio de importación) se calculan acá.
"""

import pandas as pd

from pipeline.fuentes._indec import Columna, leer_tabla_mensual, validar_tabla

ID = "comex_indices"
NOMBRE = "Índices de precios y cantidades del comercio exterior (INDEC)"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/serie_mensual_indices_comex.xls"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-2-41"
EXTENSION = "xls"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Índice base 2004=100"
PRIMER_PERIODO = "2004-01-01"
CALENDARIO = "Intercambio comercial argentino"
HOJA = "sh_indec_comext_04"

COLUMNAS = {f"{f}_{m}": Columna(f"{F} | {M}", f"{F.capitalize()}: índice de {M.lower()}")
            for f, F in (("expo", "Exportaciones"), ("impo", "Importaciones"))
            for m, M in (("valor", "Valor"), ("precio", "Precio"), ("cantidad", "Cantidad"))}
COLUMNAS["terminos_intercambio"] = Columna("", "Términos del intercambio (precio de exportación / precio de importación × 100)")


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    base = {k: v for k, v in columnas.items() if k != "terminos_intercambio"}
    df = leer_tabla_mensual(contenido, HOJA, base)
    df["terminos_intercambio"] = df["expo_precio"] / df["impo_precio"] * 100
    return df[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    return validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, set(columnas), rango_nivel=(0, 5000), max_variacion=1000)
