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


def describir(url: str) -> str:
    contenido = descargar(url)
    nombre = Path(urlparse(url).path).name
    lineas = [f"URL: {url}", f"Bytes: {len(contenido)}", ""]
    if nombre.lower().endswith(".pdf"):
        import pdfplumber
        with pdfplumber.open(io.BytesIO(contenido)) as pdf:
            lineas.append(f"Páginas: {len(pdf.pages)}")
            for n, pagina in enumerate(pdf.pages[:4], 1):
                lineas.append(f"=== Página {n}")
                lineas.append(pagina.extract_text() or "(sin texto)")
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
        nombre = Path(urlparse(url).path).name or "archivo"
        try:
            texto = describir(url)
        except Exception as e:  # noqa: BLE001
            texto = f"URL: {url}\nERROR: {e}"
        (salida / f"{nombre}.txt").write_text(texto, encoding="utf-8")
        print(texto[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
