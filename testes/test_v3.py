"""Testes dos recursos da 3.0: baseline, canarios, lote, reuso de linha,
claims, manifesto, calibracao, documentos financeiros e coletores passivos."""

import contextlib
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from fio.analise import ANALISADORES
from fio.analise.lote import parse_data
from fio.coletores import REGISTRO, Contexto
from fio.coletores.baseline import similaridade, julgar, impossivel
from fio.coletores.passivos import nomes_do_certificado
from fio.core import financeiro as fin
from fio.core.documentos import extrair_documentos, analisar
from fio.diagnostico import checar_canario, carregar_fontes, sondar
from fio.evidencia import manifesto
from fio.evidencia.cache import CacheHTTP
from fio.evidencia.ledger import Ledger
from fio.grafo import claims as cl
from fio.grafo.modelo import Grafo, Entidade, Fonte
from fio.lab.calibracao import ajustar_isotonica, tabela_confiabilidade, ece
from fio.politica import Caso


# ---------------------------------------------------------------- baseline
class TestBaseline(unittest.TestCase):
    VAZIA = b"<html><body><h1>Nenhum resultado</h1><p>Busca 1234 em 05/06/2024</p></body></html>"

    def test_pagina_padrao_com_numeros_diferentes_e_igual(self):
        outra = self.VAZIA.replace(b"1234", b"9876").replace(b"05/06", b"11/12")
        self.assertGreaterEqual(similaridade(self.VAZIA, outra), 0.99)

    def test_conteudos_distintos_sao_diferentes(self):
        real = (b"<html><body><h1>Aurora Tech Solucoes</h1><p>Fale conosco "
                b"pelo telefone da matriz em Belo Horizonte, atendimento de "
                b"segunda a sexta</p></body></html>")
        self.assertLess(similaridade(real, self.VAZIA), 0.3)

    def test_julgar_descarta_soft404(self):
        v = julgar(200, self.VAZIA, 200, self.VAZIA.replace(b"1234", b"1"))
        self.assertTrue(v.soft404)

    def test_julgar_aceita_quando_a_fonte_distingue(self):
        v = julgar(200, b"<p>dados reais da empresa ltda</p>", 404, b"{}")
        self.assertFalse(v.soft404)

    def test_julgar_rejeita_erro_http(self):
        self.assertTrue(julgar(500, b"x", 200, b"y").soft404)
        self.assertTrue(julgar(0, b"", 200, b"y").soft404)

    def test_sem_baseline_nao_descarta_mas_avisa(self):
        v = julgar(200, b"<p>algo</p>", 0, b"")
        self.assertFalse(v.soft404)
        self.assertIn("nao verificada", v.motivo)

    def test_impossivel_por_tipo(self):
        self.assertTrue(impossivel("telefone").startswith("+55"))
        self.assertIn("invalid", impossivel("dominio"))

    def test_get_diferencial_registra_veredito_no_ledger(self):
        with _sessao() as ctx:
            cli = ctx.http()
            with mock.patch.object(type(cli), "get", side_effect=[
                    (200, self.VAZIA), (200, self.VAZIA)]):
                st, _, v = cli.get_diferencial("http://a/x", "http://a/y", "t")
            self.assertTrue(v.soft404)
            acoes = [r.acao for r in ctx.ledger.registros()]
            self.assertIn("coleta.baseline", acoes)


@contextlib.contextmanager
def _sessao(escopo=("alvo.test",)):
    """Contexto de coleta numa pasta temporaria; fecha o SQLite antes de
    apagar (no Windows, arquivo aberto nao pode ser removido)."""
    with tempfile.TemporaryDirectory() as t:
        ctx = _ctx(Path(t), escopo)
        try:
            yield ctx
        finally:
            ctx.cache.fechar()


def _ctx(d: Path, escopo=("alvo.test",)):
    caso = Caso(id="T", titulo="t", base_legal="pesquisa-academica",
                finalidade="teste automatizado dos recursos da 3.0",
                responsavel="ci", escopo=list(escopo))
    return Contexto(caso=caso, grafo=Grafo("T"), ledger=Ledger(d, "T", "ci"),
                    cache=CacheHTTP(d / "c.sqlite"), intervalo=0)


