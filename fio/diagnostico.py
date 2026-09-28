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
import ssl
import time
import urllib.error
import urllib.request

from .coletores.base import UA

SONDAS = [
    ("cnpj-api", "BrasilAPI (cadastro de CNPJ)",
     "https://brasilapi.com.br/api/cnpj/v1/00000000000191", None),
    ("viacep", "ViaCEP (CEP)", "https://viacep.com.br/ws/01001000/json/", None),
    ("querido-diario", "Querido Diario (diarios oficiais)",
     "https://api.queridodiario.ok.org.br/gazettes?querystring=licitacao&size=1", None),
    ("rdap", "RDAP registro.br (dominios .br)", "https://rdap.registro.br/domain/nic.br", None),
    ("rdap", "RDAP generico (outros dominios)", "https://rdap.org/domain/example.com", None),
    ("web", "DuckDuckGo (busca publica)", "https://lite.duckduckgo.com/lite/?q=teste", None),
    ("ibge", "IBGE (municipios)",
     "https://servicodados.ibge.gov.br/api/v1/localidades/municipios/3106200", None),
    ("hibp", "Have I Been Pwned (lista publica)",
     "https://haveibeenpwned.com/api/v3/breaches?domain=adobe.com", None),
    ("transparencia", "Portal da Transparencia (CEIS)",
     "https://api.portaldatransparencia.gov.br/api-de-dados/ceis?pagina=1",
     "transparencia_api_key"),
]


def _ctx():
    bundle = os.environ.get("FIO_CA_BUNDLE") or os.environ.get("REQUESTS_CA_BUNDLE")
    if bundle and os.path.exists(bundle):
        return ssl.create_default_context(cafile=bundle)
    return None


def sondar(segredos: dict | None = None, timeout: int = 12) -> list[dict]:
    segredos = segredos or {}
    out = []
    for coletor, nome, url, segredo in SONDAS:
        cab = {"User-Agent": UA, "Accept": "application/json, text/html"}
        if segredo:
            if not segredos.get(segredo):
                out.append({"coletor": coletor, "fonte": nome, "ok": None,
                            "status": "sem chave",
                            "dica": f"configure '{segredo}' para usar esta fonte"})
                continue
            cab["chave-api-dados"] = segredos[segredo]
        t = time.perf_counter()
        try:
            req = urllib.request.Request(url, headers=cab)
            with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
                r.read(2048)
                status, ok = r.status, 200 <= r.status < 400
        except urllib.error.HTTPError as e:
            status, ok = e.code, e.code in (401, 403, 404, 429) and False
        except Exception as e:
            status, ok = f"{type(e).__name__}", False
        ms = round((time.perf_counter() - t) * 1000)
        dica = ""
        if not ok:
            if status == 429:
                dica = "limite de requisicoes da fonte; tente mais tarde"
            elif isinstance(status, str):
                dica = ("sem conexao ate a fonte: verifique internet, proxy "
                        "corporativo ou firewall")
            else:
                dica = f"a fonte respondeu HTTP {status}"
        out.append({"coletor": coletor, "fonte": nome, "ok": ok,
                    "status": status, "ms": ms, "dica": dica})
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
