"""Interface de linha de comando do F.I.O."""

from __future__ import annotations

import argparse
import csv
import getpass
import json
import sys
from pathlib import Path

from . import __version__
from .politica import Caso, BASES_LEGAIS, FONTES_VEDADAS, ViolacaoDeEscopo
from .caso import CasoEmDisco, listar_casos, segredos, raiz
from .grafo.modelo import Entidade
from .grafo.clusters import detectar_clusters, tabela_correlacao, pontes
from .coletores import REGISTRO, disponiveis
from .coletores.web import montar_dorks
from .core.normalize import normalizar, variantes
from .motor import investigar
from .relatorio import gerar_html, gerar_markdown


def _p(*a):
    print(*a, file=sys.stderr)


def _caso(args) -> CasoEmDisco:
    cd = CasoEmDisco(args.caso)
    if not cd.existe:
        _p(f"caso '{args.caso}' nao existe. Use: fio caso novo --id {args.caso} ...")
        raise SystemExit(2)
    return cd


def _ator(args) -> str:
    return getattr(args, "ator", None) or getpass.getuser()


# --------------------------------------------------------------- comandos
def cmd_caso_novo(args) -> int:
    try:
        c = Caso(id=args.id, titulo=args.titulo, base_legal=args.base_legal,
                 finalidade=args.finalidade, responsavel=args.responsavel,
                 escopo=args.escopo or [])
    except ViolacaoDeEscopo as e:
        _p(f"erro: {e}")
        return 2
    if args.dias:
        import datetime as dt
        c.expira_em = (dt.datetime.now(dt.timezone.utc)
                       + dt.timedelta(days=args.dias)).isoformat(timespec="seconds")
    cd = CasoEmDisco(c.id)
    if cd.existe:
        _p(f"caso '{c.id}' ja existe em {cd.dir}")
        return 2
    cd.criar(c, _ator(args))
    print(f"caso {c.id} criado em {cd.dir}")
    print(f"base legal: {c.base_legal_texto()}")
    print(f"escopo expira em: {c.expira_em}")
    return 0


def cmd_caso_listar(args) -> int:
    casos = listar_casos()
    if not casos:
        print("nenhum caso em " + str(raiz() / "casos"))
        return 0
    for c in casos:
        marca = " [EXPIRADO]" if c.get("expirado") else ""
        print(f"{c['id']:<22} {c['titulo'][:44]:<46} "
              f"{len(c.get('escopo', []))} alvo(s){marca}")
    return 0


def cmd_caso_ver(args) -> int:
    cd = _caso(args)
    c = cd.caso()
    g = cd.grafo()
    print(c.json())
    print(f"\nentidades: {len(g.entidades)}  vinculos: {len(g.arestas)}  "
          f"registros no ledger: {len(cd.ledger())}")
    return 0


def cmd_alvo(args) -> int:
    cd = _caso(args)
    tipo = args.tipo
    valor = args.valor
    atributos = {}
    rotulo = ""
    if tipo == "telefone":
        t = normalizar(valor, ddd_padrao=args.ddd)
        if not t.valido:
            _p(f"aviso: {t.justificativa}")
        valor = t.chave
        rotulo = t.formatado()
        atributos = {"ddd": t.ddd, "assinante": t.assinante, "faixa": t.faixa,
                     "uf": t.uf, "e164": t.e164}
    elif tipo in ("email", "dominio"):
        valor = valor.lower().strip()
    elif tipo == "documento":
        atributos = {"caminho": str(Path(valor).resolve())}
    cd.add_alvo(Entidade(tipo, valor, rotulo=rotulo, atributos=atributos),
                _ator(args))
    print(f"alvo {tipo}:{valor} adicionado ao caso {args.caso} e ao escopo")
    return 0


