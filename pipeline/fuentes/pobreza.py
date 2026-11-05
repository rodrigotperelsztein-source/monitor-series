"""Pobreza e indigencia en los 31 aglomerados urbanos de la EPH: % de hogares y de personas, por semestre (INDEC, API).
La fecha es el primer mes del semestre (enero o julio).
"""

import pandas as pd

from pipeline.fuentes import _api_indec as api
from pipeline.fuentes import _api_simple as simple
from pipeline.fuentes._indec import Columna

ID = "pobreza"
NOMBRE = "Pobreza e indigencia, 31 aglomerados urbanos (INDEC, EPH)"
TABLA_API = "pobreza_eph"
URL = "https://api.indec.gob.ar/v1/" + TABLA_API
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-4-46-152"
EXTENSION = "json"
FRECUENCIA = "S"
ORGANISMO = "INDEC"
UNIDAD = "%"
CALENDARIO = "Incidencia de la pobreza y la indigencia"
AREA = "T_31_A"

CAMPOS = {"pobreza_personas": "tasa_pobreza_personas", "pobreza_hogares": "tasa_pobreza_hogares",
          "indigencia_personas": "tasa_indigencia_personas", "indigencia_hogares": "tasa_indigencia_hogares"}
NOMBRES = {"pobreza_personas": "Pobreza, % de personas", "pobreza_hogares": "Pobreza, % de hogares",
           "indigencia_personas": "Indigencia, % de personas", "indigencia_hogares": "Indigencia, % de hogares"}
COLUMNAS = {k: Columna("", n) for k, n in NOMBRES.items()}


def bajar(descargar, hoy):
    return simple.bajar(TABLA_API)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    import json
    d = pd.DataFrame(json.loads(contenido[len(api.MARCA):].decode("utf-8"))["filas"])
    d = d[d["area_geografica_nom"] == AREA]
    d["fecha"] = pd.to_datetime([f"{a}-{1 if s == 1 else 7:02d}-01" for a, s in zip(d["anio"], d["semestre"])])
    out = d.groupby("fecha").last().sort_index().rename(columns={v: k for k, v in CAMPOS.items()})
    out.index.name = "fecha"
    return out.reset_index()[["fecha", *columnas]].astype({c: float for c in columnas})


def validar(nuevo, anterior, columnas=COLUMNAS):
    errores = simple.validar_basico(nuevo, anterior, columnas, "6MS", 500)
    if not nuevo[list(columnas)].stack().between(0, 100).all():
        errores.append("Tasas fuera de 0-100.")
    return errores