# ---------------------------------------------------------------- canarios
class TestCanarios(unittest.TestCase):
    def test_registro_declarativo_carrega(self):
        fontes = carregar_fontes()
        self.assertGreaterEqual(len(fontes), 10)
        for f in fontes:
            self.assertTrue(f["url"].startswith("https://"), f)
            self.assertIn("coletor", f)
        self.assertIn("crtsh", {f["coletor"] for f in fontes})

    def test_canario_json_ok_e_quebrado(self):
        corpo = json.dumps({"razao_social": "BANCO DO BRASIL SA"}).encode()
        self.assertEqual(checar_canario(
            corpo, {"json_chave": "razao_social", "contem": "banco do brasil"})[0], True)
        ok, motivo = checar_canario(corpo, {"json_chave": "cnpj"})
        self.assertFalse(ok)
        self.assertIn("formato mudou", motivo)

    def test_canario_igual_e_lista(self):
        corpo = json.dumps([{"ibge": "3550308"}]).encode()
        self.assertTrue(checar_canario(corpo, {"json_chave": "ibge", "igual": "3550308"})[0])
        self.assertFalse(checar_canario(corpo, {"json_chave": "ibge", "igual": "1"})[0])

    def test_sem_canario_e_none(self):
        self.assertIsNone(checar_canario(b"x", {})[0])

    def test_canario_nao_json(self):
        self.assertFalse(checar_canario(b"<html>", {"json_chave": "a"})[0])

    def test_fonte_instavel_nao_reprova_e_tenta_de_novo(self):
        chamadas = []

        def falha(*a, **k):
            chamadas.append(1)
            raise OSError("reset")
        fontes = [{"coletor": "x", "nome": "Fonte X", "url": "https://x.test/",
                   "instavel": True, "canario": {}},
                  {"coletor": "y", "nome": "Fonte Y", "url": "https://y.test/",
                   "canario": {}}]
        with mock.patch("fio.diagnostico.urllib.request.urlopen", side_effect=falha):
            r = sondar({}, fontes=fontes, espera=0)
        self.assertEqual(len(chamadas), 4)           # 2 tentativas por fonte
        self.assertIsNone(r[0]["ok"])                # instavel: nao conta como falha
        self.assertIn("instavel", r[0]["dica"])
        self.assertFalse(r[1]["ok"])                 # estavel: falha de verdade

    def test_sondar_marca_falha_de_contrato(self):
        class Resp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self, n=-1): return b'{"outra_coisa": 1}'
        fontes = [{"coletor": "x", "nome": "Fonte X", "url": "https://x.test/",
                   "canario": {"json_chave": "razao_social"}}]
        with mock.patch("fio.diagnostico.urllib.request.urlopen", return_value=Resp()):
            r = sondar({}, fontes=fontes, espera=0)[0]
        self.assertFalse(r["ok"])
        self.assertFalse(r["contrato"])
        self.assertIn("contrato quebrado", r["dica"])


# --------------------------------------------------------- analisadores
def _org(g, cnpj, inicio, situacao="02", raiz=None):
    e = Entidade("organizacao", cnpj, atributos={
        "cnpj_basico": raiz or cnpj[:8], "inicio_atividade": inicio,
        "situacao_cadastral": situacao})
    return g.add_entidade(e)


def _liga(g, a, b, rel="telefone_declarado_por"):
    g.add_aresta(__import__("fio.grafo.modelo", fromlist=["Aresta"]).Aresta(
        a.id, b.id, rel, [Fonte("t", "B2")]))


