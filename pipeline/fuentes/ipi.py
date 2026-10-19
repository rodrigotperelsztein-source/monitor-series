"""IPI manufacturero: nivel general (original, desestacionalizado y tendencia-ciclo),
divisiones y subclases (serie original) y divisiones (serie desestacionalizada).

Fuente: INDEC, Índice de producción industrial manufacturero, base 2004=100.
Archivo: sh_ipi_manufacturero_<año>.xls. El nombre lleva el año, así que se prueban
el año actual y el anterior y se usa el que tenga el dato más reciente.
Cuadros: 1 (nivel general), 2 (divisiones y subclases, original), 5 (divisiones, desestacionalizada).
"""

from datetime import date

import pandas as pd

from pipeline.fuentes._indec import Columna, columnas_por_encabezado, leer_tabla_mensual, validar_tabla

ID = "ipi"
NOMBRE = "IPI manufacturero: nivel general, divisiones y subclases"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipi_manufacturero_{anio}.xls"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-6-14"
EXTENSION = "xls"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Índice base 2004=100"
PRIMER_PERIODO = "2016-01-01"
CALENDARIO = "Índice de producción industrial manufacturero"

ORIG, DES, TEN = "Serie original", "Serie desestacionalizada", "Serie tendencia-ciclo"
MES_ANT = "Variación porcentual respecto al mes anterior"
NIVEL_GENERAL = {
    "original": Columna(f"{ORIG} | Nivel general", "IPI manufacturero, serie original", hoja="Cuadro 1"),
    "original_var_ia": Columna(f"{ORIG} | Variación porcentual | respecto al mismo mes",
                               "IPI manufacturero, serie original, var. % interanual",
                               tipo="variacion", base="original", rezago=12, hoja="Cuadro 1"),
    "original_var_acum": Columna(f"{ORIG} | acumulada del año",
                                 "IPI manufacturero, serie original, var. % acumulada en el año",
                                 tipo="variacion", rezago=12, hoja="Cuadro 1"),
    "desest": Columna(f"{DES} | Nivel general", "IPI manufacturero, serie desestacionalizada", hoja="Cuadro 1"),
    "desest_var_m": Columna(f"{DES} | {MES_ANT}", "IPI manufacturero, desestacionalizada, var. % mensual",
                            tipo="variacion", base="desest", rezago=1, hoja="Cuadro 1"),
    "tendencia": Columna(f"{TEN} | Nivel general", "IPI manufacturero, serie tendencia-ciclo", hoja="Cuadro 1"),
    "tendencia_var_m": Columna(f"{TEN} | {MES_ANT}", "IPI manufacturero, tendencia-ciclo, var. % mensual",
                               tipo="variacion", base="tendencia", rezago=1, hoja="Cuadro 1"),
}


def urls(hoy: date) -> list[str]:
    return [URL.format(anio=hoy.year), URL.format(anio=hoy.year - 1)]


def columnas(contenido: bytes) -> dict[str, Columna]:
    cols = dict(NIVEL_GENERAL)
    # Cuadro 2: divisiones y subclases, serie original (sin el nivel general, que ya está).
    cols.update(columnas_por_encabezado(contenido, "Cuadro 2", desde_col=3, prefijo_id="orig_",
                                        sufijo_nombre=" (serie original)", excluir=("D | IPI",)))
    # Cuadro 5: divisiones desestacionalizadas; cada índice va seguido de su variación mensual.
    c5 = columnas_por_encabezado(contenido, "Cuadro 5", desde_col=3, prefijo_id="desest_")
    nivel = None
    for cid, col in c5.items():
        if "VARIACION PORCENTUAL" in col.prefijo:
            if nivel is None:
                continue
            cols[f"{nivel}_var_m"] = Columna(col.prefijo, f"{cols[nivel].nombre}, var. % mensual",
                                             tipo="variacion", base=nivel, rezago=1, hoja="Cuadro 5")
        elif not col.prefijo.startswith("D | "):
            nivel = cid
            cols[cid] = Columna(col.prefijo, col.nombre + " (serie desestacionalizada)", hoja="Cuadro 5")
        else:
            nivel = None  # el nivel general desestacionalizado ya está en el cuadro 1
    return cols


def leer(contenido: bytes, columnas: dict[str, Columna]) -> pd.DataFrame:
    return leer_tabla_mensual(contenido, None, columnas)


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas: dict[str, Columna]) -> list[str]:
    # El control interanual de meses nuevos se aplica al nivel general; las subclases son muy volátiles.
    sin_control = {c for c in columnas if c not in NIVEL_GENERAL}
    # Algunas subclases tienen meses en blanco o en cero (p. ej. hojas de tabaco, que es estacional),
    # lo que produce variaciones enormes en su división; el recálculo desde los índices sigue
    # controlando que no haya columnas cruzadas.
    return validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, sin_control, rango_nivel=(-1e-9, 1e5),
                         max_variacion=1e6, vacios_permitidos=sin_control)
