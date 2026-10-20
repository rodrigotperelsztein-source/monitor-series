"""CAMMESA: demanda diaria de los grandes usuarios del MEM (GUMA) por actividad.

Fuente: CAMMESA, "Comportamiento de la demanda de energía eléctrica en el MEM" (informe semanal),
"Base de datos información por región" -> "Base de datos GU Semanal.xlsx", hoja
"Base Detalle diaria GUMAs ACT". Demanda media del día en MW, desde enero de 2022.

Actividades (las agrupa CAMMESA):
  - Alimentación, comercios y servicios: cargas y puertos; comercio y servicios; industria de la
    alimentación; servicios públicos y transporte.
  - Industrias: automotriz; derivados de petróleo; construcción; madera y papel; productos metálicos
    no automotores; textil; químicas, caucho, plástico y minerales no metálicos; gran siderurgia.
  - Petróleo y minerales: extracción de minerales; extracción de petróleo.
  - Aluar.
  - Total (autogeneradores + GUMAs).

CAMMESA aclara que los datos son provisorios: salen de mediciones operativas que se ajustan a lo
largo del mes. Se publica una vez por semana; cada vez se reemplaza toda la serie.
"""

import io
import unicodedata
import zipfile

import pandas as pd

from pipeline.fuentes._indec import Columna

ID = "cammesa_gu_actividad"
NOMBRE = "CAMMESA: demanda diaria de grandes usuarios (GUMA) por actividad"
URL = "https://cammesaweb.cammesa.com/download/base-de-datos-2/?wpdmdl=39428"
PAGINA = "https://cammesaweb.cammesa.com/2026/10/16/covid-19-comportamiento-de-la-demanda-de-energia-electrica-en-el-mem/"
EXTENSION = "zip"
FRECUENCIA = "D"
ORGANISMO = "CAMMESA"
UNIDAD = "MW (demanda media del día)"
PRIMER_PERIODO = "2022-01-01"
CALENDARIO = ""
GUARDAR_ORIGINAL = False
REGISTRAR_REVISIONES = False
HOJA = "Base Detalle diaria GUMAs ACT"

# id: (encabezado en la hoja, nombre)
SERIES = {
    "total": ("AUTO+GUMAs", "total (autogeneradores + GUMAs)"),
    "alim_com_serv": ("ALIMENTACIÓN, COMERCIOS Y SERVICIOS TOTAL", "alimentación, comercios y servicios (total)"),
    "cargas_puertos": ("CARGAS Y PUERTOS", "cargas y puertos"),
    "comercio_servicios": ("COMERCIO Y SERVICIOS", "comercio y servicios"),
    "ind_alimentacion": ("INDUSTRIA DE LA ALIMENTACIÓN", "industria de la alimentación"),
    "servicios_publicos_transporte": ("SECTOR DE SERVICIOS PÚBLICOS", "servicios públicos y transporte"),
    "industrias": ("INDUSTRIAS TOTAL", "industrias (total)"),
    "ind_automotriz": ("INDUSTRIA AUTOMOTRIZ", "industria automotriz"),
    "ind_derivados_petroleo": ("INDUSTRIA DE DERIVADOS DE PETRÓLEO", "industria de derivados de petróleo"),
    "ind_construccion": ("INDUSTRIA DE LA CONSTRUCCIÓN", "industria de la construcción"),
    "ind_madera_papel": ("INDUSTRIA DE LA MADERA Y EL PAPEL", "industria de la madera y el papel"),
    "ind_metalicos": ("INDUSTRIA DE PRODUCTOS METÁLICOS", "productos metálicos no automotores"),
    "ind_textil": ("INDUSTRIA TEXTIL", "industria textil"),
    "ind_quimicas": ("INDUSTRIAS QUÍMICAS", "químicas, caucho, plástico y minerales no metálicos"),
    "gran_siderurgia": ("GRAN SIDERURGIA", "gran siderurgia"),
    "petroleo_minerales": ("PETROLEOS Y MINERALES TOTAL", "petróleo y minerales (total)"),
    "extraccion_minerales": ("EXTRACCIÓN DE MINERALES", "extracción de minerales"),
    "extraccion_petroleo": ("EXTRACCIÓN DE PETRÓLEO", "extracción de petróleo"),
    "aluar": ("ALUAR", "Aluar"),
}
GRUPOS = {
    "alim_com_serv": ["cargas_puertos", "comercio_servicios", "ind_alimentacion", "servicios_publicos_transporte"],
    "industrias": ["ind_automotriz", "ind_derivados_petroleo", "ind_construccion", "ind_madera_papel",
                   "ind_metalicos", "ind_textil", "ind_quimicas", "gran_siderurgia"],
    "petroleo_minerales": ["extraccion_minerales", "extraccion_petroleo"],
    "total": ["alim_com_serv", "industrias", "petroleo_minerales", "aluar"],
}
COLUMNAS = {cid: Columna("", f"Demanda de grandes usuarios (GUMA), {n}") for cid, (_, n) in SERIES.items()}
COLUMNAS["dia_habil"] = Columna("", "Día hábil según CAMMESA (1 = hábil, 0 = no hábil)", unidad="indicador")


