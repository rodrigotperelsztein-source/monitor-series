"""BCRA: principales variables monetarias y cambiarias, diarias, desde la API pública de estadísticas (v4).

Fuente: BCRA, API de estadísticas monetarias (https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/<id>), pública y sin
clave. Cada variable tiene un número; acá se baja una lista cerrada (VARIABLES). La API devuelve hasta 3.000 datos por
pedido, así que se pagina. Saldos en millones de pesos o de dólares, tasas en % nominal anual, tipos de cambio en pesos
por dólar. Las series diarias tienen días hábiles; algunos saldos se publican con dos o tres días de rezago.
"""

import io
import json
import zipfile
from datetime import date

import pandas as pd

from pipeline.fuentes._indec import Columna

ID = "bcra"
NOMBRE = "BCRA: reservas, base monetaria, depósitos, préstamos, tasas y tipo de cambio (diario)"
PAGINA = "https://www.bcra.gob.ar/PublicacionesEstadisticas/Principales_variables.asp"
API = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/{}?desde={}&hasta={}&limit=3000&offset={}"
URL = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias"
EXTENSION = "zip"
FRECUENCIA = "D"
ORGANISMO = "BCRA"
UNIDAD = "Según la serie"
PRIMER_PERIODO = "1996-01-01"
CALENDARIO = ""
GUARDAR_ORIGINAL = False

