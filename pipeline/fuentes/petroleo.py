"""Petróleo: precio spot de cierre del Brent y del WTI, por día (dólares por barril).

Fuente: U.S. Energy Information Administration (EIA), precios spot que la EIA publica con
permiso de Refinitiv (LSEG):
  - historia: planillas diarias RBRTEd.xls (Europe Brent Spot Price FOB, desde 1987-05-20) y
    RWTCd.xls (Cushing, OK WTI Spot Price FOB, desde 1986-01-02). Se publican una vez por semana
    (los miércoles) con los datos hasta el día anterior;
  - último cierre: página "Today in Energy - Daily Prices", que se actualiza cada día hábil entre
    las 7:30 y las 8:30 de Washington con el cierre del día hábil anterior. Con ella se agregan los
    días que todavía no están en las planillas; cuando llega la planilla, sus valores reemplazan
    a los de la página (las diferencias quedan en data/revisiones/).

Brent y WTI no cotizan exactamente los mismos días (feriados de Londres y de EE.UU.): en los días
en que solo hay uno de los dos, el otro queda vacío. El WTI cerró negativo el 20/04/2020 (-36,98).
"""

import io
import re
import zipfile
from datetime import date

import pandas as pd

from pipeline.fuentes._indec import Columna

ID = "petroleo"
NOMBRE = "Petróleo: precio spot de cierre del Brent y del WTI (EIA)"
PAGINA = "https://www.eia.gov/dnav/pet/pet_pri_spt_s1_d.htm"
URL_BRENT = "https://www.eia.gov/dnav/pet/hist_xls/RBRTEd.xls"
URL_WTI = "https://www.eia.gov/dnav/pet/hist_xls/RWTCd.xls"
URL_DIARIA = "https://www.eia.gov/TODAYinENERGY/prices.php"
URL = URL_BRENT
EXTENSION = "zip"
FRECUENCIA = "D"
ORGANISMO = "EIA (EE.UU.), con datos de Refinitiv"
UNIDAD = "Dólares por barril"
PRIMER_PERIODO = "1986-01-02"
CALENDARIO = ""
GUARDAR_ORIGINAL = False  # se baja todos los días; el original no aporta

COLUMNAS = {
    "brent": Columna("", "Petróleo Brent, precio spot FOB (Europa), cierre del día"),
    "wti": Columna("", "Petróleo WTI, precio spot FOB (Cushing, Oklahoma), cierre del día"),
    "diferencial": Columna("", "Diferencial Brent - WTI"),
}


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("brent.xls", descargar(URL_BRENT, minimo=100_000))
        z.writestr("wti.xls", descargar(URL_WTI, minimo=100_000))
        try:
            z.writestr("diaria.html", descargar(URL_DIARIA, minimo=5_000))
        except Exception:  # noqa: BLE001 — sin la página igual sirven las planillas
            pass
    return f"{URL_BRENT} {URL_WTI} {URL_DIARIA}", buf.getvalue()


def _planilla(contenido: bytes, clave: str) -> pd.Series:
    hoja = pd.read_excel(io.BytesIO(contenido), sheet_name="Data 1", header=None)
    if str(hoja.iloc[1, 1]).strip() != clave:
        raise ValueError(f"La planilla no es la serie {clave} (dice {hoja.iloc[1, 1]!r}).")
    datos = hoja.iloc[3:]
    fecha = pd.to_datetime(datos[0], errors="coerce")
    valor = pd.to_numeric(datos[1], errors="coerce")
    ok = fecha.notna() & valor.notna()
    return pd.Series(valor[ok].values, index=fecha[ok].dt.normalize().values).sort_index()


