"""Entrada diaria de camiones a puertos, fábricas y molinos, por zona portuaria y por producto.

Fuente: Secretaría de Agricultura, Ganadería y Pesca (Subsecretaría de Mercados Agropecuarios),
elaborado en base a datos de Williams Entregas. Cantidad de camiones descargados por día.

La página muestra el mes en curso en una tabla HTML que se actualiza cada día hábil; los meses
anteriores están en un PDF por mes (total_mensual_<mes>_<año>.pdf, con el mes escrito a veces
completo y a veces abreviado). Se toman desde enero de 2024.

Los días sin actividad o sin informe (domingos, feriados) figuran en cero.
La última columna, vagones, se rotula "total vagones" en los PDF viejos y "vagones en playa" en
los nuevos.
"""

import io
import re
import unicodedata
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

from pipeline.fuentes._indec import Columna

ID = "camiones_puertos"
NOMBRE = "Entrada diaria de camiones con granos a puertos, fábricas y molinos"
PAGINA = ("https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/logistica/_archivos/"
          "000023_Posici%C3%B3n%20de%20Camiones%20y%20Vagones/000020_Entrada%20diaria%20de%20camiones%20y%20"
          "vagones%20a%20puertos,%20f%C3%A1bricas%20y%20molinos%20(por%20zona%20portuaria%20y%20por%20producto).php")
URL = PAGINA
INFORMES = "https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/informes/entrada_camiones/"
EXTENSION = "zip"
FRECUENCIA = "D"
ORGANISMO = "Secretaría de Agricultura, Ganadería y Pesca (datos de Williams Entregas)"
UNIDAD = "Camiones por día"
PRIMER_PERIODO = "2024-01-01"
CALENDARIO = ""
GUARDAR_ORIGINAL = False
REGISTRAR_REVISIONES = False

HISTORIA = Path(__file__).resolve().parents[2] / "data" / f"{ID}.csv"

ZONAS = {"rosario": "Rosario y aledaños", "darsena_bsas_entre_rios": "Dársena Buenos Aires y Entre Ríos",
         "necochea": "Puerto Necochea", "bahia_blanca": "Puerto Bahía Blanca"}
PRODUCTOS = {"trigo": "trigo", "maiz": "maíz", "sorgo": "sorgo", "cebada": "cebada", "soja": "soja",
             "girasol": "girasol"}
ORDEN = [*ZONAS, "total", *PRODUCTOS, "total_productos", "vagones"]

COLUMNAS = {"total": Columna("", "Camiones descargados por día, total")}
for _k, _n in ZONAS.items():
    COLUMNAS[_k] = Columna("", f"Camiones descargados por día, {_n}")
for _k, _n in PRODUCTOS.items():
    COLUMNAS[_k] = Columna("", f"Camiones descargados por día, {_n}")
COLUMNAS["vagones"] = Columna("", "Vagones por día", unidad="Vagones por día")

MESES = {m: i for i, m in enumerate(["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct",
                                      "nov", "dic"], 1)}
NUM = r"\d{1,3}(?:\.\d{3})+|\d+"
FILA = re.compile(rf"\b(\d{{1,2}})-([a-z]{{3}})[a-z]*\s+((?:(?:{NUM})\s+){{12}}(?:{NUM}))\b")


def _sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def _pdfs(html: str) -> dict[str, str]:
    """'AAAA-MM' -> URL del PDF mensual, según los links de la página."""
    out = {}
    for m in re.finditer(r"entrada_camiones/(\d{4})/(total_mensual_([a-z]+)_(\d{4})\.pdf)", html):
        mes = MESES.get(_sin_tildes(m[3])[:3])
        if mes:
            out[f"{m[4]}-{mes:02d}"] = INFORMES + f"{m[1]}/{m[2]}"
    return out


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    html = descargar(PAGINA)
    pdfs = _pdfs(html.decode("utf-8", "replace"))
    if HISTORIA.exists():
        # El mes anterior, por si el PDF trae correcciones de los últimos días; el resto ya está guardado.
        previo = (pd.Period(hoy, freq="M") - 1).strftime("%Y-%m")
        meses = [m for m in pdfs if m >= previo]
    else:
        meses = [m for m in pdfs if m >= PRIMER_PERIODO[:7]]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        info = zipfile.ZipInfo("pagina.html", date_time=(2000, 1, 1, 0, 0, 0))
        z.writestr(info, html)
        for m in sorted(meses):
            z.writestr(zipfile.ZipInfo(f"{m}.pdf", date_time=(2000, 1, 1, 0, 0, 0)), descargar(pdfs[m]))
    return " ".join([PAGINA] + [pdfs[m] for m in sorted(meses)]), buf.getvalue()


