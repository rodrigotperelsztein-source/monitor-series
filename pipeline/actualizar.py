"""Actualiza las series: baja cada archivo de origen, lo procesa solo si cambió,
valida y guarda los resultados en data/.

Uso (desde la raíz del repositorio):
    python -m pipeline.actualizar              # todas las fuentes
    python -m pipeline.actualizar emae_letras  # una sola
    python -m pipeline.actualizar --forzar     # procesa aunque el archivo no haya cambiado

Sale con código 1 si alguna fuente falla la descarga, la lectura o la validación;
en ese caso no se modifica nada de esa fuente.
"""

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from pipeline.fuentes import emae_letras

FUENTES = {f.ID: f for f in [emae_letras]}

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"


def descargar(url: str, intentos: int = 3) -> bytes:
    ultimo = None
    for i in range(intentos):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
            r.raise_for_status()
            if len(r.content) < 1000:
                raise ValueError(f"Respuesta demasiado chica ({len(r.content)} bytes)")
            return r.content
        except Exception as e:  # noqa: BLE001
            ultimo = e
            print(f"  intento {i + 1} falló: {e}")
            time.sleep(10 * (i + 1))
    raise RuntimeError(f"No pude descargar {url}: {ultimo}")


def leer_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def leer_csv(p: Path) -> pd.DataFrame | None:
    return pd.read_csv(p, parse_dates=["fecha"]) if p.exists() else None


def registrar_revisiones(fid: str, nuevo: pd.DataFrame, anterior: pd.DataFrame | None, ahora: str) -> int:
    if anterior is None:
        return 0
    cols = [c for c in nuevo.columns if c != "fecha"]
    comunes = nuevo.merge(anterior, on="fecha", suffixes=("", "_ant"))
    filas = []
    for c in cols:
        cambio = (comunes[c] - comunes[f"{c}_ant"]).abs() > 1e-6
        for _, r in comunes[cambio].iterrows():
            filas.append({"detectado": ahora, "periodo": f"{r['fecha']:%Y-%m}", "serie": c,
                          "valor_anterior": r[f"{c}_ant"], "valor_nuevo": r[c]})
    if filas:
        p = DATA / "revisiones" / f"{fid}.csv"
        p.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(filas).to_csv(p, mode="a", header=not p.exists(), index=False)
    return len(filas)


def escribir_excel(fuente, df: pd.DataFrame, meta: dict) -> None:
    p = DATA / "excel" / f"{fuente.ID}.xlsx"
    p.parent.mkdir(parents=True, exist_ok=True)
    nombres = {sid: nombre for sid, (_, nombre) in fuente.SECTORES.items()}
    with pd.ExcelWriter(p, engine="openpyxl") as xw:
        df.rename(columns=nombres).to_excel(xw, sheet_name="Niveles", index=False)
        pd.DataFrame([
            ["Serie", fuente.NOMBRE], ["Unidad", fuente.UNIDAD], ["Fuente", fuente.PAGINA],
            ["Archivo de origen", fuente.URL], ["Descargado (UTC)", meta["descargado"]],
            ["Último período", meta["ultimo_periodo"]],
        ]).to_excel(xw, sheet_name="Datos de la serie", index=False, header=False)
        hoja = xw.sheets["Niveles"]
        hoja.column_dimensions["A"].width = 12
        for fila in hoja.iter_rows(min_row=2, max_col=1):
            fila[0].number_format = "mmm-yyyy"


def procesar(fuente, forzar: bool, ahora: str) -> str:
    fid = fuente.ID
    p_meta = DATA / "meta" / f"{fid}.json"
    p_csv = DATA / f"{fid}.csv"
    meta = leer_json(p_meta)

    contenido = descargar(fuente.URL)
    huella = hashlib.sha256(contenido).hexdigest()
    if huella == meta.get("sha256") and not forzar:
        # No se escribe nada: así el repositorio solo registra cambios reales.
        return "sin cambios en el archivo"

    nuevo = fuente.leer(contenido)
    anterior = leer_csv(p_csv)
    errores = fuente.validar(nuevo, anterior)
    if errores:
        raise ValueError("Validación fallida:\n  - " + "\n  - ".join(errores))

    meta.update({
        "id": fid, "nombre": fuente.NOMBRE, "url": fuente.URL, "pagina": fuente.PAGINA,
        "frecuencia": fuente.FRECUENCIA, "unidad": fuente.UNIDAD, "sha256": huella,
    })

    datos_iguales = anterior is not None and nuevo.shape == anterior.shape and \
        (nuevo.drop(columns="fecha").sub(anterior.drop(columns="fecha")).abs() < 1e-6).all().all()
    if datos_iguales:
        p_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return "archivo distinto pero mismos datos"

    revisados = registrar_revisiones(fid, nuevo, anterior, ahora)
    raw = DATA / "raw" / fid / f"{ahora[:10]}_{huella[:8]}.{fuente.EXTENSION}"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(contenido)

    nuevo.to_csv(p_csv, index=False, date_format="%Y-%m-%d", float_format="%.6f")
    meta.update({"descargado": ahora, "ultimo_periodo": f"{nuevo['fecha'].max():%Y-%m}",
                 "observaciones": len(nuevo), "original_guardado": str(raw.relative_to(RAIZ))})
    p_meta.parent.mkdir(parents=True, exist_ok=True)
    p_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    escribir_excel(fuente, nuevo, meta)

    ant = f"{anterior['fecha'].max():%Y-%m}" if anterior is not None else "—"
    return f"actualizada: último período {ant} → {meta['ultimo_periodo']}; valores revisados: {revisados}"


def catalogo() -> None:
    filas = [leer_json(p) for p in sorted((DATA / "meta").glob("*.json"))]
    if filas:
        cols = ["id", "nombre", "frecuencia", "unidad", "ultimo_periodo", "observaciones",
                "descargado", "pagina", "url"]
        pd.DataFrame(filas).reindex(columns=cols).to_csv(DATA / "catalogo.csv", index=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fuentes", nargs="*", help="ids a procesar (por defecto, todas)")
    ap.add_argument("--forzar", action="store_true")
    args = ap.parse_args()

    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ids = args.fuentes or list(FUENTES)
    (DATA / "meta").mkdir(parents=True, exist_ok=True)
    fallas = 0
    for fid in ids:
        print(f"[{fid}]")
        try:
            print("  " + procesar(FUENTES[fid], args.forzar, ahora))
        except Exception as e:  # noqa: BLE001
            fallas += 1
            print(f"  ERROR: {e}")
    catalogo()
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
