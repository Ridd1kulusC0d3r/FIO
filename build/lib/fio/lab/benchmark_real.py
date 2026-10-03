"""Benchmark com dados REAIS da Receita, sem gabarito fabricado.

A ideia: a propria base publica tem um rotulo natural, a raiz do CNPJ.
Estabelecimentos com a mesma raiz sao, por definicao, a mesma empresa.
Escondemos a raiz e perguntamos: a partir das outras evidencias publicas
(e-mail, dominio, endereco, nome fantasia, telefone compartilhado,
numeracao), quanto cada heuristica consegue reunir as filiais de uma mesma
empresa sem juntar empresas diferentes?

Cuidados de desenho:
- pares de telefones do MESMO estabelecimento ficam fora (seriam triviais);
- o quadro societario fica fora: na base ele e indexado pela propria raiz,
  usa-lo seria vazar o gabarito;
- a amostra e um municipio denso, porque e na densidade que aparecem
  contador em comum, mesmo predio e linhas vizinhas -- os falsos positivos
  que interessam medir;
- a saida e so agregada (contagens e metricas). Nenhum nome sai daqui.
"""

from __future__ import annotations

import random
import re
import sqlite3
from itertools import combinations
from pathlib import Path

from .avaliacao import UF, _metricas

LIVRES = {"gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "yahoo.com.br",
          "bol.com.br", "uol.com.br", "icloud.com", "live.com", "terra.com.br",
          "globo.com", "ig.com.br", "msn.com", "hotmail.com.br", "outlook.com.br"}