def _filas(texto: str, anio: int, mes: int | None) -> list[dict]:
    filas = []
    for m in FILA.finditer(_sin_tildes(texto)):
        mes_fila = MESES.get(m[2])
        if mes_fila is None or (mes and mes_fila != mes):
            continue
        nums = [int(x.replace(".", "")) for x in m[3].split()]
        filas.append({"fecha": pd.Timestamp(anio, mes_fila, int(m[1])), **dict(zip(ORDEN, nums))})
    return filas


def _texto_html(html: str) -> str:
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"&nbsp;", " ", t)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    import pdfplumber

    filas = []
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        for nombre in sorted(z.namelist()):
            if nombre.endswith(".pdf"):
                anio, mes = map(int, nombre[:7].split("-"))
                with pdfplumber.open(io.BytesIO(z.read(nombre))) as pdf:
                    texto = "\n".join(p.extract_text() or "" for p in pdf.pages)
                nuevas = _filas(texto, anio, mes)
                if not nuevas:
                    raise ValueError(f"No encontré filas en el PDF de {nombre[:7]}.")
                filas += nuevas
        texto = _sin_tildes(_texto_html(z.read("pagina.html").decode("utf-8", "replace")))
        # La tabla del mes en curso se rotula "Octubre 2026", etc., y termina en la fila "Acumulados".
        m = re.search(r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)"
                      r"\s+(\d{4})\s+zona", texto)
        if not m:
            raise ValueError("No encontré el mes de la tabla en la página.")
        fin = texto.find("acumulados", m.end())
        filas += _filas(texto[m.end(): fin if fin > 0 else None], int(m[2]), MESES[m[1][:3]])
    df = pd.DataFrame(filas)
    if df.empty:
        raise ValueError("No encontré datos.")
    # El mes en curso de la página pisa al PDF si se superponen (la página es la versión más nueva).
    df = df.drop_duplicates("fecha", keep="last").sort_values("fecha")
    df = df[df["fecha"] >= PRIMER_PERIODO]
    df.attrs["controles"] = df[ORDEN].copy()
    return df.reset_index(drop=True)[["fecha", *columnas]]


def combinar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None) -> pd.DataFrame:
    if anterior is None:
        return nuevo
    viejo = anterior[anterior["fecha"] < nuevo["fecha"].min()]
    return pd.concat([viejo, nuevo]).sort_values("fecha").reset_index(drop=True)[list(nuevo.columns)]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    if nuevo["fecha"].min() != pd.Timestamp(PRIMER_PERIODO):
        errores.append(f"La serie no empieza el {PRIMER_PERIODO}.")
    faltan = sorted(set(pd.date_range(nuevo["fecha"].min(), nuevo["fecha"].max())) - set(nuevo["fecha"]))
    if faltan:
        errores.append(f"Faltan {len(faltan)} días: {[f'{x:%Y-%m-%d}' for x in faltan[:5]]}")
    zonas = nuevo[list(ZONAS)].sum(axis=1)
    productos = nuevo[list(PRODUCTOS)].sum(axis=1)
    mal_z = (zonas - nuevo["total"]).abs() > 1
    mal_p = (productos - nuevo["total"]).abs() > 1
    # Algún día suelto puede venir mal sumado en la fuente: se avisa; si son muchos, se frena (columnas corridas).
    for nombre, mal in (("zonas", mal_z), ("productos", mal_p)):
        if mal.any():
            print(f"  aviso: en {int(mal.sum())} días la suma por {nombre} no da el total: "
                  f"{[f'{x:%Y-%m-%d}' for x in nuevo.loc[mal, 'fecha'][:5]]}")
        if mal.sum() > 10:
            errores.append(f"En {int(mal.sum())} días la suma por {nombre} no coincide con el total.")
    if anterior is not None and len(anterior) and nuevo["fecha"].max() < anterior["fecha"].max():
        errores.append("El último día es anterior al de la versión guardada.")
    return errores
