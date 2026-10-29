"""Acciones de empresas de energía que operan en la Argentina: cotización de cierre diaria en Nueva York (dólares).

Empresas (ADR que cotizan en la Bolsa de Nueva York):
  - YPF (YPF), Vista Energy (VIST), Pampa Energía (PAM) y Transportadora de Gas del Sur (TGS).

Fuente: historial de precios de Nasdaq (api.nasdaq.com, el mismo que muestra nasdaq.com en "Historical Quotes"),
de los últimos 10 años (Vista cotiza desde julio de 2019); los días que ya se guardaron se conservan aunque la fuente
los deje de devolver. Es el precio de cierre sin ajustar por dividendos. Se baja en la corrida
completa de cada noche, después del cierre del mercado de Nueva York.

Solo cotizaciones públicas de mercado: no hay datos de ninguna empresa más allá de lo que publica la bolsa.
"""

import io
import json
import zipfile
from datetime import date

import pandas as pd

from pipeline.fuentes._indec import Columna

ID = "acciones_energia"
NOMBRE = "Acciones de energía en Nueva York: YPF, Vista, Pampa y TGS (cierre diario, dólares)"
PAGINA = "https://www.nasdaq.com/market-activity/stocks/ypf/historical"
API = "https://api.nasdaq.com/api/quote/{}/historical?assetclass=stocks&fromdate={}&todate={}&limit=9999"
URL = API.format("YPF", "2016-01-01", "hoy")
EXTENSION = "zip"
FRECUENCIA = "D"
ORGANISMO = "Bolsa de Nueva York, vía Nasdaq"
UNIDAD = "Dólares por acción (ADR)"
PRIMER_PERIODO = "2016-10-28"
CALENDARIO = ""
GUARDAR_ORIGINAL = False

EMPRESAS = {"ypf": ("YPF", "YPF"), "vista": ("VIST", "Vista Energy"), "pampa": ("PAM", "Pampa Energía"),
            "tgs": ("TGS", "Transportadora de Gas del Sur")}
COLUMNAS = {cid: Columna("", f"{nombre} ({tk}, Nueva York), precio de cierre en dólares")
            for cid, (tk, nombre) in EMPRESAS.items()}


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    buf = io.BytesIO()
    urls = []
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for cid, (tk, _) in EMPRESAS.items():
            url = API.format(tk, "2016-01-01", f"{hoy:%Y-%m-%d}")
            urls.append(url)
            z.writestr(f"{cid}.json", descargar(url, minimo=10_000))
    return " ".join(urls), buf.getvalue()


def _serie(contenido: bytes, tk: str) -> pd.Series:
    j = json.loads(contenido)
    datos = j.get("data") or {}
    if datos.get("symbol", "").upper() != tk:
        raise ValueError(f"La respuesta no es de {tk} (dice {datos.get('symbol')!r}).")
    filas = datos["tradesTable"]["rows"]
    fecha = pd.to_datetime([f["date"] for f in filas], format="%m/%d/%Y")
    cierre = pd.to_numeric([str(f["close"]).replace("$", "").replace(",", "") for f in filas], errors="coerce")
    return pd.Series(cierre, index=fecha).dropna().sort_index()


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        out = pd.DataFrame({cid: _serie(z.read(f"{cid}.json"), tk) for cid, (tk, _) in EMPRESAS.items()})
    out = out[out.index >= PRIMER_PERIODO].sort_index()
    out.index.name = "fecha"
    return out.reset_index()[["fecha", *columnas]]


def combinar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None) -> pd.DataFrame:
    """Si la fuente acorta el historial que devuelve, se conservan los días viejos ya guardados."""
    if anterior is None or not len(anterior):
        return nuevo
    viejos = anterior[anterior["fecha"] < nuevo["fecha"].min()]
    return pd.concat([viejos, nuevo]).sort_values("fecha").reset_index(drop=True)[list(nuevo.columns)]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    if not nuevo["fecha"].is_monotonic_increasing or nuevo["fecha"].duplicated().any():
        errores.append("Las fechas no están ordenadas o hay repetidas.")
    for c in columnas:
        s = nuevo[c].dropna()
        if len(s) < 250:
            errores.append(f"{c}: muy pocos días ({len(s)}).")
        elif not s.between(0.1, 2000).all():
            errores.append(f"{c}: precios fuera de rango.")
        if len(s) and (pd.Timestamp.today() - nuevo.loc[s.index[-1], "fecha"]).days > 10:
            errores.append(f"{c}: el último cierre tiene más de 10 días.")
    if anterior is not None and len(anterior):
        comunes = nuevo.merge(anterior, on="fecha", suffixes=("", "_ant"))
        for c in columnas:
            d = (comunes[c] / comunes[f"{c}_ant"] - 1).abs()
            if (d > 0.02).sum() > 5:
                errores.append(f"{c}: cambiaron más de 5 cierres ya guardados (¿ajuste por dividendos o split?).")
    return errores
