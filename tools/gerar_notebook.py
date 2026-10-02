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

Tudo roda na nuvem do Google, sem instalar nada no seu computador.

### Comece aqui (3 células)

1. **Instalar** (seção 1) e **Preparar a sessão** (seção 2).
2. **Abrir o F.I.O.** (seção 3): a tela do F.I.O. abre dentro do caderno. É ali que se trabalha: informe o telefone, monte o índice da Receita com progresso na tela e baixe o relatório.

Use **Ambiente de execução › Executar tudo** à vontade: o que baixa muito dado ou demora (índice, benchmark, avaliação, testes) só roda quando você marca **executar**.

| Seção | O que faz | Internet |
|---|---|---|
| 1 | Instala o F.I.O. (do GitHub ou do próprio caderno) | opcional |
| 2 | Prepara a sessão efêmera (sem Drive) e mostra os recursos da máquina | não |
| **3** | **Abre o F.I.O. dentro do caderno** | não |
| *Avançado (opcional)* | | |
| 4 | Confere as fontes públicas | sim |
| 5 | Demonstração com mapa interativo | não |
| 6 | Índice da Receita pelo caderno (segundo plano, progresso ao vivo) | sim (alguns GB) |
| 7 | Caso pontual com fontes reais | sim |
| 8 | Relatório e exportação | não |
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
os.environ.setdefault("FIO_HOME", str(TRABALHO / "fio-runtime"))
''')
    md("## 2. Sessão efêmera\nNada é montado no Google Drive. Casos, fila e índice ficam apenas no runtime e somem quando a sessão é encerrada. Baixe os relatórios que quiser preservar.")
    code('''
#@title Preparar sessão efêmera { display-mode: "form" }
limpar_sessao_anterior = False  #@param {type:"boolean"}
FIO_HOME = TRABALHO / "fio-runtime"
if limpar_sessao_anterior and FIO_HOME.exists():
    shutil.rmtree(FIO_HOME)
FIO_HOME.mkdir(parents=True, exist_ok=True)
os.environ["FIO_HOME"] = str(FIO_HOME)
if (FIO_HOME / "cnpj.sqlite").exists():
    os.environ["FIO_INDICE_CNPJ"] = str(FIO_HOME / "cnpj.sqlite")
else:
    os.environ.pop("FIO_INDICE_CNPJ", None)

def _ram_gb():
    try:
        for linha in open("/proc/meminfo"):
            if linha.startswith("MemTotal"):
                return int(linha.split()[1]) / 1e6
    except OSError:
        pass
    return None

livre = shutil.disk_usage(str(TRABALHO)).free / 1e9
ram = _ram_gb()
cpus = os.cpu_count() or 1
try:
    import google.colab  # noqa: F401
    ambiente = "Google Colab"
except ImportError:
    ambiente = "fora do Colab (execução local)"
print(f"sessao efemera: {FIO_HOME}")
print(f"ambiente: {ambiente} · Python {sys.version.split()[0]} · {cpus} CPU(s)"
      + (f" · RAM {ram:,.1f} GB" if ram else "") + f" · disco livre {livre:,.0f} GB")
avisos = []
if livre < 12:
    avisos.append("disco livre abaixo de 12 GB: o indice da Receita por UF pode nao caber "
                  "(os ZIPs sao baixados um por vez, mas o maior chega a varios GB). "
                  "Reinicie o runtime para liberar espaco.")
if ram is not None and ram < 4:
    avisos.append("menos de 4 GB de RAM: use UF unica no indice e profundidade 1 nos casos.")
if sys.version_info < (3, 10):
    avisos.append("Python abaixo de 3.10: o F.I.O. exige 3.10 ou mais novo.")
for a in avisos:
    print("ATENCAO:", a)
if not avisos:
    print("recursos suficientes para o fluxo completo.")
print("Ao encerrar o runtime, estes dados somem. Exporte o relatorio antes de sair.")
''')
    md("""## 3. Abrir o F.I.O.
**É por aqui que se trabalha.** Abre a **bancada completa** do F.I.O. dentro do caderno (a mesma da demonstração do GitHub): painel, caso, **grafo**, vínculos, observações, custódia, experimentos, ferramentas BR e o índice da Receita com progresso na tela. Se preferir uma tela mínima (só telefone, índice e relatório), escolha `interface: simples`.

Tudo o que vem depois deste ponto é **opcional**: demonstração, verificação das fontes, índice pelo caderno, caso pontual, pesquisa e testes.""")
    code('''
