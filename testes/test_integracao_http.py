"""Integracao HTTP de verdade, contra um servidor local que imita as APIs.

Os testes de parser (test_lab) injetam a resposta pronta. Aqui o caminho
inteiro roda: ClienteHTTP monta a requisicao, o urllib abre conexao TCP,
o servidor responde (inclusive com gzip e erro HTTP), o cache guarda, o
ledger registra o artefato e o coletor interpreta. So o endereco e
reescrito para 127.0.0.1.
"""

import gzip
import json
import tempfile
import threading
import unittest
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from unittest import mock

from fio.politica import Caso
from fio.grafo.modelo import Grafo, Entidade
from fio.evidencia.ledger import Ledger
from fio.evidencia.cache import CacheHTTP
from fio.coletores.base import Contexto
from fio.coletores import REGISTRO

DDG_HTML = (b'<html><body><a class="result-link" href="https://duckduckgo.com/l/?uddg='
            b'https%3A%2F%2Fwww.auroratech.com.br%2Fcontato&rut=x">Contato</a>'
            b'<td>Fale conosco (31) 98888-7777 ou (31) 3333-4444, '
            b'comercial@auroratech.com.br</td></body></html>')

DDG_VAZIO = (b'<html><body><p>Nenhum resultado encontrado para a sua busca. '
             b'Tente outros termos ou verifique a ortografia.</p></body></html>')

RESPOSTAS = {
    "/haveibeenpwned.com/api/v3/breachedaccount/contato@auroratech.com.br": [
        {"Name": "ExemploBreach", "Title": "Exemplo", "BreachDate": "2024-01-01",
         "PwnCount": 1000, "IsVerified": True,
         "DataClasses": ["Email addresses", "Phone numbers"]}],
    "/brasilapi.com.br/api/cnpj/v1/11222333000181": {
        "razao_social": "AURORA TECH SOLUCOES LTDA", "uf": "MG", "cep": "30120010",
        "ddd_telefone_1": "3133334444", "ddd_telefone_2": "31988887777",
        "email": "contato@auroratech.com.br",
        "qsa": [{"nome_socio": "MARIA CLARA PEREIRA", "cnpj_cpf_do_socio": "***456789**",
                 "qualificacao_socio": "Socio-Administrador"}]},
    "/viacep.com.br/ws/30120010/json/": {
        "cep": "30120-010", "logradouro": "Rua dos Andradas", "bairro": "Centro",
        "localidade": "Belo Horizonte", "uf": "MG", "ibge": "3106200", "ddd": "31"},
    "/api.queridodiario.ok.org.br/gazettes": {
        "total_gazettes": 1, "gazettes": [{
            "territory_id": "3106200", "territory_name": "Belo Horizonte",
            "state_code": "MG", "date": "2026-03-10", "edition": "6801",
            "is_extra_edition": False, "url": "https://dom-web.pbh.gov.br/x.pdf",
            "excerpts": ["contrato com AURORA TECH, CNPJ 11.222.333/0001-81, "
                         "telefone (31) 98888-7777, CEP 30120-010"]}]},
    "/rdap.registro.br/domain/auroratech.com.br": {
        "handle": "auroratech.com.br",
        "entities": [{"handle": "AUR123", "roles": ["registrant"],
                      "vcardArray": ["vcard", [["fn", {}, "text", "AURORA TECH SOLUCOES LTDA"],
                                               ["tel", {}, "text", "tel:+55-31-3333-4444"]]]}]},
}


class Falso(BaseHTTPRequestHandler):
    contagem = {}

    def log_message(self, *a):
        pass

    def do_GET(self):
        caminho = urllib.parse.urlparse(self.path).path
        Falso.contagem[caminho] = Falso.contagem.get(caminho, 0) + 1
        if caminho.startswith("/viacep.com.br/ws/00000000"):
            self.send_response(400); self.end_headers(); return
        if caminho.startswith("/lite.duckduckgo.com/lite"):
            # valor impossivel do baseline: a fonte responde "sem resultados"
            corpo = DDG_VAZIO if "fio-baseline" in self.path or "5500000000000" in self.path else DDG_HTML
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
            return
        corpo = RESPOSTAS.get(caminho)
        if corpo is None:
            self.send_response(404); self.end_headers(); self.wfile.write(b"{}"); return
        dados = gzip.compress(json.dumps(corpo).encode())
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)


class TestIntegracaoHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), Falso)
        cls.porta = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        original = urllib.request.urlopen

        def reescrever(req, *a, **kw):
            url = req.full_url if isinstance(req, urllib.request.Request) else req
            p = urllib.parse.urlparse(url)
            novo = f"http://127.0.0.1:{cls.porta}/{p.netloc}{p.path}" + (f"?{p.query}" if p.query else "")
            if isinstance(req, urllib.request.Request):
                req = urllib.request.Request(novo, headers=dict(req.header_items()))
            else:
                req = novo
            kw.pop("context", None)
            return original(req, *a, **kw)
        cls.patch = mock.patch("fio.coletores.base.urllib.request.urlopen", side_effect=reescrever)
        cls.patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.patch.stop()
        cls.srv.shutdown()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.caso = Caso(id="HTTP", titulo="t", base_legal="pesquisa-academica",
                         finalidade="teste de integracao http",
                         responsavel="ci", escopo=["11222333000181", "30120010",
                                                   "auroratech.com.br", "+5531988887777"])
        self.ctx = Contexto(caso=self.caso, grafo=Grafo("HTTP"),
                            ledger=Ledger(d, "HTTP", "ci"),
                            cache=CacheHTTP(d / "c.sqlite"), intervalo=0)

    def tearDown(self):
        self.ctx.cache.fechar()
        self.tmp.cleanup()

    def test_cnpj_api_ponta_a_ponta_com_gzip_cache_e_ledger(self):
        col = REGISTRO["cnpj-api"]
        alvo = Entidade("cnpj", "11222333000181")
        a1 = col.executar(alvo, self.ctx)
        rel = {a.relacao for a in a1}
        self.assertIn("telefone_declarado", rel)
        self.assertIn("tem_socio", rel)
        socio = [a.destino for a in a1 if a.relacao == "tem_socio"][0]
        self.assertEqual(socio.valor, "MARIA CLARA PEREIRA [***456789**]")
        antes = Falso.contagem.get("/brasilapi.com.br/api/cnpj/v1/11222333000181", 0)
        a2 = col.executar(alvo, self.ctx)             # segunda vez: cache
        self.assertEqual(len(a1), len(a2))
        self.assertEqual(Falso.contagem["/brasilapi.com.br/api/cnpj/v1/11222333000181"], antes)
        acoes = [r.acao for r in self.ctx.ledger.registros()]
        self.assertIn("coleta.http", acoes)
        self.assertIn("coleta.cache", acoes)
        self.assertTrue(self.ctx.ledger.verificar()[0])
        http = [r for r in self.ctx.ledger.registros() if r.acao == "coleta.http"][0]
        bruto = self.ctx.ledger.artefato(http.artefato_sha256)
        self.assertEqual(json.loads(bruto)["razao_social"], "AURORA TECH SOLUCOES LTDA")

    def test_viacep(self):
        a = REGISTRO["viacep"].executar(Entidade("cep", "30120010"), self.ctx)
        self.assertEqual(a[0].destino.tipo, "municipio")
        self.assertEqual(a[0].destino.valor, "3106200")

    def test_querido_diario_extrai_coocorrencias(self):
        a = REGISTRO["querido-diario"].executar(Entidade("telefone", "+5531988887777"), self.ctx)
        self.assertTrue(any(x.relacao == "publicado_em" for x in a))
        mencoes = {x.destino.valor for x in a if x.relacao == "menciona"}
        self.assertIn("11222333000181", mencoes)
        self.assertIn("30120010", mencoes)

    def test_rdap_registro_br(self):
        a = REGISTRO["rdap"].executar(Entidade("dominio", "auroratech.com.br"), self.ctx)
        tels = [x.destino.valor for x in a if x.relacao == "telefone_registrado"]
        self.assertEqual(tels, ["+553133334444"])

    def test_http_404_nao_quebra_e_fica_no_ledger(self):
        self.caso.escopo.append("99999999000191")
        a = REGISTRO["cnpj-api"].executar(Entidade("cnpj", "99999999000191"), self.ctx)
        self.assertEqual(a, [])
        regs = [r for r in self.ctx.ledger.registros() if r.acao == "coleta.http"]
        self.assertEqual(regs[-1].metadados["status"], 404)


    def test_web_extrai_url_dominio_e_coocorrencias(self):
        a = REGISTRO["web"].executar(Entidade("telefone", "+5531988887777"), self.ctx)
        urls = {x.destino.valor for x in a if x.relacao == "mencionado_em"}
        self.assertIn("https://www.auroratech.com.br/contato", urls)
        coo = {x.destino.valor for x in a if x.relacao == "cocorre_com"}
        self.assertIn("+553133334444", coo)
        self.assertIn("comercial@auroratech.com.br", coo)
        # coocorrencia nasce fraca (D3)
        fr = [x.fonte.admiralty for x in a if x.relacao == "cocorre_com"]
        self.assertTrue(all(f == "D3" for f in fr))

    def test_hibp_com_chave(self):
        self.caso.escopo.append("contato@auroratech.com.br")
        self.ctx.segredos["hibp_api_key"] = "chave-teste"
        alvo = Entidade("email", "contato@auroratech.com.br")
        a = REGISTRO["hibp"].executar(alvo, self.ctx)
        self.assertEqual(a[0].relacao, "exposto_em")
        self.assertTrue(alvo.atributos.get("telefone_possivelmente_exposto"))

    def test_hibp_sem_chave_e_pulado(self):
        self.caso.escopo.append("x@y.com")
        self.assertEqual(REGISTRO["hibp"].executar(Entidade("email", "x@y.com"), self.ctx), [])
        self.assertIn("coletor.pulado", [r.acao for r in self.ctx.ledger.registros()])

    def test_modo_offline_bloqueia_coletor_de_rede(self):
        self.ctx.permitir_rede = False
        self.assertEqual(REGISTRO["viacep"].executar(Entidade("cep", "30120010"), self.ctx), [])


