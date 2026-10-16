"""EMAE por sector de actividad (letras A a O e impuestos netos de subsidios).

Fuente: INDEC, Estimador Mensual de Actividad Económica, base 2004=100, serie original.
Archivo: sh_emae_actividad_base2004.xls, hoja "Tabla Letras".

Estructura del archivo (octubre de 2026):
  - una fila de encabezados con "Período" y un texto por sector ("A - Agricultura, ...");
  - debajo, una fila por mes: el año figura solo en enero (columna 0) y el mes en la columna 1;
  - al final, una nota "Fuente: INDEC."

El lector busca los encabezados por su texto y no por posición fija, para tolerar
filas o columnas agregadas.
"""

import io
import unicodedata

import pandas as pd

ID = "emae_letras"
NOMBRE = "EMAE por sector de actividad (letras), serie original"
URL = "https://www.indec.gob.ar/ftp/cuadros/economia/sh_emae_actividad_base2004.xls"
PAGINA = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-9-48"
EXTENSION = "xls"
HOJA = "Tabla Letras"
FRECUENCIA = "M"
UNIDAD = "Índice base 2004=100"

# id de columna -> (prefijo con que empieza el encabezado en el archivo, nombre para mostrar)
SECTORES = {
    "a_agro": ("A -", "A - Agricultura, ganadería, caza y silvicultura"),
    "b_pesca": ("B -", "B - Pesca"),
    "c_mineria": ("C -", "C - Explotación de minas y canteras"),
    "d_industria": ("D -", "D - Industria manufacturera"),
    "e_electricidad_gas_agua": ("E -", "E - Electricidad, gas y agua"),
    "f_construccion": ("F -", "F - Construcción"),
    "g_comercio": ("G -", "G - Comercio mayorista, minorista y reparaciones"),
    "h_hoteles_restaurantes": ("H -", "H - Hoteles y restaurantes"),
    "i_transporte_comunicaciones": ("I -", "I - Transporte y comunicaciones"),
    "j_intermediacion_financiera": ("J -", "J - Intermediación financiera"),
    "k_inmobiliarias_empresariales": ("K -", "K - Actividades inmobiliarias, empresariales y de alquiler"),
    "l_administracion_publica": ("L -", "L - Administración pública y defensa; seguridad social obligatoria"),
    "m_ensenanza": ("M -", "M - Enseñanza"),
    "n_salud": ("N -", "N - Servicios sociales y de salud"),
    "o_otros_servicios": ("O -", "O - Otras actividades de servicios comunitarios, sociales y personales"),
    "impuestos_netos": ("IMPUESTOS NETOS", "Impuestos netos de subsidios"),
}

# Sectores muy volátiles que no se controlan contra el mismo mes del año anterior.
SIN_CONTROL_INTERANUAL = {"b_pesca"}

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

PRIMER_PERIODO = "2004-01-01"


def _norm(texto) -> str:
    """Mayúsculas, sin tildes ni espacios repetidos."""
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return ""
    s = unicodedata.normalize("NFKD", str(texto))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.upper().split())


