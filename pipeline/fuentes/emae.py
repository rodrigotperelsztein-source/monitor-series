"""EMAE total: serie original, desestacionalizada y tendencia-ciclo, con sus variaciones.

Fuente: INDEC, Estimador Mensual de Actividad Económica, base 2004=100.
Archivo: sh_emae_mensual_base2004.xls, hoja "Tabla".

Las variaciones son las que publica INDEC; el pipeline las recalcula desde los índices
y frena la actualización si no coinciden (eso detectaría columnas cruzadas).
INDEC escribe 0 como variación interanual de 2004, cuando no hay año anterior;
acá esos meses quedan vacíos.
"""

import numpy as np
import pandas as pd

from pipeline.fuentes._indec import Columna, leer_tabla_mensual, validar_tabla

ID = "emae"
NOMBRE = "EMAE total: original, desestacionalizado y tendencia-ciclo"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/sh_emae_mensual_base2004.xls"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-9-48"
EXTENSION = "xls"
HOJA = "Tabla"
FRECUENCIA = "M"
UNIDAD = "Índice base 2004=100; variaciones en %"
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


def leer(contenido: bytes) -> pd.DataFrame:
    df = leer_tabla_mensual(contenido, HOJA, COLUMNAS)
    for cid, col in COLUMNAS.items():
        if col.tipo == "variacion":
            df.loc[df.index[: col.rezago], cid] = np.nan
    return df


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None) -> list[str]:
    return validar_tabla(nuevo, anterior, COLUMNAS, PRIMER_PERIODO)
