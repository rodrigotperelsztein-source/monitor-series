"""Copia de una selección de series de Monitor Argy (https://monitorargy.com), para quien necesite leerlas
desde este repositorio sin consultar la API (por ejemplo, el informe mensual de indicadores).

Se guarda una serie por archivo en data/monitorargy/series/<id>.csv (fecha,valor), tal como la publica Monitor
Argy: los valores no se modifican. Las series diarias se guardan desde 2020. Se actualiza en la corrida
completa de cada noche; si una serie falla, queda la copia anterior.
"""

import io
import time

import pandas as pd
import requests

API = "https://monitorargy.com/api/v1/series/{}"
DESDE_DIARIAS = "2020-01-01"

# id de Monitor Argy -> para qué se usa (solo documentación). Quedan los precios de mercado que todavía no tienen
# fuente propia (dólar contado con liquidación, brecha y riesgo país) y la liquidación de divisas del agro, que
# Monitor Argy toma del archivo de CIARA-CEC: va un mes adelante de datos.gob.ar y con la historia ya revisada.
# El resto ya sale de los organismos (ver README).
SERIES = {
    "tc_ccl": "Dólar contado con liquidación (diario)",
    "brecha_ccl": "Brecha CCL vs. mayorista (diario)",
    "riesgo_pais": "Riesgo país (diario)",
    "liquidacion_agro": "Liquidación de divisas del agro, CIARA-CEC (mensual)",
}


def leer(contenido: bytes, frecuencia: str) -> pd.DataFrame:
    import json
    j = json.loads(contenido)
    d = pd.DataFrame([p for p in j["puntos"] if p.get("valor") is not None], columns=["fecha", "valor"])
    d["fecha"] = pd.to_datetime(d["fecha"].str[:10])
    d["valor"] = pd.to_numeric(d["valor"])
    d = d.dropna().drop_duplicates("fecha", keep="last").sort_values("fecha")
    if frecuencia == "D":
        d = d[d["fecha"] >= DESDE_DIARIAS]
    return d


def espejo(carpeta, ua: str, catalogo: dict) -> str:
    """Baja cada serie de SERIES y la guarda si es válida. catalogo: id -> frecuencia (del catálogo de MA)."""
    carpeta.mkdir(parents=True, exist_ok=True)
    bien, fallas = 0, []
    for sid in SERIES:
        try:
            r = requests.get(API.format(sid), headers={"User-Agent": ua}, timeout=60)
            r.raise_for_status()
            d = leer(r.content, catalogo.get(sid, "M"))
            if len(d) < 12:
                raise ValueError(f"solo {len(d)} datos")
            buf = io.StringIO()
            d.to_csv(buf, index=False, date_format="%Y-%m-%d", float_format="%.6f")
            (carpeta / f"{sid}.csv").write_text(buf.getvalue(), encoding="utf-8")
            bien += 1
        except Exception as e:  # noqa: BLE001
            fallas.append(f"{sid} ({e})")
        time.sleep(0.5)  # sin apuro: no cargar la API
    return f"{bien} de {len(SERIES)} series" + (f"; fallaron: {', '.join(fallas)}" if fallas else "")
