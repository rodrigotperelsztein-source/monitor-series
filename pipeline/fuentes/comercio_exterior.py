"""Comercio exterior de bienes (INDEC, ICA): exportaciones por rubro y destino, importaciones por uso económico y
origen, y saldo. Millones de dólares por mes (exportaciones FOB, importaciones CIF).

Fuente: Catálogo API-INDEC, tablas comercio_exterior_exportacion_bienes y comercio_exterior_importacion_bienes (una fila
por mes, rubro o uso económico, subrubro o grupo y país, desde 1986). Se suman por mes. La corrida diaria baja los
últimos años y conserva los meses anteriores ya guardados (INDEC revisa sobre todo los meses recientes).
Rubros y usos económicos: los de la difusión oficial del ICA, que reparte entre ellos las operaciones bajo secreto
estadístico (la API las deja sin rubro, con código 9). Salen de la serie 74.3 del Ministerio de Economía en datos.gob.ar
(intercambio-comercial-argentino-mensual.csv, desde 1992), que replica los cuadros del ICA. En 2016-2017 y 2022-2023
el total de la API (con revisiones posteriores) difiere hasta 2% del de esos cuadros, así que ahí los rubros no suman
exactamente el total.
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
URL_RUBROS = "https://infra.datos.gob.ar/catalog/sspm/dataset/74/distribution/74.3/download/intercambio-comercial-argentino-mensual.csv"
CSV_RUBROS = {"expo_primarios": "ica_exportacion_productos_primarios", "expo_moa": "ica_exportacion_manufacturas_origen_agropecuario",
              "expo_moi": "ica_exportacion_manufacturas_origen_industrial", "expo_combustibles": "ica_exportacion_combustible_energia",
              "impo_capital": "ica_importaciones_bienes_capital", "impo_intermedios": "ica_importaciones_bienes_intermedios",
              "impo_combustibles": "ica_importaciones_combustibles_lubricantes",
              "impo_piezas": "ica_importaciones_piezas_accesorios_bienes_capital", "impo_consumo": "ica_importaciones_bienes_consumo",
              "impo_vehiculos": "ica_importaciones_vehiculos_automotores_pasajeros", "impo_resto": "ica_importaciones_resto"}

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
COLUMNAS["saldo"] = Columna("", "Saldo comercial (exportaciones - importaciones)")


def bajar(descargar, hoy) -> tuple[str, bytes]:
    api.exigir(*TABLAS)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for t in TABLAS:
            z.writestr(f"{t}.json", api.contenido(t)[1])
        z.writestr("rubros.csv", descargar(URL_RUBROS, minimo=20_000))
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
    for k, paises in PAISES.items():
        out[f"expo_{k}"] = ex[ex["pais_cod"].isin(paises)].groupby("fecha")["v"].sum()
    out["importaciones"] = im.groupby("fecha")["v"].sum()
    for k, paises in PAISES.items():
        out[f"impo_{k}"] = im[im["pais_cod"].isin(paises)].groupby("fecha")["v"].sum()
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        rub = pd.read_csv(z.open("rubros.csv"), parse_dates=["indice_tiempo"]).set_index("indice_tiempo")
    out = out.reindex(out.index.union(rub.index[rub.index >= "1992-01-01"]))
    for k, c in CSV_RUBROS.items():
        out[k] = rub[c].reindex(out.index)
    # Control: el total del CSV y el de la API son el mismo dato.
    tot = rub["ica_expo_totales"].reindex(out.index)
    dif = (tot - out["exportaciones"]).abs().dropna()
    if len(dif) and dif.max() > 1:
        print(f"  aviso: el total exportado del CSV difiere del de la API hasta {dif.max():.1f} millones de USD")
    out["saldo"] = out["exportaciones"] - out["importaciones"]
    out.index.name = "fecha"
    return out.sort_index().reset_index()[["fecha", *columnas]]


def combinar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None) -> pd.DataFrame:
    """La corrida diaria baja de la API solo los últimos años (los rubros y usos, toda la serie): manda lo nuevo y los
    huecos se completan con lo ya guardado."""
    if anterior is None or not len(anterior):
        return nuevo
    n, a = nuevo.set_index("fecha"), anterior.set_index("fecha")
    out = n.combine_first(a[[c for c in n.columns if c in a.columns]])
    out["saldo"] = out["exportaciones"] - out["importaciones"]
    return out.sort_index().reset_index()[list(nuevo.columns)]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los meses no son consecutivos (¿falta bajar la historia completa?).")
    for partes, total in (([f"expo_{k}" for k in RUBROS], "exportaciones"), ([f"impo_{k}" for k in USOS], "importaciones")):
        d = nuevo.dropna(subset=partes + [total])
        dif = (d[partes].sum(axis=1) - d[total]).abs()
        # En 2016-2017 y 2022-2023 el total de la API (revisado) difiere hasta 2% del de los cuadros del ICA.
        if (dif.tail(24) > 1).any() or (dif / d[total] > 0.03).any():
            errores.append(f"Los rubros o usos no suman {total} (diferencia máxima {dif.max():.1f} millones de USD).")
        if nuevo[partes].iloc[:-2].loc[nuevo["fecha"] >= "1992-01-01"].isna().any().any():
            errores.append(f"Faltan rubros o usos de {total} antes de los dos últimos meses.")
    if not nuevo["exportaciones"].between(100, 20_000).all():
        errores.append("Exportaciones mensuales fuera de rango (100 a 20.000 millones de USD).")
    if (pd.Timestamp.today() - nuevo["fecha"].max()).days > 75:
        errores.append("El último mes tiene más de dos meses de atraso.")
    return errores
