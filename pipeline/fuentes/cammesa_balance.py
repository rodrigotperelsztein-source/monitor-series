"""CAMMESA: balance mensual de energía del Mercado Eléctrico Mayorista (GWh).

Fuente: CAMMESA, Informe síntesis mensual, archivo "Balance Mensual.xlsx" (hoja BALANCE).
Demanda: distribuidoras, grandes usuarios, exportación, bombeo, consumos internos y pérdidas.
Oferta: generación térmica, nuclear, renovable (Ley 27.191), hidráulica e importación.

El archivo trae solo los últimos años (hoy, desde enero de 2023): los meses que salen de la
ventana se conservan en data/cammesa_balance.csv. "demanda_mercado" es distribuidoras + grandes
usuarios, la demanda local sin exportación, bombeo ni pérdidas (la que publica Monitor Argy
como "demanda eléctrica").
"""

import io
import unicodedata

import pandas as pd

from pipeline.fuentes._indec import Columna

ID = "cammesa_balance"
NOMBRE = "CAMMESA: balance mensual de energía (demanda y generación)"
URL = ("https://microfe.cammesa.com/static-content/CammesaWeb/download-manager-files/"
       "Sintesis%20Mensual/Estadisticas/Balance%20Mensual.xlsx")
PAGINA = "https://cammesaweb.cammesa.com/informe-sintesis-mensual/"
EXTENSION = "xlsx"
FRECUENCIA = "M"
ORGANISMO = "CAMMESA"
UNIDAD = "GWh"
PRIMER_PERIODO = "2023-01-01"
CALENDARIO = ""

FILAS = {  # id: (rótulo en la columna TIPO, nombre)
    "demanda_distribuidores": ("distribuidor", "Demanda de distribuidoras"),
    "demanda_grandes_usuarios": ("gran usuario", "Demanda de grandes usuarios"),
    "demanda_exportacion": ("exportacion", "Exportación"),
    "demanda_bombeo": ("bombeo", "Bombeo"),
    "demanda_consumos_internos": ("consumos internos", "Consumos internos"),
    "demanda_perdidas": ("perdidas", "Pérdidas"),
    "demanda_total": ("total demanda", "Demanda total (incluye exportación, bombeo y pérdidas)"),
    "generacion_termica": ("termica", "Generación térmica"),
    "generacion_nuclear": ("nuclear", "Generación nuclear"),
    "generacion_renovable": ("renovable", "Generación renovable (Ley 27.191)"),
    "generacion_hidraulica": ("hidraulica", "Generación hidráulica"),
    "importacion": ("importacion", "Importación"),
    "generacion_total": ("total generacion", "Oferta total (generación + importación)"),
}
COLUMNAS = {"demanda_mercado": Columna("", "Demanda de energía eléctrica: distribuidoras + grandes usuarios")}
COLUMNAS["demanda_mercado_var_ia"] = Columna("", "Demanda de energía eléctrica, var. % interanual",
                                             tipo="variacion", base="demanda_mercado", rezago=12)
for _cid, (_rot, _nombre) in FILAS.items():
    COLUMNAS[_cid] = Columna("", _nombre)


def _norm(s) -> str:
    s = "" if pd.isna(s) else str(s)
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").strip().lower()


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    hoja = pd.read_excel(io.BytesIO(contenido), sheet_name="BALANCE", header=None)
    fila_fechas = next(i for i in range(len(hoja)) if _norm(hoja.iat[i, 0]) == "balance")
    fechas = pd.to_datetime(hoja.iloc[fila_fechas, 2:], errors="coerce")
    validas = fechas.notna().values
    tipos = hoja.iloc[:, 1].map(_norm)
    out = pd.DataFrame({"fecha": fechas[validas].values})
    for cid, (rotulo, _) in FILAS.items():
        filas = [i for i, t in tipos.items() if t.startswith(rotulo) and i > fila_fechas]
        if len(filas) != 1:
            raise ValueError(f"No encontré una única fila '{rotulo}' en la hoja BALANCE (encontré {len(filas)}).")
        out[cid] = pd.to_numeric(hoja.iloc[filas[0], 2:][validas], errors="coerce").values
    out["fecha"] = pd.to_datetime(out["fecha"]).dt.to_period("M").dt.to_timestamp()
    out["demanda_mercado"] = out["demanda_distribuidores"] + out["demanda_grandes_usuarios"]
    out["demanda_mercado_var_ia"] = None
    return out[["fecha", *columnas]]


def combinar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None) -> pd.DataFrame:
    """Los meses del archivo reemplazan a los guardados; los que salieron de la ventana se conservan."""
    if anterior is not None:
        viejo = anterior[anterior["fecha"] < nuevo["fecha"].min()]
        nuevo = pd.concat([viejo, nuevo])
    nuevo = nuevo.sort_values("fecha").reset_index(drop=True)
    nuevo["demanda_mercado_var_ia"] = nuevo["demanda_mercado"].pct_change(12, fill_method=None) * 100
    return nuevo


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los meses no son consecutivos.")
    if nuevo[[c for c in FILAS]].isna().any().any():
        errores.append("Hay valores vacíos.")
    partes = [c for c in FILAS if c.startswith("demanda_") and c != "demanda_total"]
    if ((nuevo[partes].sum(axis=1) - nuevo["demanda_total"]).abs() > 1).any():
        errores.append("Las partes de la demanda no suman la demanda total.")
    oferta = ["generacion_termica", "generacion_nuclear", "generacion_renovable", "generacion_hidraulica", "importacion"]
    if ((nuevo[oferta].sum(axis=1) - nuevo["generacion_total"]).abs() > 1).any():
        errores.append("Las fuentes de generación no suman la oferta total.")
    if not nuevo["demanda_mercado"].between(5000, 25000).all():
        errores.append("Demanda mensual fuera de rango (5.000 a 25.000 GWh): ¿cambió la unidad?")
    if anterior is not None and len(anterior) and nuevo["fecha"].max() < anterior["fecha"].max():
        errores.append("El último mes es anterior al de la versión guardada.")
    return errores
