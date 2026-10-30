"""Lectura de las planillas provinciales del OEDE por rama de actividad (Secretaría de Trabajo, en base al SIPA).

Dos archivos, enlazados desde la página de estadísticas provinciales del OEDE:
  - provinciales_serie_remuneraciones_mensual_2dig_<n>.xlsx: remuneración promedio por todo concepto de los
    asalariados registrados del sector privado, por provincia y rama (letra y dos dígitos de la CIIU rev. 3), mensual;
  - provinciales_serie_empleo_trimestral_2dig_<n>.xlsx: puestos de trabajo asalariados registrados del sector privado,
    por provincia y rama, trimestral.
Una hoja por provincia (GBA son los partidos del conurbano; CABA y el resto de Buenos Aires van aparte). Los datos en
secreto estadístico figuran como "s.d." y quedan vacíos.
"""

import io
import re
import unicodedata
import zipfile
from datetime import date
from urllib.parse import urljoin

import numpy as np
import pandas as pd

PAGINA = "https://www.argentina.gob.ar/trabajo/estadisticas/oede-estadisticas-provinciales"
PATRONES = {"salarios": r"provinciales_serie_remuneraciones_mensual_2dig[^\"']*\.xlsx",
            "empleo": r"provinciales_serie_empleo_trimestral_2dig[^\"']*\.xlsx"}
RESPALDO = {"salarios": "https://www.argentina.gob.ar/sites/default/files/provinciales_serie_remuneraciones_mensual_2dig_9.xlsx",
            "empleo": "https://www.argentina.gob.ar/sites/default/files/provinciales_serie_empleo_trimestral_2dig_7.xlsx"}
# Nombres de hoja que difieren entre los dos archivos -> nombre común
HOJAS = {"GBA": "PARTIDOS DE GBA", "RESTO PCIA. BS. AS.": "RESTO DE BUENOS AIRES"}

# Ramas que se publican: id -> (código en la planilla, nombre)
RAMAS = {
    "agro": ("A", "Agricultura, ganadería, caza y silvicultura"), "pesca": ("B", "Pesca"),
    "mineria": ("C", "Explotación de minas y canteras (incluye petróleo y gas)"),
    "petroleo_gas": ("11", "Extracción de petróleo crudo y gas natural (incluye servicios a la extracción)"),
    "industria": ("D", "Industria manufacturera"), "refinacion": ("23", "Refinación de petróleo y coque (productos de petróleo)"),
    "electricidad_gas_agua": ("E", "Electricidad, gas y agua"), "construccion": ("F", "Construcción"),
    "comercio": ("G", "Comercio"), "venta_combustibles": ("50", "Venta y reparación de vehículos y venta al por menor de combustible"),
    "hoteles_restaurantes": ("H", "Hoteles y restaurantes"), "transporte": ("I", "Transporte, almacenamiento y comunicaciones"),
    "transporte_terrestre": ("60", "Transporte terrestre y por tuberías"), "finanzas": ("J", "Intermediación financiera"),
    "inmobiliarias_empresariales": ("K", "Servicios inmobiliarios, empresariales y de alquiler"), "ensenanza": ("M", "Enseñanza"),
    "salud": ("N", "Servicios sociales y de salud"), "otros_servicios": ("O", "Otros servicios comunitarios, sociales y personales"),
}
LETRAS = [r for r, (c, _) in RAMAS.items() if c.isalpha()]
# Provincias con producción de petróleo y gas (y CABA, donde están las sedes) para la apertura del sector petrolero.
PROVINCIAS_PETROLERAS = {"NEUQUEN": "neuquen", "CHUBUT": "chubut", "SANTA CRUZ": "santa_cruz", "MENDOZA": "mendoza",
                         "RIO NEGRO": "rio_negro", "TIERRA DEL FUEGO": "tierra_del_fuego", "SALTA": "salta", "CABA": "caba"}
NOMBRE_PROV = {"neuquen": "Neuquén", "chubut": "Chubut", "santa_cruz": "Santa Cruz", "mendoza": "Mendoza", "rio_negro": "Río Negro",
               "tierra_del_fuego": "Tierra del Fuego", "salta": "Salta", "caba": "Ciudad de Buenos Aires"}


