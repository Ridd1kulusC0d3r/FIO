"""Modelo de entidades e vinculos com proveniencia obrigatoria.

Regra dura: toda aresta nasce com pelo menos uma Fonte. Vinculo sem fonte
e opiniao, e opiniao nao entra no grafo.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
from collections import deque
from dataclasses import dataclass, field, asdict

from .scoring import score_admiralty, combinar, rotulo, descrever

TIPOS = ("telefone", "pessoa", "organizacao", "email", "dominio", "cnpj",
         "cpf-parcial", "endereco", "perfil", "url", "faixa", "documento")


@dataclass
class Fonte:
    coletor: str
    admiralty: str = "F6"
    url: str = ""
    ts: str = ""
    artefato_sha256: str = ""
    nota: str = ""

    def __post_init__(self) -> None:
        self.ts = self.ts or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        self.admiralty = (self.admiralty or "F6").upper()

    @property
    def score(self) -> float:
        return score_admiralty(self.admiralty)

    def dict(self) -> dict:
        d = asdict(self)
        d["score"] = self.score
        d["admiralty_texto"] = descrever(self.admiralty)
        return d


@dataclass
class Entidade:
    tipo: str
    valor: str          # forma canonica; e a chave
    rotulo: str = ""
    atributos: dict = field(default_factory=dict)
    fontes: list[Fonte] = field(default_factory=list)
    alvo_primario: bool = False

    @property
    def id(self) -> str:
        return f"{self.tipo}:{self.valor}"

    def dict(self) -> dict:
        return {"id": self.id, "tipo": self.tipo, "valor": self.valor,
                "rotulo": self.rotulo or self.valor,
                "atributos": self.atributos,
                "alvo_primario": self.alvo_primario,
                "fontes": [f.dict() for f in self.fontes]}


@dataclass
class Aresta:
    origem: str         # Entidade.id
    destino: str
    relacao: str
    fontes: list[Fonte] = field(default_factory=list)
    observacao: str = ""
    dirigida: bool = True

    @property
    def id(self) -> str:
        return f"{self.origem}|{self.relacao}|{self.destino}"

    @property
    def confianca(self) -> float:
        # OU-ruidoso pressupoe independencia. Duas leituras da MESMA fonte
        # nao sao duas confirmacoes: agrupa-se por coletor e toma-se o
        # melhor de cada um antes de combinar.
        melhor: dict[str, float] = {}
        for f in self.fontes:
            melhor[f.coletor] = max(melhor.get(f.coletor, 0.0), f.score)
        return combinar(list(melhor.values()))

    @property
    def fontes_independentes(self) -> int:
        return len({f.coletor for f in self.fontes})

    @property
    def nivel(self) -> str:
        return rotulo(self.confianca)

    def dict(self) -> dict:
        return {"id": self.id, "origem": self.origem, "destino": self.destino,
                "relacao": self.relacao, "observacao": self.observacao,
                "confianca": self.confianca, "nivel": self.nivel,
                "corroboracoes": len(self.fontes),
                "fontes": [f.dict() for f in self.fontes]}


class Grafo:
    def __init__(self, caso: str = ""):
        self.caso = caso
        self.entidades: dict[str, Entidade] = {}
        self.arestas: dict[str, Aresta] = {}
        # achados analiticos que nao sao vinculo (incoerencias, alertas)
        self.observacoes: list[dict] = []

    def observar(self, tipo: str, texto: str, entidades: list[str],
                 gravidade: str = "info", analisador: str = "") -> None:
        chave = (tipo, tuple(sorted(entidades)))
        if any((o["tipo"], tuple(sorted(o["entidades"]))) == chave
               for o in self.observacoes):
            return
        self.observacoes.append({"tipo": tipo, "texto": texto,
                                 "entidades": entidades,
                                 "gravidade": gravidade,
                                 "analisador": analisador})

    # ------------------------------------------------------------ escrita
    def add_entidade(self, e: Entidade) -> Entidade:
        existente = self.entidades.get(e.id)
        if existente:
            existente.atributos.update({k: v for k, v in e.atributos.items() if v})
            existente.fontes.extend(e.fontes)
            existente.alvo_primario = existente.alvo_primario or e.alvo_primario
            if e.rotulo and not existente.rotulo:
                existente.rotulo = e.rotulo
            return existente
        self.entidades[e.id] = e
        return e

    def add_aresta(self, a: Aresta) -> Aresta:
        for ponta in (a.origem, a.destino):
            if ponta not in self.entidades:
                raise KeyError(f"entidade inexistente no grafo: {ponta}")
        existente = self.arestas.get(a.id)
        if existente:
            # corroboracao: fontes distintas somam confianca
            conhecidas = {(f.coletor, f.url, f.nota) for f in existente.fontes}
            for f in a.fontes:
                if (f.coletor, f.url, f.nota) not in conhecidas:
                    existente.fontes.append(f)
            return existente
        self.arestas[a.id] = a
        return a

    def ligar(self, origem: Entidade, destino: Entidade, relacao: str,
              fonte: Fonte, observacao: str = "") -> Aresta:
        o = self.add_entidade(origem)
        d = self.add_entidade(destino)
        return self.add_aresta(Aresta(o.id, d.id, relacao, [fonte], observacao))

    # ------------------------------------------------------------ leitura
    def _adjacencia(self) -> dict[str, list[tuple[Aresta, str]]]:
        """Vizinhanca por entidade, calculada uma vez e reaproveitada.

        `vizinhos` varria TODAS as arestas a cada chamada (O(E)); os
        analisadores e o calculo de pontes chamam isso milhares de vezes. A
        chave de cache (numero de arestas e de entidades) invalida sozinha
        quando o grafo cresce.
        """
        chave = (len(self.arestas), len(self.entidades))
        if getattr(self, "_adj_chave", None) != chave:
            adj: dict[str, list[tuple[Aresta, str]]] = {k: [] for k in self.entidades}
            for a in self.arestas.values():
                adj.setdefault(a.origem, []).append((a, a.destino))
                adj.setdefault(a.destino, []).append((a, a.origem))
            self._adj, self._adj_chave = adj, chave
        return self._adj

    def vizinhos(self, eid: str) -> list[tuple[Aresta, str]]:
        return list(self._adjacencia().get(eid, ()))

    def por_tipo(self, tipo: str) -> list[Entidade]:
        return [e for e in self.entidades.values() if e.tipo == tipo]

    def componentes(self) -> list[list[str]]:
        """Componentes conexos, maior primeiro."""
        adj = {k: {o for _, o in v} for k, v in self._adjacencia().items()}
        vistos: set[str] = set()
        comps: list[list[str]] = []
        for no in self.entidades:
            if no in vistos:
                continue
            pilha, comp = [no], []
            vistos.add(no)
            while pilha:
                atual = pilha.pop()
                comp.append(atual)
                for viz in adj[atual]:
                    if viz not in vistos:
                        vistos.add(viz)
                        pilha.append(viz)
            comps.append(sorted(comp))
        return sorted(comps, key=len, reverse=True)

    def caminho(self, origem: str, destino: str) -> list[str] | None:
        """Menor caminho entre duas entidades: o 'como esses dois se ligam'."""
        if origem not in self.entidades or destino not in self.entidades:
            return None
        adj = self._adjacencia()
        # BFS guardando o antecessor: reconstroi o caminho no fim, sem copiar
        # uma lista por nó visitado como antes
        antes = {origem: None}
        fila = deque([origem])
        while fila:
            atual = fila.popleft()
            if atual == destino:
                cam = []
                while atual is not None:
                    cam.append(atual)
                    atual = antes[atual]
                return cam[::-1]
            for _, viz in adj.get(atual, ()):
                if viz not in antes:
                    antes[viz] = atual
                    fila.append(viz)
        return None

    def grau(self) -> dict[str, int]:
        g = {k: 0 for k in self.entidades}
        for a in self.arestas.values():
            g[a.origem] += 1
            g[a.destino] += 1
        return g

    # ---------------------------------------------------------- exportacao
    def dict(self) -> dict:
        return {"caso": self.caso,
                "entidades": [e.dict() for e in self.entidades.values()],
                "arestas": [a.dict() for a in self.arestas.values()],
                "observacoes": self.observacoes}

    def json(self) -> str:
        return json.dumps(self.dict(), ensure_ascii=False, indent=2)

    def csv_arestas(self) -> str:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["origem_tipo", "origem", "relacao", "destino_tipo",
                    "destino", "confianca", "nivel", "corroboracoes",
                    "coletores", "observacao"])
        for a in sorted(self.arestas.values(), key=lambda x: -x.confianca):
            o = self.entidades[a.origem]
            d = self.entidades[a.destino]
            w.writerow([o.tipo, o.valor, a.relacao, d.tipo, d.valor,
                        a.confianca, a.nivel, len(a.fontes),
                        ";".join(sorted({f.coletor for f in a.fontes})),
                        a.observacao])
        return buf.getvalue()

    @staticmethod
    def de_dict(d: dict) -> "Grafo":
        g = Grafo(d.get("caso", ""))
        for e in d.get("entidades", []):
            g.entidades[e["id"]] = Entidade(
                tipo=e["tipo"], valor=e["valor"], rotulo=e.get("rotulo", ""),
                atributos=e.get("atributos", {}),
                alvo_primario=e.get("alvo_primario", False),
                fontes=[Fonte(**{k: v for k, v in f.items()
                                 if k in ("coletor", "admiralty", "url", "ts",
                                          "artefato_sha256", "nota")})
                        for f in e.get("fontes", [])])
        for a in d.get("arestas", []):
            g.arestas[a["id"]] = Aresta(
                origem=a["origem"], destino=a["destino"], relacao=a["relacao"],
                observacao=a.get("observacao", ""),
                fontes=[Fonte(**{k: v for k, v in f.items()
                                 if k in ("coletor", "admiralty", "url", "ts",
                                          "artefato_sha256", "nota")})
                        for f in a.get("fontes", [])])
        g.observacoes = list(d.get("observacoes", []))
        return g
