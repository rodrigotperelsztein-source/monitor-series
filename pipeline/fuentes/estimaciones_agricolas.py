"""Estimación de la campaña agrícola en curso: superficie y producción de trigo, maíz, soja y girasol.

Fuente: Secretaría de Agricultura, Ganadería y Pesca, Dirección de Estimaciones Agrícolas (ver _magyp.py):
  - informe mensual (mediados de mes): superficie implantada y, cuando ya se estimó, producción de la campaña
    en curso de cada cultivo. La producción se publica recién avanzado el ciclo (el trigo, cerca de la cosecha);
  - informe semanal: área sembrada y producción de las últimas diez campañas cerradas, de donde sale el
    rendimiento tendencial (mediana de las últimas cinco, toneladas por hectárea sembrada).

Por cultivo, una fila por mes (el del informe mensual):
  - <cultivo>_campania: año en que empezó la campaña a la que se refiere el informe;
  - <cultivo>_superficie_ha y <cultivo>_produccion_t: lo que informa la Secretaría (producción vacía si todavía
    no la estimó);
  - <cultivo>_produccion_tendencial_t: superficie por rendimiento tendencial, una referencia para cuando todavía
    no hay estimación de producción (no la reemplaza: un año bueno o malo se aparta de la tendencia).
"""

import io
import zipfile
from datetime import date
from statistics import median

import pandas as pd

from pipeline.fuentes import _magyp
from pipeline.fuentes._indec import Columna

ID = "estimaciones_agricolas"
NOMBRE = "Estimación de la campaña agrícola en curso: trigo, maíz, soja y girasol (Secretaría de Agricultura)"
PAGINA = _magyp.INFORMES
URL = _magyp.INFORMES
EXTENSION = "zip"
FRECUENCIA = "M"
ORGANISMO = "Secretaría de Agricultura, Ganadería y Pesca (Estimaciones Agrícolas)"
UNIDAD = "Toneladas"
PRIMER_PERIODO = "2026-10-01"
CALENDARIO = ""
GUARDAR_ORIGINAL = False
DIAS_DEL_MES = range(12, 32)  # el informe mensual sale a mediados de mes

NOMBRES = {"trigo": "trigo", "maiz": "maíz", "soja": "soja", "girasol": "girasol"}
COLUMNAS = {}
for _c, _n in NOMBRES.items():
    COLUMNAS[f"{_c}_campania"] = Columna("", f"{_n.capitalize()}: año de inicio de la campaña estimada", unidad="año")
    COLUMNAS[f"{_c}_superficie_ha"] = Columna("", f"{_n.capitalize()}: superficie implantada, campaña en curso", unidad="Hectáreas")
    COLUMNAS[f"{_c}_produccion_t"] = Columna("", f"{_n.capitalize()}: producción estimada, campaña en curso")
    COLUMNAS[f"{_c}_produccion_tendencial_t"] = Columna(
        "", f"{_n.capitalize()}: producción con rendimiento tendencial (superficie × mediana de 5 campañas)")


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    urls = _magyp.ultimos_informes(descargar, hoy)
    if "mensual" not in urls:
        raise ValueError("No encontré el informe mensual de Estimaciones Agrícolas del mes ni del anterior.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("urls.txt", f"{urls['mensual']}\n{urls['semanal']}")
        z.writestr("mensual.pdf", descargar(urls["mensual"], minimo=100_000))
        z.writestr("semanal.pdf", descargar(urls["semanal"], minimo=100_000))
    return f"{urls['mensual']} {urls['semanal']}", buf.getvalue()


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        url_mensual = z.read("urls.txt").decode().splitlines()[0]
        est = _magyp.estimacion_mensual(z.read("mensual.pdf"))
        dec = _magyp.series_decenales(z.read("semanal.pdf"))
    falta = [c for c in NOMBRES if c not in est]
    if falta:
        raise ValueError(f"El informe mensual no trae {', '.join(falta)} ({url_mensual}).")
    fila = {"fecha": pd.Timestamp(_magyp.fecha_informe(url_mensual).replace(day=1))}
    for c in NOMBRES:
        e = est[c]
        rend = None
        area, prod = dec["area"].get(c, {}), dec["produccion"].get(c, {})
        comunes = sorted(set(area) & set(prod))[-5:]
        if len(comunes) == 5:
            rend = median(prod[k] / area[k] for k in comunes)
        fila[f"{c}_campania"] = e["campania"]
        fila[f"{c}_superficie_ha"] = e["superficie_ha"]
        fila[f"{c}_produccion_t"] = e["produccion_t"]
        fila[f"{c}_produccion_tendencial_t"] = round(e["superficie_ha"] * rend) if rend and e["superficie_ha"] else None
    return pd.DataFrame([fila], columns=["fecha", *columnas])


def combinar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None) -> pd.DataFrame:
    """Se guarda una fila por informe mensual: los meses anteriores se conservan."""
    if anterior is None or not len(anterior):
        return nuevo
    a = anterior[~anterior["fecha"].isin(nuevo["fecha"])].reindex(columns=nuevo.columns)
    return pd.concat([a, nuevo], ignore_index=True).sort_values("fecha").reset_index(drop=True)


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    rangos = {"trigo": (2e6, 50e6), "maiz": (5e6, 120e6), "soja": (5e6, 90e6), "girasol": (0.3e6, 15e6)}
    for c, (lo, hi) in rangos.items():
        for col in (f"{c}_produccion_t", f"{c}_produccion_tendencial_t"):
            if not nuevo[col].dropna().between(lo, hi).all():
                errores.append(f"{col}: fuera de rango ({lo:,.0f}-{hi:,.0f} t).")
        if not nuevo[f"{c}_superficie_ha"].dropna().between(lo / 10, hi / 1.5).all():
            errores.append(f"{c}_superficie_ha: fuera de rango.")
    return errores
