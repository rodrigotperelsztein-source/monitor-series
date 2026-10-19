"""Desestacionalización propia con X-13ARIMA-SEATS (Oficina del Censo de EE.UU.) y calendario argentino.

El programa está en bin/x13as (versión 1.1, compilación 57, Linux de 64 bits, tomado de
github.com/x13org/x13prebuilt). Para cada serie se arma una especificación (.spc) y se corre.

Método (calibrado contra las series desestacionalizadas que publica Monitor Argy):
  - modelo regARIMA con la especificación fija de cada serie (orden ARIMA, transformación, outliers);
  - días de la semana: regresores estándar de X-13 (td); se quitan de la serie;
  - feriados: regresor propio, la cantidad de feriados nacionales que caen de lunes a viernes en el
    mes, centrada por mes calendario. Incluye traslados; excluye Jueves Santo (día no laborable),
    los feriados puente "con fines turísticos" y los feriados únicos (censos, bicentenarios, etc.);
  - Pascua: regresor estándar easter[8];
  - el efecto de feriados y de Pascua se estima en el modelo pero queda en la serie
    desestacionalizada (como hace Monitor Argy: "enLaSerie");
  - descomposición X-11; la serie desestacionalizada es la tabla D11.
"""

import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
X13 = RAIZ / "bin" / "x13as"
PROGRAMA = "X-13ARIMA-SEATS 1.1, compilación 57 (Oficina del Censo de EE.UU.)"

# Días que no se cuentan como feriado (se compara con el nombre que da la biblioteca holidays).
NO_FERIADOS = ("Jueves Santo", "turísticos", "Censo", "Bicentenario", "Copa Mundial", "Papa")


@dataclass
class Especificacion:
    """Cómo se desestacionaliza una serie.

    modelo: orden ARIMA "(p d q)(P D Q)"; None para que X-13 lo elija (automdl).
    transformacion: "log" o "niveles"; "auto" para que X-13 elija.
    outliers: lista fija de (tipo, "AAAA-MM"), p. ej. ("LS", "2020-03"). None: se detectan.
    dias_semana / feriados / pascua: regresores de calendario incluidos.
    efectos_en_serie: si el efecto de feriados y Pascua queda en la serie desestacionalizada.
    origen: de dónde sale la especificación.
    """
    modelo: str | None
    transformacion: str = "auto"
    outliers: list[tuple[str, str]] | None = None
    dias_semana: bool = True
    feriados: bool = True
    pascua: bool = True
    pascua_dias: int = 8
    efectos_en_serie: bool = True
    origen: str = ""
    extra: dict = field(default_factory=dict)

    def describir(self) -> dict:
        return {
            "modelo": self.modelo or "automático",
            "transformacion": self.transformacion,
            "outliers": [{"tipo": t, "fecha": f} for t, f in self.outliers or []],
            "dias_semana": self.dias_semana, "feriados": self.feriados,
            "pascua": f"easter[{self.pascua_dias}]" if self.pascua else False,
            "efectos_feriados_pascua_en_la_serie": self.efectos_en_serie,
            "origen": self.origen,
        }


def regresor_feriados(desde: str = "2004-01", hasta: str = "2032-12") -> pd.Series:
    """Feriados nacionales en días hábiles por mes, centrados por mes calendario."""
    import holidays

    meses = pd.period_range(desde, hasta, freq="M")
    feriados = holidays.Argentina(years=range(meses[0].year, meses[-1].year + 1))
    cuenta = pd.Series(0.0, index=meses)
    for dia, nombre in feriados.items():
        nombres = [n.strip() for n in str(nombre).split(";")]
        if all(any(x in n for x in NO_FERIADOS) for n in nombres):
            continue
        if pd.Timestamp(dia).weekday() < 5:
            p = pd.Period(dia, freq="M")
            if p in cuenta.index:
                cuenta[p] += 1
    return cuenta - cuenta.groupby(cuenta.index.month).transform("mean")


def _fecha_x13(periodo: str) -> str:
    p = pd.Period(periodo, freq="M")
    return f"{p.year}.{p.strftime('%b').lower()}"


def _spc(nombre: str, serie: pd.Series, esp: Especificacion) -> str:
    inicio = serie.index[0]
    datos = "\n".join(f"{v:.6f}" for v in serie.values)
    variables = []
    if esp.dias_semana:
        variables.append("td")
    if esp.pascua:
        variables.append(f"easter[{esp.pascua_dias}]")
    for tipo, periodo in esp.outliers or []:
        variables.append(f"{tipo.lower()}{_fecha_x13(periodo)}")

    partes = [f'series{{title="{nombre}" start={inicio.year}.{inicio.month} period=12\n data=(\n{datos}\n)}}']
    funcion = {"auto": "auto", "log": "log", "niveles": "none"}[esp.transformacion]
    partes.append(f"transform{{function={funcion}}}")

    # X-13 admite líneas de hasta 132 caracteres: un argumento por línea.
    reg = [f"variables=({' '.join(variables)})"] if variables else []
    if esp.feriados:
        # usertype=user: el efecto se estima pero no se quita de la serie desestacionalizada.
        tipo = "user" if esp.efectos_en_serie else "holiday"
        reg += ["user=(feriados)", 'file="feriados.dat"', 'format="datevalue"', f"usertype={tipo}"]
    if esp.modelo is None or esp.outliers is None:
        reg.append("aictest=(td easter)")
    if reg:
        partes.append("regression{\n " + "\n ".join(reg) + "\n save=(td hol)\n}")

    partes.append(f"arima{{model={esp.modelo}}}" if esp.modelo else "automdl{}")
    if esp.outliers is None:
        partes.append("outlier{types=(ao ls tc)}")
    partes.append("estimate{save=(mdl est rsd)}")
    partes.append("check{print=(acf) save=(acf)}")
    modo = {"niveles": " mode=add", "log": " mode=mult"}.get(esp.transformacion, "")
    partes.append(f"x11{{{modo.strip()} save=(d10 d11 d16)}}")
    return "\n".join(partes) + "\n"


