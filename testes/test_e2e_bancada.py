"""Ponta a ponta no navegador (Chromium headless), como um leigo usaria.

Pulado automaticamente se o Playwright nao estiver instalado -- ele NAO e
dependencia do F.I.O.; so do ambiente de teste.
"""

import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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


@unittest.skipUnless(TEM_PW and not os.environ.get("FIO_SEM_E2E"), "playwright indisponivel")
class TestBancadaAtrasDeProxy(unittest.TestCase):
    """Simula o Colab: a bancada servida por um proxy com prefixo de caminho,
    dentro de um iframe de outra origem, com sessionStorage bloqueado.
    Foi exatamente aqui que a tela completa deixava de carregar."""

    PREFIXO = "/_proxy/8791"

    def test_tela_completa_carrega_no_iframe_com_prefixo(self):
        from fio.lab.bancada.servidor import servir, Estado
        prefixo = self.PREFIXO
        with tempfile.TemporaryDirectory() as tmp:
            antigo = os.environ.get("FIO_HOME")
            os.environ["FIO_HOME"] = tmp
            srv = servir(porta=8791, abrir=False, token="simtok", bloquear=False,
                         modo_colab=True)

            class Proxy(BaseHTTPRequestHandler):
                def log_message(self, *a):
                    pass

                def _enc(self, corpo=None):
                    if not self.path.startswith(prefixo):
                        self.send_response(404)
                        self.end_headers()
                        return
                    req = urllib.request.Request(
                        "http://127.0.0.1:8791" + (self.path[len(prefixo):] or "/"),
                        data=corpo, method=self.command,
                        headers={k: v for k, v in self.headers.items()
                                 if k.lower() not in ("host", "content-length")})
                    req.add_header("Host", "8791-abc.colab.googleusercontent.com")
                    try:
                        r = urllib.request.urlopen(req)
                    except urllib.error.HTTPError as e:
                        r = e
                    dados = r.read()
                    self.send_response(r.status)
                    for k, v in r.headers.items():
                        if k.lower() in ("content-type", "cache-control",
                                         "content-security-policy"):
                            self.send_header(k, v)
                    self.send_header("Content-Length", str(len(dados)))
                    self.end_headers()
                    self.wfile.write(dados)

                def do_GET(self):
                    self._enc()

                def do_POST(self):
                    self._enc(self.rfile.read(int(self.headers.get("Content-Length", 0))))

            class Pai(BaseHTTPRequestHandler):
                def log_message(self, *a):
                    pass

                def do_GET(self):
                    alvo = prefixo + "/" + ("workbench/" if "wb" in self.path else "")
                    h = (f'<iframe id="f" src="http://127.0.0.1:8792{alvo}#t=simtok" '
                         f'style="width:1200px;height:800px"></iframe>').encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(h)

            servidores = [ThreadingHTTPServer(("127.0.0.1", 8792), Proxy),
                          ThreadingHTTPServer(("127.0.0.1", 8793), Pai)]
            for sv in servidores:
                threading.Thread(target=sv.serve_forever, daemon=True).start()
            time.sleep(0.3)
            erros = []
            try:
                with sync_playwright() as pw:
                    nav = pw.chromium.launch()
                    for url, texto in (("http://127.0.0.1:8793/", "Telefone e caso"),
                                       ("http://127.0.0.1:8793/?wb", "Bem-vindo ao F.I.O. Lab")):
                        pg = nav.new_page(viewport={"width": 1300, "height": 900})
                        pg.on("pageerror", lambda e: erros.append(str(e)))
                        pg.add_init_script(
                            "Object.defineProperty(window,'sessionStorage',"
                            "{get(){throw new DOMException('blocked','SecurityError')}});")
                        pg.goto(url)
                        fr = pg.frame_locator("#f")
                        fr.locator(f"text={texto}").first.wait_for(timeout=10000)
                        if "wb" not in url:
                            # frontend do Colab: a lista de base legal tem de vir
                            # do /api/estado (dict) e a versao aparecer
                            fr.locator("#baseLegal option").nth(3).wait_for(
                                state="attached", timeout=10000)
                            n = fr.locator("#baseLegal option").count()
                            assert n >= 10, f"base legal com {n} opcoes"
                            assert fr.locator("#baseLegal").input_value() == ""
                            assert "F.I.O." in fr.locator("#versao").inner_text()
                        if "wb" in url:
                            fr.locator("#bvdemo").click()
                            fr.locator("#g circle").first.wait_for(timeout=15000)
                        pg.close()
                    nav.close()
            finally:
                for sv in servidores:
                    sv.shutdown()
                    sv.server_close()
                Estado.fila.parar()
                srv.shutdown()
                srv.server_close()
                if antigo is None:
                    os.environ.pop("FIO_HOME", None)
                else:
                    os.environ["FIO_HOME"] = antigo
            self.assertEqual(erros, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
