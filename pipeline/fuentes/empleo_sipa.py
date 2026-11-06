"""Trabajo registrado (SIPA): personas con trabajo registrado y asalariados registrados del sector privado, miles, serie
original y desestacionalizada por la Secretaría de Trabajo (Observatorio de Empleo y Dinámica Empresarial).

Archivo: trabajoregistrado_<aamm>_estadisticas.xlsx, enlazado desde la página "Situación y evolución del trabajo
registrado" (el nombre cambia con cada informe). Hojas T.1 (total), T.2.1 y T.2.2 (por modalidad, original y sin
estacionalidad) y A.1 (asalariados privados).
"""

import io
import re
from datetime import date

import pandas as pd

from pipeline.fuentes import _enlace
from pipeline.fuentes.deuda import _mes
from pipeline.fuentes._indec import Columna, norm

ID = "empleo_sipa"
NOMBRE = "Trabajo registrado: total, por modalidad y asalariados privados (SIPA, Secretaría de Trabajo)"
PAGINA = "https://www.argentina.gob.ar/trabajo/estadisticas/situacion-y-evolucion-del-trabajo-registrado"
URL = PAGINA
EXTENSION = "xlsx"
FRECUENCIA = "M"
ORGANISMO = "Secretaría de Trabajo (OEDE, en base al SIPA)"
UNIDAD = "Miles de personas"
PRIMER_PERIODO = "2009-01-01"
CALENDARIO = ""

# Texto que identifica la columna en el encabezado ("Empleo asalariado en el sector privado", etc.).
MODALIDADES = {"asalariados_privados": "SECTOR PRIVADO", "asalariados_publicos": "SECTOR PUBLICO",
               "casas_particulares": "CASAS PARTICULARES", "autonomos": "AUTONOMOS", "monotributo": "MONOTRIBUTO",
               "monotributo_social": "MONOTRIBUTO SOCIAL"}
NOMBRES = {"asalariados_privados": "Asalariados registrados del sector privado",
           "asalariados_publicos": "Asalariados registrados del sector público",
           "casas_particulares": "Asalariados registrados de casas particulares", "autonomos": "Independientes autónomos",
           "monotributo": "Independientes monotributistas", "monotributo_social": "Monotributistas sociales"}
COLUMNAS = {"total": Columna("", "Personas con trabajo registrado"),
            "total_desest": Columna("", "Personas con trabajo registrado, desestacionalizada (Secretaría de Trabajo)")}
# El monotributo no tiene estacionalidad: la hoja sin estacionalidad repite la serie original.
SIN_DESEST = {"monotributo", "monotributo_social"}
for _k, _n in NOMBRES.items():
    COLUMNAS[_k] = Columna("", _n)
    if _k not in SIN_DESEST:
        COLUMNAS[f"{_k}_desest"] = Columna("", f"{_n}, desestacionalizada (Secretaría de Trabajo)")
COLUMNAS["empleo_privado"] = Columna("", "Asalariados registrados del sector privado (serie larga, desde 2009)")
COLUMNAS["empleo_privado_desest"] = Columna("", "Asalariados registrados del sector privado, desestacionalizada (serie larga)")
COLUMNAS["empleo_privado_var_ia"] = Columna("", "Asalariados registrados del sector privado, var. % interanual", unidad="%",
                                            tipo="variacion", base="empleo_privado", rezago=12)
COLUMNAS["empleo_privado_desest_var_m"] = Columna("", "Asalariados registrados del sector privado, desestacionalizada, var. % mensual",
                                                  unidad="%", tipo="variacion", base="empleo_privado_desest", rezago=1)


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    url = _enlace.buscar(descargar, PAGINA, r"/sites/default/files/[\w/-]*trabajoregistrado_\d{4}_estadisticas\.xlsx$")
    return url, descargar(url, minimo=1_000_000)


