"""Baja un archivo de una fuente y describe su estructura, para escribir el lector.

Uso: python -m pipeline.inspeccionar URL [URL ...]
Escribe un resumen por archivo en inspeccion/<nombre>.txt: hojas, dimensiones,
primeras filas completas, últimas filas y filas que parecen encabezados.
"""

import io
import sys
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from pipeline.actualizar import RAIZ, descargar


def celda(v, ancho=70) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = str(v).replace("\n", " ").strip()
    return s if len(s) <= ancho else s[: ancho - 1] + "…"


def describir(url: str, contenido: bytes) -> str:
    nombre = Path(urlparse(url).path).name
    lineas = [f"URL: {url}", f"Bytes: {len(contenido)}", ""]
    if contenido[:200].lstrip().lower().startswith((b"<!doctype html", b"<html")):
        import re
        links = sorted(set(re.findall(rb'href=["\']([^"\']+\.(?:xls|xlsx|csv|pdf|zip))["\']', contenido, re.I)))
        lineas.append(f"Página HTML; links a archivos ({len(links)}):")
        lineas += ["  " + l.decode("utf-8", "replace") for l in links]
        return "\n".join(lineas)
    if nombre.lower().endswith(".csv"):
        texto = contenido.decode("utf-8", "replace") if not contenido.startswith(b"\xff\xfe") else contenido.decode("utf-16")
        filas = texto.splitlines()
        lineas.append(f"CSV: {len(filas)} líneas")
        lineas += ["  " + f[:300] for f in filas[:15]]
        lineas.append("  ...")
        lineas += ["  " + f[:300] for f in filas[-5:]]
        return "\n".join(lineas)
    if nombre.lower().endswith(".pdf"):
        import pdfplumber
        with pdfplumber.open(io.BytesIO(contenido)) as pdf:
            lineas.append(f"Páginas: {len(pdf.pages)}")
            for n, pagina in enumerate(pdf.pages[:4], 1):
                lineas.append(f"=== Página {n}")
                lineas.append(pagina.extract_text() or "(sin texto)")
        return "\n".join(lineas)
    if not contenido.startswith((b"PK", b"\xd0\xcf")):
        # Ni Excel (xlsx/zip ni xls/OLE): se muestra como texto (JSON, CSV de una API, etc.).
        texto = contenido.decode("utf-8", "replace")
        lineas.append("Texto:")
        lineas += ["  " + f[:300] for f in texto.splitlines()[:40]]
        return "\n".join(lineas)
    motor = "xlrd" if nombre.lower().endswith(".xls") else None
    hojas = pd.read_excel(io.BytesIO(contenido), sheet_name=None, header=None, engine=motor)
    for hoja, df in hojas.items():
        df = df.dropna(how="all").dropna(axis=1, how="all")
        lineas.append(f"=== Hoja '{hoja}': {df.shape[0]} filas con datos x {df.shape[1]} columnas")
        def fila(i):
            vals = [f"c{j}:{celda(v)}" for j, v in df.loc[i].items() if celda(v)]
            return f"  f{i}: " + " | ".join(vals)
        idx = list(df.index)
        lineas.append("  -- primeras 25 filas")
        lineas += [fila(i) for i in idx[:25]]
        lineas.append("  -- últimas 6 filas")
        lineas += [fila(i) for i in idx[-6:]]
        lineas.append("")
    return "\n".join(lineas)


def main() -> int:
    salida = RAIZ / "inspeccion"
    salida.mkdir(exist_ok=True)
    for url in sys.argv[1:]:
        u = urlparse(url)
        nombre = Path(u.path).name or "archivo"
        if u.query:
            import hashlib
            nombre += "_" + hashlib.sha256(u.query.encode()).hexdigest()[:6]
        try:
            (salida / "archivos").mkdir(exist_ok=True)
            contenido = descargar(url, minimo=1)
            (salida / "archivos" / nombre).write_bytes(contenido)
            texto = describir(url, contenido)
        except Exception as e:  # noqa: BLE001
            texto = f"URL: {url}\nERROR: {e}"
        (salida / f"{nombre}.txt").write_text(texto, encoding="utf-8")
        print(texto[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
