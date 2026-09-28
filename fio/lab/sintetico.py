"""Gerador de mundos ficticios com gabarito.

Heuristica de vinculo sem medicao e palpite com grafico bonito. Este modulo
fabrica um "Brasil de mentira" -- empresas, socios, linhas, dominios --
em que a resposta certa e conhecida, e planta as armadilhas que derrubam
analise de vinculo na vida real:

  contabilidade   um telefone de escritorio contabil declarado como segunda
                  linha por empresas de grupos diferentes (hub falso)
  bloco-isca      linhas de grupos distintos no mesmo bloco de numeracao
  sequencia-isca  linhas de grupos distintos numericamente contiguas
  gmail           grupos que usam provedor gratuito (dominio nao liga)
  socio-oculto    empresas do mesmo grupo com raizes de CNPJ diferentes,
                  ligadas apenas por socio em comum
  cnpj-alfa       parte das empresas novas ja no formato alfanumerico

Seguranca: numeros gerados podem coincidir com linhas reais. Por isso todo
caso sintetico e forcado a modo offline -- nenhum numero ficticio sai da
maquina -- e os dominios usam o TLD reservado .test (RFC 2606).
"""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path

from ..core.documentos import cnpj_dv, REGIAO_FISCAL_CPF
from ..core.anatel import DDD_INFO

NOMES = ["ANA", "BRUNO", "CARLA", "DIEGO", "ELISA", "FABIO", "GISELE", "HUGO",
         "ISABELA", "JONAS", "KARINA", "LUCAS", "MARINA", "NELSON", "OTAVIO",
         "PRISCILA", "RAFAEL", "SABRINA", "TIAGO", "VANESSA", "WAGNER", "YARA"]
SOBRENOMES = ["ALMEIDA", "BARBOSA", "CARDOSO", "DUARTE", "ESTEVES", "FARIAS",
              "GUEDES", "HOLANDA", "IRIAS", "JARDIM", "LACERDA", "MOREIRA",
              "NOGUEIRA", "PAIVA", "QUEIROZ", "RIBAS", "SEIXAS", "TAVARES",
              "VALADARES", "XAVIER"]
RAMOS = ["LOGISTICA", "TECNOLOGIA", "ALIMENTOS", "CONSTRUTORA", "COMERCIO",
         "SERVICOS", "CONSULTORIA", "TRANSPORTES", "DISTRIBUIDORA", "SAUDE"]
SUFIXOS = ["LTDA", "EIRELI", "S.A.", "ME", "EPP"]
UF_DDDS: dict[str, list[str]] = {}
for _ddd, (_uf, _) in DDD_INFO.items():
    UF_DDDS.setdefault(_uf, []).append(_ddd)
UFS_USADAS = ["MG", "SP", "RJ", "PE", "PR", "BA", "RS", "DF"]
CEP_BASE = {"MG": 30100, "SP": 1300, "RJ": 20000, "PE": 50000, "PR": 80000,
            "BA": 40000, "RS": 90000, "DF": 70000}


@dataclass
class Mundo:
    semente: int
    grupos: dict = field(default_factory=dict)        # gid -> descricao
    telefones: dict = field(default_factory=dict)     # e164 -> gid
    armadilhas: list = field(default_factory=list)
    estabelecimentos: list = field(default_factory=list)
    empresas: list = field(default_factory=list)
    socios: list = field(default_factory=list)

    def gabarito(self) -> dict:
        return {"semente": self.semente, "grupos": self.grupos,
                "telefones": self.telefones, "armadilhas": self.armadilhas}