class TestLote(unittest.TestCase):
    def test_datas(self):
        import datetime as dt
        self.assertEqual(parse_data("20230301"), dt.date(2023, 3, 1))
        self.assertEqual(parse_data("01/03/2023"), dt.date(2023, 3, 1))
        self.assertEqual(parse_data("2023-03-01"), dt.date(2023, 3, 1))
        self.assertIsNone(parse_data("lixo"))
        self.assertIsNone(parse_data(None))

    def _rede(self, datas, raizes_distintas=True):
        g = Grafo("T")
        tel = g.add_entidade(Entidade("telefone", "+5531999990000"))
        for i, d in enumerate(datas):
            o = _org(g, f"{10000000 + i}000100", d)
            _liga(g, tel, o)
        return g

    def test_detecta_lote_de_quatro_em_doze_dias(self):
        g = self._rede(["20230301", "20230305", "20230309", "20230313"])
        n = ANALISADORES["lote-de-registro"].analisar(g)
        self.assertEqual(n, 1)
        self.assertEqual(g.observacoes[0]["tipo"], "lote-de-registro")

    def test_nao_dispara_com_aberturas_espalhadas(self):
        g = self._rede(["20100101", "20130101", "20160101", "20190101"])
        self.assertEqual(ANALISADORES["lote-de-registro"].analisar(g), 0)

    def test_nao_dispara_com_menos_de_tres(self):
        g = self._rede(["20230301", "20230302"])
        self.assertEqual(ANALISADORES["lote-de-registro"].analisar(g), 0)

    def test_filiais_da_mesma_raiz_contam_uma_vez(self):
        g = Grafo("T")
        tel = g.add_entidade(Entidade("telefone", "+5531999990000"))
        for i in range(5):
            o = _org(g, f"11111111000{i}00", "20230301", raiz="11111111")
            _liga(g, tel, o)
        self.assertEqual(ANALISADORES["lote-de-registro"].analisar(g), 0)

    def test_ponte_com_lote_sobe_para_atencao(self):
        g = self._rede(["20230301", "20230305", "20230309", "20230313"])
        g.entidades["telefone:+5531999990000"].atributos["intermediario_provavel"] = True
        ANALISADORES["lote-de-registro"].analisar(g)
        self.assertEqual(g.observacoes[0]["gravidade"], "atencao")

    def test_mesma_rede_nao_e_reportada_duas_vezes(self):
        g = self._rede(["20230301", "20230305", "20230309"])
        cep = g.add_entidade(Entidade("cep", "30120010"))
        for o in g.por_tipo("organizacao"):
            _liga(g, o, cep, "endereco_no_cep")
        ANALISADORES["lote-de-registro"].analisar(g)
        self.assertEqual(len([o for o in g.observacoes
                              if o["tipo"] == "lote-de-registro"]), 1)


class TestReusoDeLinha(unittest.TestCase):
    def _g(self, sit_a, sit_b, ini_a="20150101", ini_b="20220101"):
        g = Grafo("T")
        tel = g.add_entidade(Entidade("telefone", "+5531999990000"))
        _liga(g, tel, _org(g, "11111111000100", ini_a, sit_a))
        _liga(g, tel, _org(g, "22222222000100", ini_b, sit_b))
        return g

    def test_baixada_mais_ativa_vira_observacao(self):
        g = self._g("08", "02")
        self.assertEqual(ANALISADORES["reuso-de-linha"].analisar(g), 1)
        o = g.observacoes[0]
        self.assertEqual(o["tipo"], "linha-possivelmente-reciclada")
        self.assertIn("abriu depois", o["texto"])
        self.assertTrue(g.entidades["telefone:+5531999990000"]
                        .atributos["linha_reciclada_provavel"])

    def test_duas_ativas_nao_dispara(self):
        self.assertEqual(ANALISADORES["reuso-de-linha"].analisar(self._g("02", "02")), 0)

    def test_duas_baixadas_nao_dispara(self):
        self.assertEqual(ANALISADORES["reuso-de-linha"].analisar(self._g("08", "08")), 0)


