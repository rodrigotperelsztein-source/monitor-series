"""Remuneración promedio de los asalariados registrados del sector privado por rama de actividad: total del país y,
para el sector petrolero (extracción de petróleo y gas), las principales provincias. Pesos corrientes, mensual.

Fuente: Secretaría de Trabajo, OEDE, en base al SIPA (ver _oede_ramas.py). El OEDE publica la remuneración por rama solo
por provincia; el total del país de cada rama es el promedio de las provincias ponderado por los puestos de trabajo de
esa rama en cada provincia (planilla de empleo trimestral; los meses posteriores al último trimestre publicado usan
ese último trimestre). Las provincias en secreto estadístico quedan afuera, así que el promedio nacional puede diferir
apenas del oficial: para petróleo y gas, el promedio anual calculado así difiere menos de 1,5% del que publica el OEDE
(cuadro anual a dos dígitos) en 2015-2025.

"Por todo concepto": incluye aguinaldo (junio y diciembre) y pagos extraordinarios.
"""

from datetime import date

import pandas as pd

from pipeline.fuentes import _oede_ramas as o
from pipeline.fuentes._indec import Columna

ID = "salarios_ramas"
NOMBRE = "Remuneración promedio de los asalariados registrados del sector privado, por rama de actividad (OEDE, SIPA)"
PAGINA = o.PAGINA
URL = o.RESPALDO["salarios"]
EXTENSION = "zip"
FRECUENCIA = "M"
ORGANISMO = "Secretaría de Trabajo (OEDE, en base al SIPA)"
UNIDAD = "Pesos corrientes por mes"
PRIMER_PERIODO = "1996-01-01"  # el empleo por provincia y rama arranca en el primer trimestre de 1996
CALENDARIO = ""
GUARDAR_ORIGINAL = False

COLUMNAS = {"total": Columna("", "Remuneración promedio, asalariados registrados privados: total del país (promedio de las ramas)")}
for _r, (_c, _n) in o.RAMAS.items():
    COLUMNAS[_r] = Columna("", f"Remuneración promedio, asalariados registrados privados: {_n}, total del país")
for _p in o.PROVINCIAS_PETROLERAS.values():
    COLUMNAS[f"petroleo_gas_{_p}"] = Columna("", f"Remuneración promedio, extracción de petróleo y gas: {o.NOMBRE_PROV[_p]}")


def bajar(descargar, hoy: date):
    return o.bajar(descargar, hoy)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    S, E = o.leer_archivos(contenido)
    out = {}
    pesos = {}
    for r, (code, _) in o.RAMAS.items():
        out[r], pesos[r] = o.nacional(S, E, code)
    # Total: promedio de las ramas (letras) ponderado por su empleo
    num = sum(out[r].fillna(0) * pesos[r] for r in o.LETRAS)
    den = sum(pesos[r].where(out[r].notna(), 0) for r in o.LETRAS)
    out["total"] = num / den
    for prov, cid in o.PROVINCIAS_PETROLERAS.items():
        out[f"petroleo_gas_{cid}"] = S[prov].get("11")
    df = pd.DataFrame(out)
    df = df[df.index >= pd.Period(PRIMER_PERIODO[:7], "M")]
    df.index = df.index.to_timestamp()
    df.index.name = "fecha"
    return df.reset_index()[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    esperado = pd.date_range(PRIMER_PERIODO, periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los meses no son consecutivos.")
    u = nuevo.iloc[-1]
    if u[["total", "petroleo_gas", "industria", "comercio"]].isna().any():
        errores.append("Falta el último mes del total o de las ramas principales.")
    elif not (u["comercio"] < u["total"] < u["petroleo_gas"]):
        errores.append("Orden de salarios inesperado en el último mes (comercio < total < petróleo).")
    if anterior is not None and len(anterior):
        comunes = nuevo.merge(anterior, on="fecha", suffixes=("", "_ant"))
        cambio = (comunes["total"] / comunes["total_ant"] - 1).abs() > 0.05
        if cambio.sum() > 12:
            errores.append(f"El total cambió más de 5% en {int(cambio.sum())} meses ya publicados.")
    return errores
