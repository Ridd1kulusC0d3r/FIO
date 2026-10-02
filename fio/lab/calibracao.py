"""Calibracao da confianca das arestas contra o gabarito sintetico.

O score Admiralty ordena bem, mas "0.64" so significa "64% das vezes certo"
se alguem medir. Aqui se mede: para cada aresta entre entidades cujo grupo
verdadeiro e conhecido (telefone, organizacao), o rotulo e "as duas pontas
sao do mesmo grupo?". Com varios mundos, agrupa-se por faixa de confianca e
compara-se a confianca declarada com a precisao observada.

Dois resultados saem disso:
 - a tabela de confiabilidade e o erro de calibracao esperado (ECE);
 - uma regressao isotonica (Pool Adjacent Violators), monotona por
   construcao, que mapeia a confianca declarada para a precisao observada.

A calibracao vale para o gabarito sintetico. Ela diz se o escalonamento
interno e coerente; nao e garantia sobre o mundo real, que tem armadilhas
que o gerador nao conhece.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..grafo.modelo import Grafo
from .avaliacao import executar_mundo

FAIXAS = (0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0)
TIPOS_COM_GABARITO = ("telefone", "organizacao")


def grupo_de(g_ent, mundo) -> str | None:
    if g_ent.tipo == "telefone":
        return mundo.telefones.get(g_ent.valor)
    if g_ent.tipo == "organizacao":
        for gid, info in mundo.grupos.items():
            if g_ent.valor in info.get("empresas", ()):
                return gid
    return None


def pares_rotulados(g: Grafo, mundo) -> list[tuple[float, bool]]:
    """[(confianca declarada, as duas pontas sao do mesmo grupo?)]"""
    saida = []
    for a in g.arestas.values():
        o, d = g.entidades[a.origem], g.entidades[a.destino]
        if o.tipo not in TIPOS_COM_GABARITO or d.tipo not in TIPOS_COM_GABARITO:
            continue
        go, gd = grupo_de(o, mundo), grupo_de(d, mundo)
        if go is None or gd is None:
            continue
        saida.append((a.confianca, go == gd))
    return saida


def tabela_confiabilidade(pares: list[tuple[float, bool]]) -> list[dict]:
    linhas = []
    for lo, hi in zip(FAIXAS, FAIXAS[1:]):
        grupo = [(c, y) for c, y in pares
                 if lo <= c < hi or (hi == FAIXAS[-1] and c == hi)]
        if not grupo:
            continue
        n = len(grupo)
        linhas.append({"faixa": f"{lo:.1f}-{hi:.1f}", "n": n,
                       "confianca_media": round(sum(c for c, _ in grupo) / n, 4),
                       "precisao_observada": round(sum(y for _, y in grupo) / n, 4)})
    return linhas


def ece(tabela: list[dict]) -> float:
    total = sum(l["n"] for l in tabela)
    if not total:
        return 0.0
    return round(sum(l["n"] * abs(l["confianca_media"] - l["precisao_observada"])
                     for l in tabela) / total, 4)


@dataclass
class Calibrador:
    """Funcao em degraus, monotona nao decrescente (isotonica)."""
    limites: list[float] = field(default_factory=list)   # confianca ate (inclusive)
    valores: list[float] = field(default_factory=list)   # precisao no degrau

    def aplicar(self, confianca: float) -> float:
        if not self.limites:
            return confianca
        for lim, val in zip(self.limites, self.valores):
            if confianca <= lim:
                return val
        return self.valores[-1]

    def dict(self) -> dict:
        return {"limites": self.limites, "valores": self.valores}


def ajustar_isotonica(pares: list[tuple[float, bool]]) -> Calibrador:
    """Pool Adjacent Violators sobre os pares ordenados por confianca."""
    if not pares:
        return Calibrador()
    # empates em x viram um ponto so (soma de acertos, contagem)
    por_x: dict[float, list[float]] = {}
    for x, y in pares:
        acc = por_x.setdefault(x, [0.0, 0.0])
        acc[0] += float(y)
        acc[1] += 1.0
    # cada bloco: [soma_y, n, maior_x]
    blocos: list[list[float]] = []
    for x in sorted(por_x):
        blocos.append([por_x[x][0], por_x[x][1], x])
        while len(blocos) > 1 and (blocos[-2][0] / blocos[-2][1]
                                   > blocos[-1][0] / blocos[-1][1]):
            b = blocos.pop()
            blocos[-1][0] += b[0]
            blocos[-1][1] += b[1]
            blocos[-1][2] = b[2]
    return Calibrador([round(b[2], 4) for b in blocos],
                      [round(b[0] / b[1], 4) for b in blocos])


def calibrar(destino: Path, sementes: list[int], n_grupos: int = 12,
             log=lambda s: None) -> dict:
    """Roda varios mundos, junta os pares e devolve a calibracao."""
    todos: list[tuple[float, bool]] = []
    por_semente = []
    for s in sementes:
        mundo, g, _, _, _ = executar_mundo(Path(destino) / f"s{s}", s, n_grupos,
                                           log=log)
        p = pares_rotulados(g, mundo)
        todos += p
        por_semente.append({"semente": s, "arestas_rotuladas": len(p)})
    tab = tabela_confiabilidade(todos)
    cal = ajustar_isotonica(todos)
    antes = ece(tab)
    # ECE depois de calibrar (resubstituicao: otimista, serve de teto)
    tab_depois = tabela_confiabilidade([(cal.aplicar(c), y) for c, y in todos])
    res = {"sementes": sementes, "arestas_rotuladas": len(todos),
           "por_semente": por_semente, "tabela": tab, "ece_antes": antes,
           "ece_depois_resubstituicao": ece(tab_depois),
           "isotonica": cal.dict(),
           "aviso": ("calibracao sobre mundos sinteticos; valida o "
                     "escalonamento interno, nao substitui validacao em campo")}
    Path(destino).mkdir(parents=True, exist_ok=True)
    (Path(destino) / "calibracao.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    return res


def tabela_markdown(res: dict) -> str:
    L = [f"## Calibracao da confianca ({len(res['sementes'])} mundos, "
         f"{res['arestas_rotuladas']} arestas rotuladas)", "",
         "| faixa | arestas | confianca declarada | precisao observada |",
         "|---|---|---|---|"]
    for l in res["tabela"]:
        L.append(f"| {l['faixa']} | {l['n']} | {l['confianca_media']} | "
                 f"{l['precisao_observada']} |")
    L += ["", f"ECE antes: **{res['ece_antes']}**; "
              f"depois da isotonica (resubstituicao): "
              f"**{res['ece_depois_resubstituicao']}**.", "",
          f"_{res['aviso']}_"]
    return "\n".join(L) + "\n"
