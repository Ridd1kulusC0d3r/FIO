"""Download e montagem do indice da Receita contra um servidor local que
imita o repositorio de dados abertos (listagem de meses, .zip, Range)."""

import tempfile
import threading
import unittest
import zipfile
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from fio.receita_download import baixar, descobrir, montar
from fio.indice import IndiceCNPJ, construir

DEMO = Path(__file__).resolve().parents[1] / "fio" / "dados_demo"


class Repo(BaseHTTPRequestHandler):
    arquivos: dict = {}
    quebrar_uma_vez = set()

    def log_message(self, *a):
        pass

    def do_GET(self):
        p = self.path
        if p == "/dados/":
            corpo = b'<a href="2026-07/">2026-07/</a> <a href="2026-08/">2026-08/</a>'
        elif p == "/dados/2026-08/":
            corpo = "".join(f'<a href="{n}">{n}</a>' for n in self.arquivos).encode()
        elif p.startswith("/dados/2026-08/") and p.rsplit("/", 1)[1] in self.arquivos:
            nome = p.rsplit("/", 1)[1]
            dados = self.arquivos[nome]
            ini = 0
            rng = self.headers.get("Range")
            if rng:
                ini = int(rng.split("=")[1].split("-")[0])
            parte = dados[ini:]
            self.send_response(206 if rng else 200)
            self.send_header("Content-Length", str(len(parte)))
            self.end_headers()
            if nome in self.quebrar_uma_vez and not rng:
                self.quebrar_uma_vez.discard(nome)
                self.wfile.write(parte[: len(parte) // 2])
                self.wfile.flush()
                self.connection.close()       # queda no meio do download
                return
            self.wfile.write(parte)
            return
        else:
            self.send_response(404); self.end_headers(); return
        self.send_response(200)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)


def _zip(nome_csv: str, interno: str) -> bytes:
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(DEMO / nome_csv, interno)
    return buf.getvalue()


class TestReceita(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Repo.arquivos = {
            "Estabelecimentos0.zip": _zip("Estabelecimentos0.csv", "K.ESTABELE"),
            "Empresas0.zip": _zip("Empresas0.csv", "K.EMPRECSV"),
            "Socios0.zip": _zip("Socios0.csv", "K.SOCIOCSV"),
            "Cnaes.zip": b"ignorar",
        }
        Repo.quebrar_uma_vez = {"Estabelecimentos0.zip"}
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), Repo)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}/dados/"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_descobre_mes_mais_recente(self):
        b, m, arqs = descobrir(self.base, log=lambda s: None)
        self.assertEqual(m, "2026-08")
        self.assertIn("Socios0.zip", arqs)

    def test_monta_indice_so_de_MG_com_retomada_e_apaga_zips(self):
        import fio.receita_download as rd
        rd.time.sleep = lambda s: None           # sem espera entre tentativas
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            log = []
            c = montar(d / "cnpj.sqlite", ufs={"MG"}, base=self.base,
                       pasta_tmp=d / "tmp", log=log.append)
            self.assertEqual(c["mes"], "2026-08")
            self.assertEqual(c["estabelecimentos"], 2)        # filial RJ descartada
            self.assertEqual(c["descartados_por_uf"], 1)
            self.assertTrue(any("nova tentativa" in l for l in log))   # houve queda
            self.assertEqual(list((d / "tmp").glob("*.zip")), [])      # apagou
            idx = IndiceCNPJ(d / "cnpj.sqlite")
            self.assertEqual(idx.meta()["ufs"], "MG")
            self.assertEqual(idx.por_telefone("+5521988887778"), [])
            self.assertEqual(len(idx.por_telefone("+5531988887777")), 1)
            # empresas e socios filtrados pelas raizes de MG
            self.assertEqual(idx.estatisticas()["empresa"], 2)
            nomes_indices = {
                r[0] for r in idx._con.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                )
            }
            self.assertTrue({"ix_tel1", "ix_tel2", "ix_email", "ix_basico"} <= nomes_indices)
            idx.close()
            self.assertIsNone(idx._con)

    def test_downloader_nao_promove_zip_corrompido(self):
        import fio.receita_download as rd
        rd.time.sleep = lambda s: None
        Repo.arquivos["Corrompido.zip"] = b"isto-nao-e-um-zip"
        try:
            with tempfile.TemporaryDirectory() as d:
                destino = Path(d) / "Corrompido.zip"
                with self.assertRaises(RuntimeError):
                    baixar(self.base + "2026-08/Corrompido.zip", destino,
                           log=lambda s: None, tentativas=2)
                self.assertFalse(destino.exists())
                self.assertFalse(destino.with_suffix(".zip.parcial").exists())
        finally:
            Repo.arquivos.pop("Corrompido.zip", None)

    def test_construir_local_com_filtro(self):
        with tempfile.TemporaryDirectory() as d:
            caminho = Path(d) / "i.sqlite"
            c = construir(DEMO, caminho, log=lambda s: None, ufs={"RJ"})
            self.assertEqual(c["estabelecimentos"], 1)
            self.assertEqual(c["socios"], 2)       # so os da raiz com filial no RJ
            with IndiceCNPJ(caminho) as idx:
                self.assertEqual(idx.meta()["ufs"], "RJ")
            self.assertIsNone(idx._con)


class TestBenchmarkReal(unittest.TestCase):
    def test_benchmark_roda_sobre_indice_e_nao_expoe_nomes(self):
        import json
        from fio.lab.sintetico import Gerador
        from fio.lab.benchmark_real import benchmark, tabela
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            g = Gerador(5)
            g.gravar(g.gerar(20), d)
            construir(d / "receita", d / "i.sqlite", log=lambda s: None)
            r = benchmark(d / "i.sqlite", log=lambda s: None)
            self.assertGreater(r["pares_verdadeiros"], 0)
            self.assertIn("telefone-compartilhado-podado", r["heuristicas"])
            texto = json.dumps(r) + tabela(r)
            for s in g.gerar(20).socios[:5]:      # nenhum nome de socio na saida
                self.assertNotIn(s["nome"], texto)


class TestModoColab(unittest.TestCase):
    def test_modo_colab_libera_iframe_e_host_mas_exige_token(self):
        import os, time, urllib.request, urllib.error
        from fio.lab.bancada.servidor import servir, Estado
        with tempfile.TemporaryDirectory() as d:
            os.environ["FIO_HOME"] = d
            srv = servir(porta=8795, abrir=False, token="c0l", bloquear=False, modo_colab=True)
            time.sleep(0.3)
            try:
                r = urllib.request.Request("http://127.0.0.1:8795/", headers={"Host": "x-8795-colab.dev"})
                with urllib.request.urlopen(r) as x:
                    self.assertIsNone(x.headers.get("X-Frame-Options"))
                    self.assertIn("frame-ancestors *", x.headers.get("Content-Security-Policy"))
                r = urllib.request.Request("http://127.0.0.1:8795/api/casos", headers={"Host": "x-8795-colab.dev"})
                with self.assertRaises(urllib.error.HTTPError) as e:
                    urllib.request.urlopen(r)
                self.assertEqual(e.exception.code, 401)
            finally:
                srv.shutdown(); srv.server_close(); Estado.fila.parar()
                Estado.hosts_extra = (); Estado.permitir_iframe = False
                os.environ.pop("FIO_HOME", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
