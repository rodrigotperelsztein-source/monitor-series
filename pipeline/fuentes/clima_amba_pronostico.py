"""Pronóstico diario de temperatura y lluvia para CABA y el AMBA, próximos 16 días (Open-Meteo). Se reemplaza en cada
corrida: la fecha es el día pronosticado. Más allá de una semana, el pronóstico es poco confiable.

Ver pipeline/fuentes/_clima.py: cómo se definen las áreas.
"""

from datetime import date

import pandas as pd

from pipeline.fuentes import _clima
from pipeline.fuentes._indec import Columna

ID = "clima_amba_pronostico"
NOMBRE = "Pronóstico de temperatura y lluvia para CABA y el AMBA, próximos 16 días (Open-Meteo)"
API = ("https://api.open-meteo.com/v1/forecast?{coords}&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
       "precipitation_sum,precipitation_probability_max&timezone={tz}&forecast_days=16")
URL = "https://api.open-meteo.com/v1/forecast"
PAGINA = "https://open-meteo.com/en/docs"
EXTENSION = "json"
FRECUENCIA = "D"
ORGANISMO = "Modelos meteorológicos (GFS, ECMWF y otros) vía Open-Meteo, CC BY 4.0"
UNIDAD = "°C, mm y %"
CALENDARIO = ""
GUARDAR_ORIGINAL = False

VARIABLES = {"tmax": "temperature_2m_max", "tmin": "temperature_2m_min", "tmed": "temperature_2m_mean",
             "lluvia": "precipitation_sum", "prob_lluvia": "precipitation_probability_max"}
NOMBRES = {"tmax": ("Temperatura máxima pronosticada", "°C"), "tmin": ("Temperatura mínima pronosticada", "°C"),
           "tmed": ("Temperatura media pronosticada", "°C"), "lluvia": ("Lluvia pronosticada en el día", "mm"),
           "prob_lluvia": ("Probabilidad máxima de lluvia en el día", "%")}
COLUMNAS = {f"{a}_{k}": Columna("", f"{n} ({A})", unidad=u)
            for a, A in (("caba", "CABA"), ("amba", "AMBA, promedio de los partidos")) for k, (n, u) in NOMBRES.items()}


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    return URL, descargar(API.format(coords=_clima.coordenadas(), tz=_clima.TZ), minimo=2_000)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    return _clima.promediar(contenido, VARIABLES).reset_index()[["fecha", *columnas]]


def validar(nuevo, anterior, columnas=COLUMNAS):
    errores = []
    if len(nuevo) < 7:
        errores.append("El pronóstico trae menos de siete días.")
    if nuevo["fecha"].min() > pd.Timestamp.today().normalize() + pd.Timedelta(days=1):
        errores.append("El pronóstico no empieza hoy.")
    if nuevo[["caba_tmed", "amba_tmed"]].head(7).isna().any().any():
        errores.append("Faltan temperaturas en la primera semana.")
    return errores
