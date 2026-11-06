"""Series del portal datos.gob.ar (Ministerio de Economía, catálogo sspm): CSV con indice_tiempo y una columna por serie."""

import io

import pandas as pd


def leer(contenido: bytes, mapa: dict[str, str], desde: str) -> pd.DataFrame:
    t = pd.read_csv(io.BytesIO(contenido), parse_dates=["indice_tiempo"])
    faltan = set(mapa.values()) - set(t.columns)
    if faltan:
        raise ValueError(f"Faltan columnas en el CSV: {sorted(faltan)}")
    df = pd.DataFrame({"fecha": t["indice_tiempo"], **{k: pd.to_numeric(t[c], errors="coerce") for k, c in mapa.items()}})
    df = df[df["fecha"] >= desde].sort_values("fecha")
    df = df.dropna(how="all", subset=list(mapa)).reset_index(drop=True)
    return df


def validar(nuevo: pd.DataFrame, anterior, columnas, desde: str, max_atraso_dias: int = 120, obligatorias=()) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)[:8]}"]
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq="MS")
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los meses no son consecutivos.")
    for c in obligatorias:
        u = nuevo[c].last_valid_index()
        if u is None or (pd.Timestamp.today() - nuevo.loc[u, "fecha"]).days > max_atraso_dias:
            errores.append(f"{c}: el último dato está demasiado atrasado.")
    if anterior is not None and len(anterior):
        for c in columnas:
            if c in anterior and nuevo[c].count() < anterior[c].count():
                errores.append(f"{c}: se perdió historia.")
    return errores
