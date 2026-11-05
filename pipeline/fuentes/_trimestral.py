"""Lectura de cuadros trimestrales "anchos" del INDEC: los trimestres van en columnas y los conceptos en filas.

Formatos que se reconocen en los encabezados de columna:
  - una fila con años (2004, 2005, "2026 (2)") y otra con "1º trimestre"... "4º trimestre";
  - una sola fila con "2006T1", "2026T2*".
Las columnas de totales anuales ("TOTAL", "Año") se ignoran.
"""

import re

import pandas as pd

from pipeline.fuentes._indec import norm


def _encabezado(df: pd.DataFrame) -> tuple[int, dict[int, pd.Period]]:
    """(fila del encabezado de trimestres, posición -> trimestre)."""
    for i in range(min(15, len(df))):
        fila = df.iloc[i].tolist()
        # Formato "2006T1"
        cols = {}
        for j, v in enumerate(fila):
            m = re.fullmatch(r"((?:19|20)\d\d)\s*T\s*([1-4])\*?", str(v).strip()) if pd.notna(v) else None
            if m:
                cols[j] = pd.Period(f"{m[1]}Q{m[2]}", "Q")
        if len(cols) >= 8:
            return i, cols
        # Formato años + "1º trimestre"
        trims = {j: int(m[1]) for j, v in enumerate(fila) if pd.notna(v)
                 and (m := re.match(r"([1-4])\s*[ºoO°]?\s*TRIM", norm(v)))}
        if len(trims) >= 8 and i > 0:
            anios, actual = {}, None
            for j, v in enumerate(df.iloc[i - 1].tolist()):
                m = re.match(r"((?:19|20)\d\d)", str(v).strip()) if pd.notna(v) else None
                if m:
                    actual = int(m[1])
                anios[j] = actual
            cols = {j: pd.Period(f"{anios[j]}Q{q}", "Q") for j, q in trims.items() if anios.get(j)}
            return i, cols
    raise ValueError("No encontré el encabezado de trimestres.")


def filas(df: pd.DataFrame, columnas_texto: int = 2) -> list[tuple[str, pd.Series]]:
    """Lista de (rótulo normalizado, serie trimestral) en el orden de la hoja.

    El rótulo une el texto de las primeras columnas (p. ej. el código y la descripción).
    """
    i0, cols = _encabezado(df)
    out = []
    for i in range(i0 + 1, len(df)):
        fila = df.iloc[i]
        rotulo = " ".join(norm(v) for v in fila.iloc[:columnas_texto].tolist() if pd.notna(v) and not isinstance(v, (int, float)))
        if not rotulo:
            continue
        valores = pd.to_numeric(pd.Series({p: fila.iloc[j] for j, p in cols.items()}), errors="coerce")
        if valores.notna().sum() == 0:
            continue
        out.append((re.sub(r"\(\d+\)", "", rotulo).strip(), valores.sort_index()))
    return out


def buscar(lista: list[tuple[str, pd.Series]], prefijo: str, ocurrencia: int = 1, despues_de: str | None = None) -> pd.Series:
    """La serie cuyo rótulo empieza con `prefijo` (la n-ésima, o la primera después de otro rótulo)."""
    p = norm(prefijo)
    inicio = 0
    if despues_de:
        d = norm(despues_de)
        inicio = next((k for k, (r, _) in enumerate(lista) if r.startswith(d)), None)
        if inicio is None:
            raise ValueError(f"No encontré el rótulo '{despues_de}'.")
        inicio += 1
    hallados = [s for r, s in lista[inicio:] if r.startswith(p)]
    if len(hallados) < ocurrencia:
        raise ValueError(f"No encontré el rótulo '{prefijo}'" + (f" después de '{despues_de}'" if despues_de else ""))
    return hallados[ocurrencia - 1]
