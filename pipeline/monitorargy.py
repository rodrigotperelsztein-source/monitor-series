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

# id de Monitor Argy -> para qué se usa (solo documentación)
SERIES = {
    "confianza_gobierno": "Índice de Confianza en el Gobierno (UTDT)",
    "confianza_consumidor": "Índice de Confianza del Consumidor (UTDT)",
    "tc_mayorista": "Tipo de cambio mayorista (diario)",
    "tc_ccl": "Dólar contado con liquidación (diario)",
    "brecha_ccl": "Brecha CCL vs. mayorista (diario)",
    "reservas": "Reservas internacionales del BCRA (diario)",
    "riesgo_pais": "Riesgo país (diario)",
    "tasa_tamar": "Tasa TAMAR, bancos privados (diario)",
    "patentamientos_autos_desest": "Patentamientos de autos, desestacionalizado",
    "patentamientos_autos_interanual": "Patentamientos de autos, var. interanual",
    "mayoristas_interanual": "Ventas en autoservicios mayoristas, var. interanual",
    "shoppings_interanual": "Ventas en shoppings, var. interanual",
    "petroleo": "Producción de petróleo",
    "petroleo_desest": "Producción de petróleo, desestacionalizada",
    "petroleo_interanual": "Producción de petróleo, var. interanual",
    "petroleo_no_convencional": "Producción de petróleo no convencional",
    "gas_desest": "Producción de gas natural, desestacionalizada",
    "gas_interanual": "Producción de gas natural, var. interanual",
    "empleo_privado_desest": "Asalariados registrados del sector privado, desestacionalizado",
    "empleo_privado_interanual": "Asalariados registrados del sector privado, var. interanual",
    "exportaciones": "Exportaciones de bienes",
    "importaciones": "Importaciones de bienes",
    "saldo_comercial": "Saldo comercial",
    "expo_combustibles": "Exportaciones de combustibles y energía",
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
