"""Encuesta de centros de compras (shoppings): índice de ventas a precios constantes y ventas por rubro (INDEC).

Archivo: sh_compras_<mes>_<año>.xls (nombre con la fecha de publicación). Cuadros 1 (índice) y 3 (ventas en millones de
pesos corrientes, total del país y por rubro).
"""

from datetime import date

import pandas as pd

from pipeline.fuentes._fechas import urls_mm_aa
from pipeline.fuentes._indec import Columna, leer_tabla_mensual, validar_tabla

ID = "shoppings"
NOMBRE = "Encuesta de centros de compras: índice de ventas y ventas por rubro (INDEC)"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/sh_compras_{mm}_{aa}.xls"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-1-36"
EXTENSION = "xls"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Según la serie"
PRIMER_PERIODO = "2017-01-01"
CALENDARIO = "Encuesta de centros de compras"

ORIG, DES = "Serie original", "Serie desestacionalizada"
INDICE = "Índice de ventas totales a precios constantes"
RUBROS = {"indumentaria": "Indumentaria, calzado y marroquinería", "deportes": "Ropa y accesorios deportivos",
          "hogar": "Amoblamientos, decoración y textiles para el hogar", "comidas": "Patio de comidas, alimentos y kioscos",
          "electronicos": "Electrónicos, CD, electrodomésticos y computación", "jugueteria": "Juguetería",
          "libreria": "Librería y papelería", "diversion": "Diversión y esparcimiento", "perfumeria": "Perfumería y farmacia",
          "otros": "Otros"}
COLUMNAS = {
    "indice": Columna(f"{ORIG} | {INDICE}", "Índice de ventas a precios constantes, serie original", hoja="CuadroWEB_1"),
    "indice_var_ia": Columna(f"{ORIG} | Variación porcentual | respecto al mismo mes", "Índice de ventas, var. % interanual",
                             tipo="variacion", base="indice", rezago=12, hoja="CuadroWEB_1"),
    "indice_desest": Columna(f"{DES} | {INDICE}", "Índice de ventas, serie desestacionalizada", hoja="CuadroWEB_1"),
    "indice_desest_var_m": Columna(f"{DES} | Variación porcentual respecto al mes anterior", "Índice de ventas, desestacionalizada, var. % mensual",
                                   tipo="variacion", base="indice_desest", rezago=1, hoja="CuadroWEB_1"),
    "ventas_corrientes": Columna("Total del país | Total", "Ventas totales a precios corrientes", unidad="Millones de $", hoja="CuadroWEB_3"),
}
COLUMNAS |= {f"ventas_{k}": Columna(f"Total del país | {v}", f"Ventas a precios corrientes: {v.lower()}", unidad="Millones de $",
                                    hoja="CuadroWEB_3") for k, v in RUBROS.items()}


def urls(hoy: date) -> list[str]:
    return urls_mm_aa(URL, hoy)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    return leer_tabla_mensual(contenido, None, columnas)


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    corrientes = {c for c in columnas if c.startswith("ventas_")}
    return validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, corrientes, rango_nivel=(0, 1e9), max_variacion=100000,
                        vacios_permitidos={"ventas_diversion"})  # cerrados en la pandemia; rebote de 2021
