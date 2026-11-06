"""Universidad Torcuato Di Tella: Índice Líder (Centro de Investigación en Finanzas), Índice de Confianza del Consumidor
(nacional, por región y por subíndice) e Índice de Confianza en el Gobierno (Escuela de Gobierno).

La UTDT ofrece las series históricas para descarga gratuita; el nombre de cada planilla cambia con cada publicación
(download.php?fname=_<número>.xls), así que el enlace se toma de la página de cada índice.
"""

import io
import zipfile
from datetime import date

import pandas as pd

from pipeline.fuentes import _enlace
from pipeline.fuentes._indec import Columna, norm
from pipeline.fuentes.deuda import _mes

ID = "utdt"
NOMBRE = "Índice Líder, confianza del consumidor y confianza en el gobierno (UTDT)"
PAGINAS = {"lider": "https://www.utdt.edu/ver_contenido.php?id_contenido=13306&id_item_menu=16461",
           "icc": "https://www.utdt.edu/ver_contenido.php?id_contenido=8513&id_item_menu=16458",
           "icg": "https://www.utdt.edu/listado_contenidos.php?id_item_menu=28756"}
PAGINA = "https://www.utdt.edu/ver_contenido.php?id_contenido=27166&id_item_menu=44662"
URL = PAGINA
EXTENSION = "zip"
FRECUENCIA = "M"
ORGANISMO = "Universidad Torcuato Di Tella"
UNIDAD = "Según la serie"
CALENDARIO = ""
ARCHIVO = r"download\.php\?fname=_\d+\.xls$"

COLUMNAS = {
    "indice_lider": Columna("", "Índice Líder de la actividad (UTDT), desestacionalizado", unidad="Índice 2004=100"),
    "indice_lider_var_m": Columna("", "Índice Líder, var. % mensual", unidad="%", tipo="variacion", base="indice_lider", rezago=1),
    "difusion_lider": Columna("", "Índice de difusión del Índice Líder (% de series que suben)", unidad="%"),
    "confianza_consumidor": Columna("", "Índice de Confianza del Consumidor, nacional", unidad="Índice 0-100"),
    "confianza_consumidor_caba": Columna("", "Índice de Confianza del Consumidor: Capital Federal", unidad="Índice 0-100"),
    "confianza_consumidor_gba": Columna("", "Índice de Confianza del Consumidor: Gran Buenos Aires", unidad="Índice 0-100"),
    "confianza_consumidor_interior": Columna("", "Índice de Confianza del Consumidor: interior", unidad="Índice 0-100"),
    "confianza_situacion_personal": Columna("", "Confianza del consumidor: subíndice situación personal", unidad="Índice 0-100"),
    "confianza_situacion_macro": Columna("", "Confianza del consumidor: subíndice situación macroeconómica", unidad="Índice 0-100"),
    "confianza_durables": Columna("", "Confianza del consumidor: subíndice bienes durables e inmuebles", unidad="Índice 0-100"),
    "confianza_gobierno": Columna("", "Índice de Confianza en el Gobierno", unidad="Índice 0-5"),
}


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    buf, urls = io.BytesIO(), []
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for k, pagina in PAGINAS.items():
            url = _enlace.buscar(descargar, pagina, ARCHIVO)
            urls.append(url)
            z.writestr(f"{k}.xls", descargar(url, minimo=10_000))
    return " ".join(urls), buf.getvalue()


def _largo(h: pd.DataFrame, columnas: dict[str, int]) -> pd.DataFrame:
    """Planilla con fechas en la primera columna."""
    f = pd.Series([_mes(v) for v in h.iloc[:, 0]], index=h.index)
    d = h[f.notna()]
    return pd.DataFrame({k: pd.to_numeric(d.iloc[:, j], errors="coerce").values for k, j in columnas.items()},
                        index=pd.DatetimeIndex(f[f.notna()]))


