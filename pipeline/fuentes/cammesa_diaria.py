"""CAMMESA: demanda eléctrica diaria del sistema (SADI), desde los datos cada 5 minutos.

Fuente: API pública de CAMMESA (api.cammesa.com, servicio demanda-svc), región 1002 = total
del sistema. Trae la demanda en MW cada 5 minutos y la temperatura cada 15.

La API guarda solo los últimos meses (hoy, desde marzo de 2026 aproximadamente), así que la serie
empieza ahí y se va acumulando en data/cammesa_diaria.csv. Cada noche se bajan los últimos días
(CAMMESA a veces completa o corrige datos del día anterior); el día en curso no se incluye.

Por día:
  - energia: energía demandada en GWh (promedio de la potencia × 24 h);
  - potencia_maxima / potencia_minima: en MW;
  - temperatura_media: °C (la que informa CAMMESA junto con la demanda);
  - mediciones: cuántas mediciones de 5 minutos hubo (288 en un día completo).
"""

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from pipeline.fuentes._indec import Columna

ID = "cammesa_diaria"
NOMBRE = "CAMMESA: demanda eléctrica diaria del sistema"
API = "https://api.cammesa.com/demanda-svc/demanda/ObtieneDemandaYTemperaturaRegionByFecha?id_region=1002&fecha={}"
URL = API.format("AAAA-MM-DD")
PAGINA = "https://cammesaweb.cammesa.com/demanda-diaria/"
EXTENSION = "json"
FRECUENCIA = "D"
ORGANISMO = "CAMMESA"
UNIDAD = "GWh por día"
PRIMER_PERIODO = None  # el primer día que tenga la API
CALENDARIO = ""
GUARDAR_ORIGINAL = False
REGISTRAR_REVISIONES = False
DIAS_REPASO = 7          # días recientes que se vuelven a bajar cada noche
MAX_HISTORIA = 400       # la primera vez, hasta cuántos días atrás se busca

HISTORIA = Path(__file__).resolve().parents[2] / "data" / f"{ID}.csv"

COLUMNAS = {
    "energia": Columna("", "Demanda de energía eléctrica del día (SADI)"),
    "potencia_maxima": Columna("", "Potencia máxima demandada en el día (SADI)", unidad="MW"),
    "potencia_minima": Columna("", "Potencia mínima demandada en el día (SADI)", unidad="MW"),
    "temperatura_media": Columna("", "Temperatura media del día informada por CAMMESA", unidad="°C"),
    "mediciones": Columna("", "Mediciones de 5 minutos en el día (288 = completo)", unidad="cantidad"),
}


def _dia(descargar, d: date) -> list[dict]:
    datos = json.loads(descargar(API.format(d.isoformat()), minimo=2))
    return [x for x in datos if str(x.get("fecha", "")).startswith(d.isoformat())]


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    ayer = hoy - timedelta(days=1)
    dias = {}
    if HISTORIA.exists():
        ultimo = pd.read_csv(HISTORIA, parse_dates=["fecha"])["fecha"].max().date()
        d = min(ultimo, ayer) - timedelta(days=DIAS_REPASO - 1)
        while d <= ayer:
            dias[d.isoformat()] = _dia(descargar, d)
            d += timedelta(days=1)
    else:
        # Hacia atrás desde ayer hasta el primer día sin datos.
        d, vacios = ayer, 0
        while (ayer - d).days < MAX_HISTORIA and vacios < 3:
            puntos = _dia(descargar, d)
            vacios = 0 if puntos else vacios + 1
            if puntos:
                dias[d.isoformat()] = puntos
            d -= timedelta(days=1)
    return URL, json.dumps(dias, sort_keys=True).encode()


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    dias = json.loads(contenido)
    filas = []
    for dia, puntos in sorted(dias.items()):
        if not puntos:
            continue
        p = pd.DataFrame(puntos)
        dem = pd.to_numeric(p["dem"], errors="coerce").dropna()
        temp = pd.to_numeric(p["temp"], errors="coerce").dropna() if "temp" in p else pd.Series(dtype=float)
        filas.append({
            "fecha": pd.Timestamp(dia),
            "energia": dem.mean() * 24 / 1000,
            "potencia_maxima": dem.max(),
            "potencia_minima": dem.min(),
            "temperatura_media": temp.mean() if len(temp) else None,
            "mediciones": len(dem),
        })
    if not filas:
        raise ValueError("La API no devolvió datos.")
    return pd.DataFrame(filas)[["fecha", *columnas]]


def combinar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None) -> pd.DataFrame:
    if anterior is not None:
        viejo = anterior[~anterior["fecha"].isin(nuevo["fecha"])]
        nuevo = pd.concat([viejo, nuevo])
    return nuevo.sort_values("fecha").reset_index(drop=True)


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    faltan = sorted(set(pd.date_range(nuevo["fecha"].min(), nuevo["fecha"].max())) - set(nuevo["fecha"]))
    if faltan:
        print(f"  aviso: faltan {len(faltan)} días: {[f'{x:%Y-%m-%d}' for x in faltan[:10]]}")
    if not nuevo["energia"].between(150, 900).all():
        errores.append("Energía diaria fuera de rango (150 a 900 GWh): ¿cambió la unidad?")
    incompletos = nuevo[nuevo["mediciones"] < 250]
    if len(incompletos):
        print(f"  aviso: días con menos de 250 mediciones: {[f'{x:%Y-%m-%d}' for x in incompletos['fecha'][-5:]]}")
    if anterior is not None and len(anterior) and nuevo["fecha"].min() > anterior["fecha"].min():
        errores.append("Se perdió historia guardada.")
    return errores
