"""CAME: ventas minoristas pyme e industria pyme (IPIP), variación % interanual.

Fuente: Confederación Argentina de la Mediana Empresa (redcame.org.ar). CAME no publica tablas ni
planillas: cada mes difunde un informe de prensa con el resultado en una frase (por ejemplo, "las
ventas minoristas pyme registraron una suba real del 0,3% interanual"). Se leen esos informes.

  - minoristas_var_ia: ventas minoristas pyme a precios constantes (encuesta a unos 1.000 comercios),
    variación % contra el mismo mes del año anterior. Sale en los primeros días del mes siguiente.
    Hasta 2020 CAME la midió en cantidades; desde 2021, a precios constantes. Entre 2019 y 2020 los
    informes dan el resultado de los locales físicos.
  - ipip_var_ia: Índice de Producción Industrial Pyme, variación % interanual. Desde marzo de 2025
    (los informes anteriores no están en el sitio).

Historia (HISTORIA): reconstruida una vez desde el archivo de informes de redcame.org.ar
(septiembre de 2018 en adelante), revisada a mano contra el título de cada informe; los meses
que faltan en el archivo se completaron con la cobertura de prensa del informe de CAME. No se
encontraron julio de 2019 (el informe solo da la variación mensual) ni junio de 2022.

Cada corrida lee las dos primeras páginas de comunicados de prensa, toma los informes de ventas
minoristas e industria pyme y suma los meses nuevos.
"""

import io
import html as htmlmod
import json
import re
import time
import zipfile
from datetime import date

import pandas as pd

from pipeline.fuentes._indec import Columna

ID = "came"
NOMBRE = "CAME: ventas minoristas pyme e industria pyme (variación interanual)"
PAGINA = "https://www.redcame.org.ar/estadisticas-pyme/78/ndice-de-ventas-minoristas"
BASE = "https://www.redcame.org.ar"
LISTADOS = [BASE + "/prensa", BASE + "/prensa/comunicados/p2/"]
URL = LISTADOS[0]
EXTENSION = "zip"
FRECUENCIA = "M"
ORGANISMO = "CAME"
UNIDAD = "%"
PRIMER_PERIODO = "2018-09-01"
CALENDARIO = ""
GUARDAR_ORIGINAL = False

COLUMNAS = {
    "minoristas_var_ia": Columna("", "CAME, ventas minoristas pyme a precios constantes, var. % interanual", tipo="variacion"),
    "ipip_var_ia": Columna("", "CAME, producción industrial pyme (IPIP), var. % interanual", tipo="variacion"),
}

HISTORIA = {
    "minoristas_var_ia": {
    "2018-09": -9.2, "2018-10": -9.4, "2018-11": -15.6, "2018-12": -9.9, "2019-01": -11.6, "2019-02": -14.0,
    "2019-03": -13.2, "2019-04": -13.4, "2019-05": -14.1, "2019-06": -12.2, "2019-08": -18.6, "2019-09": -14.5,
    "2019-10": -11.6, "2019-11": -7.1, "2019-12": -3.8, "2020-01": -3.5, "2020-02": -1.1, "2020-03": -48.7,
    "2020-04": -57.6, "2020-05": -50.8, "2020-06": -34.8, "2020-07": -27.7, "2020-08": -17.8, "2020-09": -10.1,
    "2020-10": -14.9, "2020-11": -6.7, "2020-12": -8.0, "2021-01": -5.8, "2021-02": -6.5, "2021-03": 14.4,
    "2021-04": 40.8, "2021-05": 29.6, "2021-06": 8.6, "2021-07": 11.4, "2021-08": 9.1, "2021-09": 15.7,
    "2021-10": 9.1, "2021-11": 8.9, "2021-12": 4.0, "2022-01": 17.5, "2022-02": 20.7, "2022-03": 15.0,
    "2022-04": 6.0, "2022-05": -3.4, "2022-07": -3.5, "2022-08": -2.1, "2022-09": -3.5, "2022-10": -3.2,
    "2022-11": -3.1, "2022-12": 2.7, "2023-01": -0.3, "2023-02": -0.9, "2023-03": -0.1, "2023-04": -0.1,
    "2023-05": -2.8, "2023-06": -3.6, "2023-07": -3.6, "2023-08": -4.1, "2023-09": -5.1, "2023-10": -0.7,
    "2023-11": -2.9, "2023-12": -13.7, "2024-01": -28.5, "2024-02": -25.5, "2024-03": -12.6, "2024-04": -7.3,
    "2024-05": -7.3, "2024-06": -21.9, "2024-07": -15.7, "2024-08": -10.5, "2024-09": -5.2, "2024-10": 2.9,
    "2024-11": -1.7, "2024-12": 17.7, "2025-01": 25.5, "2025-02": 24.0, "2025-03": 10.5, "2025-04": 3.7,
    "2025-05": -2.9, "2025-06": -0.5, "2025-07": -2.0, "2025-08": -2.6, "2025-09": -4.2, "2025-10": -1.4,
    "2025-11": -4.1, "2025-12": -5.2, "2026-01": -4.8, "2026-02": -5.6, "2026-03": -0.6, "2026-04": -3.2,
    "2026-05": -1.2, "2026-06": 0.9, "2026-07": -3.8, "2026-08": -0.2, "2026-09": 0.3,
    },
    "ipip_var_ia": {
    "2025-03": 2.4, "2025-04": 3.7, "2025-05": 0.8, "2025-06": -1.0, "2025-07": -1.5, "2025-08": -4.7,
    "2025-09": -5.2, "2025-10": -3.2, "2025-12": -6.8, "2026-01": -7.3, "2026-02": -7.9, "2026-03": -3.8,
    "2026-04": -7.3, "2026-05": -7.8, "2026-06": -7.1, "2026-07": -3.9, "2026-08": -6.1,
    },
}