class Gerador:
    def __init__(self, semente: int = 7):
        self.r = random.Random(semente)
        self.semente = semente
        self._usados: set[str] = set()
        self._raizes: set[str] = set()

    # --------------------------------------------------------- primitivas
    def _raiz(self, alfa: bool = False) -> str:
        while True:
            if alfa:
                chars = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"
                r = "".join(self.r.choice(chars) for _ in range(8))
            else:
                r = "".join(str(self.r.randint(0, 9)) for _ in range(8))
            if r not in self._raizes and len(set(r)) > 2:
                self._raizes.add(r)
                return r

    def _cnpj(self, raiz: str, ordem: int) -> str:
        base = f"{raiz}{ordem:04d}"
        return base + cnpj_dv(base)

    def _movel(self, ddd: str, prefixo: str | None = None,
               sufixo: int | None = None) -> str:
        while True:
            pref = prefixo or f"9{self.r.randint(6000, 9999)}"
            suf = sufixo if sufixo is not None else self.r.randint(0, 9999)
            num = f"{ddd}{pref}{suf:04d}"
            if num not in self._usados:
                self._usados.add(num)
                return num

    def _pessoa(self) -> str:
        return (f"{self.r.choice(NOMES)} {self.r.choice(SOBRENOMES)} "
                f"{self.r.choice(SOBRENOMES)}")

    def _cpf_mascara(self, uf: str) -> str:
        regiao = next(k for k, v in REGIAO_FISCAL_CPF.items() if uf in v)
        meio = "".join(str(self.r.randint(0, 9)) for _ in range(5)) + regiao
        return f"***{meio}**"

    # ------------------------------------------------------------- mundo
    def gerar(self, n_grupos: int = 12, armadilhas: bool = True) -> Mundo:
        m = Mundo(semente=self.semente)
        pendentes_seq: list[tuple[str, str]] = []

        for gi in range(n_grupos):
            gid = f"G{gi + 1:02d}"
            uf = self.r.choice(UFS_USADAS)
            ddd = self.r.choice(UF_DDDS[uf])
            ramo = self.r.choice(RAMOS)
            marca = f"{self.r.choice(SOBRENOMES)} {ramo}"
            usa_gmail = armadilhas and self.r.random() < 0.3
            dominio = "gmail.com" if usa_gmail else \
                f"{marca.split()[0].lower()}{gi}.fio-sintetico.test"
            socios = [self._pessoa() for _ in range(self.r.randint(1, 3))]
            # uma pessoa tem UM cpf: a mascara e fixa por pessoa, nao por empresa
            mascaras = {s: self._cpf_mascara(uf) for s in socios}
            n_emp = self.r.randint(1, 3)
            m.grupos[gid] = {"marca": marca, "uf": uf, "ddd": ddd,
                             "socios": socios, "dominio": dominio,
                             "empresas": []}

            raiz_principal = self._raiz(alfa=armadilhas and self.r.random() < 0.15)
            # linhas corporativas: parte em bloco contiguo
            base_pref = f"9{self.r.randint(6000, 9999)}"
            base_suf = self.r.randint(100, 9000)
            for ei in range(n_emp):
                socio_oculto = armadilhas and ei > 0 and self.r.random() < 0.5
                parente = False
                if socio_oculto:
                    raiz, ordem = self._raiz(), 1
                    # parte das empresas "irmas" esta em nome de parente: o
                    # vinculo existe no mundo, mas nao no cadastro
                    parente = self.r.random() < 0.35
                    m.armadilhas.append({"tipo": "parente" if parente else "socio-oculto",
                                         "grupo": gid})
                else:
                    raiz, ordem = raiz_principal, ei + 1
                cnpj = self._cnpj(raiz, ordem)
                razao = f"{marca} {self.r.choice(SUFIXOS)}" if ei == 0 else \
                    f"{marca} {self.r.choice(['FILIAL', 'NORTE', 'SUL', 'CENTRO'])} LTDA"
                if self.r.random() < 0.5:
                    t1 = self._movel(ddd, base_pref, base_suf + ei)   # contiguo
                else:
                    t1 = self._movel(ddd)
                t2 = self._movel(ddd) if self.r.random() < 0.4 else ""
                email = f"contato{ei}@{dominio}" if not usa_gmail else \
                    f"{marca.split()[0].lower()}.{gi}{ei}@gmail.com"
                cep = f"{CEP_BASE[uf] + self.r.randint(0, 900):05d}{self.r.randint(0, 999):03d}"
                m.estabelecimentos.append({
                    "raiz": raiz, "ordem": f"{ordem:04d}", "dv": cnpj[-2:],
                    "matriz": "1" if ordem == 1 else "2",
                    "fantasia": razao.split(" LTDA")[0], "uf": uf, "cep": cep,
                    "ddd1": ddd, "tel1": t1[2:], "ddd2": ddd if t2 else "",
                    "tel2": t2[2:] if t2 else "", "email": email})
                if not any(e["raiz"] == raiz for e in m.empresas):
                    m.empresas.append({"raiz": raiz, "razao": razao})
                    quem = socios
                    if parente:
                        sob = socios[0].split()[-1]
                        novo = f"{self.r.choice(NOMES)} {self.r.choice(SOBRENOMES)} {sob}"
                        mascaras[novo] = self._cpf_mascara(uf)
                        quem = [novo]
                    for s in quem:
                        m.socios.append({"raiz": raiz, "nome": s, "doc": mascaras[s]})
                m.grupos[gid]["empresas"].append(cnpj)
                for t in (t1, t2):
                    if t:
                        m.telefones[f"+55{t}"] = gid
                pendentes_seq.append((gid, t1))

        if armadilhas:
            self._armar(m, pendentes_seq)
        return m

    @staticmethod
    def _trocar_tel2(m: Mundo, est: dict, novo: str, gid: str) -> None:
        """Substitui a segunda linha sem deixar numero orfao no gabarito."""
        if est.get("tel2"):
            m.telefones.pop(f"+55{est['ddd2']}{est['tel2']}", None)
        est["ddd2"], est["tel2"] = novo[:2], novo[2:]
        m.telefones[f"+55{novo}"] = gid

    def _armar(self, m: Mundo, linhas: list[tuple[str, str]]) -> None:
        # 1. contabilidade: um telefone em empresas de 5+ grupos distintos
        uf = "MG"
        contab = self._movel(UF_DDDS[uf][0])
        grupos_alvo = self.r.sample(sorted(m.grupos), min(5, len(m.grupos)))
        m.grupos["G-CONTAB"] = {"marca": "ESCRITORIO CONTABIL (armadilha)",
                                "uf": uf, "socios": [], "empresas": []}
        m.telefones[f"+55{contab}"] = "G-CONTAB"
        for gid in grupos_alvo:
            cnpj0 = m.grupos[gid]["empresas"][0]
            for est in m.estabelecimentos:
                if est["raiz"] + est["ordem"] + est["dv"] == cnpj0:
                    self._trocar_tel2(m, est, contab, "G-CONTAB")
        m.armadilhas.append({"tipo": "contabilidade", "telefone": f"+55{contab}",
                             "grupos": grupos_alvo})

        # 2. bloco-isca: linha de outro grupo no mesmo bloco de numeracao
        g_a, g_b = self.r.sample(sorted(k for k in m.grupos if k.startswith("G0") or k.startswith("G1")), 2)
        tel_a = next(t for t, g in m.telefones.items() if g == g_a)
        isca = self._movel(tel_a[3:5], tel_a[5:10], None)
        est_b = next(e for e in m.estabelecimentos
                     if e["raiz"] + e["ordem"] + e["dv"] in m.grupos[g_b]["empresas"])
        self._trocar_tel2(m, est_b, isca, g_b)
        m.armadilhas.append({"tipo": "bloco-isca", "telefones": [tel_a, f"+55{isca}"],
                             "grupos": [g_a, g_b]})

        # 3. sequencia-isca: numero contiguo de grupo diferente
        reais = sorted(k for k in m.grupos if k != "G-CONTAB")
        for _ in range(30):
            g_c, g_d = self.r.sample(reais, 2)
            tel_c = next(t for t, g in m.telefones.items() if g == g_c)
            viz = f"{tel_c[3:5]}{int(tel_c[5:]) + 3:09d}"
            livres = [e for e in m.estabelecimentos
                      if e["raiz"] + e["ordem"] + e["dv"] in m.grupos[g_d]["empresas"]
                      and not e["tel2"]]
            if viz in self._usados or not livres:
                continue
            self._usados.add(viz)
            self._trocar_tel2(m, livres[0], viz, g_d)
            m.armadilhas.append({"tipo": "sequencia-isca",
                                 "telefones": [tel_c, f"+55{viz}"],
                                 "grupos": [g_c, g_d]})
            break

        # 4. numero reciclado: cadastro antigo de outro grupo ainda declara
        #    uma linha que hoje pertence a este grupo (dado desatualizado)
        g_e, g_f = self.r.sample(reais, 2)
        tel_e = next(t for t, g in m.telefones.items() if g == g_e)
        est_f = next((e for e in m.estabelecimentos
                      if e["raiz"] + e["ordem"] + e["dv"] in m.grupos[g_f]["empresas"]
                      and not e["tel2"]), None)
        if est_f:
            est_f["ddd2"], est_f["tel2"] = tel_e[3:5], tel_e[5:]
            est_f["situacao"] = "08"          # cadastro antigo: baixado
            m.armadilhas.append({"tipo": "numero-reciclado", "telefone": tel_e,
                                 "grupo_atual": g_e, "cadastro_antigo_de": g_f})

        # 5. laranja: a MESMA pessoa (mesma mascara) socia em dois grupos
        g_h, g_i = self.r.sample(reais, 2)
        raiz_h = m.grupos[g_h]["empresas"][0][:8]
        raiz_i = m.grupos[g_i]["empresas"][0][:8]
        pessoa = m.grupos[g_h]["socios"][0]
        mascara = next(s["doc"] for s in m.socios if s["nome"] == pessoa and s["raiz"] == raiz_h)
        m.socios.append({"raiz": raiz_i, "nome": pessoa, "doc": mascara})
        m.armadilhas.append({"tipo": "laranja", "pessoa": pessoa,
                             "grupos": [g_h, g_i]})

        # 6. homonimo: MESMO NOME, outra pessoa (mascara diferente) em outro
        #    grupo. Chave por nome funde os dois; nome+mascara nao.
        g_j, g_k = self.r.sample(reais, 2)
        raiz_k = m.grupos[g_k]["empresas"][0][:8]
        nome = m.grupos[g_j]["socios"][0]
        m.socios.append({"raiz": raiz_k, "nome": nome,
                         "doc": self._cpf_mascara(m.grupos[g_k]["uf"])})
        m.armadilhas.append({"tipo": "homonimo", "pessoa": nome,
                             "grupos": [g_j, g_k]})

    # --------------------------------------------------------- gravacao
    def gravar(self, m: Mundo, destino: Path) -> dict:
        destino.mkdir(parents=True, exist_ok=True)
        rec = destino / "receita"
        rec.mkdir(exist_ok=True)

        def w(nome, linhas):
            with (rec / nome).open("w", encoding="latin-1", newline="") as fh:
                cw = csv.writer(fh, delimiter=";", quoting=csv.QUOTE_ALL)
                cw.writerows(linhas)

        est_linhas = []
        for e in m.estabelecimentos:
            est_linhas.append([e["raiz"], e["ordem"], e["dv"], e["matriz"],
                               e["fantasia"], e.get("situacao", "02"), "", "0", "", "", "01/01/2020",
                               "4930202", "", "RUA", "FICTICIA", "100", "", "CENTRO",
                               e["cep"], e["uf"], "0001", e["ddd1"], e["tel1"],
                               e["ddd2"], e["tel2"], "", "", e["email"], "", ""])
        w("Estabelecimentos0.csv", est_linhas)
        w("Empresas0.csv", [[e["raiz"], e["razao"], "2062", "49", "10000,00", "01", ""]
                            for e in m.empresas])
        w("Socios0.csv", [[s["raiz"], "2", s["nome"], s["doc"], "49", "01/01/2020",
                           "", "", "", "", ""] for s in m.socios])
        (destino / "gabarito.json").write_text(
            json.dumps(m.gabarito(), ensure_ascii=False, indent=2), encoding="utf-8")
        return {"grupos": len(m.grupos), "telefones": len(m.telefones),
                "empresas": len(m.empresas),
                "estabelecimentos": len(m.estabelecimentos),
                "armadilhas": [a["tipo"] for a in m.armadilhas]}