def cmd_buscar(args) -> int:
    from . import busca
    try:
        cd, alvo = busca.preparar(args.valor, args.base_legal, _ator(args),
                                  finalidade=args.finalidade, ddd=args.ddd,
                                  dias=args.dias)
    except (ValueError, ViolacaoDeEscopo) as e:
        _p(f"nao foi possivel buscar: {e}")
        return 2
    print(f"alvo: {alvo.tipo} {alvo.rotulo or alvo.valor}  (caso {cd.caso_id})")
    busca.executar(cd, _ator(args), offline=args.offline, rapido=not args.completo,
                   orcamento=None if args.completo else args.orcamento,
                   log=_p if args.verboso else (lambda s: None))
    r = busca.resumo(cd)
    print(f"entidades: {r['entidades']}  vinculos: {r['vinculos']} "
          f"(alta confianca: {r['vinculos_alta']})")
    for rot, itens in (("empresas", r["organizacoes"]), ("pessoas", r["pessoas"])):
        if itens:
            print(f"{rot}: {'; '.join(itens)}")
    for a in r["avisos"]:
        print(f"  ! {a}")
    for a in r["proximo"]:
        print(f"  -> {a}")
    print(f"detalhes: fio relatorio --caso {cd.caso_id}   |   grafo: fio grafo --caso {cd.caso_id}")
    return 0


def cmd_investigar(args) -> int:
    cd = _caso(args)
    cols = args.coletores.split(",") if args.coletores else None
    if cols:
        for c in cols:
            if c not in REGISTRO:
                _p(f"coletor desconhecido: {c}. Disponiveis: "
                   f"{', '.join(disponiveis())}")
                return 2
    try:
        res = investigar(cd, _ator(args), coletores=cols,
                         profundidade=args.profundidade,
                         permitir_rede=not args.offline,
                         intervalo=args.intervalo, paralelo=args.paralelo,
                         orcamento=args.orcamento, rapido=args.rapido,
                         expandir=args.expandir_escopo,
                         log=_p if args.verboso else (lambda s: None))
    except ViolacaoDeEscopo as e:
        _p(f"bloqueado pela politica do caso: {e}")
        return 3
    print(f"coletores executados: {', '.join(res.executados) or '-'}")
    if res.bloqueados:
        print(f"pivos bloqueados pelo escopo: {len(res.bloqueados)} "
              f"(use --expandir-escopo para incluir entidades derivadas)")
        for b in sorted(set(res.bloqueados))[:12]:
            print(f"  - {b}")
    print(f"entidades novas: {res.novas_entidades}   "
          f"vinculos novos: {res.novas_arestas}   "
          f"alvos visitados: {len(res.alvos_visitados)}")
    for e in res.erros:
        _p(f"  erro: {e}")
    return 0


def cmd_grafo(args) -> int:
    cd = _caso(args)
    g = cd.grafo()
    if args.formato == "csv":
        sys.stdout.write(g.csv_arestas())
    else:
        sys.stdout.write(g.json())
    return 0


def cmd_clusters(args) -> int:
    g = _caso(args).grafo()
    cl = detectar_clusters(g)
    if args.json:
        print(json.dumps([c.dict() for c in cl], ensure_ascii=False, indent=2))
        return 0
    if not cl:
        print("nenhum agrupamento detectado")
    for c in cl:
        print(f"\n[{c.forca:>5.2f}] {c.tipo} · {c.chave} · {len(c.membros)} membros")
        print(f"        {c.explicacao}")
        print(f"        ressalva: {c.ressalva}")
        for m in c.membros:
            print(f"          - {m}")
    for p in pontes(g):
        via = " -> ".join(i["rotulo"] for i in p["intermediarios"]) or "direto"
        print(f"\nponte: {p['de']} <-> {p['para']} ({p['saltos']} salto(s), "
              f"elo mais fraco {p['elo_mais_fraco']}) via {via}")
    return 0


