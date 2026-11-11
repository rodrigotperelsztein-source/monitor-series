"""Lógica del proceso que ya falló alguna vez o que no se ve hasta que falla."""

import argparse
import contextlib
import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd

from pipeline import actualizar as a
from pipeline import indec_api
from pipeline.fuentes import _api_indec, _fechas, camiones_puertos, deuda
from pipeline.fuentes import _trimestral


def _callado(f, *args, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*args, **kw)


class Camiones(unittest.TestCase):
    FILA = "{}-{} 3.816 115 448 796 5.175 937 2.242 0 82 1.882 32 5.175 112\n"

    def test_titulo_del_mes_anterior(self):
        # Noviembre de 2026: la página seguía titulada "Octubre 2026" con filas "1-nov", "2-nov"...
        tabla = "".join(self.FILA.format(d, "nov") for d in range(1, 7))
        self.assertEqual(_callado(camiones_puertos._mes_de_la_tabla, tabla, 2026, 10), (2026, 11))

    def test_cambio_de_anio(self):
        tabla = "".join(self.FILA.format(d, "ene") for d in range(1, 4))
        self.assertEqual(_callado(camiones_puertos._mes_de_la_tabla, tabla, 2026, 12), (2027, 1))

    def test_titulo_correcto_o_una_fila_mal_tipeada(self):
        tabla = "".join(self.FILA.format(d, "oct") for d in range(1, 9)) + self.FILA.format(9, "nov")
        self.assertEqual(camiones_puertos._mes_de_la_tabla(tabla, 2026, 10), (2026, 10))
        self.assertEqual(camiones_puertos._mes_de_la_tabla("1-10 " + "5 " * 13, 2026, 10), (2026, 10))

    def test_mes_que_no_es_el_siguiente(self):
        tabla = "".join(self.FILA.format(d, "mar") for d in range(1, 7))
        with self.assertRaises(ValueError):
            camiones_puertos._mes_de_la_tabla(tabla, 2026, 10)

    def test_filas(self):
        filas = camiones_puertos._filas(self.FILA.format(3, "nov"), 2026, 11)
        self.assertEqual((filas[0]["fecha"], filas[0]["total"], filas[0]["soja"]), (pd.Timestamp(2026, 11, 3), 5175, 1882))


class ApiIndec(unittest.TestCase):
    def test_motivo_de_la_falta(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(indec_api, "CARPETA", Path(d)):
            (Path(d) / "ipc_nacional.json").write_text("{}")
            _api_indec.exigir("ipc_nacional")  # está: no avisa
            (Path(d) / indec_api.ESTADO).write_text(json.dumps({"pobreza_eph": "caida"}))
            with self.assertRaises(_api_indec.ApiNoDisponible) as e:
                _api_indec.exigir("ipc_nacional", "pobreza_eph")
            self.assertFalse(e.exception.token)  # API caída: aviso, no error
            (Path(d) / indec_api.ESTADO).write_text(json.dumps({"pobreza_eph": "token"}))
            with self.assertRaises(_api_indec.ApiNoDisponible) as e:
                _api_indec.exigir("pobreza_eph")
            self.assertTrue(e.exception.token)  # token rechazado: hay que enterarse

    def test_el_token_no_sale_en_los_mensajes(self):
        self.assertEqual(indec_api._limpio("falló con abc123 en la URL", "abc123"), "falló con *** en la URL")


class Horarios(unittest.TestCase):
    def test_calendario_espera_la_hora_de_publicacion(self):
        args = argparse.Namespace(fuentes=[], modo="calendario")
        hoy = date(2026, 11, 12)
        cal = pd.DataFrame({"fecha": [pd.Timestamp(hoy)], "titulo": ["Índice de precios al consumidor (IPC)"]})
        with mock.patch.object(a.calendario, "fechas", lambda nombre, c: [hoy] if nombre else []), \
                mock.patch.object(a, "fecha_cambio", lambda fid: None):
            self.assertEqual(a.elegir(args, hoy, cal, avisar=False, hora="15:59"), [])
            despues = a.elegir(args, hoy, cal, avisar=False, hora="16:00")
        self.assertIn("ipc", despues)
        self.assertNotIn("bcra", despues)  # sin calendario: no entra en modo calendario

    def test_atrasos(self):
        cambios = {"bcra": date(2026, 11, 1), "ipc": date(2026, 10, 14), "electrodomesticos": date(2026, 8, 1)}
        with mock.patch.object(a, "fecha_cambio", lambda fid: cambios.get(fid)):
            r = {fid: (dias, tol) for fid, dias, tol in a.atrasos(date(2026, 11, 20))}
        self.assertEqual(r, {"bcra": (19, 10)})  # diaria con 19 días; IPC (37 de 50) y electrodomésticos (111 de 130), no


class Utilidades(unittest.TestCase):
    def test_nombres_con_fecha(self):
        self.assertEqual(_fechas.urls_mm_aa("a_{mm}_{aa}.xls", date(2027, 1, 5), 3), ["a_01_27.xls", "a_12_26.xls", "a_11_26.xls"])
        self.assertEqual(_fechas.urls_trimestre("c_{t}_{anio}.xls", date(2027, 2, 1), 3),
                         ["c_I_2027.xls", "c_IV_2026.xls", "c_III_2026.xls"])

    def test_meses_en_texto(self):
        self.assertEqual(deuda._mes("jul-26*"), pd.Timestamp(2026, 7, 1))
        self.assertEqual(deuda._mes("Sep-2019"), pd.Timestamp(2019, 9, 1))
        self.assertIsNone(deuda._mes("Total"))

    def test_cuadro_trimestral(self):
        trimestres = [f"{q}º trimestre" for _ in (2025, 2026) for q in (1, 2, 3, 4)]
        df = pd.DataFrame([[None, None, 2025, None, None, None, "2026 (2)", None, None, None],
                           [None, None, *trimestres],
                           ["B1B", "Producto interno bruto", *range(1, 9)]])
        (rotulo, serie), = _trimestral.filas(df)
        self.assertTrue(rotulo.startswith("B1B"))
        self.assertEqual((serie.index[0], serie.index[-1], serie.iloc[-1]), (pd.Period("2025Q1"), pd.Period("2026Q4"), 8))


if __name__ == "__main__":
    unittest.main()
