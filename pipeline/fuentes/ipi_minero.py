"""IPI minero: nivel general (original, desestacionalizado y tendencia-ciclo), aperturas por categoría, división,
grupo y producto (serie original), y extracción de petróleo, gas y carbonato de litio en unidades físicas.

Fuente: INDEC, Índice de producción industrial minero, base 2016=100 (serie desde enero de 2017).
Archivo: serie_ipi_minero.xlsx.
Cuadros: 1 (nivel general), 2 (aperturas, índices de la serie original), 5 (petróleo crudo convencional y no
convencional, miles de m³), 6 (gas natural convencional y no convencional, millones de m³) y 7 (carbonato de
litio, toneladas; los primeros meses están en secreto estadístico y quedan vacíos).

Las aperturas de los cuadros 2, 5, 6 y 7 se leen por posición y se controla que el nombre de cada columna sea
el esperado: si INDEC agrega, quita o mueve una columna, la actualización frena.
"""

import pandas as pd

from pipeline.fuentes._indec import Columna, buscar_hoja, leer_excel, leer_tabla_mensual, norm, tabla_mensual, validar_tabla

ID = "ipi_minero"
NOMBRE = "IPI minero: nivel general, aperturas y producción de petróleo, gas y litio"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipi_minero.xlsx"
PAGINA = "https://www.indec.gob.ar/Nivel4/Tema/3/7/172"
EXTENSION = "xlsx"
FRECUENCIA = "M"
ORGANISMO = "INDEC"
UNIDAD = "Índice base 2016=100"
PRIMER_PERIODO = "2017-01-01"
CALENDARIO = "Índice de producción industrial minero"

ORIG, DES, TEN = "Serie original", "Serie desestacionalizada", "Serie tendencia-ciclo"
MES_ANT = "Variación porcentual respecto al mes anterior"
NIVEL_GENERAL = {
    "original": Columna(f"{ORIG} | Nivel general", "IPI minero, serie original", hoja="Cuadro 1"),
    "original_var_ia": Columna(f"{ORIG} | Variación porcentual | respecto al mismo mes",
                               "IPI minero, serie original, var. % interanual",
                               tipo="variacion", base="original", rezago=12, hoja="Cuadro 1"),
    "original_var_acum": Columna(f"{ORIG} | acumulada del año", "IPI minero, serie original, var. % acumulada en el año",
                                 tipo="variacion", rezago=12, hoja="Cuadro 1"),
    "desest": Columna(f"{DES} | Nivel general", "IPI minero, serie desestacionalizada (INDEC)", hoja="Cuadro 1"),
    "desest_var_m": Columna(f"{DES} | {MES_ANT}", "IPI minero, desestacionalizada (INDEC), var. % mensual",
                            tipo="variacion", base="desest", rezago=1, hoja="Cuadro 1"),
    "tendencia": Columna(f"{TEN} | Nivel general", "IPI minero, serie tendencia-ciclo", hoja="Cuadro 1"),
    "tendencia_var_m": Columna(f"{TEN} | {MES_ANT}", "IPI minero, tendencia-ciclo, var. % mensual",
                               tipo="variacion", base="tendencia", rezago=1, hoja="Cuadro 1"),
}