def cmd_tabela(args) -> int:
    g = _caso(args).grafo()
    linhas = tabela_correlacao(g)
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            if linhas:
                w = csv.DictWriter(fh, fieldnames=list(linhas[0]))
                w.writeheader()
                w.writerows(linhas)
        print(f"{len(linhas)} linhas em {args.csv}")
        return 0
    for l in linhas[:args.limite]:
        print(f"{l['confianca']:>6.3f} {l['nivel']:<11} {l['entidade']:<26} "
              f"--{l['relacao']}--> {l['vinculada_a'][:40]:<42} "
              f"[{l['coletores']}]")
    return 0


def cmd_relatorio(args) -> int:
    cd = _caso(args)
    c, g = cd.caso(), cd.grafo()
    led = cd.ledger(_ator(args))
    regs, verif = led.registros(), led.verificar()
    saida = Path(args.saida)
    saida.write_text(gerar_html(c, g, regs, verif), encoding="utf-8")
    print(f"relatorio HTML: {saida}")
    if args.markdown:
        Path(args.markdown).write_text(gerar_markdown(c, g, regs, verif),
                                       encoding="utf-8")
        print(f"relatorio Markdown: {args.markdown}")
    if args.csv:
        Path(args.csv).write_text(g.csv_arestas(), encoding="utf-8")
        print(f"vinculos CSV: {args.csv}")
    led.registrar("relatorio.gerado", alvo=str(saida),
                  resumo=f"{len(g.entidades)} entidades, {len(g.arestas)} vinculos")
    if args.manifesto:
        from .evidencia import manifesto
        extras = [Path(x) for x in (args.saida, args.markdown, args.csv) if x]
        destino = manifesto.gravar(cd.dir, cd.caso_id, extras)
        print(f"manifesto SHA-256 (inclui os relatorios): {destino}")
    if not verif[0]:
        _p("ATENCAO: cadeia de custodia comprometida; ver secao 9 do relatorio")
    return 0


def cmd_ledger(args) -> int:
    led = _caso(args).ledger(_ator(args))
    if args.acao == "verificar":
        ok, probs = led.verificar()
        print("cadeia integra" if ok else "CADEIA COMPROMETIDA")
        for p in probs:
            print("  " + p)
        return 0 if ok else 4
    for r in led.registros():
        print(f"{r.seq:>4} {r.ts} {r.acao:<24} {r.coletor:<14} "
              f"{(r.alvo or '')[:46]:<48} {r.resumo[:70]}")
    return 0


def cmd_numero(args) -> int:
    """Analise offline avulsa: nao exige caso porque nao coleta nada."""
    t = normalizar(args.valor, ddd_padrao=args.ddd)
    if args.json:
        print(json.dumps(t.dict(), ensure_ascii=False, indent=2))
        return 0
    print(f"entrada      : {t.original}")
    print(f"canonico     : {t.e164 or '-'}")
    print(f"formatado    : {t.formatado()}")
    print(f"valido       : {t.valido}")
    print(f"tipo         : {t.tipo}  ({t.justificativa})")
    print(f"regiao       : {t.uf or '-'} / {t.area or '-'}")
    print(f"bloco        : {t.faixa or '-'}")
    for a in t.avisos:
        print(f"aviso        : {a}")
    print("grafias      : " + ", ".join(variantes(t)[:10]))
    return 0


def cmd_dorks(args) -> int:
    tipo = args.tipo
    valor = normalizar(args.valor).chave if tipo == "telefone" else args.valor
    e = Entidade(tipo, valor)
    for d in montar_dorks(e):
        print(f"\n# {d['recorte']}")
        print(d["consulta"])
        if args.urls:
            for motor, url in d["urls"].items():
                print(f"  {motor}: {url}")
    return 0


def cmd_coletores(args) -> int:
    for nome in disponiveis():
        c = REGISTRO[nome]
        print(f"\n{nome}  [{c.admiralty}]  "
              f"{'rede' if c.requer_rede else 'offline'}"
              + (f"  requer: {c.requer_segredo}" if c.requer_segredo else ""))
        print(f"  alvos: {', '.join(c.tipos_alvo)}")
        print(f"  {c.descricao}")
        print(f"  reserva: {c.reserva}")
    print("\nfontes recusadas por construcao:")
    for k, v in FONTES_VEDADAS.items():
        print(f"  - {k}: {v}")
    return 0


