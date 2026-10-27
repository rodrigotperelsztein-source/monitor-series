"""Actualiza las series: baja cada archivo de origen, lo procesa solo si cambió,
valida y guarda los resultados en data/.

Uso (desde la raíz del repositorio):
    python -m pipeline.actualizar                    # control completo: calendario y todas las fuentes
    python -m pipeline.actualizar --modo calendario  # solo las fuentes que INDEC publica hoy
    python -m pipeline.actualizar emae_letras        # una sola fuente
    python -m pipeline.actualizar --forzar           # procesa aunque el archivo no haya cambiado

Modo completo: sale con código 1 si alguna fuente falla, o si una publicación prevista
para hoy o ayer no entró. Modo calendario: los errores de descarga no cuentan como falla
(a las 16 la página de INDEC suele saturarse; se reintenta en la próxima corrida).
En ningún caso se modifica una fuente que falló.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from pipeline import calendario, monitorargy
from pipeline.fuentes import emae, emae_letras, emae_letras_desest, ipc, ipi, ipi_minero, ipi_minero_desest, isac, ripte, ripte_real, salarios, salarios_real, sube, sube_mensual, sube_desest, petroleo, petroleo_mensual, refinados, refinados_mensual, ventas_combustibles, ventas_combustibles_desest, came, supermercados, camiones_puertos, camiones_puertos_mensual, cammesa_balance, cammesa_diaria, cammesa_gu_actividad, cammesa_gu_actividad_mensual, estimaciones_agricolas, rem, remuneraciones_provincias, remuneraciones_provincias_real, remuneraciones_provincias_desest, remuneraciones_provincias_real_desest
from pipeline.fuentes._indec import iguales

FUENTES = {f.ID: f for f in [emae, emae_letras, emae_letras_desest, ipc, ipi, ipi_minero, ipi_minero_desest, isac, supermercados, ripte, ripte_real, salarios, salarios_real, sube, sube_mensual, sube_desest, petroleo, petroleo_mensual, refinados, refinados_mensual, ventas_combustibles, ventas_combustibles_desest, came, camiones_puertos, camiones_puertos_mensual, cammesa_balance, cammesa_diaria, cammesa_gu_actividad, cammesa_gu_actividad_mensual, estimaciones_agricolas, rem, remuneraciones_provincias, remuneraciones_provincias_real, remuneraciones_provincias_desest, remuneraciones_provincias_real_desest]}
# Series calculadas a partir de otra (DERIVADA_DE): no se bajan, se recalculan cuando cambia su base.
DERIVADAS = {fid: f for fid, f in FUENTES.items() if hasattr(f, "DERIVADA_DE")}

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
TZ = ZoneInfo("America/Argentina/Buenos_Aires")
RAW = "https://raw.githubusercontent.com/rodrigotperelsztein-source/monitor-series/main"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"


class DescargaError(RuntimeError):
    pass


_CADENAS: dict[str, str] = {}  # servidor -> archivo de certificados con su intermedio


def _cadena_completa(url: str) -> str:
    """Para servidores que no envían su certificado intermedio (p. ej. energia.gob.ar).

    Hace lo mismo que un navegador: lee en el certificado del servidor la dirección de su emisor
    (campo "CA Issuers"), baja ese certificado intermedio y lo suma a las autoridades confiables
    de siempre (certifi). La verificación sigue completa: la cadena tiene que terminar en una
    autoridad raíz reconocida y el nombre del servidor tiene que coincidir. Un intermedio falso
    no pasa, porque no está firmado por una raíz confiable.
    """
    import ssl
    import tempfile
    from urllib.parse import urlparse

    import certifi

    host = urlparse(url).hostname
    if host in _CADENAS:
        return _CADENAS[host]
    hoja = ssl.get_server_certificate((host, 443), timeout=30)
    with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as f:
        f.write(hoja)
    datos = ssl._ssl._test_decode_cert(f.name)  # noqa: SLF001 — lector de certificados de la biblioteca estándar
    emisores = [u for u in datos.get("caIssuers", ()) if u.startswith(("http://", "https://"))]
    if not emisores:
        raise ValueError(f"{host}: el certificado no dice dónde está su emisor")
    r = requests.get(emisores[0], headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    intermedio = r.content if r.content.startswith(b"-----BEGIN") else ssl.DER_cert_to_PEM_cert(r.content).encode()
    with tempfile.NamedTemporaryFile("wb", suffix=".pem", delete=False) as f:
        f.write(Path(certifi.where()).read_bytes() + b"\n" + intermedio)
    _CADENAS[host] = f.name
    print(f"  {host} no envía su certificado intermedio; se tomó de {emisores[0]}")
    return f.name


def descargar(url: str, intentos: int = 3, minimo: int = 1000) -> bytes:
    ultimo = None
    for i in range(intentos):
        try:
            try:
                r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
            except requests.exceptions.SSLError as e:
                if "unable to get local issuer certificate" not in str(e):
                    raise
                r = requests.get(url, headers={"User-Agent": UA}, timeout=60, verify=_cadena_completa(url))
            if r.status_code == 404:
                raise DescargaError(f"{url}: no existe (404)")
            r.raise_for_status()
            if len(r.content) < minimo:
                raise ValueError(f"Respuesta demasiado chica ({len(r.content)} bytes)")
            return r.content
        except DescargaError:
            raise
        except Exception as e:  # noqa: BLE001
            ultimo = e
            print(f"  intento {i + 1} falló: {e}")
            if i < intentos - 1:
                time.sleep(15 * (i + 1))
    raise DescargaError(f"No pude descargar {url}: {ultimo}")


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
        if f"{c}_ant" not in comunes:
            continue
        cambio = ~iguales(comunes[c], comunes[f"{c}_ant"])
        for _, r in comunes[cambio].iterrows():
            filas.append({"detectado": ahora, "periodo": f"{r['fecha']:%Y-%m}", "serie": c,
                          "valor_anterior": r[f"{c}_ant"], "valor_nuevo": r[c]})
    if filas:
        p = DATA / "revisiones" / f"{fid}.csv"
        p.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(filas).to_csv(p, mode="a", header=not p.exists(), index=False)
    return len(filas)


def escribir_excel(fuente, df: pd.DataFrame, meta: dict, columnas: dict) -> None:
    p = DATA / "excel" / f"{fuente.ID}.xlsx"
    p.parent.mkdir(parents=True, exist_ok=True)
    nombres = {cid: col.nombre for cid, col in columnas.items()}
    with pd.ExcelWriter(p, engine="openpyxl") as xw:
        df.rename(columns=nombres).to_excel(xw, sheet_name="Niveles", index=False)
        pd.DataFrame([
            ["Serie", fuente.NOMBRE], ["Unidad", fuente.UNIDAD], ["Fuente", fuente.PAGINA],
            ["Archivo de origen", meta["url"]], ["Descargado (UTC)", meta["descargado"]],
            ["Último período", meta["ultimo_periodo"]],
        ]).to_excel(xw, sheet_name="Datos de la serie", index=False, header=False)
        hoja = xw.sheets["Niveles"]
        hoja.column_dimensions["A"].width = 12
        for fila in hoja.iter_rows(min_row=2, max_col=1):
            fila[0].number_format = "dd/mm/yyyy" if fuente.FRECUENCIA == "D" else "mmm-yyyy"


def bajar_fuente(fuente, hoy: date) -> tuple[str, bytes]:
    """URL y contenido del archivo de la fuente.

    Si el nombre del archivo lleva el año (fuente.urls), se prueba cada candidato en orden
    (año actual, después el anterior) y se usa el primero que exista.
    """
    if hasattr(fuente, "bajar"):
        # La fuente busca su archivo (p. ej., un PDF cuyo nombre cambia, enlazado desde una página).
        return fuente.bajar(descargar, hoy)
    candidatos = fuente.urls(hoy) if hasattr(fuente, "urls") else [fuente.URL]
    no_existen = []
    for url in candidatos:
        try:
            return url, descargar(url)
        except DescargaError as e:
            if "(404)" not in str(e):
                raise
            no_existen.append(url)
    raise DescargaError(f"Ninguno de los archivos existe: {no_existen}")


def procesar(fuente, forzar: bool, ahora: str, hoy: date) -> str:
    fid = fuente.ID
    p_meta = DATA / "meta" / f"{fid}.json"
    p_csv = DATA / f"{fid}.csv"
    meta = leer_json(p_meta)

    url, contenido = bajar_fuente(fuente, hoy)
    huella = hashlib.sha256(contenido).hexdigest()
    if huella == meta.get("sha256") and not forzar:
        # No se escribe nada: así el repositorio solo registra cambios reales.
        return "sin cambios en el archivo"

    columnas = fuente.columnas(contenido) if hasattr(fuente, "columnas") else fuente.COLUMNAS
    nuevo = fuente.leer(contenido, columnas)
    extra = fuente.meta_extra(nuevo) if hasattr(fuente, "meta_extra") else {}
    anterior = leer_csv(p_csv)
    if hasattr(fuente, "combinar"):
        # Fuentes que bajan solo una parte (p. ej. el año en curso) y la suman a la historia guardada.
        nuevo = fuente.combinar(nuevo, anterior)
    errores = fuente.validar(nuevo, anterior, columnas)
    if errores:
        raise ValueError("Validación fallida:\n  - " + "\n  - ".join(errores))

    meta.update({
        "id": fid, "nombre": fuente.NOMBRE, "url": url, "pagina": fuente.PAGINA,
        "frecuencia": fuente.FRECUENCIA, "unidad": fuente.UNIDAD, "sha256": huella,
        "columnas": {cid: {"nombre": c.nombre, "tipo": c.tipo,
                           "unidad": c.unidad or ("%" if c.tipo == "variacion" else fuente.UNIDAD)}
                     for cid, c in columnas.items()},
        **extra,
    })

    datos_iguales = anterior is not None and list(nuevo.columns) == list(anterior.columns) and \
        nuevo.shape == anterior.shape and nuevo["fecha"].equals(anterior["fecha"]) and \
        all(iguales(nuevo[c], anterior[c]).all() for c in nuevo.columns if c != "fecha")
    if datos_iguales:
        p_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return "archivo distinto pero mismos datos"

    revisados = registrar_revisiones(fid, nuevo, anterior, ahora) if getattr(fuente, "REGISTRAR_REVISIONES", True) else 0
    raw = None
    if getattr(fuente, "GUARDAR_ORIGINAL", True):
        raw = DATA / "raw" / fid / f"{ahora[:10]}_{huella[:8]}.{fuente.EXTENSION}"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(contenido)

    nuevo.to_csv(p_csv, index=False, date_format="%Y-%m-%d", float_format="%.6f")
    formato = "%Y-%m-%d" if fuente.FRECUENCIA == "D" else "%Y-%m"
    meta.update({"descargado": ahora, "ultimo_periodo": nuevo["fecha"].max().strftime(formato),
                 "observaciones": len(nuevo), "original_guardado": str(raw.relative_to(RAIZ)) if raw else None})
    p_meta.parent.mkdir(parents=True, exist_ok=True)
    p_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    escribir_excel(fuente, nuevo, meta, columnas)

    ant = f"{anterior['fecha'].max():%Y-%m}" if anterior is not None else "—"
    return f"actualizada: último período {ant} → {meta['ultimo_periodo']}; valores revisados: {revisados}"


def bases(fuente) -> tuple[str, ...]:
    d = fuente.DERIVADA_DE
    return (d,) if isinstance(d, str) else tuple(d)


def procesar_derivada(fuente, forzar: bool, ahora: str) -> str:
    """Recalcula una serie derivada si cambió alguna de sus series de base o la versión del cálculo."""
    fid = fuente.ID
    p_meta = DATA / "meta" / f"{fid}.json"
    p_csv = DATA / f"{fid}.csv"
    meta = leer_json(p_meta)
    rutas = [DATA / f"{b}.csv" for b in bases(fuente)]
    faltan = [r.name for r in rutas if not r.exists()]
    if faltan:
        raise ValueError(f"faltan las series de base {faltan}")
    huella = hashlib.sha256(b"".join(r.read_bytes() for r in rutas) + fuente.VERSION.encode()).hexdigest()
    if huella == meta.get("sha256") and not forzar:
        return "sin cambios en las series de base"

    originales = [leer_csv(r) for r in rutas]
    nuevo, detalle = fuente.calcular(*originales)
    errores = fuente.validar(nuevo, *originales)
    if errores:
        raise ValueError("Validación fallida:\n  - " + "\n  - ".join(errores))
    anterior = leer_csv(p_csv)

    nuevo.to_csv(p_csv, index=False, date_format="%Y-%m-%d", float_format="%.6f")
    metas = [leer_json(DATA / "meta" / f"{b}.json") for b in bases(fuente)]
    meta = {
        "id": fid, "nombre": fuente.NOMBRE, "url": fuente.URL, "pagina": fuente.PAGINA,
        "frecuencia": fuente.FRECUENCIA, "unidad": fuente.UNIDAD, "sha256": huella,
        "derivada_de": list(bases(fuente)), "archivos_de_origen": [m.get("url", "") for m in metas],
        "columnas": {cid: {"nombre": c.nombre, "tipo": c.tipo,
                           "unidad": c.unidad or ("%" if c.tipo == "variacion" else fuente.UNIDAD)}
                     for cid, c in fuente.COLUMNAS.items()},
        # Se toma la descarga más reciente de las bases: el estado respecto del calendario es el mismo.
        "descargado": max((m.get("descargado", "") for m in metas), default="") or ahora, "calculado": ahora,
        "ultimo_periodo": f"{nuevo['fecha'].max():%Y-%m}", "observaciones": len(nuevo),
    }
    if detalle:
        meta.update(detalle)
    p_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    escribir_excel(fuente, nuevo, meta, fuente.COLUMNAS)
    ant = f"{anterior['fecha'].max():%Y-%m}" if anterior is not None else "—"
    return f"recalculada: último período {ant} → {meta['ultimo_periodo']}"


def fecha_cambio(fid: str) -> date | None:
    """Día (hora de Buenos Aires) en que cambiaron los datos de la fuente por última vez."""
    d = leer_json(DATA / "meta" / f"{fid}.json").get("descargado")
    return datetime.fromisoformat(d.replace("Z", "+00:00")).astimezone(TZ).date() if d else None


def estado(fuente, cal, hoy: date) -> dict:
    """Estado de una fuente respecto del calendario de difusión."""
    fechas = calendario.fechas(getattr(fuente, "CALENDARIO", ""), cal)
    if not fechas:
        return {"estado": "sin calendario", "ultima_publicacion_prevista": "", "proxima_publicacion": ""}
    pasadas = [f for f in fechas if f <= hoy]
    futuras = [f for f in fechas if f > hoy]
    ultima = pasadas[-1] if pasadas else None
    cambio = fecha_cambio(fuente.ID)
    if ultima is None or (cambio and cambio >= ultima):
        est = "al día"
    elif ultima == hoy:
        est = "se publica hoy"
    else:
        est = "demorado"
    proxima = hoy if est == "se publica hoy" else (futuras[0] if futuras else None)
    return {"estado": est,
            "ultima_publicacion_prevista": ultima.isoformat() if ultima else "",
            "proxima_publicacion": f"{proxima.isoformat()} {calendario.HORA}" if proxima else ""}


def catalogo(cal, hoy: date) -> None:
    filas = []
    for fid, fuente in FUENTES.items():
        meta = leer_json(DATA / "meta" / f"{fid}.json")
        if meta:
            filas.append({**meta, **estado(fuente, cal, hoy)})
    if filas:
        cols = ["id", "nombre", "frecuencia", "unidad", "ultimo_periodo", "observaciones", "estado",
                "ultima_publicacion_prevista", "proxima_publicacion", "descargado", "pagina", "url"]
        pd.DataFrame(filas).reindex(columns=cols).to_csv(DATA / "catalogo.csv", index=False)


CATEGORIAS = {  # fuente -> gran categoría (para buscar y filtrar en las páginas)
    "emae": "Actividad económica", "emae_letras": "Actividad económica", "emae_letras_desest": "Actividad económica",
    "ipi": "Actividad económica", "isac": "Actividad económica",
    "ipi_minero": "Actividad económica", "ipi_minero_desest": "Actividad económica", "supermercados": "Actividad económica",
    "came": "Actividad económica",
    "ipc": "Precios",
    "ripte": "Salarios", "ripte_real": "Salarios", "salarios": "Salarios", "salarios_real": "Salarios",
    "sube": "Transporte", "sube_mensual": "Transporte", "sube_desest": "Transporte",
    "camiones_puertos": "Agro y puertos", "camiones_puertos_mensual": "Agro y puertos",
    "estimaciones_agricolas": "Agro y puertos",
    "rem": "Expectativas",
    "remuneraciones_provincias": "Salarios", "remuneraciones_provincias_real": "Salarios",
    "remuneraciones_provincias_desest": "Salarios", "remuneraciones_provincias_real_desest": "Salarios",
    "cammesa_balance": "Electricidad", "cammesa_diaria": "Electricidad", "cammesa_gu_actividad": "Electricidad",
    "cammesa_gu_actividad_mensual": "Electricidad",
    "ventas_combustibles": "Combustibles", "ventas_combustibles_desest": "Combustibles",
    "petroleo": "Petróleo y precios internacionales", "petroleo_mensual": "Petróleo y precios internacionales",
    "refinados": "Petróleo y precios internacionales", "refinados_mensual": "Petróleo y precios internacionales",
}


def clasificar(fid: str, cid: str, tipo: str) -> tuple[str, str]:
    """(dato, ajuste) de una serie, para los filtros de las páginas.

    dato: Nivel, Variación mensual, Variación interanual, Variación acumulada u Otra variación.
    ajuste: Desestacionalizada, Tendencia-ciclo, Real (deflactada) u Original.
    """
    if tipo == "variacion":
        dato = ("Variación mensual" if cid.endswith("_var_m") else "Variación interanual" if cid.endswith("_var_ia")
                else "Variación acumulada" if cid.endswith("_var_acum") else "Otra variación")
    else:
        dato = "Nivel"
    base = cid.rsplit("_var_", 1)[0]
    if fid.endswith("_desest") or "desest" in base:
        ajuste = "Desestacionalizada"
    elif "tendencia" in base:
        ajuste = "Tendencia-ciclo"
    elif fid.endswith("_real") or base.endswith("_real") or "_real_" in base:
        ajuste = "Real (deflactada)"
    else:
        ajuste = "Original"
    return dato, ajuste


def organismo_corto(texto: str) -> str:
    """'INDEC (serie original); desestacionalización propia' -> 'INDEC'."""
    for sep in (" (", ";"):
        texto = texto.split(sep)[0]
    return texto.strip()


def todas() -> None:
    """Todas las series juntas en formato largo, pensado para Power BI y similares.

    data/todas/series.csv: una fila por serie (id_serie, nombre, unidad, frecuencia, fuente...).
    data/todas/valores.csv: fecha, id_serie, valor.
    data/series/<id_serie>.csv: una serie sola (fecha, valor), para traer solo las elegidas.
    """
    series, valores = [], []
    for fid, fuente in FUENTES.items():
        p = DATA / f"{fid}.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p, parse_dates=["fecha"])
        meta = leer_json(DATA / "meta" / f"{fid}.json")
        columnas = meta.get("columnas") or {
            cid: {"nombre": c.nombre, "tipo": c.tipo, "unidad": c.unidad} for cid, c in getattr(fuente, "COLUMNAS", {}).items()}
        for cid, col in columnas.items():
            if cid not in df:
                continue
            id_serie = f"{fid}.{cid}"
            puntos = df[["fecha", cid]].dropna().rename(columns={cid: "valor"})
            if puntos.empty:  # p. ej. una estimación que la fuente todavía no publicó
                continue
            puntos.insert(1, "id_serie", id_serie)
            valores.append(puntos)
            dato, ajuste = clasificar(fid, cid, col["tipo"])
            series.append({
                "id_serie": id_serie,
                "serie": col["nombre"],
                "tipo": col["tipo"],
                "categoria": CATEGORIAS.get(fid, "Otras"),
                "dato": dato,
                "ajuste": ajuste,
                "organismo_corto": organismo_corto(getattr(fuente, "ORGANISMO", "")),
                "unidad": col["unidad"] or ("%" if col["tipo"] == "variacion" else fuente.UNIDAD),
                "frecuencia": fuente.FRECUENCIA,
                "fuente": fid,
                "fuente_nombre": fuente.NOMBRE,
                "organismo": getattr(fuente, "ORGANISMO", ""),
                "primer_periodo": f"{puntos['fecha'].min():%Y-%m-%d}",
                "ultimo_periodo": f"{puntos['fecha'].max():%Y-%m-%d}",
                "descargado": meta.get("descargado", ""),
                "pagina": fuente.PAGINA,
                "url_archivo": meta.get("url", ""),
                "url_csv": f"{RAW}/data/series/{id_serie}.csv",
            })
    if not series:
        return
    destino = DATA / "todas"
    destino.mkdir(exist_ok=True)
    # Textos que empiezan con =, +, - o @ se escapan: así una planilla que abra el CSV no los toma
    # como fórmulas (inyección de fórmulas en CSV).
    def seguro(v):
        return "'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r") else v
    pd.DataFrame(series).map(seguro).to_csv(destino / "series.csv", index=False)
    pd.concat(valores).sort_values(["id_serie", "fecha"]).to_csv(
        destino / "valores.csv", index=False, date_format="%Y-%m-%d", float_format="%.6f")

    # Un archivo por serie; se borran los de series que ya no existen.
    carpeta = DATA / "series"
    carpeta.mkdir(exist_ok=True)
    vigentes = set()
    for puntos in valores:
        id_serie = puntos["id_serie"].iloc[0]
        vigentes.add(f"{id_serie}.csv")
        puntos[["fecha", "valor"]].sort_values("fecha").to_csv(
            carpeta / f"{id_serie}.csv", index=False, date_format="%Y-%m-%d", float_format="%.6f")
    for viejo in carpeta.glob("*.csv"):
        if viejo.name not in vigentes:
            viejo.unlink()


def catalogo_monitor_argy() -> str:
    """Guarda el catálogo de Monitor Argy (data/monitorargy/catalogo.json) para la página de selección."""
    r = requests.get("https://monitorargy.com/api/v1/series", headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    datos = r.json()
    paneles = {p["id"]: p["nombre"] for p in datos.get("paneles", [])}
    filas = [{
        "id": s["id"], "nombre": s.get("nombre", ""), "descripcion": s.get("descripcion", ""),
        "panel": paneles.get(s.get("panel"), s.get("panel", "")), "unidad": s.get("unidad", ""),
        "frecuencia": s.get("frecuencia", ""), "fuente": (s.get("fuente") or {}).get("nombre", ""),
        "ultimo_periodo": s.get("ultimaFecha", ""), "frescura": s.get("frescura", ""),
    } for s in datos["series"]]
    if len(filas) < 100:
        raise ValueError(f"El catálogo de Monitor Argy vino con solo {len(filas)} series.")
    p = DATA / "monitorargy" / "catalogo.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(sorted(filas, key=lambda f: f["id"]), ensure_ascii=False, indent=0) + "\n",
                 encoding="utf-8")
    return f"{len(filas)} series"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fuentes", nargs="*", help="ids a procesar (por defecto, todas)")
    ap.add_argument("--modo", choices=["completo", "calendario"], default="completo")
    ap.add_argument("--forzar", action="store_true")
    args = ap.parse_args()

    # MONITOR_AHORA (ISO, UTC) fija el momento actual; sirve solo para pruebas.
    momento = (datetime.fromisoformat(os.environ["MONITOR_AHORA"]).replace(tzinfo=timezone.utc)
               if os.environ.get("MONITOR_AHORA") else datetime.now(timezone.utc))
    ahora = momento.strftime("%Y-%m-%dT%H:%M:%SZ")
    hoy = momento.astimezone(TZ).date()
    (DATA / "meta").mkdir(parents=True, exist_ok=True)
    fallas = 0

    if args.modo == "completo" and not args.fuentes:
        print("[calendario INDEC]")
        try:
            print("  " + calendario.actualizar(descargar, hoy))
        except Exception as e:  # noqa: BLE001
            fallas += 1
            print(f"  ERROR (se conserva el calendario anterior): {e}")
    cal = calendario.cargar()

    pedidas = args.fuentes or list(FUENTES)
    ids = [fid for fid in pedidas if fid not in DERIVADAS]
    if args.modo == "calendario":
        ids = [fid for fid in ids
               if hoy in calendario.fechas(getattr(FUENTES[fid], "CALENDARIO", ""), cal)
               and (fecha_cambio(fid) or date.min) < hoy]
        if ids:
            print(f"Publicaciones previstas hoy y todavía no descargadas: {', '.join(ids)}")
        else:
            print(f"Hoy ({hoy:%d/%m/%Y}) no hay publicaciones pendientes de INDEC para estas series.")

    # Fuentes que solo se revisan algunos días del mes (DIAS_DEL_MES), salvo que se pidan por nombre.
    if not args.fuentes:
        fuera = [fid for fid in ids if hoy.day not in getattr(FUENTES[fid], "DIAS_DEL_MES", range(1, 32))]
        for fid in fuera:
            print(f"[{fid}]\n  no se revisa hoy (solo los días {FUENTES[fid].DIAS_DEL_MES.start} a fin de mes)")
        ids = [fid for fid in ids if fid not in fuera]

    for fid in ids:
        print(f"[{fid}]")
        try:
            print("  " + procesar(FUENTES[fid], args.forzar, ahora, hoy))
        except DescargaError as e:
            print(f"  ERROR de descarga: {e}")
            if args.modo == "completo":
                fallas += 1
            else:
                print("  (se reintenta en la próxima corrida)")
        except Exception as e:  # noqa: BLE001
            fallas += 1
            print(f"  ERROR: {e}")

    # Derivadas: se recalculan si cambió su base (es una comparación de huellas, no cuesta nada).
    for fid, fuente in DERIVADAS.items():
        if args.fuentes and fid not in pedidas and not set(bases(fuente)) & set(pedidas):
            continue
        try:
            r = procesar_derivada(fuente, args.forzar and fid in pedidas, ahora)
            if args.modo == "completo" or not r.startswith("sin cambios"):
                print(f"[{fid}]\n  {r}")
        except Exception as e:  # noqa: BLE001
            fallas += 1
            print(f"[{fid}]\n  ERROR: {e}")

    if args.modo == "calendario" and not ids and not fallas:
        return 0

    if args.modo == "completo" and not args.fuentes:
        # Aviso: una publicación prevista para hoy o ayer que no entró.
        for fid, fuente in FUENTES.items():
            previstas = calendario.fechas(getattr(fuente, "CALENDARIO", ""), cal)
            # Lo previsto para hoy cuenta recién a la noche (una corrida manual de la mañana no es atraso).
            tope = hoy if momento.astimezone(TZ).hour >= 20 else hoy - timedelta(days=1)
            recientes = [f for f in previstas if hoy - timedelta(days=1) <= f <= tope]
            if recientes and (fecha_cambio(fid) or date.min) < recientes[-1]:
                fallas += 1
                print(f"AVISO: INDEC tenía previsto publicar {fid} el {recientes[-1]:%d/%m} y el dato todavía no entró.")

    if args.modo == "completo" and not args.fuentes:
        print("[catálogo de Monitor Argy]")
        try:
            print("  " + catalogo_monitor_argy())
        except Exception as e:  # noqa: BLE001
            print(f"  aviso: no se pudo actualizar ({e}); queda el anterior")
        print("[series de Monitor Argy (copia)]")
        try:
            frec = {f["id"]: f["frecuencia"] for f in json.loads((DATA / "monitorargy" / "catalogo.json").read_text("utf-8"))}
            print("  " + monitorargy.espejo(DATA / "monitorargy" / "series", UA, frec))
        except Exception as e:  # noqa: BLE001
            print(f"  aviso: no se pudo actualizar ({e}); quedan las copias anteriores")
    catalogo(cal, hoy)
    todas()
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