def _leer_tabla(p: Path) -> pd.Series:
    filas = []
    for linea in p.read_text().splitlines()[2:]:
        partes = linea.split()
        if len(partes) == 2 and partes[0].isdigit():
            filas.append((pd.Period(f"{partes[0][:4]}-{partes[0][4:]}", freq="M"), float(partes[1])))
    return pd.Series(dict(filas))


def _leer_udg(p: Path) -> dict:
    d = {}
    for linea in p.read_text(errors="replace").splitlines():
        if ":" in linea:
            k, v = linea.split(":", 1)
            d[k.strip()] = v.strip()
    return d


def _num(x):
    try:
        return float(str(x).split()[0])
    except (ValueError, IndexError):
        return None


def desestacionalizar(nombre: str, serie: pd.Series, esp: Especificacion) -> tuple[pd.Series, dict]:
    """Corre X-13 sobre una serie mensual (índice: Period mensual). Devuelve la serie
    desestacionalizada y un diccionario con los diagnósticos."""
    serie = serie.dropna()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        reg = regresor_feriados(f"{serie.index[0]}", f"{max(serie.index[-1].year + 6, 2032)}-12")
        (tmp / "feriados.dat").write_text(
            "\n".join(f"{p.year} {p.month} {v:.6f}" for p, v in reg.items()) + "\n")
        (tmp / "s.spc").write_text(_spc(nombre, serie, esp))
        r = subprocess.run([str(X13), "s", "-s"], cwd=tmp, capture_output=True, text=True, timeout=300)
        err = next((tmp / n for n in ("s.err", "s_err.html") if (tmp / n).exists()), None)
        errores = re.sub(r"<[^>]+>|&nbsp;", " ", err.read_text(errors="replace")) if err else ""
        if not (tmp / "s.d11").exists():
            raise RuntimeError(f"X-13 falló para {nombre}:\n{r.stdout[-1500:]}\n{errores[-1500:]}")
        sa = _leer_tabla(tmp / "s.d11")
        if esp.efectos_en_serie and esp.pascua and (tmp / "s.hol").exists():
            # D11 ya trae el efecto de feriados (tipo user); se le devuelve el de Pascua.
            hol = _leer_tabla(tmp / "s.hol").reindex(sa.index)
            if esp.transformacion == "niveles":
                sa = sa + hol
            else:
                sa = sa * (hol / 100 if hol.mean() > 10 else hol)
        udg = _leer_udg(tmp / "s.udg") if (tmp / "s.udg").exists() else {}
        diag = _diagnosticos(udg, errores)
    return sa, diag


def _diagnosticos(udg: dict, errores: str) -> dict:
    """Modelo, calendario, outliers y calidad del ajuste."""
    def coef(clave):
        v = udg.get(clave)
        n = [_num(x) for x in v.split()] if v else []
        return {"coef": round(n[0], 6), "t": round(n[2], 2)} if len(n) >= 3 and None not in n[:3] else None

    outliers = []
    for k in udg:
        m = re.fullmatch(r"(?:Outlier|AO|LS|TC)[^$]*\$(AO|LS|TC)(\d{4})\.(\w{3})", k)
        if m:
            fecha = pd.Period(f"{m[3]} {m[2]}", freq="M")
            outliers.append({"tipo": m[1], "fecha": f"{fecha}"})
    outliers.sort(key=lambda o: o["fecha"])
    td = None
    chi = udg.get("chi$Combined Trading Day and Leap Year Regressors") or udg.get("chi$Trading Day")
    if chi:
        n = [_num(x) for x in chi.split()]
        if len(n) >= 3:
            td = {"chi2": round(n[1], 2), "gl": int(n[0]), "p": round(n[2], 4)}
    pascua = next((coef(k) for k in udg if k.lower().startswith("easter") and "$" in k), None)
    qs = lambda v: _num(v.split()[1]) if v and len(v.split()) > 1 else None  # noqa: E731
    return {
        "programa": PROGRAMA,
        "modelo": udg.get("arimamdl"),
        "transformacion": udg.get("aictrans") or udg.get("transform"),
        "aicc": _num(udg.get("aicc")),
        "calendario": {
            "dias_semana": td,
            "feriados": coef("User-defined$feriados") or coef("User-defined Holiday$feriados"),
            "pascua": pascua,
        },
        "outliers": outliers,
        "calidad": {
            "m7": _num(udg.get("f3.m07")),
            "q": _num(udg.get("f3.q")),
            "qs_desest_p": qs(udg.get("qssadj")),
            "qs_irregular_p": qs(udg.get("qsirr")),
            "ljungbox_rezagos_significativos": int(_num(udg.get("nlbq")) or 0) if udg.get("nlbq") else None,
        },
        "advertencias": [re.sub(r"\s+", " ", l).strip() for l in errores.splitlines() if "WARNING" in l][:5],
    }
