"""Encuesta de supermercados: índice de ventas a precios constantes (original,
desestacionalizado y tendencia-ciclo) y ventas totales en millones de pesos.

Fuente: INDEC, Encuesta de supermercados.
Archivo: serie_supermercados.xlsx. Cuadros: 1 (índice de ventas) y 3 (ventas en pesos).
"""

import pandas as pd

from pipeline.fuentes._indec import Columna, leer_tabla_mensual, validar_tabla

ID = "supermercados"
NOMBRE = "Encuesta de supermercados: índice de ventas y ventas totales"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/serie_supermercados.xlsx"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-1-34"
EXTENSION = "xlsx"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Índice de ventas a precios constantes"
PRIMER_PERIODO = "2017-01-01"
CALENDARIO = "Encuesta de supermercados"

ORIG, DES, TEN = "Serie original", "Serie desestacionalizada", "Serie tendencia-ciclo"
INDICE = "Índice de ventas totales a precios constantes"
MES_ANT = "Variación porcentual respecto al mes anterior"
MILLONES = "Millones de $"

COLUMNAS = {
    "indice": Columna(f"{ORIG} | {INDICE}", "Índice de ventas a precios constantes, serie original", hoja="Cuadro 1"),
    "indice_var_ia": Columna(f"{ORIG} | Variación porcentual | respecto al mismo mes",
                             "Índice de ventas, serie original, var. % interanual",
                             tipo="variacion", base="indice", rezago=12, hoja="Cuadro 1"),
    "indice_var_acum": Columna(f"{ORIG} | acumulada del año", "Índice de ventas, serie original, var. % acumulada en el año",
                               tipo="variacion", rezago=12, hoja="Cuadro 1"),
    "indice_desest": Columna(f"{DES} | {INDICE}", "Índice de ventas, serie desestacionalizada", hoja="Cuadro 1"),
    "indice_desest_var_m": Columna(f"{DES} | {MES_ANT}", "Índice de ventas, desestacionalizada, var. % mensual",
                                   tipo="variacion", base="indice_desest", rezago=1, hoja="Cuadro 1"),
    "indice_tendencia": Columna(f"{TEN} | {INDICE}", "Índice de ventas, serie tendencia-ciclo", hoja="Cuadro 1"),
    "indice_tendencia_var_m": Columna(f"{TEN} | {MES_ANT}", "Índice de ventas, tendencia-ciclo, var. % mensual",
                                      tipo="variacion", base="indice_tendencia", rezago=1, hoja="Cuadro 1"),
    "ventas_corrientes": Columna("Ventas totales | a precios corrientes", "Ventas totales a precios corrientes",
                                 unidad=MILLONES, hoja="Cuadro 3"),
    "ventas_constantes": Columna("Ventas totales | a precios constantes", "Ventas totales a precios constantes",
                                 unidad=MILLONES, hoja="Cuadro 3"),
    "ventas_corrientes_var_ia": Columna("Variación porcentual respecto al mismo período del año anterior | a precios corrientes",
                                        "Ventas a precios corrientes, var. % interanual",
                                        tipo="variacion", base="ventas_corrientes", rezago=12, hoja="Cuadro 3"),
    "ventas_constantes_var_ia": Columna("Variación porcentual respecto al mismo período del año anterior | a precios constantes",
                                        "Ventas a precios constantes, var. % interanual",
                                        tipo="variacion", base="ventas_constantes", rezago=12, hoja="Cuadro 3"),
}


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    return leer_tabla_mensual(contenido, None, columnas)


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    # Las ventas en pesos corrientes crecen con la inflación: el control interanual va solo para los índices.
    return validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, {"ventas_corrientes"},
                         rango_nivel=(0, 1e9), max_variacion=1000)
