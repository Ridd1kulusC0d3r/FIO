"""Modelos juridicos brasileiros: Laudo/Parecer Tecnico e RELINT.

O relatorio tecnico (html.py) serve ao analista. Este modulo serve a quem
vai LER o trabalho numa peca: juiz, promotor, delegado, advogado, comite.
Por isso segue a estrutura que esse leitor espera -- preambulo, quesitos,
material, metodologia, exames, respostas, conclusao, encerramento -- e
amarra a cadeia de custodia as dez etapas do art. 158-B do CPP.

Duas cautelas estao embutidas no texto gerado e nao devem ser removidas:
a aplicacao dos arts. 158-A a 158-F a vestigio digital e analogica (o CPP
foi escrito pensando em vestigio fisico), e nenhuma conclusao e redigida
em termos categoricos -- o grau de confianca acompanha cada afirmacao.
"""

from __future__ import annotations

import datetime as dt
import html as _h
from collections import Counter

from ..grafo.modelo import Grafo
from ..grafo.clusters import detectar_clusters, pontes, tabela_correlacao
from ..grafo.scoring import descrever
from ..coletores import REGISTRO

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]

ETAPAS_158B = [
    ("I", "Reconhecimento", "ato de distinguir um elemento como de potencial interesse",
     lambda c: c["caso.aberto"] + c["alvo.adicionado"],
     "abertura do caso e inclusão dos alvos primários, com registro de base legal e finalidade"),
    ("II", "Isolamento", "evitar que se altere o estado das coisas",
     lambda c: c["pivo.bloqueado"] + c["escopo.expandido"],
     "escopo autorizado verificado a cada pivô; coleta exclusivamente passiva, sem contato com o alvo"),
    ("III", "Fixação", "descrição detalhada do vestígio",
     lambda c: c["analise.numero"] + c["analise.dorks"],
     "descrição estrutural de cada identificador (plano de numeração, grafias, bloco)"),
    ("IV", "Coleta", "recolhimento do vestígio",
     lambda c: c["coleta.http"] + c["coleta.cache"],
     "requisições a fontes abertas, com resposta bruta preservada"),
    ("V", "Acondicionamento", "embalagem individualizada",
     lambda c: c["_artefatos"],
     "cada resposta bruta gravada como artefato individual, nomeado pelo próprio SHA-256"),
    ("VI", "Transporte", "transferência com manutenção das características originais",
     lambda c: 0,
     "não houve transporte físico; artefatos gerados e armazenados no mesmo ambiente de análise"),
    ("VII", "Recebimento", "transferência de posse, documentada",
     lambda c: c["_atores"],
     "cada registro identifica o operador responsável (campo ator do ledger)"),
    ("VIII", "Processamento", "exame pericial",
     lambda c: c["coletor.fim"] + c["experimento.fim"],
     "interpretação dos artefatos em vínculos pontuados na escala Admiralty"),
    ("IX", "Armazenamento", "guarda em condições adequadas",
     lambda c: c["_total"],
     "registros encadeados por SHA-256 (append-only), verificáveis por terceiro"),
    ("X", "Descarte", "liberação do vestígio, com autorização quando for o caso",
     lambda c: 0,
     "eliminação prevista ao término da validade do escopo do caso (LGPD, art. 16)"),
]


def _e(s) -> str:
    return _h.escape(str(s if s is not None else ""))


def _data_extenso(d: dt.date) -> str:
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def _grau(conf: float) -> str:
    if conf >= 0.75:
        return "elementos de alta confiança indicam"
    if conf >= 0.5:
        return "elementos de confiança moderada sugerem"
    if conf >= 0.25:
        return "há indícios de baixa confiança de que"
    return "há apenas indício frágil, insuficiente isoladamente, de que"


