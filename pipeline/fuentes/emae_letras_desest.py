"""EMAE por sector (letras A, C, D, E, F, G, I y J), desestacionalización propia con X-13.

INDEC no publica las letras desestacionalizadas. Se calculan desde la serie original
(data/emae_letras.csv) cada vez que esta cambia. Ver pipeline/desest.py para el método.

Especificaciones:
  - A, C, D y F: las mismas que publica Monitor Argy (modelo, transformación y outliers).
  - E, G, I y J: identificadas acá con X-13 (selección automática del modelo y la
    transformación, detección de outliers y prueba AIC de días de la semana y Pascua sobre la
    muestra 2004-01 a 2026-07) y después fijadas. Conviene revisarlas una vez por año.

Las especificaciones quedan fijas: con cada dato nuevo se reestima el modelo, pero no se
cambian el orden ARIMA ni los outliers. Por eso los meses recientes se revisan todos los meses.
"""

import pandas as pd

from pipeline.desest import PROGRAMA, Especificacion, desestacionalizar
from pipeline.fuentes import emae_letras
from pipeline.fuentes._indec import Columna

ID = "emae_letras_desest"
NOMBRE = "EMAE por sector de actividad (letras), desestacionalización propia (X-13)"
DERIVADA_DE = emae_letras.ID
URL = "data/emae_letras.csv"
PAGINA = emae_letras.PAGINA
FRECUENCIA = "M"
ORGANISMO = "INDEC (serie original); desestacionalización propia"
UNIDAD = "Índice base 2004=100"
CALENDARIO = emae_letras.CALENDARIO
# Cambia cuando cambian el método o las especificaciones: obliga a recalcular.
VERSION = "2026-10-19"

MA = "Monitor Argy (emae_{}_desest)"
IDENT = "identificada con X-13 sobre 2004-01 a 2026-07 y fijada"
ESPECIFICACIONES = {
    "a_agro": Especificacion("(2 0 0)(0 1 1)", "log", [
        ("LS", "2009-04"), ("LS", "2009-07"), ("LS", "2018-04"), ("LS", "2018-07"),
        ("LS", "2023-04"), ("LS", "2023-07")], origen=MA.format("agro")),
    "c_mineria": Especificacion("(0 1 1)(0 1 1)", "niveles", [
        ("AO", "2008-05"), ("AO", "2009-08"), ("AO", "2010-12"), ("LS", "2011-04"),
        ("LS", "2020-04")], origen=MA.format("mineria")),
    "d_industria": Especificacion("(3 1 1)(0 1 1)", "niveles", [
        ("LS", "2020-03"), ("LS", "2020-06"), ("LS", "2024-07")], origen=MA.format("industria")),
    "e_electricidad_gas_agua": Especificacion("(0 1 2)(0 1 1)", "log", [], pascua=False, origen=IDENT),
    "f_construccion": Especificacion("(0 1 2)(0 1 1)", "niveles", [
        ("LS", "2020-03"), ("AO", "2020-04"), ("AO", "2020-05"), ("LS", "2020-07"),
        ("LS", "2020-10"), ("AO", "2021-05"), ("LS", "2024-01")], origen=MA.format("construccion")),
    "g_comercio": Especificacion("(0 1 3)(0 1 1)", "log", [
        ("TC", "2020-03"), ("TC", "2020-04"), ("LS", "2024-07")], pascua=False, origen=IDENT),
    "i_transporte_comunicaciones": Especificacion("(1 1 0)(0 1 1)", "niveles", [
        ("LS", "2020-03"), ("TC", "2020-04"), ("LS", "2020-07")], pascua=False, origen=IDENT),
    "j_intermediacion_financiera": Especificacion("(0 1 0)(0 1 1)", "log", [
        ("AO", "2025-09")], pascua=False, origen=IDENT),
}

COLUMNAS = {}
for _cid in ESPECIFICACIONES:
    _nombre = emae_letras.COLUMNAS[_cid].nombre
    COLUMNAS[_cid] = Columna("", f"{_nombre}, desestacionalizada (propia, X-13)")
    COLUMNAS[f"{_cid}_var_m"] = Columna("", f"{_nombre}, desestacionalizada (propia, X-13), var. % mensual",
                                        tipo="variacion", base=_cid, rezago=1)


def calcular(original: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Serie desestacionalizada de cada letra y diagnósticos de cada ajuste."""
    fechas = original["fecha"]
    idx = fechas.dt.to_period("M")
    salida = pd.DataFrame({"fecha": fechas})
    detalle = {}
    for cid, esp in ESPECIFICACIONES.items():
        serie = pd.Series(original[cid].values, index=idx)
        sa, diag = desestacionalizar(cid, serie, esp)
        sa = sa.reindex(idx)
        salida[cid] = sa.values
        salida[f"{cid}_var_m"] = (sa.pct_change() * 100).values
        diag["advertencias"] = list(dict.fromkeys(diag["advertencias"]))
        detalle[cid] = {"especificacion": esp.describir(), **diag}
    return salida, {"programa": PROGRAMA, "version_especificaciones": VERSION, "series": detalle}


def validar(nuevo: pd.DataFrame, original: pd.DataFrame) -> list[str]:
    errores = []
    if len(nuevo) != len(original):
        errores.append(f"largo distinto al de la serie original ({len(nuevo)} vs {len(original)})")
    for cid in ESPECIFICACIONES:
        if nuevo[cid].isna().any():
            errores.append(f"{cid}: hay meses sin valor desestacionalizado")
            continue
        ratio = nuevo[cid] / original[cid]
        if not ratio.between(0.3, 3).all():
            errores.append(f"{cid}: la desestacionalizada se aleja demasiado de la original "
                           f"(cociente entre {ratio.min():.2f} y {ratio.max():.2f})")
    return errores
