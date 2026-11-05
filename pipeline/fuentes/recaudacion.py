"""Recaudación tributaria nacional (ARCA): total, DGI, DGA y seguridad social desde 1997, y los principales impuestos
desde 2017. Millones de pesos corrientes.

Fuentes:
  - Total y subtotales (1997 en adelante): Ministerio de Economía, serie 172.3 del portal datos.gob.ar
    (recaudacion-tributaria-datos-mensuales.csv), que se arma con los datos de ARCA.
  - Detalle por impuesto: ARCA, "Recaudación por impuesto, recursos de la seguridad social y aduanas", un archivo por
    año (serie<año>.xls). Se bajan los años desde 2017.

IVA DGI son los pagos directos y retenciones impositivos del IVA bruto (la parte que pagan los contribuyentes por su
actividad interna); IVA DGA, el que se cobra en la aduana sobre las importaciones.
"""

import io
import re
import zipfile
from datetime import date

import pandas as pd

from pipeline.fuentes._indec import Columna, norm

ID = "recaudacion"
NOMBRE = "Recaudación tributaria nacional: total y principales impuestos (ARCA)"
URL_CSV = "https://infra.datos.gob.ar/catalog/sspm/dataset/172/distribution/172.3/download/recaudacion-tributaria-datos-mensuales.csv"
URL_ANIO = "https://contenidos.afip.gob.ar/institucional/estudios/archivos/serie{}.xls"
URL = URL_CSV
PAGINA = "https://www.arca.gob.ar/institucional/estudios/recaudacion/series.asp"
EXTENSION = "zip"
FRECUENCIA = "M"
ORGANISMO = "ARCA y Ministerio de Economía"
UNIDAD = "Millones de $"
PRIMER_PERIODO = "1997-01-01"
PRIMER_ANIO_DETALLE = 2017
CALENDARIO = ""
GUARDAR_ORIGINAL = False

TOTALES = {"total": ("total_recaudacion", "Recaudación tributaria total"),
           "dgi": ("subtotal_dgi", "Recaudación DGI (impuestos internos)"),
           "dga": ("subtotal_dga", "Recaudación DGA (aduana)"),
           "seguridad_social": ("seguridad_social", "Recaudación de la seguridad social")}
# id -> (rótulo de la fila en el archivo de ARCA, rótulo después del cual buscar, nombre)
IMPUESTOS = {
    "iva_bruto": ("IVA BRUTO", None, "IVA bruto"),
    "iva_dgi": ("PAGOS DIRECTOS Y RETENCIONES", "IVA BRUTO", "IVA DGI (pagos directos y retenciones impositivos)"),
    "iva_dga": ("PAGOS DIRECTOS Y RETENCIONES", "IVA BRUTO", "IVA DGA (aduanero)"),
    "iva_neto": ("IVA NETO", None, "IVA neto de devoluciones"),
    "ganancias": ("GANANCIAS", None, "Impuesto a las ganancias"),
    "debitos_creditos": ("CUENTAS CORRIENTES", None, "Impuesto a los débitos y créditos bancarios"),
    "combustibles": ("COMBUSTIBLES", None, "Impuestos sobre los combustibles"),
    "internos": ("INTERNOS", None, "Impuestos internos"),
    "bienes_personales": ("BIENES PERSONALES", None, "Bienes personales"),
    "derechos_exportacion": ("DERECHOS A LA EXPORTACION", None, "Derechos de exportación"),
    "derechos_importacion": ("DERECHOS A LA IMPORTACION", None, "Derechos de importación"),
}
COLUMNAS = {k: Columna("", n) for k, (_, n) in TOTALES.items()}
COLUMNAS |= {k: Columna("", n) for k, (_, _, n) in IMPUESTOS.items()}
COLUMNAS["total_var_ia"] = Columna("", "Recaudación tributaria total, var. % interanual (nominal)", unidad="%",
                                   tipo="variacion", base="total", rezago=12)


def bajar(descargar, hoy: date) -> tuple[str, bytes]:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("totales.csv", descargar(URL_CSV, minimo=10_000))
        for anio in range(PRIMER_ANIO_DETALLE, hoy.year + 1):
            try:
                z.writestr(f"serie{anio}.xls", descargar(URL_ANIO.format(anio), minimo=20_000))
            except Exception:  # noqa: BLE001 - en enero el archivo del año todavía no existe
                if anio < hoy.year - (1 if hoy.month == 1 else 0):
                    raise
    return f"{URL_CSV} {URL_ANIO.format('<año>')}", buf.getvalue()


