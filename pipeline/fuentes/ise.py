"""Indicador sintético de energía (ISE) del INDEC: nivel general y sus tres componentes.

Archivo: sh_indicadores_energeticos.xls, cuadros 1.1 (nivel general, original, desestacionalizado y
tendencia-ciclo) y 1.2 (componentes, serie original).

El ISE resume la oferta de energía: pondera la generación eléctrica neta, el gas entregado a centrales y un
conjunto de derivados del petróleo. Sale con unos cuatro meses de rezago, bastante más tarde que las series de
CAMMESA y de la Secretaría de Energía que ya están en el monitor, así que sirve de control, no de adelanto.
"""

import pandas as pd

from pipeline.fuentes._indec import Columna, leer_tabla_mensual, validar_tabla

ID = "ise"
NOMBRE = "Indicador sintético de energía (ISE, INDEC)"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/sh_indicadores_energeticos.xls"
PAGINA = "https://www.indec.gob.ar/Nivel4/Tema/3/36/145"
EXTENSION = "xls"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Índice base 2004=100"
PRIMER_PERIODO = "2015-01-01"
CALENDARIO = "Indicadores del sector energético"
MAX_DIAS_SIN_NOVEDAD = 160  # sale con unos cuatro meses de rezago

C11, C12 = "Cuadro 1.1", "Cuadro 1.2"
ORIG, DES, TEN = "Índice serie original", "Índice serie desestacionalizada", "Índice serie tendencia-ciclo"

COLUMNAS = {
    "ise": Columna(f"{ORIG} | ISE nivel general", "ISE, serie original", hoja=C11),
    "ise_var_ia": Columna(f"{ORIG} | Variación porcentual | respecto al mismo", "ISE, serie original, var. % interanual",
                          tipo="variacion", base="ise", rezago=12, hoja=C11),
    "ise_desest": Columna(f"{DES} | ISE nivel general", "ISE, serie desestacionalizada (INDEC)", hoja=C11),
    "ise_desest_var_m": Columna(f"{DES} | Variación porcentual", "ISE, desestacionalizado (INDEC), var. % mensual",
                                despues_de="ise_desest", tipo="variacion", base="ise_desest", rezago=1, hoja=C11),
    "ise_tendencia": Columna(f"{TEN} | ISE nivel general", "ISE, serie tendencia-ciclo", hoja=C11),
    "generacion_electrica": Columna("Generación neta de energía eléctrica", "ISE: generación neta de energía eléctrica",
                                    hoja=C12),
    "gas_centrales": Columna("Gas entregado neto de centrales eléctricas", "ISE: gas entregado a centrales eléctricas",
                             hoja=C12),
    "derivados_petroleo": Columna("Derivados de petróleo seleccionados", "ISE: derivados de petróleo seleccionados",
                                  hoja=C12),
}


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    df = leer_tabla_mensual(contenido, None, columnas)
    df = df[df["fecha"] >= PRIMER_PERIODO].reset_index(drop=True)
    return df[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, set(columnas),
                            rango_nivel=(0, 500), max_variacion=100)
    u = nuevo["ise"].dropna()
    if u.empty or not u.tail(24).between(50, 300).all():
        errores.append("ISE fuera de rango (¿cambió la base?).")
    return errores
