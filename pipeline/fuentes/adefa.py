"""Industria automotriz: producción, exportaciones y ventas a concesionarios de automóviles y utilitarios, unidades
(ADEFA, publicado por el Ministerio de Economía en la serie 330.3 de datos.gob.ar).
"""

import pandas as pd

from pipeline.fuentes import _csv_datos as csvd
from pipeline.fuentes._indec import Columna

ID = "adefa"
NOMBRE = "Industria automotriz: producción, exportaciones y ventas internas (ADEFA)"
URL = "https://infra.datos.gob.ar/catalog/sspm/dataset/330/distribution/330.3/download/datos-historicos-industria-automotriz-unidades-mensuales.csv"
PAGINA = "https://www.adefa.org.ar/es/estadisticas-mensuales"
EXTENSION = "csv"
FRECUENCIA = "M"
ORGANISMO = "ADEFA (vía Ministerio de Economía)"
UNIDAD = "Unidades"
PRIMER_PERIODO = "1993-01-01"
CALENDARIO = ""

MAPA = {"produccion_automoviles": "produccion_automoviles", "produccion_utilitarios": "produccion_utilitarios",
        "exportaciones_automoviles": "exportaciones_automoviles", "exportaciones_utilitarios": "exportaciones_utilitarios",
        "ventas_internas_automoviles": "ventas_mercado_interno_automoviles",
        "ventas_internas_utilitarios": "ventas_mercado_interno_utilitarios",
        "ventas_internas_nacionales": "ventas_mercado_interno_vehiculos_nacionales_total",
        "ventas_internas_importados": "ventas_mercado_interno_vehiculos_importados_total"}
NOMBRES = {"produccion": "Producción de automóviles y utilitarios", "produccion_automoviles": "Producción de automóviles",
           "produccion_utilitarios": "Producción de utilitarios", "exportaciones": "Exportaciones de automóviles y utilitarios",
           "exportaciones_automoviles": "Exportaciones de automóviles", "exportaciones_utilitarios": "Exportaciones de utilitarios",
           "ventas_internas": "Ventas a concesionarios de automóviles y utilitarios",
           "ventas_internas_automoviles": "Ventas a concesionarios: automóviles",
           "ventas_internas_utilitarios": "Ventas a concesionarios: utilitarios",
           "ventas_internas_nacionales": "Ventas a concesionarios: vehículos nacionales",
           "ventas_internas_importados": "Ventas a concesionarios: vehículos importados"}
COLUMNAS = {k: Columna("", n) for k, n in NOMBRES.items()}
COLUMNAS["produccion_var_ia"] = Columna("", "Producción de automóviles y utilitarios, var. % interanual", unidad="%",
                                        tipo="variacion", base="produccion", rezago=12)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    df = csvd.leer(contenido, MAPA, PRIMER_PERIODO)
    for k in ("produccion", "exportaciones", "ventas_internas"):
        df[k] = df[[f"{k}_automoviles", f"{k}_utilitarios"]].sum(axis=1, min_count=2)
    df["produccion_var_ia"] = (df["produccion"] / df["produccion"].shift(12) - 1) * 100
    return df[["fecha", *columnas]]


def validar(nuevo, anterior, columnas=COLUMNAS):
    return csvd.validar(nuevo, anterior, columnas, PRIMER_PERIODO, obligatorias=("produccion",))
