"""Versao Markdown do relatorio, para anexar a peca ou versionar em git."""

from __future__ import annotations

import datetime as dt

from ..grafo.modelo import Grafo
from ..grafo.clusters import detectar_clusters, tabela_correlacao, pontes
from ..coletores import REGISTRO


def gerar_markdown(caso, g: Grafo, ledger_regs: list,
                   verificacao: tuple[bool, list]) -> str:
    ok, problemas = verificacao
    alvos = [e for e in g.entidades.values() if e.alvo_primario]
    clusters = detectar_clusters(g)
    L: list[str] = []
    A = L.append

    A(f"# {caso.titulo}")
    A(f"\nCaso `{caso.id}` · relatorio de analise de vinculo · "
      f"{dt.datetime.now().strftime('%d/%m/%Y %H:%M')} · "
      f"responsavel: {caso.responsavel}\n")

    A("## 1. Mandato e limites\n")
    A(f"- **Base legal:** {caso.base_legal_texto()}")
    A(f"- **Finalidade:** {caso.finalidade}")
    A(f"- **Escopo autorizado:** {', '.join(caso.escopo)}")
    A(f"- **Validade:** {caso.expira_em}"
      + (" **(EXPIRADO)**" if caso.expirado else ""))
    A("\n> Material obtido de fontes abertas e registros publicos, sem "
      "contato com as pessoas analisadas e sem acesso a sistema protegido. "
      "Vinculo = coocorrencia documentada entre identificadores, nao relacao "
      "comprovada. Verifique na fonte primaria antes de qualquer decisao.\n")

    A("## 2. Panorama\n")
    A(f"| metrica | valor |\n|---|---|")
    A(f"| alvos primarios | {len(alvos)} |")
    A(f"| entidades | {len(g.entidades)} |")
    A(f"| vinculos | {len(g.arestas)} |")
    A(f"| alta confianca | {len([a for a in g.arestas.values() if a.nivel=='alta'])} |")
    A(f"| agrupamentos | {len(clusters)} |\n")

    p = pontes(g)
    if p:
        A("## 3. O que liga os alvos\n")
        for x in p:
            via = " → ".join(i["rotulo"] for i in x["intermediarios"]) or "ligacao direta"
            A(f"- `{x['de']}` ⟷ `{x['para']}` ({x['saltos']} salto(s), elo mais "
              f"fraco {x['elo_mais_fraco']}) via **{via}**")
        A("")

    A("## 4. Agrupamentos\n")
    for c in clusters[:20]:
        A(f"### {c.tipo} — `{c.chave}` (forca {c.forca})\n")
        A(c.explicacao)
        A(f"\n> Ressalva: {c.ressalva}\n")
        A("Membros: " + ", ".join(f"`{m}`" for m in c.membros) + "\n")

    A("## 5. Tabela de correlacao\n")
    A("| entidade | relacao | vinculada a | confianca | nivel | fontes |")
    A("|---|---|---|---|---|---|")
    for l in tabela_correlacao(g)[:200]:
        A(f"| `{l['entidade']}` | {l['relacao']} | `{l['vinculada_a']}` | "
          f"{l['confianca']} | {l['nivel']} | {l['coletores']} |")

    A("\n## 6. Reservas das fontes\n")
    for nome in sorted({f.coletor for a in g.arestas.values() for f in a.fontes}):
        col = REGISTRO.get(nome)
        if col:
            A(f"- **{nome}** ({col.admiralty}): {col.reserva}")

    A("\n## 7. Cadeia de custodia\n")
    A(f"{len(ledger_regs)} registros encadeados. Verificacao: "
      f"{'integra' if ok else 'COMPROMETIDA'}.")
    for x in problemas:
        A(f"- {x}")
    if ledger_regs:
        A(f"\nHash do ultimo registro: `{ledger_regs[-1].hash}`")
    return "\n".join(L) + "\n"
