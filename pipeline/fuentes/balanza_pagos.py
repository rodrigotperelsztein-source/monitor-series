"""Balanza de pagos trimestral: cuenta corriente, de capital y financiera, millones de dólares (INDEC, Balanza de pagos,
posición de inversión internacional y deuda externa).

Archivo: cin_<trimestre en romanos>_<año>.xls (nombre con el último trimestre publicado). Cuadro 1 (resumen por
componentes y categoría funcional).
"""

from datetime import date

import pandas as pd

from pipeline.fuentes import _trimestral as t
from pipeline.fuentes._fechas import urls_trimestre
from pipeline.fuentes._indec import Columna, buscar_hoja, leer_excel
from pipeline.fuentes._trim_fuente import a_tabla, validar_trimestral

ID = "balanza_pagos"
NOMBRE = "Balanza de pagos: cuenta corriente, de capital y financiera (INDEC, trimestral)"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/cin_{t}_{anio}.xls"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-35-45"
EXTENSION = "xls"
FRECUENCIA = "Q"
ORGANISMO = "INDEC"
UNIDAD = "Millones de USD"
PRIMER_PERIODO = "2006-01-01"
CALENDARIO = "Balanza de pagos"

# id -> (rótulo, rótulo anterior si el rótulo se repite, nombre)
FILAS = {
    "cuenta_corriente": ("1. CUENTA CORRIENTE", None, "Cuenta corriente"),
    "bienes_y_servicios": ("1.A BIENES Y SERVICIOS", None, "Bienes y servicios: saldo"),
    "bienes": ("1.A.A BIENES", None, "Bienes: saldo"),
    "bienes_exportaciones": ("CREDITO", "1.A.A BIENES", "Bienes: exportaciones"),
    "bienes_importaciones": ("DEBITO", "1.A.A BIENES", "Bienes: importaciones"),
    "servicios": ("1.A.B SERVICIOS", None, "Servicios: saldo"),
    "servicios_exportaciones": ("CREDITO", "1.A.B SERVICIOS", "Servicios: exportaciones"),
    "servicios_importaciones": ("DEBITO", "1.A.B SERVICIOS", "Servicios: importaciones"),
    "ingreso_primario": ("1.B INGRESO PRIMARIO", None, "Ingreso primario: saldo"),
    "renta_inversion": ("1.B.2 RENTA DE LA INVERSION", None, "Renta de la inversión: saldo"),
    "renta_inversion_directa": ("1.B.2.1 INVERSION DIRECTA", None, "Renta de la inversión directa: saldo"),
    "renta_inversion_cartera": ("1.B.2.2 INVERSION DE CARTERA", None, "Renta de la inversión de cartera: saldo"),
    "renta_otra_inversion": ("1.B.2.3 OTRA INVERSION", None, "Renta de otra inversión (intereses de préstamos): saldo"),
    "ingreso_secundario": ("1.C", None, "Ingreso secundario: saldo"),
    "cuenta_capital": ("2. CUENTA DE CAPITAL", None, "Cuenta de capital"),
    "prestamo_neto": ("PRESTAMO NETO", None, "Préstamo neto (+) / endeudamiento neto (-)"),
    "cuenta_financiera": ("3. CUENTA FINANCIERA", None, "Cuenta financiera"),
    "inversion_directa": ("3.1 INVERSION DIRECTA", None, "Inversión directa: neto"),
    "inversion_directa_pasivos": ("PASIVOS", "3.1 INVERSION DIRECTA", "Inversión directa en Argentina (pasivos)"),
    "inversion_cartera": ("3.2 INVERSION DE CARTERA", None, "Inversión de cartera: neto"),
    "derivados": ("3.3 INSTRUMENTOS FINANCIEROS DERIVADOS", None, "Derivados financieros: neto"),
    "otra_inversion": ("3.4 OTRA INVERSION", None, "Otra inversión: neto"),
    "activos_reserva": ("3.5 ACTIVOS DE RESERVA", None, "Variación de activos de reserva"),
    "errores_omisiones": ("ERRORES Y OMISIONES", None, "Errores y omisiones netos"),
}
COLUMNAS = {k: Columna("", n) for k, (_, _, n) in FILAS.items()}


def urls(hoy: date) -> list[str]:
    return urls_trimestre(URL, hoy)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    filas = t.filas(buscar_hoja(leer_excel(contenido), "Cuadro 1"))
    s = {k: t.buscar(filas, r, despues_de=d) for k, (r, d, _) in FILAS.items()}
    return a_tabla(s, PRIMER_PERIODO)[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = validar_trimestral(nuevo, anterior, columnas, PRIMER_PERIODO)
    d = nuevo.dropna()
    cc = d["bienes_y_servicios"] + d["ingreso_primario"] + d["ingreso_secundario"]
    if ((cc - d["cuenta_corriente"]).abs() > 5).any():
        errores.append("Los componentes no suman la cuenta corriente.")
    b = d["bienes_exportaciones"] - d["bienes_importaciones"]
    if ((b - d["bienes"]).abs() > 5).any():
        errores.append("Exportaciones menos importaciones de bienes no da el saldo de bienes.")
    return errores