def _encabezado(h: pd.DataFrame, filas: int = 3) -> dict[int, str]:
    """Texto del encabezado de cada columna, sin el título de la planilla (celdas con "DESAGREGACION")."""
    return {j: norm(" ".join(str(v) for v in h.iloc[:filas, j] if pd.notna(v) and "DESAGREGACI" not in norm(v)))
            for j in range(h.shape[1])}


def _columna(enc: dict[int, str], *palabras: str, excluir: str = "VARIACION") -> int:
    js = [j for j, t in enc.items() if all(p in t for p in palabras) and excluir not in t]
    if len(js) != 1:
        raise ValueError(f"No encontré una sola columna con {palabras} ({len(js)}).")
    return js[0]


def _lider(contenido: bytes) -> pd.DataFrame:
    h = pd.read_excel(io.BytesIO(contenido), sheet_name=0, header=None)
    enc = _encabezado(h, 1)
    return _largo(h, {"indice_lider": _columna(enc, "LIDER"), "difusion_lider": _columna(enc, "DIFUSION")})


def _icc(contenido: bytes) -> pd.DataFrame:
    libro = pd.read_excel(io.BytesIO(contenido), sheet_name=None, header=None)
    reg = next(v for k, v in libro.items() if "REGIONES" in norm(k))
    sub = next(v for k, v in libro.items() if "SUBINDICES" in norm(k).replace("Í", "I"))
    er, es = _encabezado(reg), _encabezado(sub)
    a = _largo(reg, {"confianza_consumidor": _columna(er, "NACIONAL"), "confianza_consumidor_caba": _columna(er, "CAPITAL"),
                     "confianza_consumidor_gba": _columna(er, "GBA"), "confianza_consumidor_interior": _columna(er, "INTERIOR")})
    b = _largo(sub, {"confianza_situacion_personal": _columna(es, "PERSONAL"),
                     "confianza_situacion_macro": _columna(es, "MACRO"), "confianza_durables": _columna(es, "DURABLES")})
    return a.join(b, how="outer")


def _icg(contenido: bytes) -> pd.DataFrame:
    serie = {}
    for h in pd.read_excel(io.BytesIO(contenido), sheet_name=None, header=None).values():
        fila_f = next(i for i in range(len(h)) if sum(_mes(v) is not None for v in h.iloc[i]) >= 12)
        fila_v = next(i for i in range(len(h)) if any(norm(v) == "ICG" for v in h.iloc[i] if pd.notna(v)))
        for j, v in enumerate(h.iloc[fila_f]):
            if (f := _mes(v)) is not None and pd.notna(h.iloc[fila_v, j]):
                serie[f] = float(h.iloc[fila_v, j])
    return pd.DataFrame({"confianza_gobierno": pd.Series(serie)})


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        df = _lider(z.read("lider.xls")).join(_icc(z.read("icc.xls")), how="outer").join(_icg(z.read("icg.xls")), how="outer")
    df = df.sort_index()
    df = df.reindex(pd.date_range(df.index.min(), df.index.max(), freq="MS"))
    df["difusion_lider"] = df["difusion_lider"] * 100  # la planilla la da como proporción
    df["indice_lider_var_m"] = (df["indice_lider"] / df["indice_lider"].shift(1) - 1) * 100
    df.index.name = "fecha"
    return df.reset_index()[["fecha", *columnas]]


def validar(nuevo, anterior, columnas=COLUMNAS):
    errores = []
    hoy = pd.Timestamp.today()
    for c, rango, atraso in (("indice_lider", (20, 300), 100), ("confianza_consumidor", (0, 100), 70),
                             ("confianza_gobierno", (0, 5), 70)):
        s = nuevo.set_index("fecha")[c].dropna()
        if not s.between(*rango).all():
            errores.append(f"{c} fuera de rango.")
        if (hoy - s.index.max()).days > atraso:
            errores.append(f"{c}: el último dato está atrasado.")
    if anterior is not None and len(anterior):
        for c in columnas:
            if c in anterior and nuevo[c].count() < anterior[c].count():
                errores.append(f"{c}: se perdió historia.")
    return errores