def _anio(contenido: bytes, anio: int) -> pd.DataFrame:
    hoja = pd.read_excel(io.BytesIO(contenido), sheet_name=0, header=None)
    rotulos = [norm(v) if pd.notna(v) else "" for v in hoja.iloc[:, 1]]
    enc = next(i for i, r in enumerate(rotulos) if r.startswith("CONCEPTO"))
    if f"{anio}" not in " ".join(str(v) for v in hoja.iloc[:enc, 1].tolist()):
        raise ValueError(f"serie{anio}.xls no dice el año {anio} en el encabezado.")
    cabecera = norm(" ".join(str(v) for v in hoja.iloc[:enc, 1].tolist()))
    escala = 1e-3 if "MILES DE PESOS" in cabecera else 1.0 if "MILLONES DE PESOS" in cabecera else None
    if escala is None:
        raise ValueError(f"serie{anio}.xls: no encontré la unidad (miles o millones de pesos).")
    meses = [j for j in range(2, hoja.shape[1]) if norm(hoja.iloc[enc, j]) not in ("", "TOTAL", "NAN")][:12]
    out = {}
    for k, (rot, despues, _) in IMPUESTOS.items():
        desde = next(i for i, r in enumerate(rotulos) if r.startswith(despues)) + 1 if despues else enc + 1
        filas = [i for i in range(desde, len(rotulos)) if re.sub(r"\s*\d/$", "", rotulos[i]).startswith(rot)]
        n = 2 if k == "iva_dga" else 1
        if len(filas) < n:
            raise ValueError(f"serie{anio}.xls: no encontré la fila '{rot}'.")
        out[k] = (pd.to_numeric(hoja.iloc[filas[n - 1], meses], errors="coerce") * escala).tolist()
    df = pd.DataFrame(out)
    df.insert(0, "fecha", pd.date_range(f"{anio}-01-01", periods=len(meses), freq="MS"))
    return df.dropna(subset=["iva_bruto"])


def leer(contenido: bytes, columnas=COLUMNAS) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        t = pd.read_csv(z.open("totales.csv"), parse_dates=["indice_tiempo"])
        detalle = [_anio(z.read(n), int(n[5:9])) for n in sorted(z.namelist()) if n.startswith("serie")]
    df = t.rename(columns={"indice_tiempo": "fecha", **{v[0]: k for k, v in TOTALES.items()}})[["fecha", *TOTALES]]
    df = df.merge(pd.concat(detalle), on="fecha", how="left")
    # Control cruzado: el total de ARCA y el de Economía deberían coincidir (lo valida validar()).
    df = df[df["fecha"] >= PRIMER_PERIODO].sort_values("fecha").reset_index(drop=True)
    df["total_var_ia"] = (df["total"] / df["total"].shift(12) - 1) * 100
    return df[["fecha", *columnas]]


def validar(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas=COLUMNAS) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]
    esperado = pd.date_range(PRIMER_PERIODO, periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los meses no son consecutivos.")
    d = nuevo.dropna(subset=["total", "dgi", "dga", "seguridad_social"])
    if ((d["dgi"] + d["dga"] + d["seguridad_social"]) / d["total"] - 1).abs().max() > 0.01:
        errores.append("DGI + DGA + seguridad social no suman el total.")
    det = nuevo[nuevo["fecha"] >= f"{PRIMER_ANIO_DETALLE}-01-01"]
    if det[list(IMPUESTOS)].iloc[:-1].isna().any().any():
        errores.append("Faltan impuestos en algún mes desde 2017.")
    ultimo_detalle = det.dropna(subset=["iva_bruto"])
    if len(ultimo_detalle):
        u = ultimo_detalle.iloc[-1]
        if abs((u["iva_dgi"] + u["iva_dga"]) / u["iva_bruto"] - 1) > 0.02:
            errores.append("IVA DGI + DGA no da el IVA bruto (¿filas cruzadas?).")
    if anterior is not None and len(anterior):
        for c in columnas:
            if c in anterior and nuevo[c].count() < anterior[c].count():
                errores.append(f"{c}: se perdió historia.")
    return errores
