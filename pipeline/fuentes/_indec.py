"""Lectura y validación comunes para los cuadros mensuales de INDEC.

Los cuadros de INDEC comparten una forma general:
  - un título arriba y, debajo, una o varias filas de encabezados;
  - después, una fila por mes. El período viene de una de estas maneras:
      año solo en enero en una columna y el mes en la siguiente (EMAE, ISAC, IPI),
      o una fecha completa en la primera columna (supermercados);
  - notas al pie al final.

`tabla_mensual` resuelve todo eso y devuelve, para cada columna, su "camino" de encabezados
(p. ej. "SERIE ORIGINAL | VARIACION PORCENTUAL | RESPECTO AL MISMO MES DEL AÑO ANTERIOR").
Cada fuente describe sus series con `Columna`: `prefijo` es el comienzo de ese camino.
"""

import io
import re
import unicodedata
from dataclasses import dataclass

import numpy as np
import pandas as pd

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


@dataclass(frozen=True)
class Columna:
    """Una serie del cuadro.

    prefijo: comienzo del camino de encabezados de la columna (sin tildes ni mayúsculas;
        los niveles de encabezado se separan con " | ").
    nombre: nombre para mostrar.
    despues_de: si varias columnas empiezan igual (p. ej. "Var % respecto al mes anterior"),
        se toma la primera que está a la derecha de esta otra columna.
    tipo: "nivel" (índice o valor, nunca vacío) o "variacion" (en %, puede faltar al principio).
    base / rezago: para una variación, la columna de nivel y los meses de rezago con que se
        recalcula y se controla contra el valor publicado. Sin base, no se recalcula.
    hoja: hoja del archivo, si la fuente lee de varias.
    """
    prefijo: str
    nombre: str
    despues_de: str | None = None
    tipo: str = "nivel"
    base: str | None = None
    rezago: int | None = None
    unidad: str | None = None  # si falta: la de la fuente para niveles, "%" para variaciones
    hoja: str | None = None


def norm(texto) -> str:
    """Mayúsculas, sin tildes ni espacios repetidos."""
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return ""
    s = unicodedata.normalize("NFKD", str(texto))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.upper().split())


