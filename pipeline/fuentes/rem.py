"""REM: Relevamiento de Expectativas de Mercado del BCRA (mediana de los pronósticos).

Fuente: BCRA, planilla histórica del REM (relevamiento-expectativas-mercado-historico.xlsx, hoja "Base de Datos
Completa"), que trae todas las encuestas desde junio de 2016. La encuesta se hace los últimos días de cada mes y
se publica los primeros días hábiles del siguiente.

Una fila por encuesta (fecha = mes de la encuesta). Cada columna es un pronóstico a un horizonte fijo, contado
desde el mes de la encuesta, para poder seguir cómo cambian las expectativas:
  - ipc_mes, ipc_mes_siguiente: inflación mensual esperada para el mes de la encuesta y el siguiente (%);
  - ipc_nucleo_mes: inflación núcleo esperada para el mes de la encuesta (%);
  - ipc_12m: inflación esperada para los próximos 12 meses (% i.a.); ipc_anio: para diciembre del año en curso;
  - tamar_mes_siguiente: tasa TAMAR esperada para el mes siguiente (TNA %);
  - tc_mes_siguiente, tc_fin_anio: tipo de cambio nominal esperado (promedio del mes siguiente y de diciembre, $/USD);
  - pib_trim_anterior, pib_trim_actual, pib_trim_siguiente: PIB, variación % trimestral desestacionalizada esperada
    para el trimestre anterior al de la encuesta (si INDEC todavía no lo publicó), el de la encuesta y el siguiente;
  - pib_anio, pib_anio_siguiente: PIB, variación % promedio anual esperada para el año en curso y el siguiente;
  - desocupacion_anio: desocupación esperada para el año en curso (% de la PEA);
  - exportaciones_anio, importaciones_anio: millones de dólares esperados para el año en curso;
  - resultado_primario_anio: resultado primario del sector público nacional esperado (miles de millones de $).
"""

import io
import re
from datetime import date

import pandas as pd

from pipeline.fuentes._indec import Columna

ID = "rem"
NOMBRE = "REM: expectativas de mercado del BCRA (mediana)"
PAGINA = "https://www.bcra.gob.ar/PublicacionesEstadisticas/Relevamiento_Expectativas_de_Mercado.asp"
URL = "https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/informes/relevamiento-expectativas-mercado-historico.xlsx"
EXTENSION = "xlsx"
FRECUENCIA = "M"
ORGANISMO = "BCRA (REM)"
UNIDAD = "%"
PRIMER_PERIODO = "2016-06-01"
CALENDARIO = ""
GUARDAR_ORIGINAL = False

COLUMNAS = {
    "ipc_mes": Columna("", "REM: inflación mensual esperada para el mes de la encuesta", unidad="%"),
    "ipc_mes_siguiente": Columna("", "REM: inflación mensual esperada para el mes siguiente", unidad="%"),
    "ipc_nucleo_mes": Columna("", "REM: inflación núcleo mensual esperada para el mes de la encuesta", unidad="%"),
    "ipc_12m": Columna("", "REM: inflación esperada para los próximos 12 meses", unidad="% i.a."),
    "ipc_anio": Columna("", "REM: inflación esperada para el año en curso (diciembre contra diciembre)", unidad="% i.a."),
    "tamar_mes_siguiente": Columna("", "REM: tasa TAMAR esperada para el mes siguiente", unidad="TNA %"),
    "tc_mes_siguiente": Columna("", "REM: tipo de cambio nominal esperado para el mes siguiente", unidad="$/USD"),
    "tc_fin_anio": Columna("", "REM: tipo de cambio nominal esperado para diciembre del año en curso", unidad="$/USD"),
    "pib_trim_anterior": Columna("", "REM: PIB, var. % trimestral desestacionalizada esperada, trimestre anterior al de la encuesta", unidad="%"),
    "pib_trim_actual": Columna("", "REM: PIB, var. % trimestral desestacionalizada esperada, trimestre de la encuesta", unidad="%"),
    "pib_trim_siguiente": Columna("", "REM: PIB, var. % trimestral desestacionalizada esperada, trimestre siguiente", unidad="%"),
    "pib_anio": Columna("", "REM: PIB, var. % promedio anual esperada para el año en curso", unidad="%"),
    "pib_anio_siguiente": Columna("", "REM: PIB, var. % promedio anual esperada para el año siguiente", unidad="%"),
    "desocupacion_anio": Columna("", "REM: desocupación esperada para el año en curso", unidad="% de la PEA"),
    "exportaciones_anio": Columna("", "REM: exportaciones esperadas para el año en curso", unidad="Millones de USD"),
    "importaciones_anio": Columna("", "REM: importaciones esperadas para el año en curso", unidad="Millones de USD"),
    "resultado_primario_anio": Columna("", "REM: resultado primario del SPNF esperado para el año en curso", unidad="Miles de millones de $"),
}

ROMANO = {"I": 1, "II": 2, "III": 3, "IV": 4}


