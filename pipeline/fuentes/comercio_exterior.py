"""Comercio exterior de bienes (INDEC, ICA): exportaciones por rubro y destino, importaciones por uso económico y
origen, y saldo. Millones de dólares por mes (exportaciones FOB, importaciones CIF).

Fuente: Catálogo API-INDEC, tablas comercio_exterior_exportacion_bienes y comercio_exterior_importacion_bienes (una fila
por mes, rubro o uso económico, subrubro o grupo y país, desde 1986). Se suman por mes. La corrida diaria baja los
últimos años y conserva los meses anteriores ya guardados (INDEC revisa sobre todo los meses recientes).
Rubros: primarios, manufacturas de origen agropecuario (MOA), manufacturas de origen industrial (MOI), combustibles y
energía. Usos económicos: bienes de capital, intermedios, combustibles y lubricantes, piezas y accesorios para bienes de
capital, bienes de consumo, vehículos de pasajeros y resto. Unión Europea: los 27 países actuales para toda la serie.
"""

import io
import json
import zipfile

import pandas as pd

from pipeline.fuentes import _api_indec as api
from pipeline.fuentes._indec import Columna

ID = "comercio_exterior"
NOMBRE = "Comercio exterior de bienes: exportaciones, importaciones y saldo (INDEC)"
TABLAS = ("comercio_exterior_exportacion_bienes", "comercio_exterior_importacion_bienes")
TABLA_API = TABLAS  # las dos tablas que necesita
URL = "https://api.indec.gob.ar/v1/comercio_exterior_exportacion_bienes"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-2-40"
EXTENSION = "zip"
FRECUENCIA = "M"
ORGANISMO = "INDEC (Catálogo API-INDEC)"
UNIDAD = "Millones de USD"
PRIMER_PERIODO = "1986-01-01"
CALENDARIO = "Intercambio comercial argentino"
GUARDAR_ORIGINAL = False

UE = set("AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE".split())
PAISES = {"brasil": {"BR"}, "china": {"CN"}, "eeuu": {"US"}, "ue": UE}
RUBROS = {"primarios": ("1", "Productos primarios"), "moa": ("2", "Manufacturas de origen agropecuario (MOA)"),
          "moi": ("3", "Manufacturas de origen industrial (MOI)"), "combustibles": ("4", "Combustibles y energía")}
USOS = {"capital": ("1", "Bienes de capital"), "intermedios": ("2", "Bienes intermedios"),
        "combustibles": ("3", "Combustibles y lubricantes"), "piezas": ("4", "Piezas y accesorios para bienes de capital"),
        "consumo": ("5", "Bienes de consumo"), "vehiculos": ("6", "Vehículos automotores de pasajeros"), "resto": ("7", "Resto")}
NOMBRE_PAIS = {"brasil": "Brasil", "china": "China", "eeuu": "Estados Unidos", "ue": "Unión Europea"}

COLUMNAS = {"exportaciones": Columna("", "Exportaciones de bienes (FOB)")}
COLUMNAS |= {f"expo_{k}": Columna("", f"Exportaciones: {n}") for k, (_, n) in RUBROS.items()}
COLUMNAS |= {f"expo_{k}": Columna("", f"Exportaciones a {NOMBRE_PAIS[k]}") for k in PAISES}
COLUMNAS["importaciones"] = Columna("", "Importaciones de bienes (CIF)")
COLUMNAS |= {f"impo_{k}": Columna("", f"Importaciones: {n}") for k, (_, n) in USOS.items()}
COLUMNAS |= {f"impo_{k}": Columna("", f"Importaciones desde {NOMBRE_PAIS[k]}") for k in PAISES}
# Código 9: operaciones bajo secreto estadístico, que el INDEC no abre por rubro ni por uso (sí entran en el total).
COLUMNAS["expo_sin_rubro"] = Columna("", "Exportaciones bajo secreto estadístico, sin rubro informado")
COLUMNAS["impo_sin_uso"] = Columna("", "Importaciones bajo secreto estadístico, sin uso económico informado")
COLUMNAS["saldo"] = Columna("", "Saldo comercial (exportaciones - importaciones)")


