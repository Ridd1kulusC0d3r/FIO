"""Bancada web local.

Um servidor http.server em 127.0.0.1, uma pagina, uma API JSON. Tres
protecoes, porque uma API local que dispara coleta e devolve dado pessoal
e alvo classico de pagina maliciosa aberta no mesmo navegador:

1. escuta so em loopback;
2. token aleatorio por sessao, exigido em TODA rota /api (cabecalho
   X-FIO-Token; ou ?t= apenas para abrir relatorio em nova aba);
3. checagem do cabecalho Host contra DNS rebinding, e nenhum cabecalho CORS
   -- requisicao de outra origem nao le resposta nem passa do preflight.
"""

from __future__ import annotations

import hmac
import json
import re
import secrets
import threading
import urllib.parse
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from ... import __version__
from ...caso import CasoEmDisco, listar_casos, raiz
from ...politica import Caso, BASES_LEGAIS, ViolacaoDeEscopo
from ...grafo.modelo import Entidade
from ...grafo.clusters import detectar_clusters, pontes, tabela_correlacao
from ...core.normalize import normalizar, variantes
from ...core.documentos import analisar, extrair_documentos
from .. import plugins
from ..fila import Fila
from ..experimentos import Registro

UI = Path(__file__).with_name("ui.html")
UI_COLAB = Path(__file__).with_name("ui_colab.html")
_ID_OK = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class Estado:
    token = ""
    hosts_extra: tuple = ()
    permitir_iframe = False
    modo_colab = False
    interface_simples = False    # no Colab, a tela completa e a padrao
    fila: Fila | None = None
    porta = 8765
    ator = "bancada"


# --------------------------------------------------------- manipuladores
def _tarefa_pipeline(caso_id: str, p: dict, log) -> dict:
    from ..pipeline import Config, executar
    cd = CasoEmDisco(caso_id)
    cfg = Config(coletores=p.get("coletores") or None,
                 profundidade=int(p.get("profundidade", 1)),
                 offline=bool(p.get("offline", False)),
                 expandir_escopo=bool(p.get("expandir_escopo", False)),
                 intervalo=float(p.get("intervalo", 1.5)),
                 descricao=p.get("descricao", "execucao pela bancada"))
    exp = executar(cd, p.get("ator") or Estado.ator, cfg, log=log)
    return {"experimento": exp.id, "estado": exp.estado, "metricas": exp.metricas,
            "estagios": exp.estagios, "erro": exp.erro}


def _tarefa_avaliar(_caso: str, p: dict, log) -> dict:
    from ..avaliacao import avaliar_lote, tabela_lote
    sementes = [int(x) for x in str(p.get("sementes", "1,2,3")).split(",") if x.strip()][:20]
    destino = raiz() / "lab" / "avaliacoes"
    agg = avaliar_lote(destino, sementes, int(p.get("grupos", 12)), log=log)
    return {"agregado": agg, "markdown": tabela_lote(agg)}


def _tarefa_indice(_caso: str, p: dict, log) -> dict:
    """Monta o índice da Receita em segundo plano, sempre na sessão local."""
    import os
    from ...receita_download import montar, validar_ufs
    saida = raiz() / "cnpj.sqlite"
    ufs = validar_ufs({x.strip().upper() for x in str(p.get("ufs", "")).split(",") if x.strip()} or None)
    mes = str(p.get("mes") or "").strip() or None
    if saida.exists() and not bool(p.get("reconstruir", False)):
        from ...indice import IndiceCNPJ
        with IndiceCNPJ(saida) as idx:
            return {"estado": "existente", "arquivo": str(saida), "meta": idx.meta()}
    log(f"indice Receita: UF={','.join(sorted(ufs)) if ufs else 'todas'} mes={mes or 'automatico'}")
    res = montar(saida, ufs=ufs, mes=mes, pasta_tmp=raiz() / "receita-tmp", log=log)
    os.environ["FIO_INDICE_CNPJ"] = str(saida)
    return {"estado": "pronto", "arquivo": str(saida), **res}


