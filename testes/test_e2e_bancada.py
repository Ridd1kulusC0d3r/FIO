"""Ponta a ponta no navegador (Chromium headless), como um leigo usaria.

Pulado automaticamente se o Playwright nao estiver instalado -- ele NAO e
dependencia do F.I.O.; so do ambiente de teste.
"""

import os
import tempfile
import time
import unittest

try:
    from playwright.sync_api import sync_playwright
    TEM_PW = True
except ImportError:
    TEM_PW = False


@unittest.skipUnless(TEM_PW and not os.environ.get("FIO_SEM_E2E"), "playwright indisponivel")
class TestBancadaNavegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls._env = os.environ.get("FIO_HOME")
        os.environ["FIO_HOME"] = cls.tmp.name
        from fio.lab.bancada.servidor import servir
        cls.srv = servir(porta=8793, abrir=False, token="e2e", bloquear=False)
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        from fio.lab.bancada.servidor import Estado
        Estado.fila.parar()
        cls.srv.shutdown()
        cls.srv.server_close()
        if cls._env is None:
            os.environ.pop("FIO_HOME", None)
        else:
            os.environ["FIO_HOME"] = cls._env

    def test_jornada_do_leigo(self):
        erros = []
        with sync_playwright() as pw:
            nav = pw.chromium.launch()
            for largura, tema in ((1280, "light"), (390, "dark")):
                pg = nav.new_page(viewport={"width": largura, "height": 900}, color_scheme=tema)
                pg.on("pageerror", lambda e: erros.append(str(e)))
                pg.goto("http://127.0.0.1:8793/#t=e2e")
                pg.wait_for_selector("text=Bem-vindo ao F.I.O. Lab")
                # token saiu da barra de endereco
                self.assertNotIn("e2e", pg.url)
                pg.click("#bvdemo")
                pg.wait_for_selector("#g circle", timeout=15000)
                self.assertGreater(pg.locator("#g circle").count(), 10)
                for aba in ("vínculos", "agrupamentos", "observações", "custódia",
                            "experimentos", "quesitos"):
                    pg.click(f".tab[data-t='{aba}']")
                    pg.wait_for_timeout(250)
                pg.click(".tab[data-t='custódia']")
                pg.wait_for_selector("text=Cadeia íntegra")
                with pg.expect_popup() as pop:
                    pg.click("text=Laudo")
                laudo = pop.value
                laudo.wait_for_selector("text=CADEIA DE CUSTÓDIA")
                laudo.close()
                pg.close()
            # sem token: a pagina avisa em vez de quebrar
            pg = nav.new_page()
            pg.on("pageerror", lambda e: erros.append(str(e)))
            pg.goto("http://127.0.0.1:8793/")
            pg.evaluate("sessionStorage.clear()")
            pg.goto("http://127.0.0.1:8793/")
            pg.wait_for_selector("text=Token ausente")
            nav.close()
        self.assertEqual(erros, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
