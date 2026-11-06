"""Índice Construya: despachos de insumos para la construcción de las empresas del Grupo Construya, base jun-2002=100,
con estacionalidad y desestacionalizado (Grupo Construya).

Se lee la tabla de la página del índice (los últimos años, mes por mes); los meses anteriores que ya no muestra la página
se conservan de las corridas previas.
"""

import html
import re

import pandas as pd

from pipeline.fuentes._indec import Columna

ID = "construya"
NOMBRE = "Índice Construya de despachos de insumos para la construcción (Grupo Construya)"
URL = "https://www.grupoconstruya.com.ar/servicios/indice_construya"
PAGINA = URL
EXTENSION = "html"
FRECUENCIA = "M"
ORGANISMO = "Grupo Construya"
UNIDAD = "Índice jun-2002=100"
CALENDARIO = ""

COLUMNAS = {"indice": Columna("", "Índice Construya, con estacionalidad"),
            "indice_var_ia": Columna("", "Índice Construya, var. % interanual (publicada)", unidad="%", tipo="variacion",
                                     base="indice", rezago=12),
            "indice_desest": Columna("", "Índice Construya, desestacionalizado (Grupo Construya)"),
            "indice_desest_var_m": Columna("", "Índice Construya, desestacionalizado, var. % mensual (publicada)",
                                           unidad="%", tipo="variacion", base="indice_desest", rezago=1)}
MESES = {m: i + 1 for i, m in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                                          "septiembre", "octubre", "noviembre", "diciembre"])}


def _n(v: str) -> float:
    try:
        return float(v.replace(".", "").replace(",", ".").replace("%", "").replace("+", "").strip())
    except ValueError:  # "N/A"
        return float("nan")


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    texto = html.unescape(contenido.decode("utf-8", "replace"))
    filas = {}
    for bloque in texto.split('class="TablaRowIndice"')[1:]:
        # Los eneros vienen en negrita (<strong>): se saltean las etiquetas antes del valor.
        campos = dict(re.findall(r'tituloInline">\s*([^<:]+):\s*</span>\s*(?:<[^>]+>\s*)*([^<]+)<', bloque))
        mes = re.fullmatch(r"(\w+)\s+(\d{4})", campos.get("Mes", "").strip().lower())
        if not mes or mes[1] not in MESES:
            continue
        f = pd.Timestamp(year=int(mes[2]), month=MESES[mes[1]], day=1)
        filas[f] = {"indice": _n(campos["Con Estacionalidad"]), "indice_var_ia": _n(campos.get("% Interanual", "")),
                    "indice_desest": _n(campos["Desestacionalizado"]),
                    "indice_desest_var_m": _n(campos.get("Variación Mensual", ""))}
    if len(filas) < 24:
        raise ValueError(f"La página del Índice Construya tiene {len(filas)} meses (se esperaban más de 24).")
    df = pd.DataFrame.from_dict(filas, orient="index").sort_index()
    df.index.name = "fecha"
    return df.reset_index()[["fecha", *columnas]]


def combinar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None) -> pd.DataFrame:
    if anterior is None or not len(anterior):
        return nuevo
    viejos = anterior[anterior["fecha"] < nuevo["fecha"].min()]
    return pd.concat([viejos, nuevo], ignore_index=True)[list(nuevo.columns)]


def validar(nuevo, anterior, columnas=COLUMNAS):
    errores = []
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los meses no son consecutivos.")
    if not nuevo["indice_desest"].between(50, 600).all():
        errores.append("Índice fuera de rango.")
    if (pd.Timestamp.today() - nuevo["fecha"].max()).days > 75:
        errores.append("El último mes tiene más de dos meses.")
    return errores