class TestColetoresLocais(unittest.TestCase):
    def test_exposicao_local_so_por_hash(self):
        from fio.coletores.exposicao import construir_indice
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "lista.txt").write_text("(31) 98888-7777\nalguem@exemplo.test\n", encoding="utf-8")
            n = construir_indice(d / "lista.txt", d / "idx.hashes",
                                 {"id": "c1", "titulo": "corpus", "origem": "teste"})
            self.assertEqual(n, 2)
            self.assertNotIn("98888", (d / "idx.hashes").read_text())   # sem dado em claro
            caso = Caso(id="E", titulo="t", base_legal="pesquisa-academica",
                        finalidade="teste de exposicao local", responsavel="ci",
                        escopo=["+5531988887777", "+5511999999999"])
            ctx = Contexto(caso=caso, grafo=Grafo("E"), ledger=Ledger(d, "E", "ci"),
                           cache=CacheHTTP(d / "c.sqlite"),
                           segredos={"indice_exposicao": str(d / "idx.hashes")})
            col = REGISTRO["exposicao-local"]
            alvo = Entidade("telefone", "+5531988887777", atributos={"e164": "+5531988887777"})
            self.assertEqual(col.executar(alvo, ctx)[0].relacao, "consta_em_corpus")
            outro = Entidade("telefone", "+5511999999999", atributos={"e164": "+5511999999999"})
            self.assertEqual(col.executar(outro, ctx), [])
            self.assertEqual(outro.atributos["exposicao_local"], "nao consta")
            ctx.cache.fechar()

    def test_dados_abertos_consulta_indices_por_receita(self):
        import os
        from fio.receitas import construir
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            with mock.patch.dict(os.environ, {"FIO_HOME": str(d)}):
                (d / "cnes.csv").write_text(
                    "CO_CNES;NO_FANTASIA;NU_TELEFONE;NO_EMAIL;NU_CNPJ\n"
                    "777;CLINICA DEMO;(31) 98888-7777;c@demo.test;11222333000181\n",
                    encoding="latin-1")
                construir("cnes", d / "cnes.csv", d)
                (d / "faixas.csv").write_text("CN,PREFIXO,FAIXA_INICIAL,FAIXA_FINAL,PRESTADORA\n"
                                              "31,98888,0000,9999,OPERADORA X\n")
                construir("anatel-faixas", d / "faixas.csv", d)
                caso = Caso(id="D", titulo="t", base_legal="pesquisa-academica",
                            finalidade="teste de dados abertos", responsavel="ci",
                            escopo=["+5531988887777"])
                ctx = Contexto(caso=caso, grafo=Grafo("D"), ledger=Ledger(d, "D", "ci"),
                               cache=CacheHTTP(d / "c.sqlite"))
                a = REGISTRO["dados-abertos"].executar(
                    Entidade("telefone", "+5531988887777"), ctx)
                rel = {x.relacao for x in a}
                self.assertIn("telefone_de_estabelecimento_de_saude", rel)
                self.assertIn("faixa_destinada_a", rel)
                ctx.cache.fechar()


