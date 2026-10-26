"""Remuneración promedio de los asalariados registrados por provincia, desestacionalizada (X-13), pesos corrientes.

Se calcula desde data/remuneraciones_provincias.csv cada vez que cambia. La estacionalidad de esta serie es sobre
todo el aguinaldo: junio y diciembre pagan alrededor de 30% más que un mes normal ("por todo concepto"); el ajuste
lo reparte y deja la remuneración mensual comparable de un mes a otro.

Método (ver pipeline/desest.py): X-13 en logaritmos, con selección automática del modelo ARIMA y detección
automática de outliers en cada corrida (27 series: no se fijaron especificaciones una por una). Sin regresores de
días de la semana, feriados ni Pascua: el salario mensual no depende de cuántos días hábiles tiene el mes.
Se ajusta desde enero de 2007 (antes, el peso del aguinaldo y la inflación eran distintos). Al probarlo (datos hasta
junio de 2026) todas las series dieron M7 < 0,12 y Q < 0,2: estacionalidad muy estable y bien identificada.
"""

import pandas as pd

from pipeline.desest import PROGRAMA, Especificacion, desestacionalizar
from pipeline.fuentes import remuneraciones_provincias as rp
from pipeline.fuentes._indec import Columna

ID = "remuneraciones_provincias_desest"
NOMBRE = "Remuneración promedio de los asalariados registrados del sector privado, por provincia, desestacionalizada (X-13)"
DERIVADA_DE = rp.ID
URL = "data/remuneraciones_provincias.csv"
PAGINA = rp.PAGINA
FRECUENCIA = "M"
ORGANISMO = "Secretaría de Trabajo (OEDE, SIPA); desestacionalización propia"
UNIDAD = "Pesos corrientes"
CALENDARIO = ""
VERSION = "2026-10-26"
DESDE = "2007-01"
ESPECIFICACION = Especificacion(None, "log", None, dias_semana=False, feriados=False, pascua=False,
                                efectos_en_serie=False, origen="automática en cada corrida (modelo y outliers)")
SUFIJO = ""  # columnas de la serie de origen: <provincia><SUFIJO>


def columnas(nombre_base: str, sufijo: str) -> dict:
    cols = {}
    for cid, n in rp.PROVINCIAS.values():
        cols[f"{cid}{sufijo}"] = Columna("", f"{nombre_base}: {n}, desestacionalizada (propia, X-13)")
    cols[f"total{sufijo}_var_m"] = Columna("", f"{nombre_base}: total país, desestacionalizada, var. % mensual",
                                           tipo="variacion", base=f"total{sufijo}", rezago=1)
    return cols


COLUMNAS = columnas("Remuneración promedio, asalariados registrados del sector privado", SUFIJO)


def ajustar(original: pd.DataFrame, sufijo: str, desde: str, cols: dict, version: str) -> tuple[pd.DataFrame, dict]:
    idx = original["fecha"].dt.to_period("M")
    salida = pd.DataFrame({"fecha": original["fecha"]})
    detalle = {}
    for cid, _ in rp.PROVINCIAS.values():
        c = f"{cid}{sufijo}"
        serie = pd.Series(original[c].values / 1000, index=idx)[pd.Period(desde, "M"):]  # X-13 en miles de pesos
        sa, diag = desestacionalizar(c, serie, ESPECIFICACION)
        salida[c] = (sa.reindex(idx) * 1000).round(2).values
        diag["advertencias"] = list(dict.fromkeys(diag["advertencias"]))
        detalle[c] = {"especificacion": ESPECIFICACION.describir(), **diag}
    salida[f"total{sufijo}_var_m"] = salida[f"total{sufijo}"].pct_change() * 100
    return salida[["fecha", *cols]], {"desestacionalizacion": {"programa": PROGRAMA, "version": version,
                                                               "desde": desde, "series": detalle}}


def verificar(nuevo: pd.DataFrame, original: pd.DataFrame, sufijo: str, desde: str) -> list[str]:
    errores = []
    if len(nuevo) != len(original):
        errores.append(f"largo distinto al de la serie original ({len(nuevo)} vs {len(original)})")
    tramo = nuevo["fecha"] >= pd.Timestamp(desde)
    for cid, _ in rp.PROVINCIAS.values():
        c = f"{cid}{sufijo}"
        if nuevo.loc[tramo, c].isna().any():
            errores.append(f"{c}: hay meses sin valor desestacionalizado")
            continue
        r = (nuevo[c] / original[c])[tramo]
        if not r.between(0.6, 1.25).all():
            errores.append(f"{c}: la desestacionalizada se aleja demasiado de la original ({r.min():.2f} a {r.max():.2f})")
    return errores


def calcular(original: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    return ajustar(original, SUFIJO, DESDE, COLUMNAS, VERSION)


def validar(nuevo: pd.DataFrame, original: pd.DataFrame) -> list[str]:
    return verificar(nuevo, original, SUFIJO, DESDE)
