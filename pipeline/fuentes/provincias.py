"""Ejecución presupuestaria de las provincias: administración pública no financiera, base devengado, consolidado de las
24 jurisdicciones y cada provincia, millones de pesos corrientes por año (Ministerio de Economía, Dirección Nacional de
Asuntos Provinciales).

El archivo (serie_aif-apnf-<año>.xlsx) se toma del enlace de la página de ejecuciones; trae una hoja por jurisdicción con
la serie anual desde 2005. El último año puede ser provisorio.
"""

import io
import re
import unicodedata
import zipfile
from datetime import date

import pandas as pd

from pipeline.fuentes._indec import Columna, norm

ID = "provincias"
NOMBRE = "Ejecución presupuestaria de las provincias: ingresos, gastos y resultado (DNAP)"
PAGINA = ("https://www.argentina.gob.ar/economia/sechacienda/coordinacion-fiscal-provincial/"
          "ejecucion-presupuestaria-provincial/ejecuciones")
URL = PAGINA
EXTENSION = "zip"
FRECUENCIA = "A"
ORGANISMO = "Ministerio de Economía (Dirección Nacional de Asuntos Provinciales)"
UNIDAD = "Millones de $"
PRIMER_PERIODO = "2005-01-01"
CALENDARIO = ""
ENLACE = re.compile(r'href="(https://www\.argentina\.gob\.ar/sites/default/files/[\w/-]*serie_aif-apnf-\d{4}[\w-]*\.xlsx)"')

FILAS = {  # id -> (comienzo del rótulo, nombre)
    "ingresos_totales": ("VI. INGRESOS TOTALES", "Ingresos totales"),
    "tributarios_provinciales": ("- DE ORIGEN PROVINCIAL", "Recursos tributarios de origen provincial"),
    "tributarios_nacionales": ("- DE ORIGEN NACIONAL", "Recursos tributarios de origen nacional (coparticipación y otros)"),
    "regalias": ("- REGALIAS", "Regalías"),
    "gastos_totales": ("VII. GASTOS TOTALES", "Gastos totales"),
    "personal": ("- PERSONAL", "Gasto en personal"),
    "inversion_real": (". INVERSION REAL DIRECTA", "Inversión real directa"),
    "resultado_primario": ("IX. RESULTADO PRIMARIO", "Resultado primario"),
    "resultado_financiero": ("VIII. RESULTADO FINANCIERO", "Resultado financiero"),
}
POR_PROVINCIA = ("ingresos_totales", "regalias", "resultado_primario", "resultado_financiero")


def slug(nombre: str) -> str:
    s = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


HOJAS = ["Ciudad", "Buenos Aires", "Catamarca", "Córdoba", "Corrientes", "Chaco", "Chubut", "Entre Ríos", "Formosa", "Jujuy",
         "La Pampa", "La Rioja", "Mendoza", "Misiones", "Neuquén", "Río Negro", "Salta", "San Juan", "San Luis", "Santa Cruz",
         "Santa Fe", "Santiago del Estero", "Tucumán", "Tierra del Fuego"]
NOMBRE_HOJA = {"Ciudad": "Ciudad de Buenos Aires"}
COLUMNAS = {k: Columna("", f"24 jurisdicciones: {n.lower()}") for k, (_, n) in FILAS.items()}
for _h in HOJAS:
    for _k in POR_PROVINCIA:
        COLUMNAS[f"{slug(NOMBRE_HOJA.get(_h, _h))}_{_k}"] = Columna("", f"{NOMBRE_HOJA.get(_h, _h)}: {FILAS[_k][1].lower()}")


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    pagina = descargar(PAGINA, minimo=5_000).decode("utf-8", "replace")
    enlaces = sorted(set(ENLACE.findall(pagina)), key=lambda u: re.search(r"apnf-(\d{4})", u)[1], reverse=True)
    if not enlaces:
        raise ValueError("No encontré el enlace a la serie de ejecución presupuestaria provincial.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("serie.xlsx", descargar(enlaces[0], minimo=50_000))
    return enlaces[0], buf.getvalue()


def _hoja(df: pd.DataFrame, claves) -> dict[str, pd.Series]:
    enc = next(i for i in range(min(20, len(df))) if norm(df.iloc[i, 0]).startswith("CONCEPTO"))
    anios = {j: int(float(v)) for j, v in enumerate(df.iloc[enc]) if j and pd.notna(v) and re.fullmatch(r"(19|20)\d\d(\.0)?", str(v))}
    rot = [re.sub(r"\s+", " ", norm(v)).strip() if pd.notna(v) else "" for v in df.iloc[:, 0]]
    out = {}
    for k in claves:
        pref = re.sub(r"\s+", " ", norm(FILAS[k][0]))
        i = next((i for i, r in enumerate(rot) if i > enc and r.startswith(pref)), None)
        if i is None:
            raise ValueError(f"No encontré la fila '{FILAS[k][0]}'.")
        out[k] = pd.to_numeric(pd.Series({pd.Timestamp(year=a, month=1, day=1): df.iloc[i, j] for j, a in anios.items()}),
                               errors="coerce")
    return out


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        libro = pd.read_excel(io.BytesIO(z.read("serie.xlsx")), sheet_name=None, header=None)
    hojas = {re.sub(r"\s+", " ", h).strip(): df for h, df in libro.items()}
    s = _hoja(hojas["Consolidado"], FILAS)
    for h in HOJAS:
        if h not in hojas:
            raise ValueError(f"Falta la hoja de {h}.")
        for k, v in _hoja(hojas[h], POR_PROVINCIA).items():
            s[f"{slug(NOMBRE_HOJA.get(h, h))}_{k}"] = v
    df = pd.DataFrame(s).sort_index()
    df.index.name = "fecha"
    return df.reset_index()[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)[:8]}"]
    esperado = pd.date_range(PRIMER_PERIODO, periods=len(nuevo), freq="YS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los años no son consecutivos desde 2005.")
    d = nuevo
    if ((d["ingresos_totales"] - d["gastos_totales"] - d["resultado_financiero"]).abs() > 1).any():
        errores.append("Ingresos menos gastos no da el resultado financiero.")
    suma = sum(d[f"{slug(NOMBRE_HOJA.get(h, h))}_resultado_financiero"] for h in HOJAS)
    if ((suma - d["resultado_financiero"]).abs() > d["ingresos_totales"].abs() * 0.001 + 1).any():
        errores.append("Las provincias no suman el consolidado.")
    if anterior is not None and len(anterior) and len(nuevo) < len(anterior):
        errores.append("Se perdieron años.")
    return errores
