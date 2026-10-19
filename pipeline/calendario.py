"""Calendario de difusión de INDEC: baja el PDF semestral y lo convierte en una tabla.

INDEC publica un PDF por semestre (calendario_1sem2026.pdf, calendario_2sem2026.pdf...)
con dos columnas de tres meses cada una. Cada publicación ocupa una línea; la primera
de cada día empieza con el número y el día de la semana ("21 MI Estimador mensual...").

Resultado: data/calendario/indec.csv con fecha y título de cada publicación.
Cada fuente indica en CALENDARIO el comienzo del título que le corresponde.
"""

import io
import re
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO = RAIZ / "data" / "calendario" / "indec.csv"
URL = "https://www.indec.gob.ar/ftp/cuadros/publicaciones/calendario_{s}sem{anio}.pdf"
HORA = "16:00"  # INDEC publica a las 16 (hora de Buenos Aires)

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
         "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
DIAS = {"LU": 0, "MA": 1, "MI": 2, "JU": 3, "VI": 4, "SA": 5, "DO": 6}
RE_DIA = re.compile(r"^(\d{1,2})\s+(LU|MA|MI|JU|VI|SA|DO)\s+(.*)$")


def semestre(d: date) -> tuple[int, int]:
    return d.year, 1 if d.month <= 6 else 2


def siguiente(anio: int, s: int) -> tuple[int, int]:
    return (anio, 2) if s == 1 else (anio + 1, 1)


def leer_pdf(contenido: bytes, anio: int, s: int) -> pd.DataFrame:
    """Devuelve fecha y título de cada publicación del semestre."""
    import pdfplumber

    filas = []
    with pdfplumber.open(io.BytesIO(contenido)) as pdf:
        for pagina in pdf.pages:
            palabras = pagina.extract_words()
            # Las abreviaturas de los días forman dos columnas de posición x casi fija.
            xs = [round(p["x0"]) for p in palabras if p["text"] in DIAS]
            if not xs:
                continue
            grupos = sorted(x for x, _ in Counter(xs).most_common(2))
            corte = grupos[1] - 22 if len(grupos) == 2 and grupos[1] - grupos[0] > 150 else pagina.width
            columnas = [pagina.crop((0, 0, corte, pagina.height))]
            if corte < pagina.width:
                columnas.append(pagina.crop((corte, 0, pagina.width, pagina.height)))
            for col in columnas:
                filas += _leer_columna(col.extract_text() or "", anio)

    df = pd.DataFrame(filas, columns=["fecha", "dia_semana", "titulo"])
    errores = validar(df, anio, s)
    if errores:
        raise ValueError("Calendario inválido:\n  - " + "\n  - ".join(errores))
    return df[["fecha", "titulo"]].sort_values(["fecha", "titulo"]).reset_index(drop=True)


def _leer_columna(texto: str, anio: int) -> list[list]:
    filas, mes, dia, abrev = [], None, None, None
    for linea in (l.strip() for l in texto.splitlines()):
        if not linea or linea.upper().startswith("CALENDARIO"):
            continue
        if linea.lower() in MESES:
            mes, dia = MESES[linea.lower()], None
            continue
        m = RE_DIA.match(linea)
        if m:
            dia, abrev, titulo = int(m.group(1)), m.group(2), m.group(3)
        elif dia is not None and filas and (linea[0].islower() or linea[0].isdigit()):
            filas[-1][2] += " " + linea  # continuación de un título largo
            continue
        else:
            titulo = linea
        if mes is None or dia is None or titulo.strip().upper() == "INDEC INFORMA":
            continue
        filas.append([date(anio, mes, dia), abrev, titulo.strip()])
    return filas


def validar(df: pd.DataFrame, anio: int, s: int) -> list[str]:
    errores = []
    if len(df) < 60:
        errores.append(f"Solo {len(df)} publicaciones; esperaba más de 60.")
        return errores
    meses = set(range(1, 7)) if s == 1 else set(range(7, 13))
    vistos = {d.month for d in df["fecha"]}
    if vistos != meses:
        errores.append(f"Meses leídos {sorted(vistos)}, esperaba {sorted(meses)}.")
    mal = df[[d.weekday() != DIAS[a] for d, a in zip(df["fecha"], df["dia_semana"])]]
    if len(mal):
        errores.append(f"{len(mal)} fechas no coinciden con el día de la semana, p. ej. "
                       f"{mal.iloc[0]['fecha']} {mal.iloc[0]['dia_semana']}.")
    return errores


def actualizar(descargar, hoy: date) -> str:
    """Baja el semestre actual y el siguiente (si ya está publicado) y actualiza el CSV."""
    anterior = cargar()
    semestres = [semestre(hoy), siguiente(*semestre(hoy))]
    nuevos, notas = [], []
    for anio, s in semestres:
        url = URL.format(s=s, anio=anio)
        try:
            contenido = descargar(url)
        except Exception as e:  # noqa: BLE001
            notas.append(f"{s}.º sem. {anio}: no disponible ({str(e)[:60]})")
            continue
        if not contenido.startswith(b"%PDF"):
            notas.append(f"{s}.º sem. {anio}: todavía no publicado")
            continue
        df = leer_pdf(contenido, anio, s)
        df["semestre"] = f"{anio}-S{s}"
        nuevos.append(df)
        notas.append(f"{s}.º sem. {anio}: {len(df)} publicaciones")
    if not nuevos:
        return "sin calendario nuevo; " + "; ".join(notas)

    tabla = pd.concat(nuevos)
    if anterior is not None:
        tabla = pd.concat([anterior[~anterior["semestre"].isin(tabla["semestre"])], tabla])
    tabla = tabla.sort_values(["fecha", "titulo"])
    ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(ARCHIVO, index=False, date_format="%Y-%m-%d")
    return "; ".join(notas)


def cargar() -> pd.DataFrame | None:
    if not ARCHIVO.exists():
        return None
    df = pd.read_csv(ARCHIVO)
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
    return df


def fechas(prefijo: str, cal: pd.DataFrame | None) -> list[date]:
    """Fechas en que se publica una fuente, según el comienzo de su título."""
    if cal is None or not prefijo:
        return []
    p = prefijo.lower()
    return sorted({f for f, t in zip(cal["fecha"], cal["titulo"]) if str(t).lower().startswith(p)})
