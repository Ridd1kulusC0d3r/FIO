"""Suite minima mas nao decorativa: cobre o que quebra em silencio."""

import json
import tempfile
import unittest
from pathlib import Path

from fio.core.normalize import normalizar, variantes, extrair_de_texto
from fio.core import anatel
from fio.politica import Caso, ViolacaoDeEscopo
from fio.evidencia.ledger import Ledger
from fio.grafo.modelo import Grafo, Entidade, Fonte, Aresta
from fio.grafo.scoring import score_admiralty, combinar
from fio.grafo.clusters import detectar_clusters, pontes
from fio.indice import _e164


class TestNormalizacao(unittest.TestCase):
    def test_grafias_convergem(self):
        alvo = "+5531988887777"
        for g in ["+55 31 98888-7777", "031988887777", "(31)98888-7777",
                  "55 31 9 8888 7777", "0 21 31 98888-7777", "31988887777"]:
            self.assertEqual(normalizar(g).chave, alvo, g)

    def test_csp_removido(self):
        t = normalizar("021 31 98888-7777")
        self.assertEqual(t.csp, "21")
        self.assertEqual(t.e164, "+5531988887777")

    def test_ddd_inexistente(self):
        t = normalizar("2098888777")
        self.assertFalse(t.valido)
        self.assertIn("20", t.justificativa)

    def test_fixo_e_movel(self):
        self.assertEqual(normalizar("3133334444").tipo, "fixo")
        self.assertEqual(normalizar("31988887777").tipo, "movel")

    def test_movel_legado_sinaliza_nono_digito(self):
        t = normalizar("3188887777")
        self.assertEqual(t.tipo, "movel")
        self.assertTrue(any("9o digito" in a for a in t.avisos))

    def test_nao_geografico_nao_individualiza(self):
        t = normalizar("0800 771 0000")
        self.assertEqual(t.tipo, "nao-geografico")
        self.assertTrue(t.avisos)

    def test_numero_fabricado_nao_passa(self):
        self.assertFalse(normalizar("11234567890").valido)

    def test_variantes_incluem_forma_sem_nono_digito(self):
        v = variantes(normalizar("31988887777"))
        self.assertIn("+5531988887777", v)
        self.assertTrue(any(x == "(31) 8888-7777" for x in v))

    def test_extracao_de_texto(self):
        achados = extrair_de_texto("ligue (31) 98888-7777 ou 3133334444 hoje")
        self.assertEqual({t.e164 for t in achados},
                         {"+5531988887777", "+553133334444"})

    def test_entrada_lixo_nao_explode(self):
        for x in [None, "", "abc", "()", "+++", "0"]:
            self.assertFalse(normalizar(x).valido)

    def test_todos_ddds_tem_uf(self):
        for ddd, (uf, area) in anatel.DDD_INFO.items():
            self.assertEqual(len(ddd), 2)
            self.assertEqual(len(uf), 2)
            self.assertTrue(area)


class TestPolitica(unittest.TestCase):
    def caso(self, **kw):
        base = dict(id="C1", titulo="t", base_legal="lgpd-7-vi",
                    finalidade="instruir defesa em acao civil",
                    responsavel="analista", escopo=["+5531988887777", "x.com.br"])
        base.update(kw)
        return Caso(**base)

    def test_base_legal_invalida(self):
        with self.assertRaises(ViolacaoDeEscopo):
            self.caso(base_legal="porque-sim")

    def test_finalidade_vaga_recusada(self):
        with self.assertRaises(ViolacaoDeEscopo):
            self.caso(finalidade="osint")

    def test_escopo_bloqueia_terceiro(self):
        c = self.caso()
        c.autorizar("+5531988887777")
        c.autorizar("www.x.com.br")
        with self.assertRaises(ViolacaoDeEscopo):
            c.autorizar("+5511999998888")

    def test_escopo_vazio_recusa_tudo(self):
        c = self.caso(escopo=[])
        with self.assertRaises(ViolacaoDeEscopo):
            c.autorizar("qualquer")

    def test_caso_expirado_nao_coleta(self):
        c = self.caso(expira_em="2000-01-01T00:00:00+00:00")
        with self.assertRaises(ViolacaoDeEscopo):
            c.autorizar("+5531988887777")