#@title Abrir o F.I.O. { display-mode: "form" }
interface = "completa"  #@param ["completa", "simples"]
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
Estado.interface_simples = (interface == "simples")   # vale para a proxima abertura
try:
    from google.colab import output
    if exibir == "dentro do caderno":
        output.serve_kernel_port_as_iframe(porta, path=f"/#t={Estado.token}", height=860)
    else:
        # "nova aba" é conveniência experimental. O iframe é o caminho principal
        # porque mudanças de segurança do navegador podem bloquear o proxy direto.
        from google.colab.output import eval_js
        url = eval_js(f"google.colab.kernel.proxyPort({porta})")
        display(HTML(f'<a href="{url.rstrip("/")}/#t={Estado.token}" target="_blank" rel="noopener" style="font-size:16px;font-weight:700">Abrir o F.I.O. em nova aba</a><p>Se o navegador bloquear, use <b>dentro do caderno</b>.</p>'))
except ImportError:
    display(HTML(f'<a href="http://127.0.0.1:{porta}/#t={Estado.token}" target="_blank">Abrir o F.I.O.</a>'))
print("O endereço contém a senha desta sessão. Não compartilhe.")
''')
    md("""---
## Avançado (opcional)
As seções abaixo **não são necessárias** para usar o F.I.O. As que baixam muito dado ou demoram (índice, benchmark, avaliação, testes) só rodam quando você marca a caixa **executar**, para que *Executar tudo* não dispare nada pesado sem querer.""")
    md("## 4. Conferir as fontes públicas\nConsulta neutra a cada fonte (CNPJ do Banco do Brasil, CEP da Praça da Sé, domínio nic.br). Nenhuma pessoa é pesquisada.")
    code('''
#@title Verificar conexões { display-mode: "form" }
from fio.diagnostico import sondar
from fio.caso import segredos
res = sondar(segredos(), timeout=12)
quadro("Fontes online", [[r["fonte"], "✓ conectado" if r["ok"] else ("— sem chave" if r["ok"] is None else "✗ sem acesso"),
                          r.get("ms", ""), r["dica"]] for r in res], ["fonte", "situação", "ms", "o que fazer"])
print(f"{sum(1 for r in res if r['ok'])} de {len(res)} fontes respondendo.")
''')
    md("## 5. Demonstração\nEmpresas e pessoas inventadas, sem internet. Mapa interativo: arraste os círculos, filtre por confiança e clique para ver detalhes.")
    code('''
#@title Montar a demonstração { display-mode: "form" }
from fio.demo import montar, CASO_ID
from fio.caso import CasoEmDisco
from fio.relatorio.mapa import mapa_html
r = montar(recriar=True)
print(f"{r['metricas']['entidades']} entidades, {r['metricas']['vinculos']} vínculos, {r['metricas']['observacoes']} observações")
display(HTML(mapa_html(CasoEmDisco(CASO_ID).grafo(), altura=560)))
''')
    md("""## 6. Índice da Receita Federal por UF (pelo caderno)
A fonte mais forte do F.I.O.: telefone → empresa → sócios → filiais, sem internet depois de pronto. O mesmo índice pode ser montado pela tela da seção 3; aqui é a versão pelo caderno.

**Roda em segundo plano e mostra o progresso ao vivo.** O downloader trabalha **um arquivo por vez** (alguns GB no total), filtra pela UF e apaga o ZIP antes do seguinte; leva de 10 a 40 minutos conforme a banda. A célula só **acompanha**: se você interromper (■), o trabalho continua e basta rodar a célula de novo para voltar a acompanhar.

Se a listagem raiz da Receita resetar a conexão, o F.I.O. tenta `urllib`, depois `curl` e, por fim, sonda diretamente pastas mensais recentes. Informar `mes` (AAAA-MM) pula a listagem raiz. O filtro reduz o SQLite final e a RAM, mas não o tráfego, porque os arquivos de Estabelecimentos não são separados por UF.""")
    code('''
#@title Montar índice (segundo plano, com progresso) { display-mode: "form" }
executar = False  #@param {type:"boolean"}
ufs = "MG"  #@param {type:"string"}
mes = ""  #@param {type:"string"}
reconstruir = False  #@param {type:"boolean"}
import threading, time, collections, datetime
from IPython.display import clear_output
from fio.receita_download import montar as montar_indice, validar_ufs
from fio.indice import IndiceCNPJ
alvo = FIO_HOME / "cnpj.sqlite"

def _hora():
    return datetime.datetime.now().strftime("%H:%M:%S")

