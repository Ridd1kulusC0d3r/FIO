"""Relatorio HTML autocontido: um arquivo, sem rede, sem dependencia.

Ordem deliberada das secoes: o que o caso autorizava vem antes do que o
caso encontrou, e as reservas de cada fonte vem antes das conclusoes. Um
relatorio de vinculo que comeca pelo grafo bonito convida o leitor a
acreditar nele.
"""

from __future__ import annotations

import datetime as dt
import html as _h
import json

from ..grafo.modelo import Grafo
from ..grafo.clusters import detectar_clusters, tabela_correlacao, pontes
from ..grafo.scoring import descrever
from ..coletores import REGISTRO
from .layout import posicionar

CORES = {
    "telefone": "#3b82f6", "pessoa": "#f59e0b", "organizacao": "#10b981",
    "email": "#a855f7", "dominio": "#06b6d4", "cnpj": "#14b8a6",
    "url": "#94a3b8", "faixa": "#64748b", "endereco": "#ef4444",
    "documento": "#e11d48", "perfil": "#8b5cf6", "cpf-parcial": "#fb7185",
}
NIVEL_COR = {"alta": "#10b981", "media": "#f59e0b",
             "baixa": "#f97316", "indiciaria": "#94a3b8"}

CSS = """
:root{--bg:#f7f8fa;--card:#fff;--txt:#111827;--mut:#5b6472;--bor:#e3e6ec;
--ac:#1d4ed8;--warn:#fff7ed;--warnb:#fdba74}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){
--bg:#0d1117;--card:#161b22;--txt:#e6edf3;--mut:#9aa4b2;--bor:#2b3240;
--ac:#60a5fa;--warn:#2a1e12;--warnb:#7c4a1e}}
:root[data-theme=dark]{--bg:#0d1117;--card:#161b22;--txt:#e6edf3;
--mut:#9aa4b2;--bor:#2b3240;--ac:#60a5fa;--warn:#2a1e12;--warnb:#7c4a1e}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);font:15px/1.6 -apple-system,
BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 16px 80px}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.02em}
h2{font-size:18px;margin:34px 0 12px;letter-spacing:-.01em}
h3{font-size:15px;margin:18px 0 8px}
.sub{color:var(--mut);font-size:14px;margin:0 0 22px}
.card{background:var(--card);border:1px solid var(--bor);border-radius:12px;
padding:16px 18px;margin:12px 0}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(168px,1fr))}
.kpi{background:var(--card);border:1px solid var(--bor);border-radius:12px;padding:14px}
.kpi b{display:block;font-size:26px;line-height:1.2;letter-spacing:-.02em}
.kpi span{color:var(--mut);font-size:12.5px;text-transform:uppercase;letter-spacing:.04em}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{text-align:left;padding:8px 9px;border-bottom:1px solid var(--bor);
vertical-align:top}
th{color:var(--mut);font-weight:600;font-size:12px;text-transform:uppercase;
letter-spacing:.04em;position:sticky;top:0;background:var(--card)}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.tag{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11.5px;
font-weight:600;color:#fff;white-space:nowrap}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}
.mut{color:var(--mut)}
.aviso{background:var(--warn);border:1px solid var(--warnb);border-radius:10px;
padding:12px 14px;margin:12px 0;font-size:14px}
.barra{height:6px;border-radius:3px;background:var(--bor);overflow:hidden;
min-width:56px;margin-top:5px}
.barra i{display:block;height:100%}
details{border:1px solid var(--bor);border-radius:10px;padding:10px 14px;
margin:8px 0;background:var(--card)}
summary{cursor:pointer;font-weight:600;font-size:14px}
svg{max-width:100%;height:auto;display:block}
.leg{display:flex;flex-wrap:wrap;gap:10px;margin:10px 0;font-size:12.5px;color:var(--mut)}
.leg i{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:5px}
code{background:var(--bg);padding:1px 5px;border-radius:5px;font-size:12.5px}
.ok{color:#10b981;font-weight:600}.ruim{color:#ef4444;font-weight:600}
footer{margin-top:40px;color:var(--mut);font-size:12.5px;border-top:1px solid var(--bor);
padding-top:14px}
@media(max-width:640px){.wrap{padding:18px 14px 60px}h1{font-size:21px}
table{font-size:12.5px}th,td{padding:7px 6px}}
"""


def _e(s) -> str:
    return _h.escape(str(s if s is not None else ""))


