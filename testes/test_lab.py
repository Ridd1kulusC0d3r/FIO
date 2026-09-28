"""Testes da edicao BR e do lab."""

import json
import os
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from pathlib import Path

from fio.core import documentos as D
from fio.grafo.modelo import Grafo, Entidade, Fonte
from fio.analise.padrao import CoerenciaGeografica, Intermediarios


class TestDocumentos(unittest.TestCase):
    def test_cpf(self):
        self.assertTrue(D.cpf_valido("529.982.247-25"))
        self.assertFalse(D.cpf_valido("529.982.247-24"))
        self.assertFalse(D.cpf_valido("111.111.111-11"))
        self.assertEqual(D.cpf_mascarar("52998224725"), "***.982.247-**")

    def test_regiao_fiscal_pela_mascara_da_receita(self):
        # ***456789** -> 9o digito = 9 -> PR/SC
        self.assertEqual(D.cpf_regiao("***456789**"), ("PR", "SC"))
        self.assertEqual(D.cpf_regiao("52998224725"), ("ES", "RJ"))

    def test_cpf_compativel_com_mascara(self):
        self.assertTrue(D.cpf_compativel_com_mascara("52998224725", "***982247**"))
        self.assertFalse(D.cpf_compativel_com_mascara("52998224725", "***456789**"))

    def test_cnpj_numerico_e_alfanumerico(self):
        self.assertTrue(D.cnpj_valido("11.222.333/0001-81"))
        self.assertTrue(D.cnpj_valido("12.ABC.345/01DE-35"))   # exemplo oficial RFB
        self.assertFalse(D.cnpj_valido("12.ABC.345/01DE-36"))
        self.assertTrue(D.cnpj_alfanumerico("12ABC34501DE35"))
        self.assertEqual(D.cnpj_raiz("12.ABC.345/01DE-35"), "12ABC345")

    def test_mesma_rotina_serve_aos_dois_formatos(self):
        for base in ("112223330001", "ABCDEFGH0001", "1A2B3C4D5E6F"):
            cnpj = base + D.cnpj_dv(base)
            self.assertTrue(D.cnpj_valido(cnpj), cnpj)

    def test_cep_uf(self):
        self.assertEqual(D.cep_uf("30120-010"), "MG")
        self.assertEqual(D.cep_uf("01310-100"), "SP")
        self.assertEqual(D.cep_uf("69301-000"), "RR")
        self.assertEqual(D.cep_uf("73010-000"), "DF")
        self.assertIsNone(D.cep_uf("00000-000"))

    def test_placa_equivalencia(self):
        self.assertEqual(D.placa_equivalentes("ABC-1234"), ["ABC1234", "ABC1C34"])
        self.assertEqual(D.placa_equivalentes("ABC1C34"), ["ABC1C34", "ABC1234"])
        self.assertEqual(D.placa_tipo("AB12345"), None)

    def test_titulo_eleitor_ida_e_volta(self):
        for seq, uf in (("10230045", "02"), ("55512309", "01"), ("98765432", "13")):
            for d1 in range(10):
                for d2 in range(10):
                    t = f"{seq}{uf}{d1}{d2}"
                    if D.titulo_valido(t):
                        self.assertEqual(D.titulo_uf(t), D.UF_TITULO[uf])
                        break

    def test_pis_e_renavam_rejeitam_repetidos(self):
        self.assertFalse(D.pis_valido("11111111111"))
        self.assertFalse(D.renavam_valido("00000000000"))

    def test_extracao_marca_ambiguidade_cpf_telefone(self):
        docs = D.extrair_documentos("contato 52998224725 e CNPJ 11.222.333/0001-81")
        cpf = [d for d in docs if d.tipo == "cpf"][0]
        self.assertTrue(cpf.ambiguo)
        self.assertTrue(any(d.tipo == "cnpj" for d in docs))


