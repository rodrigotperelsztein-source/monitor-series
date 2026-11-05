"""Encuesta de comercios de electrodomésticos y artículos para el hogar: ventas por rubro (INDEC).

Archivo: sh_electro_<mes>_<año>.xls (nombre con la fecha de publicación). Ventas en millones de pesos corrientes
(cuadros 1 y 2). Trimestral en su difusión, con datos mensuales.
"""

from datetime import date

import pandas as pd

from pipeline.fuentes._fechas import urls_mm_aa
from pipeline.fuentes._indec import Columna, leer_tabla_mensual, validar_tabla

ID = "electrodomesticos"
NOMBRE = "Encuesta de comercios de electrodomésticos: ventas por rubro (INDEC)"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/sh_electro_{mm}_{aa}.xls"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-1-37"
EXTENSION = "xls"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Millones de $ corrientes"
PRIMER_PERIODO = "2020-01-01"
CALENDARIO = "Encuesta de comercios de electrodomésticos"

RUBROS = {"televisores": "Televisores, video y fotografía", "audio": "Equipos de audio, radios y similares",
          "heladeras": "Heladeras y freezers", "aire_acondicionado": "Equipos de aire acondicionado y climatizadores",
          "lavarropas": "Lavarropas, secarropas y lavavajillas", "cocinas": "Cocinas a gas y eléctricas",
          "computacion": "Computación y accesorios informáticos", "telefonia": "Telefonía", "cuidado_personal": "Cuidado personal",
          "pequenos": "Pequeños electrodomésticos", "otros": "Otros electrodomésticos y artículos para el hogar"}
COLUMNAS = {"ventas": Columna("Ventas totales | Millones de pesos", "Ventas totales a precios corrientes", hoja="Cuadro 1"),
            "ventas_var_ia": Columna("Variación porcentual | respecto al mismo mes", "Ventas totales, var. % interanual",
                                     tipo="variacion", base="ventas", rezago=12, hoja="Cuadro 1")}
COLUMNAS |= {f"ventas_{k}": Columna(v, f"Ventas: {v.lower()}", hoja="Cuadro 2") for k, v in RUBROS.items()}


def urls(hoy: date) -> list[str]:
    return urls_mm_aa(URL, hoy)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    return leer_tabla_mensual(contenido, None, columnas)


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    return validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, set(columnas), rango_nivel=(0, 1e9), max_variacion=1000)