def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def benchmark(indice: str | Path, municipio: str | None = None, max_raizes: int = 800,
              semente: int = 7, log=print) -> dict:
    con = sqlite3.connect(str(indice))
    con.row_factory = sqlite3.Row
    rnd = random.Random(semente)

    if not municipio:
        cand = [r[0] for r in con.execute(
            "SELECT municipio, COUNT(DISTINCT cnpj_basico) n FROM estabelecimento "
            "WHERE e164_1 IS NOT NULL GROUP BY municipio HAVING n BETWEEN 100 AND ?",
            (max_raizes * 4,))]
        municipio = rnd.choice(sorted(cand)) if cand else None
    filtro, args = ("WHERE municipio=?", (municipio,)) if municipio else ("", ())
    raizes = [r[0] for r in con.execute(
        f"SELECT DISTINCT cnpj_basico FROM estabelecimento {filtro}", args)]
    rnd.shuffle(raizes)
    raizes = set(raizes[:max_raizes])
    est = [dict(r) for r in con.execute(
        f"SELECT * FROM estabelecimento {filtro}", args) if r["cnpj_basico"] in raizes]
    log(f"amostra: municipio {municipio or 'todos'}, {len(raizes)} raizes, {len(est)} estabelecimentos")

    # telefones -> raizes e estabelecimentos
    tel_raizes: dict[str, set] = {}
    tel_est: dict[str, set] = {}
    for e in est:
        for t in (e["e164_1"], e["e164_2"]):
            if t:
                tel_raizes.setdefault(t, set()).add(e["cnpj_basico"])
                tel_est.setdefault(t, set()).add(e["cnpj"])
    # contagem global de raizes por telefone (para a poda de intermediarios)
    global_raizes = {t: con.execute(
        "SELECT COUNT(DISTINCT cnpj_basico) FROM estabelecimento WHERE e164_1=? OR e164_2=?",
        (t, t)).fetchone()[0] for t in tel_raizes}
    ouro = {t: next(iter(r)) for t, r in tel_raizes.items() if len(r) == 1}

    def pares_de(grupo_por_tel: dict[str, str]) -> set:
        """Pares de telefones-ouro do mesmo grupo, excluindo os do mesmo estabelecimento."""
        inv: dict[str, list] = {}
        for t, g in grupo_por_tel.items():
            if t in ouro:
                inv.setdefault(g, []).append(t)
        saida = set()
        for membros in inv.values():
            for a, b in combinations(sorted(membros), 2):
                if not (tel_est[a] & tel_est[b]):
                    saida.add(frozenset((a, b)))
        return saida

    real = pares_de(ouro)

    def por_chave(chave) -> dict[str, str]:
        uf = UF()
        grupos: dict[str, list] = {}
        for e in est:
            k = chave(e)
            if k:
                grupos.setdefault(k, []).append(e["cnpj"])
        for membros in grupos.values():
            for x, y in zip(membros, membros[1:]):
                uf.unir(x, y)
        return uf

    def telefones(uf: UF) -> dict[str, str]:
        return {t: uf.achar(next(iter(sorted(tel_est[t])))) for t in tel_est}

    def compartilhado(podar: bool) -> UF:
        uf = UF()
        for t, cnpjs in tel_est.items():
            if podar and global_raizes.get(t, 0) >= 4:
                continue
            cs = sorted(cnpjs)
            for x, y in zip(cs, cs[1:]):
                uf.unir(x, y)
        return uf

    def dominio(e):
        em = e.get("email") or ""
        d = em.split("@")[-1] if "@" in em else ""
        return d if d and d not in LIVRES else None

    heur = {
        "email-exato": por_chave(lambda e: (e.get("email") or "").strip() or None),
        "dominio-email": por_chave(dominio),
        "endereco": por_chave(lambda e: (e["cep"] + "|" + _norm(e["logradouro"])) if e.get("cep") and e.get("logradouro") else None),
        "nome-fantasia": por_chave(lambda e: _norm(e["nome_fantasia"]) or None),
        "telefone-compartilhado": compartilhado(False),
        "telefone-compartilhado-podado": compartilhado(True),
    }
    res = {"municipio": municipio, "raizes": len(raizes), "estabelecimentos": len(est),
           "telefones": len(tel_est), "telefones_ouro": len(ouro),
           "telefones_multiraiz": len(tel_raizes) - len(ouro),
           "pares_verdadeiros": len(real), "heuristicas": {}}
    for nome, uf in heur.items():
        res["heuristicas"][nome] = _metricas(pares_de(telefones(uf)), real)

    # numeracao
    for nome, janela, bloco in (("sequencial", 20, False), ("bloco", 0, True)):
        uf = UF()
        tels = sorted(tel_est)
        if bloco:
            por = {}
            for t in tels:
                por.setdefault(t[:10], []).append(t)
            for membros in por.values():
                for x, y in zip(membros, membros[1:]):
                    uf.unir(x, y)
        else:
            for x, y in zip(tels, tels[1:]):
                if x[:5] == y[:5] and len(x) == len(y) and 0 < int(y[5:]) - int(x[5:]) <= janela:
                    uf.unir(x, y)
        res["heuristicas"][nome] = _metricas(pares_de({t: uf.achar(t) for t in tels}), real)

    # combinado: evidencias fortes + telefone compartilhado com poda
    uf = UF()
    for chave in (lambda e: (e.get("email") or "").strip() or None,
                  lambda e: (e["cep"] + "|" + _norm(e["logradouro"])) if e.get("cep") and e.get("logradouro") else None):
        g = {}
        for e in est:
            k = chave(e)
            if k:
                g.setdefault(k, []).append(e["cnpj"])
        for m in g.values():
            for x, y in zip(m, m[1:]):
                uf.unir(x, y)
    for t, cnpjs in tel_est.items():
        if global_raizes.get(t, 0) < 4:
            cs = sorted(cnpjs)
            for x, y in zip(cs, cs[1:]):
                uf.unir(x, y)
    res["heuristicas"]["combinado"] = _metricas(pares_de(telefones(uf)), real)
    con.close()
    return res


def tabela(res: dict) -> str:
    L = [f"Municipio {res['municipio']}: {res['raizes']} raizes, {res['estabelecimentos']} "
         f"estabelecimentos, {res['telefones_ouro']} telefones de raiz unica, "
         f"{res['telefones_multiraiz']} compartilhados entre raizes, "
         f"{res['pares_verdadeiros']} pares verdadeiros entre estabelecimentos distintos.", "",
         "| heuristica | precisao | revocacao | F1 | VP | FP |", "|---|---|---|---|---|---|"]
    for n, m in sorted(res["heuristicas"].items(), key=lambda x: -x[1]["f1"]):
        L.append(f"| {n} | {m['precisao']} | {m['revocacao']} | {m['f1']} | {m['vp']} | {m['fp']} |")
    return "\n".join(L) + "\n"
