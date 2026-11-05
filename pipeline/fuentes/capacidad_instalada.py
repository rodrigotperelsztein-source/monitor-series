"""Utilización de la capacidad instalada en la industria (UCII), nivel general y bloques sectoriales, % (INDEC).

Archivo: sh_capacidad_<mes>_<año>.xls (el nombre lleva la fecha de publicación: se prueba del mes actual hacia atrás).
"""

from datetime import date

import pandas as pd

from pipeline.fuentes._fechas import urls_mm_aa
from pipeline.fuentes._indec import Columna, leer_tabla_mensual, validar_tabla

ID = "capacidad_instalada"
NOMBRE = "Utilización de la capacidad instalada en la industria (INDEC)"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/sh_capacidad_{mm}_{aa}.xls"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-6-15"
EXTENSION = "xls"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "% de la capacidad instalada"
PRIMER_PERIODO = "2016-01-01"
CALENDARIO = "Utilización de la capacidad instalada en la industria"
HOJA = "UCI - NG y bloques"

BLOQUES = {"nivel_general": "Nivel general", "alimentos": "Productos alimenticios y bebidas", "tabaco": "Productos del tabaco",
           "textiles": "Productos textiles", "papel": "Papel y cartón", "edicion": "Edición e impresión",
           "refinacion_petroleo": "Refinación del petróleo", "quimicos": "Sustancias y productos químicos",
           "caucho_plastico": "Productos de caucho y plástico", "minerales_no_metalicos": "Productos minerales no metálicos",
           "metalicas_basicas": "Industrias metálicas básicas", "automotriz": "Industria automotriz",
           "metalmecanica": "Metalmecánica excluida industria automotriz"}
COLUMNAS = {k: Columna(v, f"Capacidad instalada utilizada: {v.lower() if k != 'nivel_general' else 'nivel general'}")
            for k, v in BLOQUES.items()}


def urls(hoy: date) -> list[str]:
    return urls_mm_aa(URL, hoy)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    return leer_tabla_mensual(contenido, HOJA, columnas)


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    return validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, set(columnas), rango_nivel=(-0.01, 100))  # en abril de 2020 algunos bloques marcaron 0