# --------------------------------------------------------------- claims
class TestClaims(unittest.TestCase):
    def _g(self):
        g = Grafo("T")
        t = g.add_entidade(Entidade("telefone", "+5531999990000"))
        o = g.add_entidade(Entidade("organizacao", "11111111000100"))
        _liga(g, t, o)
        g.arestas[next(iter(g.arestas))].fontes = [Fonte("a", "A1"), Fonte("b", "B2")]
        g.observar("x", "achado de teste", [t.id], "info", "an")
        return g

    def test_claims_citam_evidencia_e_validam(self):
        g = self._g()
        c = cl.derivar(g)
        self.assertEqual({x.tipo for x in c}, {"vinculo", "observacao"})
        self.assertEqual(cl.validar(c, g), [])
        v = next(x for x in c if x.tipo == "vinculo")
        self.assertEqual(v.coletores, ["a", "b"])
        self.assertGreater(v.confianca, 0.5)

    def test_claim_sem_evidencia_e_invalido(self):
        g = self._g()
        c = cl.derivar(g)
        c[0].evidencias = []
        self.assertTrue(any("sem evidencia" in p for p in cl.validar(c, g)))

    def test_evidencia_inexistente_e_invalida(self):
        g = self._g()
        c = cl.derivar(g)
        c[0].evidencias = ["nao|existe|mesmo"]
        self.assertTrue(any("inexistente" in p for p in cl.validar(c, g)))

    def test_limiar_filtra_vinculo_fraco(self):
        g = Grafo("T")
        t = g.add_entidade(Entidade("telefone", "+5531999990000"))
        o = g.add_entidade(Entidade("organizacao", "11111111000100"))
        g.add_aresta(__import__("fio.grafo.modelo", fromlist=["Aresta"]).Aresta(
            t.id, o.id, "r", [Fonte("a", "E5")]))
        self.assertEqual(cl.derivar(g, 0.5), [])

    def test_ids_estaveis(self):
        g = self._g()
        self.assertEqual([c.id for c in cl.derivar(g)], [c.id for c in cl.derivar(g)])


