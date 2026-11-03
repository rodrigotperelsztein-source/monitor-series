"""Gas natural entregado a usuarios finales, total del sistema, por tipo de usuario y GNC por área de licencia (ENARGAS).

Fuente: ENARGAS, Datos operativos de transporte y distribución, planilla GETD.xlsx ("Total sistema: gas entregado").
En miles de m³ de 9.300 kcal, mensual desde 1993. La planilla trae dos tablas dinámicas armadas sobre la misma base
(período, fuente, distribuidora y tipo de cliente); se lee esa base, guardada en la caché de la tabla dinámica, en vez
de las hojas, que muestran solo el filtro con que se guardó el archivo. Así se obtiene el GNC (lo que entregan las
distribuidoras a las estaciones de GNC) para el total del país y por área de licencia, que en la planilla se ve
tocando el filtro de tipo de cliente de la hoja AreaLicencia.

Se agrega el GNC en miles de m³ por día (el total del mes dividido por sus días), que es como se suele citar.
"""

import io
import zipfile
import xml.etree.ElementTree as ET

import pandas as pd

from pipeline.fuentes._indec import Columna

ID = "gas_entregado"
NOMBRE = "Gas natural entregado por tipo de usuario y GNC por área de licencia (ENARGAS)"
URL = "https://www.enargas.gob.ar/secciones/transporte-y-distribucion/datos-estadisticos/GETD/GETD.xlsx"
PAGINA = "https://www.enargas.gob.ar/secciones/transporte-y-distribucion/datos-operativos.php"
EXTENSION = "xlsx"
FRECUENCIA = "M"
ORGANISMO = "ENARGAS"
UNIDAD = "Miles de m³ de 9.300 kcal"
PRIMER_PERIODO = "1993-01-01"
CALENDARIO = ""
GUARDAR_ORIGINAL = False

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
CAMPOS = ["Periodo", "Fuente", "Distribuidor", "TipoDeCliente", "Volumen"]
TIPOS = {"residencial": "Residencial", "comercial": "Comercial", "entes_oficiales": "Entes Oficiales",
         "industria": "Industria", "centrales": "Centrales eléctricas", "gnc": "GNC", "subdistribuidor": "Subdistribuidor",
         "rtp": "RTP", "exportaciones": "Exportaciones"}
AREAS = {"metrogas": ("Metrogas", "Metrogas (CABA y sur del conurbano)"), "ban": ("Ban", "Naturgy BAN (norte y oeste del conurbano)"),
         "pampeana": ("Pampeana", "Camuzzi Pampeana"), "sur": ("Sur", "Camuzzi Sur"), "litoral": ("Litoral", "Litoral Gas"),
         "centro": ("Centro", "Ecogas Centro"), "cuyana": ("Cuyana", "Ecogas Cuyana"), "noroeste": ("Noroeste", "Gasnor (Noroeste)"),
         "gasnea": ("GasNea", "GasNEA"), "parana": ("Parana", "Redengas (Paraná)")}

COLUMNAS = {"total": Columna("", "Gas entregado a usuarios finales, total del sistema")}
for _k, _n in TIPOS.items():
    COLUMNAS[_k] = Columna("", f"Gas entregado: {_n.lower() if _k != 'gnc' else 'GNC (estaciones de carga)'}")
COLUMNAS["gnc_por_dia"] = Columna("", "GNC: promedio diario del mes", unidad="Miles de m³ de 9.300 kcal por día")
COLUMNAS["gnc_var_ia"] = Columna("", "GNC: var. % interanual", tipo="variacion", base="gnc", rezago=12)
for _k, (_, _n) in AREAS.items():
    COLUMNAS[f"gnc_{_k}"] = Columna("", f"GNC entregado en el área de {_n}")


def base(contenido: bytes) -> pd.DataFrame:
    """La base de la tabla dinámica: una fila por período, fuente, distribuidora y tipo de cliente."""
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        nombres = z.namelist()
        defs = [n for n in nombres if n.startswith("xl/pivotCache/pivotCacheDefinition") and n.endswith(".xml")]
        if not defs:
            raise ValueError("La planilla no trae la base de la tabla dinámica.")
        d = ET.fromstring(z.read(defs[0]))
        campos = []
        for cf in d.find("m:cacheFields", NS):
            it = cf.find("m:sharedItems", NS)
            campos.append((cf.get("name"), [c.get("v") for c in it] if it is not None else []))
        if [n for n, _ in campos] != CAMPOS:
            raise ValueError(f"Cambiaron los campos de la base: {[n for n, _ in campos]}")
        reg = defs[0].replace("Definition", "Records")
        r = ET.fromstring(z.read(reg))
    filas = []
    for rec in r:
        fila = []
        for (_, items), c in zip(campos, rec):
            tag, v = c.tag.split("}")[1], c.get("v")
            fila.append(items[int(v)] if tag == "x" else (None if tag == "m" else v))
        filas.append(fila)
    df = pd.DataFrame(filas, columns=CAMPOS)
    if len(df) != int(d.get("recordCount", len(df))):
        raise ValueError("La base no tiene la cantidad de registros que declara.")
    df["fecha"] = pd.to_datetime(df["Periodo"]).dt.to_period("M").dt.to_timestamp()
    df["Volumen"] = pd.to_numeric(df["Volumen"], errors="coerce")
    return df


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    df = base(contenido)
    desconocidos = set(df["TipoDeCliente"]) - set(TIPOS.values())
    if desconocidos:
        raise ValueError(f"Tipos de cliente nuevos: {desconocidos}")
    por_tipo = df.pivot_table(index="fecha", columns="TipoDeCliente", values="Volumen", aggfunc="sum")
    gnc = df[df["TipoDeCliente"] == "GNC"].pivot_table(index="fecha", columns="Distribuidor", values="Volumen", aggfunc="sum")
    out = pd.DataFrame(index=por_tipo.index)
    out["total"] = df.groupby("fecha")["Volumen"].sum()
    for k, n in TIPOS.items():
        out[k] = por_tipo.get(n)
    out["gnc_por_dia"] = out["gnc"] / out.index.days_in_month
    out["gnc_var_ia"] = out["gnc"].pct_change(12, fill_method=None) * 100
    for k, (cod, _) in AREAS.items():
        out[f"gnc_{k}"] = gnc.get(cod)
    out.index.name = "fecha"
    return out.sort_index().reset_index()[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    if len(nuevo) < 300:
        errores.append(f"Solo {len(nuevo)} meses.")
    f = nuevo["fecha"]
    if not f.is_monotonic_increasing or (f.diff().dropna().dt.days > 31).any():
        errores.append("Faltan meses o están desordenados.")
    suma = nuevo[list(TIPOS)].sum(axis=1)
    if ((suma - nuevo["total"]).abs() > 1).any():
        errores.append("La suma por tipo de usuario no da el total.")
    areas = nuevo[[f"gnc_{k}" for k in AREAS]].sum(axis=1)
    if ((areas - nuevo["gnc"]).abs() > 1).any():
        errores.append("La suma del GNC por área no da el GNC total.")
    g = nuevo["gnc_por_dia"].dropna()
    if not g.between(1_000, 30_000).all():
        errores.append("GNC por día fuera de rango (1 a 30 millones de m³).")
    if anterior is not None and len(anterior) and len(nuevo) < len(anterior):
        errores.append("La serie nueva es más corta que la guardada.")
    if (pd.Timestamp.today() - f.max()).days > 150:
        errores.append("El último mes tiene más de cuatro meses de atraso.")
    return errores