def _svg(g: Grafo) -> str:
    ids = list(g.entidades)
    if not ids:
        return "<p class='mut'>Grafo vazio.</p>"
    if len(ids) > 220:
        graus = g.grau()
        ids = sorted(ids, key=lambda i: -graus[i])[:220]
    conj = set(ids)
    arestas = [(a.origem, a.destino, a) for a in g.arestas.values()
               if a.origem in conj and a.destino in conj]
    pos = posicionar(ids, [(o, d) for o, d, _ in arestas])
    graus = g.grau()

    partes = ['<svg viewBox="0 0 1100 680" xmlns="http://www.w3.org/2000/svg" '
              'role="img" aria-label="Grafo de vinculos do caso">']
    for o, d, a in arestas:
        x1, y1 = pos[o]
        x2, y2 = pos[d]
        cor = NIVEL_COR.get(a.nivel, "#94a3b8")
        larg = 1 + a.confianca * 2.6
        tracejado = ' stroke-dasharray="5 4"' if a.confianca < 0.35 else ""
        partes.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{cor}" '
            f'stroke-width="{larg:.2f}" stroke-opacity=".55"{tracejado}>'
            f'<title>{_e(a.relacao)} — confianca {a.confianca} ({_e(a.nivel)})</title></line>')
    for i in ids:
        e = g.entidades[i]
        x, y = pos[i]
        r = 6 + min(13, graus.get(i, 0) * 1.5) + (5 if e.alvo_primario else 0)
        cor = CORES.get(e.tipo, "#94a3b8")
        borda = "#111827" if e.alvo_primario else cor
        rotulo = (e.rotulo or e.valor)[:34]
        partes.append(
            f'<circle cx="{x}" cy="{y}" r="{r:.1f}" fill="{cor}" '
            f'fill-opacity=".9" stroke="{borda}" stroke-width="'
            f'{3 if e.alvo_primario else 1}"><title>{_e(e.tipo)}: {_e(e.valor)}'
            f'</title></circle>')
        partes.append(
            f'<text x="{x}" y="{y + r + 12:.1f}" text-anchor="middle" '
            f'font-size="10.5" fill="currentColor" fill-opacity=".8">'
            f'{_e(rotulo)}</text>')
    partes.append("</svg>")
    return "".join(partes)