class TestAnalisadores(unittest.TestCase):
    def test_intermediario_sem_socio_comum(self):
        g = Grafo("x")
        contab = Entidade("telefone", "+5531900000000", atributos={"uf": "MG"})
        for i in range(5):
            org = Entidade("organizacao", f"org{i}", atributos={"uf": "MG"})
            g.ligar(org, contab, "telefone_declarado", Fonte("t", "A2"))
            g.ligar(org, Entidade("pessoa", f"SOCIO {i}"), "tem_socio", Fonte("t", "A2"))
        Intermediarios().analisar(g)
        self.assertTrue(g.entidades[contab.id].atributos.get("intermediario_provavel"))

    def test_nao_e_intermediario_se_ha_socio_comum(self):
        g = Grafo("x")
        tel = Entidade("telefone", "+5531900000000")
        for i in range(5):
            org = Entidade("organizacao", f"org{i}")
            g.ligar(org, tel, "telefone_declarado", Fonte("t", "A2"))
            g.ligar(org, Entidade("pessoa", "DONO COMUM"), "tem_socio", Fonte("t", "A2"))
        Intermediarios().analisar(g)
        self.assertFalse(g.entidades[tel.id].atributos.get("intermediario_provavel"))

    def test_duas_direcoes_contam_uma_vez(self):
        g = Grafo("x")
        tel = Entidade("telefone", "+5531900000000")
        for i in range(2):   # so 2 empresas, mas com arestas nas duas direcoes
            org = Entidade("organizacao", f"org{i}")
            g.ligar(org, tel, "telefone_declarado", Fonte("t", "A2"))
            g.ligar(tel, org, "telefone_declarado_por", Fonte("t", "A2"))
        Intermediarios().analisar(g)
        self.assertEqual(g.observacoes, [])

    def test_incoerencia_geografica(self):
        g = Grafo("x")
        tel = Entidade("telefone", "+5521988887777", atributos={"uf": "RJ"})
        org = Entidade("organizacao", "o", atributos={"uf": "MG"})
        g.ligar(tel, org, "telefone_declarado_por", Fonte("t", "A2"))
        CoerenciaGeografica().analisar(g)
        self.assertEqual(g.observacoes[0]["tipo"], "incoerencia-geografica")


class TestReceitas(unittest.TestCase):
    def test_receita_generica_detecta_colunas_e_indexa(self):
        from fio.receitas import construir, Indice
        with tempfile.TemporaryDirectory() as d:
            raiz = Path(d)
            csvp = raiz / "cnes.csv"
            csvp.write_text("CO_CNES;NO_FANTASIA;NU_TELEFONE;NO_EMAIL;NU_CNPJ\n"
                            "123;CLINICA X;(31) 3333-4444;a@x.com.br;11222333000181\n",
                            encoding="latin-1")
            meta = construir("cnes", csvp, raiz)
            self.assertEqual(meta["chaves"], "3")
            with Indice(raiz / "indices" / "cnes.sqlite") as idx:
                self.assertEqual(idx.buscar("telefone", "+553133334444")[0]["rotulo"], "CLINICA X")
                self.assertEqual(len(idx.buscar("cnpj", "11222333000181")), 1)
                self.assertEqual(len(idx.meta["sha256"]), 64)

    def test_receita_de_faixa(self):
        from fio.receitas import construir, Indice
        with tempfile.TemporaryDirectory() as d:
            raiz = Path(d)
            p = raiz / "faixas.csv"
            p.write_text("CN,PREFIXO,FAIXA_INICIAL,FAIXA_FINAL,PRESTADORA\n"
                         "31,98888,0000,9999,OPERADORA TESTE\n", encoding="utf-8")
            construir("anatel-faixas", p, raiz)
            with Indice(raiz / "indices" / "anatel-faixas.sqlite") as idx:
                self.assertEqual(idx.faixa("31", "988887777")[0]["prestadora"], "OPERADORA TESTE")
                self.assertEqual(idx.faixa("31", "977777777"), [])


class TestLab(unittest.TestCase):
    def test_sintetico_e_deterministico(self):
        from fio.lab.sintetico import Gerador
        a = Gerador(3).gerar(8)
        b = Gerador(3).gerar(8)
        self.assertEqual(a.telefones, b.telefones)
        self.assertIn("contabilidade", [x["tipo"] for x in a.armadilhas])

    def test_avaliacao_poda_melhora_precisao(self):
        from fio.lab.avaliacao import avaliar
        with tempfile.TemporaryDirectory() as d:
            r = avaliar(Path(d), semente=4, n_grupos=10)
            sem = [c for c in r["combinado"] if c["limiar"] == 0.5 and not c["poda_intermediarios"]][0]
            com = [c for c in r["combinado"] if c["limiar"] == 0.5 and c["poda_intermediarios"]][0]
            self.assertGreaterEqual(com["precisao"], sem["precisao"])
            self.assertGreater(r["pares_verdadeiros"], 0)
            # caso sintetico e forcado offline: nenhuma requisicao de rede
            from fio.lab.experimentos import Registro
            from fio.caso import CasoEmDisco
            exp = Registro(CasoEmDisco("SINT-4", base=Path(d) / "casos").dir).obter(r["experimento"])
            self.assertEqual(exp.metricas["requisicoes"], 0)
            self.assertTrue(exp.parametros["offline"])

    def test_pipeline_reprodutivel(self):
        from fio.lab.avaliacao import avaliar
        from fio.lab import pipeline as pl
        from fio.lab.experimentos import Registro
        from fio.caso import CasoEmDisco
        with tempfile.TemporaryDirectory() as d:
            r = avaliar(Path(d), semente=2, n_grupos=6)
            cd = CasoEmDisco("SINT-2", base=Path(d) / "casos")
            cfg = pl.Config(coletores=["nucleo", "cnpj-reverso"], profundidade=2,
                            offline=True, expandir_escopo=True,
                            extras={"segredos": {"indice_cnpj": str(Path(d) / "cnpj.sqlite")}})
            e2 = pl.executar(cd, "teste", cfg)
            comp = Registro(cd.dir).comparar(r["experimento"], e2.id)
            self.assertTrue(comp["mesmo_resultado"], comp)


