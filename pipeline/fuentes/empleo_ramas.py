"""Puestos de trabajo asalariados registrados del sector privado por rama de actividad: total del país y, para el
sector petrolero (extracción de petróleo y gas), las principales provincias. Trimestral.

Fuente: Secretaría de Trabajo, OEDE, en base al SIPA (ver _oede_ramas.py). El total del país de cada rama es la suma de
las provincias; las provincias en secreto estadístico ("s.d.") no suman, así que en ramas chicas el total queda apenas
por debajo del real. Se agrega la participación de cada rama en el empleo privado registrado total (suma de las ramas),
que sirve para ponderar los salarios por rama.
"""

from datetime import date

import pandas as pd

from pipeline.fuentes import _oede_ramas as o
from pipeline.fuentes._indec import Columna

ID = "empleo_ramas"
NOMBRE = "Puestos de trabajo asalariados registrados del sector privado, por rama de actividad (OEDE, SIPA)"
PAGINA = o.PAGINA
URL = o.RESPALDO["empleo"]
EXTENSION = "zip"
FRECUENCIA = "Q"
ORGANISMO = "Secretaría de Trabajo (OEDE, en base al SIPA)"
UNIDAD = "Puestos de trabajo"
PRIMER_PERIODO = "1996-01-01"
CALENDARIO = ""
GUARDAR_ORIGINAL = False

COLUMNAS = {"total": Columna("", "Puestos asalariados registrados privados: total del país (suma de las ramas)")}
for _r, (_c, _n) in o.RAMAS.items():
    COLUMNAS[_r] = Columna("", f"Puestos asalariados registrados privados: {_n}, total del país")
for _r, (_c, _n) in o.RAMAS.items():
    COLUMNAS[f"{_r}_part"] = Columna("", f"Participación en el empleo privado registrado: {_n}", unidad="%")
for _p in o.PROVINCIAS_PETROLERAS.values():
    COLUMNAS[f"petroleo_gas_{_p}"] = Columna("", f"Puestos asalariados registrados, extracción de petróleo y gas: {o.NOMBRE_PROV[_p]}")


def bajar(descargar, hoy: date):
    return o.bajar(descargar, hoy)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    _, E = o.leer_archivos(contenido)
    out = {}
    for r, (code, _) in o.RAMAS.items():
        out[r] = sum(E[p][code].fillna(0) for p in E if code in E[p])
    out["total"] = sum(out[r] for r in o.LETRAS)
    for r in o.RAMAS:
        out[f"{r}_part"] = out[r] / out["total"] * 100
    for prov, cid in o.PROVINCIAS_PETROLERAS.items():
        out[f"petroleo_gas_{cid}"] = E[prov].get("11")
    df = pd.DataFrame(out)
    df = df[(df.index >= pd.Period("1996Q1", "Q")) & (df["total"] > 0)]
    df.index = df.index.to_timestamp()
    df.index.name = "fecha"
    return df.reset_index()[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    esperado = pd.date_range(PRIMER_PERIODO, periods=len(nuevo), freq="QS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los trimestres no son consecutivos.")
    u = nuevo.iloc[-1]
    if not 4_000_000 < u["total"] < 9_000_000:
        errores.append(f"Total de puestos fuera de rango ({u['total']:.0f}).")
    if not 20_000 < u["petroleo_gas"] < 200_000:
        errores.append(f"Puestos de petróleo y gas fuera de rango ({u['petroleo_gas']:.0f}).")
    return errores
