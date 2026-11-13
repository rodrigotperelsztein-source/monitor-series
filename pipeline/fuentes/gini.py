"""Coeficiente de Gini del ingreso per cápita familiar (INDEC, EPH): total de aglomerados urbanos, por trimestre.

Archivo: serie_coeficiente_gini.xlsx, una sola hoja con el año en una columna y el trimestre en otra. Se toma
desde 2003, cuando empieza la EPH continua; los puntos anteriores son de la EPH puntual de octubre y no son
comparables. El INDEC advierte además que la serie tiene cortes por los cambios de muestra de la encuesta.

Va de 0 a 1: cuanto más alto, más desigual es el reparto del ingreso.
"""

import io
import re

import pandas as pd

from pipeline.fuentes._indec import Columna, norm

ID = "gini"
NOMBRE = "Coeficiente de Gini del ingreso per cápita familiar (INDEC)"
URL = "https://www.indec.gob.ar/ftp/cuadros/sociedad/serie_coeficiente_gini.xlsx"
PAGINA = "https://www.indec.gob.ar/Nivel4/Tema/4/31/60"
EXTENSION = "xlsx"
FRECUENCIA = "Q"
ORGANISMO = "INDEC"
UNIDAD = "Coeficiente de 0 a 1"
PRIMER_PERIODO = "2003-07-01"
CALENDARIO = "Evolución de la distribución del ingreso"
MAX_DIAS_SIN_NOVEDAD = 220  # trimestral, con unos cuatro meses de rezago

COLUMNAS = {"gini": Columna("", "Coeficiente de Gini del ingreso per cápita familiar", unidad="Coeficiente")}


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    hoja = pd.read_excel(io.BytesIO(contenido), header=None)
    anio, filas = None, []
    for _, fila in hoja.iterrows():
        v0, v1, v2 = fila.iloc[0], fila.iloc[1], fila.iloc[2]
        m = re.fullmatch(r"((?:19|20)\d\d)", str(v0).strip().split(".")[0]) if pd.notna(v0) else None
        if m:
            anio = int(m.group(1))
        t = re.match(r"([1-4])\s*[ºoO°]?\s*TRIM", norm(v1)) if pd.notna(v1) else None
        if not (t and anio):
            continue
        valor = pd.to_numeric(v2, errors="coerce")
        if pd.notna(valor):
            filas.append((pd.Period(f"{anio}Q{t.group(1)}", "Q").start_time, float(valor)))
    df = pd.DataFrame(filas, columns=["fecha", "gini"]).drop_duplicates("fecha", keep="last").sort_values("fecha")
    df = df[df["fecha"] >= PRIMER_PERIODO].reset_index(drop=True)
    return df[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", "gini"]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    if len(nuevo) < 50:
        errores.append(f"Muy pocos trimestres: {len(nuevo)}.")
    if not nuevo["gini"].between(0.3, 0.7).all():
        errores.append("Hay coeficientes fuera de 0,3 a 0,7.")
    if anterior is not None and len(anterior) and len(nuevo) < len(anterior):
        errores.append("Se perdió historia.")
    return errores