def _norm(s) -> str:
    s = "" if pd.isna(s) else str(s)
    return " ".join("".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
                    .upper().split())


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        nombre = next((n for n in z.namelist() if n.lower().endswith(".xlsx")), None)
        if not nombre:
            raise ValueError("El zip no trae un Excel.")
        hoja = pd.read_excel(io.BytesIO(z.read(nombre)), sheet_name=HOJA, header=None)
    cab = [i for i in range(len(hoja)) if _norm(hoja.iat[i, 1]) == "ANO"]
    if len(cab) != 1:
        raise ValueError(f"No encontré la fila de encabezados ('Año') en la hoja {HOJA}.")
    encabezados = [_norm(v) for v in hoja.iloc[cab[0]]]
    datos = hoja.iloc[cab[0] + 1:]
    out = pd.DataFrame()
    fecha_mes = pd.to_datetime(datos[encabezados.index("MES/ANO")], errors="coerce")
    dia = pd.to_numeric(datos[encabezados.index("N° DIA")], errors="coerce")
    ok = fecha_mes.notna() & dia.notna()
    out["fecha"] = [pd.Timestamp(f.year, f.month, int(d)) for f, d in zip(fecha_mes[ok], dia[ok])]
    tipo = datos.loc[ok, encabezados.index("HABIL/NO HABIL")].map(_norm)
    if not set(tipo) <= {"HABIL", "NO HABIL"}:
        raise ValueError(f"Valores inesperados en Hábil/No Hábil: {set(tipo)}")
    out["dia_habil"] = (tipo == "HABIL").astype(int).values
    for cid, (rotulo, _) in SERIES.items():
        r = _norm(rotulo)
        cols = [j for j, e in enumerate(encabezados) if e == r or (e.startswith(r) and cid not in GRUPOS and r != "ALUAR")]
        if r == "ALUAR":
            cols = [j for j, e in enumerate(encabezados) if e == "ALUAR"]
        if len(cols) != 1:
            raise ValueError(f"No encontré una única columna '{rotulo}' (encontré {len(cols)}).")
        out[cid] = pd.to_numeric(datos.loc[ok, cols[0]], errors="coerce").values
    return out.sort_values("fecha").reset_index(drop=True)[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if nuevo["fecha"].min() != pd.Timestamp(PRIMER_PERIODO):
        errores.append(f"La serie no empieza el {PRIMER_PERIODO}.")
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="D")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los días no son consecutivos.")
    if nuevo[list(SERIES)].isna().any().any():
        errores.append(f"Hay valores vacíos: {nuevo[list(SERIES)].isna().sum()[lambda s: s > 0].to_dict()}")
    for grupo, partes in GRUPOS.items():
        dif = (nuevo[partes].sum(axis=1) - nuevo[grupo]).abs()
        if (dif > 1).any():
            errores.append(f"{grupo}: las actividades no suman el total (diferencia máxima {dif.max():.1f} MW).")
    if not nuevo["total"].between(500, 6000).all():
        errores.append("Total fuera de rango (500 a 6.000 MW).")
    if anterior is not None and len(anterior) and nuevo["fecha"].max() < anterior["fecha"].max():
        errores.append("El último día es anterior al de la versión guardada.")
    return errores
