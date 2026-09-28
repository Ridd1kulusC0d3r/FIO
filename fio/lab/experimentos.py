"""Rastreador de experimentos.

Todo pipeline executado vira um experimento: parametros, assinatura do
codigo, versao de cada fonte local, metricas por estagio e o SHA-256 do
grafo resultante. Com isso da para responder, meses depois, as perguntas
que um contraditorio (ou um revisor de artigo) faz: "rodando de novo, sai
o mesmo resultado?" e "o que mudou entre a versao de marco e a de maio?".
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import secrets
from dataclasses import dataclass, field, asdict
from pathlib import Path

from ..grafo.modelo import Grafo


def _agora() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def sha_grafo(g: Grafo) -> str:
    """Hash canonico do CONTEUDO: ignora timestamps de coleta."""
    ents = sorted((e.id, json.dumps(e.atributos, sort_keys=True, default=str))
                  for e in g.entidades.values())
    ars = sorted((a.id, round(a.confianca, 4)) for a in g.arestas.values())
    corpo = json.dumps({"e": ents, "a": ars}, sort_keys=True).encode()
    return hashlib.sha256(corpo).hexdigest()


@dataclass
class Experimento:
    id: str
    caso: str
    descricao: str = ""
    inicio: str = ""
    fim: str = ""
    duracao_s: float = 0.0
    parametros: dict = field(default_factory=dict)
    codigo: dict = field(default_factory=dict)
    fontes: dict = field(default_factory=dict)
    estagios: list = field(default_factory=list)
    metricas: dict = field(default_factory=dict)
    grafo_sha256: str = ""
    ledger_seq: list = field(default_factory=list)   # [inicio, fim]
    estado: str = "em-andamento"
    erro: str = ""

    def dict(self) -> dict:
        return asdict(self)


class Registro:
    def __init__(self, dir_caso: Path):
        self.dir = Path(dir_caso) / "experimentos"
        self.dir.mkdir(parents=True, exist_ok=True)

    def novo(self, caso: str, descricao: str, parametros: dict) -> Experimento:
        eid = dt.datetime.now().strftime("EXP-%Y%m%d-%H%M%S-") + secrets.token_hex(2)
        return Experimento(id=eid, caso=caso, descricao=descricao,
                           inicio=_agora(), parametros=parametros)

    def salvar(self, exp: Experimento, g: Grafo | None = None) -> None:
        (self.dir / f"{exp.id}.json").write_text(
            json.dumps(exp.dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        if g is not None:
            (self.dir / f"{exp.id}.grafo.json").write_text(g.json(), encoding="utf-8")

    def listar(self) -> list[Experimento]:
        out = []
        for arq in sorted(self.dir.glob("EXP-*.json")):
            if arq.name.endswith(".grafo.json"):
                continue
            out.append(Experimento(**json.loads(arq.read_text(encoding="utf-8"))))
        return out

    def obter(self, eid: str) -> Experimento:
        return Experimento(**json.loads((self.dir / f"{eid}.json").read_text(encoding="utf-8")))

    def grafo(self, eid: str) -> Grafo:
        return Grafo.de_dict(json.loads(
            (self.dir / f"{eid}.grafo.json").read_text(encoding="utf-8")))

    def comparar(self, a: str, b: str) -> dict:
        ga, gb = self.grafo(a), self.grafo(b)
        ea, eb = set(ga.entidades), set(gb.entidades)
        aa, ab = set(ga.arestas), set(gb.arestas)
        mudou = []
        for k in aa & ab:
            ca, cb = ga.arestas[k].confianca, gb.arestas[k].confianca
            if abs(ca - cb) >= 0.05:
                mudou.append({"aresta": k, "antes": ca, "depois": cb})
        xa, xb = self.obter(a), self.obter(b)
        return {
            "a": a, "b": b,
            "mesmo_resultado": xa.grafo_sha256 == xb.grafo_sha256,
            "mesmo_codigo": xa.codigo.get("sha256_pacote") == xb.codigo.get("sha256_pacote"),
            "fontes_alteradas": sorted(k for k in set(xa.fontes) | set(xb.fontes)
                                       if xa.fontes.get(k) != xb.fontes.get(k)),
            "entidades_novas": sorted(eb - ea), "entidades_removidas": sorted(ea - eb),
            "vinculos_novos": sorted(ab - aa), "vinculos_removidos": sorted(aa - ab),
            "confianca_alterada": sorted(mudou, key=lambda x: -abs(x["depois"] - x["antes"])),
        }
