"""Analisadores temporais sobre o cadastro: lote de registro e reuso de linha.

Os dois olham para o que o grafo ja tem (data de inicio de atividade,
situacao cadastral, entidades compartilhadas) e nao fazem rede.

Nenhum dos dois acusa: lote de abertura tambem e o que um escritorio
contabil faz para varios clientes legitimos, e linha reaproveitada tambem e
o que acontece quando uma empresa fecha e a operadora revende o numero. A
observacao descreve o padrao e as explicacoes concorrentes.
"""

from __future__ import annotations

import datetime as dt
import re

from .base import Analisador, registrar_analisador
from ..grafo.modelo import Grafo

JANELA_DIAS = 30
MIN_EMPRESAS_LOTE = 3
LIGACOES = ("telefone", "email", "pessoa", "cep")
SITUACAO_ENCERRADA = {"04", "08", "inapta", "baixada", "INAPTA", "BAIXADA"}
_DIGITOS = re.compile(r"\D")


def parse_data(s) -> dt.date | None:
    """Aceita AAAAMMDD (Receita), AAAA-MM-DD e DD/MM/AAAA."""
    if not s:
        return None
    s = str(s).strip()
    try:
        if "/" in s:
            d, m, a = s.split("/")[:3]
            return dt.date(int(a), int(m), int(d))
        d = _DIGITOS.sub("", s)[:8]
        if len(d) == 8:
            return dt.date(int(d[:4]), int(d[4:6]), int(d[6:8]))
    except ValueError:
        return None
    return None


def _raiz(e) -> str:
    return str(e.atributos.get("cnpj_basico") or e.valor[:8])


def _orgs_distintas(g: Grafo, eid: str) -> dict[str, list[str]]:
    """Organizacoes vizinhas agrupadas por raiz de CNPJ (matriz e filiais
    da mesma raiz contam como uma empresa so)."""
    por_raiz: dict[str, list[str]] = {}
    for _, vid in g.vizinhos(eid):
        v = g.entidades[vid]
        if v.tipo == "organizacao":
            por_raiz.setdefault(_raiz(v), []).append(vid)
    return por_raiz


def _socio_comum(g: Grafo, orgs: list[str]) -> bool:
    contagem: dict[str, set[str]] = {}
    for o in orgs:
        raiz = _raiz(g.entidades[o])
        for _, vid in g.vizinhos(o):
            if g.entidades[vid].tipo == "pessoa":
                contagem.setdefault(vid, set()).add(raiz)
    return any(len(r) >= 2 for r in contagem.values())


def _janela(datas: list[tuple[dt.date, str]], dias: int, minimo: int
            ) -> list[tuple[dt.date, str]] | None:
    """Maior grupo de raizes cujas datas cabem em `dias`, se >= minimo."""
    datas = sorted(datas)
    melhor: list[tuple[dt.date, str]] = []
    j = 0
    for i in range(len(datas)):
        while (datas[i][0] - datas[j][0]).days > dias:
            j += 1
        if i - j + 1 > len(melhor):
            melhor = datas[j:i + 1]
    return melhor if len(melhor) >= minimo else None


