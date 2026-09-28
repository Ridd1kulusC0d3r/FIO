"""Gera colab/FIO_Lab_Colab.ipynb a partir do codigo do repositorio.

So biblioteca padrao. O pacote vai embutido (base64) para o caderno
funcionar sem GitHub; se o repositorio estiver configurado, o caderno
prefere baixar a versao mais nova de la e usa o embutido como reserva.

    python tools/gerar_notebook.py            # grava colab/FIO_Lab_Colab.ipynb
    python tools/gerar_notebook.py --checar   # falha se o arquivo estiver desatualizado
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "colab" / "FIO_Lab_Colab.ipynb"
INCLUIR = ["fio", "testes", "exemplos", "pyproject.toml", "LICENSE"]


def _repo() -> str:
    cfg = RAIZ / "tools" / "repositorio.txt"
    return cfg.read_text(encoding="utf-8").strip() if cfg.exists() else "SEU-USUARIO/fio-lab"


def pacote() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for item in INCLUIR:
            p = RAIZ / item
            arquivos = [p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file())
            for a in arquivos:
                if "__pycache__" in a.parts or a.suffix == ".pyc":
                    continue
                info = zipfile.ZipInfo(str(Path("fio") / a.relative_to(RAIZ)).replace("\\", "/"),
                                       date_time=(2026, 1, 1, 0, 0, 0))   # zip deterministico
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, a.read_bytes())
    return buf.getvalue()


CELULAS: list[dict] = []
_n = 0


def _id() -> str:
    global _n
    _n += 1
    return f"fio{_n:03d}"


def md(texto: str) -> None:
    CELULAS.append({"cell_type": "markdown", "id": _id(), "metadata": {},
                    "source": texto.strip().splitlines(keepends=True)})


def code(texto: str) -> None:
    CELULAS.append({"cell_type": "code", "id": _id(), "metadata": {"cellView": "form"},
                    "execution_count": None, "outputs": [],
                    "source": texto.strip().splitlines(keepends=True)})


def montar_celulas(b64: str, versao: str, repo: str) -> None:
    linhas = "\n".join(b64[i:i + 120] for i in range(0, len(b64), 120))
    md(f"""
# F.I.O. Lab no Google Colab

**Fontes, Identificadores e Origens** · versão {versao} · análise de vínculos a partir de telefones e registros públicos brasileiros.

Tudo roda na nuvem do Google, sem instalar nada no seu computador. Use o menu **Ambiente de execução › Executar tudo** na primeira vez; depois, altere os formulários e rode só a seção que quiser (▶ à esquerda).

| Seção | O que faz | Precisa de internet |
|---|---|---|
| 1 | Instala o F.I.O. (do GitHub ou do próprio caderno) | opcional |
| 2 | Escolhe onde guardar: sessão temporária ou seu Google Drive | não |
| 3 | Confere as fontes públicas | sim |
| 4 | Demonstração com mapa interativo | não |
| 5 | Monta o índice da Receita Federal por UF | sim (vários GB) |
| 6 | Caso pontual com fontes reais | sim |
| 7 | Laudo e exportação | não |
| 8 | Bancada web completa | não |
| 9 | Benchmark com dados reais e avaliação sintética | não |
| 10 | Testes | opcional |

