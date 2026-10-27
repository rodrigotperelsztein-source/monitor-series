"""IPI minero: aperturas y producción física desestacionalizadas (X-13, propia).

INDEC publica desestacionalizado solo el nivel general del IPI minero (está en ipi_minero.desest). Acá se
desestacionalizan, desde data/ipi_minero.csv y cada vez que cambia, los agregados (categorías, divisiones y
grupos), los productos principales y la extracción de petróleo, gas y litio en unidades físicas.

Método (ver pipeline/desest.py): X-13 con modelo ARIMA, transformación y outliers elegidos automáticamente en
cada corrida; días de la semana y Pascua se incluyen si mejoran el modelo (prueba AIC); feriados como regresor
propio, con su efecto dentro de la serie desestacionalizada. Cada serie se ajusta desde el primer mes a partir
del cual todos los valores son positivos (el litio, desde 2020; el no convencional, desde 2019). Las arenas de
fractura y el litio en toneladas no se ajustan: no tienen una estacionalidad identificable (M7 > 1). El petróleo no
convencional tiene estacionalidad débil (M7 cerca de 1,2): su desestacionalizada se aparta poco de la original.
"""

import pandas as pd

from pipeline.desest import PROGRAMA, Especificacion, desestacionalizar
from pipeline.fuentes import ipi_minero as im
from pipeline.fuentes._indec import Columna

ID = "ipi_minero_desest"
NOMBRE = "IPI minero: aperturas y producción de petróleo, gas y litio, desestacionalizadas (X-13, propia)"
DERIVADA_DE = im.ID
URL = "data/ipi_minero.csv"
PAGINA = im.PAGINA
FRECUENCIA = "M"
ORGANISMO = "INDEC (serie original); desestacionalización propia"
UNIDAD = "Índice base 2016=100 (aperturas); unidades físicas (petróleo, gas, litio)"
CALENDARIO = im.CALENDARIO
VERSION = "2026-10-27"
ESPECIFICACION = Especificacion(None, "auto", None, origen="automática en cada corrida (modelo, transformación y outliers)")

SERIES = [f"orig_{c}" for c in ("g_petroleo_gas", "petroleo_crudo", "gas_natural", "servicios_apoyo", "g_metaliferos",
                                 "plata_oro", "bullon_dore", "g_no_metaliferos", "g_rocas_ornamentales", "g_caliza_yeso",
                                 "g_arenas_triturados", "g_arcilla_caolin", "g_minerales_quimicos",
                                 "litio", "g_sal", "g_carbon_otros")] + [
    "petroleo_m3", "petroleo_convencional_m3", "petroleo_no_convencional_m3", "gas_m3", "gas_convencional_m3",
    "gas_no_convencional_m3"]
# El no convencional era marginal al principio (en 2017, menos de 1% del total): se ajusta desde 2019.
DESDE_MINIMO = {"petroleo_no_convencional_m3": "2019-01", "gas_no_convencional_m3": "2019-01"}


def _id(c: str) -> str:
    return c.removeprefix("orig_")


COLUMNAS = {}
for _c in SERIES:
    _nombre = im.COLUMNAS[_c].nombre.replace(" (serie original)", "")
    COLUMNAS[_id(_c)] = Columna("", f"{_nombre}, desestacionalizada (propia, X-13)", unidad=im.COLUMNAS[_c].unidad)
    COLUMNAS[f"{_id(_c)}_var_m"] = Columna("", f"{_nombre}, desestacionalizada (propia, X-13), var. % mensual",
                                          tipo="variacion", base=_id(_c), rezago=1)


def _desde(s: pd.Series, c: str = "") -> pd.Period:
    """Primer mes desde el cual la serie no tiene vacíos ni valores menores o iguales a cero."""
    malos = s[(s.isna()) | (s <= 0)]
    desde = s.index[0] if malos.empty else malos.index[-1] + 1
    return max(desde, pd.Period(DESDE_MINIMO[c], "M")) if c in DESDE_MINIMO else desde


def calcular(original: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    idx = original["fecha"].dt.to_period("M")
    salida = pd.DataFrame({"fecha": original["fecha"]})
    detalle = {}
    for c in SERIES:
        s = pd.Series(original[c].values, index=idx)
        desde = _desde(s, c)
        sa, diag = desestacionalizar(c, s[desde:], ESPECIFICACION)
        sa = sa.reindex(idx)
        salida[_id(c)] = sa.values
        salida[f"{_id(c)}_var_m"] = (sa.pct_change() * 100).values
        diag["advertencias"] = list(dict.fromkeys(diag["advertencias"]))
        detalle[_id(c)] = {"especificacion": ESPECIFICACION.describir(), "desde": str(desde), **diag}
    return salida[["fecha", *COLUMNAS]], {"desestacionalizacion": {"programa": PROGRAMA, "version": VERSION,
                                                                  "series": detalle}}


def validar(nuevo: pd.DataFrame, original: pd.DataFrame) -> list[str]:
    errores = []
    if len(nuevo) != len(original):
        errores.append(f"largo distinto al de la serie original ({len(nuevo)} vs {len(original)})")
    idx = original["fecha"].dt.to_period("M")
    for c in SERIES:
        s = pd.Series(original[c].values, index=idx)
        tramo = (idx >= _desde(s, c))
        if nuevo.loc[tramo, _id(c)].isna().any():
            errores.append(f"{_id(c)}: hay meses sin valor desestacionalizado")
            continue
        r = (nuevo[_id(c)] / original[c])[tramo]
        if not r.between(0.4, 2.5).all():
            errores.append(f"{_id(c)}: la desestacionalizada se aleja demasiado de la original ({r.min():.2f} a {r.max():.2f})")
    return errores