def _hoja(libro: dict, nombre: str) -> pd.DataFrame:
    return next(v for k, v in libro.items() if k.strip() == nombre)


def _por_fecha(h: pd.DataFrame) -> pd.DataFrame:
    """Filas con período en la primera columna: fechas de Excel o texto como "may-17" o "jul-26*"."""
    fechas = pd.Series([_mes(v) for v in h.iloc[:, 0]], index=h.index)
    d = h[fechas.notna()].copy()
    d.index = pd.DatetimeIndex(fechas[fechas.notna()])
    if d.index.duplicated().any():
        raise ValueError("Hay meses repetidos en la hoja.")
    return d


def _modalidades(h: pd.DataFrame) -> dict[str, pd.Series]:
    """Columna de cada modalidad según el encabezado (las primeras filas)."""
    enc = {j: norm(" ".join(str(v) for v in h.iloc[:4, j] if pd.notna(v) and not hasattr(v, "year")))
           .replace("Ú", "U").replace("Ó", "O") for j in range(1, h.shape[1])}
    d = _por_fecha(h)
    out = {}
    for k, rot in MODALIDADES.items():
        cols = [j for j, t in enc.items() if rot in re.sub(r"\s+", " ", t)
                and not (k == "monotributo" and "SOCIAL" in t)]
        if len(cols) != 1:
            raise ValueError(f"No encontré una sola columna con '{rot}' ({len(cols)}).")
        out[k] = pd.to_numeric(d.iloc[:, cols[0]], errors="coerce")
    return out


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    libro = pd.read_excel(io.BytesIO(contenido), sheet_name=["T.1", "T.2.1", "T.2.2", "A.1"], header=None)
    t1, a1 = _por_fecha(_hoja(libro, "T.1")), _por_fecha(_hoja(libro, "A.1"))
    s = {"total": pd.to_numeric(t1.iloc[:, 1], errors="coerce"), "total_desest": pd.to_numeric(t1.iloc[:, 2], errors="coerce"),
         "empleo_privado": pd.to_numeric(a1.iloc[:, 1], errors="coerce"),
         "empleo_privado_desest": pd.to_numeric(a1.iloc[:, 2], errors="coerce")}
    for k, v in _modalidades(_hoja(libro, "T.2.1")).items():
        s[k] = v
    for k, v in _modalidades(_hoja(libro, "T.2.2")).items():
        if k not in SIN_DESEST:
            s[f"{k}_desest"] = v
    df = pd.DataFrame(s).sort_index()
    df = df[df.index >= PRIMER_PERIODO]
    df = df.reindex(pd.date_range(df.index.min(), df.index.max(), freq="MS"))
    df["empleo_privado_var_ia"] = (df["empleo_privado"] / df["empleo_privado"].shift(12) - 1) * 100
    df["empleo_privado_desest_var_m"] = (df["empleo_privado_desest"] / df["empleo_privado_desest"].shift(1) - 1) * 100
    df.index.name = "fecha"
    return df.reset_index()[["fecha", *columnas]]


def validar(nuevo, anterior, columnas=COLUMNAS):
    errores = []
    if nuevo["empleo_privado"].isna().any():
        errores.append("Hay meses sin asalariados privados.")
    if not nuevo["empleo_privado"].between(4_000, 9_000).all():
        errores.append("Asalariados privados fuera de rango (¿cambió la unidad?).")
    u = nuevo.dropna(subset=["asalariados_privados"]).iloc[-1]
    if abs(u["asalariados_privados"] / u["empleo_privado"] - 1) > 0.05:
        errores.append("Los asalariados privados de T.2.1 y de A.1 difieren más de 5% (¿columnas cruzadas?).")
    if (pd.Timestamp.today() - nuevo["fecha"].max()).days > 200:
        errores.append("El último dato tiene más de seis meses.")
    if anterior is not None and len(anterior) and len(nuevo) < len(anterior):
        errores.append("Se perdieron meses.")
    return errores
