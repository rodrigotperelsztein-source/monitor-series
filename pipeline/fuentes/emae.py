"""EMAE total: serie original, desestacionalizada y tendencia-ciclo, con sus variaciones.

Fuente: INDEC, Estimador Mensual de Actividad Económica, base 2004=100.
Datos: Catálogo API-INDEC (tabla estimador-mensual-de-actividad-economica-nivel-general), con respaldo en el archivo
sh_emae_mensual_base2004.xls (hoja "Tabla") si la API no está disponible.

Las variaciones son las que publica INDEC; el pipeline las recalcula desde los índices
y frena la actualización si no coinciden (eso detectaría columnas cruzadas).
INDEC escribe 0 como variación interanual de 2004, cuando no hay año anterior;
acá esos meses quedan vacíos.
"""

import numpy as np
import pandas as pd

from pipeline.fuentes import _api_indec as api
from pipeline.fuentes._indec import Columna, leer_tabla_mensual, validar_tabla

ID = "emae"
NOMBRE = "EMAE total: original, desestacionalizado y tendencia-ciclo"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/sh_emae_mensual_base2004.xls"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-9-48"
EXTENSION = "xls"
HOJA = "Tabla"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
# Comienzo del título en el calendario de difusión de INDEC.
CALENDARIO = "Estimador mensual de actividad económica"
UNIDAD = "Índice base 2004=100"
PRIMER_PERIODO = "2004-01-01"

MES_ANT = "Var % respecto al mes anterior"
COLUMNAS = {
    "original": Columna("Índice Serie Original", "Índice serie original (2004=100)"),
    "original_var_ia": Columna("Var % respecto a igual período", "Serie original, var. % interanual",
                               tipo="variacion", base="original", rezago=12),
    "desest": Columna("Índice Serie Desestacionalizada", "Índice serie desestacionalizada (2004=100)"),
    "desest_var_m": Columna(MES_ANT, "Serie desestacionalizada, var. % mensual", despues_de="desest",
                            tipo="variacion", base="desest", rezago=1),
    "tendencia": Columna("Índice Serie Tendencia-Ciclo", "Índice serie tendencia-ciclo (2004=100)"),
    "tendencia_var_m": Columna(MES_ANT, "Serie tendencia-ciclo, var. % mensual", despues_de="tendencia",
                               tipo="variacion", base="tendencia", rezago=1),
}


TABLA_API = "estimador-mensual-de-actividad-economica-nivel-general"
SERIES_API = {"original": "Índice serie original", "original_var_ia": "Var % interanual serie original",
              "desest": "Índice serie desestacionalizada", "desest_var_m": "Var % mensual serie desestacionalizada",
              "tendencia": "Índice serie tendencia-ciclo", "tendencia_var_m": "Var % mensual serie tendencia-ciclo"}


def bajar(descargar, hoy) -> tuple[str, bytes]:
    return api.bajar(TABLA_API, descargar, lambda: (URL, descargar(URL)))


def _leer_api(contenido: bytes, columnas) -> pd.DataFrame:
    f = api.filas(contenido)
    f["serie"] = f["tipo_de_indicador_descripcion"].str.strip().str.lower()
    ancho = f.pivot_table(index="fecha", columns="serie", values="valor", aggfunc="first")
    faltan = [d for d in SERIES_API.values() if d.lower() not in ancho.columns]
    if faltan:
        raise ValueError(f"API del INDEC: faltan series del EMAE: {faltan}")
    df = pd.DataFrame({cid: ancho[SERIES_API[cid].lower()] for cid in columnas}).reset_index()
    return df.sort_values("fecha").reset_index(drop=True)[["fecha", *columnas]]


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    df = _leer_api(contenido, columnas) if api.es_api(contenido) else leer_tabla_mensual(contenido, HOJA, columnas)
    for cid, col in columnas.items():
        if col.tipo == "variacion":
            df.loc[df.index[: col.rezago], cid] = np.nan
    return df


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    return validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO)
