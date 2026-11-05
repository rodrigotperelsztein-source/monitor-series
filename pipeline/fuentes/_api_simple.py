"""Piezas comunes de las fuentes que leen una sola tabla de la API del INDEC."""

import pandas as pd

from pipeline.fuentes import _api_indec as api


def bajar(tabla: str) -> tuple[str, bytes]:
    if not api.disponible(tabla):
        raise ValueError(f"No está la tabla {tabla} de la API del INDEC (¿token vencido o API caída?).")
    return api.contenido(tabla)


def validar_basico(nuevo: pd.DataFrame, anterior: pd.DataFrame | None, columnas, freq: str, max_atraso_dias: int) -> list[str]:
    errores = []
    if list(nuevo.columns) != ["fecha", *columnas]:
        return [f"Columnas inesperadas: {list(nuevo.columns)[:8]}"]
    esperado = pd.date_range(nuevo["fecha"].min(), periods=len(nuevo), freq=freq)
    if not nuevo["fecha"].reset_index(drop=True).equals(pd.Series(esperado, name="fecha")):
        errores.append("Los períodos no son consecutivos.")
    if (pd.Timestamp.today() - nuevo["fecha"].max()).days > max_atraso_dias:
        errores.append("El último dato está demasiado atrasado.")
    if anterior is not None and len(anterior):
        for c in columnas:
            if c in anterior and nuevo[c].count() < anterior[c].count():
                errores.append(f"{c}: se perdió historia.")
    return errores
