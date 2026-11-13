"""IPI pesquero: nivel general (original y desestacionalizado) y aperturas por sector de actividad.

Fuente: INDEC, Índice de producción industrial pesquero, base 2004=100 (serie desde enero de 2012).
Archivo: serie_ipi_pesquero.xlsx. Cuadros 1 (nivel general) y 2 (aperturas, serie original).

Es una serie muy estacional: la temporada de langostino y merluza concentra la captura en pocos meses, así que
la variación mensual solo se lee en la desestacionalizada y la interanual es la comparación útil.
"""

import pandas as pd

from pipeline.fuentes._indec import Columna, leer_tabla_mensual, validar_tabla

ID = "ipi_pesquero"
NOMBRE = "IPI pesquero: nivel general y aperturas (INDEC)"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipi_pesquero.xlsx"
PAGINA = "https://www.indec.gob.ar/Nivel4/Tema/3/6/40"
EXTENSION = "xlsx"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Índice base 2004=100"
PRIMER_PERIODO = "2012-01-01"
CALENDARIO = "Índice de producción industrial pesquero"

# Código ClaNAE -> (id, nombre). El archivo abre el nivel general en solo dos sectores.
APERTURAS = {"03.11": ("pesca_maritima", "Pesca marítima"), "03.20": ("acuicultura", "Acuicultura")}
SECTOR = "Sector de actividad económica"

COLUMNAS = {
    "original": Columna("Índice serie original | Nivel general", "IPI pesquero, serie original", hoja="Cuadro 1"),
    "original_var_ia": Columna("Índice serie original | Variación porcentual | respecto al mismo",
                               "IPI pesquero, serie original, var. % interanual",
                               tipo="variacion", base="original", rezago=12, hoja="Cuadro 1"),
    "desest": Columna("Índice serie desestacionalizada | Nivel general", "IPI pesquero, serie desestacionalizada (INDEC)",
                      hoja="Cuadro 1"),
    "desest_var_m": Columna("Índice serie desestacionalizada | Variación porcentual",
                            "IPI pesquero, desestacionalizado (INDEC), var. % mensual",
                            despues_de="desest", tipo="variacion", base="desest", rezago=1, hoja="Cuadro 1"),
}
COLUMNAS |= {cid: Columna(f"{SECTOR} | {codigo} | {nombre}", f"IPI pesquero: {nombre.lower()}, serie original",
                          hoja="Cuadro 2", despues_de="_ancla")
             for codigo, (cid, nombre) in APERTURAS.items()}
# La hoja 2 repite el nivel general antes de las aperturas: el ancla marca dónde empieza el bloque.
_ANCLA = {"_ancla": Columna(f"{SECTOR} | Índice serie original | Nivel general", "", hoja="Cuadro 2")}


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    df = leer_tabla_mensual(contenido, None, _ANCLA | columnas)
    return df[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    # La acuicultura empieza más tarde y es un índice chico con saltos grandes: se le permiten vacíos y un rango amplio.
    return validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, {"acuicultura"},
                         rango_nivel=(0, 3000), max_variacion=400, vacios_permitidos={"acuicultura"})