# Cuadro 2: posición -> (id, comienzo del nombre en el archivo, nombre para mostrar). Los "g_" son agregados
# (categoría, división o grupo); el resto, productos dentro del agregado anterior.
APERTURAS = {
    4: ("g_petroleo_gas", "Extracción de petróleo crudo y gas natural", "Extracción de petróleo crudo y gas natural y servicios de apoyo"),
    5: ("petroleo_crudo", "Petróleo crudo", "Petróleo crudo"),
    6: ("gas_natural", "Gas natural", "Gas natural"),
    7: ("servicios_apoyo", "Servicios de apoyo", "Servicios de apoyo para la extracción de petróleo y gas"),
    8: ("g_metaliferos", "Extracción de minerales metalíferos", "Extracción de minerales metalíferos"),
    9: ("plata_oro", "Plata y oro", "Plata y oro y sus concentrados"),
    10: ("bullon_dore", "Bullón Dorado", "Bullón dorado (doré)"),
    11: ("metaliferos_resto", "Resto (incluye hierro", "Resto de metalíferos (hierro, cobre, plomo, cinc, molibdeno y otros)"),
    12: ("g_no_metaliferos", "Extracción de minerales no metalíferos", "Extracción de minerales no metalíferos y rocas de aplicación"),
    13: ("g_rocas_ornamentales", "Extracción de rocas ornamentales", "Extracción de rocas ornamentales"),
    14: ("granito", "Granito", "Granito"),
    15: ("piedra_laja", "Piedra laja", "Piedra laja"),
    16: ("dolomita_cruda", "Dolomita cruda", "Dolomita cruda, excepto para cal o cemento"),
    17: ("rocas_ornamentales_resto", "Resto (incluye mármol", "Resto de rocas ornamentales (mármol, travertino y otras)"),
    18: ("g_caliza_yeso", "Extracción de piedra caliza y yeso", "Extracción de piedra caliza y yeso"),
    19: ("yeso", "Yeso", "Yeso"),
    20: ("caliza_cal_cemento", "Roca o piedra caliza", "Piedra caliza y calcáreos para cal y cemento"),
    21: ("clinker", "Clínker", "Clínker"),
    22: ("g_arenas_triturados", "Extracción de arenas", "Extracción de arenas, canto rodado y triturados pétreos"),
    23: ("arena_construccion", "Arena común", "Arena común para construcción"),
    24: ("arenas_industriales", "Arenas industriales", "Arenas industriales y arenas y gravas silíceas"),
    25: ("arenas_fractura", "Arenas de fractura", "Arenas de fractura (fracking)"),
    26: ("triturados_petreos", "Rocas para triturados", "Rocas para triturados pétreos"),
    27: ("canto_rodado", "Canto rodado", "Canto rodado, granza y ripio"),
    28: ("arenas_triturados_resto", "Resto (incluye roca o piedra caliza", "Resto de arenas y triturados"),
    29: ("g_arcilla_caolin", "Extracción de arcilla", "Extracción de arcilla y caolín"),
    30: ("caolin_bentonita", "Caolín y bentonita", "Caolín y bentonita"),
    31: ("arcilla_comun", "Arcilla común", "Arcilla común"),
    32: ("arcillas_plasticas", "Arcillas plásticas", "Arcillas plásticas"),
    33: ("zeolita_limo", "Zeolita", "Zeolita natural y limo arcilloso"),
    34: ("g_minerales_quimicos", "Extracción de minerales para la fabricación", "Extracción de minerales para productos químicos"),
    35: ("litio", "Carbonato de litio", "Carbonato de litio y otros minerales de litio"),
    36: ("calcita", "Calcita", "Calcita y carbonato de calcio"),
    37: ("boro", "Minerales de boro", "Minerales de boro"),
    38: ("minerales_quimicos_resto", "Resto (incluye sulfato", "Resto de minerales para productos químicos"),
    39: ("g_sal", "Extracción de sal", "Extracción de sal"),
    40: ("salmuera", "Salmuera", "Salmuera o solución saturada de sal"),
    41: ("sal_refinada", "Sal refinada", "Sal refinada, de mesa e industrial"),
    42: ("cloruro_sodio", "Cloruro de sodio", "Cloruro de sodio puro"),
    43: ("g_carbon_otros", "Extracción y aglomeración de carbón", "Carbón, turba y explotación de minas y canteras n.c.p."),
    44: ("turba", "Turba", "Turba"),
    45: ("puzolana_feldespato", "Puzolana", "Puzolana y feldespatos"),
    46: ("suelo_seleccionado", "Suelo seleccionado", "Suelo seleccionado o estabilizado para relleno"),
    47: ("cuarzo", "Cuarzo", "Cuarzo y cuarzo amatista"),
    48: ("diatomita_perlita", "Diatomita", "Diatomita y perlita"),
    49: ("carbon_otros_resto", "Resto (incluye carbón", "Resto (carbón térmico, talco, baritina y otros)"),
}
# Cuadros 5, 6 y 7: (hoja, posición) -> (id, comienzo del nombre, nombre para mostrar, unidad)
FISICAS = {
    ("Cuadro 5", 3): ("petroleo_m3", "Petróleo crudo", "Extracción de petróleo crudo", "Miles de m³"),
    ("Cuadro 5", 4): ("petroleo_convencional_m3", "Petróleo crudo convencional", "Extracción de petróleo crudo convencional", "Miles de m³"),
    ("Cuadro 5", 5): ("petroleo_no_convencional_m3", "Petróleo crudo no convencional", "Extracción de petróleo crudo no convencional", "Miles de m³"),
    ("Cuadro 6", 3): ("gas_m3", "Gas natural", "Extracción de gas natural", "Millones de m³"),
    ("Cuadro 6", 4): ("gas_convencional_m3", "Gas natural convencional", "Extracción de gas natural convencional", "Millones de m³"),
    ("Cuadro 6", 5): ("gas_no_convencional_m3", "Gas natural no convencional", "Extracción de gas natural no convencional", "Millones de m³"),
    ("Cuadro 7", 3): ("litio_toneladas", "Carbonato de litio", "Producción de carbonato de litio", "Toneladas"),
}