> **LGPD.** No Colab os dados ficam em servidores do Google. Use para teste, demonstração, alvos institucionais e pesquisa com dados abertos. Em caso real com dados pessoais, rode o F.I.O. no seu computador e registre base legal e finalidade.
""")
    md("## 1. Instalar")
    code(f'''
#@title Instalar o F.I.O. {{ display-mode: "form" }}
origem = "automatico"  #@param ["automatico", "github", "embutido"]
repositorio = "{repo}"  #@param {{type:"string"}}
ramo = "main"  #@param {{type:"string"}}
import base64, io, os, sys, zipfile, pathlib, shutil, urllib.request, html as _html
PACOTE = """
{linhas}
"""
TRABALHO = pathlib.Path("/content") if pathlib.Path("/content").exists() else pathlib.Path.cwd()
DESTINO = TRABALHO / "fio-lab"
if DESTINO.exists():
    shutil.rmtree(DESTINO)
DESTINO.mkdir(parents=True)

def _extrair(dados):
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        z.extractall(DESTINO)
    for p in DESTINO.rglob("fio/__init__.py"):
        if p.parent.parent.joinpath("pyproject.toml").exists():
            return p.parent.parent
    raise RuntimeError("pacote sem fio/__init__.py")

usado = None
if origem in ("automatico", "github") and repositorio and "SEU-USUARIO" not in repositorio:
    try:
        url = f"https://codeload.github.com/{{repositorio}}/zip/refs/heads/{{ramo}}"
        req = urllib.request.Request(url, headers={{"User-Agent": "FIO-Colab"}})
        RAIZ = _extrair(urllib.request.urlopen(req, timeout=60).read())
        usado = f"GitHub {{repositorio}}@{{ramo}}"
    except Exception as e:
        if origem == "github":
            raise
        print("GitHub indisponivel (", type(e).__name__, e, "); usando a versao embutida.")
if usado is None:
    RAIZ = _extrair(base64.b64decode("".join(PACOTE.split())))
    usado = "versao embutida no caderno"
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
for m in [m for m in list(sys.modules) if m == "fio" or m.startswith("fio.")]:
    del sys.modules[m]
import fio
from IPython.display import HTML, display

FIO_CSS = """
<style>
.fio-card{{font-family:Arial,sans-serif;background:#fff;color:#17212B;border:1px solid #D2D9D6;border-radius:14px;padding:16px 18px;margin:10px 0;box-shadow:0 1px 2px #17212b0f,0 4px 14px #17212b0d}}
.fio-card h3{{font-family:Georgia,serif;margin:0 0 5px;font-size:21px}}.fio-muted{{color:#5B6770}}.fio-accent{{color:#0E7C6B}}.fio-pill{{display:inline-block;border:1px solid #D2D9D6;border-radius:999px;padding:2px 8px;margin-right:6px;font-size:12px}}.fio-table{{border-collapse:collapse;width:100%;font-size:13px}}.fio-table th{{text-align:left;color:#5B6770;font-size:11px;text-transform:uppercase;letter-spacing:.05em}}.fio-table th,.fio-table td{{padding:7px 10px;border-top:1px solid #D2D9D6}}.fio-table tr:first-child th{{border-top:0}}
</style>
"""

def cartao(titulo, texto, *selos):
    pills = "".join(f"<span class='fio-pill'>{{_html.escape(str(s))}}</span>" for s in selos if s)
    display(HTML(FIO_CSS + f"<div class='fio-card'><h3>{{_html.escape(titulo)}}</h3><p class='fio-muted'>{{_html.escape(texto)}}</p>{{pills}}</div>"))

def quadro(titulo, linhas, colunas):
    cab = "".join(f"<th>{{_html.escape(str(c))}}</th>" for c in colunas)
    corpo = "".join("<tr>" + "".join(f"<td>{{_html.escape(str(v))}}</td>" for v in l) + "</tr>" for l in linhas)
    display(HTML(FIO_CSS + f"<div class='fio-card'><h3>{{_html.escape(titulo)}}</h3><div style='overflow-x:auto'><table class='fio-table'><tr>{{cab}}</tr>{{corpo}}</table></div></div>"))

def mostrar_html(doc, altura=720):
    import warnings
    warnings.filterwarnings("ignore", message="Consider using IPython.display.IFrame")
    display(HTML(f'<iframe srcdoc="{{_html.escape(doc, quote=True)}}" style="width:100%;height:{{altura}}px;border:1px solid #8885;border-radius:8px"></iframe>'))

print(f"F.I.O. Lab {{fio.__version__}} · fonte: {{usado}} · Python {{sys.version.split()[0]}}")
cartao("F.I.O. pronto", "Escolha uma seção abaixo. O caderno usa o GitHub quando disponível e mantém uma cópia embutida como fallback.", f"v{{fio.__version__}}", usado, f"Python {{sys.version.split()[0]}}")
os.environ.setdefault("FIO_HOME", str(TRABALHO / "fio-dados"))
''')
    md("## 2. Onde guardar os dados\nPor padrão, tudo fica nesta sessão e some quando ela termina. Com o Drive, casos e o índice da Receita continuam lá na próxima vez.")
    code('''
#@title Escolher armazenamento { display-mode: "form" }
guardar_no_drive = False  #@param {type:"boolean"}
confirmo_base_legal_para_guardar_no_drive = False  #@param {type:"boolean"}
pasta_no_drive = "FIO-Lab"  #@param {type:"string"}
if guardar_no_drive and confirmo_base_legal_para_guardar_no_drive:
    from google.colab import drive
    drive.mount("/content/drive")
    os.environ["FIO_HOME"] = f"/content/drive/MyDrive/{pasta_no_drive}"
elif guardar_no_drive:
    print("Drive NAO montado: marque a confirmacao de base legal (LGPD) para guardar dados no Drive.")
    os.environ["FIO_HOME"] = str(TRABALHO / "fio-dados")
else:
    os.environ["FIO_HOME"] = str(TRABALHO / "fio-dados")
FIO_HOME = pathlib.Path(os.environ["FIO_HOME"]); FIO_HOME.mkdir(parents=True, exist_ok=True)
# indice no Drive e lido de uma copia local (o disco do Drive e lento para sqlite)
if (FIO_HOME / "cnpj.sqlite").exists() and not str(FIO_HOME).startswith(str(TRABALHO / "fio-dados")):
    local = TRABALHO / "cnpj-local.sqlite"
    shutil.copy(FIO_HOME / "cnpj.sqlite", local)
    os.environ["FIO_INDICE_CNPJ"] = str(local)
elif (FIO_HOME / "cnpj.sqlite").exists():
    os.environ["FIO_INDICE_CNPJ"] = str(FIO_HOME / "cnpj.sqlite")
livre = shutil.disk_usage(str(TRABALHO)).free / 1e9
print(f"dados em: {FIO_HOME} · disco livre da sessao: {livre:,.0f} GB")
print("indice da Receita:", os.environ.get("FIO_INDICE_CNPJ", "ainda nao montado (secao 5)"))
''')
    md("## 3. Conferir as fontes públicas\nConsulta neutra a cada fonte (CNPJ do Banco do Brasil, CEP da Praça da Sé, domínio nic.br). Nenhuma pessoa é pesquisada.")
    code('''
#@title Verificar conexões { display-mode: "form" }
from fio.diagnostico import sondar
from fio.caso import segredos
res = sondar(segredos(), timeout=12)
quadro("Fontes online", [[r["fonte"], "✓ conectado" if r["ok"] else ("— sem chave" if r["ok"] is None else "✗ sem acesso"),
                          r.get("ms", ""), r["dica"]] for r in res], ["fonte", "situação", "ms", "o que fazer"])
print(f"{sum(1 for r in res if r['ok'])} de {len(res)} fontes respondendo.")
''')
    md("## 4. Demonstração\nEmpresas e pessoas inventadas, sem internet. Mapa interativo: arraste os círculos, filtre por confiança e clique para ver detalhes.")
    code('''
#@title Montar a demonstração { display-mode: "form" }
from fio.demo import montar, CASO_ID
from fio.caso import CasoEmDisco
from fio.relatorio.mapa import mapa_html
r = montar(recriar=True)
print(f"{r['metricas']['entidades']} entidades, {r['metricas']['vinculos']} vínculos, {r['metricas']['observacoes']} observações")
display(HTML(mapa_html(CasoEmDisco(CASO_ID).grafo(), altura=560)))
''')
    md("""## 5. Índice da Receita Federal por UF
A fonte mais forte do F.I.O.: telefone → empresa → sócios → filiais, sem internet depois de pronto. O caderno descobre o mês mais recente publicado pela Receita, baixa **um arquivo por vez**, filtra pela UF, apaga e segue. Com o Drive ligado (seção 2), o índice fica guardado para as próximas sessões.

São vários arquivos e vários gigabytes: conte com dezenas de minutos a algumas horas, conforme a velocidade da Receita. O filtro reduz o SQLite final e a RAM, mas não o tráfego, porque os arquivos de Estabelecimentos não são separados por UF. Mantenha esta aba aberta; o Colab gratuito desconecta sessões ociosas.""")
    code('''
#@title Montar índice { display-mode: "form" }
ufs = "MG"  #@param {type:"string"}
mes = ""  #@param {type:"string"}
reconstruir = False  #@param {type:"boolean"}
from fio.receita_download import montar as montar_indice, validar_ufs
from fio.indice import IndiceCNPJ
alvo = FIO_HOME / "cnpj.sqlite"
if alvo.exists() and not reconstruir:
    with IndiceCNPJ(os.environ.get("FIO_INDICE_CNPJ", str(alvo))) as _idx:
        m = _idx.meta()
    print("Ja existe um indice:", {k: m.get(k) for k in ("ufs", "mes", "estabelecimentos", "construido_em")})
    print("Marque 'reconstruir' para montar de novo.")
else:
    filtro = validar_ufs({u.strip().upper() for u in ufs.split(",") if u.strip()} or None)
    local = TRABALHO / "cnpj-local.sqlite"
    res = montar_indice(local, ufs=filtro, mes=mes or None, pasta_tmp=TRABALHO / "receita-tmp")
    if local.resolve() != alvo.resolve():
        shutil.copy(local, alvo)
    os.environ["FIO_INDICE_CNPJ"] = str(local)
    quadro("Índice pronto", [[k, v] for k, v in res.items()], ["campo", "valor"])
''')
    md("""## 6. Caso pontual com fontes reais
Os valores de exemplo usam **alvos institucionais públicos**. Troque pelos seus alvos só se tiver base legal. Tipos reconhecidos sozinhos: e-mail (tem @), CNPJ, CEP (8 dígitos com hífen), domínio (tem ponto e letras) e telefone.""")
    code('''
#@title Rodar o caso { display-mode: "form" }
identificador = "TESTE-COLAB-01"  #@param {type:"string"}
titulo = "Teste de funcionamento com alvos institucionais"  #@param {type:"string"}
base_legal = "pesquisa-academica"  #@param ["pesquisa-academica", "lgpd-7-i", "lgpd-7-ii", "lgpd-7-v", "lgpd-7-vi", "lgpd-7-ix", "lgpd-4-iii", "contrato-pentest", "resposta-incidente", "judicial"]
finalidade = "verificar o funcionamento das fontes publicas com alvos institucionais, sem pessoa fisica"  #@param {type:"string"}
responsavel = "Analista"  #@param {type:"string"}
alvos = "00.000.000/0001-91, 01001-000, registro.br"  #@param {type:"string"}
usar_internet = True  #@param {type:"boolean"}
profundidade = 1  #@param {type:"slider", min:0, max:2, step:1}
expandir_escopo = False  #@param {type:"boolean"}
import re
from fio.politica import Caso
from fio.grafo.modelo import Entidade
from fio.core.normalize import normalizar
from fio.core.documentos import cnpj_valido, cnpj_limpar, cep_valido
from fio.lab.pipeline import Config, executar
from fio.grafo.clusters import tabela_correlacao
from fio.relatorio.mapa import mapa_html

def reconhecer(v):
    v = v.strip()
    if "@" in v: return "email", v.lower(), {}
    if cnpj_valido(v): return "cnpj", cnpj_limpar(v), {"cnpj": cnpj_limpar(v)}
    if re.fullmatch(r"\\d{5}-\\d{3}", v) and cep_valido(v): return "cep", re.sub(r"\\D", "", v), {}
    if re.search(r"[a-zA-Z]", v) and "." in v: return "dominio", v.lower(), {}
    t = normalizar(v)
    return "telefone", t.chave, {"ddd": t.ddd, "assinante": t.assinante, "faixa": t.faixa, "uf": t.uf, "e164": t.e164}

itens = [reconhecer(x) for x in alvos.split(",") if x.strip()]
cd = CasoEmDisco(identificador)
if cd.dir.exists():
    shutil.rmtree(cd.dir)
cd.criar(Caso(id=identificador, titulo=titulo, base_legal=base_legal, finalidade=finalidade,
              responsavel=responsavel, escopo=[v for _, v, _ in itens]), responsavel)
for tipo, v, at in itens:
    cd.add_alvo(Entidade(tipo, v, atributos=at), responsavel)
exp = executar(cd, responsavel, Config(profundidade=profundidade, offline=not usar_internet,
                                        expandir_escopo=expandir_escopo, intervalo=1.0,
                                        descricao="caso pontual no Colab"))
m = exp.metricas
print(f"{exp.estado}: {m['entidades']} entidades, {m['vinculos']} vínculos, {m['requisicoes']} requisições "
      f"({m['falhas']} falhas), {m['pivos_bloqueados']} pivôs bloqueados")
g = cd.grafo()
falhas = [r for r in cd.ledger().registros() if r.acao == "coleta.falha"]
if falhas:
    quadro("Fontes que falharam", [[r.coletor, r.resumo] for r in falhas[:15]], ["coletor", "erro"])
display(HTML(mapa_html(g, altura=520)))
quadro("Vínculos mais fortes", [[l["entidade"], l["relacao"], l["vinculada_a"], l["confianca"], l["admiralty"]]
       for l in tabela_correlacao(g)[:25]], ["entidade", "relação", "vinculada a", "confiança", "grau"])
''')
    md("## 7. Laudo e exportação")
    code('''
#@title Gerar laudo e exportar o caso { display-mode: "form" }
caso = "TESTE-COLAB-01"  #@param {type:"string"}
modelo = "laudo"  #@param ["laudo", "relint", "tecnico"]
exportar_pasta_do_caso = False  #@param {type:"boolean"}
from fio.relatorio import gerar_html
from fio.relatorio.laudo import gerar_laudo
from fio.lab.experimentos import Registro
cd = CasoEmDisco(caso); led = cd.ledger()
args = (cd.caso(), cd.grafo(), led.registros(), led.verificar())
exps = Registro(cd.dir).listar()
doc = gerar_html(*args) if modelo == "tecnico" else gerar_laudo(*args, modelo=modelo, experimento=exps[-1].dict() if exps else None)
saida = TRABALHO / f"{modelo}_{caso}.html"
saida.write_text(doc, encoding="utf-8")
arquivos = [saida]
if exportar_pasta_do_caso:
    arquivos.append(pathlib.Path(shutil.make_archive(str(TRABALHO / f"caso_{caso}"), "zip", cd.dir)))
print("gerado:", ", ".join(str(a) for a in arquivos), "| cadeia", "integra" if args[3][0] else "COMPROMETIDA")
try:
    from google.colab import files
    for a in arquivos:
        files.download(str(a))
except ImportError:
    mostrar_html(doc, 480)
''')
    md("## 8. Bancada web\nA interface completa do F.I.O. (casos, mapa, abas, quesitos, experimentos), servida pelo túnel autenticado do Colab.")
    code('''
#@title Abrir a bancada { display-mode: "form" }
exibir = "dentro do caderno"  #@param ["dentro do caderno", "nova aba (experimental)"]
porta = 8765  #@param {type:"integer"}
import time, contextlib, io as _io
from fio.lab.bancada.servidor import servir, Estado
try:
    BANCADA
except NameError:
    with contextlib.redirect_stdout(_io.StringIO()):
        BANCADA = servir(porta=porta, abrir=False, bloquear=False, modo_colab=True)
    time.sleep(0.5)
try:
    from google.colab import output
    if exibir == "dentro do caderno":
        output.serve_kernel_port_as_iframe(porta, path=f"/#t={Estado.token}", height=760)
    else:
        # "nova aba" é conveniência experimental. O iframe é o caminho principal
        # porque mudanças de segurança do navegador podem bloquear o proxy direto.
        # mantemos como conveniência. O iframe acima é o modo suportado principal.
        from google.colab.output import eval_js
        url = eval_js(f"google.colab.kernel.proxyPort({porta})")
        display(HTML(f'<a href="{url.rstrip("/")}/#t={Estado.token}" target="_blank" rel="noopener" style="font-size:16px;font-weight:700">Abrir a bancada em nova aba</a><p>Se o navegador bloquear, use <b>dentro do caderno</b>.</p>'))
except ImportError:
    display(HTML(f'<a href="http://127.0.0.1:{porta}/#t={Estado.token}" target="_blank">Abrir a bancada</a>'))
print("O endereço contém a senha desta sessão. Não compartilhe.")
''')
    md("""## 9. Pesquisa: benchmark com dados reais e avaliação sintética
**Benchmark real** (precisa do índice da seção 5): esconde a raiz do CNPJ e mede quanto cada evidência pública (e-mail, domínio, endereço, nome fantasia, telefone compartilhado, numeração) reúne as filiais de uma mesma empresa sem juntar empresas diferentes. Saída só agregada, sem nomes.

**Avaliação sintética**: mundos fictícios com armadilhas e gabarito.""")
    code('''
#@title Benchmark com dados reais { display-mode: "form" }
municipio = ""  #@param {type:"string"}
max_raizes = 800  #@param {type:"integer"}
semente = 7  #@param {type:"integer"}
from fio.lab.benchmark_real import benchmark, tabela
idx = os.environ.get("FIO_INDICE_CNPJ")
if not idx:
    print("Monte o indice na secao 5 primeiro.")
else:
    r = benchmark(idx, municipio=municipio or None, max_raizes=max_raizes, semente=semente)
    print(tabela(r))
''')
    code('''
#@title Avaliação sintética { display-mode: "form" }
sementes = "1,2,3,4,5"  #@param {type:"string"}
grupos = 12  #@param {type:"integer"}
from fio.lab.avaliacao import avaliar_lote, tabela_lote
agg = avaliar_lote(TRABALHO / "avaliacao", [int(s) for s in sementes.split(",") if s.strip()], grupos)
print(tabela_lote(agg))
''')
    md("## 10. Testes\nSuíte completa e, com internet, o teste de contrato contra as APIs reais (alvos neutros).")
    code('''
#@title Rodar os testes { display-mode: "form" }
testar_fontes_reais = True  #@param {type:"boolean"}
import subprocess
env = {**os.environ, "FIO_SEM_E2E": "1", "PYTHONPATH": str(RAIZ)}
env.pop("FIO_HOME", None); env.pop("FIO_INDICE_CNPJ", None)
p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "testes"], cwd=RAIZ,
                   capture_output=True, text=True, env=env)
print("Suíte:", " ".join(l for l in p.stderr.splitlines() if l.startswith(("Ran", "OK", "FAILED"))))
if p.returncode:
    print(p.stderr[-3000:])
if testar_fontes_reais:
    q = subprocess.run([sys.executable, "testes/ao_vivo.py"], cwd=RAIZ, capture_output=True, text=True, env=env)
    print("\\nFontes reais:\\n" + q.stdout + q.stderr[-1500:])
''')
    md("---\nManual completo: `docs/MANUAL.html` · Coleta passiva, só fontes públicas. O F.I.O. recusa bases vazadas, senhas de terceiros, interceptação e enumeração de mensageria.")


def gerar() -> str:
    sys.path.insert(0, str(RAIZ))
    from fio import __version__
    b64 = base64.b64encode(pacote()).decode()
    CELULAS.clear()
    global _n
    _n = 0
    montar_celulas(b64, __version__, _repo())
    nb = {"cells": CELULAS, "metadata": {
        "colab": {"name": "FIO_Lab_Colab.ipynb", "provenance": [], "toc_visible": True},
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    return json.dumps(nb, ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    texto = gerar()
    if "--checar" in sys.argv:
        atual = SAIDA.read_text(encoding="utf-8") if SAIDA.exists() else ""
        if hashlib.sha256(atual.encode()).digest() != hashlib.sha256(texto.encode()).digest():
            print("colab/FIO_Lab_Colab.ipynb desatualizado: rode python tools/gerar_notebook.py")
            sys.exit(1)
        print("caderno em dia")
        sys.exit(0)
    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(texto, encoding="utf-8")
    print(f"{SAIDA} ({len(texto) // 1024} KB)")