def cmd_indice(args) -> int:
    from .indice import construir, IndiceCNPJ
    from .receita_download import validar_ufs

    try:
        ufs = validar_ufs(
            {u.strip().upper() for u in (args.uf or "").split(",") if u.strip()} or None
        )
    except ValueError as e:
        _p(f"erro: {e}")
        return 2

    saida = Path(args.saida or (raiz() / "cnpj.sqlite")).expanduser()
    if args.acao == "exportar":
        from .indice_pronto import exportar
        origem = Path(args.origem).expanduser() if args.origem else saida
        uf = (args.uf or "").strip().upper() or None
        if uf and "," in uf:
            _p("erro: --uf do exportar aceita uma UF por arquivo (ex.: --uf MG)")
            return 2
        destino = Path(args.para or f"cnpj-{uf or 'todas'}.sqlite.xz")
        try:
            man = exportar(origem, destino, uf=uf, log=_p)
        except FileNotFoundError as e:
            _p(f"erro: {e}")
            return 2
        print(json.dumps(man, ensure_ascii=False, indent=2))
        print(f"publique {destino} e {destino}.json (ex.: gh release upload indice-latest ...)")
        return 0

    if args.acao == "baixar" and args.pronto:
        from .indice_pronto import importar, IndiceProntoIndisponivel
        if not ufs:
            _p("erro: --pronto exige --uf (uma ou mais UFs)")
            return 2
        saida.parent.mkdir(parents=True, exist_ok=True)
        try:
            res = importar(saida, sorted(ufs), base=args.de, log=_p)
        except IndiceProntoIndisponivel as e:
            _p(f"erro: {e}")
            return 3
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    if args.acao == "baixar":
        from .receita_download import montar
        saida.parent.mkdir(parents=True, exist_ok=True)
        cont = montar(saida, ufs=ufs, mes=args.mes, base=args.base,
                      pasta_tmp=args.tmp, manter_zips=args.manter_zips, log=_p,
                      leve=args.leve)
        print(json.dumps(cont, ensure_ascii=False, indent=2))
        return 0

    if args.acao == "construir":
        if not args.origem:
            _p("erro: --origem e obrigatorio em 'fio indice construir'")
            return 2
        origem = Path(args.origem).expanduser()
        if not origem.exists() or not origem.is_dir():
            _p(f"erro: origem inexistente ou nao e diretorio: {origem}")
            return 2
        saida.parent.mkdir(parents=True, exist_ok=True)
        cont = construir(origem, saida, log=_p, ufs=ufs, leve=args.leve)
        print(json.dumps(cont, ensure_ascii=False, indent=2))
        print(f"indice em {saida}")
        return 0

    caminho = Path(
        args.saida or segredos().get("indice_cnpj") or (raiz() / "cnpj.sqlite")
    ).expanduser()
    with IndiceCNPJ(caminho) as idx:
        stats = idx.estatisticas()
        meta = idx.meta()
    print(f"{caminho}: {json.dumps(stats, ensure_ascii=False)}")
    if meta:
        print(f"uf={meta.get('ufs', 'todas')} mes={meta.get('mes', '-')}")
    return 0 if stats.get("indice") != "ausente" else 1


def cmd_exposicao(args) -> int:
    from .coletores.exposicao import construir_indice
    n = construir_indice(args.origem, args.saida,
                         {"id": args.id, "titulo": args.titulo,
                          "origem": args.descricao})
    print(f"{n} identificadores indexados por hash em {args.saida}")
    print("o arquivo de origem em claro pode e deve ser eliminado agora")
    return 0


