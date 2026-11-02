"""Índice de tipo de cambio real multilateral (ITCRM) del BCRA y bilaterales, diario.

Fuente: BCRA, planilla itcrm-serie.xlsx (hoja "ITCRM y bilaterales"), base 17-12-2015 = 100, desde 1997. Mide el
precio de los bienes de los socios comerciales en relación con los argentinos: si sube, el peso se deprecia en términos
reales (la economía gana competitividad cambiaria); si baja, se aprecia. El multilateral pondera a los socios por su
peso en el comercio; los bilaterales comparan con un solo país. Los datos de los últimos meses son provisorios: usan
inflación estimada (REM y relevamientos) hasta que se publican los IPC, así que se revisan.
"""

import io

import pandas as pd

from pipeline.fuentes._indec import Columna

ID = "itcrm"
NOMBRE = "Tipo de cambio real multilateral y bilaterales (BCRA), diario"
PAGINA = "https://www.bcra.gob.ar/indices-de-tipo-de-cambio-multilateral/"
URL = "https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/itcrm-serie.xlsx"
EXTENSION = "xlsx"
FRECUENCIA = "D"
ORGANISMO = "BCRA"
UNIDAD = "Índice 17-12-2015=100"
PRIMER_PERIODO = "1997-01-01"
CALENDARIO = ""
GUARDAR_ORIGINAL = False
HOJA = "ITCRM y bilaterales"

# id -> (encabezado en la planilla, nombre)
SOCIOS = {"multilateral": ("ITCRM", "Tipo de cambio real multilateral (ITCRM)"),
          "brasil": ("ITCRB Brasil", "Tipo de cambio real bilateral con Brasil"),
          "estados_unidos": ("ITCRB Estados Unidos", "Tipo de cambio real bilateral con Estados Unidos"),
          "china": ("ITCRB China", "Tipo de cambio real bilateral con China"),
          "zona_euro": ("ITCRB Zona Euro", "Tipo de cambio real bilateral con la zona del euro"),
          "chile": ("ITCRB Chile", "Tipo de cambio real bilateral con Chile"),
          "uruguay": ("ITCRB Uruguay", "Tipo de cambio real bilateral con Uruguay"),
          "mexico": ("ITCRB México", "Tipo de cambio real bilateral con México"),
          "canada": ("ITCRB Canadá", "Tipo de cambio real bilateral con Canadá"),
          "india": ("ITCRB India", "Tipo de cambio real bilateral con India"),
          "japon": ("ITCRB Japón", "Tipo de cambio real bilateral con Japón"),
          "reino_unido": ("ITCRB Reino Unido", "Tipo de cambio real bilateral con el Reino Unido"),
          "suiza": ("ITCRB Suiza", "Tipo de cambio real bilateral con Suiza"),
          "vietnam": ("ITCRB Vietnam", "Tipo de cambio real bilateral con Vietnam"),
          "sudamerica": ("ITCRB Sudamérica", "Tipo de cambio real bilateral con Sudamérica (promedio de Brasil, Chile y Uruguay)")}
COLUMNAS = {k: Columna("", n) for k, (_, n) in SOCIOS.items()}


def leer_hoja(contenido: bytes, hoja: str) -> pd.DataFrame:
    d = pd.read_excel(io.BytesIO(contenido), sheet_name=hoja, header=1)
    d.columns = [str(c).strip().rstrip("*").strip() for c in d.columns]
    faltan = [enc for enc, _ in SOCIOS.values() if enc not in d.columns]
    if "Período" not in d.columns or faltan:
        raise ValueError(f"La planilla del ITCRM cambió de formato: faltan {faltan or ['Período']}")
    d["fecha"] = pd.to_datetime(d["Período"], errors="coerce")
    d = d[d["fecha"].notna()]  # saca las notas al pie
    out = pd.DataFrame({"fecha": d["fecha"].values})
    for k, (enc, _) in SOCIOS.items():
        out[k] = pd.to_numeric(d[enc], errors="coerce").values
    return out.sort_values("fecha").reset_index(drop=True)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    return leer_hoja(contenido, HOJA)[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS, minimo: int = 5000,
            dias: int = 15, base_diaria: bool = True) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    if len(nuevo) < minimo:
        errores.append(f"Solo {len(nuevo)} filas.")
    if not nuevo["fecha"].is_monotonic_increasing or nuevo["fecha"].duplicated().any():
        errores.append("Fechas desordenadas o repetidas.")
    m = nuevo["multilateral"].dropna()
    if not m.between(20, 400).all():
        errores.append("ITCRM fuera de rango.")
    # El índice vale 100 el 17-12-2015 (base).
    base = nuevo.loc[nuevo["fecha"] == "2015-12-17", "multilateral"]
    if base_diaria and (len(base) != 1 or abs(float(base.iloc[0]) - 100) > 0.5):
        errores.append("El ITCRM no vale 100 el 17-12-2015: ¿cambió la base?")
    if len(m) and (pd.Timestamp.today() - nuevo.loc[m.index[-1], "fecha"]).days > dias:
        errores.append(f"El último dato tiene más de {dias} días.")
    return errores