COLUMNAS = dict(NIVEL_GENERAL)
for _j, (_cid, _, _nombre) in APERTURAS.items():
    COLUMNAS[f"orig_{_cid}"] = Columna("", f"IPI minero, {_nombre} (serie original)", hoja="Cuadro 2")
for (_h, _j), (_cid, _, _nombre, _u) in FISICAS.items():
    COLUMNAS[_cid] = Columna("", _nombre, unidad=_u, hoja=_h)
APERTURAS_IDS = [c for c in COLUMNAS if c not in NIVEL_GENERAL]


def _por_posicion(libro, hoja: str, posiciones: dict[int, tuple[str, str]]) -> pd.DataFrame:
    """Columnas de una hoja por posición, controlando que el último encabezado empiece con el nombre esperado."""
    datos, _, originales = tabla_mensual(buscar_hoja(libro, hoja))
    out = pd.DataFrame({"fecha": datos["fecha"]})
    for j, (cid, esperado) in posiciones.items():
        textos = [t for t in originales.get(j, []) if norm(t) not in ("%", "NUMEROS INDICE", "MILES DE M3", "MILLONES DE M3", "TONELADAS")]
        nombre = textos[-1] if textos else ""
        if not norm(nombre).startswith(norm(esperado)):
            raise ValueError(f"{hoja}, columna {j}: esperaba '{esperado}' y dice '{nombre}'.")
        out[cid] = datos[j].values
    return out.dropna(how="all", subset=[c for c, _ in posiciones.values()])


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    libro = leer_excel(contenido)
    df = leer_tabla_mensual(contenido, None, NIVEL_GENERAL)
    partes = [_por_posicion(libro, "Cuadro 2", {j: (f"orig_{c}", e) for j, (c, e, _) in APERTURAS.items()})]
    for hoja in ("Cuadro 5", "Cuadro 6", "Cuadro 7"):
        partes.append(_por_posicion(libro, hoja, {j: (c, e) for (h, j), (c, e, _, _) in FISICAS.items() if h == hoja}))
    for p in partes:
        df = df.merge(p, on="fecha", how="left")
    return df[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    # Las aperturas son muy volátiles (y algunas tienen meses en cero o en secreto): sin control interanual.
    sin_control = set(APERTURAS_IDS)
    return validar_tabla(nuevo, anterior, columnas, PRIMER_PERIODO, sin_control, rango_nivel=(-1e-9, 1e6),
                         max_variacion=1e6, vacios_permitidos=sin_control)