# ------------------------------------------------------------- manifesto
class TestManifesto(unittest.TestCase):
    def _caso(self, d):
        led = Ledger(d, "T", "ci")
        led.registrar("caso.aberto", alvo="T", artefato=b"bruto")
        (d / "grafo.json").write_text('{"a":1}', encoding="utf-8")
        (d / "caso.json").write_text('{"id":"T"}', encoding="utf-8")
        return led

    def test_gerar_e_verificar(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            self._caso(d)
            manifesto.gravar(d, "T")
            ok, probs = manifesto.verificar(d)
            self.assertTrue(ok, probs)

    def test_ledger_pode_crescer_depois_do_manifesto(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            led = self._caso(d)
            manifesto.gravar(d, "T")
            led.registrar("coleta", alvo="x")
            ok, probs = manifesto.verificar(d)
            self.assertTrue(ok, probs)

    def test_peca_alterada_e_detectada(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            self._caso(d)
            manifesto.gravar(d, "T")
            (d / "grafo.json").write_text('{"a":2}', encoding="utf-8")
            ok, probs = manifesto.verificar(d)
            self.assertFalse(ok)
            self.assertTrue(any("grafo.json" in p for p in probs))

    def test_manifesto_adulterado_e_detectado(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            self._caso(d)
            manifesto.gravar(d, "T")
            m = json.loads((d / "manifesto.json").read_text())
            m["pecas"]["grafo.json"]["sha256"] = "0" * 64
            (d / "manifesto.json").write_text(json.dumps(m))
            ok, probs = manifesto.verificar(d)
            self.assertFalse(ok)
            self.assertTrue(any("proprio manifesto" in p for p in probs))

    def test_sem_manifesto(self):
        with tempfile.TemporaryDirectory() as t:
            ok, probs = manifesto.verificar(Path(t))
            self.assertFalse(ok)

    def test_ledger_reescrito_e_detectado(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            self._caso(d)
            manifesto.gravar(d, "T")
            linhas = (d / "ledger.jsonl").read_text().splitlines()
            r = json.loads(linhas[0])
            r["resumo"] = "adulterado"
            linhas[0] = json.dumps(r)
            (d / "ledger.jsonl").write_text("\n".join(linhas) + "\n")
            ok, _ = manifesto.verificar(d)
            self.assertFalse(ok)


# ------------------------------------------------------------ calibracao
class TestCalibracao(unittest.TestCase):
    def test_isotonica_e_monotona(self):
        pares = [(0.2, False), (0.2, True), (0.5, False), (0.5, False),
                 (0.8, True), (0.9, True), (0.6, True), (0.6, False)]
        c = ajustar_isotonica(pares)
        self.assertEqual(c.valores, sorted(c.valores))
        self.assertEqual(c.aplicar(0.95), c.valores[-1])

    def test_isotonica_vazia_e_identidade(self):
        self.assertEqual(ajustar_isotonica([]).aplicar(0.42), 0.42)

    def test_ece_zero_quando_calibrado(self):
        pares = [(0.5, True), (0.5, False)] * 10
        self.assertEqual(ece(tabela_confiabilidade(pares)), 0.0)

    def test_ece_alto_quando_descalibrado(self):
        pares = [(0.9, False)] * 10
        self.assertGreater(ece(tabela_confiabilidade(pares)), 0.8)


# ------------------------------------------------------- financeiro / docs
class TestFinanceiro(unittest.TestCase):
    LINHA = fin.montar_linha_digitavel("001", 9000, 12345, "1234567890123456789012345")

    def test_boleto_gerado_e_valido_e_dados(self):
        self.assertTrue(fin.boleto_valido(self.LINHA))
        d = fin.boleto_dados(self.LINHA)
        self.assertEqual(d["banco"], "001")
        self.assertEqual(d["valor"], 123.45)
        # fator 9000 = 29/05/2022 (calendario do boleto)
        self.assertIn("2022-05-29", d["vencimentos_possiveis"])

    def test_boleto_com_digito_trocado_e_invalido(self):
        for pos in (3, 12, 25, 40):
            ruim = self.LINHA[:pos] + str((int(self.LINHA[pos]) + 1) % 10) + self.LINHA[pos + 1:]
            self.assertFalse(fin.boleto_valido(ruim), pos)

    def test_boleto_extraido_de_texto_formatado_sem_virar_cnpj(self):
        l = self.LINHA
        fmt = f"{l[:5]}.{l[5:10]} {l[10:15]}.{l[15:21]} {l[21:26]}.{l[26:32]} {l[32]} {l[33:]}"
        docs = extrair_documentos(f"Pague {fmt} ate sexta")
        self.assertEqual([d.tipo for d in docs], ["boleto"])

    def test_pix_classifica_chaves(self):
        c = fin.classificar_chave_pix
        self.assertEqual(c("123e4567-e89b-42d3-a456-426614174000"), "evp")
        self.assertEqual(c("+5531988887777"), "telefone")
        self.assertEqual(c("fulano@exemplo.com.br"), "email")
        self.assertEqual(c("11222333000181"), "cnpj")
        self.assertEqual(c("529.982.247-25"), "cpf")
        self.assertIsNone(c("texto qualquer"))
        self.assertIsNone(c("12345678900"))      # CPF invalido

    def test_evp_extraido_de_texto(self):
        docs = extrair_documentos("chave: 123e4567-e89b-42d3-a456-426614174000.")
        self.assertIn("pix-evp", [d.tipo for d in docs])

    def test_cns_definitivo_e_provisorio(self):
        # gera CNS provisorio valido: soma ponderada de 15 digitos % 11 == 0
        base = "7000000000000"
        for a in range(10):
            for b in range(10):
                cand = base + f"{a}{b}"
                if sum(int(cand[i]) * (15 - i) for i in range(15)) % 11 == 0:
                    self.assertTrue(fin.cns_valido(cand))
                    self.assertFalse(fin.cns_valido(cand[:-1] + str((int(cand[-1]) + 1) % 10)))
                    return
        self.fail("nenhum candidato")

    def test_cnh_rejeita_repetidos_e_tamanho(self):
        self.assertFalse(fin.cnh_valida("11111111111"))
        self.assertFalse(fin.cnh_valida("123"))

    def test_analisar_novos_tipos(self):
        self.assertTrue(analisar("boleto", self.LINHA).valido)
        self.assertFalse(analisar("pix-evp", "nao-e-uuid").valido)


# ------------------------------------------------------ coletores passivos
class TestPassivos(unittest.TestCase):
    CRT = [
        {"name_value": "www.exemplo.com.br\nexemplo.com.br", "issuer_name": "LE",
         "not_before": "2024-03-01T00:00:00"},
        {"name_value": "*.exemplo.com.br\nloja.exemplo.com.br\nlixo@exemplo.com.br",
         "issuer_name": "LE", "not_before": "2023-01-10T00:00:00"},
        {"name_value": "outro.com\nnao-relacionado.com", "issuer_name": "X",
         "not_before": "2024-01-01T00:00:00"},
        "invalido",
    ]

    def test_nomes_do_certificado_filtra_e_limpa(self):
        n = nomes_do_certificado(self.CRT, "exemplo.com.br")
        self.assertEqual(sorted(n), ["exemplo.com.br", "loja.exemplo.com.br",
                                     "www.exemplo.com.br"])
        # o curinga *.exemplo.com.br soma ao dominio e usa a data mais antiga
        self.assertEqual(n["exemplo.com.br"]["inicio"][:10], "2023-01-10")
        self.assertEqual(n["exemplo.com.br"]["certificados"], 2)

    def test_crtsh_coletor(self):
        with _sessao(("exemplo.com.br",)) as ctx:
            alvo = Entidade("dominio", "exemplo.com.br")
            with mock.patch("fio.coletores.base.ClienteHTTP.get_json",
                            return_value=(200, self.CRT)):
                achados = REGISTRO["crtsh"].executar(alvo, ctx)
            dests = sorted(a.destino.valor for a in achados)
            self.assertEqual(dests, ["loja.exemplo.com.br", "www.exemplo.com.br"])
            self.assertTrue(all(a.relacao == "nome_em_certificado" for a in achados))
            self.assertEqual(alvo.atributos["crtsh_primeiro_certificado"][:10], "2023-01-10")

    def test_wayback_coletor(self):
        resp = {"archived_snapshots": {"closest": {
            "available": True, "timestamp": "20030415120000",
            "url": "http://web.archive.org/web/20030415120000/http://exemplo.com.br/"}}}
        with _sessao(("exemplo.com.br",)) as ctx:
            alvo = Entidade("dominio", "exemplo.com.br")
            with mock.patch("fio.coletores.base.ClienteHTTP.get_json",
                            return_value=(200, resp)):
                achados = REGISTRO["wayback"].executar(alvo, ctx)
            self.assertEqual(len(achados), 1)
            self.assertEqual(alvo.atributos["wayback_primeiro"], "20030415120000")

    def test_wayback_sem_captura(self):
        with _sessao(("novo.test",)) as ctx:
            alvo = Entidade("dominio", "novo.test")
            with mock.patch("fio.coletores.base.ClienteHTTP.get_json",
                            return_value=(200, {"archived_snapshots": {}})):
                self.assertEqual(REGISTRO["wayback"].executar(alvo, ctx), [])
            self.assertIsNone(alvo.atributos["wayback_primeiro"])

    def test_coletores_passivos_exigem_escopo(self):
        from fio.politica import ViolacaoDeEscopo
        with _sessao(("outro.test",)) as ctx:
            with self.assertRaises(ViolacaoDeEscopo):
                REGISTRO["crtsh"].executar(Entidade("dominio", "exemplo.com.br"), ctx)


# ------------------------------------------------- mundo sintetico (fachada)
class TestMundoFachada(unittest.TestCase):
    def test_gerador_planta_rede_de_fachada_e_o_lote_a_encontra(self):
        from fio.lab.avaliacao import executar_mundo
        with tempfile.TemporaryDirectory() as d:
            mundo, g, _, _, _ = executar_mundo(Path(d), 1, 12)
            tipos = [a["tipo"] for a in mundo.armadilhas]
            self.assertIn("rede-fachada", tipos)
            fach = next(a for a in mundo.armadilhas if a["tipo"] == "rede-fachada")
            lotes = [o for o in g.observacoes if o["tipo"] == "lote-de-registro"]
            self.assertTrue(any(f"telefone:{fach['telefone']}" in o["entidades"]
                                for o in lotes),
                            "o analisador deveria achar a rede plantada")
            # e nenhum lote fora da rede plantada (sem falso positivo no mundo)
            self.assertEqual(len(lotes), 1)


# ------------------------------------------ Receita inacessivel (Colab)
class TestReceitaInacessivel(unittest.TestCase):
    """O Colab nao alcanca dadosabertos.rfb.gov.br (timeout de conexao): em vez
    de sondar mes a mes por 10 minutos, falha na hora com o que fazer."""

    def _tempo_esgotado(self, chamadas):
        def falso(url, timeout=60):
            chamadas.append(url)
            raise RuntimeError("urllib: URLError: <urlopen error timed out>; "
                               "curl: RuntimeError: curl: (28) Failed to connect to "
                               "dadosabertos.rfb.gov.br port 443 after 15002 ms")
        return falso

    def test_timeout_na_raiz_nao_sonda_meses(self):
        from fio import receita_download as rd
        chamadas = []
        with mock.patch.object(rd, "_get", self._tempo_esgotado(chamadas)):
            with self.assertRaises(rd.ReceitaInacessivel) as cm:
                rd.descobrir("https://exemplo.test/cnpj/", log=lambda s: None)
        self.assertEqual(len(chamadas), 1)            # so a raiz, nenhum mes
        msg = str(cm.exception)
        self.assertIn("bloquear faixas de IP de nuvem", msg)
        self.assertIn("fio indice baixar", msg)

    def test_timeout_com_mes_informado_tambem_falha_rapido(self):
        from fio import receita_download as rd
        chamadas = []
        with mock.patch.object(rd, "_get", self._tempo_esgotado(chamadas)):
            with self.assertRaises(rd.ReceitaInacessivel):
                rd.descobrir("https://exemplo.test/cnpj/", mes="2026-08", log=lambda s: None)
        self.assertEqual(len(chamadas), 1)

    def test_reset_de_conexao_continua_sondando_meses(self):
        from fio import receita_download as rd
        chamadas = []

        def falso(url, timeout=60):
            chamadas.append(url)
            if url.endswith("/cnpj/"):
                raise RuntimeError("urllib: ConnectionResetError: Connection reset by peer")
            return '<a href="Empresas0.zip">x</a>' if url.endswith("-07/") else "<html></html>"
        with mock.patch.object(rd, "_get", falso):
            b, m, arqs = rd.descobrir("https://exemplo.test/cnpj/", log=lambda s: None)
        self.assertEqual(arqs, ["Empresas0.zip"])
        self.assertGreater(len(chamadas), 1)          # reset NAO e falta de rota

    def test_sem_rota_classifica_mensagens(self):
        from fio.receita_download import _sem_rota
        self.assertTrue(_sem_rota("curl: (28) Failed to connect ... Timeout was reached"))
        self.assertTrue(_sem_rota("Network is unreachable"))
        self.assertFalse(_sem_rota("HTTP Error 404: Not Found"))
        self.assertFalse(_sem_rota("Connection reset by peer"))


# ------------------------------------------------- coleta em paralelo
class TestColetaParalela(unittest.TestCase):
    """Fontes de rede de um mesmo alvo rodam juntas; o resultado nao muda."""

    def _montar(self, tmp, n=4, espera=0.4):
        from fio.coletores.base import Coletor, Achado, REGISTRO
        from fio.caso import CasoEmDisco
        from fio.politica import Caso

        class Lenta(Coletor):
            requer_rede = True
            tipos_alvo = ("dominio",)
            admiralty = "B2"

            def coletar(self, alvo, ctx):
                time.sleep(espera)
                return [Achado(alvo, "rel", Entidade("dominio", f"{self.nome}.exemplo.test"),
                               Fonte(self.nome, "B2"))]

        nomes = []
        for i in range(n):
            c = type(f"Lenta{i}", (Lenta,), {"nome": f"lenta{i}"})()
            REGISTRO[c.nome] = c
            nomes.append(c.nome)
        cd = CasoEmDisco("PAR", base=Path(tmp))
        cd.criar(Caso(id="PAR", titulo="paralelo", base_legal="pesquisa-academica",
                      finalidade="medir o ganho da coleta em paralelo",
                      responsavel="ci", escopo=["exemplo.test"]), "ci")
        cd.add_alvo(Entidade("dominio", "exemplo.test"), "ci")
        return cd, nomes

    def test_paralelo_e_mais_rapido_e_igual(self):
        from fio.motor import investigar
        from fio.coletores.base import REGISTRO
        with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
            cd1, nomes = self._montar(t1)
            t = time.perf_counter()
            investigar(cd1, "ci", coletores=nomes, paralelo=1, intervalo=0)
            seq = time.perf_counter() - t
            cd2, _ = self._montar(t2)
            t = time.perf_counter()
            investigar(cd2, "ci", coletores=nomes, paralelo=4, intervalo=0)
            par = time.perf_counter() - t
            for n in nomes:
                REGISTRO.pop(n, None)
            self.assertGreaterEqual(seq, 1.5)           # 4 x 0,4 s em sequencia
            self.assertLess(par, seq * 0.6)             # em paralelo: ~0,4 s
            g1, g2 = cd1.grafo(), cd2.grafo()
            self.assertEqual(sorted(g1.entidades), sorted(g2.entidades))
            self.assertEqual(sorted(g1.arestas), sorted(g2.arestas))
            # a cadeia de custodia sobrevive a gravacoes concorrentes
            for cd in (cd1, cd2):
                ok, probs = cd.ledger().verificar()
                self.assertTrue(ok, probs)

    def test_orcamento_para_de_abrir_consultas(self):
        from fio.motor import investigar
        from fio.coletores.base import REGISTRO
        with tempfile.TemporaryDirectory() as t:
            cd, nomes = self._montar(t, n=2, espera=0.3)
            # segundo alvo para o orcamento (0 s) cortar antes de consulta-lo
            cd.add_alvo(Entidade("dominio", "outro.exemplo.test"), "ci")
            investigar(cd, "ci", coletores=nomes, paralelo=1, intervalo=0, orcamento=0.0)
            for n in nomes:
                REGISTRO.pop(n, None)
            acoes = [r.acao for r in cd.ledger().registros()]
            self.assertIn("orcamento.esgotado", acoes)


class TestLedgerRapido(unittest.TestCase):
    def test_gravar_nao_reler_o_arquivo_inteiro(self):
        with tempfile.TemporaryDirectory() as t:
            led = Ledger(Path(t), "T", "ci")
            for i in range(300):
                led.registrar("a", alvo=str(i), metadados={"x": "y" * 50})
            ini = time.perf_counter()
            for i in range(300):
                led.registrar("b", alvo=str(i))
            dt = time.perf_counter() - ini
            self.assertLess(dt, 1.5)                    # antes: O(n^2), varios segundos
            ok, probs = led.verificar()
            self.assertTrue(ok, probs)
            self.assertEqual(len(led), 600)

    def test_instancias_diferentes_encadeiam_corretamente(self):
        with tempfile.TemporaryDirectory() as t:
            a, b = Ledger(Path(t), "T", "ci"), Ledger(Path(t), "T", "ci")
            for i in range(20):
                (a if i % 2 else b).registrar("x", alvo=str(i))
            ok, probs = a.verificar()
            self.assertTrue(ok, probs)

    def test_registro_longo_com_ultima_linha_maior_que_o_bloco(self):
        with tempfile.TemporaryDirectory() as t:
            led = Ledger(Path(t), "T", "ci")
            led.registrar("curto")
            led.registrar("longo", metadados={"lixo": "z" * 30000})
            r = led.registrar("depois")
            self.assertEqual(r.seq, 3)
            self.assertTrue(led.verificar()[0])


class TestGrafoRapido(unittest.TestCase):
    def test_vizinhos_e_caminho_com_cache_invalidam_ao_crescer(self):
        from fio.grafo.modelo import Aresta
        g = Grafo("T")
        ents = [g.add_entidade(Entidade("telefone", f"+55319999{i:04d}")) for i in range(5)]
        for a, b in zip(ents, ents[1:]):
            g.add_aresta(Aresta(a.id, b.id, "r", [Fonte("t", "B2")]))
        self.assertEqual(len(g.vizinhos(ents[2].id)), 2)
        self.assertEqual(g.caminho(ents[0].id, ents[4].id),
                         [e.id for e in ents])
        # atalho: o cache precisa perceber a aresta nova
        g.add_aresta(Aresta(ents[0].id, ents[4].id, "atalho", [Fonte("t", "B2")]))
        self.assertEqual(len(g.vizinhos(ents[0].id)), 2)
        self.assertEqual(g.caminho(ents[0].id, ents[4].id), [ents[0].id, ents[4].id])
        self.assertIsNone(g.caminho(ents[0].id, "telefone:inexistente"))


if __name__ == "__main__":
    unittest.main()