class TestPluginsERelatorios(unittest.TestCase):
    def test_plugin_de_exemplo_carrega_e_entra_na_assinatura(self):
        import shutil
        from fio.lab import plugins
        from fio.analise import ANALISADORES
        with tempfile.TemporaryDirectory() as d:
            pasta = Path(d) / "plugins"
            pasta.mkdir()
            shutil.copy(Path(__file__).resolve().parents[1] / "exemplos" / "plugin_exemplo.py", pasta)
            (pasta / "quebrado.py").write_text("raise RuntimeError('plugin ruim')\n")
            info = plugins.carregar(pasta)
            self.assertIn("exemplo-nao-geografico-pessoa", ANALISADORES)
            erros = [v["erro"] for v in info.values() if v["erro"]]
            self.assertTrue(any("plugin ruim" in e for e in erros))
            self.assertIn("plugin_exemplo.py", plugins.assinatura_codigo()["plugins"])
            inv = plugins.inventario()
            self.assertIn("normalizacao", inv["coletores"])

    def test_relatorios_tecnico_markdown_e_laudo(self):
        import os
        from fio.demo import montar
        from fio.caso import CasoEmDisco
        from fio.relatorio import gerar_html, gerar_markdown
        from fio.relatorio.laudo import gerar_laudo
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.dict(os.environ, {"FIO_HOME": d}):
                montar(recriar=True)
                cd = CasoEmDisco("DEMO-FRAUDE-BOLETO")
                led = cd.ledger()
                args = (cd.caso(), cd.grafo(), led.registros(), led.verificar())
                h = gerar_html(*args)
                self.assertIn("Cadeia de custodia", h)
                self.assertIn("<svg", h)
                self.assertNotIn("529.982.247-25", h)      # minimizacao do CPF
                m = gerar_markdown(*args)
                self.assertIn("Tabela de correlacao", m)
                for modelo in ("laudo", "relint"):
                    l = gerar_laudo(*args, modelo=modelo)
                    self.assertIn("158-B", l)
                    self.assertNotIn("529.982.247-25", l)


class TestCLI(unittest.TestCase):
    def test_comandos_principais_em_processo(self):
        import os, io, contextlib
        from fio.cli import main
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.dict(os.environ, {"FIO_HOME": d}):
                saida = io.StringIO()
                with contextlib.redirect_stdout(saida):
                    self.assertEqual(main(["numero", "31988887777"]), 0)
                    self.assertEqual(main(["doc", "cep", "30120-010"]), 0)
                    self.assertEqual(main(["demo"]), 0)
                    self.assertEqual(main(["caso", "listar"]), 0)
                    self.assertEqual(main(["caso", "ver", "--caso", "DEMO-FRAUDE-BOLETO"]), 0)
                    self.assertEqual(main(["clusters", "--caso", "DEMO-FRAUDE-BOLETO"]), 0)
                    self.assertEqual(main(["tabela", "--caso", "DEMO-FRAUDE-BOLETO"]), 0)
                    self.assertEqual(main(["grafo", "--caso", "DEMO-FRAUDE-BOLETO", "--formato", "csv"]), 0)
                    self.assertEqual(main(["ledger", "listar", "--caso", "DEMO-FRAUDE-BOLETO"]), 0)
                    self.assertEqual(main(["coletores"]), 0)
                    self.assertEqual(main(["receita", "listar"]), 0)
                    self.assertEqual(main(["quesito", "listar", "--caso", "DEMO-FRAUDE-BOLETO"]), 0)
                    self.assertEqual(main(["quesito", "responder", "--caso", "DEMO-FRAUDE-BOLETO",
                                           "--n", "1", "--texto", "Sim."]), 0)
                    self.assertEqual(main(["laudo", "--caso", "DEMO-FRAUDE-BOLETO",
                                           "--saida", str(Path(d) / "l.html")]), 0)
                    self.assertEqual(main(["ledger", "verificar", "--caso", "DEMO-FRAUDE-BOLETO"]), 0)
                texto = saida.getvalue()
                self.assertIn("+5531988887777", texto)
                self.assertIn("cadeia integra", texto)


class TestDemoEDiagnostico(unittest.TestCase):
    def test_demo_monta_offline(self):
        import os
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.dict(os.environ, {"FIO_HOME": d}):
                from fio.demo import montar
                r = montar(recriar=True)
                self.assertEqual(r["metricas"]["requisicoes"], 0)
                self.assertGreaterEqual(r["metricas"]["vinculos"], 30)
                self.assertTrue(montar()["ja_existia"])

    def test_diagnostico_sem_rede_nao_explode(self):
        from fio import diagnostico
        with mock.patch("fio.diagnostico.urllib.request.urlopen",
                        side_effect=OSError("sem rede")):
            res = diagnostico.sondar({}, espera=0)
        self.assertTrue(all(r["ok"] in (False, None) for r in res))
        self.assertTrue(any("sem chave" == r["status"] for r in res))


if __name__ == "__main__":
    unittest.main(verbosity=2)
