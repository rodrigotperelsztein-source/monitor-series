"""Nombres de archivo que llevan la fecha de publicación (el INDEC cambia el nombre en cada difusión)."""

from datetime import date

ROMANOS = {1: "I", 2: "II", 3: "III", 4: "IV"}


def meses_atras(hoy: date, n: int = 14) -> list[tuple[int, int]]:
    """(mes, año) desde el mes actual hacia atrás."""
    m, a, out = hoy.month, hoy.year, []
    for _ in range(n):
        out.append((m, a))
        m, a = (12, a - 1) if m == 1 else (m - 1, a)
    return out


def urls_mm_aa(plantilla: str, hoy: date, n: int = 14) -> list[str]:
    """plantilla con {mm} y {aa}: sh_capacidad_{mm}_{aa}.xls -> sh_capacidad_10_26.xls, sh_capacidad_09_26.xls..."""
    return [plantilla.format(mm=f"{m:02d}", aa=f"{a % 100:02d}") for m, a in meses_atras(hoy, n)]


def urls_trimestre(plantilla: str, hoy: date, n: int = 6) -> list[str]:
    """plantilla con {t} (romano) y {anio}: cin_{t}_{anio}.xls, del trimestre actual hacia atrás."""
    q, a, out = (hoy.month - 1) // 3 + 1, hoy.year, []
    for _ in range(n):
        out.append(plantilla.format(t=ROMANOS[q], anio=a))
        q, a = (4, a - 1) if q == 1 else (q - 1, a)
    return out
