"""IPC por apertura: los grupos y las clases que el INDEC publica para cada una de las seis regiones.

Es el nivel de desagregación que está abajo de las divisiones: dentro de "Transporte" aparecen
"Combustibles y lubricantes para vehículos de uso del hogar" y "Transporte público", que se mueven por razones
distintas y pesan distinto en cada región. El nivel general y las doce divisiones no se repiten acá: ya están en
la fuente ipc, que además trae el total nacional y las categorías (núcleo, regulados, estacionales).

El INDEC no publica el nacional de las aperturas, solo el de las divisiones, así que acá hay seis regiones y no
siete. El nombre de cada serie lleva la ponderación de la apertura en la canasta de su región, que es fija para
toda la base diciembre 2016 = 100 y sale de data/referencia/ipc_ponderadores.csv (ver
pipeline/herramientas/ipc_ponderadores.py). La única apertura sin ponderación publicada es 06.4.1 (gastos de
prepagas): la metodología llega hasta el grupo 06.4.

Fuente: INDEC, Índice de precios al consumidor, base diciembre 2016=100.
Datos: serie_ipc_aperturas.csv (formato largo, separador ";", coma decimal, codificación latin-1). El archivo
repite el mismo código con descripciones que difieren en mayúsculas o espacios: se toma la primera.
"""

import csv
import io
from pathlib import Path

import pandas as pd

from pipeline.fuentes._indec import Columna, slug, validar_tabla

ID = "ipc_aperturas"
NOMBRE = "IPC por apertura (grupos y clases), por región"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipc_aperturas.csv"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-5-31"
EXTENSION = "csv"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Índice base dic-2016=100"
PRIMER_PERIODO = "2016-12-01"
CALENDARIO = "Índice de precios al consumidor (IPC)"

REGIONES = ["GBA", "Pampeana", "Noreste", "Noroeste", "Cuyo", "Patagonia"]
# El nivel general y las divisiones ya están en la fuente ipc: acá se saltean para no duplicar series.
EN_IPC = {"0", *(f"{i:02d}" for i in range(1, 13))}
COLUMNAS_CSV = ["Codigo", "Descripcion_aperturas", "Clasificador", "Periodo", "Indice_IPC", "v_m_IPC", "v_i_a_IPC",
                "Region"]
PONDERADORES = Path(__file__).resolve().parents[2] / "data" / "referencia" / "ipc_ponderadores.csv"
MEDIDAS = {"indice": "Indice_IPC", "var_m": "v_m_IPC", "var_ia": "v_i_a_IPC"}
AISLAMIENTO = ("2020-04-01", "2020-07-01")  # meses sin relevamiento de algunos rubros (ver validar)


def _ponderadores() -> dict[tuple[str, str], float]:
    """{(código, región): ponderación en la canasta de esa región}, de la metodología del IPC."""
    with PONDERADORES.open(encoding="utf8") as f:
        filas = list(csv.DictReader(f))
    return {(fila["codigo"], region): float(fila[slug(region)])
            for fila in filas if fila["codigo"] for region in REGIONES}


def _tabla(contenido: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(contenido), sep=";", decimal=",", encoding="latin-1", na_values=["NA", ""],
                     dtype={"Codigo": str})
    if list(df.columns) != COLUMNAS_CSV:
        raise ValueError(f"Columnas del CSV inesperadas: {list(df.columns)}")
    df["Codigo"] = df["Codigo"].str.strip()
    df["fecha"] = pd.to_datetime(df["Periodo"].astype(str), format="%Y%m")
    return df[~df["Codigo"].isin(EN_IPC)]


def columnas(contenido: bytes) -> dict[str, Columna]:
    df = _tabla(contenido)
    desc = df.dropna(subset=["Descripcion_aperturas"]).groupby("Codigo")["Descripcion_aperturas"].first()
    aperturas = sorted(desc.index)
    # No todas las aperturas salen en todas las regiones: 04.3 y 09.1, por ejemplo, solo en GBA.
    hay = set(zip(df["Region"], df["Codigo"]))
    faltan = {r for r in REGIONES if not any((r, c) in hay for c in aperturas)}
    if faltan or len(aperturas) < 25:
        raise ValueError(f"El CSV no trae lo esperado: regiones sin datos {sorted(faltan)}, "
                         f"{len(aperturas)} aperturas")
    pond = _ponderadores()
    cols = {}
    for region in REGIONES:
        for codigo in aperturas:
            if (region, codigo) not in hay:
                continue
            p = pond.get((codigo, region))
            detalle = codigo if p is None else f"{codigo} · pond. {f'{p:.2f}'.replace('.', ',')}%"
            base = f"IPC {region} - {str(desc[codigo]).strip().capitalize()} ({detalle})"
            k = f"{slug(region)}_{slug(codigo)}"
            cols[f"{k}_indice"] = Columna(f"{region}|{codigo}|Indice_IPC", f"{base} - índice")
            cols[f"{k}_var_m"] = Columna(f"{region}|{codigo}|v_m_IPC", f"{base} - var. % mensual",
                                         tipo="variacion", base=f"{k}_indice", rezago=1)
            cols[f"{k}_var_ia"] = Columna(f"{region}|{codigo}|v_i_a_IPC", f"{base} - var. % interanual",
                                          tipo="variacion", base=f"{k}_indice", rezago=12)
    return cols


def leer(contenido: bytes, columnas: dict[str, Columna]) -> pd.DataFrame:
    df = _tabla(contenido)
    ancho = df.pivot_table(index="fecha", columns=["Region", "Codigo"], values=list(MEDIDAS.values()),
                           aggfunc="first")
    partes = {}
    for cid, col in columnas.items():
        region, codigo, medida = col.prefijo.split("|")
        partes[cid] = ancho[(medida, region, codigo)]
    return pd.concat(partes, axis=1).reset_index()[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas: dict[str, Columna]) -> list[str]:
    # Durante el aislamiento de 2020 no se pudo relevar prendas, calzado ni restaurantes, y esas aperturas quedaron
    # en blanco. Se les permite el hueco de esos meses (y los vacíos iniciales de cada variación), nada más: si
    # falta un mes reciente, la fuente falla.
    permitidos = set()
    for cid, col in columnas.items():
        faltan = nuevo.loc[nuevo[cid].isna(), "fecha"]
        arranque = nuevo["fecha"].iloc[col.rezago or 0]
        if not faltan.empty and (faltan.between(*AISLAMIENTO) | (faltan < arranque)).all():
            permitidos.add(cid)
    return validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, rango_nivel=(0, 1e7), max_variacion=1000,
                         tol_variacion=0.1, vacios_permitidos=permitidos)
