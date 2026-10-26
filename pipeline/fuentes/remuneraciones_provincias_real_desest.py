"""Remuneración promedio real de los asalariados registrados por provincia, desestacionalizada (X-13).

Se calcula desde data/remuneraciones_provincias_real.csv (a precios del último IPC publicado) cada vez que cambia,
con el mismo método que remuneraciones_provincias_desest (X-13 en logaritmos, modelo y outliers automáticos, sin
efectos de calendario), desde diciembre de 2016, el primer mes de la serie real. Como la serie real se reescala
cuando sale un IPC nuevo, la desestacionalizada también.
"""

import pandas as pd

from pipeline.fuentes import remuneraciones_provincias_desest as base
from pipeline.fuentes import remuneraciones_provincias_real as rr

ID = "remuneraciones_provincias_real_desest"
NOMBRE = "Remuneración promedio real de los asalariados registrados del sector privado, por provincia, desestacionalizada (X-13)"
DERIVADA_DE = rr.ID
URL = "data/remuneraciones_provincias_real.csv"
PAGINA = rr.PAGINA
FRECUENCIA = "M"
ORGANISMO = "Secretaría de Trabajo (OEDE, SIPA) e INDEC; deflactación y desestacionalización propias"
UNIDAD = "Pesos del último IPC publicado"
CALENDARIO = ""
VERSION = "2026-10-26"
DESDE = "2016-12"
SUFIJO = "_real"
COLUMNAS = base.columnas("Remuneración promedio real (a precios del último IPC)", SUFIJO)


def calcular(original: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    return base.ajustar(original, SUFIJO, DESDE, COLUMNAS, VERSION)


def validar(nuevo: pd.DataFrame, original: pd.DataFrame) -> list[str]:
    return base.verificar(nuevo, original, SUFIJO, DESDE)
