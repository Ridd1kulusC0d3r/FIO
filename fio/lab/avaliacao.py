"""Avaliacao das heuristicas de vinculo contra o gabarito sintetico.

Tarefa: dado o conjunto de telefones do mundo, agrupa-los. Metrica
pareada: cada par de telefones e "mesmo grupo" ou nao; comparamos os pares
previstos com os pares verdadeiros e medimos precisao, revocacao e F1.

Cada heuristica e avaliada ISOLADA (o que ela sozinha junta) e o modelo
combinado e varrido em limiares de confianca, com e sem poda de
intermediarios. O resultado responde a pergunta que importa para laudo:
"quando o F.I.O. diz que dois numeros sao do mesmo grupo, com que
frequencia ele erra?"
"""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

from ..grafo.modelo import Grafo
from ..politica import Caso
from ..caso import CasoEmDisco
from ..indice import construir as construir_cnpj
from ..grafo.modelo import Entidade
from ..core.normalize import normalizar
from .sintetico import Gerador
from . import pipeline as pl

LIVRES = {"gmail.com", "hotmail.com", "outlook.com", "yahoo.com.br"}


class UF:
    def __init__(self):
        self.p: dict[str, str] = {}

    def achar(self, x: str) -> str:
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def unir(self, a: str, b: str) -> None:
        self.p[self.achar(a)] = self.achar(b)


def _pares(grupos: dict[str, str]) -> set[frozenset]:
    inv: dict[str, list[str]] = {}
    for t, g in grupos.items():
        inv.setdefault(g, []).append(t)
    return {frozenset(p) for membros in inv.values()
            for p in combinations(sorted(membros), 2)}


def _metricas(prev: set[frozenset], real: set[frozenset]) -> dict:
    tp = len(prev & real)
    fp = len(prev - real)
    fn = len(real - prev)
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"precisao": round(p, 4), "revocacao": round(r, 4), "f1": round(f1, 4),
            "vp": tp, "fp": fp, "fn": fn, "pares_previstos": len(prev)}


def _componentes(g: Grafo, telefones: list[str], aresta_ok, no_ok) -> dict[str, str]:
    uf = UF()
    for a in g.arestas.values():
        if not aresta_ok(a):
            continue
        if not (no_ok(g.entidades[a.origem]) and no_ok(g.entidades[a.destino])):
            continue
        uf.unir(a.origem, a.destino)
    return {t: uf.achar(f"telefone:{t}") for t in telefones}


def prever(g: Grafo, telefones: list[str]) -> dict[str, dict[str, str]]:
    tel_ents = {t: g.entidades.get(f"telefone:{t}") for t in telefones}
    prev: dict[str, dict[str, str]] = {}
    CAD = {"telefone_declarado_por", "telefone_declarado", "mesmo_grupo_cadastral"}

    # cadastro: mesma empresa ou mesma raiz de CNPJ
    prev["cadastro"] = _componentes(
        g, telefones, lambda a: a.relacao in CAD,
        lambda e: e.tipo in ("telefone", "organizacao"))

    # societario: cadastro + socio em comum
    prev["societario"] = _componentes(
        g, telefones, lambda a: a.relacao in CAD | {"tem_socio"},
        lambda e: e.tipo in ("telefone", "organizacao", "pessoa"))

    # ablacao: o que aconteceria identificando socio SO pelo nome
    uf_n = UF()
    def chave(eid: str) -> str:
        e = g.entidades[eid]
        return f"pessoa-nome:{e.rotulo or e.valor}" if e.tipo == "pessoa" else eid
    for a in g.arestas.values():
        if a.relacao in CAD | {"tem_socio"}:
            tipos = {g.entidades[a.origem].tipo, g.entidades[a.destino].tipo}
            if tipos <= {"telefone", "organizacao", "pessoa"}:
                uf_n.unir(chave(a.origem), chave(a.destino))
    prev["societario-so-nome"] = {t: uf_n.achar(f"telefone:{t}") for t in telefones}

    # dominio de e-mail proprio
    prev["dominio-email"] = {}
    uf = UF()
    por_dom: dict[str, list[str]] = {}
    for a in g.arestas.values():
        if a.relacao == "email_declarado":
            dom = g.entidades[a.destino].valor.split("@")[-1]
            if dom not in LIVRES:
                por_dom.setdefault(dom, []).append(a.origem)
    org_tel: dict[str, list[str]] = {}
    for a in g.arestas.values():
        if a.relacao in ("telefone_declarado_por",):
            org_tel.setdefault(a.destino, []).append(a.origem)
        if a.relacao == "telefone_declarado":
            org_tel.setdefault(a.origem, []).append(a.destino)
    for dom, orgs in por_dom.items():
        tels = [t for o in orgs for t in org_tel.get(o, [])]
        for x, y in zip(tels, tels[1:]):
            uf.unir(x, y)
    prev["dominio-email"] = {t: uf.achar(f"telefone:{t}") for t in telefones}

    # bloco de numeracao
    prev["bloco"] = {t: (tel_ents[t].atributos.get("faixa") if tel_ents[t] else t) or t
                     for t in telefones}

    # sequencial (janela 20)
    uf = UF()
    por_ddd: dict[str, list[tuple[int, str]]] = {}
    for t in telefones:
        n = normalizar(t)
        if n.ddd and n.assinante:
            por_ddd.setdefault(n.ddd, []).append((int(n.assinante), t))
    for itens in por_ddd.values():
        itens.sort()
        for (n1, t1), (n2, t2) in zip(itens, itens[1:]):
            if n2 - n1 <= 20:
                uf.unir(f"telefone:{t1}", f"telefone:{t2}")
    prev["sequencial"] = {t: uf.achar(f"telefone:{t}") for t in telefones}
    return prev


