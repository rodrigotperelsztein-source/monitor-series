"""Lectura de los registros guardados dentro de una tabla dinámica de Excel (.xlsx).

Una tabla dinámica conectada a una base de datos guarda una copia de todos los registros en
xl/pivotCache/pivotCacheRecords1.xml. Cada registro es una fila de la consulta original; los
textos repetidos se guardan una vez en la definición (sharedItems) y el registro los referencia
por posición (<x v="3"/>). Se lee en flujo, sin cargar todo el XML en memoria.
"""

import io
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from collections.abc import Callable, Iterable

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def campos(z: zipfile.ZipFile) -> list[tuple[str, list]]:
    raiz = ET.fromstring(z.read("xl/pivotCache/pivotCacheDefinition1.xml"))
    out = []
    for cf in raiz.iter(NS + "cacheField"):
        si = cf.find(NS + "sharedItems")
        items = [] if si is None else [None if it.tag == NS + "m" else it.get("v") for it in si]
        out.append((cf.get("name"), items))
    return out


def sumar(xlsx: bytes, claves: Iterable[str], valor: str,
          filtro: Callable[[dict], bool] | None = None, prefiltro: tuple[str, set] | None = None) -> tuple[dict, int]:
    """Suma `valor` agrupando por los campos `claves`.

    prefiltro: (campo, valores) para descartar rápido los registros que no interesan, antes de
    decodificar el resto de los campos. filtro: condición sobre el registro ya decodificado.
    Devuelve las sumas y la cantidad de registros leídos.
    """
    claves = list(claves)
    with zipfile.ZipFile(io.BytesIO(xlsx)) as z:
        cf = campos(z)
        nombres = [c[0] for c in cf]
        faltan = [c for c in [*claves, valor] if c not in nombres]
        if faltan:
            raise ValueError(f"La tabla dinámica no tiene los campos {faltan} (tiene {nombres}).")
        ipre, quiero = None, None
        if prefiltro:
            ipre = nombres.index(prefiltro[0])
            quiero = {str(i) for i, v in enumerate(cf[ipre][1]) if v is not None and v.strip() in prefiltro[1]}
        sumas = defaultdict(float)
        n = 0
        with z.open("xl/pivotCache/pivotCacheRecords1.xml") as f:
            for _, el in ET.iterparse(f):
                if el.tag != NS + "r":
                    continue
                n += 1
                vals = list(el)
                if len(vals) != len(cf):
                    raise ValueError(f"Registro {n} con {len(vals)} campos (se esperaban {len(cf)}).")
                if ipre is not None:
                    p = vals[ipre]
                    if p.tag != NS + "x" or p.get("v") not in quiero:
                        el.clear()
                        continue
                reg = {}
                for (nombre, items), v in zip(cf, vals):
                    if v.tag == NS + "x":
                        reg[nombre] = items[int(v.get("v"))]
                    elif v.tag == NS + "m":
                        reg[nombre] = None
                    else:
                        reg[nombre] = v.get("v")
                if filtro is None or filtro(reg):
                    clave = tuple((reg[c] or "").strip() for c in claves)
                    sumas[clave] += float(reg[valor] or 0)
                el.clear()
        esperados = ET.fromstring(z.read("xl/pivotCache/pivotCacheDefinition1.xml")).get("recordCount")
    if esperados and int(esperados) != n:
        raise ValueError(f"Se leyeron {n} registros y la tabla dice tener {esperados}.")
    return dict(sumas), n
