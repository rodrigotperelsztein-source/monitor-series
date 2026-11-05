"""Piezas comunes de las fuentes trimestrales que se leen con _trimestral."""

import pandas as pd


def a_tabla(series: dict[str, pd.Series], primer: str) -> pd.DataFrame:
    df = pd.DataFrame(series)
    df = df[df.index >= pd.Period(primer, "Q")].dropna(how="all")
    df.index = df.index.to_timestamp()
    df.index.name = "fecha"
    return df.reset_index()


def var_ia(s: pd.Series) -> pd.Series:
    return (s / s.shift(4) - 1) * 100


def validar_trimestral(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas, primer: str,
                       pueden_faltar: set[str] = frozenset()) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)[:8]}…"]
    esperado = pd.date_range(primer, periods=len(nuevo), freq="QS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append(f"Los trimestres no son consecutivos desde {primer}.")
    if (pd.Timestamp.today() - nuevo["fecha"].max()).days > 400:
        errores.append("El último trimestre tiene más de un año.")
    faltan = [c for c in columnas if c not in pueden_faltar and nuevo[c].iloc[4:].isna().any()]
    if faltan:
        errores.append(f"Valores vacíos en {faltan[:5]}")
    if anterior is not None and len(anterior):
        for c in columnas:
            if c in anterior and nuevo[c].count() < anterior[c].count():
                errores.append(f"{c}: se perdió historia.")
    return errores
