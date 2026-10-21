"""SUBE mensual desestacionalizada (desestacionalización propia con X-13).

Se calcula desde las transacciones del mes de data/sube_mensual.csv (solo meses completos),
cada vez que esta cambia. Ver pipeline/desest.py para el método.

Diferencias con el EMAE por sector (emae_letras_desest):
  - acá los feriados y la Pascua SÍ se quitan de la serie desestacionalizada: en el transporte un
    feriado baja mucho los viajes del mes y no es un cambio de la tendencia;
  - la serie empieza en 2020-01, así que incluye la pandemia: los outliers de marzo y abril de 2020
    la separan del resto. Con pocos años, los factores estacionales se revisan más que en series
    largas cuando entran datos nuevos.

Lo que queda en la serie: la tendencia y lo irregular (paros, cortes, cambios de tarifa). Las
huelgas aparecen como caídas puntuales (outliers AO): no se quitan.

Especificaciones identificadas con X-13 (selección automática del modelo y la transformación,
detección de outliers y prueba AIC de días de la semana y Pascua) sobre 2020-01 a 2026-09 y
fijadas; en subte se fijaron logaritmos y días de la semana. Conviene revisarlas una vez por año.

Total, AMBA e interior se desestacionalizan por separado (método directo): AMBA + interior
desestacionalizados no suman exactamente el total desestacionalizado.
"""

import pandas as pd

from pipeline.desest import PROGRAMA, Especificacion, desestacionalizar
from pipeline.fuentes import sube, sube_mensual
from pipeline.fuentes._indec import Columna

ID = "sube_desest"
NOMBRE = "SUBE: transacciones por mes, desestacionalización propia (X-13)"
DERIVADA_DE = sube_mensual.ID
URL = "data/sube_mensual.csv"
PAGINA = sube.PAGINA
FRECUENCIA = "M"
ORGANISMO = "Secretaría de Transporte (datos originales); desestacionalización propia"
UNIDAD = "Transacciones por mes"
CALENDARIO = ""
VERSION = "2026-10-21"

IDENT = "identificada con X-13 sobre 2020-01 a 2026-09 y fijada"
_esp = dict(pascua=False, efectos_en_serie=False, origen=IDENT)
ESPECIFICACIONES = {
    "total": Especificacion("(0 1 1)(0 1 1)", "niveles", [
        ("LS", "2020-03"), ("AO", "2020-04"), ("TC", "2022-01")], **_esp),
    "amba": Especificacion("(0 1 1)(0 1 1)", "niveles", [
        ("AO", "2020-03"), ("LS", "2020-04")], **_esp),
    "interior": Especificacion("(0 1 1)(0 1 1)", "niveles", [("AO", "2020-04")], **_esp),
    "colectivo": Especificacion("(1 1 0)(0 1 1)", "niveles", [
        ("LS", "2020-03"), ("AO", "2020-04")], **_esp),
    "tren": Especificacion("(0 1 1)(0 1 1)", "niveles", [
        ("LS", "2020-03"), ("LS", "2020-04"), ("LS", "2021-03"), ("TC", "2021-04"), ("AO", "2021-05"),
        ("AO", "2021-10"), ("AO", "2022-01"), ("AO", "2025-02"), ("AO", "2025-10"), ("AO", "2026-07")], **_esp),
    # Subte en logaritmos: en 2020 cayó a menos del 5% de su nivel y el modelo aditivo
    # deformaba los factores estacionales de 2021.
    "subte": Especificacion("(0 1 1)(0 1 1)", "log", [
        ("TC", "2020-03"), ("LS", "2020-04"), ("TC", "2020-05"), ("TC", "2022-01")], **_esp),
}

COLUMNAS = {}
for _cid in ESPECIFICACIONES:
    _nombre = sube.COLUMNAS[_cid].nombre.replace("SUBE, transacciones por día, ", "")
    COLUMNAS[_cid] = Columna("", f"SUBE, transacciones del mes, {_nombre}, desestacionalizada (propia, X-13)")
    COLUMNAS[f"{_cid}_var_m"] = Columna(
        "", f"SUBE, transacciones del mes, {_nombre}, desestacionalizada (propia, X-13), var. % mensual",
        tipo="variacion", base=_cid, rezago=1)

ESCALA = 1e6  # X-13 trabaja en millones de transacciones


def calcular(mensual: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    fechas = mensual["fecha"]
    idx = fechas.dt.to_period("M")
    salida = pd.DataFrame({"fecha": fechas})
    detalle = {}
    for cid, esp in ESPECIFICACIONES.items():
        serie = pd.Series(mensual[cid].values / ESCALA, index=idx)
        sa, diag = desestacionalizar(f"sube_{cid}", serie, esp)
        sa = sa.reindex(idx) * ESCALA
        salida[cid] = sa.round(0).values
        salida[f"{cid}_var_m"] = (sa.pct_change() * 100).values
        diag["advertencias"] = list(dict.fromkeys(diag["advertencias"]))
        detalle[cid] = {"especificacion": esp.describir(), **diag}
    return salida, {"desestacionalizacion": {"programa": PROGRAMA, "version_especificaciones": VERSION,
                                             "series": detalle}}


def validar(nuevo: pd.DataFrame, mensual: pd.DataFrame) -> list[str]:
    errores = []
    if len(nuevo) != len(mensual):
        errores.append(f"largo distinto al de la serie mensual ({len(nuevo)} vs {len(mensual)})")
    for cid in ESPECIFICACIONES:
        if nuevo[cid].isna().any():
            errores.append(f"{cid}: hay meses sin valor desestacionalizado")
            continue
        ratio = nuevo[cid] / mensual[cid]
        # Abril de 2020 (pandemia) se aleja mucho; desde 2021 la desestacionalizada debe quedar cerca.
        reciente = ratio[mensual["fecha"] >= "2021-01-01"]
        if not reciente.between(0.6, 1.6).all():
            errores.append(f"{cid}: la desestacionalizada se aleja demasiado de la original "
                           f"(cociente entre {reciente.min():.2f} y {reciente.max():.2f})")
    return errores