def cmd_manifesto(args) -> int:
    from .evidencia import manifesto
    cd = _caso(args)
    if args.acao == "gerar":
        destino = manifesto.gravar(cd.dir, cd.caso_id)
        m = json.loads(destino.read_text(encoding="utf-8"))
        print(f"manifesto gravado em {destino}")
        print(f"{len(m['pecas'])} pecas; ledger com {m['ledger']['registros']} "
              f"registros; sha256 {m['manifesto_sha256']}")
        return 0
    ok, problemas = manifesto.verificar(cd.dir)
    print("manifesto integro" if ok else "MANIFESTO COM PROBLEMAS")
    for p in problemas:
        print(f"  - {p}")
    return 0 if ok else 1


def cmd_claims(args) -> int:
    from .grafo import claims as cl
    g = _caso(args).grafo()
    lista = cl.derivar(g, args.confianca_minima)
    problemas = cl.validar(lista, g)
    if args.json:
        print(cl.como_json(lista))
    else:
        for c in lista:
            conf = f"{c.confianca:.2f}" if c.confianca is not None else "  - "
            print(f"{c.id}  {c.tipo:<10} {conf}  {c.texto[:110]}")
        print(f"\n{len(lista)} claims; "
              + ("todos rastreaveis ao grafo" if not problemas
                 else f"{len(problemas)} problema(s)"))
    for p in problemas:
        _p(f"  invalido: {p}")
    return 1 if problemas else 0


def cmd_diagnostico(args) -> int:
    from .diagnostico import sondar, imprimir
    print("Testando conexao com as fontes online (consultas neutras, sem pessoa)...\n")
    return imprimir(sondar(segredos()))


def cmd_demo(args) -> int:
    from .demo import montar
    r = montar(_ator(args), recriar=args.recriar)
    if r.get("ja_existia"):
        print(f"caso {r['caso']} ja existe (use --recriar para montar de novo)")
    else:
        m = r["metricas"]
        print(f"caso {r['caso']} montado: {m['entidades']} entidades, "
              f"{m['vinculos']} vinculos, {m['observacoes']} observacoes")
    if args.abrir:
        from .lab.bancada.servidor import servir
        servir()
    return 0


def cmd_bases(args) -> int:
    for k, v in BASES_LEGAIS.items():
        print(f"{k:<22} {v}")
    return 0


