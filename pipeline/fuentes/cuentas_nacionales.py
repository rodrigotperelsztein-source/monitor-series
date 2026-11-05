"""Cuentas nacionales trimestrales: oferta y demanda globales (PIB, consumo, inversión, exportaciones, importaciones) a
precios de 2004 y corrientes, y valor agregado bruto por sector (INDEC, Informe de avance del nivel de actividad).

Archivo: sh_oferta_demanda_<mes>_<año>.xls (nombre con la fecha de publicación). Cuadros 1 (precios de 2004), 4 (PIB por
sector, precios de 2004) y 8 (precios corrientes). Millones de pesos, valores trimestrales. Las variaciones interanuales y
el índice de precios implícitos del PIB se calculan acá.
"""

from datetime import date

import pandas as pd

from pipeline.fuentes import _trimestral as t
from pipeline.fuentes._fechas import urls_mm_aa
from pipeline.fuentes._indec import Columna, buscar_hoja, leer_excel
from pipeline.fuentes._trim_fuente import a_tabla, validar_trimestral, var_ia

ID = "cuentas_nacionales"
NOMBRE = "Cuentas nacionales: PIB, oferta y demanda globales y valor agregado por sector (INDEC, trimestral)"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/sh_oferta_demanda_{mm}_{aa}.xls"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-9-47"
EXTENSION = "xls"
FRECUENCIA = "Q"
ORGANISMO = "INDEC"
UNIDAD = "Millones de $"
PRIMER_PERIODO = "2004-01-01"
CALENDARIO = "Informe de avance del nivel de actividad"

DEMANDA = {"pib": ("B1B", "Producto interno bruto"), "importaciones": ("P7", "Importaciones de bienes y servicios"),
           "consumo_privado": ("P3_S14_S15", "Consumo privado"), "consumo_publico": ("P3_S13", "Consumo público"),
           "exportaciones": ("P6", "Exportaciones de bienes y servicios"),
           "inversion": ("P51B", "Formación bruta de capital fijo"), "variacion_existencias": ("P52", "Variación de existencias")}
SECTORES = {"agro": ("A", "Agricultura, ganadería, caza y silvicultura"), "pesca": ("B", "Pesca"),
            "mineria": ("C", "Explotación de minas y canteras"), "industria": ("D", "Industria manufacturera"),
            "electricidad_gas_agua": ("E", "Electricidad, gas y agua"), "construccion": ("F", "Construcción"),
            "comercio": ("G", "Comercio mayorista, minorista y reparaciones"), "hoteles_restaurantes": ("H", "Hoteles y restaurantes"),
            "transporte_comunicaciones": ("I", "Transporte, almacenamiento y comunicaciones"),
            "intermediacion_financiera": ("J", "Intermediación financiera"),
            "inmobiliarias": ("K", "Actividades inmobiliarias, empresariales y de alquiler"),
            "administracion_publica": ("L", "Administración pública y defensa"), "ensenanza": ("M", "Enseñanza"),
            "salud": ("N", "Servicios sociales y de salud"), "otros_servicios": ("O", "Otras actividades de servicios"),
            "servicio_domestico": ("P", "Hogares privados con servicio doméstico")}

COLUMNAS = {}
for _k, (_c, _n) in DEMANDA.items():
    COLUMNAS[_k] = Columna("", f"{_n}, a precios de 2004")
    if _k != "variacion_existencias":
        COLUMNAS[f"{_k}_var_ia"] = Columna("", f"{_n}, a precios de 2004, var. % interanual", unidad="%",
                                           tipo="variacion", base=_k, rezago=4)
for _k, (_c, _n) in DEMANDA.items():
    COLUMNAS[f"{_k}_corriente"] = Columna("", f"{_n}, a precios corrientes")
COLUMNAS["pib_deflactor"] = Columna("", "Índice de precios implícitos del PIB (2004=100)", unidad="Índice 2004=100")
COLUMNAS["pib_deflactor_var_ia"] = Columna("", "Índice de precios implícitos del PIB, var. % interanual", unidad="%",
                                           tipo="variacion", base="pib_deflactor", rezago=4)
COLUMNAS["vab"] = Columna("", "Valor agregado bruto a precios básicos, a precios de 2004")
for _k, (_c, _n) in SECTORES.items():
    COLUMNAS[f"vab_{_k}"] = Columna("", f"Valor agregado bruto: {_n.lower()}, a precios de 2004")
    COLUMNAS[f"vab_{_k}_var_ia"] = Columna("", f"Valor agregado bruto: {_n.lower()}, var. % interanual", unidad="%",
                                           tipo="variacion", base=f"vab_{_k}", rezago=4)


def urls(hoy: date) -> list[str]:
    return urls_mm_aa(URL, hoy)


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    libro = leer_excel(contenido)
    c1, c4, c8 = (t.filas(buscar_hoja(libro, f"cuadro {n}")) for n in (1, 4, 8))
    s = {}
    for k, (cod, _) in DEMANDA.items():
        s[k] = t.buscar(c1, f"{cod} ")
        s[f"{k}_corriente"] = t.buscar(c8, f"{cod} ")
    s["pib_deflactor"] = s["pib_corriente"] / s["pib"] * 100
    s["vab"] = t.buscar(c4, "B1B VALOR AGREGADO")
    for k, (letra, _) in SECTORES.items():
        s[f"vab_{k}"] = t.buscar(c4, f"{letra} ", despues_de="B1B VALOR AGREGADO")
    for k in list(s):
        if f"{k}_var_ia" in columnas:
            s[f"{k}_var_ia"] = var_ia(s[k])
    return a_tabla(s, PRIMER_PERIODO)[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = validar_trimestral(nuevo, anterior, columnas, PRIMER_PERIODO)
    u = nuevo.iloc[-1]
    suma = sum(u[f"vab_{k}"] for k in SECTORES)
    if abs(suma / u["vab"] - 1) > 0.02:
        errores.append(f"Los sectores no suman el valor agregado ({suma:.0f} vs {u['vab']:.0f}).")
    if not 400_000 < u["pib"] < 2_000_000:
        errores.append(f"PIB a precios de 2004 fuera de rango ({u['pib']:.0f}).")
    return errores
