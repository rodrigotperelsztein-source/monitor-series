"""Ventas al mercado de gasoil y naftas grado 2 y grado 3, por empresa, en m³ por mes.

Fuente: Secretaría de Energía, "Refinación y comercialización de petróleo, gas y derivados
(tablas dinámicas)", tabla "Ventas al mercado" (sistema SESCO, Resolución 1104/2004). Hay dos
archivos: TD_ventas_mercado_2010_2019.zip (cerrado) y TD_ventas_mercado.zip (2020 en adelante,
se actualiza una vez por mes).

Cada archivo es un Excel con una tabla dinámica conectada a la base de datos interna de la
Secretaría (tabla sesconew.down_ventas), que no es accesible desde afuera. La tabla guarda una
copia de todos los registros (año, mes, empresa, canal de venta, producto, unidad, provincia,
país, cantidad): se leen esos registros (ver _pivot.py), no la vista de la tabla.

Series, para cada producto (gasoil G2, gasoil G3, nafta G2, nafta G3 y los totales de gasoil y de
naftas) y cada empresa (las principales, el resto y el total del mercado):
  - <producto>_<empresa>: todas las ventas al mercado;
  - <producto>_<empresa>_sin_usinas_bunker: sin las ventas a usinas eléctricas ni el bunker
    internacional (combustible para buques en viajes al exterior).
Incluyen las ventas a otras empresas del sector ("Otras Empresas"): al sumar empresas, ese
volumen puede aparecer dos veces (lo vende una y lo revende otra).

Empresas (se juntan las razones sociales de una misma red):
  - axion: ESSO S.A.P.A. hasta 2018 y Pan American Energy después (compró Esso en 2018);
  - shell: Shell C.A.P.S.A. (red Shell, operada por Raízen desde 2018);
  - trafigura: Trafigura Argentina (red Puma);
  - delta_gulf: DeltaPatagonia y Gulf Oil Argentina (red Gulf);
  - las de otras redes, que cambiaron de dueño o cerraron (Petrobras, Oil Combustibles, etc.),
    van en "resto".

El archivo 2010-2019 se baja solo si falta la historia; los meses anteriores a 2020 salen de
data/ventas_combustibles.csv.
"""

import io
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

from pipeline.fuentes import _pivot
from pipeline.fuentes._indec import Columna

ID = "ventas_combustibles"
NOMBRE = "Ventas al mercado de gasoil y naftas (grados 2 y 3) por empresa"
PAGINA = ("https://www.argentina.gob.ar/economia/energia/hidrocarburos/"
          "refinacion-y-comercializacion-de-petroleo-gas-y-derivados-tablas-dinamicas")
_BASE = ("https://www.energia.gob.ar/contenidos/archivos/Reorganizacion/informacion_del_mercado/"
         "mercado_hidrocarburos/tablas_dinamicas/dowstream/individuales/")
URL = _BASE + "TD_ventas_mercado.zip"
URL_HISTORIA = _BASE + "TD_ventas_mercado_2010_2019.zip"
EXTENSION = "zip"
FRECUENCIA = "M"
ORGANISMO = "Secretaría de Energía"
UNIDAD = "m³"
PRIMER_PERIODO = "2010-01-01"
CALENDARIO = ""
# Se publica una vez por mes, hacia fin de mes: se revisa del 20 al último día.
DIAS_DEL_MES = range(20, 32)
GUARDAR_ORIGINAL = False  # 6 MB por mes (y 17 MB el histórico); se puede volver a bajar

HISTORIA = Path(__file__).resolve().parents[2] / "data" / f"{ID}.csv"

PRODUCTOS = {  # nombre en la base -> id
    "Gasoil Grado 2 (Común)": "gasoil_g2",
    "Gasoil Grado 3 (Ultra)": "gasoil_g3",
    "Nafta Grado 2 (Súper)": "nafta_g2",
    "Nafta Grado 3 (Ultra)": "nafta_g3",
}
GRUPOS = {"gasoil": ("gasoil_g2", "gasoil_g3"), "naftas": ("nafta_g2", "nafta_g3")}
NOMBRE_PRODUCTO = {"gasoil_g2": "gasoil grado 2 (común)", "gasoil_g3": "gasoil grado 3 (ultra)",
                   "nafta_g2": "nafta grado 2 (súper)", "nafta_g3": "nafta grado 3 (ultra)",
                   "gasoil": "gasoil grados 2 y 3", "naftas": "naftas grados 2 y 3"}

EMPRESAS = {  # razón social en la base -> id
    "YPF S.A.": "ypf",
    "SHELL C.A.P.S.A.": "shell",
    "ESSO S.A.P.A.": "axion",
    "PAN AMERICAN ENERGY (SUCURSAL ARGENTINA) LLC": "axion",
    "PAN AMERICAN ENERGY SL": "axion",
    "Trafigura Argentina S.A.": "trafigura",
    "Destilería Argentina de Petróleo S.A.": "dapsa",
    "DeltaPatagonia S.A.": "delta_gulf",
    "GULF OIL ARGENTINA S.A.": "delta_gulf",
    "REFINERIA DEL NORTE  S.A.( REFINOR)": "refinor",
}
NOMBRE_EMPRESA = {"ypf": "YPF", "shell": "Shell (Raízen)", "axion": "Axion (Esso / Pan American)",
                  "trafigura": "Trafigura (Puma)", "dapsa": "DAPSA", "delta_gulf": "Delta Patagonia / Gulf",
                  "refinor": "Refinor", "resto": "resto de las empresas", "total": "total del mercado"}
EXCLUIDOS = {"Usinas Eléctricas", "Bunker Internacional"}

