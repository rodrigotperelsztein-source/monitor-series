"""Remuneración promedio de los trabajadores registrados del sector privado, por provincia (pesos corrientes).

Fuente: Ministerio de Capital Humano, Secretaría de Trabajo, Empleo y Seguridad Social, Observatorio de Empleo y
Dinámica Empresarial (OEDE), en base al SIPA. Planilla "provinciales_serie_remuneraciones_mensual_2dig_<n>.xlsx",
enlazada desde la página de estadísticas regionales del OEDE; se usa solo la hoja "Total": remuneración por todo
concepto por provincia y total país, a valores corrientes, desde enero de 1995.

Notas:
  - "Por todo concepto" incluye el aguinaldo: junio y diciembre son mucho más altos que el resto de los meses.
  - Gran Buenos Aires (CABA más los partidos del conurbano), Capital Federal y "Buenos Aires" (el resto de la
    provincia, sin el conurbano) son las tres áreas de la planilla para esa región.
  - El nombre del archivo cambia con cada actualización (el número final): se busca en la página.
"""

import io
import re
import unicodedata
from datetime import date
from urllib.parse import urljoin

import pandas as pd

from pipeline.fuentes._indec import Columna

ID = "remuneraciones_provincias"
NOMBRE = "Remuneración promedio de los asalariados registrados del sector privado, por provincia (OEDE, SIPA)"
PAGINA = "https://www.argentina.gob.ar/trabajo/estadisticas/oede-estadisticas-provinciales"
URL = "https://www.argentina.gob.ar/sites/default/files/provinciales_serie_remuneraciones_mensual_2dig_9.xlsx"
EXTENSION = "xlsx"
FRECUENCIA = "M"
ORGANISMO = "Secretaría de Trabajo, Empleo y Seguridad Social (OEDE, en base al SIPA)"
UNIDAD = "Pesos corrientes"
PRIMER_PERIODO = "1995-01-01"
CALENDARIO = ""
GUARDAR_ORIGINAL = False  # 11 MB, y se baja de nuevo cuando cambia

# Fila de la hoja "Total" (sin tildes, en mayúsculas) -> (id de columna, nombre para mostrar)
PROVINCIAS = {
    "TOTAL": ("total", "Total país"),
    "GRAN BUENOS AIRES": ("gba", "Gran Buenos Aires (CABA y conurbano)"),
    "CAPITAL FEDERAL": ("caba", "Ciudad de Buenos Aires"),
    "BUENOS AIRES": ("buenos_aires_resto", "Buenos Aires, resto de la provincia (sin el conurbano)"),
    "CATAMARCA": ("catamarca", "Catamarca"), "CORDOBA": ("cordoba", "Córdoba"), "CORRIENTES": ("corrientes", "Corrientes"),
    "CHACO": ("chaco", "Chaco"), "CHUBUT": ("chubut", "Chubut"), "ENTRE RIOS": ("entre_rios", "Entre Ríos"),
    "FORMOSA": ("formosa", "Formosa"), "JUJUY": ("jujuy", "Jujuy"), "LA PAMPA": ("la_pampa", "La Pampa"),
    "LA RIOJA": ("la_rioja", "La Rioja"), "MENDOZA": ("mendoza", "Mendoza"), "MISIONES": ("misiones", "Misiones"),
    "NEUQUEN": ("neuquen", "Neuquén"), "RIO NEGRO": ("rio_negro", "Río Negro"), "SALTA": ("salta", "Salta"),
    "SAN JUAN": ("san_juan", "San Juan"), "SAN LUIS": ("san_luis", "San Luis"), "SANTA CRUZ": ("santa_cruz", "Santa Cruz"),
    "SANTA FE": ("santa_fe", "Santa Fe"), "SANTIAGO DEL ESTERO": ("santiago_del_estero", "Santiago del Estero"),
    "TUCUMAN": ("tucuman", "Tucumán"), "TIERRA DEL FUEGO": ("tierra_del_fuego", "Tierra del Fuego"),
}
COLUMNAS = {cid: Columna("", f"Remuneración promedio, asalariados registrados del sector privado: {n}")
            for cid, n in PROVINCIAS.values()}


def _norm(s) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip().upper()


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    """Busca en la página del OEDE el link vigente de la planilla (el número final cambia con cada versión)."""
    url = URL
    try:
        html = descargar(PAGINA, minimo=5_000).decode("utf-8", "replace")
        links = re.findall(r"""["']([^"']*provinciales_serie_remuneraciones_mensual_2dig[^"']*\.xlsx)["']""", html, re.I)
        if links:
            url = urljoin(PAGINA, links[0])
    except Exception:  # noqa: BLE001 — si la página falla, se prueba el último link conocido
        pass
    return url, descargar(url, minimo=1_000_000)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    d = pd.read_excel(io.BytesIO(contenido), sheet_name="Total", header=None)
    fila_enc = next((i for i in range(min(15, len(d))) if _norm(d.iat[i, 0]) == "PROVINCIA"), None)
    if fila_enc is None:
        raise ValueError("No encontré la fila de encabezado ('Provincia') en la hoja Total.")
    fechas = pd.to_datetime(d.iloc[fila_enc, 1:], errors="coerce")
    if fechas.isna().any():
        raise ValueError("Hay columnas sin fecha en el encabezado de la hoja Total.")
    meses = fechas.dt.to_period("M").dt.to_timestamp()  # la planilla pone día 11 en cada mes
    out = pd.DataFrame({"fecha": meses.values})
    filas = {_norm(d.iat[i, 0]): i for i in range(fila_enc + 1, len(d)) if pd.notna(d.iat[i, 0])}
    for nombre, (cid, _) in PROVINCIAS.items():
        if nombre not in filas:
            raise ValueError(f"Falta la fila {nombre} en la hoja Total.")
        out[cid] = pd.to_numeric(d.iloc[filas[nombre], 1:].replace({"s.d.": None}), errors="coerce").values
    return out[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    esperado = pd.date_range(PRIMER_PERIODO, periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los meses no son consecutivos o no empiezan en enero de 1995.")
    if nuevo["total"].isna().any():
        errores.append("Hay meses sin total país.")
    u = nuevo.iloc[-1]
    otras = [c for c in columnas if c != "total"]
    if not (u[otras].min() < u["total"] < u[otras].max()):
        errores.append("El total país del último mes no queda entre la provincia más baja y la más alta.")
    if anterior is not None and len(anterior):
        comunes = nuevo.merge(anterior, on="fecha", suffixes=("", "_ant"))
        cambio = ((comunes["total"] / comunes["total_ant"] - 1).abs() > 0.05)
        if cambio.sum() > 6:
            errores.append(f"El total país cambió más de 5% en {int(cambio.sum())} meses ya publicados.")
    return errores
