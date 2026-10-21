"""Precios internacionales de naftas y gasoil: precio spot de cierre en EE.UU., por día (dólares por galón).

Los marcadores RBOB y HO (heating oil) son, en sentido estricto, los contratos de futuros de la
bolsa NYMEX. La EIA dejó de publicar esos futuros en abril de 2024 (licencia de CME) y la bolsa no
permite descargarlos libremente. Se usan los precios spot (físicos) que publica la EIA con datos de
Refinitiv (LSEG), que son los que siguen esos marcadores:

  Historia (planillas diarias de la EIA, se publican los miércoles):
    - nafta_nyh: nafta convencional regular, puerto de Nueva York, desde 1986;
    - nafta_usgc: nafta convencional regular, Costa del Golfo, desde 1986;
    - nafta_rbob_la: nafta RBOB regular, Los Ángeles, desde 2003;
    - ho_nyh: heating oil N.º 2, puerto de Nueva York, desde 1986;
    - gasoil_nyh: diésel ultra bajo azufre (ULSD), puerto de Nueva York, desde 2006;
    - gasoil_usgc: diésel ultra bajo azufre (ULSD), Costa del Golfo, desde 2006.
  Solo en la página diaria de la EIA (se acumulan desde octubre de 2026, sin historia previa):
    - nafta_rbob_nyh: nafta RBOB, puerto de Nueva York;
    - nafta_rbob_usgc: nafta RBOB, Costa del Golfo;
    - ho_usgc: heating oil, Costa del Golfo.

La Costa del Golfo (USGC) es la referencia habitual para la paridad de importación en Argentina.
Para pasar a dólares por m³: multiplicar por 264,172 (galones por m³).

Como en `petroleo`, la historia sale de las planillas y el último cierre de la página diaria
("Today in Energy - Daily Prices"); cuando llega la planilla, reemplaza esos días.
"""

import io
import re
import zipfile
from datetime import date

import pandas as pd

from pipeline.fuentes import petroleo
from pipeline.fuentes._indec import Columna

ID = "refinados"
NOMBRE = "Precios internacionales de naftas y gasoil (spot EE.UU., EIA)"
PAGINA = petroleo.PAGINA
URL_DIARIA = petroleo.URL_DIARIA
_HIST = "https://www.eia.gov/dnav/pet/hist_xls/{}d.xls"
URL = _HIST.format("EER_EPMRU_PF4_RGC_DPG")
EXTENSION = "zip"
FRECUENCIA = "D"
ORGANISMO = petroleo.ORGANISMO
UNIDAD = "Dólares por galón"
PRIMER_PERIODO = "1986-06-02"
CALENDARIO = ""
GUARDAR_ORIGINAL = False

PLANILLAS = {  # id: (clave EIA, nombre, (sección, zona) en la página diaria o None)
    "nafta_nyh": ("EER_EPMRU_PF4_Y35NY_DPG", "Nafta convencional regular, puerto de Nueva York, spot", None),
    "nafta_usgc": ("EER_EPMRU_PF4_RGC_DPG", "Nafta convencional regular, Costa del Golfo (EE.UU.), spot", None),
    "nafta_rbob_la": ("EER_EPMRR_PF4_Y05LA_DPG", "Nafta RBOB regular, Los Ángeles, spot", ("Gasoline (RBOB)", "Los Angeles")),
    "ho_nyh": ("EER_EPD2F_PF4_Y35NY_DPG", "Heating oil N.º 2, puerto de Nueva York, spot", ("Heating Oil", "NY Harbor")),
    "gasoil_nyh": ("EER_EPD2DXL0_PF4_Y35NY_DPG", "Gasoil (diésel ULSD), puerto de Nueva York, spot", ("Low-Sulfur Diesel", "NY Harbor")),
    "gasoil_usgc": ("EER_EPD2DXL0_PF4_RGC_DPG", "Gasoil (diésel ULSD), Costa del Golfo (EE.UU.), spot", ("Low-Sulfur Diesel", "Gulf Coast")),
}
SOLO_PAGINA = {  # id: (nombre, (sección, zona))
    "nafta_rbob_nyh": ("Nafta RBOB, puerto de Nueva York, spot (desde oct-2026)", ("Gasoline (RBOB)", "NY Harbor")),
    "nafta_rbob_usgc": ("Nafta RBOB, Costa del Golfo (EE.UU.), spot (desde oct-2026)", ("Gasoline (RBOB)", "Gulf Coast")),
    "ho_usgc": ("Heating oil, Costa del Golfo (EE.UU.), spot (desde oct-2026)", ("Heating Oil", "Gulf Coast")),
}
COLUMNAS = {cid: Columna("", n) for cid, (_, n, _) in PLANILLAS.items()}
COLUMNAS.update({cid: Columna("", n) for cid, (n, _) in SOLO_PAGINA.items()})


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    buf = io.BytesIO()
    urls = []
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for cid, (clave, _, _) in PLANILLAS.items():
            url = _HIST.format(clave)
            z.writestr(f"{cid}.xls", descargar(url, minimo=50_000))
            urls.append(url)
        try:
            z.writestr("diaria.html", descargar(URL_DIARIA, minimo=5_000))
            urls.append(URL_DIARIA)
        except Exception:  # noqa: BLE001 — sin la página igual sirven las planillas
            pass
    return " ".join(urls), buf.getvalue()


