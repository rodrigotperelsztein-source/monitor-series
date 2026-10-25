"""Lectura de los informes de Estimaciones Agrícolas de la Secretaría de Agricultura, Ganadería y Pesca.

La Dirección de Estimaciones Agrícolas publica en
https://www.magyp.gob.ar/sitio/areas/estimaciones/estimaciones/informes/ (con ?mes=AAAA-MM para meses
anteriores) un informe semanal (los jueves) y uno mensual (a mediados de mes), en PDF. No hay planillas: se lee
el texto de los PDF.

  - informe semanal: entre otras cosas, el área sembrada y la producción de las últimas diez campañas cerradas.
  - informe mensual: superficie implantada y producción estimada de cada cultivo para la campaña en curso.
"""

import re
import unicodedata
from datetime import date

INFORMES = "https://www.magyp.gob.ar/sitio/areas/estimaciones/estimaciones/informes/"
SITIO = "https://www.magyp.gob.ar"
CULTIVOS = {"TRIGO": "trigo", "MAIZ": "maiz", "SOJA": "soja", "GIRASOL": "girasol"}
NUM = r"\d{1,3}(?:\.\d{3})+"
_LINK = re.compile(r'href="(/sitio/areas/estimaciones/_archivos/[^"]+\.pdf)"', re.I)


def sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def fecha_informe(url: str) -> date:
    """El nombre de cada PDF empieza con AAMMDD."""
    m = re.match(r"(\d{2})(\d{2})(\d{2})", url.rsplit("/", 1)[-1])
    if not m:
        raise ValueError(f"No reconozco la fecha del informe: {url}")
    return date(2000 + int(m[1]), int(m[2]), int(m[3]))


def ultimos_informes(descargar, hoy: date) -> dict[str, str]:
    """URL del último informe semanal y del último mensual (mira el mes en curso y, si hace falta, el anterior)."""
    from urllib.parse import quote
    encontrados: dict[str, tuple[date, str]] = {}
    mes_ant = date(hoy.year - (hoy.month == 1), (hoy.month - 2) % 12 + 1, 1)
    for url in (INFORMES, f"{INFORMES}?mes={mes_ant:%Y-%m}"):
        texto = descargar(url, minimo=5_000).decode("utf-8", "replace")
        for href in _LINK.findall(texto):
            nombre = sin_tildes(href.rsplit("/", 1)[-1]).lower()
            tipo = "semanal" if "semanal" in nombre else "mensual" if "mensual" in nombre else None
            if not tipo:
                continue
            f = fecha_informe(href)
            if tipo not in encontrados or f > encontrados[tipo][0]:
                encontrados[tipo] = (f, SITIO + quote(href))
        if len(encontrados) == 2:
            break
    if "semanal" not in encontrados:
        raise ValueError("No encontré informes semanales de Estimaciones Agrícolas.")
    return {k: v[1] for k, v in encontrados.items()}


def _texto_paginas(pdf_bytes: bytes) -> list[str]:
    import io
    import pdfplumber
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return [p.extract_text() or "" for p in pdf.pages]


def series_decenales(pdf_bytes: bytes) -> dict[str, dict[str, dict[int, float]]]:
    """Área sembrada (ha) y producción (t) de las últimas diez campañas cerradas, por cultivo:
    {"area": {cultivo: {campaña: valor}}, "produccion": {...}}."""
    out = {"area": {}, "produccion": {}}
    for t in _texto_paginas(pdf_bytes):
        u = sin_tildes(t).upper()
        clave = "area" if "AREA SEMBRADA DE GRANOS" in u else "produccion" if "VOLUMENES DE PRODUCCION" in u else None
        if not clave:
            continue
        campanias = [int(a) for a in re.findall(r"(\d{4})/\d{4}", u.split("CULTIVOS", 1)[-1].splitlines()[0])]
        for linea in u.splitlines():
            m = re.match(r"^(TRIGO|MAIZ|SOJA|GIRASOL)\s+((?:" + NUM + r"\s*)+)$", linea.strip())
            if m and campanias:
                vals = [float(x.replace(".", "")) for x in re.findall(NUM, m[2])]
                if len(vals) == len(campanias):
                    out[clave][CULTIVOS[m[1]]] = dict(zip(campanias, vals))
    return out


def estimacion_mensual(pdf_bytes: bytes) -> dict[str, dict]:
    """Superficie implantada y producción estimada de la campaña en curso, por cultivo."""
    out = {}
    for t in _texto_paginas(pdf_bytes):
        t = sin_tildes(t)
        cab = "\n".join(t.splitlines()[:4]).upper()
        m = re.search(r"\n(TRIGO|MAIZ|SOJA|GIRASOL)\s*\n\s*CAMPANA (\d{4})/(\d{2})", cab)
        if not m:
            continue
        if "Superficie implantada" in t:
            i = t.find("Superficie implantada")
            sup = re.findall(NUM, t[i:t.find("(ha)", i)])
        else:
            i = t.find("Superficie\n")
            sup = re.findall(NUM, t[i:t.find("implantada", i)]) if i >= 0 else []
        k = t.find("Produccion")
        prod = [x for x in re.findall(NUM, t[k:t.find("(ton)", k)])] if k >= 0 else []
        v = lambda x: float(x.replace(".", ""))  # noqa: E731
        out[CULTIVOS[m[1]]] = {
            "campania": int(m[2]),
            "superficie_ha": v(sup[-1]) if len(sup) >= 2 else None,
            # El primer número es la producción de la campaña anterior; si hay más, el último es el de la actual.
            "produccion_t": v(prod[-1]) if len(prod) >= 2 else None,
        }
    return out