def leer(contenido: bytes) -> pd.DataFrame:
    """Devuelve un DataFrame con la columna 'fecha' (primer día del mes) y una columna por sector."""
    hoja = pd.read_excel(io.BytesIO(contenido), sheet_name=HOJA, header=None, engine="xlrd")

    # 1. Fila de encabezados: la que tiene un texto que empieza con "A -".
    fila_enc = None
    for i in range(min(len(hoja), 30)):
        if any(_norm(v).startswith("A -") for v in hoja.iloc[i].tolist()):
            fila_enc = i
            break
    if fila_enc is None:
        raise ValueError("No encontré la fila de encabezados (ningún texto empieza con 'A -').")

    # 2. Columna de cada sector, buscada por el comienzo del texto.
    encabezados = {j: _norm(v) for j, v in enumerate(hoja.iloc[fila_enc].tolist())}
    columnas = {}
    for sid, (prefijo, _) in SECTORES.items():
        coincidencias = [j for j, t in encabezados.items() if t.startswith(prefijo)]
        if len(coincidencias) != 1:
            raise ValueError(f"Encabezado de {sid} ('{prefijo}'): {len(coincidencias)} coincidencias, esperaba 1.")
        columnas[sid] = coincidencias[0]

    # 3. Filas de datos: año (se arrastra desde enero) y mes en las dos primeras columnas.
    registros = []
    anio = None
    for i in range(fila_enc + 1, len(hoja)):
        fila = hoja.iloc[i]
        a, m = fila.iloc[0], fila.iloc[1]
        if pd.notna(a):
            try:
                anio = int(float(str(a).strip().rstrip("*")))
            except ValueError:
                pass  # textos como "Fuente: INDEC." no cambian el año
        mes = MESES.get(_norm(m).lower().rstrip("*").strip())
        if mes is None or anio is None:
            continue
        valores = {sid: pd.to_numeric(fila.iloc[j], errors="coerce") for sid, j in columnas.items()}
        if all(pd.isna(v) for v in valores.values()):
            continue
        registros.append({"fecha": pd.Timestamp(anio, mes, 1), **valores})

    if not registros:
        raise ValueError("No encontré filas de datos debajo de los encabezados.")
    return pd.DataFrame(registros)


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None) -> list[str]:
    """Devuelve una lista de errores (vacía si todo está bien). Los avisos van por print."""
    errores = []
    cols = list(SECTORES)

    if list(nuevo.columns) != ["fecha"] + cols:
        errores.append(f"Columnas inesperadas: {list(nuevo.columns)}")
        return errores

    # Fechas consecutivas, desde el primer período conocido.
    esperado = pd.date_range(PRIMER_PERIODO, periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append(f"Las fechas no son meses consecutivos desde {PRIMER_PERIODO}.")

    # Sin huecos y en rango razonable para un índice base 2004=100.
    huecos = nuevo[cols].isna().sum()
    if huecos.any():
        errores.append(f"Valores vacíos: {huecos[huecos > 0].to_dict()}")
    fuera = ((nuevo[cols] <= 0) | (nuevo[cols] > 2000)).sum()
    if fuera.any():
        errores.append(f"Valores fuera de rango (0, 2000]: {fuera[fuera > 0].to_dict()}")

    if anterior is not None and len(anterior):
        # No puede perder historia.
        if nuevo["fecha"].max() < anterior["fecha"].max():
            errores.append("El último período es anterior al de la versión guardada.")
        if len(nuevo) < len(anterior):
            errores.append(f"Tiene menos meses ({len(nuevo)}) que la versión guardada ({len(anterior)}).")

        # Revisiones: se aceptan, pero una diferencia enorme suele ser un error de lectura.
        comunes = nuevo.merge(anterior, on="fecha", suffixes=("", "_ant"))
        for c in cols:
            dif = (comunes[c] / comunes[f"{c}_ant"] - 1).abs()
            if (dif > 0.25).any():
                errores.append(f"{c}: valores históricos cambiaron más de 25% respecto de la versión guardada.")
            elif (dif > 0.0005).any():
                print(f"Aviso: {c} tiene {(dif > 0.0005).sum()} meses revisados respecto de la versión guardada.")

        # Meses nuevos: comparación contra el mismo mes del año anterior.
        nuevos = nuevo[nuevo["fecha"] > anterior["fecha"].max()]
        indexado = nuevo.set_index("fecha")
        for _, fila in nuevos.iterrows():
            hace_un_anio = fila["fecha"] - pd.DateOffset(years=1)
            if hace_un_anio not in indexado.index:
                continue
            for c in cols:
                if c in SIN_CONTROL_INTERANUAL:
                    continue
                ratio = fila[c] / indexado.loc[hace_un_anio, c]
                if not 0.2 <= ratio <= 5:
                    errores.append(f"{c} {fila['fecha']:%Y-%m}: variación interanual sospechosa (x{ratio:.2f}).")
    return errores
