"""Accesos a internet (INDEC): total del país por tipo de acceso (móviles y fijos) y por categoría de usuario
(residenciales y organizaciones), en cantidad de accesos.

Archivo: serie22_accesos_internet.xlsx, cuadro 1. La serie mensual empieza en enero de 2022.
"""

import pandas as pd

from pipeline.fuentes._indec import Columna, leer_tabla_mensual, validar_tabla

ID = "accesos_internet"
NOMBRE = "Accesos a internet: móviles, fijos y por categoría de usuario (INDEC)"
URL = "https://www.indec.gob.ar/ftp/cuadros/sociedad/serie22_accesos_internet.xlsx"
PAGINA = "https://www.indec.gob.ar/Nivel4/Tema/4/26/153"
EXTENSION = "xlsx"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Accesos"
PRIMER_PERIODO = "2022-01-01"
CALENDARIO = "Accesos a internet"
MAX_DIAS_SIN_NOVEDAD = 160  # sale con unos cuatro meses de rezago

C1 = "Cuadro 1"
COLUMNAS = {
    "total": Columna("Total", "Accesos a internet, total", hoja=C1),
    "total_var_ia": Columna("Variación interanual", "Accesos a internet, var. % interanual",
                            despues_de="total", tipo="variacion", base="total", rezago=12, hoja=C1),
    "moviles": Columna("Tipo de acceso | Móviles", "Accesos a internet móviles", hoja=C1),
    "fijos": Columna("Tipo de acceso | Fijos", "Accesos a internet fijos", hoja=C1),
    "residenciales": Columna("Categoría | Residenciales", "Accesos a internet residenciales", hoja=C1),
    "organizaciones": Columna("Categoría | Organizaciones", "Accesos a internet de organizaciones", hoja=C1),
}


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    df = leer_tabla_mensual(contenido, None, columnas)
    return df[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, set(columnas),
                            rango_nivel=(0, 100_000_000), max_variacion=50)
    u = nuevo.dropna(subset=["total", "moviles", "fijos"]).tail(24)
    if ((u["moviles"] + u["fijos"] - u["total"]).abs() > 1).any():
        errores.append("Móviles más fijos no da el total.")
    return errores