class TestLedger(unittest.TestCase):
    def test_cadeia_integra(self):
        with tempfile.TemporaryDirectory() as d:
            l = Ledger(d, "C1", "analista")
            l.registrar("caso.aberto")
            l.registrar("coleta", artefato=b"conteudo")
            self.assertEqual(l.verificar(), (True, []))

    def test_alteracao_e_detectada(self):
        with tempfile.TemporaryDirectory() as d:
            l = Ledger(d, "C1", "analista")
            l.registrar("a", resumo="original")
            l.registrar("b")
            p = Path(d) / "ledger.jsonl"
            p.write_text(p.read_text().replace("original", "trocado"))
            ok, probs = l.verificar()
            self.assertFalse(ok)
            self.assertTrue(any("alterado" in x for x in probs))

    def test_remocao_quebra_elo(self):
        with tempfile.TemporaryDirectory() as d:
            l = Ledger(d, "C1", "analista")
            for i in range(3):
                l.registrar(f"acao{i}")
            p = Path(d) / "ledger.jsonl"
            linhas = p.read_text().splitlines()
            p.write_text("\n".join([linhas[0], linhas[2]]) + "\n")
            ok, probs = l.verificar()
            self.assertFalse(ok)
            self.assertTrue(any("elo quebrado" in x for x in probs))

    def test_artefato_adulterado_em_disco(self):
        with tempfile.TemporaryDirectory() as d:
            l = Ledger(d, "C1", "analista")
            r = l.registrar("coleta", artefato=b"pagina original")
            (Path(d) / "artefatos" / f"{r.artefato_sha256}.bin").write_bytes(b"outra")
            ok, probs = l.verificar()
            self.assertFalse(ok)
            self.assertTrue(any("adulterado" in x for x in probs))


class TestGrafo(unittest.TestCase):
    def grafo(self):
        g = Grafo("C1")
        t1 = Entidade("telefone", "+5531988887777", alvo_primario=True,
                      atributos={"ddd": "31", "assinante": "988887777",
                                 "faixa": "3198888"})
        t2 = Entidade("telefone", "+5531988887779", alvo_primario=True,
                      atributos={"ddd": "31", "assinante": "988887779",
                                 "faixa": "3198888"})
        org = Entidade("organizacao", "11222333000181", rotulo="AURORA")
        g.ligar(t1, org, "telefone_declarado_por", Fonte("cnpj-reverso", "A2"))
        g.ligar(t2, org, "telefone_declarado_por", Fonte("cnpj-reverso", "A2"))
        return g, t1, t2, org

    def test_corroboracao_entre_coletores_aumenta(self):
        g, t1, _, org = self.grafo()
        a = g.arestas[f"{t1.id}|telefone_declarado_por|{org.id}"]
        antes = a.confianca
        g.ligar(t1, org, "telefone_declarado_por", Fonte("rdap", "A2"))
        self.assertGreater(a.confianca, antes)

    def test_repeticao_da_mesma_fonte_nao_aumenta(self):
        g, t1, _, org = self.grafo()
        a = g.arestas[f"{t1.id}|telefone_declarado_por|{org.id}"]
        antes = a.confianca
        for _ in range(5):
            g.ligar(t1, org, "telefone_declarado_por",
                    Fonte("cnpj-reverso", "A2", nota=f"registro {_}"))
        self.assertAlmostEqual(a.confianca, antes, places=4)

    def test_confianca_nunca_atinge_certeza(self):
        self.assertLess(combinar([0.95] * 20), 1.0)

    def test_score_invalido_cai_em_f6(self):
        self.assertEqual(score_admiralty("ZZ"), score_admiralty("F6"))

    def test_aresta_exige_entidades_no_grafo(self):
        g = Grafo("C1")
        with self.assertRaises(KeyError):
            g.add_aresta(Aresta("telefone:x", "pessoa:y", "r", [Fonte("t")]))

    def test_ponte_entre_alvos(self):
        g, t1, t2, org = self.grafo()
        p = pontes(g)
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]["saltos"], 2)
        self.assertEqual(p[0]["intermediarios"][0]["id"], org.id)

    def test_clusters_detectam_ancora_e_sequencia(self):
        g, *_ = self.grafo()
        tipos = {c.tipo for c in detectar_clusters(g)}
        self.assertIn("ancora-organizacao", tipos)
        self.assertIn("numeracao-sequencial", tipos)
        self.assertIn("bloco-numeracao", tipos)

    def test_bloco_e_indicio_mais_fraco_que_ancora(self):
        g, *_ = self.grafo()
        cl = {c.tipo: c.forca for c in detectar_clusters(g)}
        self.assertLess(cl["bloco-numeracao"], cl["ancora-organizacao"])

    def test_serializacao_ida_e_volta(self):
        g, *_ = self.grafo()
        g2 = Grafo.de_dict(json.loads(g.json()))
        self.assertEqual(len(g2.entidades), len(g.entidades))
        self.assertEqual(len(g2.arestas), len(g.arestas))
        self.assertEqual([a.confianca for a in g2.arestas.values()],
                         [a.confianca for a in g.arestas.values()])


