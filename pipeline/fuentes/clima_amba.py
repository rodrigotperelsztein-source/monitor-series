"""Temperatura y lluvia diarias de CABA y el AMBA desde noviembre de 2024 (reanálisis ERA5 vía Open-Meteo).

Ver pipeline/fuentes/_clima.py: cómo se definen las áreas y por qué no son datos de estaciones. La corrida diaria pide
los últimos 60 días (ERA5 corrige los más recientes) y conserva el resto; la primera corrida baja todo desde el inicio.
"""

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from pipeline.fuentes import _clima
from pipeline.fuentes._indec import Columna

ID = "clima_amba"
NOMBRE = "Temperatura y lluvia diarias de CABA y el AMBA (reanálisis ERA5, Open-Meteo)"
API = ("https://archive-api.open-meteo.com/v1/archive?{coords}&start_date={desde}&end_date={hasta}"
       "&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum&timezone={tz}&models=era5_seamless")
URL = "https://archive-api.open-meteo.com/v1/archive"
PAGINA = "https://open-meteo.com/en/docs/historical-weather-api"
EXTENSION = "json"
FRECUENCIA = "D"
ORGANISMO = "Copernicus/ECMWF (ERA5 y ERA5-Land) vía Open-Meteo, CC BY 4.0"
UNIDAD = "°C y mm"
PRIMER_PERIODO = "2024-11-01"
CALENDARIO = ""
GUARDAR_ORIGINAL = False
GUARDADO = Path(__file__).resolve().parents[2] / "data" / f"{ID}.csv"

VARIABLES = {"tmax": "temperature_2m_max", "tmin": "temperature_2m_min", "tmed": "temperature_2m_mean",
             "lluvia": "precipitation_sum"}
NOMBRES = {"tmax": ("Temperatura máxima", "°C"), "tmin": ("Temperatura mínima", "°C"), "tmed": ("Temperatura media", "°C"),
           "lluvia": ("Lluvia acumulada en el día", "mm")}
COLUMNAS = {f"{a}_{k}": Columna("", f"{n} ({A})", unidad=u)
            for a, A in _clima.AREAS.items() for k, (n, u) in NOMBRES.items()}


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    completo = GUARDADO.exists() and set(COLUMNAS) <= set(GUARDADO.read_text(encoding="utf-8").split("\n", 1)[0].split(","))
    # Sin archivo guardado, o si se agregó un área, se baja todo desde el inicio.
    desde = f"{hoy - timedelta(days=60):%Y-%m-%d}" if completo else PRIMER_PERIODO
    url = API.format(coords=_clima.coordenadas(), desde=desde, hasta=f"{hoy - timedelta(days=1):%Y-%m-%d}", tz=_clima.TZ)
    return URL, descargar(url, minimo=2_000)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    df = _clima.promediar(contenido, VARIABLES)
    # ERA5 llega con unos cinco días de demora: los días sin dato todavía vienen vacíos.
    df = df.dropna(subset=["caba_tmed", "amba_tmed"])
    return df.reset_index()[["fecha", *columnas]]


def combinar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None) -> pd.DataFrame:
    if anterior is None or not len(anterior):
        return nuevo
    viejos = anterior[anterior["fecha"] < nuevo["fecha"].min()]
    return pd.concat([viejos, nuevo], ignore_index=True)[list(nuevo.columns)]


def validar(nuevo, anterior, columnas=COLUMNAS):
    errores = []
    esperado = pd.date_range(PRIMER_PERIODO, periods=len(nuevo), freq="D")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los días no son consecutivos desde el inicio.")
    if (pd.Timestamp.today() - nuevo["fecha"].max()).days > 12:
        errores.append("El último día tiene más de 12 días.")
    t = nuevo[[c for c in columnas if "_t" in c]]
    if not t.stack().between(-15, 48).all():
        errores.append("Temperaturas fuera de rango.")
    if not nuevo[[c for c in columnas if c.endswith("_lluvia")]].stack().between(0, 400).all():
        errores.append("Lluvia fuera de rango.")
    return errores