def norm(s) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip().upper()


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    urls = dict(RESPALDO)
    try:
        html = descargar(PAGINA, minimo=5_000).decode("utf-8", "replace")
        for k, patron in PATRONES.items():
            m = re.findall(r"""["']([^"']*""" + patron + r""")["']""", html, re.I)
            if m:
                urls[k] = urljoin(PAGINA, m[0].split("#")[-1])
    except Exception:  # noqa: BLE001 — si la página falla, se prueban los últimos links conocidos
        pass
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for k, url in urls.items():
            z.writestr(f"{k}.xlsx", descargar(url, minimo=500_000))
    return " ".join(urls.values()), buf.getvalue()


def _tabla(df: pd.DataFrame, trimestral: bool) -> pd.DataFrame | None:
    """Filas = período, columnas = código de rama. None si la hoja no es una tabla de ramas."""
    fila = next((i for i in range(min(12, len(df))) if norm(df.iat[i, 0]).startswith("RAMA") or norm(df.iat[i, 1]).startswith("RAMA")), None)
    if fila is None:
        return None
    per = []
    for c in df.iloc[fila, 2:]:
        if pd.isna(c):
            per.append(None)
        elif trimestral:
            m = re.match(r"\s*(\d)\D+(\d{4})", str(c))
            per.append(pd.Period(f"{m[2]}Q{m[1]}", "Q") if m else None)
        else:
            per.append(pd.Timestamp(c).to_period("M"))
    out = {}
    for i in range(fila + 1, len(df)):
        code = df.iat[i, 0]
        if pd.isna(code):
            continue
        code = str(code).strip().removesuffix(".0")
        vals = pd.to_numeric(df.iloc[i, 2:].replace({"s.d.": np.nan}), errors="coerce").values
        out[code] = pd.Series(vals, index=per)
    t = pd.DataFrame(out)
    return t[t.index.notna()]


def leer_archivos(contenido: bytes) -> tuple[dict, dict]:
    """(salarios, empleo): provincia -> DataFrame período x código de rama."""
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        sal = pd.read_excel(io.BytesIO(z.read("salarios.xlsx")), sheet_name=None, header=None)
        emp = pd.read_excel(io.BytesIO(z.read("empleo.xlsx")), sheet_name=None, header=None)
    S, E = {}, {}
    for h, df in sal.items():
        if df.shape[1] >= 50 and norm(h) != "TOTAL" and (t := _tabla(df, False)) is not None:
            S[HOJAS.get(norm(h), norm(h))] = t
    for h, df in emp.items():
        if df.shape[1] >= 50 and (t := _tabla(df, True)) is not None:
            E[norm(h)] = t
    if len(S) < 24 or set(S) != set(E):
        raise ValueError(f"Las provincias de los dos archivos no coinciden: {sorted(set(S) ^ set(E))}")
    return S, E


def empleo_mensual(e: pd.Series, meses: pd.PeriodIndex) -> pd.Series:
    """Empleo trimestral repetido en los meses del trimestre; los meses posteriores al último trimestre usan el último."""
    return pd.Series(e.reindex([m.asfreq("Q") for m in meses]).values, index=meses).ffill()


def nacional(S: dict, E: dict, code: str) -> tuple[pd.Series, pd.Series]:
    """Salario promedio nacional de la rama (promedio de las provincias ponderado por su empleo en la rama) y empleo
    con el que se ponderó (mensual)."""
    num = den = None
    for p in S:
        s, e = S[p].get(code), E[p].get(code)
        if s is None or e is None:
            continue
        em = empleo_mensual(e, s.index)
        ok = s.notna() & em.notna()
        a, b = (s.where(ok) * em.where(ok)).fillna(0), em.where(ok).fillna(0)
        num = a if num is None else num.add(a, fill_value=0)
        den = b if den is None else den.add(b, fill_value=0)
    return (num / den.replace(0, np.nan)), den