@registrar_analisador
class LoteDeRegistro(Analisador):
    nome = "lote-de-registro"
    descricao = ("Agrupa empresas de raizes distintas abertas na mesma janela "
                 f"de {JANELA_DIAS} dias que compartilham telefone, e-mail, "
                 "CEP ou socio. Rede de empresas de fachada abre em lote; "
                 "escritorio contabil tambem.")

    def analisar(self, g: Grafo) -> int:
        antes = len(g.observacoes)
        vistos: set[frozenset] = set()
        # telefone antes de CEP: a mesma rede nao e reportada duas vezes
        candidatos = sorted((e for e in g.entidades.values() if e.tipo in LIGACOES),
                            key=lambda e: (LIGACOES.index(e.tipo), e.id))
        for e in candidatos:
            por_raiz = _orgs_distintas(g, e.id)
            datas = []
            for raiz, ids in por_raiz.items():
                ds = [parse_data(g.entidades[i].atributos.get("inicio_atividade"))
                      for i in ids]
                ds = [d for d in ds if d]
                if ds:
                    datas.append((min(ds), raiz))
            lote = _janela(datas, JANELA_DIAS, MIN_EMPRESAS_LOTE)
            if not lote:
                continue
            raizes = {r for _, r in lote}
            if frozenset(raizes) in vistos:
                continue
            vistos.add(frozenset(raizes))
            ids = sorted(i for r in raizes for i in por_raiz[r])
            ponte = bool(e.atributos.get("intermediario_provavel"))
            ini, fim = lote[0][0], lote[-1][0]
            if ponte:
                leitura = (
                    "Esta entidade ja foi marcada como ponte sem socio em "
                    "comum. Ponte fraca SOZINHA e o perfil de contabilidade "
                    "ou coworking, que atende clientes ao longo do tempo; "
                    "ponte fraca COM abertura em lote e o que mais se parece "
                    "com rede de empresas de fachada. Tambem pode ser um "
                    "servico de abertura de empresas atendendo clientes de "
                    "uma vez so. ")
            elif _socio_comum(g, ids):
                leitura = (
                    "As empresas compartilham ao menos um socio, o que "
                    "aponta para um grupo que se expandiu (leitura mais "
                    "provavel), nao para empresas independentes. ")
            else:
                leitura = (
                    "As empresas nao tem socio em comum, mas sao poucas "
                    "demais para o perfil de ponte: pode ser coincidencia de "
                    "endereco ou linha, ou rede em formacao. ")
            g.observar(
                "lote-de-registro",
                f"{len(raizes)} empresas de raizes distintas abertas entre "
                f"{ini.isoformat()} e {fim.isoformat()} compartilham "
                f"{e.tipo} '{e.rotulo or e.valor}'. {leitura}"
                f"Confronte socios e atividade antes de concluir.",
                [e.id] + ids[:12], "atencao" if ponte else "info", self.nome)
            e.atributos["lote_de_registro"] = {
                "empresas": len(raizes), "inicio": ini.isoformat(),
                "fim": fim.isoformat()}
        return len(g.observacoes) - antes


@registrar_analisador
class ReusoDeLinha(Analisador):
    nome = "reuso-de-linha"
    descricao = ("Telefone declarado por empresa encerrada (baixada/inapta) "
                 "e por outra ativa: linha possivelmente reciclada, nao "
                 "operador em comum.")

    def analisar(self, g: Grafo) -> int:
        antes = len(g.observacoes)
        for tel in g.por_tipo("telefone"):
            por_raiz = _orgs_distintas(g, tel.id)
            if len(por_raiz) < 2:
                continue
            encerradas, ativas = [], []
            for raiz, ids in por_raiz.items():
                reps = [g.entidades[i] for i in ids]
                sit = {str(r.atributos.get("situacao_cadastral") or "").strip()
                       for r in reps} - {""}
                if sit and sit <= SITUACAO_ENCERRADA:
                    encerradas.append((raiz, reps))
                elif sit:
                    ativas.append((raiz, reps))
            if not encerradas or not ativas:
                continue
            ids = sorted(r.id for _, reps in encerradas + ativas for r in reps)
            tel.atributos["linha_reciclada_provavel"] = True
            datas_ant = [parse_data(r.atributos.get("inicio_atividade"))
                         for _, reps in encerradas for r in reps]
            datas_nov = [parse_data(r.atributos.get("inicio_atividade"))
                         for _, reps in ativas for r in reps]
            ordem = ""
            da, dn = [d for d in datas_ant if d], [d for d in datas_nov if d]
            if da and dn and max(dn) > min(da):
                ordem = (" A empresa ativa abriu depois da encerrada, o que "
                         "reforca a hipotese de reaproveitamento da linha.")
            g.observar(
                "linha-possivelmente-reciclada",
                f"Telefone {tel.rotulo or tel.valor} consta em "
                f"{len(encerradas)} empresa(s) encerrada(s) e "
                f"{len(ativas)} ativa(s).{ordem} Cadastro antigo nao e "
                f"vinculo atual: nao use este numero para ligar as empresas "
                f"sem outra evidencia.",
                [tel.id] + ids[:12], "atencao", self.nome)
        return len(g.observacoes) - antes
