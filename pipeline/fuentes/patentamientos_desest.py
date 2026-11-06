"""Patentamientos de automotores y de motos (total del país), desestacionalización propia (X-13).

Se calcula desde data/patentamientos.csv cada vez que esta cambia. Ver pipeline/desest.py para el método. Se quitan los
días de la semana (un mes con más días hábiles inscribe más); los efectos de feriados y Pascua quedan en la serie.

Especificaciones identificadas con X-13 (selección automática del modelo y la transformación, detección de outliers y
prueba AIC de calendario) sobre 2000-01 (autos) y 2007-01 (motos) a 2026-10, y fijadas. En motos se fijó el modelo
(1 1 1)(0 1 1), que deja residuos sin autocorrelación (el automático dejaba 18 rezagos significativos). Conviene
revisarlas una vez por año.
"""

import pandas as pd

from pipeline.desest import PROGRAMA, Especificacion, desestacionalizar
from pipeline.fuentes import patentamientos as pat
from pipeline.fuentes._indec import Columna

ID = "patentamientos_desest"
NOMBRE = "Patentamientos de automotores y motos, desestacionalización propia (X-13)"
DERIVADA_DE = pat.ID
URL = "data/patentamientos.csv"
PAGINA = pat.PAGINA
FRECUENCIA = "M"
ORGANISMO = "DNRPA (datos originales); desestacionalización propia"
UNIDAD = "Unidades"
CALENDARIO = ""
VERSION = "2026-11-06"

IDENT = "identificada con X-13 sobre los datos hasta 2026-10 y fijada"
ESPECIFICACIONES = {
    "autos": Especificacion("(1 1 0)(1 1 1)", "niveles", [
        ("TC", "2012-09"), ("TC", "2013-04"), ("LS", "2014-02"), ("AO", "2015-01"), ("AO", "2016-01"), ("AO", "2018-01"),
        ("LS", "2018-06"), ("AO", "2020-03"), ("AO", "2020-04"), ("TC", "2020-10"), ("TC", "2024-01")],
        pascua=False, origen=IDENT),
    "motos": Especificacion("(1 1 1)(0 1 1)", "niveles", [
        ("LS", "2014-02"), ("AO", "2020-04"), ("TC", "2024-01"), ("AO", "2024-08"), ("LS", "2024-11"), ("AO", "2025-02")],
        origen=IDENT),
}
DESDE = {"autos": "2000-01", "motos": "2007-01"}
ESCALA = 1000  # X-13 trabaja en miles de unidades

COLUMNAS = {}
for _cid in ESPECIFICACIONES:
    _n = pat.COLUMNAS[_cid].nombre
    COLUMNAS[_cid] = Columna("", f"{_n}, desestacionalizada (propia, X-13)")
    COLUMNAS[f"{_cid}_var_m"] = Columna("", f"{_n}, desestacionalizada (propia, X-13), var. % mensual", unidad="%",
                                        tipo="variacion", base=_cid, rezago=1)


def calcular(original: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    idx = original["fecha"].dt.to_period("M")
    salida = pd.DataFrame({"fecha": original["fecha"]})
    detalle = {}
    for cid, esp in ESPECIFICACIONES.items():
        serie = pd.Series(original[cid].values / ESCALA, index=idx)[pd.Period(DESDE[cid], "M"):]
        sa, diag = desestacionalizar(cid, serie, esp)
        sa = sa.reindex(idx) * ESCALA
        salida[cid] = sa.round(1).values
        salida[f"{cid}_var_m"] = (sa.pct_change(fill_method=None) * 100).values
        diag["advertencias"] = list(dict.fromkeys(diag["advertencias"]))
        detalle[cid] = {"especificacion": esp.describir(), **diag}
    return salida, {"desestacionalizacion": {"programa": PROGRAMA, "version_especificaciones": VERSION,
                                             "series": detalle}}


def validar(nuevo: pd.DataFrame, original: pd.DataFrame) -> list[str]:
    errores = []
    if len(nuevo) != len(original):
        errores.append(f"largo distinto al de la serie original ({len(nuevo)} vs {len(original)})")
    for cid in ESPECIFICACIONES:
        desde = DESDE[cid] + "-01"
        if nuevo.loc[nuevo["fecha"] >= desde, cid].isna().any():
            errores.append(f"{cid}: hay meses sin valor desestacionalizado")
            continue
        r = (nuevo[cid] / original[cid])[original["fecha"] >= "2021-01-01"]
        # Enero concentra los patentamientos del año (el modelo nuevo): la estacionalidad es muy marcada.
        if not r.between(0.4, 2.5).all():
            errores.append(f"{cid}: la desestacionalizada se aleja demasiado de la original "
                           f"(cociente entre {r.min():.2f} y {r.max():.2f})")
    return errores
