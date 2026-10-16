"""Lectura y validación comunes para los cuadros mensuales de INDEC.

Casi todos los cuadros de INDEC tienen la misma forma: una fila de encabezados con
un texto por serie y, debajo, una fila por mes con el año solo en enero (columna 0)
y el nombre del mes en la columna 1. Cada fuente describe sus columnas con
`Columna` y usa `leer_tabla_mensual` y `validar_tabla`.
"""

import io
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

    prefijo: comienzo del encabezado en el archivo (se compara sin tildes ni mayúsculas).
    nombre: nombre para mostrar.
    despues_de: si varios encabezados empiezan igual (p. ej. "Var % respecto al mes anterior"),
        se toma el primero que está a la derecha de esta otra columna.
    tipo: "nivel" (índice o valor, nunca vacío) o "variacion" (en %, puede faltar al principio).
    base / rezago: para una variación, la columna de nivel y los meses de rezago con que
        se recalcula y se controla contra el valor publicado.
    """
    prefijo: str
    nombre: str
    despues_de: str | None = None
    tipo: str = "nivel"
    base: str | None = None
    rezago: int | None = None


def norm(texto) -> str:
    """Mayúsculas, sin tildes ni espacios repetidos."""
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return ""
    s = unicodedata.normalize("NFKD", str(texto))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.upper().split())


def leer_tabla_mensual(contenido: bytes, hoja: str, columnas: dict[str, Columna]) -> pd.DataFrame:
    """Devuelve un DataFrame con 'fecha' (primer día del mes) y una columna por serie."""
    motor = "xlrd" if contenido[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" else None
    tabla = pd.read_excel(io.BytesIO(contenido), sheet_name=hoja, header=None, engine=motor)

    # 1. Fila de encabezados: la primera donde aparece el prefijo de la primera columna.
    primera = norm(next(iter(columnas.values())).prefijo)
    fila_enc = next((i for i in range(min(len(tabla), 30))
                     if any(norm(v).startswith(primera) for v in tabla.iloc[i].tolist())), None)
    if fila_enc is None:
        raise ValueError(f"No encontré la fila de encabezados (ningún texto empieza con '{primera}').")

    # 2. Columna de cada serie.
    encabezados = {j: norm(v) for j, v in enumerate(tabla.iloc[fila_enc].tolist())}
    posicion: dict[str, int] = {}
    for cid, col in columnas.items():
        desde = posicion[col.despues_de] if col.despues_de else -1
        candidatas = [j for j, t in encabezados.items() if t.startswith(norm(col.prefijo)) and j > desde]
        if col.despues_de:
            candidatas = candidatas[:1]
        if len(candidatas) != 1:
            raise ValueError(f"Encabezado de {cid} ('{col.prefijo}'): {len(candidatas)} coincidencias, esperaba 1.")
        posicion[cid] = candidatas[0]

    # 3. Filas de datos.
    registros, anio = [], None
    for i in range(fila_enc + 1, len(tabla)):
        fila = tabla.iloc[i]
        a, m = fila.iloc[0], fila.iloc[1]
        if pd.notna(a):
            try:
                anio = int(float(str(a).strip().rstrip("*")))
            except ValueError:
                pass  # notas al pie como "Fuente: INDEC."
        mes = MESES.get(norm(m).lower().rstrip("*").strip())
        if mes is None or anio is None:
            continue
        valores = {cid: pd.to_numeric(fila.iloc[j], errors="coerce") for cid, j in posicion.items()}
        if all(pd.isna(v) for v in valores.values()):
            continue
        registros.append({"fecha": pd.Timestamp(anio, mes, 1), **valores})
    if not registros:
        raise ValueError("No encontré filas de datos debajo de los encabezados.")
    return pd.DataFrame(registros)


def iguales(a: pd.Series, b: pd.Series, tol: float = 1e-6) -> np.ndarray:
    return np.isclose(a.to_numpy(float), b.to_numpy(float), atol=tol, rtol=0, equal_nan=True)


def validar_tabla(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas: dict[str, Columna],
                  primer_periodo: str, sin_control_interanual: set[str] = frozenset(),
                  rango_nivel=(0, 2000), max_variacion=100) -> list[str]:
    """Devuelve una lista de errores (vacía si todo está bien). Los avisos van por print."""
    errores = []
    ids = list(columnas)
    niveles = [c for c in ids if columnas[c].tipo == "nivel"]
    variaciones = [c for c in ids if columnas[c].tipo == "variacion"]

    if list(nuevo.columns) != ["fecha"] + ids:
        return [f"Columnas inesperadas: {list(nuevo.columns)}"]

    esperado = pd.date_range(primer_periodo, periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append(f"Las fechas no son meses consecutivos desde {primer_periodo}.")

    # Niveles: sin vacíos y en rango.
    huecos = nuevo[niveles].isna().sum()
    if huecos.any():
        errores.append(f"Valores vacíos: {huecos[huecos > 0].to_dict()}")
    lo, hi = rango_nivel
    fuera = ((nuevo[niveles] <= lo) | (nuevo[niveles] > hi)).sum()
    if fuera.any():
        errores.append(f"Valores fuera de rango ({lo}, {hi}]: {fuera[fuera > 0].to_dict()}")

    # Variaciones: solo pueden faltar al principio, en rango, y deben coincidir con el recálculo.
    for c in variaciones:
        col = columnas[c]
        serie = nuevo[c]
        if serie.iloc[col.rezago:].isna().any():
            errores.append(f"{c}: valores vacíos después de los primeros {col.rezago} meses.")
        if (serie.abs() > max_variacion).any():
            errores.append(f"{c}: variaciones mayores a {max_variacion}%.")
        if col.base:
            recalculo = (nuevo[col.base] / nuevo[col.base].shift(col.rezago) - 1) * 100
            dif = (serie - recalculo).abs().iloc[col.rezago:]
            if (dif > 0.05).any():
                errores.append(f"{c}: no coincide con la variación recalculada desde {col.base} "
                               f"(diferencia máxima {dif.max():.3f} p.p.). ¿Columnas cruzadas?")

    if anterior is not None and len(anterior):
        if nuevo["fecha"].max() < anterior["fecha"].max():
            errores.append("El último período es anterior al de la versión guardada.")
        if len(nuevo) < len(anterior):
            errores.append(f"Tiene menos meses ({len(nuevo)}) que la versión guardada ({len(anterior)}).")

        comunes = nuevo.merge(anterior, on="fecha", suffixes=("", "_ant"))
        for c in niveles:
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
