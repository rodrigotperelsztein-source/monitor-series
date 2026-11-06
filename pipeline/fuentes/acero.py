"""Producción siderúrgica: hierro primario, acero crudo y laminados, miles de toneladas por mes desde 2016 (Cámara
Argentina del Acero).

La Cámara publica un PDF ("Producción Siderúrgica Argentina 1960 - <año>") cuyo nombre y carpeta cambian con cada
actualización: el enlace se toma de su página de estadísticas locales. En el PDF, los meses de cada año van antes de la
fila con el total del año; se controla que sumen ese total.
"""

import io
import re
from datetime import date

import pandas as pd
import pdfplumber

from pipeline.fuentes import _enlace
from pipeline.fuentes._indec import Columna

ID = "acero"
NOMBRE = "Producción siderúrgica: acero crudo, hierro primario y laminados (Cámara Argentina del Acero)"
PAGINA = "https://www.acero.org.ar/estadisticas-locales/"
URL = PAGINA
EXTENSION = "pdf"
FRECUENCIA = "M"
ORGANISMO = "Cámara Argentina del Acero"
UNIDAD = "Miles de toneladas"
PRIMER_PERIODO = "2016-01-01"
CALENDARIO = ""

CAMPOS = ["arrabio", "hierro_esponja", "hierro_primario", "acero_crudo", "laminados_no_planos", "laminados_planos",
          "laminados_caliente", "planos_frio"]
NOMBRES = {"arrabio": "Hierro primario: arrabio", "hierro_esponja": "Hierro primario: hierro esponja",
           "hierro_primario": "Hierro primario, total", "acero_crudo": "Acero crudo",
           "laminados_no_planos": "Laminados en caliente no planos", "laminados_planos": "Laminados en caliente planos",
           "laminados_caliente": "Laminados en caliente, total", "planos_frio": "Laminados planos en frío"}
COLUMNAS = {k: Columna("", f"Producción de {n[0].lower()}{n[1:]}") for k, n in NOMBRES.items()}
COLUMNAS["acero_crudo_var_ia"] = Columna("", "Producción de acero crudo, var. % interanual", unidad="%", tipo="variacion",
                                         base="acero_crudo", rezago=12)
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre",
         "diciembre"]
NUM = r"(-?[\d.]+,\d|\d+)"


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    url = _enlace.buscar(descargar, PAGINA, r"/wp-content/uploads/\d{4}/\d{2}/Produccion-Siderurgica-Argentina-[\w-]*\.pdf$")
    return url, descargar(url, minimo=20_000)


def _num(v: str) -> float:
    return float(v.replace(".", "").replace(",", "."))


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    with pdfplumber.open(io.BytesIO(contenido)) as pdf:
        lineas = "\n".join(p.extract_text() or "" for p in pdf.pages).splitlines()
    filas, pendientes = {}, []
    for linea in lineas:
        m = re.fullmatch(r"(\w+)\s+" + r"\s+".join([NUM] * 8) + r"\s*", linea.strip())
        if not m:
            continue
        valores = [_num(v) for v in m.groups()[1:]]
        cab = m[1].lower()
        if cab in MESES:
            pendientes.append((MESES.index(cab) + 1, valores))
        elif re.fullmatch(r"(19|20)\d\d", cab):
            anio = int(cab)
            if pendientes:
                if [mm for mm, _ in pendientes] != list(range(1, len(pendientes) + 1)):
                    raise ValueError(f"Los meses antes del total de {anio} no van de enero en adelante.")
                crudo = sum(v[3] for _, v in pendientes)
                if abs(crudo - valores[3]) > 1.5:
                    raise ValueError(f"Los meses de {anio} no suman el total del año ({crudo:.1f} vs {valores[3]:.1f}).")
                for mm, v in pendientes:
                    if any(v):  # los meses que faltan publicar vienen en cero
                        filas[pd.Timestamp(year=anio, month=mm, day=1)] = v
            pendientes = []
    if pendientes:
        raise ValueError("Quedaron meses sin la fila del total del año.")
    df = pd.DataFrame.from_dict(filas, orient="index", columns=CAMPOS).sort_index()
    df = df[df.index >= PRIMER_PERIODO]
    df["acero_crudo_var_ia"] = (df["acero_crudo"] / df["acero_crudo"].shift(12) - 1) * 100
    df.index.name = "fecha"
    return df.reset_index()[["fecha", *columnas]]


def validar(nuevo, anterior, columnas=COLUMNAS):
    errores = []
    esperado = pd.date_range(PRIMER_PERIODO, periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los meses no son consecutivos desde 2016.")
    if not nuevo["acero_crudo"].between(50, 700).all():
        errores.append("Acero crudo fuera de rango.")
    if (pd.Timestamp.today() - nuevo["fecha"].max()).days > 100:
        errores.append("El último mes tiene más de tres meses.")
    if anterior is not None and len(anterior) and len(nuevo) < len(anterior):
        errores.append("Se perdieron meses.")
    return errores
