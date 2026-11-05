"""Descarga de tablas del Catálogo API-INDEC (https://api.indec.gob.ar, beta).

La API pide un token personal (JWT) que vence a los 12 meses. El token está en el secreto INDEC_API_TOKEN del
repositorio y solo llega al paso del workflow que corre este módulo: ese paso únicamente descarga y escribe JSON en
una carpeta local (api_indec/, fuera de data/ y fuera del repositorio). El procesamiento corre después, sin token.

Seguridad:
  - Solo se consulta https://api.indec.gob.ar/v1/ (el host está fijo; las tablas, en una lista cerrada).
  - El token nunca se escribe en disco ni en la salida: si un error lo incluyera, se reemplaza por "***".
  - Las respuestas se guardan tal cual (JSON); los lectores de cada fuente las validan.

Uso:  python -m pipeline.indec_api bajar    [TABLA ...]  descarga completa a api_indec/ (para procesar)
      python -m pipeline.indec_api muestra  [TABLA ...]  primeras filas de cada tabla, a inspeccion/indec_api/
      python -m pipeline.indec_api completo [TABLA ...]  descarga completa comprimida, a inspeccion/indec_api/
"""

import gzip
import json
import os
import sys
import time
from pathlib import Path

import requests

BASE = "https://api.indec.gob.ar/v1/"
RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "api_indec"
UA = "monitor-series (github.com/rodrigotperelsztein-source/monitor-series)"
PAGINA = 1000  # máximo de filas por pedido que devuelve la API

# Tablas que se bajan: nombre -> (orden estable, filtros). El orden es la clave completa que indica la documentación:
# sin un orden único, la paginación puede repetir o saltear filas.
TABLAS = {
    "ipc_nacional": ("clasificador,nivel,codigo,descripcion,periodo,anio,mes,indicador,tipo_de_indicador,"
                     "tipo_de_indicador_descripcion,region,unidad_de_medida", {}),
    "estimador-mensual-de-actividad-economica-nivel-general": ("tipo_de_indicador_descripcion,anio,mes,periodo,tipo_de_indicador", {}),
    "estimador-mensual-de-actividad-economica-sectores": ("anio,mes,codigo,descripcion,periodo,tipo_de_indicador", {}),
    "ipi_manufacturero": ("periodo,anio,mes,indicador,cuadro_web,codigo_CLaNAE_2004,descripcion,serie,tipo_de_indicador,unidad_de_medida", {}),
    "ipi_minero": ("periodo,anio,mes,indicador,cuadro_web,codigo_ClaNAE_2010,codigo_CPC_2_1,serie,descripcion,tipo_de_indicador,"
                   "unidad_de_medida", {}),
    "indice_salarios": ("clasificador,nivel,codigo,descripcion,periodo,anio,mes,indicador,tipo_de_indicador,"
                        "tipo_de_indicador_descripcion,unidad_de_medida", {}),
    "valorizacion_canastas_cba_cbt": ("clasificador,nivel,codigo,descripcion,periodo,anio,mes,indicador,tipo_de_indicador,"
                                      "tipo_de_indicador_descripcion,region,unidad_de_medida", {}),
    "sipm_precios_mayoristas": ("operativo,indicador,clasificador,nivel,codigo_apertura,descripcion,periodo,anio,mes,"
                                "tipo_de_indicador,tipo_de_indicador_descripcion,region,unidad_de_medida",
                                # Sin las clases y grupos de la CIIU (unas 150 mil filas que no se usan).
                                {"nivel": 'in.("Nivel general",Origen,Sector,División)'}),
    "icc_precios_construccion": ("indicador,codigo_apertura,codigo_CPC_1,clasificador,nivel,descripcion,periodo,anio,mes,"
                                 "tipo_de_indicador,tipo_de_indicador_descripcion,region,unidad_de_medida",
                                # Sin las clases y grupos de la CIIU (unas 150 mil filas que no se usan).
                                {"nivel": 'in.("Nivel general",Origen,Sector,División)'}),
    "comercio_exterior_nomenclaturas": ("nombre_columna,codigo", {}),
    "comercio_exterior_exportacion_bienes": ("Periodo,rubro_cod,subrubro_cod,pais_cod", {}),
    "comercio_exterior_importacion_bienes": ("Periodo,uso_economico_cod,gce_cod,pais_cod", {}),
    "canasta-crianza": ("Periodo", {}),
    "pobreza_eph": ("area_geografica_cod,periodo,anio,semestre", {}),
    "mercado_trabajo_eph": ("area_geografica_cod,periodo,anio,trimestre", {}),
}


