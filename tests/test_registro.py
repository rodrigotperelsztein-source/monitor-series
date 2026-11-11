"""Controles sobre el registro de fuentes: que cada una tenga lo que el proceso necesita."""

import unittest
from datetime import date

from pipeline import actualizar as a
from pipeline import indec_api


class Registro(unittest.TestCase):
    def test_ids_unicos_y_iguales_al_modulo(self):
        modulos = [f for _, fuentes in a.REGISTRO for f in fuentes]
        self.assertEqual(len(modulos), len(a.FUENTES), "hay una fuente repetida en REGISTRO")
        for f in modulos:
            self.assertEqual(f.ID, f.__name__.rsplit(".", 1)[-1])
            self.assertRegex(f.ID, r"^[a-z0-9_]+$")

    def test_atributos(self):
        for fid, f in a.FUENTES.items():
            with self.subTest(fuente=fid):
                for campo in ("NOMBRE", "PAGINA", "FRECUENCIA", "UNIDAD", "ORGANISMO"):
                    self.assertTrue(getattr(f, campo, ""), f"falta {campo}")
                self.assertIn(f.FRECUENCIA, a.TOLERANCIA_DIAS)
                self.assertTrue(f.PAGINA.startswith("https://"))
                self.assertTrue(hasattr(f, "COLUMNAS") or hasattr(f, "columnas"))
                if fid in a.DERIVADAS:
                    self.assertTrue(callable(f.calcular) and callable(f.validar) and f.VERSION)
                else:
                    self.assertTrue(callable(f.leer) and callable(f.validar))
                    self.assertTrue(hasattr(f, "bajar") or hasattr(f, "urls") or f.URL.startswith("https://"))

    def test_columnas(self):
        for fid, f in a.FUENTES.items():
            for cid, c in getattr(f, "COLUMNAS", {}).items():
                with self.subTest(serie=f"{fid}.{cid}"):
                    self.assertRegex(cid, r"^[a-z0-9_]+$")
                    self.assertTrue(c.nombre)
                    if c.tipo == "variacion" and getattr(c, "base", None):
                        self.assertIn(c.base, f.COLUMNAS, "la variación apunta a una columna que no existe")

    def test_derivadas_despues_de_su_base(self):
        orden = list(a.FUENTES)
        for fid, f in a.DERIVADAS.items():
            for b in a.bases(f):
                self.assertLess(orden.index(b), orden.index(fid), f"{fid} va antes que su base {b}")

    def test_tablas_de_la_api_habilitadas(self):
        for fid, f in a.FUENTES.items():
            t = getattr(f, "TABLA_API", None)
            for tabla in ([t] if isinstance(t, str) else list(t or ())):
                self.assertIn(tabla, indec_api.TABLAS, f"{fid} pide una tabla que indec_api no baja")

    def test_urls_con_fecha(self):
        for fid, f in a.FUENTES.items():
            if hasattr(f, "urls"):
                urls = f.urls(date(2027, 1, 15))  # cambio de año
                self.assertTrue(urls and all(u.startswith("https://") and "{" not in u for u in urls), fid)


if __name__ == "__main__":
    unittest.main()
