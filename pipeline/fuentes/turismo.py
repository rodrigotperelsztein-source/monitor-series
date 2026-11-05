"""Turismo internacional: turistas residentes que viajaron al exterior (emisivo) y no residentes que llegaron al país
(receptivo), por vía, miles de personas (INDEC, Estadísticas de turismo internacional).

Archivos: serie_turismo_emisivo_total_vias.xlsx y serie_turismo_receptivo_total_vias.xlsx (desde 2022, todas las vías).
"""

import io
import zipfile

import pandas as pd

from pipeline.fuentes._indec import Columna, leer_tabla_mensual, validar_tabla

ID = "turismo"
NOMBRE = "Turismo internacional: turistas emisivos y receptivos, por vía (INDEC)"
URL_E = "https://www.indec.gob.ar/ftp/cuadros/economia/serie_turismo_emisivo_total_vias.xlsx"
URL_R = "https://www.indec.gob.ar/ftp/cuadros/economia/serie_turismo_receptivo_total_vias.xlsx"
URL = URL_E
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-13-55"
EXTENSION = "zip"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Miles de personas"
PRIMER_PERIODO = "2022-01-01"
CALENDARIO = "Estadísticas de turismo internacional"

VIAS = {"total": "Total", "aerea": "Aérea", "fluvial": "Fluvial", "terrestre": "Terrestre"}
COLUMNAS = {}
for _p, _n in (("emisivo", "Turistas residentes que viajaron al exterior"), ("receptivo", "Turistas no residentes que llegaron al país")):
    for _v, _vn in VIAS.items():
        COLUMNAS[f"{_p}_{_v}"] = Columna(f"Turistas | {_vn}", f"{_n}{'' if _v == 'total' else ', vía ' + _vn.lower()}")


def bajar(descargar, hoy) -> tuple[str, bytes]:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("emisivo.xlsx", descargar(URL_E))
        z.writestr("receptivo.xlsx", descargar(URL_R))
    return f"{URL_E} {URL_R}", buf.getvalue()


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    partes = []
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        for p in ("emisivo", "receptivo"):
            cols = {k: v for k, v in columnas.items() if k.startswith(p)}
            partes.append(leer_tabla_mensual(z.read(f"{p}.xlsx"), f"turismo {p}", cols).set_index("fecha"))
    return pd.concat(partes, axis=1).sort_index().reset_index()[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    return validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, set(columnas), rango_nivel=(0, 1e5), max_variacion=10000)