CSS = """
:root{--bg:#fbfaf7;--card:#fff;--txt:#1a1a1a;--mut:#5d5d5d;--bor:#dedad2;--ac:#7a1f1f}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#121212;
--card:#1b1b1b;--txt:#ececec;--mut:#a3a3a3;--bor:#333;--ac:#e39b9b}}
:root[data-theme=dark]{--bg:#121212;--card:#1b1b1b;--txt:#ececec;--mut:#a3a3a3;
--bor:#333;--ac:#e39b9b}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);
font:16px/1.7 Georgia,"Times New Roman",serif}
.folha{max-width:880px;margin:0 auto;padding:40px 22px 90px}
.classif{text-align:center;font:600 12px/1.4 -apple-system,Segoe UI,sans-serif;
letter-spacing:.12em;color:var(--ac);border:1px solid var(--ac);padding:6px;
margin-bottom:26px;text-transform:uppercase}
h1{font-size:23px;text-align:center;margin:0 0 4px;letter-spacing:.02em}
.sub{text-align:center;color:var(--mut);margin:0 0 30px;font-size:14px}
h2{font-size:17px;margin:34px 0 10px;text-transform:uppercase;letter-spacing:.05em;
border-bottom:1px solid var(--bor);padding-bottom:6px}
p{text-align:justify;margin:10px 0}
table{width:100%;border-collapse:collapse;font:13.5px/1.5 -apple-system,Segoe UI,sans-serif;
margin:10px 0}
th,td{border:1px solid var(--bor);padding:7px 9px;text-align:left;vertical-align:top}
th{background:var(--card);font-weight:600}
.mono{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;word-break:break-all}
.quesito{background:var(--card);border-left:3px solid var(--ac);padding:10px 14px;margin:14px 0}
.mut{color:var(--mut)}
.scroll{overflow-x:auto}
.assin{margin-top:60px;text-align:center}
.assin .linha{border-top:1px solid var(--txt);width:280px;margin:0 auto 6px}
@media(max-width:640px){.folha{padding:24px 14px 60px}body{font-size:15px}
table{font-size:12px}th,td{padding:5px}}
@media print{.classif{border-width:2px}body{background:#fff;color:#000}}
"""


