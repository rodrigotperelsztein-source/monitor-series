"""Canasta de crianza: costo mensual de bienes y servicios y del cuidado de niños y niñas, por edad (menores de 1 año,
1 a 3, 4 a 5 y 6 a 12), pesos por mes (INDEC, API).
"""

import pandas as pd

from pipeline.fuentes import _api_indec as api
from pipeline.fuentes import _api_simple as simple
from pipeline.fuentes._indec import Columna

ID = "canasta_crianza"
NOMBRE = "Canasta de crianza de la primera infancia, la niñez y la adolescencia (INDEC)"
TABLA_API = "canasta-crianza"
URL = "https://api.indec.gob.ar/v1/" + TABLA_API
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-4-43-149"
EXTENSION = "json"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Pesos por mes"
CALENDARIO = "Valorización mensual de la canasta básica alimentaria (CBA)"

EDADES = {"men1": "menores de 1 año", "1a3": "de 1 a 3 años", "4a5": "de 4 a 5 años", "6a12": "de 6 a 12 años"}
PARTES = {"tot": "total", "bys": "bienes y servicios", "cuid": "cuidado"}
COLUMNAS = {f"{p}_{e}": Columna("", f"Canasta de crianza, {pn}, {en}") for e, en in EDADES.items() for p, pn in PARTES.items()}


def bajar(descargar, hoy):
    return simple.bajar(TABLA_API)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    f = api.filas(contenido).groupby("fecha").last().sort_index()
    df = f[list(columnas)].apply(pd.to_numeric, errors="coerce")
    df.index.name = "fecha"
    return df.reset_index()[["fecha", *columnas]]


def validar(nuevo, anterior, columnas=COLUMNAS):
    errores = simple.validar_basico(nuevo, anterior, columnas, "MS", 120)
    d = nuevo.dropna()
    for e in EDADES:
        if ((d[f"bys_{e}"] + d[f"cuid_{e}"] - d[f"tot_{e}"]).abs() > 1).any():
            errores.append(f"Bienes y servicios + cuidado no da el total ({e}).")
    return errores
