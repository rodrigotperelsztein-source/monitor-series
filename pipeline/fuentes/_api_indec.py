"""Lectura de las tablas del Catálogo API-INDEC que bajó el paso con token (pipeline/indec_api.py).

Las fuentes de INDEC que usan la API la prefieren y, si la tabla no está (sin token, token vencido o API caída),
vuelven a bajar el archivo de siempre del sitio de INDEC. El contenido que se guarda y se compara es una versión
canónica de las filas (ordenada, sin la hora de descarga), para que la huella solo cambie si cambian los datos.
"""

import json
from pathlib import Path

import pandas as pd

from pipeline import indec_api

MARCA = b"INDEC-API\n"


def disponible(tabla: str) -> bool:
    return (indec_api.CARPETA / f"{tabla}.json").exists()


def contenido(tabla: str) -> tuple[str, bytes]:
    """(url, contenido canónico) de una tabla bajada de la API."""
    d = json.loads(Path(indec_api.CARPETA / f"{tabla}.json").read_text(encoding="utf-8"))
    filas = d["filas"]
    if not filas:
        raise ValueError(f"API del INDEC: la tabla {tabla} vino vacía.")
    filas = sorted(filas, key=lambda f: json.dumps(f, sort_keys=True, ensure_ascii=False))
    texto = json.dumps({"tabla": tabla, "filas": filas}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return d["url"], MARCA + texto.encode("utf-8")


def bajar(tabla: str, descargar, respaldo) -> tuple[str, bytes]:
    """Usa la tabla de la API si está; si no, `respaldo()` (la descarga del archivo de siempre)."""
    if disponible(tabla):
        try:
            return contenido(tabla)
        except Exception as e:  # noqa: BLE001
            print(f"  API del INDEC: {tabla} no se pudo leer ({e}); uso el archivo del sitio.")
    else:
        print(f"  API del INDEC: no está {tabla}; uso el archivo del sitio.")
    return respaldo()


def es_api(contenido: bytes) -> bool:
    return contenido.startswith(MARCA)


def filas(contenido: bytes) -> pd.DataFrame:
    d = json.loads(contenido[len(MARCA):].decode("utf-8"))
    df = pd.DataFrame(d["filas"])
    col = "periodo" if "periodo" in df else "Periodo"  # comercio exterior lo escribe con mayúscula
    df["fecha"] = pd.to_datetime(df[col].astype(str).str.replace(r"\D", "", regex=True).str[:6], format="%Y%m")
    return df