# ----------------------------------------------------------------- http
class Manipulador(BaseHTTPRequestHandler):
    server_version = f"FIO-Bancada/{__version__}"

    def log_message(self, fmt, *args):   # silencioso; o ledger e o registro
        pass

    # ------------------------------------------------------------- saida
    def _json(self, obj, status=200):
        corpo = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _html(self, texto: str, status=200, download_name: str | None = None):
        corpo = texto.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        if download_name:
            self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
        if not Estado.permitir_iframe:
            self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; script-src 'unsafe-inline'; "
                         "style-src 'unsafe-inline'; img-src 'self' data:; "
                         "connect-src 'self'; frame-ancestors "
                         + ("*" if Estado.permitir_iframe else "'none'"))
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _texto(self, texto: str, content_type="text/plain; charset=utf-8",
               download_name: str | None = None, status=200):
        corpo = texto.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if download_name:
            self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _erro(self, msg, status=400):
        self._json({"erro": msg}, status)

    # --------------------------------------------------------- seguranca
    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").split(":")[0].lower()
        if host in ("127.0.0.1", "localhost"):
            return True
        # proxies autenticados (Google Colab, Codespaces) usam outro Host; so
        # os sufixos declarados explicitamente passam, e o token continua
        # exigido em toda rota /api
        return any(h == "*" or host == h or host.endswith("." + h.lstrip("."))
                   for h in Estado.hosts_extra)

    def _token_ok(self, qs: dict) -> bool:
        t = self.headers.get("X-FIO-Token") or (qs.get("t") or [""])[0]
        return bool(t) and hmac.compare_digest(t, Estado.token)

    def _corpo(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if n > 2_000_000:
            raise ValueError("corpo grande demais")
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def _caso(self, cid: str) -> CasoEmDisco:
        if not _ID_OK.match(cid):
            raise ValueError("id de caso invalido")
        cd = CasoEmDisco(cid)
        if not cd.existe:
            raise FileNotFoundError(cid)
        return cd

    # -------------------------------------------------------------- rotas
    @staticmethod
    def _caminho(bruto: str) -> tuple[str, bool]:
        """Separa o prefixo /simples/: a tela simples do Colab e a bancada
        completa compartilham a mesma API, mas a simples usa `./api` relativo
        a pagina, entao `/simples/api/...` precisa chegar como `/api/...`."""
        if bruto == "/simples" or bruto.startswith("/simples/"):
            return (bruto[len("/simples"):] or "/"), True
        return bruto, False

    def do_GET(self):
        if not self._host_ok():
            return self._erro("host nao permitido", 403)
        url = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(url.query)
        caminho, simples = self._caminho(url.path)
        if caminho in ("/", "/index.html"):
            quer_simples = simples or (Estado.modo_colab and Estado.interface_simples)
            pagina = UI_COLAB if quer_simples and UI_COLAB.exists() else UI
            return self._html(pagina.read_text(encoding="utf-8"))
        if caminho in ("/workbench", "/workbench/"):
            return self._html(UI.read_text(encoding="utf-8"))
        if not caminho.startswith("/api/"):
            return self._erro("nao encontrado", 404)
        if not self._token_ok(qs):
            return self._erro("token ausente ou invalido", 401)
        try:
            return self._rota_get(caminho, qs)
        except FileNotFoundError as e:
            return self._erro(f"nao encontrado: {e}", 404)
        except (ValueError, KeyError) as e:
            return self._erro(str(e))

    def do_POST(self):
        if not self._host_ok():
            return self._erro("host nao permitido", 403)
        url = urllib.parse.urlparse(self.path)
        if not self.headers.get("X-FIO-Token") or not self._token_ok({}):
            return self._erro("token ausente ou invalido", 401)
        try:
            return self._rota_post(self._caminho(url.path)[0], self._corpo())
        except ViolacaoDeEscopo as e:
            return self._erro(f"politica do caso: {e}", 403)
        except FileNotFoundError as e:
            return self._erro(f"nao encontrado: {e}", 404)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
            return self._erro(str(e))

    def _rota_get(self, caminho: str, qs: dict):
        partes = [p for p in caminho.split("/") if p][1:]      # sem 'api'
        if partes == ["estado"]:
            return self._json({"versao": __version__, "bases_legais": BASES_LEGAIS,
                               "inventario": plugins.inventario(),
                               "tarefas": Estado.fila.listar(15)})
        if partes == ["casos"]:
            return self._json(listar_casos())
        if partes == ["diagnostico"]:
            from ...diagnostico import sondar
            from ...caso import segredos
            return self._json(sondar(segredos(), timeout=8))
        if partes == ["indice"]:
            from ...indice import IndiceCNPJ
            p = raiz() / "cnpj.sqlite"
            if not p.exists():
                return self._json({"existe": False})
            with IndiceCNPJ(p) as idx:
                return self._json({"existe": True, "arquivo": str(p), "meta": idx.meta(),
                                   "estatisticas": idx.estatisticas()})
        if partes == ["modelo-relatorio"]:
            from ...relatorio.modelo import modelo_markdown, modelo_html
            formato = (qs.get("formato") or ["md"])[0]
            download = (qs.get("download") or [""])[0] in ("1", "true", "sim")
            if formato == "html":
                return self._html(modelo_html(), download_name="FIO-modelo-relatorio.html" if download else None)
            return self._texto(modelo_markdown(), "text/markdown; charset=utf-8",
                               "FIO-modelo-relatorio.md" if download else None)
        if partes[:1] == ["tarefas"] and len(partes) == 2:
            t = Estado.fila.obter(int(partes[1]))
            return self._json(t) if t else self._erro("tarefa inexistente", 404)
        if partes == ["avaliacao"]:
            arq = raiz() / "lab" / "avaliacoes" / "avaliacao_lote.json"
            return self._json(json.loads(arq.read_text()) if arq.exists() else {})
        if partes[:1] == ["casos"] and len(partes) >= 2:
            cd = self._caso(partes[1])
            sub = partes[2] if len(partes) > 2 else ""
            if sub == "":
                g = cd.grafo()
                return self._json({"caso": cd.caso().dict(),
                                   "entidades": len(g.entidades),
                                   "vinculos": len(g.arestas),
                                   "ledger": len(cd.ledger())})
            if sub == "grafo":
                g = cd.grafo()
                return self._json({**g.dict(),
                                   "clusters": [c.dict() for c in detectar_clusters(g)],
                                   "pontes": pontes(g),
                                   "tabela": tabela_correlacao(g)})
            if sub == "ledger":
                led = cd.ledger()
                ok, probs = led.verificar()
                return self._json({"integro": ok, "problemas": probs,
                                   "registros": [r.__dict__ for r in led.registros()[-400:]]})
            if sub == "experimentos":
                return self._json([e.dict() for e in Registro(cd.dir).listar()])
            if sub == "comparar":
                return self._json(Registro(cd.dir).comparar(qs["a"][0], qs["b"][0]))
            if sub == "relatorio":
                modelo = (qs.get("modelo") or ["tecnico"])[0]
                download = (qs.get("download") or [""])[0] in ("1", "true", "sim")
                led = cd.ledger()
                c, g, regs, verif = cd.caso(), cd.grafo(), led.registros(), led.verificar()
                nome = f"{modelo}_{cd.caso_id}.html" if download else None
                if modelo in ("laudo", "relint"):
                    from ...relatorio.laudo import gerar_laudo
                    exps = Registro(cd.dir).listar()
                    return self._html(gerar_laudo(c, g, regs, verif, modelo=modelo,
                                                  experimento=exps[-1].dict() if exps else None),
                                      download_name=nome)
                from ...relatorio import gerar_html
                return self._html(gerar_html(c, g, regs, verif), download_name=nome)
        return self._erro("rota inexistente", 404)

    def _rota_post(self, caminho: str, d: dict):
        partes = [p for p in caminho.split("/") if p][1:]
        ator = str(d.get("ator") or Estado.ator)[:80]
        if partes == ["casos"]:
            if not _ID_OK.match(str(d.get("id", ""))):
                raise ValueError("id do caso: letras, numeros, ponto, hifen, ate 64")
            c = Caso(id=d["id"], titulo=d["titulo"], base_legal=d["base_legal"],
                     finalidade=d["finalidade"], responsavel=d["responsavel"],
                     escopo=[s.strip() for s in d.get("escopo", []) if s.strip()])
            cd = CasoEmDisco(c.id)
            if cd.existe:
                raise ValueError("caso ja existe")
            cd.criar(c, ator)
            return self._json({"ok": True, "id": c.id}, 201)
        if partes == ["numero"]:
            t = normalizar(str(d.get("valor", "")), ddd_padrao=d.get("ddd") or None)
            return self._json({**t.dict(), "variantes": variantes(t)})
        if partes == ["documento"]:
            if d.get("texto"):
                return self._json([x.dict() for x in extrair_documentos(str(d["texto"])[:500000])])
            return self._json(analisar(d["tipo"], str(d["valor"])).dict())
        if partes == ["indice"]:
            tid = Estado.fila.enfileirar("indice", "-", d)
            return self._json({"tarefa": tid}, 202)
        if partes == ["avaliar"]:
            tid = Estado.fila.enfileirar("avaliar", "-", d)
            return self._json({"tarefa": tid}, 202)
        if partes == ["demo"]:
            from ...demo import montar
            return self._json(montar(ator, recriar=bool(d.get("recriar"))), 201)
        if partes[:1] == ["casos"] and len(partes) == 3:
            cd = self._caso(partes[1])
            if partes[2] == "alvos":
                tipo, valor = d["tipo"], str(d["valor"]).strip()
                atributos, rotulo = {}, ""
                if tipo == "telefone":
                    t = normalizar(valor, ddd_padrao=d.get("ddd") or None)
                    if not t.valido:
                        raise ValueError(f"telefone invalido: {t.justificativa}")
                    valor, rotulo = t.chave, t.formatado()
                    atributos = {"ddd": t.ddd, "assinante": t.assinante,
                                 "faixa": t.faixa, "uf": t.uf, "e164": t.e164}
                elif tipo in ("email", "dominio"):
                    valor = valor.lower()
                cd.add_alvo(Entidade(tipo, valor, rotulo=rotulo, atributos=atributos), ator)
                return self._json({"ok": True, "id": f"{tipo}:{valor}"}, 201)
            if partes[2] == "pipeline":
                d["ator"] = ator
                tid = Estado.fila.enfileirar("pipeline", cd.caso_id, d)
                return self._json({"tarefa": tid}, 202)
            if partes[2] == "quesitos":
                c = cd.caso()
                if d.get("n"):
                    q = next(q for q in c.quesitos if q["n"] == int(d["n"]))
                    q["resposta"] = str(d.get("resposta", ""))
                else:
                    c.quesitos.append({"n": len(c.quesitos) + 1,
                                       "texto": str(d["texto"]), "resposta": "",
                                       "entidades": d.get("entidades", [])})
                cd.salvar_caso(c)
                cd.ledger(ator).registrar("quesito.atualizado", resumo=str(d)[:200])
                return self._json({"ok": True, "quesitos": c.quesitos})
        return self._erro("rota inexistente", 404)


def servir(porta: int = 8765, abrir: bool = True, token: str | None = None,
           bloquear: bool = True, hosts_extra: list[str] | None = None,
           modo_colab: bool = False, interface_simples: bool = False):
    """modo_colab: o Colab entrega a pagina por um proxy autenticado do
    Google, com Host proprio e dentro de iframe. Nesse modo aceitamos
    qualquer Host e a exibicao em iframe; o token segue obrigatorio."""
    import os
    plugins.carregar()
    Estado.token = token or secrets.token_urlsafe(24)
    extra = list(hosts_extra or []) + [h.strip() for h in
                                       os.environ.get("FIO_HOSTS_PERMITIDOS", "").split(",") if h.strip()]
    if modo_colab:
        extra.append("*")
    Estado.hosts_extra = tuple(h.lower() for h in extra)
    Estado.permitir_iframe = modo_colab
    Estado.modo_colab = modo_colab
    Estado.interface_simples = interface_simples
    Estado.porta = porta
    (raiz() / "lab").mkdir(parents=True, exist_ok=True)
    Estado.fila = Fila(raiz() / "lab" / "fila.sqlite")
    Estado.fila.registrar("pipeline", _tarefa_pipeline)
    Estado.fila.registrar("avaliar", _tarefa_avaliar)
    Estado.fila.registrar("indice", _tarefa_indice)
    Estado.fila.iniciar(2)
    srv = ThreadingHTTPServer(("127.0.0.1", porta), Manipulador)
    url = f"http://127.0.0.1:{porta}/#t={Estado.token}"
    # flush: com a saida num pipe (testes, lancadores, Colab) o Python guarda
    # no buffer e quem le a primeira linha ficaria esperando para sempre
    print(f"F.I.O. Lab {__version__} — bancada em {url}", flush=True)
    print("o token no endereco e a unica credencial desta sessao; nao compartilhe", flush=True)
    if abrir:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    if not bloquear:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        Estado.fila.parar()
        srv.server_close()
