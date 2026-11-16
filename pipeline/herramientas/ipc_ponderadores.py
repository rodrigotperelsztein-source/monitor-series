"""Arma data/referencia/ipc_ponderadores.csv con la estructura de ponderaciones del IPC por región.

Los ponderadores son fijos: salen de la ENGHo y valen para toda la base diciembre 2016 = 100, así que no se
bajan en cada corrida. Están publicados en la metodología del IPC (INDEC, Metodología Nº 32, 2019), cuadros 6
(peso de cada región en el total nacional), 7 (aperturas), 8 (categorías) y 9 (bienes y servicios).

Para regenerar el archivo cuando el INDEC cambie de base:

    curl -sO https://www.indec.gob.ar/ftp/cuadros/economia/metodologia_ipc_nacional_2019.pdf
    pdftotext -layout metodologia_ipc_nacional_2019.pdf metodologia.txt
    python -m pipeline.herramientas.ipc_ponderadores metodologia.txt

El ponderador nacional de cada apertura se calcula como el promedio de los regionales pesado por el cuadro 6,
que es la forma en que el INDEC agrega las regiones para el índice nacional.
"""

import csv
import re
import sys
from pathlib import Path

REGIONES = ["gba", "pampeana", "noreste", "noroeste", "cuyo", "patagonia"]
# Cuadro 6: participación de cada región en el gasto de consumo de los hogares del total nacional.
PESO_REGION = {"gba": 0.447, "pampeana": 0.342, "noreste": 0.045, "noroeste": 0.069, "cuyo": 0.052,
               "patagonia": 0.046}
# El cuadro 6 viene redondeado a tres decimales y suma 1,001: se normaliza para que el nacional cierre en 100.
TOTAL_REGIONES = sum(PESO_REGION.values())

FILA = re.compile(r"^\s*(\d{2}(?:\.\d)?(?:\.\d{1,2})?|0)\s{2,}(.+?)\s{2,}" + r"([\d,]+)\s+" * 5 + r"([\d,]+)\s*$")
FILA_SIN_CODIGO = re.compile(r"^\s*(Estacional|Núcleo|Regulados|Bienes|Servicios)\s{2,}" + r"([\d,]+)\s+" * 5 +
                             r"([\d,]+)\s*$")
NIVEL = {1: "Nivel general", 2: "División", 4: "Grupo"}  # por el largo del código: 0, 01, 01.1, 01.1.1
# El PDF parte algunas descripciones en dos líneas, así que la fila con los números queda sin texto: se completan
# a mano con lo que dice el cuadro.
DESCRIPCIONES = {
    "07.2.4": "Otros servicios relativos al equipo de vehículos de uso del hogar",
    "09.1": "Equipos audiovisuales, fotográficos y de procesamiento de la información",
    "09.1.1": "Equipos para la recepción, grabación y reproducción de sonidos e imágenes",
    "09.3.2": "Equipo para el deporte, campamento y recreación al aire libre",
    "12.1.1": "Salones de peluquería y establecimientos de cuidados personales",
    "12.1.3": "Otros aparatos, artículos y productos para la atención personal",
}


def numero(t: str) -> float:
    return float(t.replace(".", "").replace(",", "."))


def nacional(valores: dict) -> float:
    return round(sum(valores[r] * PESO_REGION[r] for r in REGIONES) / TOTAL_REGIONES, 4)


def leer(texto: str) -> list[dict]:
    filas, vistos = [], set()
    for linea in texto.splitlines():
        m = FILA.match(linea)
        if m:
            codigo, desc = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
            if codigo in vistos:
                continue
            vistos.add(codigo)
            vals = {r: numero(v) for r, v in zip(REGIONES, m.groups()[2:])}
            desc = DESCRIPCIONES.get(codigo, desc)
            filas.append({"codigo": codigo, "nivel": NIVEL.get(len(codigo), "Clase"), "descripcion": desc,
                          **vals, "nacional": nacional(vals)})
            continue
        m = FILA_SIN_CODIGO.match(linea)
        if m:
            desc = m.group(1)
            if desc in vistos:
                continue
            vistos.add(desc)
            vals = {r: numero(v) for r, v in zip(REGIONES, m.groups()[1:])}
            nivel = "Categoría" if desc in ("Estacional", "Núcleo", "Regulados") else "Bienes y servicios"
            filas.append({"codigo": "", "nivel": nivel, "descripcion": desc, **vals, "nacional": nacional(vals)})
    return filas


def main() -> None:
    texto = Path(sys.argv[1]).read_text(encoding="utf8", errors="replace")
    filas = leer(texto)
    divisiones = [f for f in filas if f["nivel"] == "División"]
    assert len(divisiones) == 12, f"esperaba 12 divisiones, encontré {len(divisiones)}"
    for r in REGIONES + ["nacional"]:
        total = sum(f[r] for f in divisiones)
        assert abs(total - 100) < 0.05, f"las divisiones de {r} suman {total}"
    salida = Path(__file__).resolve().parents[2] / "data" / "referencia" / "ipc_ponderadores.csv"
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, ["codigo", "nivel", "descripcion", *REGIONES, "nacional"])
        w.writeheader()
        w.writerows(filas)
    print(f"ok: {salida} ({len(filas)} filas)")


if __name__ == "__main__":
    main()
