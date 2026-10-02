"""Pipeline em estagios.

  preparacao -> coleta (ingestao/normalizacao/enriquecimento) -> analise -> relatorio

Cada estagio devolve metricas proprias e o conjunto vira um Experimento.
As metricas de rede (requisicoes, cache, falhas, pivos bloqueados) saem do
proprio ledger, para que o numero reportado seja o numero auditavel.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from ..caso import CasoEmDisco
from ..motor import investigar
from ..analise import ANALISADORES
from ..grafo.clusters import detectar_clusters, pontes
from ..receitas import versoes_fontes
from ..caso import raiz
from . import plugins
from .experimentos import Experimento, Registro, sha_grafo


@dataclass
class Config:
    coletores: list[str] | None = None
    analisadores: list[str] | None = None
    profundidade: int = 1
    offline: bool = False
    expandir_escopo: bool = False
    intervalo: float = 1.5
    paralelo: int = 4                     # coletores de rede simultaneos por alvo
    orcamento: float | None = None        # segundos de coleta (None = sem limite)
    rapido: bool = False                  # modo leve: menos consultas por fonte
    relatorio: str | None = None          # caminho .html
    laudo: str | None = None              # caminho .html do laudo
    modelo_laudo: str = "laudo"
    descricao: str = ""
    extras: dict = field(default_factory=dict)

    def dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def _contar_ledger(regs, desde: int) -> dict:
    c = {"requisicoes": 0, "cache": 0, "falhas": 0, "pivos_bloqueados": 0,
         "coletores_pulados": 0, "erros_coletor": 0}
    for r in regs:
        if r.seq <= desde:
            continue
        c["requisicoes"] += r.acao == "coleta.http"
        c["cache"] += r.acao == "coleta.cache"
        c["falhas"] += r.acao == "coleta.falha"
        c["pivos_bloqueados"] += r.acao == "pivo.bloqueado"
        c["coletores_pulados"] += r.acao == "coletor.pulado"
        c["erros_coletor"] += r.acao == "coletor.erro"
    return c


def executar(cd: CasoEmDisco, ator: str, cfg: Config,
             log=lambda s: None) -> "Experimento":
    reg = Registro(cd.dir)
    led = cd.ledger(ator)
    plugins.carregar()
    exp = reg.novo(cd.caso_id, cfg.descricao, cfg.dict())
    exp.codigo = plugins.assinatura_codigo()
    exp.fontes = versoes_fontes(raiz())
    seq0 = len(led.registros())
    led.registrar("experimento.inicio", alvo=exp.id, resumo=cfg.descricao,
                  metadados={"parametros": cfg.dict(), "codigo": exp.codigo})
    t_total = time.perf_counter()

    def estagio(nome: str, fn):
        t = time.perf_counter()
        log(f"[{nome}]")
        try:
            m = fn() or {}
            exp.estagios.append({"estagio": nome, "ok": True,
                                 "segundos": round(time.perf_counter() - t, 3), **m})
        except Exception as e:
            exp.estagios.append({"estagio": nome, "ok": False, "erro": str(e),
                                 "segundos": round(time.perf_counter() - t, 3)})
            raise

    try:
        def preparacao():
            c = cd.caso()
            c.autorizar(c.escopo[0]) if c.escopo else None   # valida validade
            g = cd.grafo()
            return {"alvos": len([e for e in g.entidades.values() if e.alvo_primario]),
                    "fontes_locais": len(exp.fontes),
                    "plugins": len(exp.codigo.get("plugins", {}))}
        estagio("preparacao", preparacao)

        def coleta():
            r = investigar(cd, ator, coletores=cfg.coletores,
                           profundidade=cfg.profundidade,
                           permitir_rede=not cfg.offline,
                           intervalo=cfg.intervalo, paralelo=cfg.paralelo,
                           orcamento=cfg.orcamento, rapido=cfg.rapido,
                           expandir=cfg.expandir_escopo,
                           segredos_extra=cfg.extras.get("segredos"), log=log)
            return {"coletores": r.executados, "entidades_novas": r.novas_entidades,
                    "vinculos_novos": r.novas_arestas,
                    "visitados": len(r.alvos_visitados),
                    "bloqueados": len(r.bloqueados), "erros": r.erros[:20]}
        estagio("coleta", coleta)

        def analise():
            g = cd.grafo()
            g.observacoes = []
            nomes = cfg.analisadores or sorted(ANALISADORES)
            por = {}
            for n in nomes:
                if n in ANALISADORES:
                    por[n] = ANALISADORES[n].analisar(g)
            cd.salvar_grafo(g)
            return {"observacoes": por, "clusters": len(detectar_clusters(g)),
                    "pontes": len(pontes(g))}
        estagio("analise", analise)

        def relatorio():
            out = {}
            if cfg.relatorio or cfg.laudo:
                from ..relatorio import gerar_html
                from ..relatorio.laudo import gerar_laudo
                c, g = cd.caso(), cd.grafo()
                regs = led.registros()
                verif = led.verificar()
                if cfg.relatorio:
                    Path(cfg.relatorio).write_text(gerar_html(c, g, regs, verif), encoding="utf-8")
                    out["relatorio"] = cfg.relatorio
                if cfg.laudo:
                    Path(cfg.laudo).write_text(
                        gerar_laudo(c, g, regs, verif, modelo=cfg.modelo_laudo,
                                    experimento=exp.dict()), encoding="utf-8")
                    out["laudo"] = cfg.laudo
            return out
        estagio("relatorio", relatorio)
        exp.estado = "concluido"
    except Exception as e:
        exp.estado = "falhou"
        exp.erro = f"{type(e).__name__}: {e}"

    g = cd.grafo()
    regs = led.registros()
    exp.fim = regs[-1].ts if regs else ""
    exp.duracao_s = round(time.perf_counter() - t_total, 3)
    exp.grafo_sha256 = sha_grafo(g)
    exp.metricas = {
        "entidades": len(g.entidades), "vinculos": len(g.arestas),
        "alta_confianca": len([a for a in g.arestas.values() if a.nivel == "alta"]),
        "componentes": len(g.componentes()), "observacoes": len(g.observacoes),
        **_contar_ledger(regs, seq0),
    }
    fim = led.registrar("experimento.fim", alvo=exp.id,
                        resumo=f"{exp.estado}; grafo {exp.grafo_sha256[:16]}",
                        metadados={"metricas": exp.metricas})
    exp.ledger_seq = [seq0 + 1, fim.seq]
    reg.salvar(exp, g)
    return exp