def prever_combinado(g: Grafo, telefones: list[str], limiar: float,
                     podar: bool) -> dict[str, str]:
    ignorar = {"faixa", "url", "diario", "documento", "cep", "municipio",
               "cpf-parcial", "email"}
    return _componentes(
        g, telefones,
        lambda a: a.confianca >= limiar,
        lambda e: e.tipo not in ignorar and not (
            podar and e.atributos.get("intermediario_provavel")))


def avaliar(destino: Path, semente: int = 7, n_grupos: int = 12,
            armadilhas: bool = True, ator: str = "lab",
            log=lambda s: None) -> dict:
    destino = Path(destino)
    ger = Gerador(semente)
    mundo = ger.gerar(n_grupos, armadilhas)
    resumo = ger.gravar(mundo, destino)
    log(f"mundo sintetico: {resumo}")

    idx = destino / "cnpj.sqlite"
    if idx.exists():
        idx.unlink()
    construir_cnpj(destino / "receita", idx, log=lambda s: None)

    caso_id = f"SINT-{semente}"
    base = destino / "casos"
    cd = CasoEmDisco(caso_id, base=base)
    if cd.dir.exists():
        import shutil
        shutil.rmtree(cd.dir)
    telefones = sorted(mundo.telefones)
    cd.criar(Caso(id=caso_id, titulo=f"Avaliacao sintetica semente {semente}",
                  base_legal="pesquisa-academica",
                  finalidade=("avaliacao de heuristicas de vinculo sobre mundo "
                              "ficticio gerado localmente, sem dado pessoal real"),
                  responsavel=ator, escopo=list(telefones),
                  observacoes="SINTETICO - execucao forcada offline"), ator)
    for t in telefones:
        n = normalizar(t)
        cd.add_alvo(Entidade("telefone", t, rotulo=n.formatado(),
                             atributos={"ddd": n.ddd, "assinante": n.assinante,
                                        "faixa": n.faixa, "uf": n.uf, "e164": n.e164}),
                    ator)

    cfg = pl.Config(coletores=["nucleo", "cnpj-reverso"], profundidade=2,
                    offline=True,                      # nunca sai da maquina
                    expandir_escopo=True,
                    descricao=f"avaliacao sintetica s={semente} n={n_grupos}",
                    extras={"segredos": {"indice_cnpj": str(idx)}})
    exp = pl.executar(cd, ator, cfg, log=log)
    g = cd.grafo()

    real = _pares(mundo.telefones)
    resultado = {"semente": semente, "mundo": resumo, "experimento": exp.id,
                 "pares_verdadeiros": len(real), "heuristicas": {},
                 "combinado": [], "armadilhas": mundo.armadilhas}

    for nome, grupos in prever(g, telefones).items():
        resultado["heuristicas"][nome] = _metricas(_pares(grupos), real)

    for podar in (False, True):
        for lim in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
            m = _metricas(_pares(prever_combinado(g, telefones, lim, podar)), real)
            resultado["combinado"].append({"limiar": lim, "poda_intermediarios": podar, **m})

    melhor = max(resultado["combinado"], key=lambda x: (x["f1"], x["precisao"]))
    resultado["melhor_configuracao"] = melhor
    (destino / "avaliacao.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return resultado


def tabela_markdown(res: dict) -> str:
    L = [f"## Avaliacao sintetica (semente {res['semente']})", "",
         f"Mundo: {res['mundo']['grupos']} grupos, {res['mundo']['telefones']} "
         f"telefones, {res['pares_verdadeiros']} pares verdadeiros. "
         f"Armadilhas: {', '.join(res['mundo']['armadilhas'])}.", "",
         "### Heuristicas isoladas", "",
         "| heuristica | precisao | revocacao | F1 | VP | FP | FN |",
         "|---|---|---|---|---|---|---|"]
    for n, m in sorted(res["heuristicas"].items(), key=lambda x: -x[1]["f1"]):
        L.append(f"| {n} | {m['precisao']} | {m['revocacao']} | {m['f1']} | "
                 f"{m['vp']} | {m['fp']} | {m['fn']} |")
    L += ["", "### Modelo combinado (varredura de limiar)", "",
          "| limiar | poda | precisao | revocacao | F1 | FP |", "|---|---|---|---|---|---|"]
    for c in res["combinado"]:
        L.append(f"| {c['limiar']} | {'sim' if c['poda_intermediarios'] else 'nao'} | "
                 f"{c['precisao']} | {c['revocacao']} | {c['f1']} | {c['fp']} |")
    b = res["melhor_configuracao"]
    L += ["", f"**Melhor configuracao:** limiar {b['limiar']}, poda "
              f"{'ligada' if b['poda_intermediarios'] else 'desligada'} -> "
              f"precisao {b['precisao']}, revocacao {b['revocacao']}, F1 {b['f1']}."]
    return "\n".join(L) + "\n"


def avaliar_lote(destino: Path, sementes: list[int], n_grupos: int = 12,
                 log=lambda s: None) -> dict:
    """Varias sementes -> media e desvio. Um numero so nao e resultado."""
    import statistics as st
    rodadas = [avaliar(Path(destino) / f"s{s}", s, n_grupos, log=log) for s in sementes]
    agg: dict = {"sementes": sementes, "heuristicas": {}, "combinado": {}}
    for h in rodadas[0]["heuristicas"]:
        for met in ("precisao", "revocacao", "f1"):
            vals = [r["heuristicas"][h][met] for r in rodadas]
            agg["heuristicas"].setdefault(h, {})[met] = {
                "media": round(st.mean(vals), 4),
                "desvio": round(st.pstdev(vals), 4)}
    for i, c in enumerate(rodadas[0]["combinado"]):
        chave = f"t={c['limiar']}|poda={'sim' if c['poda_intermediarios'] else 'nao'}"
        for met in ("precisao", "revocacao", "f1"):
            vals = [r["combinado"][i][met] for r in rodadas]
            agg["combinado"].setdefault(chave, {})[met] = {
                "media": round(st.mean(vals), 4),
                "desvio": round(st.pstdev(vals), 4)}
    agg["rodadas"] = [{"semente": r["semente"], "experimento": r["experimento"],
                       "armadilhas": [a["tipo"] for a in r["armadilhas"]]}
                      for r in rodadas]
    (Path(destino) / "avaliacao_lote.json").write_text(
        json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
    return agg


def tabela_lote(agg: dict) -> str:
    fmt = lambda d: f"{d['media']:.3f} ± {d['desvio']:.3f}"
    L = [f"## Avaliacao em lote ({len(agg['sementes'])} mundos)", "",
         "| heuristica | precisao | revocacao | F1 |", "|---|---|---|---|"]
    for h, m in sorted(agg["heuristicas"].items(), key=lambda x: -x[1]["f1"]["media"]):
        L.append(f"| {h} | {fmt(m['precisao'])} | {fmt(m['revocacao'])} | {fmt(m['f1'])} |")
    L += ["", "| combinado | precisao | revocacao | F1 |", "|---|---|---|---|"]
    for k, m in agg["combinado"].items():
        L.append(f"| {k} | {fmt(m['precisao'])} | {fmt(m['revocacao'])} | {fmt(m['f1'])} |")
    return "\n".join(L) + "\n"