def gerar_html(caso, g: Grafo, ledger_regs: list, verificacao: tuple[bool, list],
               coletores_usados: list[str] | None = None) -> str:
    clusters = detectar_clusters(g)
    tabela = tabela_correlacao(g)
    pnt = pontes(g)
    comps = g.componentes()
    alvos = [e for e in g.entidades.values() if e.alvo_primario]
    ok, problemas = verificacao
    agora = dt.datetime.now().strftime("%d/%m/%Y %H:%M")
    usados = coletores_usados or sorted({f.coletor for a in g.arestas.values()
                                         for f in a.fontes})

    tipos: dict[str, int] = {}
    for e in g.entidades.values():
        tipos[e.tipo] = tipos.get(e.tipo, 0) + 1

    P: list[str] = []
    A = P.append
    A("<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>")
    A("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    A(f"<title>F.I.O. — {_e(caso.id)}</title><style>{CSS}</style></head><body>")
    A("<div class='wrap'>")
    A(f"<h1>{_e(caso.titulo)}</h1>")
    A(f"<p class='sub'>Caso <span class='mono'>{_e(caso.id)}</span> · "
      f"relatorio de analise de vinculo · gerado em {agora} · "
      f"responsavel: {_e(caso.responsavel)}</p>")

    # ---------------------------------------------------------- 1. mandato
    A("<h2>1. Mandato e limites da analise</h2><div class='card'>")
    A("<table><tbody>")
    for rot, val in (("Base legal", caso.base_legal_texto()),
                     ("Finalidade declarada", caso.finalidade),
                     ("Escopo autorizado", ", ".join(caso.escopo)),
                     ("Modo de coleta", caso.modo),
                     ("Aberto em", caso.criado_em),
                     ("Validade do escopo", caso.expira_em
                      + (" — EXPIRADO" if caso.expirado else ""))):
        A(f"<tr><th style='width:210px'>{_e(rot)}</th><td>{_e(val)}</td></tr>")
    A("</tbody></table></div>")
    A("<div class='aviso'><b>Natureza do material.</b> Todo o conteudo deste "
      "relatorio provem de fontes abertas e registros publicos, coletados sem "
      "contato com as pessoas analisadas e sem acesso a sistema protegido. "
      "Vinculo aqui significa <i>coocorrencia documentada entre "
      "identificadores</i>, nao relacao juridica, societaria ou pessoal "
      "comprovada. Nenhum item dispensa verificacao na fonte primaria antes "
      "de sustentar decisao, acusacao ou medida contra pessoa.</div>")

    # ---------------------------------------------------------- 2. panorama
    A("<h2>2. Panorama</h2><div class='grid'>")
    for val, rot in ((len(alvos), "alvos primarios"),
                     (len(g.entidades), "entidades"),
                     (len(g.arestas), "vinculos"),
                     (len([a for a in g.arestas.values() if a.nivel == 'alta']),
                      "vinculos de alta confianca"),
                     (len(clusters), "agrupamentos"),
                     (len(comps), "componentes isolados")):
        A(f"<div class='kpi'><b>{val}</b><span>{_e(rot)}</span></div>")
    A("</div>")
    A("<div class='leg'>" + "".join(
        f"<span><i style='background:{CORES.get(t,'#94a3b8')}'></i>{_e(t)} "
        f"({n})</span>" for t, n in sorted(tipos.items(), key=lambda x: -x[1]))
      + "</div>")

    # ------------------------------------------------------------- 3. grafo
    A("<h2>3. Grafo de vinculos</h2><div class='card'>")
    A(_svg(g))
    A("<p class='mut' style='font-size:12.5px;margin:10px 0 0'>Circulo com "
      "contorno escuro = alvo primario. Tamanho = numero de conexoes. "
      "Espessura e cor da linha = confianca do vinculo "
      "(<span style='color:#10b981'>alta</span>, "
      "<span style='color:#f59e0b'>media</span>, "
      "<span style='color:#f97316'>baixa</span>, "
      "<span style='color:#94a3b8'>indiciaria — tracejada</span>). "
      "Passe o cursor sobre qualquer elemento para ver a origem.</p></div>")

    # --------------------------------------------------------- 4. pontes
    if pnt:
        A("<h2>4. O que liga os alvos entre si</h2>")
        for p in pnt:
            inter = " → ".join(
                f"<b>{_e(i['rotulo'])}</b> <span class='mut'>({_e(i['tipo'])})</span>"
                for i in p["intermediarios"]) or "<i>ligacao direta</i>"
            A(f"<div class='card'><b>{_e(p['de'].split(':',1)[1])}</b> "
              f"⟷ <b>{_e(p['para'].split(':',1)[1])}</b> "
              f"<span class='mut'>({p['saltos']} salto(s) · elo mais fraco "
              f"{p['elo_mais_fraco']})</span><br>"
              f"<span style='font-size:14px'>via {inter}</span></div>")

    # ------------------------------------------------------- 5. clusters
    A("<h2>5. Agrupamentos detectados</h2>")
    if not clusters:
        A("<div class='card mut'>Nenhum agrupamento identificado com os "
          "criterios aplicados.</div>")
    for c in clusters[:25]:
        cor = NIVEL_COR["alta"] if c.forca >= .7 else (
            NIVEL_COR["media"] if c.forca >= .45 else NIVEL_COR["baixa"])
        membros = "".join(
            f"<li class='mono'>{_e(m.split(':',1)[1])} "
            f"<span class='mut'>({_e(m.split(':',1)[0])})</span></li>"
            for m in c.membros)
        A(f"<details><summary>{_e(c.tipo)} · <span class='mono'>{_e(c.chave)}"
          f"</span> · {len(c.membros)} membros "
          f"<span class='tag' style='background:{cor}'>forca {c.forca}</span>"
          f"</summary><p>{_e(c.explicacao)}</p>"
          f"<p class='mut'><b>Ressalva:</b> {_e(c.ressalva)}</p>"
          f"<ul>{membros}</ul></details>")

    if g.observacoes:
        A("<h2>5b. Observacoes analiticas</h2>")
        for o in g.observacoes[:40]:
            cor = {"alta": "#ef4444", "atencao": "#f59e0b"}.get(o["gravidade"], "#94a3b8")
            A(f"<div class='card'><span class='tag' style='background:{cor}'>"
              f"{_e(o['gravidade'])}</span> <b>{_e(o['tipo'])}</b> "
              f"<span class='mut'>· {_e(o['analisador'])}</span>"
              f"<p style='margin:6px 0 0'>{_e(o['texto'])}</p></div>")

    # --------------------------------------------- 6. tabela de correlacao
    A("<h2>6. Tabela de correlacao</h2>")
    A("<div class='card scroll'><table><thead><tr>"
      "<th>Entidade</th><th>Relacao</th><th>Vinculada a</th>"
      "<th>Confianca</th><th>Admiralty</th><th>Fontes</th><th>Evidencia</th>"
      "</tr></thead><tbody>")
    for l in tabela[:400]:
        cor = NIVEL_COR.get(l["nivel"], "#94a3b8")
        ev = _e(l["evidencia"])[:160]
        A(f"<tr><td class='mono'>{_e(l['entidade'])}<br>"
          f"<span class='mut'>{_e(l['tipo'])}</span></td>"
          f"<td>{_e(l['relacao'])}</td>"
          f"<td class='mono'>{_e(l['vinculada_a'])}<br>"
          f"<span class='mut'>{_e(l['tipo_vinculo'])}</span></td>"
          f"<td><b>{l['confianca']}</b> "
          f"<span class='tag' style='background:{cor}'>{_e(l['nivel'])}</span>"
          f"<div class='barra'><i style='width:{l['confianca']*100:.0f}%;"
          f"background:{cor}'></i></div>"
          f"<span class='mut'>{l['corroboracoes']} fonte(s)</span></td>"
          f"<td class='mono'>{_e(l['admiralty'])}</td>"
          f"<td>{_e(l['coletores'])}</td>"
          f"<td class='mut' style='max-width:300px;word-break:break-all'>{ev}</td></tr>")
    A("</tbody></table></div>")
    if len(tabela) > 400:
        A(f"<p class='mut'>Exibidas 400 de {len(tabela)} linhas. "
          f"A tabela integral esta no CSV exportado junto a este relatorio.</p>")

    # ------------------------------------------------ 7. ficha dos alvos
    A("<h2>7. Ficha dos alvos primarios</h2>")
    for e in alvos:
        A(f"<div class='card'><h3 class='mono'>{_e(e.rotulo or e.valor)} "
          f"<span class='mut'>({_e(e.tipo)})</span></h3><table><tbody>")
        for k, v in e.atributos.items():
            if k in ("dorks", "variantes"):
                continue
            if isinstance(v, (list, dict)):
                v = json.dumps(v, ensure_ascii=False)[:400]
            A(f"<tr><th style='width:190px'>{_e(k)}</th><td>{_e(v)}</td></tr>")
        A("</tbody></table>")
        if e.atributos.get("variantes"):
            A("<p class='mut' style='margin-top:10px'><b>Grafias pesquisadas:"
              "</b> " + ", ".join(f"<code>{_e(v)}</code>"
                                  for v in e.atributos["variantes"][:14]) + "</p>")
        if e.atributos.get("dorks"):
            A("<details><summary>Consultas geradas para conferencia manual</summary><ul>")
            for d in e.atributos["dorks"]:
                A(f"<li><b>{_e(d['recorte'])}</b>: <code>{_e(d['consulta'])}</code></li>")
            A("</ul></details>")
        A("</div>")

    # --------------------------------------------- 8. reservas das fontes
    A("<h2>8. Reservas de cada fonte utilizada</h2><div class='card'>")
    A("<table><thead><tr><th>Coletor</th><th>Grau</th><th>Reserva</th>"
      "</tr></thead><tbody>")
    for nome in usados:
        col = REGISTRO.get(nome)
        if not col:
            continue
        A(f"<tr><td><b>{_e(nome)}</b><br><span class='mut'>{_e(col.descricao)}"
          f"</span></td><td class='mono'>{_e(descrever(col.admiralty))}</td>"
          f"<td>{_e(col.reserva)}</td></tr>")
    A("</tbody></table></div>")

    # -------------------------------------------------- 9. cadeia de custodia
    A("<h2>9. Cadeia de custodia</h2><div class='card'>")
    estado = ("<span class='ok'>cadeia integra</span>" if ok else
              "<span class='ruim'>CADEIA COMPROMETIDA</span>")
    A(f"<p>{len(ledger_regs)} registros encadeados por SHA-256. "
      f"Estado da verificacao: {estado}.</p>")
    if problemas:
        A("<ul>" + "".join(f"<li class='ruim'>{_e(p)}</li>" for p in problemas) + "</ul>")
    ultimo = ledger_regs[-1].hash if ledger_regs else "-"
    A(f"<p class='mut'>Hash do ultimo registro: <span class='mono'>"
      f"{_e(ultimo)}</span></p>")
    A("<details><summary>Registro cronologico completo</summary>"
      "<div class='scroll'><table><thead><tr><th>#</th><th>Momento (UTC)</th>"
      "<th>Acao</th><th>Coletor</th><th>Alvo</th><th>Resumo</th>"
      "<th>SHA-256 do artefato</th></tr></thead><tbody>")
    for r in ledger_regs:
        A(f"<tr><td>{r.seq}</td><td class='mono'>{_e(r.ts)}</td>"
          f"<td>{_e(r.acao)}</td><td>{_e(r.coletor)}</td>"
          f"<td class='mono' style='max-width:220px;word-break:break-all'>"
          f"{_e(r.alvo)}</td><td>{_e(r.resumo)}</td>"
          f"<td class='mono'>{_e(r.artefato_sha256[:16])}</td></tr>")
    A("</tbody></table></div></details></div>")

    A("<footer>Gerado por F.I.O. — Fontes, Identificadores e Origens. "
      "Coleta passiva de fontes abertas e registros publicos. "
      "Este documento contem dados pessoais: trate conforme a LGPD, "
      "restrinja a distribuicao ao necessario para a finalidade declarada e "
      "elimine ao fim do prazo do caso.</footer>")
    A("</div></body></html>")
    return "".join(P)
