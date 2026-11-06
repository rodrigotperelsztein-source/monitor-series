"""Patentamientos (inscripciones iniciales en el Registro de la Propiedad Automotor) de automotores y de motovehículos,
total del país y por provincia, unidades por mes (DNRPA, Ministerio de Justicia, datos abiertos).

El nombre del CSV cambia cada mes (lleva el último período): se toma de la API del portal datos.jus.gob.ar (CKAN). No
distingue tipo de motor ni de combustible.
"""

import io
import json
import re
import unicodedata
import zipfile
from datetime import date

import pandas as pd

from pipeline.fuentes._indec import Columna

ID = "patentamientos"
NOMBRE = "Patentamientos de automotores y motos, total y por provincia (DNRPA)"
PAQUETES = {"autos": "estadistica-de-tramites-de-automotores", "motos": "estadistica-de-tramites-de-motovehiculos"}
API = "https://datos.jus.gob.ar/api/3/action/package_show?id={}"
URL = "https://datos.jus.gob.ar/dataset/estadistica-de-tramites-de-automotores"
PAGINA = URL
EXTENSION = "zip"
FRECUENCIA = "M"
ORGANISMO = "DNRPA (Ministerio de Justicia)"
UNIDAD = "Unidades"
PRIMER_PERIODO = "2000-01-01"
CALENDARIO = ""
GUARDAR_ORIGINAL = False

PROVINCIAS = ["Buenos Aires", "Catamarca", "Chaco", "Chubut", "Ciudad Autónoma de Bs.As.", "Córdoba", "Corrientes",
              "Entre Ríos", "Formosa", "Jujuy", "La Pampa", "La Rioja", "Mendoza", "Misiones", "Neuquén", "Río Negro", "Salta",
              "San Juan", "San Luis", "Santa Cruz", "Santa Fe", "Santiago del Estero", "Tierra del Fuego", "Tucumán"]


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = {"ciudad autonoma de bs.as.": "caba"}.get(s, s)
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


COLUMNAS = {"autos": Columna("", "Patentamientos de automotores, total del país"),
            "autos_var_ia": Columna("", "Patentamientos de automotores, var. % interanual", unidad="%", tipo="variacion",
                                    base="autos", rezago=12),
            "motos": Columna("", "Patentamientos de motos, total del país"),
            "motos_var_ia": Columna("", "Patentamientos de motos, var. % interanual", unidad="%", tipo="variacion",
                                    base="motos", rezago=12)}
for _t, _n in (("autos", "automotores"), ("motos", "motos")):
    for _p in PROVINCIAS:
        COLUMNAS[f"{_t}_{slug(_p)}"] = Columna("", f"Patentamientos de {_n}: {_p.replace('Ciudad Autónoma de Bs.As.', 'CABA')}")


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    buf, urls = io.BytesIO(), []
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for t, paquete in PAQUETES.items():
            meta = json.loads(descargar(API.format(paquete), minimo=500))
            recursos = [r["url"] for r in meta["result"]["resources"]
                        if "inscripciones-iniciales" in r["url"] and r["url"].endswith(".csv")
                        and r["url"].startswith("https://datos.jus.gob.ar/")]
            if not recursos:
                raise ValueError(f"No encontré el CSV de inscripciones iniciales de {t}.")
            urls.append(recursos[0])
            z.writestr(f"{t}.csv", descargar(recursos[0], minimo=50_000))
    return " ".join(urls), buf.getvalue()


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    partes = []
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        for t in PAQUETES:
            d = pd.read_csv(z.open(f"{t}.csv"), encoding="utf-8-sig")
            d["fecha"] = pd.to_datetime(dict(year=d["anio_inscripcion_inicial"], month=d["mes_inscripcion_inicial"], day=1))
            d["col"] = t + "_" + d["provincia_inscripcion_inicial"].map(slug)
            tabla = d.pivot_table(index="fecha", columns="col", values="cantidad_inscripciones_iniciales", aggfunc="sum")
            tabla[t] = tabla.sum(axis=1)
            partes.append(tabla)
    df = pd.concat(partes, axis=1).sort_index()
    df = df.reindex(pd.date_range(df.index.min(), df.index.max(), freq="MS"))
    for t in PAQUETES:
        df[f"{t}_var_ia"] = (df[t] / df[t].shift(12) - 1) * 100
    faltan = [c for c in columnas if c not in df]
    if faltan:
        raise ValueError(f"Provincias que no aparecen en el CSV: {faltan[:5]}")
    df.index.name = "fecha"
    return df.reset_index()[["fecha", *columnas]]


def validar(nuevo, anterior, columnas=COLUMNAS):
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)[:8]}"]
    if nuevo["autos"].isna().any():
        errores.append("Hay meses sin patentamientos de automotores.")
    if nuevo.loc[nuevo["fecha"] >= "2007-01-01", "motos"].isna().any():
        errores.append("Hay meses sin patentamientos de motos desde 2007.")
    if (pd.Timestamp.today() - nuevo["fecha"].max()).days > 75:
        errores.append("El último mes tiene más de dos meses.")
    if anterior is not None and len(anterior) and len(nuevo) < len(anterior):
        errores.append("Se perdieron meses.")
    return errores
