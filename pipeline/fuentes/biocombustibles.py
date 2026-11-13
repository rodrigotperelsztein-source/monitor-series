"""Biodiésel y bioetanol (INDEC): producción, despachos al mercado interno y exportaciones.

Archivo: sh_indicadores_energeticos.xls, cuadros 3.1 (biodiésel, en toneladas) y 3.2 (bioetanol, en m³, abierto
entre caña de azúcar y maíz).

El biodiésel es casi todo exportación y el bioetanol casi todo mercado interno, porque se corta con las naftas:
son las dos caras del corte obligatorio y de los cupos.
"""

import pandas as pd

from pipeline.fuentes._indec import Columna, leer_tabla_mensual, validar_tabla

ID = "biocombustibles"
NOMBRE = "Biodiésel y bioetanol: producción, mercado interno y exportaciones (INDEC)"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/sh_indicadores_energeticos.xls"
PAGINA = "https://www.indec.gob.ar/Nivel4/Tema/3/36/145"
EXTENSION = "xls"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Toneladas (biodiésel) y m³ (bioetanol)"
PRIMER_PERIODO = "2009-11-01"
CALENDARIO = "Indicadores del sector energético"
MAX_DIAS_SIN_NOVEDAD = 160  # sale con unos cuatro meses de rezago

C31, C32 = "Cuadro 3.1", "Cuadro 3.2"

COLUMNAS = {
    "biodiesel_produccion": Columna("Producción", "Biodiésel: producción", unidad="Toneladas", hoja=C31),
    "biodiesel_interno": Columna("Despachos al mercado interno", "Biodiésel: despachos al mercado interno",
                                 unidad="Toneladas", hoja=C31),
    "biodiesel_exportaciones": Columna("Exportaciones", "Biodiésel: exportaciones", unidad="Toneladas", hoja=C31),
    "bioetanol_produccion": Columna("Producción | Total", "Bioetanol: producción total", unidad="m³", hoja=C32),
    "bioetanol_cana": Columna("Producción | Bioetanol de caña", "Bioetanol: producción de caña", unidad="m³", hoja=C32),
    "bioetanol_maiz": Columna("Producción | Bioetanol de maíz", "Bioetanol: producción de maíz", unidad="m³", hoja=C32),
    "bioetanol_interno": Columna("Despachos al mercado interno", "Bioetanol: despachos al mercado interno",
                                 unidad="m³", hoja=C32),
}
# El bioetanol de maíz arranca en 2012 y algunos meses del biodiésel quedan vacíos en el archivo.
_PARCIALES = set(COLUMNAS)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    df = leer_tabla_mensual(contenido, None, columnas)
    return df[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, set(columnas),
                            rango_nivel=(-1, 1_500_000), max_variacion=500, vacios_permitidos=_PARCIALES)
    u = nuevo["bioetanol_produccion"].dropna()
    if u.empty or not u.tail(24).between(20_000, 200_000).all():
        errores.append("Producción de bioetanol fuera de rango (¿cambió la unidad?).")
    return errores