def _pagina(html: str) -> tuple[pd.Timestamp, dict]:
    """Fecha del cierre y precios de la tabla "Wholesale Spot Petroleum Prices", por (sección, zona)."""
    m = re.search(r"Wholesale Spot Petroleum Prices,\s*(\d{1,2})/(\d{1,2})/(\d{2,4})\s*Close", html)
    if not m:
        raise ValueError("No encontré la fecha del cierre en la página diaria.")
    anio = int(m[3]) + (2000 if len(m[3]) == 2 else 0)
    fecha = pd.Timestamp(anio, int(m[1]), int(m[2]))
    fin = html.find("</table>", m.end())
    tabla = html[m.end():fin if fin > 0 else m.end() + 20000]
    precios, seccion = {}, None
    for celda in re.finditer(r'<td class="(s1|s2|d1)"[^>]*>(.*?)</td>', tabla, re.S):
        texto = re.sub(r"<[^>]+>", " ", celda[2])
        texto = re.sub(r"\s+", " ", texto).strip()
        if celda[1] == "s1":
            seccion = re.sub(r"\s*\(\$[^)]*\)\s*$", "", texto).strip()
        elif celda[1] == "s2":
            zona = texto
        elif seccion:
            try:
                precios[(seccion, zona)] = float(texto.replace(",", ""))
            except ValueError:
                pass
    return fecha, precios


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        series = {cid: petroleo._planilla(z.read(f"{cid}.xls"), clave)  # noqa: SLF001
                  for cid, (clave, _, _) in PLANILLAS.items()}
        html = z.read("diaria.html").decode("utf-8", "replace") if "diaria.html" in z.namelist() else None
    out = pd.DataFrame(series)
    hasta = out.index.max()
    for cid in SOLO_PAGINA:
        out[cid] = float("nan")
    if html:
        fecha, precios = _pagina(html)
        for cid, (_, _, lugar) in PLANILLAS.items():
            if lugar and lugar in precios and fecha > out[cid].last_valid_index():
                out.loc[fecha, cid] = precios[lugar]
        for cid, (_, lugar) in SOLO_PAGINA.items():
            if lugar in precios:
                out.loc[fecha, cid] = precios[lugar]
    out = out.sort_index()
    out.index.name = "fecha"
    out = out.reset_index()[["fecha", *columnas]]
    out.attrs["planillas_hasta"] = hasta
    return out


def meta_extra(nuevo: pd.DataFrame) -> dict:
    h = nuevo.attrs.get("planillas_hasta")
    return {"planillas_hasta": f"{h:%Y-%m-%d}" if h is not None else None}


def combinar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None) -> pd.DataFrame:
    """Suma lo que solo se guarda corrida a corrida: los días de la página que las planillas todavía no
    traen y toda la historia acumulada de las series que solo están en la página."""
    hasta = nuevo.attrs.get("planillas_hasta")
    if anterior is None or not len(anterior) or hasta is None:
        return nuevo
    n = nuevo.set_index("fecha")
    a = anterior.set_index("fecha").reindex(columns=n.columns)
    todas = n.index.union(a.index)
    n, a = n.reindex(todas), a.reindex(todas)
    recientes = todas > hasta
    for c in n.columns:
        if c in SOLO_PAGINA:
            n[c] = n[c].combine_first(a[c])
        else:
            n.loc[recientes, c] = n.loc[recientes, c].combine_first(a.loc[recientes, c])
    n = n.dropna(how="all")
    return n.reset_index()[list(nuevo.columns)]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    if nuevo["fecha"].min() != pd.Timestamp(PRIMER_PERIODO):
        errores.append(f"La serie no empieza el {PRIMER_PERIODO}.")
    if not nuevo["fecha"].is_monotonic_increasing or nuevo["fecha"].duplicated().any():
        errores.append("Las fechas no están ordenadas o hay repetidas.")
    for cid in columnas:
        if not nuevo[cid].dropna().between(0.1, 15).all():
            errores.append(f"{cid}: precio fuera de rango (0,10 a 15 dólares por galón).")
        reciente = nuevo.loc[nuevo["fecha"] >= nuevo["fecha"].max() - pd.Timedelta(days=60), cid].dropna()
        if (reciente.pct_change().abs() > 0.35).any():
            errores.append(f"{cid}: un salto de más de 35% en un día en los últimos dos meses.")
    if nuevo["fecha"].max() < pd.Timestamp.today() - pd.Timedelta(days=21):
        errores.append(f"El último dato ({nuevo['fecha'].max():%d/%m/%Y}) tiene más de tres semanas.")
    if anterior is not None and len(anterior):
        comunes = nuevo.merge(anterior, on="fecha", suffixes=("", "_ant"))
        for cid in columnas:
            if f"{cid}_ant" in comunes:
                dif = (comunes[cid] - comunes[f"{cid}_ant"]).abs()
                if (dif > 0.3).any():
                    errores.append(f"{cid}: {int((dif > 0.3).sum())} días cambiaron más de 30 centavos contra la versión guardada.")
    return errores
