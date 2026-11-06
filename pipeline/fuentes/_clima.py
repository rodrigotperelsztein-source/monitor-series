"""Clima de CABA y el AMBA desde Open-Meteo (https://open-meteo.com, datos bajo licencia CC BY 4.0).

No son mediciones de estaciones: son celdas de una grilla de modelos meteorológicos.
  - Histórico: reanálisis ERA5 de Copernicus/ECMWF en la versión "seamless" de Open-Meteo: la temperatura sale de
    ERA5-Land (celdas de unos 11 km) y la lluvia de ERA5 (celdas de unos 28 km; ERA5-Land no trae lluvia en Open-Meteo).
    Tiene unos cinco días de demora.
  - Pronóstico: la mejor combinación de modelos que elige Open-Meteo para la zona (GFS, ECMWF y otros).
Los días se cuentan en hora argentina (de 0 a 24).

Áreas:
  - CABA: promedio de cuatro puntos repartidos en la ciudad (cubren las celdas que caen sobre ella).
  - AMBA: promedio de un punto por cada uno de los 40 partidos del Gran Buenos Aires ampliado más los cuatro de CABA. El
    punto de cada partido es su centroide según el Servicio de Normalización de Datos Geográficos (georef). Cada partido
    pesa lo mismo sin importar su superficie; el de San Fernando y el de Tigre caen en la parte de islas del delta.
"""

import json

import pandas as pd

TZ = "America%2FArgentina%2FBuenos_Aires"
CABA = [(-34.57, -58.46), (-34.60, -58.40), (-34.62, -58.50), (-34.66, -58.45)]
PARTIDOS = [
    ("Almirante Brown", -34.8356, -58.3674), ("Avellaneda", -34.6782, -58.3411), ("Berazategui", -34.8182, -58.1555),
    ("Berisso", -34.9094, -57.8284), ("Brandsen", -35.2225, -58.1752), ("Campana", -34.1384, -58.8830),
    ("Cañuelas", -35.1448, -58.6911), ("Ensenada", -34.8421, -57.9791), ("Escobar", -34.3287, -58.7712),
    ("Esteban Echeverría", -34.8312, -58.4769), ("Exaltación de la Cruz", -34.2951, -59.1559), ("Ezeiza", -34.8761, -58.5647),
    ("Florencio Varela", -34.8777, -58.2586), ("General Las Heras", -34.9094, -58.9954), ("General Rodríguez", -34.6506, -58.9878),
    ("General San Martín", -34.5528, -58.5643), ("Hurlingham", -34.5993, -58.6495), ("Ituzaingó", -34.6361, -58.6888),
    ("José C. Paz", -34.5119, -58.7776), ("La Matanza", -34.7703, -58.6254), ("Lanús", -34.7057, -58.3947),
    ("La Plata", -35.0038, -58.0178), ("Lomas de Zamora", -34.7550, -58.4241), ("Luján", -34.5673, -59.1585),
    ("Marcos Paz", -34.8140, -58.8478), ("Malvinas Argentinas", -34.4873, -58.7121), ("Moreno", -34.6107, -58.8109),
    ("Merlo", -34.7110, -58.7420), ("Morón", -34.6494, -58.6198), ("Pilar", -34.4482, -58.9033),
    ("Presidente Perón", -34.9298, -58.3981), ("Quilmes", -34.7350, -58.2769), ("San Fernando", -34.1558, -58.5346),
    ("San Isidro", -34.4869, -58.5372), ("San Miguel", -34.5521, -58.6918), ("San Vicente", -35.0715, -58.4318),
    ("Tigre", -34.3820, -58.5882), ("Tres de Febrero", -34.5960, -58.5792), ("Vicente López", -34.5265, -58.5045),
    ("Zárate", -33.9971, -59.1282)]
PUNTOS = CABA + [(la, lo) for _, la, lo in PARTIDOS]


def coordenadas() -> str:
    return (f"latitude={','.join(f'{la:.4f}' for la, _ in PUNTOS)}"
            f"&longitude={','.join(f'{lo:.4f}' for _, lo in PUNTOS)}")


def promediar(contenido: bytes, variables: dict[str, str]) -> pd.DataFrame:
    """Respuesta de Open-Meteo con varios puntos -> promedio de CABA y del AMBA por día."""
    puntos = json.loads(contenido)
    if not isinstance(puntos, list) or len(puntos) != len(PUNTOS):
        raise ValueError(f"Open-Meteo devolvió {len(puntos) if isinstance(puntos, list) else 'un objeto'} puntos; se esperaban {len(PUNTOS)}.")
    tablas = []
    for p in puntos:
        d = p["daily"]
        tablas.append(pd.DataFrame({k: pd.to_numeric(pd.Series(d[v]), errors="coerce").values for k, v in variables.items()},
                                   index=pd.to_datetime(d["time"])))
    caba = pd.concat(tablas[:len(CABA)]).groupby(level=0).mean()
    amba = pd.concat(tablas).groupby(level=0).mean()
    out = pd.concat([caba.add_prefix("caba_"), amba.add_prefix("amba_")], axis=1).round(2)
    out.index.name = "fecha"
    return out
