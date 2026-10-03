"""Comandos da edicao BR e do lab."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .caso import CasoEmDisco, raiz


def _p(*a):
    print(*a, file=sys.stderr)


def _cd(caso: str) -> CasoEmDisco:
    cd = CasoEmDisco(caso)
    if not cd.existe:
        _p(f"caso '{caso}' nao existe")
        raise SystemExit(2)
    return cd


# ------------------------------------------------------------ documentos
def cmd_doc(a) -> int:
    from .core.documentos import analisar, extrair_documentos
    if a.tipo == "extrair":
        texto = Path(a.valor).read_text(encoding="utf-8", errors="replace") \
            if Path(a.valor).exists() else a.valor
        for d in extrair_documentos(texto):
            amb = "  [AMBIGUO]" if d.ambiguo else ""
            print(f"{d.tipo:<12} {d.valor:<20} {json.dumps(d.atributos, ensure_ascii=False)}{amb}")
        return 0
    d = analisar(a.tipo, a.valor)
    print(json.dumps(d.dict(), ensure_ascii=False, indent=2))
    return 0 if d.valido else 1


# --------------------------------------------------------------- receitas
def cmd_receita(a) -> int:
    from .receitas import carregar_receitas, construir, indices_disponiveis, Indice
    recs = carregar_receitas(raiz())
    if a.acao == "listar":
        prontos = {p.stem for p in indices_disponiveis(raiz())}
        for k, r in sorted(recs.items()):
            marca = "[indice pronto]" if k in prontos else ""
            print(f"{k:<16} {r.get('admiralty', '?'):<3} {r.get('titulo', '')} {marca}")
            print(f"{'':16}     fonte: {r.get('fonte', '')}")
        return 0
    if a.acao == "construir":
        if not a.id or not a.origem:
            _p("uso: fio receita construir --id <receita> --origem <arquivo>")
            return 2
        meta = construir(a.id, a.origem, raiz(), recs, log=_p)
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return 0
    for p in indices_disponiveis(raiz()):
        idx = Indice(p)
        print(f"{p.stem}: {idx.meta.get('linhas')} linhas, {idx.meta.get('chaves')} chaves, "
              f"construido {idx.meta.get('construido_em')}, sha {str(idx.meta.get('sha256'))[:12]}")
        idx.fechar()
    return 0


# --------------------------------------------------------------- quesitos
def cmd_quesito(a) -> int:
    cd = _cd(a.caso)
    c = cd.caso()
    if a.acao == "add":
        n = len(c.quesitos) + 1
        c.quesitos.append({"n": n, "texto": a.texto, "resposta": "",
                           "entidades": a.entidades or []})
        cd.salvar_caso(c)
        cd.ledger(a.ator or "analista").registrar("quesito.adicionado", resumo=a.texto[:200])
        print(f"quesito {n} registrado")
    elif a.acao == "responder":
        q = next((q for q in c.quesitos if q["n"] == a.n), None)
        if not q:
            _p(f"quesito {a.n} inexistente")
            return 2
        q["resposta"] = a.texto
        if a.entidades:
            q["entidades"] = a.entidades
        cd.salvar_caso(c)
        cd.ledger(a.ator or "analista").registrar(
            "quesito.respondido", resumo=f"quesito {a.n}: {a.texto[:160]}")
        print(f"quesito {a.n} respondido")
    else:
        for q in c.quesitos:
            print(f"{q['n']}. {q['texto']}\n   -> {q.get('resposta') or '(sem resposta)'}")
    return 0


def cmd_caso_editar(a) -> int:
    cd = _cd(a.caso)
    c = cd.caso()
    for campo in ("solicitante", "referencia", "registro_profissional",
                  "conclusao", "classificacao"):
        v = getattr(a, campo, None)
        if v is not None:
            setattr(c, campo, v)
    cd.salvar_caso(c)
    cd.ledger(a.ator or "analista").registrar("caso.editado", resumo="metadados do laudo")
    print("caso atualizado")
    return 0


def cmd_laudo(a) -> int:
    from .relatorio.laudo import gerar_laudo
    from .lab.experimentos import Registro
    cd = _cd(a.caso)
    led = cd.ledger(a.ator or "analista")
    exps = Registro(cd.dir).listar()
    html = gerar_laudo(cd.caso(), cd.grafo(), led.registros(), led.verificar(),
                       modelo=a.modelo, experimento=exps[-1].dict() if exps else None)
    Path(a.saida).write_text(html, encoding="utf-8")
    led.registrar("laudo.gerado", alvo=a.saida, resumo=f"modelo {a.modelo}")
    print(f"{a.modelo}: {a.saida}")
    return 0


# -------------------------------------------------------------------- lab
def cmd_lab(a) -> int:
    from .lab import plugins
    if a.acao == "plugins":
        inv = plugins.inventario()
        for est, cols in inv["coletores"].items():
            print(f"\n[{est}]")
            for c in cols:
                print(f"  {c['nome']:<18} {c['admiralty']:<3} "
                      f"{'rede' if c['rede'] else 'offline':<8} {c['origem']}")
        print("\n[analise]")
        for x in inv["analisadores"]:
            print(f"  {x['nome']:<22} {x['origem']}")
        for p in inv["plugins"]:
            print(f"\nplugin {p['arquivo']}: {p['coletores'] + p['analisadores']}"
                  + (f" ERRO {p['erro']}" if p["erro"] else ""))
        return 0

    if a.acao == "pipeline":
        from .lab.pipeline import Config, executar
        cd = _cd(a.caso)
        cfg = Config(coletores=a.coletores.split(",") if a.coletores else None,
                     profundidade=a.profundidade, offline=a.offline,
                     expandir_escopo=a.expandir_escopo, intervalo=a.intervalo,
                     paralelo=a.paralelo, orcamento=a.orcamento, rapido=a.rapido,
                     relatorio=a.relatorio, laudo=a.laudo, modelo_laudo=a.modelo,
                     descricao=a.descricao or "")
        exp = executar(cd, a.ator or "analista", cfg, log=_p if a.verboso else (lambda s: None))
        for e in exp.estagios:
            extra = {k: v for k, v in e.items() if k not in ("estagio", "ok", "segundos")}
            print(f"  {e['estagio']:<11} {'ok' if e['ok'] else 'FALHOU'} "
                  f"{e['segundos']:>7.2f}s  {json.dumps(extra, ensure_ascii=False)[:150]}")
        print(f"experimento {exp.id}: {exp.estado}; grafo {exp.grafo_sha256[:16]}")
        print(json.dumps(exp.metricas, ensure_ascii=False))
        return 0 if exp.estado == "concluido" else 1

    if a.acao == "experimentos":
        from .lab.experimentos import Registro
        for e in Registro(_cd(a.caso).dir).listar():
            print(f"{e.id}  {e.estado:<10} {e.duracao_s:>7.2f}s  "
                  f"ent={e.metricas.get('entidades')} vin={e.metricas.get('vinculos')} "
                  f"req={e.metricas.get('requisicoes')}  grafo={e.grafo_sha256[:12]}  {e.descricao}")
        return 0

    if a.acao == "comparar":
        from .lab.experimentos import Registro
        r = Registro(_cd(a.caso).dir).comparar(a.a, a.b)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0

    if a.acao == "sintetico":
        from .lab.sintetico import Gerador
        g = Gerador(a.semente)
        print(json.dumps(g.gravar(g.gerar(a.grupos), Path(a.saida)), ensure_ascii=False, indent=2))
        return 0

    if a.acao == "avaliar":
        from .lab.avaliacao import avaliar_lote, tabela_lote
        sementes = [int(x) for x in a.sementes.split(",")]
        agg = avaliar_lote(Path(a.saida), sementes, a.grupos, log=_p if a.verboso else (lambda s: None))
        md = tabela_lote(agg)
        (Path(a.saida) / "avaliacao_lote.md").write_text(md, encoding="utf-8")
        print(md)
        return 0

    if a.acao == "calibrar":
        from .lab.calibracao import calibrar, tabela_markdown
        sementes = [int(x) for x in a.sementes.split(",")]
        res = calibrar(Path(a.saida), sementes, a.grupos,
                       log=_p if a.verboso else (lambda s: None))
        md = tabela_markdown(res)
        (Path(a.saida) / "calibracao.md").write_text(md, encoding="utf-8")
        print(md)
        return 0

    if a.acao == "benchmark-real":
        from .lab.benchmark_real import benchmark, tabela
        from .caso import segredos
        idx = a.indice or segredos().get("indice_cnpj") or str(raiz() / "cnpj.sqlite")
        r = benchmark(idx, municipio=a.municipio, max_raizes=a.max_raizes,
                      semente=a.semente, log=_p)
        print(tabela(r))
        return 0

    if a.acao == "bancada":
        from .lab.bancada.servidor import servir
        servir(porta=a.porta, abrir=not a.sem_navegador,
               hosts_extra=[h for h in (a.permitir_host or "").split(",") if h])
        return 0
    return 2


def registrar(sub) -> None:
    d = sub.add_parser("doc", help="validar/estruturar documentos BR ou extrair de texto")
    d.add_argument("tipo", choices=["cpf", "cpf-parcial", "cnpj", "cep", "placa",
                                    "titulo", "pis", "renavam", "boleto", "pix-evp",
                                    "cnh", "cns", "extrair"])
    d.add_argument("valor", help="documento, ou arquivo/texto para 'extrair'")
    d.set_defaults(func=cmd_doc)

    r = sub.add_parser("receita", help="indexador universal de dados abertos")
    r.add_argument("acao", choices=["listar", "construir", "status"])
    r.add_argument("--id")
    r.add_argument("--origem")
    r.set_defaults(func=cmd_receita)

    q = sub.add_parser("quesito", help="quesitos do laudo")
    q.add_argument("acao", choices=["add", "responder", "listar"])
    q.add_argument("--caso", required=True)
    q.add_argument("--texto", default="")
    q.add_argument("--n", type=int)
    q.add_argument("--entidades", nargs="*", help="ids de entidade (tipo:valor) de suporte")
    q.set_defaults(func=cmd_quesito)

    e = sub.add_parser("caso-editar", help="metadados do laudo (solicitante, referencia...)")
    e.add_argument("--caso", required=True)
    for campo in ("solicitante", "referencia", "registro_profissional",
                  "conclusao", "classificacao"):
        e.add_argument(f"--{campo.replace('_', '-')}", dest=campo)
    e.set_defaults(func=cmd_caso_editar)

    l = sub.add_parser("laudo", help="gerar laudo tecnico ou RELINT")
    l.add_argument("--caso", required=True)
    l.add_argument("--saida", required=True)
    l.add_argument("--modelo", choices=["laudo", "relint"], default="laudo")
    l.set_defaults(func=cmd_laudo)

    lab = sub.add_parser("lab", help="pipeline, experimentos, avaliacao e bancada web")
    lab.add_argument("acao", choices=["plugins", "pipeline", "experimentos", "comparar",
                                      "sintetico", "avaliar", "calibrar", "bancada",
                                      "benchmark-real"])
    lab.add_argument("--indice", help="indice da Receita (benchmark-real)")
    lab.add_argument("--municipio", help="codigo do municipio na Receita (benchmark-real)")
    lab.add_argument("--max-raizes", type=int, default=800)
    lab.add_argument("--caso")
    lab.add_argument("--coletores")
    lab.add_argument("--profundidade", type=int, default=1)
    lab.add_argument("--offline", action="store_true")
    lab.add_argument("--expandir-escopo", action="store_true")
    lab.add_argument("--intervalo", type=float, default=1.5)
    lab.add_argument("--paralelo", type=int, default=4,
                     help="pipeline: coletores de rede simultaneos por alvo")
    lab.add_argument("--orcamento", type=float, default=None, metavar="SEGUNDOS",
                     help="pipeline: limite de tempo de coleta")
    lab.add_argument("--rapido", action="store_true",
                     help="pipeline: modo leve (menos consultas por fonte)")
    lab.add_argument("--relatorio")
    lab.add_argument("--laudo")
    lab.add_argument("--modelo", choices=["laudo", "relint"], default="laudo")
    lab.add_argument("--descricao")
    lab.add_argument("--a")
    lab.add_argument("--b")
    lab.add_argument("--semente", type=int, default=7)
    lab.add_argument("--sementes", default="1,2,3,4,5")
    lab.add_argument("--grupos", type=int, default=12)
    lab.add_argument("--saida", default=str(Path.cwd() / "lab-saida"))
    lab.add_argument("--porta", type=int, default=8765)
    lab.add_argument("--sem-navegador", action="store_true")
    lab.add_argument("--permitir-host", help="sufixos de Host aceitos alem de localhost "
                     "(ex.: colab.googleusercontent.com); o token continua obrigatorio")
    lab.add_argument("-v", "--verboso", action="store_true")
    lab.set_defaults(func=cmd_lab)
