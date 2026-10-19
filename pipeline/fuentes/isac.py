"""ISAC: Indicador sintético de la actividad de la construcción (original, desestacionalizado
y tendencia-ciclo) e insumos para la construcción (serie original y desestacionalizada).

Fuente: INDEC, Indicadores de coyuntura de la actividad de la construcción, base 2004=100.
Archivo: sh_isac_<año>.xls. El nombre lleva el año, así que se prueban el año actual
y el anterior y se usa el que tenga el dato más reciente.
Cuadros: 1 (ISAC), 2.1 (insumos, original), 3.1 (insumos, desestacionalizada).
"""

from datetime import date

import pandas as pd

from pipeline.fuentes._indec import Columna, columnas_por_encabezado, leer_tabla_mensual, validar_tabla

ID = "isac"
NOMBRE = "ISAC: actividad de la construcción e insumos"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/sh_isac_{anio}.xls"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-3-42"
EXTENSION = "xls"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Índice base 2004=100"
PRIMER_PERIODO = "2012-01-01"
CALENDARIO = "Indicadores de coyuntura de la actividad de la construcción"

ORIG, DES, TEN = "Serie original", "Serie desestacionalizada", "Serie tendencia-ciclo"
MES_ANT = "Variación porcentual respecto al mes anterior"
ISAC = {
    "original": Columna(f"{ORIG} | ISAC nivel general", "ISAC, serie original", hoja="Cuadro 1"),
    "original_var_ia": Columna(f"{ORIG} | Variación porcentual | respecto al mismo mes",
                               "ISAC, serie original, var. % interanual",
                               tipo="variacion", base="original", rezago=12, hoja="Cuadro 1"),
    "original_var_acum": Columna(f"{ORIG} | acumulada del año", "ISAC, serie original, var. % acumulada en el año",
                                 tipo="variacion", rezago=12, hoja="Cuadro 1"),
    "desest": Columna(f"{DES} | ISAC nivel general", "ISAC, serie desestacionalizada", hoja="Cuadro 1"),
    "desest_var_m": Columna(f"{DES} | {MES_ANT}", "ISAC, desestacionalizada, var. % mensual",
                            tipo="variacion", base="desest", rezago=1, hoja="Cuadro 1"),
    "tendencia": Columna(f"{TEN} | ISAC nivel general", "ISAC, serie tendencia-ciclo", hoja="Cuadro 1"),
    "tendencia_var_m": Columna(f"{TEN} | {MES_ANT}", "ISAC, tendencia-ciclo, var. % mensual",
                               tipo="variacion", base="tendencia", rezago=1, hoja="Cuadro 1"),
}


def urls(hoy: date) -> list[str]:
    return [URL.format(anio=hoy.year), URL.format(anio=hoy.year - 1)]


def columnas(contenido: bytes) -> dict[str, Columna]:
    cols = dict(ISAC)
    cols.update(columnas_por_encabezado(contenido, "Cuadro 2.1", desde_col=2, prefijo_id="insumo_orig_",
                                        sufijo_nombre=" (insumo, serie original)"))
    cols.update(columnas_por_encabezado(contenido, "Cuadro 3.1", desde_col=2, prefijo_id="insumo_desest_",
                                        sufijo_nombre=" (insumo, serie desestacionalizada)"))
    return cols


def leer(contenido: bytes, columnas: dict[str, Columna]) -> pd.DataFrame:
    return leer_tabla_mensual(contenido, None, columnas)


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas: dict[str, Columna]) -> list[str]:
    sin_control = {c for c in columnas if c not in ISAC}
    # En 2021, contra la base de la pandemia, hubo variaciones de más de 100%.
    return validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, sin_control, rango_nivel=(0, 1e4),
                         max_variacion=500, vacios_permitidos={c for c in columnas if c.startswith("insumo_")})
