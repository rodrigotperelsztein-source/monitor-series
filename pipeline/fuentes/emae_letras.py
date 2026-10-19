"""EMAE por sector de actividad (letras A a O e impuestos netos de subsidios).

Fuente: INDEC, Estimador Mensual de Actividad Económica, base 2004=100, serie original.
Archivo: sh_emae_actividad_base2004.xls, hoja "Tabla Letras".
INDEC no publica las letras desestacionalizadas.
"""

import pandas as pd

from pipeline.fuentes._indec import Columna, leer_tabla_mensual, validar_tabla

ID = "emae_letras"
NOMBRE = "EMAE por sector de actividad (letras), serie original"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/sh_emae_actividad_base2004.xls"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-9-48"
EXTENSION = "xls"
HOJA = "Tabla Letras"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Índice base 2004=100"
PRIMER_PERIODO = "2004-01-01"

COLUMNAS = {
    "a_agro": Columna("A -", "A - Agricultura, ganadería, caza y silvicultura"),
    "b_pesca": Columna("B -", "B - Pesca"),
    "c_mineria": Columna("C -", "C - Explotación de minas y canteras"),
    "d_industria": Columna("D -", "D - Industria manufacturera"),
    "e_electricidad_gas_agua": Columna("E -", "E - Electricidad, gas y agua"),
    "f_construccion": Columna("F -", "F - Construcción"),
    "g_comercio": Columna("G -", "G - Comercio mayorista, minorista y reparaciones"),
    "h_hoteles_restaurantes": Columna("H -", "H - Hoteles y restaurantes"),
    "i_transporte_comunicaciones": Columna("I -", "I - Transporte y comunicaciones"),
    "j_intermediacion_financiera": Columna("J -", "J - Intermediación financiera"),
    "k_inmobiliarias_empresariales": Columna("K -", "K - Actividades inmobiliarias, empresariales y de alquiler"),
    "l_administracion_publica": Columna("L -", "L - Administración pública y defensa; seguridad social obligatoria"),
    "m_ensenanza": Columna("M -", "M - Enseñanza"),
    "n_salud": Columna("N -", "N - Servicios sociales y de salud"),
    "o_otros_servicios": Columna("O -", "O - Otras actividades de servicios comunitarios, sociales y personales"),
    "impuestos_netos": Columna("Impuestos netos", "Impuestos netos de subsidios"),
}

# Sectores muy volátiles que no se controlan contra el mismo mes del año anterior.
SIN_CONTROL_INTERANUAL = {"b_pesca"}


def leer(contenido: bytes) -> pd.DataFrame:
    return leer_tabla_mensual(contenido, HOJA, COLUMNAS)


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None) -> list[str]:
    return validar_tabla(nuevo, anterior, COLUMNAS, PRIMER_PERIODO, SIN_CONTROL_INTERANUAL)
