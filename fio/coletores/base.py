"""Infraestrutura comum dos coletores.

Tres garantias valem para todos, sem excecao:
1. o coletor so roda se o alvo estiver no escopo do caso;
2. toda resposta bruta vai para o ledger antes de virar interpretacao;
3. nenhum coletor toca o alvo -- so fontes de terceiros e material
   publicado. Coleta passiva nao e preferencia estetica: contato com o
   alvo avisa o alvo.
"""

from __future__ import annotations

import gzip
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from ..politica import Caso, ViolacaoDeEscopo
from ..grafo.modelo import Grafo, Entidade, Fonte
from ..evidencia.ledger import Ledger
from ..evidencia.cache import CacheHTTP

UA = ("Mozilla/5.0 (X11; Linux x86_64) FIO-OSINT/1.0 "
      "(coleta passiva; contato do responsavel no caso)")

REGISTRO: dict[str, "Coletor"] = {}


@dataclass
class Achado:
    """Um vinculo proposto por um coletor, ainda nao inserido no grafo."""
    origem: Entidade
    relacao: str
    destino: Entidade
    fonte: Fonte
    observacao: str = ""


@dataclass
class Contexto:
    caso: Caso
    grafo: Grafo
    ledger: Ledger
    cache: CacheHTTP
    permitir_rede: bool = True
    intervalo: float = 1.5           # segundos entre requisicoes por host
    timeout: int = 20
    segredos: dict = field(default_factory=dict)
    _ultimo: dict = field(default_factory=dict)

    def http(self) -> "ClienteHTTP":
        return ClienteHTTP(self)


class ClienteHTTP:
    """GET com cache, rate limit por host e gravacao no ledger."""

    def __init__(self, ctx: Contexto):
        self.ctx = ctx

    def _contexto_ssl(self) -> ssl.SSLContext | None:
        bundle = os.environ.get("FIO_CA_BUNDLE") or os.environ.get("REQUESTS_CA_BUNDLE")
        if bundle and os.path.exists(bundle):
            return ssl.create_default_context(cafile=bundle)
        return None

    def get(self, url: str, coletor: str, cabecalhos: dict | None = None,
            aceitar_json: bool = True) -> tuple[int, bytes]:
        if not self.ctx.permitir_rede:
            raise PermissionError("rede desabilitada para este caso (modo offline)")

        em_cache = self.ctx.cache.obter(url)
        if em_cache:
            self.ctx.ledger.registrar(
                "coleta.cache", alvo=url, coletor=coletor,
                resumo=f"HTTP {em_cache[0]} servido do cache local",
                artefato=em_cache[1])
            return em_cache

        host = url.split("/")[2] if "://" in url else url
        agora = time.time()
        ultimo = self.ctx._ultimo.get(host, 0.0)
        if agora - ultimo < self.ctx.intervalo:
            time.sleep(self.ctx.intervalo - (agora - ultimo))
        self.ctx._ultimo[host] = time.time()

        cab = {"User-Agent": UA, "Accept-Encoding": "gzip",
               "Accept": "application/json, text/html;q=0.8"
                         if aceitar_json else "text/html"}
        cab.update(cabecalhos or {})
        req = urllib.request.Request(url, headers=cab, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=self.ctx.timeout,
                                        context=self._contexto_ssl()) as r:
                corpo = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    corpo = gzip.decompress(corpo)
                status = r.status
        except urllib.error.HTTPError as e:
            corpo, status = e.read() or b"", e.code
        except Exception as e:                    # rede, DNS, TLS, timeout
            self.ctx.ledger.registrar(
                "coleta.falha", alvo=url, coletor=coletor,
                resumo=f"{type(e).__name__}: {e}")
            return (0, b"")

        self.ctx.cache.guardar(url, status, corpo)
        self.ctx.ledger.registrar(
            "coleta.http", alvo=url, coletor=coletor,
            resumo=f"HTTP {status}, {len(corpo)} bytes",
            artefato=corpo, metadados={"url": url, "status": status})
        return (status, corpo)

    def get_json(self, url: str, coletor: str,
                 cabecalhos: dict | None = None) -> tuple[int, dict | list | None]:
        status, corpo = self.get(url, coletor, cabecalhos)
        if not corpo:
            return status, None
        try:
            return status, json.loads(corpo.decode("utf-8", "replace"))
        except json.JSONDecodeError:
            return status, None


class Coletor:
    nome: str = "base"
    descricao: str = ""
    tipos_alvo: tuple[str, ...] = ()
    requer_rede: bool = True
    requer_segredo: str | None = None
    admiralty: str = "F6"
    reserva: str = ""              # limite conhecido, vai para o relatorio
    estagio: str = "enriquecimento"   # ingestao|normalizacao|enriquecimento
    origem: str = "interno"           # interno | plugin:<arquivo>
    so_brasil: bool = False

    def aplicavel(self, entidade: Entidade) -> bool:
        return entidade.tipo in self.tipos_alvo

    def coletar(self, alvo: Entidade, ctx: Contexto) -> list[Achado]:
        raise NotImplementedError

    # -------------------------------------------------------------- runner
    def executar(self, alvo: Entidade, ctx: Contexto) -> list[Achado]:
        ctx.caso.autorizar(alvo.valor)
        if self.requer_rede and not ctx.permitir_rede:
            ctx.ledger.registrar("coletor.pulado", alvo=alvo.valor,
                                 coletor=self.nome, resumo="modo offline")
            return []
        if self.requer_segredo and not ctx.segredos.get(self.requer_segredo):
            ctx.ledger.registrar(
                "coletor.pulado", alvo=alvo.valor, coletor=self.nome,
                resumo=f"segredo '{self.requer_segredo}' nao configurado")
            return []
        ctx.ledger.registrar("coletor.inicio", alvo=alvo.valor, coletor=self.nome)
        try:
            achados = self.coletar(alvo, ctx)
        except ViolacaoDeEscopo:
            raise
        except Exception as e:
            ctx.ledger.registrar("coletor.erro", alvo=alvo.valor,
                                 coletor=self.nome,
                                 resumo=f"{type(e).__name__}: {e}")
            return []
        ctx.ledger.registrar("coletor.fim", alvo=alvo.valor, coletor=self.nome,
                             resumo=f"{len(achados)} achados")
        return achados


def registrar(cls):
    """Decorador de registro."""
    inst = cls()
    REGISTRO[inst.nome] = inst
    return cls