# id propio -> (número de variable en la API, nombre, unidad, cómo se pasa a mensual: "fin" o "promedio")
VARIABLES = {
    "reservas": (1, "Reservas internacionales", "Millones de USD", "fin"),
    "reservas_var_compras": (78, "Variación de reservas por compras de divisas", "Millones de USD", "suma"),
    "tc_mayorista": (5, "Tipo de cambio mayorista de referencia (Com. A 3500)", "$ por dólar", "promedio"),
    "tc_minorista": (4, "Tipo de cambio minorista, promedio vendedor", "$ por dólar", "promedio"),
    "banda_inferior": (1187, "Bandas cambiarias: límite inferior", "$ por dólar", "promedio"),
    "banda_superior": (1188, "Bandas cambiarias: límite superior", "$ por dólar", "promedio"),
    "base_monetaria": (15, "Base monetaria", "Millones de $", "promedio"),
    "circulacion_monetaria": (16, "Circulación monetaria", "Millones de $", "promedio"),
    "billetes_publico": (17, "Billetes y monedas en poder del público", "Millones de $", "promedio"),
    "m2": (109, "M2 (billetes y monedas, cuentas corrientes y cajas de ahorro)", "Millones de $", "promedio"),
    "depositos_privados_pesos": (100, "Depósitos del sector privado no financiero en pesos", "Millones de $", "promedio"),
    "depositos_privados_usd": (108, "Depósitos del sector privado no financiero en dólares", "Millones de USD", "promedio"),
    "depositos_plazo_privados": (96, "Depósitos a plazo fijo del sector privado (no ajustables)", "Millones de $", "promedio"),
    "prestamos_privados_pesos": (117, "Préstamos al sector privado en pesos", "Millones de $", "promedio"),
    "prestamos_adelantos": (110, "Préstamos al sector privado: adelantos en cuenta corriente", "Millones de $", "promedio"),
    "prestamos_documentos": (111, "Préstamos al sector privado: documentos", "Millones de $", "promedio"),
    "prestamos_hipotecarios": (112, "Préstamos al sector privado: hipotecarios", "Millones de $", "promedio"),
    "prestamos_prendarios": (113, "Préstamos al sector privado: prendarios", "Millones de $", "promedio"),
    "prestamos_personales": (114, "Préstamos al sector privado: personales", "Millones de $", "promedio"),
    "prestamos_tarjetas": (115, "Préstamos al sector privado: tarjetas de crédito", "Millones de $", "promedio"),
    "prestamos_privados_usd": (125, "Préstamos al sector privado en dólares", "Millones de USD", "promedio"),
    "tasa_tamar": (44, "Tasa TAMAR de bancos privados", "% nominal anual", "promedio"),
    "tasa_badlar": (7, "Tasa BADLAR de bancos privados", "% nominal anual", "promedio"),
    "tasa_tm20": (8, "Tasa TM20 de bancos privados", "% nominal anual", "promedio"),
    "tasa_plazo_fijo_30d": (12, "Tasa de depósitos a 30 días", "% nominal anual", "promedio"),
    "tasa_baibar": (11, "Tasa de préstamos interbancarios (BAIBAR)", "% nominal anual", "promedio"),
    "tasa_adelantos": (13, "Tasa de adelantos en cuenta corriente", "% nominal anual", "promedio"),
    "tasa_personales": (14, "Tasa de préstamos personales", "% nominal anual", "promedio"),
    "pases_pasivos": (152, "Pases pasivos del BCRA", "Millones de $", "promedio"),
    "cer": (30, "Coeficiente de estabilización de referencia (CER)", "Índice 2-2-2002=1", "fin"),
    "uva": (31, "Unidad de valor adquisitivo (UVA)", "$", "fin"),
    "icl": (40, "Índice para contratos de locación (ICL)", "Índice 30-6-2020=1", "fin"),
    "factor_total": (46, "Base monetaria: total de factores de explicación", "Millones de $", "suma"),
    "factor_compras_privado": (47, "Base monetaria: compras de divisas al sector privado", "Millones de $", "suma"),
    "factor_compras_tesoro": (48, "Base monetaria: compras de divisas al Tesoro", "Millones de $", "suma"),
    "factor_adelantos_tesoro": (49, "Base monetaria: adelantos transitorios al Tesoro", "Millones de $", "suma"),
    "factor_utilidades": (50, "Base monetaria: transferencia de utilidades al Tesoro", "Millones de $", "suma"),
    "factor_resto_tesoro": (51, "Base monetaria: resto de operaciones con el Tesoro", "Millones de $", "suma"),
    "factor_pases": (52, "Base monetaria: pases", "Millones de $", "suma"),
    "factor_letras_fiscales": (58, "Base monetaria: letras fiscales de liquidez (LEFI)", "Millones de $", "suma"),
    "factor_otros": (59, "Base monetaria: otras operaciones", "Millones de $", "suma"),
}
COLUMNAS = {k: Columna("", n, unidad=u) for k, (_, n, u, _) in VARIABLES.items()}


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for k, (num, *_r) in VARIABLES.items():
            filas, offset = [], 0
            while True:
                j = json.loads(descargar(API.format(num, PRIMER_PERIODO, f"{hoy:%Y-%m-%d}", offset), minimo=50))
                res = j.get("results") or []
                det = res[0].get("detalle", []) if res else []
                filas += det
                total = (j.get("metadata") or {}).get("resultset", {}).get("count", 0)
                offset += len(det)
                if not det or offset >= total:
                    break
            z.writestr(f"{k}.json", json.dumps(filas))
    return URL, buf.getvalue()


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    partes = {}
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        for k in columnas:
            filas = json.loads(z.read(f"{k}.json"))
            if not filas:
                raise ValueError(f"La API del BCRA no devolvió datos de {k} (variable {VARIABLES[k][0]}).")
            s = pd.Series([f["valor"] for f in filas], index=pd.to_datetime([f["fecha"] for f in filas]))
            partes[k] = pd.to_numeric(s, errors="coerce").groupby(level=0).last().sort_index()
    out = pd.DataFrame(partes)
    out = out[out.index >= PRIMER_PERIODO]
    out.index.name = "fecha"
    return out.reset_index()[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    if not nuevo["fecha"].is_monotonic_increasing or nuevo["fecha"].duplicated().any():
        errores.append("Fechas desordenadas o repetidas.")
    ult = nuevo.dropna(subset=["reservas"])
    if not len(ult) or (pd.Timestamp.today() - ult["fecha"].max()).days > 10:
        errores.append("Las reservas tienen más de 10 días de atraso.")
    if not nuevo["reservas"].dropna().between(1_000, 200_000).all():
        errores.append("Reservas fuera de rango.")
    tasas = [c for c in columnas if c.startswith("tasa_")]
    if not nuevo[tasas].stack().between(-5, 1_000).all():
        errores.append("Alguna tasa fuera de rango.")
    if anterior is not None and len(anterior):
        for c in columnas:
            if c in anterior and nuevo[c].count() < anterior[c].count() * 0.98:
                errores.append(f"{c}: se perdió historia.")
    return errores
