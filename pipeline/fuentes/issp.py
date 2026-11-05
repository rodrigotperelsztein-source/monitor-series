"""Indicador sintético de servicios públicos (ISSP): nivel general y componentes, base 2004=100 (INDEC).

Archivo: sh_issp_<año>.xls. Cuadros 1 (nivel general original, desestacionalizado y tendencia) y 2 (componentes, serie
original).
"""

from datetime import date

import pandas as pd

from pipeline.fuentes._indec import Columna, leer_tabla_mensual, validar_tabla

ID = "issp"
NOMBRE = "Indicador sintético de servicios públicos (ISSP, INDEC)"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/sh_issp_{anio}.xls"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-11-53"
EXTENSION = "xls"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Índice base 2004=100"
PRIMER_PERIODO = "2012-01-01"
CALENDARIO = "Indicador sintético de servicios públicos"

COMP = {"electricidad_gas_agua": "Electricidad, gas y agua", "residuos": "Recolección de residuos",
        "transporte_pasajeros": "Transporte de pasajeros", "transporte_carga": "Transporte de carga", "peajes": "Peajes",
        "correo": "Servicios de correo", "telefonia": "Telefonía"}
COLUMNAS = {
    "nivel_general": Columna("Índice serie original", "ISSP, nivel general, serie original", hoja="1"),
    "nivel_general_var_ia": Columna("Variación porcentual respecto a mismo mes", "ISSP, var. % interanual",
                                    tipo="variacion", base="nivel_general", rezago=12, hoja="1"),
    "desest": Columna("Índice serie desestacionalizada", "ISSP, serie desestacionalizada", hoja="1"),
    "desest_var_m": Columna("Variación porcentual respecto al mes anterior", "ISSP, desestacionalizado, var. % mensual",
                            despues_de="desest", tipo="variacion", base="desest", rezago=1, hoja="1"),
}
COLUMNAS |= {k: Columna(v, f"ISSP: {v.lower()}, serie original", hoja="2", despues_de="_ancla") for k, v in COMP.items()}
# La hoja 2 repite los componentes (índices y luego variaciones %): el ancla marca el bloque de índices.
_ANCLA = {"_ancla": Columna("ISSP nivel general | Números índice", "", hoja="2")}


def urls(hoy: date) -> list[str]:
    return [URL.format(anio=hoy.year), URL.format(anio=hoy.year - 1)]


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    df = leer_tabla_mensual(contenido, None, _ANCLA | columnas)
    return df[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    return validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, set(COMP), rango_nivel=(0, 5000), max_variacion=1000)
