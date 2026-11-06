"""Faena de ganado por especie, cabezas por mes (Secretaría de Agricultura, Ganadería y Pesca, publicado por el
Ministerio de Economía en la serie 40.3 de datos.gob.ar).
"""

import pandas as pd

from pipeline.fuentes import _csv_datos as csvd
from pipeline.fuentes._indec import Columna

ID = "faena"
NOMBRE = "Faena de ganado vacuno, porcino y ovino (Secretaría de Agricultura)"
URL = "https://infra.datos.gob.ar/catalog/sspm/dataset/40/distribution/40.3/download/faena-pecuaria-por-especies-valores-mensuales.csv"
PAGINA = "https://www.magyp.gob.ar/sitio/areas/bovinos/informacion_sectorial/"
EXTENSION = "csv"
FRECUENCIA = "M"
ORGANISMO = "Secretaría de Agricultura, Ganadería y Pesca (vía Ministerio de Economía)"
UNIDAD = "Cabezas"
PRIMER_PERIODO = "1990-01-01"
CALENDARIO = ""

ESPECIES = {"vacunos": "vacuno", "porcinos": "porcino", "ovinos": "ovino"}
COLUMNAS = {k: Columna("", f"Faena de ganado {n}") for k, n in ESPECIES.items()}
COLUMNAS["vacunos_var_ia"] = Columna("", "Faena de ganado vacuno, var. % interanual", unidad="%", tipo="variacion",
                                     base="vacunos", rezago=12)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    mapa = {k: f"{k}_cabezas" for k in ESPECIES}
    df = csvd.leer(contenido, mapa, PRIMER_PERIODO)
    df["vacunos_var_ia"] = (df["vacunos"] / df["vacunos"].shift(12) - 1) * 100
    return df[["fecha", *columnas]]


def validar(nuevo, anterior, columnas=COLUMNAS):
    errores = csvd.validar(nuevo, anterior, columnas, PRIMER_PERIODO, max_atraso_dias=150, obligatorias=("vacunos",))
    if not nuevo["vacunos"].dropna().tail(24).between(500_000, 2_000_000).all():
        errores.append("Faena vacuna fuera de rango (¿cambió la unidad?).")
    return errores