MESES = {m: i + 1 for i, m in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                                          "agosto", "septiembre", "octubre", "noviembre", "diciembre"])}
NEG = r"(ca[ií]d|cay|baj|descen|contracci|retroce|retraj|declin|derrumb|disminu|retracci)"
POS = r"(sub|aument|crec|alza|increment|mejor)"
NOTA = re.compile(r'href="(/prensa/\d+/[^"]*(?:ventas-minoristas-pyme|produccion-industrial-pyme)[^"]*)"')


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    notas = []
    for url in LISTADOS:
        texto = descargar(url, minimo=5_000).decode("utf-8", "replace")
        notas += [BASE + h for h in NOTA.findall(texto) if not re.search(r"navidad|reyes|madre|padre|nino|ninez", h)]
    notas = list(dict.fromkeys(notas))
    if not notas:
        raise ValueError("No encontré informes de ventas minoristas ni de industria pyme en los comunicados de CAME.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("notas.json", json.dumps(notas))
        for i, url in enumerate(notas):
            time.sleep(1)
            z.writestr(f"{i}.html", descargar(url, minimo=5_000))
    return " ".join(LISTADOS), buf.getvalue()


def _texto(h: str) -> str:
    h = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    return re.sub(r"\s+", " ", htmlmod.unescape(re.sub(r"<[^>]+>", " ", h)))


def extraer(url: str, h: str) -> tuple[str, str, float] | None:
    """(columna, "AAAA-MM", variación interanual) de un informe, o None si no se reconoce."""
    t = _texto(h)
    m = re.search(r"(\d{1,2}) de (\w+) (\d{4}) \| \d{1,2}:\d{2}", t)
    if not m or m[2].lower() not in MESES:
        return None
    anio_pub, mes_pub = int(m[3]), MESES[m[2].lower()]
    col = "ipip_var_ia" if "industrial" in url else "minoristas_var_ia"
    meses = [MESES[x] for x in re.findall("|".join(MESES), url.rsplit("/", 1)[-1])]
    mes = 1 if "inicio-del-ano" in url else (meses[0] if meses else (mes_pub - 1 or 12))
    anio = anio_pub if mes <= mes_pub else anio_pub - 1
    for s in re.split(r"(?<=[.])\s", t[m.end():m.end() + 4000]):
        if not re.search(r"interanual|anual|mismo (mes|per[ií]odo)|igual mes", s):
            continue
        n = re.search(r"(-?\d+(?:,\d+)?)\s?%", s)
        if not n:
            continue
        antes = s[:n.start()].lower()
        if re.search(r"acumul|primer (bimestre|trimestre|semestre)|primeros", antes):
            continue
        v = float(n[1].replace(",", "."))
        if v > 0:
            neg = [x.end() for x in re.finditer(NEG, antes)]
            pos = [x.end() for x in re.finditer(POS, antes)]
            if (max(neg) if neg else -1) > (max(pos) if pos else -1):
                v = -v
        # Control con el título: el número del enlace (sin coma) tiene que coincidir.
        slug = re.search(r"-(\d+)-(?:interanual|anual|en-)", url)
        if slug and slug[1] != f"{abs(v):g}".replace(".", ""):
            return None
        return col, f"{anio}-{mes:02d}", v
    return None


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    datos = {c: dict(HISTORIA[c]) for c in columnas}
    nuevos = {}
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        notas = json.loads(z.read("notas.json"))
        for i, url in enumerate(notas):
            r = extraer(url, z.read(f"{i}.html").decode("utf-8", "replace"))
            if r:
                col, periodo, v = r
                if periodo in datos[col] and abs(datos[col][periodo] - v) > 0.05:
                    raise ValueError(f"{col} {periodo}: el informe dice {v} y la historia {datos[col][periodo]} ({url}).")
                datos[col].setdefault(periodo, v)
                nuevos[f"{col} {periodo}"] = url
    fechas = pd.period_range(PRIMER_PERIODO[:7], max(max(d) for d in datos.values()), freq="M")
    out = pd.DataFrame({"fecha": fechas.to_timestamp()})
    for c in columnas:
        out[c] = [datos[c].get(str(p)) for p in fechas]
    out.attrs["informes_leidos"] = nuevos
    return out


def meta_extra(nuevo: pd.DataFrame) -> dict:
    return {"informes_leidos": nuevo.attrs.get("informes_leidos", {})}


def combinar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None) -> pd.DataFrame:
    """Los meses leídos en corridas anteriores (que ya no están en las páginas de comunicados) se conservan."""
    if anterior is None or not len(anterior):
        return nuevo
    n, a = nuevo.set_index("fecha"), anterior.set_index("fecha").reindex(columns=nuevo.columns[1:])
    todas = n.index.union(a.index)
    n = n.reindex(todas).combine_first(a.reindex(todas))
    return n.reset_index().rename(columns={"index": "fecha"})[list(nuevo.columns)]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    esperado = pd.date_range(PRIMER_PERIODO, periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los meses no son consecutivos.")
    for c in columnas:
        if not nuevo[c].dropna().between(-80, 80).all():
            errores.append(f"{c}: variación fuera de rango (±80%).")
    if anterior is not None and len(anterior):
        comunes = nuevo.merge(anterior, on="fecha", suffixes=("", "_ant"))
        for c in columnas:
            if ((comunes[c] - comunes[f"{c}_ant"]).abs() > 0.05).any():
                errores.append(f"{c}: cambió un mes ya publicado.")
    return errores