def gerar_laudo(caso, g: Grafo, regs: list, verificacao: tuple[bool, list],
                modelo: str = "laudo", experimento: dict | None = None) -> str:
    ok, problemas = verificacao
    hoje = dt.date.today()
    alvos = [e for e in g.entidades.values() if e.alvo_primario]
    clusters = detectar_clusters(g)
    pnt = pontes(g)
    tabela = tabela_correlacao(g)
    fortes = [l for l in tabela if l["nivel"] in ("alta", "media")]
    cont = Counter(r.acao for r in regs)
    cont["_artefatos"] = len({r.artefato_sha256 for r in regs if r.artefato_sha256})
    cont["_atores"] = len({r.ator for r in regs})
    cont["_total"] = len(regs)
    usados = sorted({f.coletor for a in g.arestas.values() for f in a.fontes})
    relint = modelo == "relint"
    titulo = ("RELATÓRIO DE INTELIGÊNCIA" if relint
              else "LAUDO TÉCNICO DE ANÁLISE DE VÍNCULOS EM FONTES ABERTAS")
    n = 0

    def secao(t: str) -> str:
        nonlocal n
        n += 1
        return f"<h2>{n}. {_e(t)}</h2>"

    P: list[str] = []
    A = P.append
    A("<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
      "<meta name='viewport' content='width=device-width,initial-scale=1'>"
      f"<title>{'RELINT' if relint else 'Laudo'} {_e(caso.id)}</title>"
      f"<style>{CSS}</style></head><body><div class='folha'>")
    A(f"<div class='classif'>{_e(caso.classificacao)}</div>")
    A(f"<h1>{titulo}</h1>")
    A(f"<p class='sub'>{_e(caso.id)}"
      + (f" · Ref.: {_e(caso.referencia)}" if caso.referencia else "")
      + f" · {_data_extenso(hoje)}</p>")

    # ------------------------------------------------------------ preambulo
    if relint:
        A("<table><tbody>"
          f"<tr><th style='width:180px'>Assunto</th><td>{_e(caso.titulo)}</td></tr>"
          f"<tr><th>Referência</th><td>{_e(caso.referencia or '—')}</td></tr>"
          f"<tr><th>Solicitante</th><td>{_e(caso.solicitante or '—')}</td></tr>"
          f"<tr><th>Difusão</th><td>restrita ao solicitante, para a finalidade declarada</td></tr>"
          f"<tr><th>Base legal</th><td>{_e(caso.base_legal_texto())}</td></tr>"
          "</tbody></table>")
        A(secao("Síntese"))
        top = clusters[0] if clusters else None
        A(f"<p>Foram analisados {len(alvos)} identificador(es) primário(s). "
          f"A análise produziu {len(g.entidades)} entidades e {len(g.arestas)} "
          f"vínculos, dos quais {len(fortes)} de confiança média ou alta, e "
          f"{len(clusters)} agrupamento(s). "
          + (f"O agrupamento mais forte ({_e(top.tipo)}, força {top.forca}) "
             f"reúne {len(top.membros)} entidades: {_e(top.explicacao)}"
             if top else "Não se identificou agrupamento.") + "</p>")
    else:
        A(secao("Preâmbulo"))
        A(f"<p>Em {_data_extenso(hoje)}, {_e(caso.responsavel)}"
          + (f", {_e(caso.registro_profissional)}" if caso.registro_profissional else "")
          + (f", atendendo à solicitação de {_e(caso.solicitante)}" if caso.solicitante else "")
          + (f", nos autos/expediente {_e(caso.referencia)}" if caso.referencia else "")
          + f", elaborou o presente laudo técnico, destinado a "
          f"{_e(caso.finalidade)}, com fundamento em {_e(caso.base_legal_texto())}.</p>")

    # ------------------------------------------------------------- quesitos
    A(secao("Objetivo e quesitos"))
    if caso.quesitos:
        for q in caso.quesitos:
            A(f"<div class='quesito'><b>Quesito {q.get('n')}:</b> {_e(q.get('texto'))}</div>")
    else:
        A("<p>Não foram formulados quesitos. O exame buscou identificar e "
          "qualificar vínculos entre os identificadores listados na seção "
          "seguinte, dentro da finalidade declarada.</p>")

    # ------------------------------------------------------------- material
    A(secao("Material examinado"))
    A("<table><thead><tr><th>Tipo</th><th>Identificador</th><th>Observação</th>"
      "</tr></thead><tbody>")
    for e in alvos:
        obs = e.atributos.get("justificativa") or e.atributos.get("caminho") or ""
        A(f"<tr><td>{_e(e.tipo)}</td><td class='mono'>{_e(e.rotulo or e.valor)}</td>"
          f"<td>{_e(obs)}</td></tr>")
    A("</tbody></table>")

    # ----------------------------------------------------------- metodologia
    A(secao("Metodologia"))
    A("<p>O exame foi realizado exclusivamente por coleta passiva em fontes "
      "abertas e registros públicos, sem contato com as pessoas analisadas, "
      "sem uso de credenciais de terceiros e sem acesso a sistema protegido. "
      "Adotaram-se como referência a ABNT NBR ISO/IEC 27037:2013 "
      "(identificação, coleta, aquisição e preservação de evidência digital) "
      "e, por analogia, os arts. 158-A a 158-F do Código de Processo Penal "
      "(cadeia de custódia), cuja redação foi concebida para vestígios "
      "materiais.</p>")
    A("<p>Cada vínculo foi pontuado na escala Admiralty (STANAG 2511): uma "
      "letra para a confiabilidade da fonte (A a F) e um algarismo para a "
      "credibilidade da informação (1 a 6). Fontes independentes que "
      "corroboram o mesmo vínculo são combinadas por OU-ruidoso; leituras "
      "repetidas da mesma fonte não contam como corroboração.</p>")
    A("<table><thead><tr><th>Fonte</th><th>Grau</th><th>Limitação declarada</th>"
      "</tr></thead><tbody>")
    for nome in usados:
        c = REGISTRO.get(nome)
        if c:
            A(f"<tr><td>{_e(nome)}<br><span class='mut'>{_e(c.descricao)}</span></td>"
              f"<td class='mono'>{_e(descrever(c.admiralty))}</td><td>{_e(c.reserva)}</td></tr>")
    A("</tbody></table>")
    if experimento:
        cod = experimento.get("codigo", {})
        A("<p><b>Reprodutibilidade.</b> Execução registrada como experimento "
          f"<span class='mono'>{_e(experimento.get('id'))}</span>, produzida "
          f"pela ferramenta F.I.O. versão {_e(cod.get('versao'))} (SHA-256 do "
          f"código <span class='mono'>{_e(str(cod.get('sha256_pacote', ''))[:24])}…</span>). "
          f"Resultado identificado pelo SHA-256 do grafo "
          f"<span class='mono'>{_e(str(experimento.get('grafo_sha256', ''))[:24])}…</span>.</p>")

    # --------------------------------------------------------------- exames
    A(secao("Exames e resultados"))
    A(f"<p>Foram estabelecidos {len(g.arestas)} vínculos entre {len(g.entidades)} "
      f"entidades. Relacionam-se abaixo os de confiança média ou alta "
      f"({len(fortes)}).</p>")
    A("<div class='scroll'><table><thead><tr><th>Entidade</th><th>Relação</th>"
      "<th>Vinculada a</th><th>Confiança</th><th>Fonte(s)</th></tr></thead><tbody>")
    for l in fortes[:120]:
        A(f"<tr><td class='mono'>{_e(l['entidade'])}</td><td>{_e(l['relacao'])}</td>"
          f"<td class='mono'>{_e(l['vinculada_a'])}</td>"
          f"<td>{l['confianca']} ({_e(l['nivel'])}; {_e(l['admiralty'])})</td>"
          f"<td>{_e(l['coletores'])}</td></tr>")
    A("</tbody></table></div>")
    if clusters:
        A("<p><b>Agrupamentos.</b></p><ol>")
        for c in clusters[:12]:
            A(f"<li><b>{_e(c.tipo)}</b> ({_e(c.chave)}; força {c.forca}): "
              f"{_e(c.explicacao)} <i>Ressalva: {_e(c.ressalva)}</i></li>")
        A("</ol>")
    if g.observacoes:
        A("<p><b>Observações analíticas.</b></p><ul>")
        for o in g.observacoes[:20]:
            A(f"<li>[{_e(o['gravidade'])}] {_e(o['texto'])}</li>")
        A("</ul>")

    # ------------------------------------------------------ cadeia (158-B)
    A(secao("Cadeia de custódia"))
    A(f"<p>O registro de custódia contém {len(regs)} eventos encadeados por "
      f"SHA-256. Verificação de integridade na data deste documento: "
      f"<b>{'íntegra' if ok else 'COMPROMETIDA'}</b>."
      + ("" if ok else " Problemas: " + _e("; ".join(problemas))) + "</p>")
    A("<div class='scroll'><table><thead><tr><th>Etapa (art. 158-B, CPP)</th>"
      "<th>Conteúdo legal</th><th>Correspondência no exame</th><th>Registros</th>"
      "</tr></thead><tbody>")
    for rom, nome, desc, contar, feito in ETAPAS_158B:
        A(f"<tr><td><b>{rom}. {nome}</b></td><td>{_e(desc)}</td>"
          f"<td>{_e(feito)}</td><td>{contar(cont)}</td></tr>")
    A("</tbody></table></div>")
    if regs:
        A(f"<p class='mut'>Hash do último registro: <span class='mono'>"
          f"{_e(regs[-1].hash)}</span>. Prazo de guarda: até {_e(caso.expira_em)}.</p>")

    # ------------------------------------------------------ respostas
    A(secao("Respostas aos quesitos" if caso.quesitos else "Discussão"))
    if caso.quesitos:
        for q in caso.quesitos:
            A(f"<div class='quesito'><b>Quesito {q.get('n')}:</b> {_e(q.get('texto'))}"
              f"<br><b>Resposta:</b> {_e(q.get('resposta') or 'Prejudicado: resposta não registrada pelo analista.')}")
            ids = q.get("entidades") or []
            ligados = [a for a in g.arestas.values()
                       if a.origem in ids or a.destino in ids]
            if ligados:
                A("<br><span class='mut'>Elementos de suporte: " + "; ".join(
                    _e(f"{g.entidades[a.origem].valor} —{a.relacao}→ "
                       f"{g.entidades[a.destino].valor} ({a.confianca})")
                    for a in sorted(ligados, key=lambda x: -x.confianca)[:6]) + "</span>")
            A("</div>")
    for p in pnt[:8]:
        via = ", ".join(i["rotulo"] for i in p["intermediarios"]) or "ligação direta"
        A(f"<p>Entre <span class='mono'>{_e(p['de'].split(':', 1)[1])}</span> e "
          f"<span class='mono'>{_e(p['para'].split(':', 1)[1])}</span>, "
          f"{_grau(p['elo_mais_fraco'])} existe conexão em {p['saltos']} "
          f"salto(s), por intermédio de {_e(via)} (elo mais fraco: "
          f"{p['elo_mais_fraco']}).</p>")

    # ------------------------------------------------------ limitacoes
    A(secao("Limitações"))
    A("<p>Vínculo, neste documento, designa coocorrência documentada entre "
      "identificadores em fontes abertas e registros públicos, e não relação "
      "jurídica, societária ou pessoal comprovada. Registros cadastrais são "
      "autodeclarados e podem estar desatualizados; o código de área (DDD) "
      "indica a área de habilitação original da linha, não a localização do "
      "usuário; a destinação de faixa de numeração não reflete portabilidade. "
      "A ausência de um vínculo nas fontes consultadas não permite concluir "
      "pela sua inexistência.</p>")

    # ------------------------------------------------------ conclusao
    A(secao("Conclusão"))
    if caso.conclusao:
        A(f"<p>{_e(caso.conclusao)}</p>")
    else:
        if clusters:
            c0 = clusters[0]
            A(f"<p>Com base nos exames realizados, {_grau(c0.forca)} as "
              f"entidades do agrupamento “{_e(c0.chave)}” compartilham origem "
              f"comum ({_e(c0.tipo)}). As demais conclusões dependem de "
              f"confirmação nas fontes primárias indicadas.</p>")
        else:
            A("<p>Os exames não identificaram agrupamento entre os "
              "identificadores analisados, dentro das fontes consultadas.</p>")
        A("<p class='mut'>Conclusão gerada automaticamente a partir dos graus de "
          "confiança; recomenda-se redação final pelo responsável técnico.</p>")

    # ------------------------------------------------------ encerramento
    A(f"<p>Nada mais havendo a relatar, encerra-se o presente "
      f"{'relatório' if relint else 'laudo'}, composto de {n} seções, "
      f"elaborado com o auxílio da ferramenta F.I.O. e sob responsabilidade "
      f"técnica de quem o subscreve.</p>")
    A(f"<div class='assin'><div class='linha'></div>{_e(caso.responsavel)}"
      + (f"<br><span class='mut'>{_e(caso.registro_profissional)}</span>"
         if caso.registro_profissional else "") + "</div>")
    A("</div></body></html>")
    return "".join(P)