def _pagina(html: str) -> tuple[pd.Timestamp, dict]:
    """Fecha del cierre y precios de WTI y Brent de la tabla de precios spot."""
    m = re.search(r"Wholesale Spot Petroleum Prices,\s*(\d{1,2})/(\d{1,2})/(\d{2,4})\s*Close", html)
    if not m:
        raise ValueError("No encontré la fecha del cierre en la página diaria.")
    anio = int(m[3]) + (2000 if len(m[3]) == 2 else 0)
    fecha = pd.Timestamp(anio, int(m[1]), int(m[2]))
    tabla = html[m.end():m.end() + 6000]
    precios = {}
    for nombre, cid in (("WTI", "wti"), ("Brent", "brent")):
        p = re.search(rf'<td class="s2">\s*{nombre}\s*</td>\s*<td class="d1">\s*(-?[\d.,]+)\s*</td>', tabla)
        if p:
            precios[cid] = float(p[1].replace(",", ""))
    return fecha, precios


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        brent = _planilla(z.read("brent.xls"), "RBRTE")
        wti = _planilla(z.read("wti.xls"), "RWTC")
        html = z.read("diaria.html").decode("utf-8", "replace") if "diaria.html" in z.namelist() else None
    out = pd.DataFrame({"brent": brent, "wti": wti})
    hasta = out.index.max()
    diaria = None
    if html:
        fecha, precios = _pagina(html)
        if precios and fecha > out.index.max():
            for cid, v in precios.items():
                out.loc[fecha, cid] = v
            diaria = fecha
    out = out.sort_index()
    out["diferencial"] = out["brent"] - out["wti"]
    out.index.name = "fecha"
    out = out.reset_index()[["fecha", *columnas]]
    out.attrs["planillas_hasta"] = hasta
    out.attrs["fuente_ultimo_dia"] = "página diaria de la EIA" if diaria is not None else "planillas de la EIA"
    return out


def meta_extra(nuevo: pd.DataFrame) -> dict:
    h = nuevo.attrs.get("planillas_hasta")
    return {"fuente_ultimo_dia": nuevo.attrs.get("fuente_ultimo_dia"),
            "planillas_hasta": f"{h:%Y-%m-%d}" if h is not None else None}


def combinar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None) -> pd.DataFrame:
    """Conserva los días que vinieron de la página diaria en corridas anteriores y que las
    planillas todavía no traen (la página muestra solo el último cierre)."""
    hasta = nuevo.attrs.get("planillas_hasta")
    if anterior is None or not len(anterior) or hasta is None:
        return nuevo
    extra = anterior[(anterior["fecha"] > hasta) & ~anterior["fecha"].isin(nuevo["fecha"])]
    if not len(extra):
        return nuevo
    return pd.concat([nuevo, extra]).sort_values("fecha").reset_index(drop=True)[list(nuevo.columns)]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    if nuevo["fecha"].min() != pd.Timestamp(PRIMER_PERIODO):
        errores.append(f"La serie no empieza el {PRIMER_PERIODO}.")
    if not nuevo["fecha"].is_monotonic_increasing or nuevo["fecha"].duplicated().any():
        errores.append("Las fechas no están ordenadas o hay repetidas.")
    if nuevo[["brent", "wti"]].isna().all(axis=1).any():
        errores.append("Hay días sin Brent ni WTI.")
    if not nuevo["brent"].dropna().between(5, 400).all():
        errores.append("Brent fuera de rango (5 a 400 dólares).")
    if not nuevo["wti"].dropna().between(-50, 400).all():
        errores.append("WTI fuera de rango (-50 a 400 dólares).")
    if nuevo["fecha"].max() < pd.Timestamp.today() - pd.Timedelta(days=21):
        errores.append(f"El último dato ({nuevo['fecha'].max():%d/%m/%Y}) tiene más de tres semanas.")
    reciente = nuevo[nuevo["fecha"] >= nuevo["fecha"].max() - pd.Timedelta(days=60)]
    for cid in ("brent", "wti"):
        salto = reciente[cid].dropna().pct_change().abs()
        if (salto > 0.35).any():
            errores.append(f"{cid}: un salto de más de 35% en un día en los últimos dos meses.")
    if anterior is not None and len(anterior):
        if len(nuevo) < len(anterior):
            errores.append("La serie nueva tiene menos días que la guardada.")
        comunes = nuevo.merge(anterior, on="fecha", suffixes=("", "_ant"))
        for cid in ("brent", "wti"):
            dif = (comunes[cid] - comunes[f"{cid}_ant"]).abs()
            if (dif > 5).any():
                errores.append(f"{cid}: {int((dif > 5).sum())} días cambiaron más de 5 dólares contra la versión guardada.")
    return errores