# ------------------------------------------------------------------ parser
def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fio",
        description="F.I.O. — analise de vinculo a partir de telefones e "
                    "registros publicos. Coleta passiva, sob escopo de caso.",
        epilog="Nenhum coletor roda fora de um caso com base legal declarada.")
    p.add_argument("--versao", action="version", version=f"fio {__version__}")
    p.add_argument("--ator", help="identificacao de quem opera (vai para o ledger)")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("caso", help="abrir, listar e inspecionar casos")
    cs = c.add_subparsers(dest="sub", required=True)
    n = cs.add_parser("novo")
    n.add_argument("--id", required=True)
    n.add_argument("--titulo", required=True)
    n.add_argument("--base-legal", required=True, choices=sorted(BASES_LEGAIS))
    n.add_argument("--finalidade", required=True,
                   help="descricao especifica: delimita o que pode ser coletado")
    n.add_argument("--responsavel", required=True)
    n.add_argument("--escopo", nargs="*", help="identificadores autorizados")
    n.add_argument("--dias", type=int, default=0, help="validade do escopo")
    n.set_defaults(func=cmd_caso_novo)
    l = cs.add_parser("listar"); l.set_defaults(func=cmd_caso_listar)
    v = cs.add_parser("ver"); v.add_argument("--caso", required=True)
    v.set_defaults(func=cmd_caso_ver)

    a = sub.add_parser("alvo", help="incluir alvo primario no caso")
    a.add_argument("--caso", required=True)
    a.add_argument("--tipo", required=True,
                   choices=["telefone", "email", "dominio", "cnpj", "pessoa",
                            "organizacao", "documento"])
    a.add_argument("--valor", required=True)
    a.add_argument("--ddd", help="DDD assumido para numero sem DDD")
    a.set_defaults(func=cmd_alvo)

    b = sub.add_parser("buscar", help="busca em um passo: abre o caso, consulta as fontes e resume")
    b.add_argument("valor", help="telefone, CNPJ, e-mail, dominio ou CEP")
    b.add_argument("--base-legal", required=True, help="base legal (ver `fio bases`)")
    b.add_argument("--finalidade", help="finalidade da consulta (ha um texto padrao)")
    b.add_argument("--ddd", help="DDD assumido para telefone sem DDD")
    b.add_argument("--dias", type=int, default=30, help="validade do escopo (padrao 30)")
    b.add_argument("--completo", action="store_true", help="busca completa, sem orcamento de tempo")
    b.add_argument("--orcamento", type=float, default=45.0, metavar="SEGUNDOS",
                   help="limite de tempo da busca rapida (padrao 45)")
    b.add_argument("--offline", action="store_true", help="so fontes locais")
    b.add_argument("-v", "--verboso", action="store_true")
    b.set_defaults(func=cmd_buscar)

    i = sub.add_parser("investigar", help="rodar os coletores e pivotar")
    i.add_argument("--caso", required=True)
    i.add_argument("--coletores", help="lista separada por virgula")
    i.add_argument("--profundidade", type=int, default=1)
    i.add_argument("--offline", action="store_true", help="so coletores locais")
    i.add_argument("--paralelo", type=int, default=4,
                   help="coletores de rede simultaneos por alvo (1 = em sequencia)")
    i.add_argument("--orcamento", type=float, default=None, metavar="SEGUNDOS",
                   help="limite de tempo de coleta; esgotado, nao abre novas consultas")
    i.add_argument("--rapido", action="store_true",
                   help="modo leve: fontes lentas fazem menos consultas (ex.: 3 recortes de busca)")
    i.add_argument("--intervalo", type=float, default=1.5,
                   help="segundos entre requisicoes ao mesmo host")
    i.add_argument("--expandir-escopo", action="store_true",
                   help="autoriza pivotar sobre entidades derivadas da "
                        "coleta; cada inclusao fica registrada no ledger")
    i.add_argument("-v", "--verboso", action="store_true")
    i.set_defaults(func=cmd_investigar)

    g = sub.add_parser("grafo", help="exportar o grafo")
    g.add_argument("--caso", required=True)
    g.add_argument("--formato", choices=["json", "csv"], default="json")
    g.set_defaults(func=cmd_grafo)

    cl = sub.add_parser("clusters", help="agrupamentos e pontes entre alvos")
    cl.add_argument("--caso", required=True)
    cl.add_argument("--json", action="store_true")
    cl.set_defaults(func=cmd_clusters)

    t = sub.add_parser("tabela", help="tabela de correlacao")
    t.add_argument("--caso", required=True)
    t.add_argument("--csv", help="grava em arquivo em vez da tela")
    t.add_argument("--limite", type=int, default=40)
    t.set_defaults(func=cmd_tabela)

    r = sub.add_parser("relatorio", help="gerar relatorio final")
    r.add_argument("--caso", required=True)
    r.add_argument("--saida", required=True, help="arquivo .html")
    r.add_argument("--markdown", help="tambem gravar .md")
    r.add_argument("--csv", help="tambem gravar vinculos em .csv")
    r.add_argument("--manifesto", action="store_true",
                   help="gravar o manifesto SHA-256 do caso e dos relatorios gerados")
    r.set_defaults(func=cmd_relatorio)

    le = sub.add_parser("ledger", help="cadeia de custodia")
    le.add_argument("acao", choices=["listar", "verificar"])
    le.add_argument("--caso", required=True)
    le.set_defaults(func=cmd_ledger)

    nu = sub.add_parser("numero", help="analise offline avulsa de um numero")
    nu.add_argument("valor")
    nu.add_argument("--ddd")
    nu.add_argument("--json", action="store_true")
    nu.set_defaults(func=cmd_numero)

    d = sub.add_parser("dorks", help="gerar consultas para busca manual")
    d.add_argument("--tipo", default="telefone",
                   choices=["telefone", "email", "pessoa", "organizacao", "dominio"])
    d.add_argument("--valor", required=True)
    d.add_argument("--urls", action="store_true")
    d.set_defaults(func=cmd_dorks)

    co = sub.add_parser("coletores", help="listar coletores e suas reservas")
    co.set_defaults(func=cmd_coletores)

    ix = sub.add_parser("indice", help="indice reverso dos Dados Abertos do CNPJ")
    ix.add_argument("acao", choices=["baixar", "construir", "status", "exportar"])
    ix.add_argument("--uf", help="filtrar por UF, ex.: MG ou MG,SP; reduz o indice final e a RAM, nao o trafego da Receita")
    ix.add_argument("--mes", help="AAAA-MM; padrao: o mais recente publicado")
    ix.add_argument("--base", help="URL base da Receita, se o endereco mudar")
    ix.add_argument("--origem", help="diretorio com os CSV da Receita Federal")
    ix.add_argument("--saida", help="arquivo sqlite de destino")
    ix.add_argument("--tmp", help="pasta temporaria dos ZIPs baixados")
    ix.add_argument("--manter-zips", action="store_true",
                    help="nao apagar os ZIPs depois de processar")
    ix.add_argument("--leve", action="store_true",
                    help="indice enxuto: so estabelecimentos com telefone/e-mail (ou matriz), sem endereco completo nem CNAE")
    ix.add_argument("--pronto", action="store_true",
                    help="baixar: em vez de montar pela Receita, baixa o indice ja pronto (segundos; precisa de --uf)")
    ix.add_argument("--de", metavar="URL", help="baixar --pronto: URL base dos arquivos (padrao: Release do repositorio)")
    ix.add_argument("--para", metavar="ARQUIVO", help="exportar: arquivo .sqlite.xz de saida (padrao: cnpj-UF.sqlite.xz)")
    ix.set_defaults(func=cmd_indice)

    ex = sub.add_parser("exposicao",
                        help="indexar por hash um corpus ja detido legitimamente")
    ex.add_argument("--origem", required=True)
    ex.add_argument("--saida", required=True)
    ex.add_argument("--id", default="corpus")
    ex.add_argument("--titulo", default="corpus interno")
    ex.add_argument("--descricao", default="")
    ex.set_defaults(func=cmd_exposicao)

    b = sub.add_parser("bases", help="bases legais aceitas")
    b.set_defaults(func=cmd_bases)

    mf = sub.add_parser("manifesto", help="SHA-256 de cada peca do caso, amarrado ao ledger")
    mf.add_argument("acao", choices=["gerar", "verificar"])
    mf.add_argument("--caso", required=True)
    mf.set_defaults(func=cmd_manifesto)

    cm = sub.add_parser("claims", help="conclusoes do caso, cada uma com a evidencia que a sustenta")
    cm.add_argument("--caso", required=True)
    cm.add_argument("--confianca-minima", type=float, default=0.5)
    cm.add_argument("--json", action="store_true")
    cm.set_defaults(func=cmd_claims)

    dg = sub.add_parser("diagnostico", help="testar conexao com as fontes online")
    dg.set_defaults(func=cmd_diagnostico)

    dm = sub.add_parser("demo", help="montar o caso de demonstracao (ficticio, offline)")
    dm.add_argument("--recriar", action="store_true")
    dm.add_argument("--abrir", action="store_true", help="abrir a bancada em seguida")
    dm.set_defaults(func=cmd_demo)

    from .cli_lab import registrar as registrar_lab
    registrar_lab(sub)
    return p


def main(argv=None) -> int:
    # Terminal do Windows costuma vir em cp1252: sem isto, qualquer acento ou
    # travessao na saida derruba o programa com UnicodeEncodeError.
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    args = construir_parser().parse_args(argv)
    return args.func(args)
