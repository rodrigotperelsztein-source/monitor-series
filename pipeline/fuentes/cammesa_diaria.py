"""CAMMESA: demanda eléctrica diaria del MEM: total, grandes usuarios y distribuidoras.

Fuente: CAMMESA, "Comportamiento de la demanda de energía eléctrica en el MEM" (informe semanal),
"Base de datos información por región" -> "Base de datos GU Semanal.xlsx", hoja "Base diaria".
Demanda media del día en MW, desde enero de 2022, y la temperatura media de GBA.

  - total: demanda total del MEM;
  - grandes_usuarios: autogeneradores + GUMAs (el detalle por actividad está en cammesa_gu_actividad);
  - distribuidoras: resto de la demanda (distribuidoras);
  - temperatura_gba: temperatura media del día en GBA, °C;
  - dia_habil: 1 si CAMMESA lo cuenta como hábil.

Para pasar a energía: GWh del día = MW medios × 24 / 1000. Datos provisorios; se publican una vez
por semana y cada vez se reemplaza toda la serie.
"""

import io
import zipfile

import pandas as pd

from pipeline.fuentes._indec import Columna
from pipeline.fuentes.cammesa_gu_actividad import PAGINA, URL, _norm

ID = "cammesa_diaria"
NOMBRE = "CAMMESA: demanda eléctrica diaria del MEM"
EXTENSION = "zip"
FRECUENCIA = "D"
ORGANISMO = "CAMMESA"
UNIDAD = "MW (demanda media del día)"
PRIMER_PERIODO = "2022-01-01"
CALENDARIO = ""
GUARDAR_ORIGINAL = False
REGISTRAR_REVISIONES = False
HOJA = "Base diaria"

SERIES = {  # id: (encabezado, nombre)
    "total": ("DEM TOTAL", "Demanda eléctrica total del MEM"),
    "grandes_usuarios": ("AUTO +GUMAS", "Demanda de grandes usuarios (autogeneradores + GUMAs)"),
    "distribuidoras": ("DEMANDA RESTO DISTCO", "Demanda de distribuidoras"),
    "temperatura_gba": ("TEMPERATURA MEDIA GBA °C", "Temperatura media del día en GBA"),
}
COLUMNAS = {cid: Columna("", n, unidad="°C" if cid == "temperatura_gba" else None)
            for cid, (_, n) in SERIES.items()}
COLUMNAS["dia_habil"] = Columna("", "Día hábil según CAMMESA (1 = hábil, 0 = no hábil)", unidad="indicador")


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        nombre = next((n for n in z.namelist() if n.lower().endswith(".xlsx")), None)
        if not nombre:
            raise ValueError("El zip no trae un Excel.")
        hoja = pd.read_excel(io.BytesIO(z.read(nombre)), sheet_name=HOJA, header=None)
    # Encabezados de la tabla diaria: la fila con "TIPO DIA" (los rótulos de valores están en la fila 2).
    cab = [i for i in range(len(hoja)) if any(_norm(v) == "TIPO DIA" for v in hoja.iloc[i])]
    if not cab:
        raise ValueError(f"No encontré la tabla diaria en la hoja {HOJA}.")
    rotulos = [_norm(v) for v in hoja.iloc[2]]
    datos = hoja.iloc[cab[0] + 1:]
    fecha = pd.to_datetime(datos[0], errors="coerce")
    ok = fecha.notna()
    out = pd.DataFrame({"fecha": fecha[ok].dt.normalize().values})
    for cid, (rotulo, _) in SERIES.items():
        cols = [j for j, e in enumerate(rotulos) if e == _norm(rotulo)]
        if not cols:
            raise ValueError(f"No encontré la columna '{rotulo}'.")
        out[cid] = pd.to_numeric(datos.loc[ok, cols[0]], errors="coerce").values
    j_tipo = next(j for j, v in enumerate(hoja.iloc[cab[0]]) if _norm(v).startswith("HABIL"))
    tipo = datos.loc[ok, j_tipo].map(_norm)
    if not set(tipo) <= {"HABIL", "NO HABIL"}:
        raise ValueError(f"Valores inesperados en Hábil/No Hábil: {set(tipo)}")
    out["dia_habil"] = (tipo == "HABIL").astype(int).values
    return out.sort_values("fecha").reset_index(drop=True)[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if nuevo["fecha"].min() != pd.Timestamp(PRIMER_PERIODO):
        errores.append(f"La serie no empieza el {PRIMER_PERIODO}.")
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="D")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los días no son consecutivos.")
    if nuevo[["total", "grandes_usuarios", "distribuidoras"]].isna().any().any():
        errores.append("Hay días sin demanda.")
    dif = (nuevo["grandes_usuarios"] + nuevo["distribuidoras"] - nuevo["total"]).abs()
    if (dif > 1).any():
        errores.append(f"Grandes usuarios + distribuidoras no suman el total (diferencia máxima {dif.max():.1f} MW).")
    if not nuevo["total"].between(7000, 35000).all():
        errores.append("Demanda total fuera de rango (7.000 a 35.000 MW).")
    if anterior is not None and len(anterior) and nuevo["fecha"].max() < anterior["fecha"].max():
        errores.append("El último día es anterior al de la versión guardada.")
    return errores
