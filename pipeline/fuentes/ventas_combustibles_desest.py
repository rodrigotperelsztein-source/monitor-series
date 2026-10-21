"""Ventas al mercado de gasoil y naftas (total del mercado y principales empresas), desestacionalización propia (X-13).

Se calcula desde data/ventas_combustibles.csv cada vez que esta cambia. Ver pipeline/desest.py
para el método. Como en SUBE, los efectos de días de la semana y feriados SÍ se quitan de la serie
(un mes con más días hábiles vende más combustible, sin que cambie la tendencia); Pascua no
resultó significativa en ninguna.

Especificaciones identificadas con X-13 (selección automática del modelo y la transformación,
detección de outliers y prueba AIC de días de la semana y Pascua) sobre 2010-01 a 2026-08 y
fijadas. Conviene revisarlas una vez por año.

Las series se ajustan por separado: G2 + G3 desestacionalizados no suman exactamente el total
desestacionalizado. En gasoil quedan movimientos grandes de un mes a otro que no son estacionales
fijos (la cosecha se adelanta o se atrasa): mirar también la variación interanual de la original.
"""

import pandas as pd

from pipeline.desest import PROGRAMA, Especificacion, desestacionalizar
from pipeline.fuentes import ventas_combustibles as vc
from pipeline.fuentes._indec import Columna

ID = "ventas_combustibles_desest"
NOMBRE = "Ventas al mercado de gasoil y naftas, desestacionalización propia (X-13)"
DERIVADA_DE = vc.ID
URL = "data/ventas_combustibles.csv"
PAGINA = vc.PAGINA
FRECUENCIA = "M"
ORGANISMO = "Secretaría de Energía (datos originales); desestacionalización propia"
UNIDAD = "m³"
CALENDARIO = ""
VERSION = "2026-10-21b"

IDENT = "identificada con X-13 sobre 2010-01 a 2026-08 y fijada"
_e = dict(pascua=False, efectos_en_serie=False, origen=IDENT)
ESPECIFICACIONES = {
    "gasoil_total": Especificacion("(0 1 1)(0 1 1)", "niveles", [
        ("TC", "2016-05"), ("TC", "2020-03"), ("AO", "2020-04"), ("AO", "2020-08")], **_e),
    "gasoil_total_sin_usinas_bunker": Especificacion("(0 1 1)(0 1 1)", "niveles", [
        ("AO", "2015-04"), ("LS", "2020-03"), ("TC", "2020-04"), ("LS", "2023-12")], **_e),
    "gasoil_g2_total": Especificacion("(0 1 1)(0 1 1)", "niveles", [
        ("AO", "2015-04"), ("TC", "2016-05"), ("TC", "2020-03"), ("AO", "2020-08")], **_e),
    "gasoil_g3_total": Especificacion("(0 1 0)(0 1 1)", "niveles", [
        ("AO", "2012-03"), ("LS", "2020-03"), ("AO", "2020-04"), ("TC", "2022-04")], **_e),
    "naftas_total": Especificacion("(0 1 1)(0 1 1)", "niveles", [
        ("LS", "2020-03"), ("TC", "2020-04"), ("AO", "2020-06"), ("LS", "2020-12"), ("AO", "2021-04"),
        ("TC", "2021-05"), ("LS", "2023-12")], **_e),
    "nafta_g2_total": Especificacion("(0 1 1)(0 1 1)", "niveles", [
        ("LS", "2020-03"), ("TC", "2020-04"), ("LS", "2020-05"), ("LS", "2020-12"), ("TC", "2021-05"),
        ("LS", "2021-07"), ("TC", "2022-01")], **_e),
    "nafta_g3_total": Especificacion("(0 1 0)(0 1 1)", "niveles", [
        ("LS", "2018-09"), ("LS", "2020-03"), ("TC", "2020-04"), ("TC", "2021-05"), ("AO", "2023-12"),
        ("LS", "2023-12")], **_e),
    # Por empresa (gasoil y naftas, grados 2 + 3). DAPSA y Delta/Gulf no se ajustan: no tienen una
    # estacionalidad estable que X-13 pueda identificar (M7 > 1).
    "gasoil_ypf": Especificacion("(0 1 1)(0 1 1)", "niveles", [
        ("AO", "2015-04"), ("TC", "2016-05"), ("LS", "2020-03"), ("AO", "2020-04"), ("AO", "2020-08")], **_e),
    "gasoil_shell": Especificacion("(0 1 1)(0 1 1)", "niveles", [("TC", "2020-03")], **_e),
    "gasoil_axion": Especificacion("(0 1 1)(0 1 1)", "log", [
        ("LS", "2012-11"), ("TC", "2014-02"), ("AO", "2016-09"), ("TC", "2017-04"), ("TC", "2020-03"),
        ("TC", "2020-12")], **_e),
    "gasoil_trafigura": Especificacion("(1 0 2)(1 0 0)", "log", [], dias_semana=False, **_e),
    # Refinor en logaritmos: su estacionalidad (cosecha en el NOA) es proporcional al nivel, que bajó.
    "gasoil_refinor": Especificacion("(1 0 0)(0 1 1)", "log", [
        ("AO", "2018-04"), ("AO", "2020-02"), ("LS", "2022-05"), ("TC", "2023-05"), ("LS", "2023-12")], **_e),
    "naftas_ypf": Especificacion("(0 1 1)(0 1 1)", "niveles", [
        ("LS", "2020-03"), ("TC", "2020-04"), ("AO", "2020-06"), ("LS", "2020-12"), ("AO", "2021-04"),
        ("TC", "2021-05")], dias_semana=False, **_e),
    "naftas_shell": Especificacion("(1 1 0)(0 1 1)", "niveles", [
        ("AO", "2020-03"), ("TC", "2020-04"), ("TC", "2021-05"), ("LS", "2023-12")], **_e),
    "naftas_axion": Especificacion("(0 1 1)(0 1 1)", "niveles", [
        ("AO", "2016-09"), ("TC", "2017-03"), ("LS", "2020-03"), ("TC", "2020-04"), ("TC", "2021-05")], **_e),
    "naftas_trafigura": Especificacion("(0 1 0)(1 1 0)", "niveles", [
        ("LS", "2020-03"), ("AO", "2020-04"), ("TC", "2020-12")], **_e),
    "naftas_refinor": Especificacion("(0 1 1)(0 1 1)", "log", [
        ("AO", "2014-01"), ("LS", "2020-03"), ("AO", "2020-04"), ("LS", "2023-12")], **_e),
}
# Trafigura (red Puma) empieza a vender en volumen en 2018, cuando compra la red de Petrobras:
# se ajusta desde 2019.
DESDE = {"gasoil_trafigura": "2019-01", "naftas_trafigura": "2019-01"}

