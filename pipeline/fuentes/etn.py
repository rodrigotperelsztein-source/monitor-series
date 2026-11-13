"""Encuesta de tendencia de negocios (INDEC): indicador de confianza empresarial de la industria manufacturera y
de los supermercados y autoservicios mayoristas.

Es un saldo de respuestas: el porcentaje de empresas que ve una mejora menos el que ve un deterioro, así que va
de -100 a 100 y el cero es el punto de equilibrio. Adelanta a la producción y a las ventas, porque pregunta por
la situación actual y por lo que las empresas esperan para los tres meses siguientes.

Archivos: serie_etn_im.xlsx (industria, desde 2025) y serie_etn_sam.xlsx (supermercados, desde 2020). Cuadro 1 de
cada uno es el indicador de confianza; el cuadro 3 son las expectativas a tres meses.
"""

import io
import zipfile
from datetime import date

import pandas as pd

from pipeline.fuentes._indec import Columna, leer_tabla_mensual, validar_tabla

ID = "etn"
NOMBRE = "Confianza empresarial: industria y supermercados (ETN, INDEC)"
URL_INDUSTRIA = "https://www.indec.gob.ar/ftp/cuadros/economia/serie_etn_im.xlsx"
URL_SUPERMERCADOS = "https://www.indec.gob.ar/ftp/cuadros/economia/serie_etn_sam.xlsx"
URL = URL_INDUSTRIA
PAGINA = "https://www.indec.gob.ar/Nivel4/Tema/3/5/32"
EXTENSION = "zip"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Saldo de respuestas (-100 a 100)"
PRIMER_PERIODO = "2020-01-01"
CALENDARIO = "Encuesta de tendencia de negocios"

_CONF = "Indicador de confianza empresarial | %"
COLUMNAS_INDUSTRIA = {
    "confianza_industria": Columna(_CONF, "Confianza empresarial en la industria manufacturera", hoja="Cuadro 1."),
}
COLUMNAS_SUPERMERCADOS = {
    "confianza_supermercados": Columna(_CONF, "Confianza empresarial en supermercados y autoservicios mayoristas",
                                       hoja="Cuadro 1."),
}
COLUMNAS = COLUMNAS_INDUSTRIA | COLUMNAS_SUPERMERCADOS


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("industria.xlsx", descargar(URL_INDUSTRIA, minimo=20_000))
        z.writestr("supermercados.xlsx", descargar(URL_SUPERMERCADOS, minimo=20_000))
    return f"{URL_INDUSTRIA} {URL_SUPERMERCADOS}", buf.getvalue()


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        partes = [leer_tabla_mensual(z.read(archivo), None, cols)
                  for archivo, cols in (("industria.xlsx", COLUMNAS_INDUSTRIA),
                                        ("supermercados.xlsx", COLUMNAS_SUPERMERCADOS))]
    df = partes[1].merge(partes[0], on="fecha", how="outer").sort_values("fecha").reset_index(drop=True)
    return df[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, set(columnas),
                            rango_nivel=(-100, 100), max_variacion=200,
                            vacios_permitidos={"confianza_industria"})
    for c in columnas:
        u = nuevo[c].dropna()
        if u.empty:
            errores.append(f"{c}: sin datos.")
        elif not u.between(-100, 100).all():
            errores.append(f"{c}: hay saldos fuera de -100 a 100.")
    return errores