class ErrorAPI(Exception):
    pass


def _token() -> str:
    t = os.environ.get("INDEC_API_TOKEN", "").strip()
    if not t:
        raise ErrorAPI("Falta el token (secreto INDEC_API_TOKEN).")
    return t


def _limpio(texto: str, token: str) -> str:
    return texto.replace(token, "***") if token else texto


def _pedir(sesion: requests.Session, tabla: str, params: dict, token: str, intentos: int = 3) -> requests.Response:
    if tabla not in TABLAS:
        raise ErrorAPI(f"Tabla no habilitada: {tabla}")
    url = BASE + tabla
    ultimo = None
    for i in range(intentos):
        try:
            r = sesion.get(url, params=params, timeout=90, allow_redirects=False,
                           headers={"Authorization": f"Bearer {token}", "User-Agent": UA, "Accept": "application/json",
                                    "Prefer": "count=exact"})
            if r.status_code in (401, 403):
                raise ErrorAPI(f"{tabla}: el INDEC rechazó el token ({r.status_code}). ¿Venció? Hay que regenerarlo.")
            if r.status_code >= 300 and r.status_code not in (206,):
                raise ErrorAPI(f"{tabla}: respuesta {r.status_code}: {_limpio(r.text[:300], token)}")
            return r
        except ErrorAPI:
            raise
        except Exception as e:  # noqa: BLE001
            ultimo = _limpio(str(e), token)
            print(f"  {tabla}: intento {i + 1} falló: {ultimo}")
            time.sleep(10 * (i + 1))
    raise ErrorAPI(f"{tabla}: no pude descargar: {ultimo}")


def bajar_tabla(sesion, tabla: str, token: str, maximo: int | None = None) -> dict:
    orden, filtros = TABLAS[tabla]
    filas, total, offset = [], None, 0
    while True:
        lim = PAGINA if maximo is None else min(PAGINA, maximo - len(filas))
        r = _pedir(sesion, tabla, {"order": orden, "limit": lim, "offset": offset, **filtros}, token)
        lote = r.json()
        if not isinstance(lote, list):
            raise ErrorAPI(f"{tabla}: respuesta inesperada (no es una lista).")
        filas += lote
        rango = r.headers.get("Content-Range", "")
        if "/" in rango and rango.split("/")[-1].isdigit():
            total = int(rango.split("/")[-1])
        offset += len(lote)
        if not lote or len(lote) < lim or (total is not None and offset >= total) or (maximo and len(filas) >= maximo):
            break
    if maximo is None and total is not None and len(filas) != total:
        raise ErrorAPI(f"{tabla}: bajé {len(filas)} filas de {total}.")
    return {"tabla": tabla, "url": BASE + tabla, "filas": filas, "total": total,
            "descargado": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("bajar", "muestra", "completo"):
        print(__doc__)
        return 2
    modo, pedidas = argv[0], argv[1:] or list(TABLAS)
    token = _token()
    destino = CARPETA if modo == "bajar" else RAIZ / "inspeccion" / "indec_api"
    destino.mkdir(parents=True, exist_ok=True)
    fallas = []
    with requests.Session() as s:
        for t in pedidas:
            try:
                d = bajar_tabla(s, t, token, maximo=60 if modo == "muestra" else None)
                texto = json.dumps(d, ensure_ascii=False)
                if modo == "completo":
                    (destino / f"{t}.json.gz").write_bytes(gzip.compress(texto.encode("utf-8")))
                else:
                    (destino / f"{t}.json").write_text(texto, encoding="utf-8")
                print(f"{t}: {len(d['filas'])} filas (total {d['total']})")
            except ErrorAPI as e:
                fallas.append(t)
                print(f"{t}: ERROR {_limpio(str(e), token)}")
    return 1 if fallas and len(fallas) == len(pedidas) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
