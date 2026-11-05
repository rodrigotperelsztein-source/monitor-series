"""Deuda bruta de la Administración Central (Tesoro nacional), fin de mes, millones de dólares, desde 2019
(Secretaría de Finanzas, boletín mensual de deuda). La deuda en pesos se convierte al tipo de cambio del último día hábil.

El nombre del archivo cambia con cada boletín (boletin_mensual_<día>_<mes>_<año>.xlsx): se toma el enlace de la página
de datos mensuales de la Secretaría. Hoja A.1 (deuda por instrumento).
"""

import io
import re
import zipfile
from datetime import date

import pandas as pd

from pipeline.fuentes._indec import Columna, norm

ID = "deuda"
NOMBRE = "Deuda bruta de la Administración Central, por instrumento (Secretaría de Finanzas)"
PAGINA = "https://www.argentina.gob.ar/economia/finanzas/datos-mensuales"
BASE = "https://www.argentina.gob.ar"
URL = PAGINA
EXTENSION = "zip"
FRECUENCIA = "M"
ORGANISMO = "Secretaría de Finanzas"
UNIDAD = "Millones de USD"
PRIMER_PERIODO = "2019-01-01"
CALENDARIO = ""
ENLACE = re.compile(r'href="((?:https://www\.argentina\.gob\.ar)?/sites/default/files/[\w/-]*boletin_mensual[\w-]*\.xlsx)"')
MESES = {m: i + 1 for i, m in enumerate(["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"])}

# id -> (rótulo de la fila, ocurrencia, nombre)
FILAS = {
    "deuda_bruta": ("A- DEUDA BRUTA", 1, "Deuda bruta de la Administración Central"),
    "pago_normal": ("I- DEUDA EN SITUACION DE PAGO NORMAL", 1, "Deuda en situación de pago normal"),
    "titulos_publicos": ("TITULOS PUBLICOS", 1, "Títulos públicos de mediano y largo plazo"),
    "titulos_moneda_nacional": ("- MONEDA NACIONAL", 1, "Títulos públicos en moneda nacional"),
    "titulos_cer": ("DEUDA AJUSTABLE POR CER", 1, "Títulos públicos ajustables por CER"),
    "titulos_moneda_extranjera": ("- MONEDA EXTRANJERA", 1, "Títulos públicos en moneda extranjera"),
    "organismos_internacionales": ("ORGANISMOS INTERNACIONALES", 1, "Préstamos de organismos internacionales"),
    "organismos_oficiales": ("ORGANISMOS OFICIALES", 1, "Préstamos de organismos oficiales"),
    "corto_plazo": ("CORTO PLAZO", 1, "Deuda de corto plazo"),
    "letras_corto_plazo": ("LETRAS DEL TESORO", 2, "Letras del Tesoro de corto plazo"),
    "pago_diferido": ("II- DEUDA EN SITUACION DE PAGO DIFERIDO", 1, "Deuda en situación de pago diferido"),
    "pendiente_reestructuracion": ("III- DEUDA ELEGIBLE PENDIENTE", 1, "Deuda elegible pendiente de reestructuración"),
}
COLUMNAS = {k: Columna("", n) for k, (_, _, n) in FILAS.items()}


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    pagina = descargar(PAGINA, minimo=5_000).decode("utf-8", "replace")
    enlaces = list(dict.fromkeys(ENLACE.findall(pagina)))
    if not enlaces:
        raise ValueError("No encontré el enlace al boletín mensual de deuda en la página de Finanzas.")
    url = enlaces[0] if enlaces[0].startswith("https://") else BASE + enlaces[0]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("boletin.xlsx", descargar(url, minimo=50_000))
    return url, buf.getvalue()


def _mes(v) -> pd.Timestamp | None:
    if isinstance(v, (pd.Timestamp, date)):
        return pd.Timestamp(v).to_period("M").to_timestamp()
    m = re.match(r"([A-Z]{3})\w*[-/ ](\d{2,4})", norm(v)) if pd.notna(v) else None
    if m and m[1] in MESES:
        a = int(m[2])
        return pd.Timestamp(year=a + 2000 if a < 100 else a, month=MESES[m[1]], day=1)
    return None


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        hoja = pd.read_excel(io.BytesIO(z.read("boletin.xlsx")), sheet_name="A.1", header=None)
    fila_mes = next(i for i in range(min(20, len(hoja))) if sum(_mes(v) is not None for v in hoja.iloc[i]) >= 12)
    cols = {j: f for j, v in enumerate(hoja.iloc[fila_mes]) if (f := _mes(v)) is not None}
    rotulos = [" ".join(norm(v) for v in hoja.iloc[i, :2] if pd.notna(v)) for i in range(len(hoja))]
    out = {}
    for k, (rot, n, _) in FILAS.items():
        filas = [i for i, r in enumerate(rotulos) if i > fila_mes and r.startswith(norm(rot))]
        if len(filas) < n:
            raise ValueError(f"No encontré la fila '{rot}' en la hoja A.1.")
        out[k] = pd.to_numeric(pd.Series({f: hoja.iloc[filas[n - 1], j] for j, f in cols.items()}), errors="coerce")
    df = pd.DataFrame(out).sort_index()
    df.index.name = "fecha"
    df = df[df.index >= PRIMER_PERIODO]
    return df.reset_index()[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    esperado = pd.date_range(PRIMER_PERIODO, periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los meses no son consecutivos.")
    if not nuevo["deuda_bruta"].between(200_000, 1_000_000).all():
        errores.append("Deuda bruta fuera de rango.")
    s = nuevo["pago_normal"] + nuevo["pago_diferido"].fillna(0) + nuevo["pendiente_reestructuracion"].fillna(0)
    if ((s / nuevo["deuda_bruta"] - 1).abs() > 0.001).any():
        errores.append("Pago normal + diferido + pendiente no suman la deuda bruta.")
    if anterior is not None and len(anterior) and len(nuevo) < len(anterior):
        errores.append("Se perdieron meses.")
    return errores