def _trimestre(s) -> pd.Period | None:
    m = re.match(r"Trim\.\s*(IV|I{1,3})-(\d{2})", str(s).strip())
    return pd.Period(f"20{m[2]}Q{ROMANO[m[1]]}", "Q") if m else None


def _mes(s) -> pd.Period | None:
    try:
        return pd.Timestamp(s).to_period("M") if not isinstance(s, str) or re.match(r"\d{4}-\d{2}", s) else None
    except (ValueError, TypeError):
        return None


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    d = pd.read_excel(io.BytesIO(contenido), sheet_name="Base de Datos Completa", header=1)
    esperadas = {"Fecha de pronóstico", "Variable", "Referencia", "Período", "Mediana"}
    if not esperadas <= set(d.columns):
        raise ValueError(f"La planilla del REM cambió de formato: columnas {list(d.columns)}")
    d = d.dropna(subset=["Fecha de pronóstico", "Variable"])
    d["encuesta"] = pd.to_datetime(d["Fecha de pronóstico"]).dt.to_period("M")
    d["var"] = d["Variable"].str.strip()
    d["ref"] = d["Referencia"].astype(str).str.strip()
    d["per"] = d["Período"].astype(str).str.strip()
    filas = []
    for m, g in d.groupby("encuesta"):
        f = {"fecha": m.to_timestamp()}

        def val(var, ref_ini, periodo):
            r = g[(g["var"] == var) & g["ref"].str.startswith(ref_ini) & (g["per"] == periodo)]
            return float(r["Mediana"].iloc[0]) if len(r) and pd.notna(r["Mediana"].iloc[0]) else None

        ipc, nuc = "Precios minoristas (IPC nivel general; INDEC)", "Precios minoristas (IPC núcleo; INDEC)"
        mes, sig, anio = str(m.to_timestamp().date()), str((m + 1).to_timestamp().date()), str(m.year)
        mes_dt, sig_dt = f"{mes} 00:00:00", f"{sig} 00:00:00"
        f["ipc_mes"] = val(ipc, "var. % mensual", mes_dt) or val(ipc, "var. % mensual", mes)
        f["ipc_mes_siguiente"] = val(ipc, "var. % mensual", sig_dt) or val(ipc, "var. % mensual", sig)
        f["ipc_nucleo_mes"] = val(nuc, "var. % mensual", mes_dt) or val(nuc, "var. % mensual", mes)
        f["ipc_12m"] = val(ipc, "var. % i.a.", "Próx. 12 meses")
        f["ipc_anio"] = val(ipc, "var. % i.a.", anio)
        f["tamar_mes_siguiente"] = val("Tasa de interés (TAMAR)", "TNA", sig_dt) or val("Tasa de interés (TAMAR)", "TNA", sig)
        f["tc_mes_siguiente"] = val("Tipo de cambio nominal", "$/USD", sig_dt) or val("Tipo de cambio nominal", "$/USD", sig)
        f["tc_fin_anio"] = val("Tipo de cambio nominal", "$/USD", anio)
        pib = "PIB a precios constantes"
        q = m.asfreq("Q")
        trims = {_trimestre(p): v for p, v in g[(g["var"] == pib) & (g["ref"] == "var. % trim. s.e.")][["per", "Mediana"]].values}
        f["pib_trim_anterior"] = trims.get(q - 1)
        f["pib_trim_actual"] = trims.get(q)
        f["pib_trim_siguiente"] = trims.get(q + 1)
        f["pib_anio"] = val(pib, "var. % prom. anual", anio)
        f["pib_anio_siguiente"] = val(pib, "var. % prom. anual", str(m.year + 1))
        f["desocupacion_anio"] = val("Desocupación abierta", "% de la PEA", anio)
        f["exportaciones_anio"] = val("Exportaciones", "millones de USD", anio)
        f["importaciones_anio"] = val("Importaciones", "millones de USD", anio)
        rp = g[g["var"].str.lower() == "resultado primario del spnf"]
        r = rp[rp["per"] == anio]
        f["resultado_primario_anio"] = float(r["Mediana"].iloc[0]) if len(r) else None
        filas.append(f)
    out = pd.DataFrame(filas, columns=["fecha", *columnas])
    for c in columnas:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    if len(nuevo) < 100:
        errores.append(f"Solo {len(nuevo)} encuestas.")
    if not nuevo["fecha"].is_monotonic_increasing or nuevo["fecha"].duplicated().any():
        errores.append("Encuestas desordenadas o repetidas.")
    for c in ("pib_trim_actual", "pib_anio"):
        if not nuevo[c].dropna().between(-30, 30).all():
            errores.append(f"{c}: fuera de rango.")
    ult = nuevo.iloc[-1]
    if pd.isna(ult["pib_anio"]) or pd.isna(ult["ipc_12m"]):
        errores.append("La última encuesta no trae PIB o inflación: revisar el formato de la planilla.")
    return errores