def slug(texto: str) -> str:
    s = norm(texto).lower()
    s = re.sub(r"\(\d+\)", "", s)  # llamadas a notas: "Resto (1)"
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def leer_excel(contenido: bytes) -> dict[str, pd.DataFrame]:
    motor = "xlrd" if contenido[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" else None
    return pd.read_excel(io.BytesIO(contenido), sheet_name=None, header=None, engine=motor)


def _periodo(fila: list, anio: int | None) -> tuple[pd.Timestamp | None, int | None]:
    """Fecha de la fila (o None) y el año vigente, mirando las primeras columnas."""
    for j, v in enumerate(fila[:4]):
        if isinstance(v, (pd.Timestamp, np.datetime64)) or hasattr(v, "year") and hasattr(v, "month"):
            t = pd.Timestamp(v)
            return pd.Timestamp(t.year, t.month, 1), t.year
        mes = MESES.get(norm(v).lower().rstrip("*").strip())
        if mes:
            # El año, si figura, está en alguna columna anterior a la del mes.
            for a in reversed(fila[:j]):
                m = re.fullmatch(r"((?:19|20)\d\d)\*?", str(a).strip().split(".")[0]) if pd.notna(a) else None
                if m:
                    anio = int(m.group(1))
                    break
            return (pd.Timestamp(anio, mes, 1) if anio else None), anio
    return None, anio


def tabla_mensual(tabla: pd.DataFrame) -> tuple[pd.DataFrame, dict[int, str], dict[int, list[str]]]:
    """Devuelve (datos, encabezados, originales).

    datos: una fila por mes, con 'fecha' y una columna por cada columna de la hoja (por posición).
    encabezados: posición -> camino de encabezados normalizado ("A | B | C").
    originales: posición -> los mismos textos tal como figuran en el archivo (para mostrar).
    """
    filas = tabla.values.tolist()
    anio, registros, primera = None, [], None
    for i, fila in enumerate(filas):
        fecha, anio = _periodo(fila, anio)
        if fecha is None:
            continue
        if primera is None:
            primera = i
        registros.append([fecha] + [pd.to_numeric(v, errors="coerce") for v in fila])
    if not registros:
        raise ValueError("No encontré filas con períodos (meses o fechas).")

    # Encabezados: filas no vacías entre el título (primera fila con texto) y el primer dato.
    con_texto = [i for i in range(primera) if any(norm(v) for v in filas[i])]
    filas_enc = con_texto[1:] if len(con_texto) > 1 else con_texto
    ancho = tabla.shape[1]
    caminos = {j: [] for j in range(ancho)}
    originales = {j: [] for j in range(ancho)}
    for k, i in enumerate(filas_enc):
        crudos = [" ".join(str(v).split()) if norm(v) else "" for v in filas[i]]
        if k == 0 and len(filas_enc) > 1:
            # La primera fila suele agrupar varias columnas en una celda combinada:
            # se extiende hacia la derecha hasta el próximo texto.
            actual = ""
            for j in range(ancho):
                actual = crudos[j] or actual
                crudos[j] = actual
        for j in range(ancho):
            if crudos[j]:
                caminos[j].append(norm(re.sub(r"\(\d+\)", "", crudos[j])))  # sin llamadas a notas
                originales[j].append(crudos[j])
    encabezados = {j: " | ".join(c) for j, c in caminos.items()}

    datos = pd.DataFrame(registros, columns=["fecha"] + list(range(ancho)))
    datos = datos.drop_duplicates("fecha", keep="first").reset_index(drop=True)
    return datos, encabezados, originales


def ubicar(encabezados: dict[int, str], columnas: dict[str, Columna]) -> dict[str, int]:
    """Posición de cada serie según el prefijo de su camino de encabezados."""
    posicion: dict[str, int] = {}
    for cid, col in columnas.items():
        desde = posicion[col.despues_de] if col.despues_de else -1
        p = norm(col.prefijo)
        candidatas = [j for j, t in encabezados.items() if t.startswith(p) and j > desde]
        if col.despues_de:
            candidatas = candidatas[:1]
        if len(candidatas) != 1:
            raise ValueError(f"Encabezado de {cid} ('{col.prefijo}'): {len(candidatas)} coincidencias, esperaba 1.")
        posicion[cid] = candidatas[0]
    return posicion


def buscar_hoja(libro: dict[str, pd.DataFrame], nombre: str) -> pd.DataFrame:
    """La hoja con ese nombre; tolera diferencias de mayúsculas, espacios y puntos finales."""
    if nombre in libro:
        return libro[nombre]
    clave = norm(nombre).rstrip(". ")
    for h, df in libro.items():
        if norm(h).rstrip(". ") == clave:
            return df
    raise ValueError(f"No encontré la hoja '{nombre}' (hay: {list(libro)}).")


def leer_tabla_mensual(contenido: bytes, hoja: str | None, columnas: dict[str, Columna]) -> pd.DataFrame:
    """Lee una o varias hojas y devuelve 'fecha' y una columna por serie, en el orden de `columnas`."""
    libro = leer_excel(contenido)
    por_hoja: dict[str, dict[str, Columna]] = {}
    for cid, col in columnas.items():
        por_hoja.setdefault(col.hoja or hoja, {})[cid] = col
    partes = []
    for nombre_hoja, cols in por_hoja.items():
        datos, encabezados, _ = tabla_mensual(buscar_hoja(libro, nombre_hoja))
        posicion = ubicar(encabezados, cols)
        parte = datos[["fecha"] + list(posicion.values())]
        parte.columns = ["fecha"] + list(posicion)
        parte = parte.dropna(how="all", subset=list(posicion))
        partes.append(parte)
    df = partes[0]
    for p in partes[1:]:
        df = df.merge(p, on="fecha", how="outer")
    return df.sort_values("fecha").reset_index(drop=True)[["fecha"] + list(columnas)]


def columnas_por_encabezado(contenido: bytes, hoja: str, desde_col: int = 1, prefijo_id: str = "",
                            sufijo_nombre: str = "", excluir: tuple[str, ...] = (),
                            nivel_id: int | None = None) -> dict[str, Columna]:
    """Una Columna por cada columna con datos de una hoja ancha (p. ej. divisiones o insumos).

    El id se arma con el camino de encabezados (o solo el nivel `nivel_id` + código si se indica).
    Sirve para cuadros con decenas de series; la validación compara contra la versión guardada,
    así que si INDEC agrega, quita o renombra una columna, la actualización frena.
    """
    datos, encabezados, originales = tabla_mensual(buscar_hoja(leer_excel(contenido), hoja))
    columnas = {}
    for j, camino in encabezados.items():
        if j < desde_col or not camino or datos[j].notna().sum() < 12:
            continue
        if any(norm(e) in camino for e in excluir):
            continue
        partes = camino.split(" | ")
        cid = prefijo_id + slug("_".join(partes) if nivel_id is None else partes[nivel_id])
        if cid in columnas:
            raise ValueError(f"Columna repetida en {hoja}: {cid}")
        nombre = " - ".join(re.sub(r"\s*\(\d+\)$", "", t) for t in originales[j] if norm(t) not in ("%", "NUMEROS INDICE"))
        columnas[cid] = Columna(camino, f"{nombre}{sufijo_nombre}", hoja=hoja)
    return columnas


def iguales(a: pd.Series, b: pd.Series, tol: float = 1e-6) -> np.ndarray:
    return np.isclose(a.to_numpy(float), b.to_numpy(float), atol=tol, rtol=0, equal_nan=True)


def validar_tabla(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas: dict[str, Columna],
                  primer_periodo: str, sin_control_interanual: set[str] = frozenset(),
                  rango_nivel=(0, 2000), max_variacion=100, tol_variacion=0.05,
                  vacios_permitidos: set[str] = frozenset()) -> list[str]:
    """Devuelve una lista de errores (vacía si todo está bien). Los avisos van por print.

    vacios_permitidos: series de nivel que pueden tener meses sin dato (p. ej. subclases que
    INDEC deja en blanco por confidencialidad).
    """
    errores = []
    ids = list(columnas)
    niveles = [c for c in ids if columnas[c].tipo == "nivel"]
    variaciones = [c for c in ids if columnas[c].tipo == "variacion"]

    if list(nuevo.columns) != ["fecha"] + ids:
        return [f"Columnas inesperadas: {list(nuevo.columns)[:10]}…"]

    esperado = pd.date_range(primer_periodo, periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append(f"Las fechas no son meses consecutivos desde {primer_periodo}.")

    # Niveles: sin vacíos y en rango.
    huecos = nuevo[[c for c in niveles if c not in vacios_permitidos]].isna().sum()
    if huecos.any():
        errores.append(f"Valores vacíos: {huecos[huecos > 0].head(5).to_dict()}")
    lo, hi = rango_nivel
    fuera = ((nuevo[niveles] <= lo) | (nuevo[niveles] > hi)).sum()
    if fuera.any():
        errores.append(f"Valores fuera de rango ({lo}, {hi}]: {fuera[fuera > 0].head(5).to_dict()}")

    # Variaciones: solo pueden faltar al principio, en rango, y deben coincidir con el recálculo.
    for c in variaciones:
        col = columnas[c]
        serie = nuevo[c]
        if serie.iloc[col.rezago or 0:].isna().any():
            errores.append(f"{c}: valores vacíos después de los primeros {col.rezago} meses.")
        if (serie.abs() > max_variacion).any():
            errores.append(f"{c}: variaciones mayores a {max_variacion}%.")
        if col.base:
            recalculo = (nuevo[col.base] / nuevo[col.base].shift(col.rezago) - 1) * 100
            dif = (serie - recalculo).abs().iloc[col.rezago:]
            if (dif > tol_variacion).any():
                errores.append(f"{c}: no coincide con la variación recalculada desde {col.base} "
                               f"(diferencia máxima {dif.max():.3f} p.p.). ¿Columnas cruzadas?")

    if anterior is not None and len(anterior):
        faltan = [c for c in anterior.columns if c not in nuevo.columns]
        if faltan:
            errores.append(f"Desaparecieron columnas que estaban en la versión guardada: {faltan[:5]}")
        if nuevo["fecha"].max() < anterior["fecha"].max():
            errores.append("El último período es anterior al de la versión guardada.")
        if len(nuevo) < len(anterior):
            errores.append(f"Tiene menos meses ({len(nuevo)}) que la versión guardada ({len(anterior)}).")

        comunes = nuevo.merge(anterior, on="fecha", suffixes=("", "_ant"))
        for c in niveles:
            if f"{c}_ant" not in comunes:
                continue
            dif = (comunes[c] / comunes[f"{c}_ant"] - 1).abs()
            if (dif > 0.25).any():
                errores.append(f"{c}: valores históricos cambiaron más de 25% respecto de la versión guardada.")
            elif (dif > 0.0005).any():
                print(f"Aviso: {c} tiene {(dif > 0.0005).sum()} meses revisados respecto de la versión guardada.")

        nuevos = nuevo[nuevo["fecha"] > anterior["fecha"].max()]
        indexado = nuevo.set_index("fecha")
        for _, fila in nuevos.iterrows():
            hace_un_anio = fila["fecha"] - pd.DateOffset(years=1)
            if hace_un_anio not in indexado.index:
                continue
            for c in niveles:
                if c in sin_control_interanual:
                    continue
                ratio = fila[c] / indexado.loc[hace_un_anio, c]
                if not 0.2 <= ratio <= 5:
                    errores.append(f"{c} {fila['fecha']:%Y-%m}: variación interanual sospechosa (x{ratio:.2f}).")
    return errores