class TestIndice(unittest.TestCase):
    def test_e164_do_cadastro(self):
        self.assertEqual(_e164("31", "988887777"), "+5531988887777")
        self.assertEqual(_e164("31", "33334444"), "+553133334444")
        self.assertIsNone(_e164("", "33334444"))
        self.assertIsNone(_e164("31", "123"))


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestColetoresOnlineSemRede(unittest.TestCase):
    """Valida o parsing dos coletores de rede com resposta simulada."""

    def _ctx(self, payload):
        from fio.coletores.base import Contexto
        from fio.evidencia.cache import CacheHTTP
        self._tmp = tempfile.TemporaryDirectory()
        d = Path(self._tmp.name)
        caso = Caso(id="C1", titulo="t", base_legal="pesquisa-academica",
                    finalidade="validacao tecnica dos parsers",
                    responsavel="analista",
                    escopo=["exemplo.com.br", "11222333000181"])
        ctx = Contexto(caso=caso, grafo=Grafo("C1"),
                       ledger=Ledger(d, "C1", "analista"),
                       cache=CacheHTTP(d / "c.sqlite"))
        ctx.http = lambda: type("H", (), {
            "get_json": lambda self, url, nome, cabecalhos=None: (200, payload),
            "get": lambda self, url, nome, cabecalhos=None, aceitar_json=True:
                (200, json.dumps(payload).encode()),
        })()
        return ctx

    def test_rdap_extrai_titular_email_e_telefone(self):
        from fio.coletores.registros import RDAP
        payload = {"handle": "exemplo.com.br", "status": ["active"],
                   "events": [{"eventAction": "registration",
                               "eventDate": "2010-04-01T00:00:00Z"}],
                   "entities": [{"handle": "ACME123", "roles": ["registrant"],
                                 "vcardArray": ["vcard", [
                                     ["version", {}, "text", "4.0"],
                                     ["fn", {}, "text", "ACME COMERCIO LTDA"],
                                     ["email", {}, "text", "TI@Exemplo.com.br"],
                                     ["tel", {}, "text", "tel:+55-31-98888-7777"]]]}]}
        ctx = self._ctx(payload)
        alvo = Entidade("dominio", "exemplo.com.br")
        achados = RDAP().executar(alvo, ctx)
        relacoes = {a.relacao for a in achados}
        self.assertIn("rdap_registrant", relacoes)
        self.assertIn("email_registrado", relacoes)
        self.assertIn("telefone_registrado", relacoes)
        tel = [a for a in achados if a.relacao == "telefone_registrado"][0]
        self.assertEqual(tel.destino.valor, "+5531988887777")
        email = [a for a in achados if a.relacao == "email_registrado"][0]
        self.assertEqual(email.destino.valor, "ti@exemplo.com.br")

    def test_cnpj_api_extrai_telefones_e_qsa(self):
        from fio.coletores.registros import ConsultaCNPJ
        payload = {"razao_social": "AURORA TECH SOLUCOES LTDA",
                   "nome_fantasia": "AURORA", "uf": "MG",
                   "municipio": "BELO HORIZONTE",
                   "ddd_telefone_1": "3133334444",
                   "ddd_telefone_2": "31988887777",
                   "email": "Contato@Auroratech.com.br",
                   "qsa": [{"nome_socio": "Maria Clara Pereira",
                            "qualificacao_socio": "Administrador"}]}
        ctx = self._ctx(payload)
        achados = ConsultaCNPJ().executar(
            Entidade("cnpj", "11222333000181"), ctx)
        tels = {a.destino.valor for a in achados
                if a.relacao == "telefone_declarado"}
        self.assertEqual(tels, {"+553133334444", "+5531988887777"})
        socios = [a.destino.valor for a in achados if a.relacao == "tem_socio"]
        self.assertEqual(socios, ["MARIA CLARA PEREIRA"])

    def test_coletor_fora_de_escopo_e_recusado(self):
        from fio.coletores.registros import RDAP
        ctx = self._ctx({})
        with self.assertRaises(ViolacaoDeEscopo):
            RDAP().executar(Entidade("dominio", "outrodominio.com"), ctx)

    def test_falha_de_rede_nao_derruba_o_caso(self):
        from fio.coletores.registros import RDAP
        ctx = self._ctx(None)
        ctx.http = lambda: type("H", (), {
            "get_json": lambda self, url, nome, cabecalhos=None: (0, None)})()
        self.assertEqual(RDAP().executar(Entidade("dominio", "exemplo.com.br"), ctx), [])

    def test_dorks_cobrem_grafias_alternativas(self):
        from fio.coletores.web import montar_dorks
        d = montar_dorks(Entidade("telefone", "+5531988887777"))
        consulta = d[0]["consulta"]
        self.assertIn('"(31) 98888-7777"', consulta)
        self.assertIn('"+5531988887777"', consulta)
        self.assertTrue(all("urls" in x and "google" in x["urls"] for x in d))
