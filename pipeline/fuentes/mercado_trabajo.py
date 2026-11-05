"""Mercado de trabajo, 31 aglomerados urbanos de la EPH: tasas de actividad, empleo, desocupación, subocupación y
empleo informal, por trimestre, % (INDEC, API).
"""

import json

import pandas as pd

from pipeline.fuentes import _api_indec as api
from pipeline.fuentes import _api_simple as simple
from pipeline.fuentes._indec import Columna

ID = "mercado_trabajo"
NOMBRE = "Mercado de trabajo: actividad, empleo y desocupación, 31 aglomerados (INDEC, EPH)"
TABLA_API = "mercado_trabajo_eph"
URL = "https://api.indec.gob.ar/v1/" + TABLA_API
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-4-31-58"
EXTENSION = "json"
FRECUENCIA = "Q"
ORGANISMO = "INDEC"
UNIDAD = "%"
CALENDARIO = "Mercado de trabajo. Tasas e indicadores socioeconómicos (EPH)"
AREA = "T_31_A"

NOMBRES = {"actividad": "Tasa de actividad", "empleo": "Tasa de empleo", "desocupacion": "Tasa de desocupación",
           "subocupacion": "Tasa de subocupación", "subocupacion_demandante": "Tasa de subocupación demandante",
           "ocupacion_demandante": "Tasa de ocupados demandantes", "empleo_informal": "Tasa de empleo informal (asalariados sin descuento jubilatorio y otros)",
           "empleo_formal": "Tasa de empleo formal"}
CAMPOS = {"actividad": "tasa_de_actividad", "empleo": "tasa_de_empleo", "desocupacion": "tasa_de_desocupacion",
          "subocupacion": "tasa_de_subocupacion", "subocupacion_demandante": "tasa_de_subocupacion_demandante",
          "ocupacion_demandante": "tasa_de_ocupacion_demandante", "empleo_informal": "tasa_de_empleo_informal",
          "empleo_formal": "tasa_de_empleo_formal"}
COLUMNAS = {k: Columna("", n) for k, n in NOMBRES.items()}


def bajar(descargar, hoy):
    return simple.bajar(TABLA_API)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    d = pd.DataFrame(json.loads(contenido[len(api.MARCA):].decode("utf-8"))["filas"])
    d = d[d["area_geografica_nom"] == AREA]
    d["fecha"] = pd.to_datetime([f"{a}-{(t - 1) * 3 + 1:02d}-01" for a, t in zip(d["anio"], d["trimestre"])])
    out = d.groupby("fecha").last().sort_index().rename(columns={v: k for k, v in CAMPOS.items()})
    out = out.reindex(pd.date_range(out.index.min(), out.index.max(), freq="QS"))
    out.index.name = "fecha"
    return out.reset_index()[["fecha", *columnas]].astype({c: float for c in columnas})


def validar(nuevo, anterior, columnas=COLUMNAS):
    errores = simple.validar_basico(nuevo, anterior, columnas, "QS", 300)
    if nuevo["desocupacion"].tail(4).isna().any():
        errores.append("Falta la desocupación del último año.")
    return errores
