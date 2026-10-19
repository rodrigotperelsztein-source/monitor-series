"""RIPTE: Remuneración Imponible Promedio de los Trabajadores Estables.

Fuente: Subsecretaría de Seguridad Social (Ministerio de Capital Humano).
Cada mes se publica un PDF con la serie completa desde julio de 1994 (monto en pesos, variación
mensual, índice base 07/1994=100 e índice no decreciente). El nombre del PDF cambia con cada
publicación (p. ej. ripte_agosto_2026-mdch.pdf), así que se lo busca en la página.

La serie de datos.gob.ar no se usa: tiene meses vacíos y valores repetidos por error.
"""

import io
import re
import unicodedata
from datetime import date
from urllib.parse import urljoin

import pandas as pd

from pipeline.fuentes._indec import Columna, validar_tabla

ID = "ripte"
NOMBRE = "RIPTE: remuneración imponible promedio de los trabajadores estables"
PAGINA = "https://www.argentina.gob.ar/trabajo/seguridadsocial/ripte"
URL = PAGINA
EXTENSION = "pdf"
FRECUENCIA = "M"
ORGANISMO = "Subsecretaría de Seguridad Social"
UNIDAD = "Pesos corrientes"
PRIMER_PERIODO = "1994-07-01"
# No figura en el calendario de INDEC: se revisa en el control de cada noche.
CALENDARIO = ""

BASE_JULIO_1994 = 874.87
INDICE = "Índice base 07/1994=100"
COLUMNAS = {
    "ripte": Columna("", "RIPTE, monto en pesos corrientes", unidad=UNIDAD),
    "ripte_var_m": Columna("", "RIPTE, var. % mensual", tipo="variacion", base="ripte", rezago=1),
    "indice": Columna("", "RIPTE, índice base 07/1994=100", unidad=INDICE),
    "indice_no_decreciente": Columna("", "RIPTE, índice no decreciente base 07/1994=100 (Res. ex MTEySS 467/2021, riesgos del trabajo)",
                                     unidad=INDICE),
}

MESES = {m: i for i, m in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                                      "septiembre", "octubre", "noviembre", "diciembre"], 1)}
NUM = r"-?[\d.]+,\d+"
# La variación puede venir como "-" (primer mes) o con un espacio después del signo ("- 2,3%").
FILA = re.compile(rf"^([a-z]+)\s+\$\s*({NUM})\s+(-|-?\s?[\d.]+,\d+%)\s+({NUM})\s+({NUM})$")


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    """Busca en la página el PDF de la última publicación y lo baja."""
    html = descargar(PAGINA).decode("utf-8", "replace")
    links = re.findall(r"(/sites/default/files/[^\"'\s<>#]*ripte[^\"'\s<>#]*\.pdf)", html, re.I)
    if not links:
        raise ValueError("No encontré el PDF del RIPTE en la página.")
    url = urljoin(PAGINA, links[0])
    return url, descargar(url)


def _numero(s: str) -> float:
    return float(s.replace("%", "").replace(" ", "").replace(".", "").replace(",", "."))


def _sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    import pdfplumber

    filas, anio = [], None
    with pdfplumber.open(io.BytesIO(contenido)) as pdf:
        for pagina in pdf.pages:
            for linea in (pagina.extract_text() or "").splitlines():
                linea = _sin_tildes(linea.strip()).lower()
                if re.fullmatch(r"(19|20)\d\d", linea):
                    anio = int(linea)
                    continue
                m = FILA.match(linea)
                if m and anio and m[1] in MESES:
                    filas.append({
                        "fecha": pd.Timestamp(anio, MESES[m[1]], 1),
                        "ripte": _numero(m[2]),
                        "ripte_var_m": None if m[3] == "-" else _numero(m[3]),
                        "indice": _numero(m[4]),
                        "indice_no_decreciente": _numero(m[5]),
                    })
    if not filas:
        raise ValueError("No encontré filas de datos en el PDF.")
    return pd.DataFrame(filas)[["fecha", *columnas]].reset_index(drop=True)


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    # Variación publicada con un decimal; montos nominales que crecen con la inflación.
    errores = validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, {"ripte", "indice", "indice_no_decreciente"},
                            rango_nivel=(0, 1e12), max_variacion=100, tol_variacion=0.06)
    # El índice tiene que ser el monto relativo a julio de 1994.
    recalculo = nuevo["ripte"] / BASE_JULIO_1994 * 100
    dif = (nuevo["indice"] / recalculo - 1).abs()
    if (dif > 1e-3).any():
        errores.append(f"indice: no coincide con el monto / julio 1994 (diferencia máxima {dif.max():.4%}).")
    # El no decreciente es el máximo acumulado del índice.
    if ((nuevo["indice_no_decreciente"] - nuevo["indice"].cummax()).abs() > 0.011).any():
        errores.append("indice_no_decreciente: no es el máximo acumulado del índice.")
    return errores
