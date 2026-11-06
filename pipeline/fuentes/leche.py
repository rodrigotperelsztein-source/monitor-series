"""Producción primaria nacional de leche, millones de litros por mes (Secretaría de Agricultura, Dirección Nacional de
Lechería). Archivo PPV021_PPV022.xlsx, hoja Mensual (litros).
"""

import io

import pandas as pd

from pipeline.fuentes._indec import Columna

ID = "leche"
NOMBRE = "Producción primaria de leche (Dirección Nacional de Lechería)"
URL = "https://www.magyp.gob.ar/sitio/areas/ss_lecheria/estadisticas/_01_primaria/_archivos/PPV021_PPV022.xlsx"
PAGINA = "https://www.magyp.gob.ar/sitio/areas/ss_lecheria/estadisticas/_01_primaria/index.php"
EXTENSION = "xlsx"
FRECUENCIA = "M"
ORGANISMO = "Secretaría de Agricultura, Ganadería y Pesca (Dirección Nacional de Lechería)"
UNIDAD = "Millones de litros"
PRIMER_PERIODO = "2015-01-01"
CALENDARIO = ""

COLUMNAS = {"produccion": Columna("", "Producción primaria de leche"),
            "produccion_var_ia": Columna("", "Producción primaria de leche, var. % interanual", unidad="%",
                                         tipo="variacion", base="produccion", rezago=12)}


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    h = pd.read_excel(io.BytesIO(contenido), sheet_name="Mensual", header=None)
    fechas = pd.to_datetime(h.iloc[:, 1], errors="coerce")
    litros = pd.to_numeric(h.iloc[:, 2], errors="coerce")
    ok = fechas.notna() & litros.notna()
    if ok.sum() < 100:
        raise ValueError("La hoja Mensual no tiene la serie esperada (MES | Litros).")
    df = pd.DataFrame({"fecha": fechas[ok].dt.to_period("M").dt.to_timestamp(), "produccion": litros[ok] / 1e6})
    df = df.groupby("fecha", as_index=False).last().sort_values("fecha").reset_index(drop=True)
    df["produccion_var_ia"] = (df["produccion"] / df["produccion"].shift(12) - 1) * 100
    return df[["fecha", *columnas]]


def validar(nuevo, anterior, columnas=COLUMNAS):
    errores = []
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los meses no son consecutivos.")
    if not nuevo["produccion"].between(400, 1_600).all():
        errores.append("Producción fuera de rango (¿cambió la unidad?).")
    if anterior is not None and len(anterior) and len(nuevo) < len(anterior):
        errores.append("Se perdieron meses.")
    return errores