def _acompanhar(job):
    """Mostra o andamento a cada 3 s. Interromper (■) so para de acompanhar."""
    try:
        while job["fio"].is_alive():
            dec = int(time.time() - job["t0"])
            clear_output(wait=True)
            print(f"Montando o indice da Receita (UF: {job['ufs']}) · {dec // 60} min {dec % 60:02d} s")
            print("-" * 72)
            for l in list(job["linhas"])[-10:]:
                print(l)
            print("-" * 72)
            print("Acompanhando. Interromper (■) NAO cancela: rode a celula de novo para voltar.")
            time.sleep(3)
    except KeyboardInterrupt:
        print("\\nParou de acompanhar; o indice continua sendo montado. Rode a celula para ver o andamento.")
        return
    clear_output(wait=True)
    if job["erro"]:
        print("A Receita nao respondeu a partir deste runtime (ou o processo falhou). O caso continua utilizavel sem o indice local.")
        print(job["erro"])
        print("Tente preencher 'mes' (AAAA-MM) ou rode novamente mais tarde; o downloader ja alterna urllib/curl.")
        for l in list(job["linhas"])[-6:]:
            print(l)
    else:
        os.environ["FIO_INDICE_CNPJ"] = str(alvo)
        quadro("Índice pronto", [[k, v] for k, v in job["res"].items()], ["campo", "valor"])

job = globals().get("INDICE_JOB")
if job and job["fio"].is_alive():
    _acompanhar(job)                       # ja ha um em andamento: so acompanha
elif alvo.exists() and not reconstruir:
    with IndiceCNPJ(os.environ.get("FIO_INDICE_CNPJ", str(alvo))) as _idx:
        m = _idx.meta()
    print("Ja existe um indice:", {k: m.get(k) for k in ("ufs", "mes", "estabelecimentos", "construido_em")})
    print("Marque 'reconstruir' (e 'executar') para montar de novo.")
elif not executar:
    print("Nada foi baixado. Marque 'executar' e rode a celula (▶) para montar o indice.")
    print("Prefira a tela da secao 3 se quiser acompanhar sem sair dela.")
else:
    filtro = validar_ufs({u.strip().upper() for u in ufs.split(",") if u.strip()} or None)
    job = INDICE_JOB = {"linhas": collections.deque(maxlen=300), "res": None, "erro": None,
                        "t0": time.time(), "ufs": ",".join(sorted(filtro)) if filtro else "todas"}
    def _log(msg):
        job["linhas"].append(f"{_hora()}  {msg}")
    def _rodar():
        try:
            job["res"] = montar_indice(alvo, ufs=filtro, mes=mes or None,
                                       pasta_tmp=FIO_HOME / "receita-tmp", log=_log)
        except BaseException as e:      # noqa: BLE001 - o erro vai para a tela
            job["erro"] = f"{type(e).__name__}: {e}"
    job["fio"] = threading.Thread(target=_rodar, daemon=True)
    job["fio"].start()
    _acompanhar(job)
''')
    md("""### 6b. Já tenho o índice (enviar arquivo ou baixar de uma URL)
**Use esta opção se a Receita não responde a partir do Colab** (a Receita costuma bloquear faixas de IP de nuvem, e o erro será "tempo esgotado ao conectar"). Monte o índice no **seu computador** (`fio indice baixar --uf MG`, gera `cnpj.sqlite`) e traga-o para cá:

- **enviar arquivo**: abre o seletor do navegador e envia o `cnpj.sqlite` para esta sessão;
- **baixar de uma URL**: se o arquivo estiver publicado em algum endereço seu (https), informe em `url`; o download mostra o progresso e retoma se cair.""")
    code('''
#@title Enviar índice pronto (cnpj.sqlite) { display-mode: "form" }
executar = False  #@param {type:"boolean"}
modo = "enviar arquivo"  #@param ["enviar arquivo", "baixar de uma URL"]
url = ""  #@param {type:"string"}
import shutil as _sh
from fio.indice import IndiceCNPJ
alvo = FIO_HOME / "cnpj.sqlite"
if not executar:
    print("Marque 'executar' e rode (▶) para trazer um indice que voce ja montou no seu computador.")
else:
    if modo == "baixar de uma URL":
        from fio.receita_download import baixar
        if not url.startswith("https://"):
            raise ValueError("informe uma URL https:// no campo 'url'")
        baixar(url, alvo, log=print)
    else:
        try:
            from google.colab import files
        except ImportError:
            raise RuntimeError("o envio de arquivo so existe no Colab; fora dele, aponte FIO_INDICE_CNPJ para o seu cnpj.sqlite")
        enviados = files.upload()
        if not enviados:
            raise RuntimeError("nenhum arquivo enviado")
        nome = next(iter(enviados))
        _sh.move(nome, alvo)
    with IndiceCNPJ(str(alvo)) as _idx:
        est = _idx.estatisticas()
        meta = _idx.meta()
    if not est.get("estabelecimento"):
        alvo.unlink(missing_ok=True)
        raise ValueError("o arquivo nao parece um indice do F.I.O. (sem estabelecimentos); descartado")
    os.environ["FIO_INDICE_CNPJ"] = str(alvo)
    quadro("Índice pronto", [[k, v] for k, v in {**est, **{k: meta.get(k) for k in ("ufs", "mes", "construido_em")}}.items()], ["campo", "valor"])
