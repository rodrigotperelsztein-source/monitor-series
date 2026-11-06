"""Índice de producción industrial metalúrgica (IPIM), base 2015=100, original y desestacionalizado (ADIMRA, Estudios
Económicos).

ADIMRA publica la planilla en Google Drive y la enlaza desde https://www.adimra.org.ar/datos (la página arma el enlace
con JavaScript, así que el identificador del archivo está fijo acá; si ADIMRA lo cambia, la descarga falla y hay que
actualizarlo).
"""

import io

import pandas as pd

from pipeline.fuentes._indec import Columna
from pipeline.fuentes.deuda import _mes

ID = "adimra"
NOMBRE = "Índice de producción industrial metalúrgica (ADIMRA)"
URL = "https://drive.usercontent.google.com/download?id=1og3v0E-gs2ETlajmKd_ngyuwXECAZEUw&export=download"
PAGINA = "https://www.adimra.org.ar/datos"
EXTENSION = "xlsx"
FRECUENCIA = "M"
ORGANISMO = "ADIMRA"
UNIDAD = "Índice 2015=100"
PRIMER_PERIODO = "2016-01-01"
CALENDARIO = ""

COLUMNAS = {"indice": Columna("", "Índice de producción metalúrgica, serie original"),
            "indice_desest": Columna("", "Índice de producción metalúrgica, desestacionalizado (ADIMRA)"),
            "indice_var_ia": Columna("", "Índice de producción metalúrgica, var. % interanual", unidad="%", tipo="variacion",
                                     base="indice", rezago=12),
            "indice_desest_var_m": Columna("", "Índice de producción metalúrgica, desestacionalizado, var. % mensual",
                                           unidad="%", tipo="variacion", base="indice_desest", rezago=1)}


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    h = pd.read_excel(io.BytesIO(contenido), sheet_name="Producción", header=None)
    if "ORIGINAL" not in str(h.iloc[0, 1]).upper() or "DESESTACIONALIZADA" not in str(h.iloc[0, 2]).upper():
        raise ValueError(f"Encabezado inesperado en la planilla de ADIMRA: {h.iloc[0, :3].tolist()}")
    fechas = pd.Series([_mes(v) for v in h.iloc[:, 0]])
    ok = fechas.notna()
    df = pd.DataFrame({"fecha": pd.DatetimeIndex(fechas[ok]),
                       "indice": pd.to_numeric(h.iloc[:, 1][ok], errors="coerce").values,
                       "indice_desest": pd.to_numeric(h.iloc[:, 2][ok], errors="coerce").values})
    df = df.dropna(subset=["indice"]).sort_values("fecha").reset_index(drop=True)
    # Las variaciones de la planilla mezclan números y texto ("-6,1%"): se recalculan.
    df["indice_var_ia"] = (df["indice"] / df["indice"].shift(12) - 1) * 100
    df["indice_desest_var_m"] = (df["indice_desest"] / df["indice_desest"].shift(1) - 1) * 100
    return df[["fecha", *columnas]]


def validar(nuevo, anterior, columnas=COLUMNAS):
    errores = []
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los meses no son consecutivos.")
    if not nuevo["indice"].between(20, 200).all():
        errores.append("Índice fuera de rango.")
    if (pd.Timestamp.today() - nuevo["fecha"].max()).days > 120:
        errores.append("El último mes tiene más de cuatro meses.")
    if anterior is not None and len(anterior) and len(nuevo) < len(anterior):
        errores.append("Se perdieron meses.")
    return errores
