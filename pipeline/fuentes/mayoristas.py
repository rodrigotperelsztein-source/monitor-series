"""Encuesta de autoservicios mayoristas: índice de ventas a precios constantes y ventas en pesos (INDEC).

Archivo: serie_autoservicios_mayoristas.xlsx. Cuadros 1 (índice de ventas) y 3 (ventas en millones de pesos).
"""

import pandas as pd

from pipeline.fuentes._indec import Columna, leer_tabla_mensual, validar_tabla

ID = "mayoristas"
NOMBRE = "Encuesta de autoservicios mayoristas: índice de ventas y ventas totales (INDEC)"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/serie_autoservicios_mayoristas.xlsx"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-1-168"
EXTENSION = "xlsx"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Índice de ventas a precios constantes"
PRIMER_PERIODO = "2017-01-01"
CALENDARIO = "Encuesta de autoservicios mayoristas"

ORIG, DES = "Serie original", "Serie desestacionalizada"
INDICE = "Índice de ventas totales a precios constantes"
COLUMNAS = {
    "indice": Columna(f"{ORIG} | {INDICE}", "Índice de ventas a precios constantes, serie original", hoja="Cuadro 1."),
    "indice_var_ia": Columna(f"{ORIG} | Variación porcentual | respecto al mismo mes", "Índice de ventas, var. % interanual",
                             tipo="variacion", base="indice", rezago=12, hoja="Cuadro 1."),
    "indice_desest": Columna(f"{DES} | {INDICE}", "Índice de ventas, serie desestacionalizada", hoja="Cuadro 1."),
    "indice_desest_var_m": Columna(f"{DES} | Variación porcentual respecto al mes anterior", "Índice de ventas, desestacionalizada, var. % mensual",
                                   tipo="variacion", base="indice_desest", rezago=1, hoja="Cuadro 1."),
    "ventas_corrientes": Columna("Ventas totales | a precios corrientes", "Ventas totales a precios corrientes", unidad="Millones de $", hoja="Cuadro 3."),
    "ventas_constantes": Columna("Ventas totales | a precios constantes", "Ventas totales a precios constantes", unidad="Millones de $", hoja="Cuadro 3."),
}


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    return leer_tabla_mensual(contenido, None, columnas)


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    return validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, {"ventas_corrientes"}, rango_nivel=(0, 1e9), max_variacion=1000)