''')
    md("""## 7. Caso pontual com fontes reais
Os valores de exemplo usam **alvos institucionais públicos**. Troque pelos seus alvos só se tiver base legal. Tipos reconhecidos sozinhos: e-mail (tem @), CNPJ, CEP (8 dígitos com hífen), domínio (tem ponto e letras) e telefone.""")
    code('''
#@title Rodar o caso { display-mode: "form" }
identificador = "TESTE-COLAB-01"  #@param {type:"string"}
titulo = "Teste de funcionamento com alvos institucionais"  #@param {type:"string"}
base_legal = "pesquisa-academica"  #@param ["pesquisa-academica", "lgpd-7-i", "lgpd-7-ii", "lgpd-7-v", "lgpd-7-vi", "lgpd-7-ix", "lgpd-4-iii", "contrato-pentest", "resposta-incidente", "judicial"]
finalidade = "verificar o funcionamento das fontes publicas com alvos institucionais, sem pessoa fisica"  #@param {type:"string"}
responsavel = "Analista"  #@param {type:"string"}
telefone = ""  #@param {type:"string"}
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

entradas = ([telefone] if telefone.strip() else []) + [x for x in alvos.split(",") if x.strip()]
itens = [reconhecer(x) for x in entradas]
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
    md("## 8. Relatório e exportação\nBaixe primeiro um modelo vazio, se quiser usar o F.I.O. apenas como roteiro. Depois de um caso, exporte laudo, RELINT ou relatório técnico. Como a sessão é efêmera, o download é a forma de preservar o resultado.")
    code('''
#@title Baixar modelo vazio de relatório { display-mode: "form" }
formato_modelo = "markdown"  #@param ["markdown", "html"]
from fio.relatorio.modelo import modelo_markdown, modelo_html
texto_modelo = modelo_html() if formato_modelo == "html" else modelo_markdown()
ext = "html" if formato_modelo == "html" else "md"
modelo_saida = TRABALHO / f"FIO-modelo-relatorio.{ext}"
modelo_saida.write_text(texto_modelo, encoding="utf-8")
try:
    from google.colab import files
    files.download(str(modelo_saida))
except ImportError:
    print(modelo_saida)
''')
    code('''
#@title Gerar relatório do caso { display-mode: "form" }
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
    md("""## 9. Pesquisa: benchmark com dados reais e avaliação sintética
**Benchmark real** (precisa do índice da seção 6): esconde a raiz do CNPJ e mede quanto cada evidência pública (e-mail, domínio, endereço, nome fantasia, telefone compartilhado, numeração) reúne as filiais de uma mesma empresa sem juntar empresas diferentes. Saída só agregada, sem nomes.

**Avaliação sintética**: mundos fictícios com armadilhas e gabarito.""")
    code('''
#@title Benchmark com dados reais { display-mode: "form" }
executar = False  #@param {type:"boolean"}
municipio = ""  #@param {type:"string"}
max_raizes = 800  #@param {type:"integer"}
semente = 7  #@param {type:"integer"}
from fio.lab.benchmark_real import benchmark, tabela
idx = os.environ.get("FIO_INDICE_CNPJ")
if not executar:
    print("Marque 'executar' e rode (▶). Precisa do indice da secao 6 (ou da tela da secao 3).")
elif not idx:
    print("Monte o indice primeiro (secao 6 ou a tela da secao 3).")
else:
    r = benchmark(idx, municipio=municipio or None, max_raizes=max_raizes, semente=semente)
    print(tabela(r))
''')
    code('''
#@title Avaliação sintética { display-mode: "form" }
executar = False  #@param {type:"boolean"}
sementes = "1,2,3,4,5"  #@param {type:"string"}
grupos = 12  #@param {type:"integer"}
from fio.lab.avaliacao import avaliar_lote, tabela_lote
if not executar:
    print("Marque 'executar' e rode (▶). Leva alguns minutos; nao usa internet.")
else:
    agg = avaliar_lote(TRABALHO / "avaliacao", [int(s) for s in sementes.split(",") if s.strip()], grupos)
    print(tabela_lote(agg))
''')
    md("## 10. Testes\nSuíte completa e, com internet, o teste de contrato contra as APIs reais (alvos neutros).")
    code('''
#@title Rodar os testes { display-mode: "form" }
executar = False  #@param {type:"boolean"}
testar_fontes_reais = True  #@param {type:"boolean"}
import subprocess
if not executar:
    print("Marque 'executar' e rode (▶) para rodar a suite; ela leva alguns minutos.")
else:
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
