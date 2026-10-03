"""Motor de investigacao: pivota a partir dos alvos ate a profundidade dada.

A logica e a de qualquer investigacao manual, so que registrada: pega o
que se sabe, pergunta a cada fonte aplicavel, guarda o que voltou, e usa o
que voltou como nova pergunta. O limite de profundidade existe porque o
grafo explode em dois saltos -- e porque cada salto afasta o material do
alvo autorizado. O escopo do caso continua valendo em cada pivo.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from .caso import CasoEmDisco, segredos
from .coletores import REGISTRO, Contexto
from .politica import ViolacaoDeEscopo


@dataclass
class Resultado:
    executados: list[str] = field(default_factory=list)
    pulados: list[tuple[str, str]] = field(default_factory=list)
    novas_entidades: int = 0
    novas_arestas: int = 0
    alvos_visitados: list[str] = field(default_factory=list)
    bloqueados: list[str] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)


def investigar(cd: CasoEmDisco, ator: str, coletores: list[str] | None = None,
               profundidade: int = 1, permitir_rede: bool = True,
               intervalo: float = 1.5, expandir: bool = False,
               segredos_extra: dict | None = None,
               log=lambda s: None, paralelo: int = 4,
               orcamento: float | None = None, rapido: bool = False) -> Resultado:
    """paralelo: coletores de REDE de um mesmo alvo rodam em ate N threads
    (o intervalo por host continua valendo); os locais rodam em sequencia.
    orcamento: segundos de coleta; esgotado, para de abrir novas consultas.
    rapido: fontes mais lentas fazem menos consultas (ex.: 3 recortes de busca)."""
    caso = cd.caso()
    grafo = cd.grafo()
    ledger = cd.ledger(ator)
    cache = cd.cache()
    ctx = Contexto(caso=caso, grafo=grafo, ledger=ledger, cache=cache,
                   permitir_rede=permitir_rede, intervalo=intervalo,
                   rapido=rapido,
                   segredos={**segredos(), **(segredos_extra or {})})
    inicio = time.monotonic()

    ordem = {"ingestao": 0, "normalizacao": 1, "enriquecimento": 2}
    nomes = sorted(coletores or list(REGISTRO),
                   key=lambda n: (ordem.get(getattr(REGISTRO.get(n), "estagio", ""), 9), n))
    res = Resultado()
    antes_e, antes_a = len(grafo.entidades), len(grafo.arestas)

    fila = [e.id for e in grafo.entidades.values() if e.alvo_primario]
    visitados: set[str] = set()
    escopo_mudou = False

    for nivel in range(profundidade + 1):
        if not fila:
            break
        atual, fila = fila, []
        log(f"nivel {nivel}: {len(atual)} entidade(s) na fila")
        for eid in atual:
            if eid in visitados or eid not in grafo.entidades:
                continue
            visitados.add(eid)
            alvo = grafo.entidades[eid]

            # O escopo vale em cada pivo, nao so nos alvos iniciais. Uma
            # entidade derivada so vira alvo de coleta se o responsavel
            # autorizar a expansao -- que fica registrada no ledger.
            try:
                caso.autorizar(alvo.valor)
            except ViolacaoDeEscopo as e:
                if expandir and nivel > 0:
                    caso.escopo.append(alvo.valor)
                    escopo_mudou = True       # grava uma vez no fim, nao a cada pivo
                    ledger.registrar(
                        "escopo.expandido", alvo=alvo.valor,
                        resumo=f"derivada de coleta no nivel {nivel}; "
                               f"incluida no escopo por --expandir-escopo")
                    log(f"  escopo expandido para {alvo.valor}")
                else:
                    res.bloqueados.append(alvo.valor)
                    ledger.registrar("pivo.bloqueado", alvo=alvo.valor,
                                     resumo=str(e))
                    continue
            res.alvos_visitados.append(eid)

            if orcamento is not None and time.monotonic() - inicio > orcamento:
                ledger.registrar("orcamento.esgotado", alvo=alvo.valor,
                                 resumo=f"{orcamento:.0f} s de coleta; alvo e seguintes nao consultados")
                log(f"  orcamento de {orcamento:.0f} s esgotado")
                fila = []
                break

            aplicaveis = [REGISTRO[n] for n in nomes
                          if REGISTRO.get(n) and REGISTRO[n].aplicavel(alvo)]
            locais = [c for c in aplicaveis if not c.requer_rede]
            rede = [c for c in aplicaveis if c.requer_rede]

            resultados: dict[str, list] = {}

            def _rodar(col):
                return col.executar(alvo, ctx)

            for col in locais:
                try:
                    resultados[col.nome] = _rodar(col)
                except Exception as e:           # escopo, parsing
                    res.erros.append(f"{col.nome}/{alvo.valor}: {e}")
            if rede:
                if paralelo > 1 and len(rede) > 1:
                    with ThreadPoolExecutor(max_workers=min(paralelo, len(rede))) as ex:
                        futuros = [(c, ex.submit(_rodar, c)) for c in rede]
                        for col, fut in futuros:
                            try:
                                resultados[col.nome] = fut.result()
                            except Exception as e:
                                res.erros.append(f"{col.nome}/{alvo.valor}: {e}")
                else:
                    for col in rede:
                        try:
                            resultados[col.nome] = _rodar(col)
                        except Exception as e:
                            res.erros.append(f"{col.nome}/{alvo.valor}: {e}")

            # o grafo e alterado so aqui, na thread principal e na ordem
            # declarada dos coletores: o resultado nao depende de quem
            # terminou primeiro
            for nome in nomes:
                if nome not in resultados:
                    continue
                achados = resultados[nome]
                if nome not in res.executados:
                    res.executados.append(nome)
                log(f"  {nome} -> {alvo.valor}: {len(achados)} achado(s)")
                for a in achados:
                    novo = a.destino.id not in grafo.entidades
                    grafo.ligar(a.origem, a.destino, a.relacao, a.fonte,
                                a.observacao)
                    if novo and nivel < profundidade:
                        fila.append(a.destino.id)

    if escopo_mudou:
        cd.salvar_caso(caso)
    cd.salvar_grafo(grafo)
    res.novas_entidades = len(grafo.entidades) - antes_e
    res.novas_arestas = len(grafo.arestas) - antes_a
    ledger.registrar(
        "investigacao.concluida",
        resumo=(f"{res.novas_entidades} entidades e {res.novas_arestas} "
                f"vinculos novos; coletores: {', '.join(res.executados)}"),
        metadados={"profundidade": profundidade,
                   "visitados": len(res.alvos_visitados),
                   "erros": res.erros})
    cache.fechar()
    return res