def bajar(descargar, hoy) -> tuple[str, bytes]:
    faltan = [t for t in TABLAS if not api.disponible(t)]
    if faltan:
        raise ValueError(f"No están las tablas de la API del INDEC {faltan} (¿token vencido o API caída?).")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for t in TABLAS:
            z.writestr(f"{t}.json", api.contenido(t)[1])
    return URL, buf.getvalue()


def _tabla(z, t: str) -> pd.DataFrame:
    df = api.filas(z.read(f"{t}.json"))
    if df.empty:
        raise ValueError(f"{t}: vino vacía.")
    return df


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        ex, im = _tabla(z, TABLAS[0]), _tabla(z, TABLAS[1])
    ex["v"] = pd.to_numeric(ex["valor_FOB"], errors="coerce") / 1e6
    im["v"] = pd.to_numeric(im["valor_CIF"], errors="coerce") / 1e6
    out = pd.DataFrame({"exportaciones": ex.groupby("fecha")["v"].sum()})
    for k, (cod, _) in RUBROS.items():
        out[f"expo_{k}"] = ex[ex["rubro_cod"].astype(str) == cod].groupby("fecha")["v"].sum()
    for k, paises in PAISES.items():
        out[f"expo_{k}"] = ex[ex["pais_cod"].isin(paises)].groupby("fecha")["v"].sum()
    out["importaciones"] = im.groupby("fecha")["v"].sum()
    for k, (cod, _) in USOS.items():
        out[f"impo_{k}"] = im[im["uso_economico_cod"].astype(str) == cod].groupby("fecha")["v"].sum()
    for k, paises in PAISES.items():
        out[f"impo_{k}"] = im[im["pais_cod"].isin(paises)].groupby("fecha")["v"].sum()
    out["expo_sin_rubro"] = ex[ex["rubro_cod"].astype(str) == "9"].groupby("fecha")["v"].sum()
    out["impo_sin_uso"] = im[im["uso_economico_cod"].astype(str) == "9"].groupby("fecha")["v"].sum()
    out[["expo_sin_rubro", "impo_sin_uso"]] = out[["expo_sin_rubro", "impo_sin_uso"]].fillna(0)
    otros_r = sorted(set(ex["rubro_cod"].astype(str)) - {c for c, _ in RUBROS.values()} - {"9"})
    otros_u = sorted(set(im["uso_economico_cod"].astype(str)) - {c for c, _ in USOS.values()} - {"9"})
    if otros_r or otros_u:
        print(f"  códigos fuera de la lista: rubros {otros_r[:10]}, usos {otros_u[:10]}")
    out["saldo"] = out["exportaciones"] - out["importaciones"]
    out.index.name = "fecha"
    return out.sort_index().reset_index()[["fecha", *columnas]]


def combinar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None) -> pd.DataFrame:
    """La corrida diaria baja solo los últimos años: se conservan los meses anteriores ya guardados."""
    if anterior is None or not len(anterior):
        return nuevo
    viejos = anterior[anterior["fecha"] < nuevo["fecha"].min()]
    return pd.concat([viejos, nuevo]).sort_values("fecha").reset_index(drop=True)[list(nuevo.columns)]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los meses no son consecutivos (¿falta bajar la historia completa?).")
    for partes, total in (([f"expo_{k}" for k in RUBROS] + ["expo_sin_rubro"], "exportaciones"),
                          ([f"impo_{k}" for k in USOS] + ["impo_sin_uso"], "importaciones")):
        dif = (nuevo[partes].sum(axis=1) - nuevo[total]).abs()
        if (dif > 0.5).any():
            errores.append(f"Las aperturas no suman {total} (diferencia máxima {dif.max():.1f} millones de USD).")
    if not nuevo["exportaciones"].between(100, 20_000).all():
        errores.append("Exportaciones mensuales fuera de rango (100 a 20.000 millones de USD).")
    if (pd.Timestamp.today() - nuevo["fecha"].max()).days > 75:
        errores.append("El último mes tiene más de dos meses de atraso.")
    return errores
