"""Cobros de exportaciones y pagos de importaciones de bienes del balance cambiario del BCRA (mercado libre de
cambios), publicados por el Ministerio de Economía en la serie 183.1 de datos.gob.ar.

No son las exportaciones e importaciones devengadas del ICA del INDEC, sino los dólares que efectivamente entran y
salen por el mercado de cambios: la diferencia entre ambas mide el financiamiento comercial.
"""

import pandas as pd

from pipeline.fuentes import _csv_datos as csvd
from pipeline.fuentes._indec import Columna

ID = "balance_cambiario"
NOMBRE = "Cobros de exportaciones y pagos de importaciones de bienes (BCRA)"
URL = "https://infra.datos.gob.ar/catalog/sspm/dataset/183/distribution/183.1/download/cobros-pagos-bienes-modalidad.csv"
PAGINA = "https://www.bcra.gob.ar/PublicacionesEstadisticas/Mercado_de_cambios.asp"
EXTENSION = "csv"
FRECUENCIA = "M"
ORGANISMO = "BCRA (vía Ministerio de Economía)"
UNIDAD = "musd"
PRIMER_PERIODO = "2003-01-01"
CALENDARIO = ""
MAX_DIAS_SIN_NOVEDAD = 120  # el BCRA publica el balance cambiario con unos dos meses de rezago

MAPA = {
    "cobros_expo": "cobros_exportaciones_bienes",
    "pagos_impo": "pagos_importaciones_bienes",
    "saldo_bienes": "total_bienes",
    "cobros_expo_anticipados": "bienes_cobros_anticipados_exportaciones",
    "cobros_expo_prefinanciaciones": "bienes_cobros_prefinanciaciones_expo_del_exterrior",
    "pagos_impo_anticipados": "bienes_pagos_anticipados_importaciones",
    "pagos_impo_vista": "bienes_pagos_a_la_vista_importaciones",
}

COLUMNAS = {
    "cobros_expo": Columna("", "Cobros de exportaciones de bienes"),
    "pagos_impo": Columna("", "Pagos de importaciones de bienes"),
    "saldo_bienes": Columna("", "Saldo de bienes del balance cambiario (cobros menos pagos)"),
    "cobros_expo_anticipados": Columna("", "Cobros anticipados de exportaciones"),
    "cobros_expo_prefinanciaciones": Columna("", "Prefinanciaciones de exportaciones del exterior"),
    "pagos_impo_anticipados": Columna("", "Pagos anticipados de importaciones"),
    "pagos_impo_vista": Columna("", "Pagos a la vista de importaciones"),
    "cobros_expo_var_ia": Columna("", "Cobros de exportaciones de bienes, var. % interanual", unidad="pct",
                                  tipo="variacion", base="cobros_expo", rezago=12),
    "pagos_impo_var_ia": Columna("", "Pagos de importaciones de bienes, var. % interanual", unidad="pct",
                                 tipo="variacion", base="pagos_impo", rezago=12),
}


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    df = csvd.leer(contenido, MAPA, PRIMER_PERIODO)
    for c in ("cobros_expo", "pagos_impo"):
        df[f"{c}_var_ia"] = (df[c] / df[c].shift(12) - 1) * 100
    return df[["fecha", *columnas]]


def validar(nuevo, anterior, columnas=COLUMNAS):
    errores = csvd.validar(nuevo, anterior, columnas, PRIMER_PERIODO, max_atraso_dias=140,
                           obligatorias=("cobros_expo", "pagos_impo"))
    u = nuevo.dropna(subset=["cobros_expo", "pagos_impo"]).tail(24)
    if not u["cobros_expo"].between(1_000, 20_000).all() or not u["pagos_impo"].between(500, 15_000).all():
        errores.append("Cobros o pagos fuera de rango (¿cambió la unidad?).")
    saldo = (u["cobros_expo"] - u["pagos_impo"] - u["saldo_bienes"]).abs()
    if (saldo > 1).any():
        errores.append("El saldo de bienes no coincide con cobros menos pagos.")
    return errores