class TestBancada(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ["FIO_HOME"] = cls.tmp.name
        from fio.lab.bancada.servidor import servir
        cls.srv = servir(porta=8797, abrir=False, token="t0k", bloquear=False)
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        from fio.lab.bancada.servidor import Estado
        Estado.fila.parar()
        cls.srv.shutdown()
        cls.srv.server_close()
        os.environ.pop("FIO_HOME", None)

    def req(self, path, token="t0k", body=None, host=None):
        r = urllib.request.Request("http://127.0.0.1:8797" + path,
                                   data=json.dumps(body).encode() if body is not None else None,
                                   headers={"Content-Type": "application/json"})
        if token:
            r.add_header("X-FIO-Token", token)
        if host:
            r.add_header("Host", host)
        try:
            with urllib.request.urlopen(r) as x:
                return x.status, json.loads(x.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def test_sem_token_401(self):
        self.assertEqual(self.req("/api/casos", token=None)[0], 401)

    def test_host_estranho_403(self):
        self.assertEqual(self.req("/api/casos", host="atacante.example")[0], 403)

    def test_host_extra_so_quando_declarado(self):
        from fio.lab.bancada.servidor import Estado
        self.assertEqual(self.req("/api/casos", host="abc-8765-colab.googleusercontent.com")[0], 403)
        Estado.hosts_extra = ("googleusercontent.com",)
        try:
            self.assertEqual(self.req("/api/casos", host="abc-8765-colab.googleusercontent.com")[0], 200)
            self.assertEqual(self.req("/api/casos", host="abc-8765-colab.googleusercontent.com",
                                      token=None)[0], 401)
            self.assertEqual(self.req("/api/casos", host="googleusercontent.com.evil.test")[0], 403)
        finally:
            Estado.hosts_extra = ()

    def test_id_malicioso_recusado(self):
        self.assertEqual(self.req("/api/casos/..%2F..%2Fetc/grafo")[0], 400)

    def test_fluxo_caso(self):
        s, _ = self.req("/api/casos", body={
            "id": "T1", "titulo": "t", "base_legal": "pesquisa-academica",
            "finalidade": "teste automatizado da bancada", "responsavel": "ci",
            "escopo": ["+5531988887777"]})
        self.assertEqual(s, 201)
        s, _ = self.req("/api/casos/T1/alvos", body={"tipo": "telefone", "valor": "31988887777"})
        self.assertEqual(s, 201)
        s, j = self.req("/api/casos/T1/pipeline", body={"offline": True, "coletores": ["nucleo"]})
        self.assertEqual(s, 202)
        for _ in range(50):
            _, t = self.req(f"/api/tarefas/{j['tarefa']}")
            if t["estado"] in ("concluida", "falhou"):
                break
            time.sleep(0.2)
        self.assertEqual(t["estado"], "concluida", t.get("erro"))
        _, g = self.req("/api/casos/T1/grafo")
        self.assertIn("telefone:+5531988887777", [e["id"] for e in g["entidades"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestIndiceZip(unittest.TestCase):
    def test_indice_da_receita_le_zip_sem_descompactar(self):
        import zipfile
        from fio.indice import construir, IndiceCNPJ
        demo = Path(__file__).resolve().parents[1] / "fio" / "dados_demo"
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for nome, interno in (("Estabelecimentos0", "K.ESTABELE"), ("Empresas0", "K.EMPRECSV"),
                                  ("Socios0", "K.SOCIOCSV")):
                with zipfile.ZipFile(d / f"{nome}.zip", "w") as z:
                    z.write(demo / f"{nome}.csv", interno)
            c = construir(d, d / "i.sqlite", log=lambda s: None)
            self.assertEqual(c["estabelecimentos"], 3)
            with IndiceCNPJ(d / "i.sqlite") as idx:
                self.assertEqual(idx.por_telefone("+5531988887777")[0]["cnpj"],
                                 "11222333000181")
