"""Diagnostico de conectividade com as fontes online.

Faz UMA consulta neutra a cada fonte -- nenhuma envolve pessoa: CNPJ do
Banco do Brasil (empresa de capital aberto), CEP da Praca da Se, dominio
nic.br, termo generico no Querido Diario. Serve para responder, antes de
abrir um caso, a pergunta mais comum de quem esta comecando: "o programa
consegue falar com as fontes a partir da minha rede?".

Nao grava ledger nem cache: nao e coleta, e teste de encanamento.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import ssl
import time
import urllib.error
import urllib.request

from .coletores.base import UA

def carregar_fontes(caminho: Path | None = None) -> list[dict]:
    """Fontes declaradas em fontes.json (URL, segredo e canario)."""
    arq = caminho or Path(__file__).with_name("fontes.json")
    return json.loads(arq.read_text(encoding="utf-8"))["fontes"]


def checar_canario(corpo: bytes, canario: dict) -> tuple[bool | None, str]:
    """True se a resposta tem a forma esperada; None se nao ha canario.

    Chaves: `json_chave` (campo que deve existir, em dict ou no 1o item de
    lista), `igual` (valor exato do campo), `contem` (texto, no campo ou no
    corpo inteiro).
    """
    if not canario:
        return None, ""
    texto = corpo.decode("utf-8", "replace")
    chave = canario.get("json_chave")
    valor = texto
    if chave:
        try:
            dados = json.loads(texto)
        except json.JSONDecodeError:
            return False, "resposta nao e JSON"
        if isinstance(dados, list):
            dados = dados[0] if dados else {}
        if not isinstance(dados, dict) or chave not in dados:
            return False, f"campo '{chave}' ausente (formato mudou?)"
        valor = dados[chave]
        if "igual" in canario and str(valor) != str(canario["igual"]):
            return False, f"'{chave}' = {str(valor)[:40]!r}, esperado {canario['igual']!r}"
        if "contem" not in canario:
            return True, ""
    alvo = str(valor)
    if "contem" in canario and canario["contem"].lower() not in alvo.lower():
        return False, f"nao contem {canario['contem']!r}"
    return True, ""


# compatibilidade: tuplas (coletor, nome, url, segredo)
SONDAS = [(f["coletor"], f["nome"], f["url"], f.get("segredo"))
          for f in carregar_fontes()]



def _ctx():
    bundle = os.environ.get("FIO_CA_BUNDLE") or os.environ.get("REQUESTS_CA_BUNDLE")
    if bundle and os.path.exists(bundle):
        return ssl.create_default_context(cafile=bundle)
    return None


def sondar(segredos: dict | None = None, timeout: int = 12,
           fontes: list[dict] | None = None, espera: float = 2.0) -> list[dict]:
    """Uma consulta neutra por fonte, mais a checagem do canario.

    `ok` e verdadeiro so se a fonte respondeu E a resposta tem a forma
    esperada. Fonte que responde 200 com formato novo sai como falha de
    contrato: e o aviso de que o coletor correspondente quebrou.
    """
    segredos = segredos or {}
    out = []
    for f in fontes if fontes is not None else carregar_fontes():
        coletor, nome, url = f["coletor"], f["nome"], f["url"]
        segredo = f.get("segredo")
        cab = {"User-Agent": UA, "Accept": "application/json, text/html"}
        if segredo:
            if not segredos.get(segredo):
                out.append({"coletor": coletor, "fonte": nome, "ok": None,
                            "status": "sem chave",
                            "dica": f"configure '{segredo}' para usar esta fonte"})
                continue
            cab["chave-api-dados"] = segredos[segredo]
        t = time.perf_counter()
        # uma segunda tentativa cobre soltura momentanea (reset de conexao,
        # 5xx, corpo truncado); falha que se repete e falha de verdade
        for tentativa in (1, 2):
            corpo = b""
            try:
                req = urllib.request.Request(url, headers=cab)
                with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
                    corpo = r.read(262144)
                    status, ok = r.status, 200 <= r.status < 400
            except urllib.error.HTTPError as e:
                status, ok = e.code, False
            except Exception as e:
                status, ok = f"{type(e).__name__}", False
            contrato, motivo = (checar_canario(corpo, f.get("canario") or {})
                                if ok else (None, ""))
            transitorio = (isinstance(status, str)
                           or (isinstance(status, int) and status >= 500)
                           or contrato is False)
            if (ok and contrato is not False) or not transitorio or tentativa == 2:
                break
            time.sleep(espera)
        ms = round((time.perf_counter() - t) * 1000)
        dica = ""
        if ok and contrato is False:
            ok, dica = False, f"contrato quebrado: {motivo}"
        elif ok:
            pass
        elif status == 429:
            dica = "limite de requisicoes da fonte; tente mais tarde"
        elif isinstance(status, str):
            dica = ("sem conexao ate a fonte: verifique internet, proxy "
                    "corporativo ou firewall")
        else:
            dica = f"a fonte respondeu HTTP {status}"
        if not ok and f.get("instavel"):
            # fonte comunitaria conhecida por oscilar: aparece, mas nao reprova
            out.append({"coletor": coletor, "fonte": nome, "ok": None,
                        "status": status, "ms": ms, "contrato": contrato,
                        "dica": f"fonte instavel (nao conta como falha): {dica}"})
            continue
        out.append({"coletor": coletor, "fonte": nome, "ok": ok,
                    "status": status, "ms": ms, "dica": dica,
                    "contrato": contrato})
    return out


def imprimir(res: list[dict]) -> int:
    falhas = 0
    for r in res:
        marca = {True: "OK  ", False: "FALHA", None: "--  "}[r["ok"]]
        falhas += r["ok"] is False
        tempo = f"{r.get('ms', 0):>5} ms" if r["ok"] is not None else "        "
        print(f"[{marca}] {r['fonte']:<38} {str(r['status']):<18} {tempo}  {r['dica']}")
    print()
    print("Fontes offline (plano de numeracao, indice da Receita, documentos) "
          "funcionam sempre, com ou sem internet.")
    return 1 if falhas else 0
