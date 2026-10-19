"""SUBE: cantidad de transacciones (usos) por día en las validadoras de la red SUBE.

Fuente: Ministerio de Economía, Secretaría de Transporte (datos.transporte.gob.ar), dataset
"SUBE - Cantidad de transacciones (usos) por fecha". Hay un CSV por año (dat-ab-usos-<año>.csv),
con una fila por día, línea y empresa. El del año en curso se actualiza casi todos los días.

Se guardan totales diarios: total, AMBA e interior, por tipo de transporte y colectivos del AMBA.
Los archivos pesan unos 50 MB por año, así que no se guarda el original y solo se baja el año en
curso (más el anterior en los primeros días de enero); la historia sale de data/sube.csv.
La primera vez, o si falta la historia, se bajan todos los años.

Los datos de los últimos meses figuran como preliminares (DATO_PRELIMINAR = SI) y se corrigen.
La cobertura del interior crece con el tiempo (ciudades que se suman a SUBE): las series del
interior y del total no son del todo comparables entre años; las del AMBA, sí.
"""

import io
import json
import re
from datetime import date
from pathlib import Path

import pandas as pd

from pipeline.fuentes._indec import Columna

ID = "sube"
NOMBRE = "SUBE: transacciones (usos) por día"
PAGINA = "https://datos.transporte.gob.ar/dataset/sube-cantidad-de-transacciones-usos-por-fecha"
URL = PAGINA
API = "https://datos.transporte.gob.ar/api/3/action/package_show?id=sube-cantidad-de-transacciones-usos-por-fecha"
EXTENSION = "csv"
FRECUENCIA = "D"
ORGANISMO = "Secretaría de Transporte"
UNIDAD = "Transacciones por día"
PRIMER_PERIODO = "2020-01-01"
CALENDARIO = ""
GUARDAR_ORIGINAL = False       # ~50 MB por año
REGISTRAR_REVISIONES = False   # los datos preliminares se corrigen todos los días

HISTORIA = Path(__file__).resolve().parents[2] / "data" / f"{ID}.csv"

COLUMNAS = {
    "total": Columna("", "SUBE, transacciones por día, total del país"),
    "amba": Columna("", "SUBE, transacciones por día, AMBA"),
    "interior": Columna("", "SUBE, transacciones por día, fuera del AMBA"),
    "colectivo": Columna("", "SUBE, transacciones por día, colectivos (todo el país)"),
    "tren": Columna("", "SUBE, transacciones por día, trenes"),
    "subte": Columna("", "SUBE, transacciones por día, subte"),
    "lanchas": Columna("", "SUBE, transacciones por día, lanchas"),
    "amba_colectivo": Columna("", "SUBE, transacciones por día, colectivos del AMBA"),
}
TIPOS = {"COLECTIVO": "colectivo", "TREN": "tren", "SUBTE": "subte", "LANCHAS": "lanchas"}


def _anios(descargar) -> dict[int, str]:
    """Año -> URL del CSV, según el catálogo del dataset."""
    r = json.loads(descargar(API, minimo=100))["result"]
    urls = {}
    for rec in r["resources"]:
        m = re.search(r"usos-(\d{4})\.csv$", rec.get("url", ""))
        if m:
            urls[int(m[1])] = rec["url"]
    if not urls:
        raise ValueError("El catálogo del dataset no tiene archivos por año.")
    return urls


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    urls = _anios(descargar)
    if HISTORIA.exists():
        anios = [a for a in urls if a == max(urls) or (hoy.month == 1 and hoy.day <= 20 and a == max(urls) - 1)]
    else:
        anios = sorted(urls)
    partes = [descargar(urls[a]) for a in sorted(anios)]
    return " ".join(urls[a] for a in sorted(anios)), b"\n".join(partes)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    d = pd.read_csv(io.BytesIO(contenido), usecols=["DIA_TRANSPORTE", "AMBA", "TIPO_TRANSPORTE", "CANTIDAD",
                                                     "DATO_PRELIMINAR"], dtype=str)
    d = d[d["DIA_TRANSPORTE"] != "DIA_TRANSPORTE"]  # encabezados de los archivos concatenados
    d["fecha"] = pd.to_datetime(d["DIA_TRANSPORTE"], format="%Y-%m-%d")
    d["CANTIDAD"] = pd.to_numeric(d["CANTIDAD"], errors="raise")
    tipos = set(d["TIPO_TRANSPORTE"].unique()) - set(TIPOS)
    if tipos:
        raise ValueError(f"Tipos de transporte nuevos: {tipos}")
    if set(d["AMBA"].unique()) - {"SI", "NO"}:
        raise ValueError(f"Valores inesperados en AMBA: {set(d['AMBA'].unique())}")

    g = d.groupby("fecha")
    out = pd.DataFrame({"total": g["CANTIDAD"].sum()})
    amba = d["AMBA"] == "SI"
    out["amba"] = d[amba].groupby("fecha")["CANTIDAD"].sum()
    out["interior"] = d[~amba].groupby("fecha")["CANTIDAD"].sum()
    for tipo, cid in TIPOS.items():
        out[cid] = d[d["TIPO_TRANSPORTE"] == tipo].groupby("fecha")["CANTIDAD"].sum()
    out["amba_colectivo"] = d[amba & (d["TIPO_TRANSPORTE"] == "COLECTIVO")].groupby("fecha")["CANTIDAD"].sum()
    out = out.fillna(0).astype("int64")
    out.attrs["preliminar_desde"] = d.loc[d["DATO_PRELIMINAR"] == "SI", "fecha"].min()
    return out.reset_index()[["fecha", *columnas]]


def combinar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None) -> pd.DataFrame:
    """Los años bajados reemplazan esos años en la historia guardada."""
    if anterior is None:
        return nuevo
    anios = set(nuevo["fecha"].dt.year)
    viejo = anterior[~anterior["fecha"].dt.year.isin(anios)]
    return pd.concat([viejo, nuevo]).sort_values("fecha").reset_index(drop=True)[list(nuevo.columns)]


def meta_extra(nuevo: pd.DataFrame) -> dict:
    p = nuevo.attrs.get("preliminar_desde")
    return {"preliminar_desde": f"{p:%Y-%m-%d}" if p is not None and not pd.isna(p) else None}


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    esperado = pd.date_range(PRIMER_PERIODO, periods=len(nuevo), freq="D")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        faltan = sorted(set(pd.date_range(PRIMER_PERIODO, nuevo["fecha"].max())) - set(nuevo["fecha"]))
        errores.append(f"Los días no son consecutivos desde {PRIMER_PERIODO}; faltan {len(faltan)}: "
                       f"{[f'{x:%Y-%m-%d}' for x in faltan[:5]]}")
    if (nuevo["total"] <= 0).any():
        errores.append("Hay días con total cero o negativo.")
    if (nuevo["amba"] + nuevo["interior"] != nuevo["total"]).any():
        errores.append("AMBA + interior no suman el total.")
    if (nuevo[list(TIPOS.values())].sum(axis=1) != nuevo["total"]).any():
        errores.append("Los tipos de transporte no suman el total.")
    if anterior is not None and len(anterior):
        if nuevo["fecha"].max() < anterior["fecha"].max():
            errores.append("El último día es anterior al de la versión guardada.")
        comunes = nuevo.merge(anterior, on="fecha", suffixes=("", "_ant"))
        dif = (comunes["total"] / comunes["total_ant"] - 1).abs()
        # Los días preliminares se corrigen, pero no tanto.
        if (dif > 0.3).any():
            errores.append(f"El total de {int((dif > 0.3).sum())} días cambió más de 30% respecto de la versión guardada.")
    return errores
