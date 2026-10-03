"""Claims: toda afirmacao do relatorio cita a evidencia que a sustenta.

O grafo ja exige proveniencia por aresta. Esta camada leva a mesma regra
para o nivel da conclusao: um claim e uma frase ("o telefone X e declarado
pela empresa Y") ligada a arestas e entidades concretas do grafo. Claim sem
evidencia, ou que cita evidencia inexistente, e invalido e nao entra em
relatorio.

Claims derivados por regra deterministica (limiar de confianca) tem origem
`regra`; os que vem de um analisador tem origem `analisador:<nome>`. Nada
aqui e gerado por modelo de linguagem; se algum dia for, a origem deve
dizer `sintese-automatica` e nunca elevar a confianca.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict

from .modelo import Grafo

GRAVIDADE_PESO = {"alta": 3, "atencao": 2, "info": 1}


@dataclass
class Claim:
    id: str
    tipo: str                  # vinculo | observacao
    texto: str
    evidencias: list[str]      # ids de arestas (vinculo) ou de entidades
    coletores: list[str] = field(default_factory=list)
    confianca: float | None = None
    nivel: str = ""
    origem: str = "regra"

    def dict(self) -> dict:
        return asdict(self)


def _id(tipo: str, chave: str) -> str:
    return "C-" + hashlib.sha256(f"{tipo}|{chave}".encode()).hexdigest()[:10]


def derivar(g: Grafo, confianca_minima: float = 0.5) -> list[Claim]:
    """Claims de vinculo (acima do limiar) e de observacao analitica."""
    claims: list[Claim] = []
    for a in sorted(g.arestas.values(), key=lambda x: (-x.confianca, x.id)):
        if a.confianca < confianca_minima:
            continue
        o, d = g.entidades[a.origem], g.entidades[a.destino]
        claims.append(Claim(
            id=_id("vinculo", a.id), tipo="vinculo",
            texto=f"{o.tipo} '{o.rotulo or o.valor}' {a.relacao.replace('_', ' ')} "
                  f"{d.tipo} '{d.rotulo or d.valor}'",
            evidencias=[a.id],
            coletores=sorted({f.coletor for f in a.fontes}),
            confianca=a.confianca, nivel=a.nivel, origem="regra"))
    for o in g.observacoes:
        claims.append(Claim(
            id=_id("observacao", o["tipo"] + "|" + ",".join(sorted(o["entidades"]))),
            tipo="observacao", texto=o["texto"],
            evidencias=list(o["entidades"]), nivel=o.get("gravidade", "info"),
            origem=f"analisador:{o.get('analisador') or 'desconhecido'}"))
    return claims


def validar(claims: list[Claim], g: Grafo) -> list[str]:
    """Problemas que invalidam o conjunto; lista vazia = tudo rastreavel."""
    problemas = []
    for c in claims:
        if not c.evidencias:
            problemas.append(f"{c.id}: claim sem evidencia")
            continue
        for ev in c.evidencias:
            existe = ev in (g.arestas if c.tipo == "vinculo" else g.entidades)
            if not existe:
                problemas.append(f"{c.id}: evidencia inexistente no grafo: {ev}")
        if c.tipo == "vinculo":
            a = g.arestas.get(c.evidencias[0])
            if a is not None and not a.fontes:
                problemas.append(f"{c.id}: aresta sem fonte")
    return problemas


def como_json(claims: list[Claim]) -> str:
    return json.dumps([c.dict() for c in claims], ensure_ascii=False, indent=2)