COLUMNAS = {}
for _cid in ESPECIFICACIONES:
    _n = vc.COLUMNAS[_cid].nombre
    COLUMNAS[_cid] = Columna("", f"{_n}, desestacionalizada (propia, X-13)")
    COLUMNAS[f"{_cid}_var_m"] = Columna("", f"{_n}, desestacionalizada (propia, X-13), var. % mensual",
                                        tipo="variacion", base=_cid, rezago=1)

ESCALA = 1000  # X-13 trabaja en miles de m³


def calcular(original: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    idx = original["fecha"].dt.to_period("M")
    salida = pd.DataFrame({"fecha": original["fecha"]})
    detalle = {}
    for cid, esp in ESPECIFICACIONES.items():
        serie = pd.Series(original[cid].values / ESCALA, index=idx)
        if cid in DESDE:
            serie = serie[pd.Period(DESDE[cid], "M"):]
        sa, diag = desestacionalizar(cid, serie, esp)
        sa = sa.reindex(idx) * ESCALA
        salida[cid] = sa.round(1).values
        salida[f"{cid}_var_m"] = (sa.pct_change() * 100).values
        diag["advertencias"] = list(dict.fromkeys(diag["advertencias"]))
        detalle[cid] = {"especificacion": esp.describir(), **diag}
    return salida, {"desestacionalizacion": {"programa": PROGRAMA, "version_especificaciones": VERSION,
                                             "series": detalle}}


def validar(nuevo: pd.DataFrame, original: pd.DataFrame) -> list[str]:
    errores = []
    if len(nuevo) != len(original):
        errores.append(f"largo distinto al de la serie original ({len(nuevo)} vs {len(original)})")
    for cid in ESPECIFICACIONES:
        desde = DESDE.get(cid, "2000-01") + "-01"
        if nuevo.loc[nuevo["fecha"] >= desde, cid].isna().any():
            errores.append(f"{cid}: hay meses sin valor desestacionalizado")
            continue
        r = (nuevo[cid] / original[cid])[original["fecha"] >= max("2021-01-01", desde)]
        # Las empresas chicas tienen estacionalidad más marcada que el total del mercado.
        lim = (0.7, 1.4) if cid.endswith("_total") or "_total_" in cid else (0.5, 2.0)
        if not r.between(*lim).all():
            errores.append(f"{cid}: la desestacionalizada se aleja demasiado de la original "
                           f"(cociente entre {r.min():.2f} y {r.max():.2f})")
    return errores