COLUMNAS = {}
for _p in [*PRODUCTOS.values(), *GRUPOS]:
    for _e in NOMBRE_EMPRESA:
        _n = f"Ventas de {NOMBRE_PRODUCTO[_p]}, {NOMBRE_EMPRESA[_e]}"
        COLUMNAS[f"{_p}_{_e}"] = Columna("", _n)
        COLUMNAS[f"{_p}_{_e}_sin_usinas_bunker"] = Columna("", f"{_n}, sin usinas eléctricas ni bunker internacional")


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    archivos = {"actual.zip": descargar(URL, minimo=1_000_000)}
    urls = [URL]
    if not HISTORIA.exists():
        archivos["historia.zip"] = descargar(URL_HISTORIA, minimo=1_000_000)
        urls.append(URL_HISTORIA)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for nombre, contenido in archivos.items():
            z.writestr(nombre, contenido)
    return " ".join(urls), buf.getvalue()


def _xlsx(zip_bytes: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        nombres = [n for n in z.namelist() if n.lower().endswith(".xlsx")]
        if len(nombres) != 1:
            raise ValueError(f"Se esperaba un Excel en el zip y hay {nombres}.")
        return z.read(nombres[0])


def _sumas(xlsx: bytes) -> pd.DataFrame:
    sumas, _ = _pivot.sumar(xlsx, ["anio", "mes", "empresa", "subtipodecomercializacion", "producto", "unidad"],
                            "cantidad", prefiltro=("producto", set(PRODUCTOS)))
    d = pd.DataFrame([(*k, v) for k, v in sumas.items()],
                     columns=["anio", "mes", "empresa", "subtipo", "producto", "unidad", "cantidad"])
    unidades = set(d["unidad"])
    if unidades != {"(m3)"}:
        raise ValueError(f"Unidades inesperadas para gasoil y naftas: {unidades}")
    d["fecha"] = pd.to_datetime(dict(year=d["anio"].astype(float).astype(int), month=d["mes"].astype(float).astype(int), day=1))
    return d


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        partes = [_sumas(_xlsx(z.read(n))) for n in sorted(z.namelist())]
    d = pd.concat(partes, ignore_index=True)
    d["prod"] = d["producto"].map(PRODUCTOS)
    d["emp"] = d["empresa"].map(EMPRESAS).fillna("resto")
    d["sin"] = ~d["subtipo"].isin(EXCLUIDOS)
    indice = pd.Index(sorted(d["fecha"].unique()), name="fecha")
    cols = {}
    for sufijo, filas in (("", d), ("_sin_usinas_bunker", d[d["sin"]])):
        t = filas.pivot_table(index="fecha", columns=["prod", "emp"], values="cantidad", aggfunc="sum").reindex(indice)
        for p in PRODUCTOS.values():
            for e in NOMBRE_EMPRESA:
                if e == "total":
                    serie = t[p].sum(axis=1) if p in t.columns.get_level_values(0) else pd.Series(0.0, index=indice)
                else:
                    serie = t[(p, e)].fillna(0) if (p, e) in t.columns else pd.Series(0.0, index=indice)
                cols[f"{p}_{e}{sufijo}"] = serie
        for g, partes_g in GRUPOS.items():
            for e in NOMBRE_EMPRESA:
                cols[f"{g}_{e}{sufijo}"] = sum(cols[f"{p}_{e}{sufijo}"] for p in partes_g)
    out = pd.DataFrame(cols, index=indice)
    out = out.reindex(columns=list(columnas)).fillna(0).round(3)
    return out.reset_index()


def combinar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None) -> pd.DataFrame:
    """El archivo actual reemplaza sus meses; los anteriores (2010-2019) salen de la historia."""
    if anterior is None:
        return nuevo
    viejo = anterior[anterior["fecha"] < nuevo["fecha"].min()]
    return pd.concat([viejo, nuevo]).sort_values("fecha").reset_index(drop=True)[list(nuevo.columns)]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)[:5]}…"]
    esperado = pd.date_range(PRIMER_PERIODO, periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append(f"Los meses no son consecutivos desde {PRIMER_PERIODO}.")
    for p in [*PRODUCTOS.values(), *GRUPOS]:
        for suf in ("", "_sin_usinas_bunker"):
            partes = sum(nuevo[f"{p}_{e}{suf}"] for e in NOMBRE_EMPRESA if e != "total")
            if ((partes - nuevo[f"{p}_total{suf}"]).abs() > 1).any():
                errores.append(f"{p}{suf}: las empresas no suman el total.")
        if (nuevo[f"{p}_total_sin_usinas_bunker"] > nuevo[f"{p}_total"] + 1).any():
            errores.append(f"{p}: el subtotal sin usinas ni bunker supera al total.")
        if (nuevo[f"{p}_total"] <= 0).any():
            errores.append(f"{p}: hay meses sin ventas.")
    tot = nuevo["gasoil_total"]
    if not tot.between(500_000, 2_500_000).all():
        errores.append("Ventas totales de gasoil fuera de rango (500 mil a 2,5 millones de m³ por mes).")
    if anterior is not None and len(anterior):
        if nuevo["fecha"].max() < anterior["fecha"].max():
            errores.append("El último mes es anterior al de la versión guardada.")
        comunes = nuevo.merge(anterior[["fecha", "gasoil_total", "naftas_total"]], on="fecha", suffixes=("", "_ant"))
        for c in ("gasoil_total", "naftas_total"):
            dif = (comunes[c] / comunes[f"{c}_ant"] - 1).abs()
            if (dif > 0.15).any():
                errores.append(f"{c}: {int((dif > 0.15).sum())} meses cambiaron más de 15% contra la versión guardada.")
    return errores
