"""IPC: nivel general, divisiones, categorías (núcleo, regulados, estacionales) y bienes y
servicios, para el total nacional y las seis regiones. Índice, variación mensual e interanual.

Fuente: INDEC, Índice de precios al consumidor, base diciembre 2016=100.
Archivo: serie_ipc_divisiones.csv (formato largo, separador ";", coma decimal, codificación latin-1).
INDEC publica los índices con cuatro decimales y las variaciones con uno; el pipeline las
recalcula desde los índices con una tolerancia de 0,1 puntos.
"""

import io

import pandas as pd

from pipeline.fuentes._indec import Columna, slug, validar_tabla

ID = "ipc"
NOMBRE = "IPC: nivel general, divisiones y categorías, por región"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipc_divisiones.csv"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-5-31"
EXTENSION = "csv"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Índice base dic-2016=100"
PRIMER_PERIODO = "2016-12-01"
CALENDARIO = "Índice de precios al consumidor (IPC)"

REGIONES = ["Nacional", "GBA", "Pampeana", "Noreste", "Noroeste", "Cuyo", "Patagonia"]
NOMBRES_FIJOS = {"0": "Nivel general", "Núcleo": "Núcleo", "Regulados": "Regulados",
                 "Estacional": "Estacionales", "B": "Bienes", "S": "Servicios"}
ORDEN = ["0", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
         "Núcleo", "Regulados", "Estacional", "B", "S"]
COLUMNAS_CSV = ["Codigo", "Descripcion", "Clasificador", "Periodo", "Indice_IPC", "v_m_IPC", "v_i_a_IPC", "Region"]


def _tabla(contenido: bytes) -> pd.DataFrame:
    for cod in ("utf-8", "latin-1"):
        try:
            texto = contenido.decode(cod)
            break
        except UnicodeDecodeError:
            continue
    df = pd.read_csv(io.StringIO(texto), sep=";", decimal=",", na_values=["NA", ""], dtype={"Codigo": str})
    if list(df.columns) != COLUMNAS_CSV:
        raise ValueError(f"Columnas del CSV inesperadas: {list(df.columns)}")
    df["fecha"] = pd.to_datetime(df["Periodo"].astype(str), format="%Y%m")
    return df


def _clave(region: str, codigo: str) -> str:
    return f"{slug(region)}_{slug(NOMBRES_FIJOS.get(codigo, 'div_' + codigo))}"


def columnas(contenido: bytes) -> dict[str, Columna]:
    df = _tabla(contenido)
    desc = df.dropna(subset=["Descripcion"]).groupby("Codigo")["Descripcion"].first().to_dict()
    faltan = {(r, c) for r in REGIONES for c in ORDEN} - set(zip(df["Region"], df["Codigo"]))
    if faltan:
        raise ValueError(f"Faltan combinaciones región/apertura en el CSV: {sorted(faltan)[:5]}")
    cols = {}
    for region in REGIONES:
        for codigo in ORDEN:
            nombre = NOMBRES_FIJOS.get(codigo) or str(desc.get(codigo, codigo)).strip().capitalize()
            k = _clave(region, codigo)
            base = f"IPC {region} - {nombre}"
            cols[f"{k}_indice"] = Columna(f"{region}|{codigo}|Indice_IPC", f"{base} - índice")
            cols[f"{k}_var_m"] = Columna(f"{region}|{codigo}|v_m_IPC", f"{base} - var. % mensual",
                                         tipo="variacion", base=f"{k}_indice", rezago=1)
            cols[f"{k}_var_ia"] = Columna(f"{region}|{codigo}|v_i_a_IPC", f"{base} - var. % interanual",
                                          tipo="variacion", base=f"{k}_indice", rezago=12)
    return cols


def leer(contenido: bytes, columnas: dict[str, Columna]) -> pd.DataFrame:
    df = _tabla(contenido)
    ancho = df.pivot_table(index="fecha", columns=["Region", "Codigo"],
                           values=["Indice_IPC", "v_m_IPC", "v_i_a_IPC"], aggfunc="first")
    partes = {}
    for cid, col in columnas.items():
        region, codigo, medida = col.prefijo.split("|")
        partes[cid] = ancho[(medida, region, codigo)]
    return pd.concat(partes, axis=1).reset_index()[["fecha"] + list(columnas)]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas: dict[str, Columna]) -> list[str]:
    return validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, rango_nivel=(0, 1e7),
                         max_variacion=1000, tol_variacion=0.1)
