"""CAMMESA: demanda mensual de energía eléctrica por sector (residencial, comercial, industrial).

Fuente: CAMMESA, "Base Informe Mensual" (zip mensual de la síntesis mensual), archivo
"Demanda Mensual.xlsx". La tabla de detalle trae la demanda de cada agente (distribuidoras por
categoría de tarifa y grandes usuarios) por mes; acá se suma por categoría de tarifa:
  - residencial;
  - comercial (usuarios no residenciales de menos de 300 kW de las distribuidoras);
  - industrial / comercial grande (no residenciales de 300 kW o más y grandes usuarios del MEM).
La suma de los tres es la demanda local (distribuidoras + grandes usuarios), y se controla
contra el total que trae el mismo archivo.

El zip pesa unos 40 MB y su link cambia cada mes, así que se lo busca en la página. Trae desde
enero de 2023; los meses que salen de la ventana se conservan en data/cammesa_sectores.csv.
"""

import html as html_mod
import io
import re
import zipfile
from datetime import date

import pandas as pd

from pipeline.fuentes._indec import Columna

ID = "cammesa_sectores"
NOMBRE = "CAMMESA: demanda de energía eléctrica por sector"
PAGINA = "https://cammesaweb.cammesa.com/informe-sintesis-mensual/"
URL = PAGINA
EXTENSION = "zip"
FRECUENCIA = "M"
ORGANISMO = "CAMMESA"
UNIDAD = "GWh"
PRIMER_PERIODO = "2023-01-01"
CALENDARIO = ""
GUARDAR_ORIGINAL = False

SECTORES = {"residencial": "Residencial", "comercial": "Comercial",
            "industrial": "Industrial/Comercial Grande"}
NOMBRES = {"residencial": "residencial", "comercial": "comercial (menos de 300 kW)",
           "industrial": "industrial y comercial grande (300 kW o más y grandes usuarios)",
           "total": "total (distribuidoras + grandes usuarios)"}
COLUMNAS = {}
for _cid, _n in NOMBRES.items():
    COLUMNAS[_cid] = Columna("", f"Demanda de energía eléctrica, {_n}")
for _cid, _n in NOMBRES.items():
    COLUMNAS[f"{_cid}_var_ia"] = Columna("", f"Demanda de energía eléctrica, {_n}, var. % interanual",
                                         tipo="variacion", base=_cid, rezago=12)


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    pagina = descargar(PAGINA).decode("utf-8", "replace")
    links = re.findall(r'data-downloadurl="([^"]*base_informe_mensual[^"]*)"', pagina, re.I)
    if not links:
        raise ValueError("No encontré el link de la Base Informe Mensual en la página.")
    url = html_mod.unescape(links[0]).split("&refresh")[0]
    return url, descargar(url)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        nombre = next((n for n in z.namelist() if n.endswith("Demanda Mensual.xlsx")), None)
        if not nombre:
            raise ValueError("El zip no trae 'Demanda Mensual.xlsx'.")
        hoja = pd.read_excel(io.BytesIO(z.read(nombre)), sheet_name="DEMANDA", header=None)
    cab = hoja.index[hoja[0].astype(str).str.strip() == "AÑO"]
    if len(cab) != 1:
        raise ValueError("No encontré la tabla de detalle (fila 'AÑO').")
    d = hoja.iloc[cab[0] + 1:].copy()
    d.columns = [str(c).strip() for c in hoja.iloc[cab[0]]]
    faltan = {"MES", "CATEGORIA TARIFA", "DEMANDA [MWh]"} - set(d.columns)
    if faltan:
        raise ValueError(f"Faltan columnas en el detalle: {faltan}")
    d = d.dropna(subset=["MES"])
    d["fecha"] = pd.to_datetime(d["MES"]).dt.to_period("M").dt.to_timestamp()
    d["mwh"] = pd.to_numeric(d["DEMANDA [MWh]"], errors="raise")
    otras = set(d["CATEGORIA TARIFA"].unique()) - set(SECTORES.values())
    if otras:
        raise ValueError(f"Categorías de tarifa nuevas: {otras}")
    t = d.pivot_table(index="fecha", columns="CATEGORIA TARIFA", values="mwh", aggfunc="sum").fillna(0) / 1000
    out = pd.DataFrame({cid: t[cat] for cid, cat in SECTORES.items()})
    out["total"] = out.sum(axis=1)

    # Control: el resumen de la misma hoja trae la demanda local por mes (en MWh).
    fila_fechas = hoja.index[hoja[0].astype(str).str.strip() == "TIPO DEMANDA"][0]
    fila_local = hoja.index[hoja[0].astype(str).str.strip() == "DEMANDA LOCAL"][0]
    fechas = pd.to_datetime(hoja.iloc[fila_fechas, 1:], errors="coerce")
    local = pd.to_numeric(hoja.iloc[fila_local, 1:], errors="coerce")
    resumen = pd.Series(local.values / 1000, index=fechas.dt.to_period("M").dt.to_timestamp().values).dropna()
    dif = (out["total"] - resumen.reindex(out.index)).abs()
    if (dif > 1).any():
        raise ValueError(f"La suma por sector no coincide con la demanda local del resumen "
                         f"(diferencia máxima {dif.max():.1f} GWh).")
    out = out.reset_index().rename(columns={"index": "fecha"})
    for cid in NOMBRES:
        out[f"{cid}_var_ia"] = None
    return out[["fecha", *columnas]]


def combinar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None) -> pd.DataFrame:
    if anterior is not None:
        nuevo = pd.concat([anterior[anterior["fecha"] < nuevo["fecha"].min()], nuevo])
    nuevo = nuevo.sort_values("fecha").reset_index(drop=True)
    for cid in NOMBRES:
        nuevo[f"{cid}_var_ia"] = nuevo[cid].pct_change(12, fill_method=None) * 100
    return nuevo


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los meses no son consecutivos.")
    if not nuevo["total"].between(5000, 25000).all():
        errores.append("Demanda mensual fuera de rango (5.000 a 25.000 GWh).")
    if (nuevo[list(SECTORES)] <= 0).any().any():
        errores.append("Hay sectores con demanda cero o negativa.")
    if anterior is not None and len(anterior) and nuevo["fecha"].max() < anterior["fecha"].max():
        errores.append("El último mes es anterior al de la versión guardada.")
    return errores
