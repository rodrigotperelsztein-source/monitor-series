"""Resultado fiscal del Sector Público Nacional no financiero, base caja: ingresos, gastos, resultado primario,
intereses y resultado financiero, mensual desde 2016 (Secretaría de Hacienda, Informe mensual de ingresos y gastos).

Fuente: Ministerio de Economía, serie 452.3 del portal datos.gob.ar (imig-mensual.csv), que replica el IMIG que
publica Hacienda cada mes. Millones de pesos corrientes.
"""

import pandas as pd

from pipeline.fuentes._indec import Columna

ID = "imig"
NOMBRE = "Resultado fiscal del Sector Público Nacional, base caja (IMIG, Secretaría de Hacienda)"
URL = "https://infra.datos.gob.ar/catalog/sspm/dataset/452/distribution/452.3/download/imig-mensual.csv"
PAGINA = "https://www.argentina.gob.ar/economia/sechacienda/infoestadistica"
EXTENSION = "csv"
FRECUENCIA = "M"
ORGANISMO = "Secretaría de Hacienda"
UNIDAD = "Millones de $"
PRIMER_PERIODO = "2016-01-01"
CALENDARIO = ""

# id propio -> (columnas del CSV que se suman, nombre)
TRIBUTARIOS = ["iva_neto_reintegros", "ganancias", "aportes_contribuciones_seguridad_social", "debitos_creditos",
               "bienes_personales", "impuestos_internos", "combustibles", "derechos_exportacion", "derechos_importacion",
               "resto_tributarios"]
RENTAS = ["fgs_cobradas_sector_privado_sector_publico_financiero", "resto_rentas_propiedad"]
OTROS_CORR = ["ingresos_no_tributarios", "transferencias_corrientes", "resto_ingresos_corrientes"]
PRESTACIONES = ["jubilaciones_pensiones_contributivas", "asignacion_familiares_hijo", "pensiones_no_contributivas",
                "prestaciones_inssjp", "otros_programas"]
SUBSIDIOS = ["energia", "transporte", "otras_funciones"]
FUNCIONAMIENTO = ["salarios", "otros_gastos_funcionamiento"]
TRANSF_PROV = ["transferencias_corrientes_provincias_educacion", "transferencias_corrientes_provincias_seguridad_social",
               "transferencias_corrientes_provincias_desarrollo_social", "transferencias_corrientes_provincias_salud",
               "transferencias_corrientes_provincias_otras"]
OTROS_GASTOS = ["otros_corrientes_transferencias_universidades", "otros_corrientes_deficit_operativo_empresas_publicas",
                "otros_corrientes_resto"]
CAPITAL = ["capital_energia_nacion", "capital_energia_tranferencias_provincias", "capital_transporte_nacion",
           "capital_transporte_tranferencias_provincias", "capital_educacion_nacion", "capital_educacion_tranferencias_provincias",
           "capital_vivienda_nacion", "capital_vivienda_tranferencias_provincias", "capital_agua_potable_alcatarillado_nacion",
           "capital_agua_potable_alcatarillado_tranferencias_provincias", "capital_otros_nacion",
           "capital_otros_tranferencias_provincias", "fondo_federal_solidario"]
SERIES = {
    "ingresos_totales": (TRIBUTARIOS + RENTAS + OTROS_CORR + ["ingresos_capital"], "Ingresos totales"),
    "ingresos_tributarios": (TRIBUTARIOS, "Ingresos tributarios"),
    "iva": (["iva_neto_reintegros"], "IVA neto de reintegros"),
    "ganancias": (["ganancias"], "Ganancias"),
    "seguridad_social": (["aportes_contribuciones_seguridad_social"], "Aportes y contribuciones a la seguridad social"),
    "derechos_exportacion": (["derechos_exportacion"], "Derechos de exportación"),
    "rentas_propiedad": (RENTAS, "Rentas de la propiedad"),
    "gasto_primario": (PRESTACIONES + SUBSIDIOS + FUNCIONAMIENTO + TRANSF_PROV + OTROS_GASTOS + CAPITAL, "Gasto primario"),
    "prestaciones_sociales": (PRESTACIONES, "Prestaciones sociales"),
    "jubilaciones": (["jubilaciones_pensiones_contributivas"], "Jubilaciones y pensiones contributivas"),
    "asignaciones": (["asignacion_familiares_hijo"], "AUH y asignaciones familiares"),
    "subsidios": (SUBSIDIOS, "Subsidios económicos"),
    "subsidios_energia": (["energia"], "Subsidios económicos a la energía"),
    "subsidios_transporte": (["transporte"], "Subsidios económicos al transporte"),
    "gastos_funcionamiento": (FUNCIONAMIENTO, "Gastos de funcionamiento"),
    "salarios": (["salarios"], "Salarios"),
    "transferencias_provincias": (TRANSF_PROV, "Transferencias corrientes a provincias"),
    "universidades": (["otros_corrientes_transferencias_universidades"], "Transferencias a universidades"),
    "gasto_capital": (CAPITAL, "Gastos de capital"),
    "resultado_primario": (["resultado_primario"], "Resultado primario"),
    "intereses": (["intereses_netos"], "Intereses netos de la deuda"),
    "resultado_financiero": (["resultado_financiero"], "Resultado financiero"),
}
COLUMNAS = {k: Columna("", n) for k, (_, n) in SERIES.items()}


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    import io
    t = pd.read_csv(io.BytesIO(contenido), parse_dates=["indice_tiempo"])
    faltan = {c for cols, _ in SERIES.values() for c in cols} - set(t.columns)
    if faltan:
        raise ValueError(f"Faltan columnas en el CSV del IMIG: {sorted(faltan)[:5]}")
    out = pd.DataFrame({"fecha": t["indice_tiempo"]})
    for k, (cols, _) in SERIES.items():
        out[k] = t[cols].sum(axis=1, min_count=1)
    out = out[out["fecha"] >= PRIMER_PERIODO].sort_values("fecha").reset_index(drop=True)
    return out[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    esperado = pd.date_range(PRIMER_PERIODO, periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los meses no son consecutivos.")
    d = nuevo.dropna()
    dif = (d["ingresos_totales"] - d["gasto_primario"] - d["resultado_primario"]).abs()
    if (dif > d["ingresos_totales"].abs() * 0.005 + 1).any():
        errores.append(f"Ingresos menos gasto primario no da el resultado primario (diferencia máxima {dif.max():.0f}).")
    if ((d["resultado_primario"] - d["intereses"] - d["resultado_financiero"]).abs() > 1).any():
        errores.append("Resultado primario menos intereses no da el resultado financiero.")
    if anterior is not None and len(anterior) and len(nuevo) < len(anterior):
        errores.append("Se perdieron meses.")
    return errores
