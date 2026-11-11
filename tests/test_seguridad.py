"""Reglas de seguridad del repositorio, como controles automáticos (ver SECURITY.md)."""

import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((RAIZ / ".github" / "workflows").glob("*.yml"))
PAGINAS = sorted((RAIZ / "docs").glob("*.html"))


class Workflows(unittest.TestCase):
    def test_sin_permisos_por_defecto(self):
        for w in WORKFLOWS:
            self.assertRegex(w.read_text("utf-8"), r"(?m)^permissions: \{\}$", f"{w.name}: falta permissions: {{}}")

    def test_acciones_fijadas_por_commit(self):
        for w in WORKFLOWS:
            for uso in re.findall(r"uses:\s*(\S+)", w.read_text("utf-8")):
                self.assertRegex(uso, r"@[0-9a-f]{40}$", f"{w.name}: {uso} no está fijada por su commit")

    def test_dependencias_con_huella(self):
        for w in WORKFLOWS:
            for linea in re.findall(r"pip install[^\n]*", w.read_text("utf-8")):
                self.assertIn("--require-hashes", linea, w.name)
                self.assertIn("--only-binary=:all:", linea, w.name)

    def test_el_token_del_indec_llega_a_un_solo_paso(self):
        texto = (RAIZ / ".github" / "workflows" / "actualizar.yml").read_text("utf-8")
        self.assertEqual(texto.count("secrets.INDEC_API_TOKEN"), 1)
        self.assertEqual(texto.count("secrets.GITHUB_TOKEN"), 1)
        self.assertIn("persist-credentials: false", texto)

    def test_cada_horario_tiene_su_modo(self):
        texto = (RAIZ / ".github" / "workflows" / "actualizar.yml").read_text("utf-8")
        horarios = re.findall(r'- cron: "([^"]+)"', texto)
        self.assertEqual(len(horarios), len(set(horarios)))
        en_el_selector = set(re.findall(r'"([\d,*/ -]+)"(?=[|)])', texto))
        self.assertTrue(en_el_selector <= set(horarios), f"horarios que ya no existen: {en_el_selector - set(horarios)}")


class Paginas(unittest.TestCase):
    def test_politica_de_contenido(self):
        for p in PAGINAS:
            html = p.read_text("utf-8")
            csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', html)
            self.assertTrue(csp, f"{p.name}: falta la política de contenido")
            self.assertIn("default-src 'none'", csp[1])
            conexiones = re.search(r"connect-src ([^;]+)", csp[1])[1].split()
            self.assertEqual(conexiones, ["https://raw.githubusercontent.com"], p.name)

    def test_nada_cargado_de_terceros(self):
        for p in PAGINAS:
            html = p.read_text("utf-8")
            for etiqueta, url in re.findall(r"<(script|link|img|iframe)\b[^>]*?\b(?:src|href)=\"(https?:[^\"]+)\"", html):
                self.fail(f"{p.name}: <{etiqueta}> carga {url}")


if __name__ == "__main__":
    unittest.main()
