"""Persistencia do caso em disco. Um diretorio, tudo dentro dele."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .politica import Caso
from .grafo.modelo import Grafo, Entidade
from .evidencia.ledger import Ledger
from .evidencia.cache import CacheHTTP


def raiz() -> Path:
    return Path(os.environ.get("FIO_HOME", Path.home() / ".fio"))


class CasoEmDisco:
    def __init__(self, caso_id: str, base: Path | None = None):
        self.dir = (Path(base) if base else raiz() / "casos") / caso_id
        self.caso_id = caso_id

    @property
    def existe(self) -> bool:
        return (self.dir / "caso.json").exists()

    # ------------------------------------------------------------ criacao
    def criar(self, caso: Caso, ator: str) -> "CasoEmDisco":
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "caso.json").write_text(caso.json(), encoding="utf-8")
        led = Ledger(self.dir, caso.id, ator)
        led.registrar("caso.aberto", alvo=caso.id, resumo=caso.titulo,
                      artefato=caso.json(),
                      metadados={"base_legal": caso.base_legal,
                                 "finalidade": caso.finalidade,
                                 "escopo": caso.escopo,
                                 "expira_em": caso.expira_em})
        self.salvar_grafo(Grafo(caso.id))
        return self

    # ------------------------------------------------------------ leitura
    def caso(self) -> Caso:
        d = json.loads((self.dir / "caso.json").read_text(encoding="utf-8"))
        for k in ("base_legal_texto", "expirado"):
            d.pop(k, None)
        return Caso(**d)

    def grafo(self) -> Grafo:
        p = self.dir / "grafo.json"
        if not p.exists():
            return Grafo(self.caso_id)
        return Grafo.de_dict(json.loads(p.read_text(encoding="utf-8")))

    def ledger(self, ator: str = "desconhecido") -> Ledger:
        return Ledger(self.dir, self.caso_id, ator)

    def cache(self, ttl: int = 86400) -> CacheHTTP:
        return CacheHTTP(self.dir / "cache.sqlite", ttl)

    # ------------------------------------------------------------ escrita
    def salvar_grafo(self, g: Grafo) -> None:
        (self.dir / "grafo.json").write_text(g.json(), encoding="utf-8")

    def salvar_caso(self, c: Caso) -> None:
        (self.dir / "caso.json").write_text(c.json(), encoding="utf-8")

    def add_alvo(self, entidade: Entidade, ator: str) -> Grafo:
        g = self.grafo()
        entidade.alvo_primario = True
        g.add_entidade(entidade)
        c = self.caso()
        if entidade.valor not in c.escopo:
            c.escopo.append(entidade.valor)
            self.salvar_caso(c)
        self.salvar_grafo(g)
        self.ledger(ator).registrar(
            "alvo.adicionado", alvo=entidade.valor,
            resumo=f"{entidade.tipo} incluido no escopo do caso")
        return g


def listar_casos() -> list[dict]:
    base = raiz() / "casos"
    if not base.exists():
        return []
    saida = []
    for d in sorted(base.iterdir()):
        arq = d / "caso.json"
        if arq.exists():
            try:
                saida.append(json.loads(arq.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
    return saida


def segredos() -> dict:
    """Config de ~/.fio/config.json sobreposta por variaveis de ambiente."""
    cfg = raiz() / "config.json"
    dados = {}
    if cfg.exists():
        try:
            dados = json.loads(cfg.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            dados = {}
    for chave, var in (("hibp_api_key", "FIO_HIBP_API_KEY"),
                       ("indice_cnpj", "FIO_INDICE_CNPJ"),
                       ("indice_exposicao", "FIO_INDICE_EXPOSICAO")):
        if os.environ.get(var):
            dados[chave] = os.environ[var]
    padrao = raiz() / "cnpj.sqlite"
    if "indice_cnpj" not in dados and padrao.exists():
        dados["indice_cnpj"] = str(padrao)
    return dados
