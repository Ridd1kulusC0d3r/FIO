"""Deteccao de agrupamento: o que faz varios numeros virarem "um grupo".

Cada heuristica devolve forca e explicacao em texto. A explicacao vai
inteira para o relatorio, porque um cluster sem justificativa legivel e
inutil em contraditorio -- e porque varias destas heuristicas produzem
falso positivo com facilidade, e o leitor precisa poder discordar.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from itertools import combinations

from .modelo import Grafo, Entidade


@dataclass
class Cluster:
    tipo: str
    chave: str
    membros: list[str] = field(default_factory=list)
    forca: float = 0.0
    explicacao: str = ""
    ressalva: str = ""

    def dict(self) -> dict:
        return asdict(self)


def _telefones(g: Grafo) -> list[Entidade]:
    return [e for e in g.por_tipo("telefone")
            if e.atributos.get("ddd") and e.atributos.get("assinante")]


def _por_faixa(g: Grafo) -> list[Cluster]:
    grupos: dict[str, list[Entidade]] = {}
    for e in _telefones(g):
        f = e.atributos.get("faixa")
        if f:
            grupos.setdefault(f, []).append(e)
    saida = []
    for faixa, membros in grupos.items():
        if len(membros) < 2:
            continue
        saida.append(Cluster(
            tipo="bloco-numeracao", chave=faixa,
            membros=sorted(m.id for m in membros),
            forca=0.35,
            explicacao=(f"{len(membros)} numeros no mesmo bloco de numeracao "
                        f"{faixa}. Blocos sao destinados em lote as "
                        f"prestadoras e linhas corporativas de uma mesma "
                        f"contratacao costumam cair no mesmo bloco."),
            ressalva=("Indicio fraco isolado: um bloco atende milhares de "
                      "assinantes sem relacao entre si. So tem valor somado "
                      "a outro vinculo."),
        ))
    return saida


def _sequenciais(g: Grafo, janela: int = 20) -> list[Cluster]:
    porddd: dict[str, list[tuple[int, Entidade]]] = {}
    for e in _telefones(g):
        try:
            n = int(e.atributos["assinante"])
        except (ValueError, KeyError):
            continue
        porddd.setdefault(e.atributos["ddd"], []).append((n, e))

    saida = []
    for ddd, itens in porddd.items():
        itens.sort()
        atual: list[tuple[int, Entidade]] = []
        blocos: list[list[tuple[int, Entidade]]] = []
        for par in itens:
            if atual and (par[0] - atual[-1][0]) <= janela:
                atual.append(par)
            else:
                if len(atual) > 1:
                    blocos.append(atual)
                atual = [par]
        if len(atual) > 1:
            blocos.append(atual)
        for b in blocos:
            saida.append(Cluster(
                tipo="numeracao-sequencial",
                chave=f"{ddd}-{b[0][1].atributos['assinante']}",
                membros=sorted(e.id for _, e in b),
                forca=0.55,
                explicacao=(f"{len(b)} numeros contiguos no DDD {ddd} "
                            f"(intervalo de {b[-1][0] - b[0][0]} posicoes). "
                            f"Contratacao corporativa em lote e a explicacao "
                            f"mais economica para numeros adjacentes."),
                ressalva=("Pode tambem indicar numeros gerados "
                          "artificialmente em fraude ou lista sintetica."),
            ))
    return saida


def _dominio_email(g: Grafo) -> list[Cluster]:
    grupos: dict[str, list[Entidade]] = {}
    for e in g.por_tipo("email"):
        if "@" in e.valor:
            grupos.setdefault(e.valor.split("@", 1)[1].lower(), []).append(e)
    livres = {"gmail.com", "hotmail.com", "outlook.com", "yahoo.com",
              "yahoo.com.br", "bol.com.br", "uol.com.br", "icloud.com",
              "proton.me", "protonmail.com", "live.com", "terra.com.br"}
    saida = []
    for dom, membros in grupos.items():
        if len(membros) < 2:
            continue
        publico = dom in livres
        saida.append(Cluster(
            tipo="dominio-email", chave=dom,
            membros=sorted(m.id for m in membros),
            forca=0.25 if publico else 0.70,
            explicacao=(f"{len(membros)} enderecos no dominio {dom}."
                        + ("" if publico else " Dominio proprio: os titulares "
                           "compartilham a mesma infraestrutura de correio, "
                           "logo a mesma organizacao ou o mesmo responsavel.")),
            ressalva=("Provedor gratuito: o dominio nao vincula ninguem a "
                      "ninguem." if publico else
                      "Confirme o titular do dominio via RDAP antes de "
                      "afirmar a relacao."),
        ))
    return saida


def _ancora_comum(g: Grafo, tipos=("organizacao", "cnpj", "dominio",
                                   "endereco", "pessoa")) -> list[Cluster]:
    """Duas ou mais entidades ligadas a mesma ancora: o vinculo classico."""
    saida = []
    for e in g.entidades.values():
        if e.tipo not in tipos:
            continue
        vizinhos = g.vizinhos(e.id)
        tel = sorted({outro for a, outro in vizinhos
                      if g.entidades[outro].tipo == "telefone"})
        if len(tel) < 2:
            continue
        confs = [a.confianca for a, outro in vizinhos if outro in tel]
        media = round(sum(confs) / len(confs), 4) if confs else 0.0
        saida.append(Cluster(
            tipo=f"ancora-{e.tipo}", chave=e.valor,
            membros=sorted(tel + [e.id]),
            forca=round(min(0.95, 0.5 + media / 2), 4),
            explicacao=(f"{len(tel)} telefones ligados a mesma entidade "
                        f"{e.tipo} '{e.rotulo or e.valor}', confianca media "
                        f"das arestas {media}."),
            ressalva=("Verifique se a ancora nao e um intermediario generico "
                      "(escritorio de contabilidade, central de atendimento, "
                      "provedor de hospedagem) antes de tratar como grupo."),
        ))
    return saida


def detectar_clusters(g: Grafo) -> list[Cluster]:
    todos = (_ancora_comum(g) + _sequenciais(g) + _dominio_email(g)
             + _por_faixa(g))
    return sorted(todos, key=lambda c: (-c.forca, c.tipo, c.chave))


def pontes(g: Grafo) -> list[dict]:
    """Entidades que conectam dois alvos primarios distintos.

    Na pratica e a pergunta que o investigador realmente tem: o que liga
    estas duas pessoas?
    """
    alvos = [e.id for e in g.entidades.values() if e.alvo_primario]
    saida = []
    for a, b in combinations(sorted(alvos), 2):
        cam = g.caminho(a, b)
        if cam and len(cam) > 1:
            # a forca de um caminho e a do seu elo mais fraco
            elos = []
            for x, y in zip(cam, cam[1:]):
                confs = [ar.confianca for ar in g.arestas.values()
                         if {ar.origem, ar.destino} == {x, y}]
                elos.append(max(confs) if confs else 0.0)
            saida.append({
                "de": a, "para": b, "saltos": len(cam) - 1,
                "elo_mais_fraco": round(min(elos), 4) if elos else 0.0,
                "caminho": cam,
                "intermediarios": [
                    {"id": i, "tipo": g.entidades[i].tipo,
                     "rotulo": g.entidades[i].rotulo or g.entidades[i].valor}
                    for i in cam[1:-1]],
            })
    return sorted(saida, key=lambda x: (x["saltos"], -x["elo_mais_fraco"]))


def tabela_correlacao(g: Grafo) -> list[dict]:
    """Saida plana, sem grafo: uma linha por vinculo, ordenada por confianca.

    E a visao que a maioria dos relatorios realmente consome.
    """
    linhas = []
    for a in g.arestas.values():
        o, d = g.entidades[a.origem], g.entidades[a.destino]
        linhas.append({
            "entidade": o.valor, "tipo": o.tipo,
            "relacao": a.relacao,
            "vinculada_a": d.valor, "tipo_vinculo": d.tipo,
            "confianca": a.confianca, "nivel": a.nivel,
            "corroboracoes": len(a.fontes),
            "admiralty": ",".join(sorted({f.admiralty for f in a.fontes})),
            "coletores": ";".join(sorted({f.coletor for f in a.fontes})),
            "evidencia": "; ".join(f.url or f.nota for f in a.fontes if (f.url or f.nota))[:300],
            "observacao": a.observacao,
        })
    return sorted(linhas, key=lambda x: (-x["confianca"], x["entidade"]))
