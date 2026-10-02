"""Fontes passivas de infraestrutura: Transparencia de Certificados e Wayback.

Nenhuma consulta toca o alvo. O crt.sh agrega os logs publicos de
Certificate Transparency (RFC 6962): todo certificado publico emitido para
um dominio deixa rastro ali, inclusive nomes que nunca foram linkados em
pagina nenhuma. O Wayback Machine responde "quando este endereco apareceu
pela primeira vez na web?", dado que desmonta historia de fachada recente.
"""

from __future__ import annotations

import re
import urllib.parse

from .base import Coletor, Contexto, Achado, registrar
from ..grafo.modelo import Entidade, Fonte

_HOST = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
LIMITE_NOMES = 80


def nomes_do_certificado(registros: list[dict], dominio: str) -> dict[str, dict]:
    """Extrai nomes distintos (sem curinga) dos registros do crt.sh.

    Devolve {nome: {"emissor":..., "inicio":..., "certificados": n}}.
    Ignora nomes que nao terminam no dominio consultado.
    """
    dominio = dominio.lower().strip(".")
    saida: dict[str, dict] = {}
    for r in registros:
        if not isinstance(r, dict):
            continue
        for nome in str(r.get("name_value", "")).splitlines():
            nome = nome.strip().lower().lstrip("*.").rstrip(".")
            if not nome or "@" in nome or not _HOST.match(nome):
                continue
            if nome != dominio and not nome.endswith("." + dominio):
                continue
            d = saida.setdefault(nome, {"emissor": r.get("issuer_name", ""),
                                        "inicio": r.get("not_before", ""),
                                        "certificados": 0})
            d["certificados"] += 1
            ini = r.get("not_before", "")
            if ini and (not d["inicio"] or ini < d["inicio"]):
                d["inicio"] = ini
    return saida


@registrar
class TransparenciaCertificados(Coletor):
    nome = "crtsh"
    descricao = ("Subdominios e nomes irmaos de um dominio, a partir dos logs "
                 "publicos de Certificate Transparency (crt.sh).")
    tipos_alvo = ("dominio",)
    requer_rede = True
    admiralty = "B3"
    reserva = ("Certificado emitido prova que alguem controlava o nome na "
               "emissao, nao que ainda controla nem quem e. Certificados "
               "compartilhados (CDN, hospedagem) listam dominios de terceiros "
               "sem relacao entre si: confira o emissor e as datas antes de "
               "tratar dois nomes como do mesmo operador.")

    URL = "https://crt.sh/?q={q}&output=json"

    def coletar(self, alvo: Entidade, ctx: Contexto) -> list[Achado]:
        dominio = alvo.valor.lower().strip(".")
        url = self.URL.format(q=urllib.parse.quote(f"%.{dominio}"))
        status, dados = ctx.http().get_json(url, self.nome)
        if status != 200 or not isinstance(dados, list):
            return []
        nomes = nomes_do_certificado(dados, dominio)
        alvo.atributos["crtsh_nomes"] = len(nomes)
        achados: list[Achado] = []
        for nome, info in sorted(nomes.items())[:LIMITE_NOMES]:
            if nome == dominio:
                alvo.atributos["crtsh_primeiro_certificado"] = info["inicio"]
                continue
            fonte = Fonte(self.nome, self.admiralty, url=url,
                          nota=f"{info['certificados']} certificado(s); "
                               f"primeiro em {info['inicio'][:10]}")
            achados.append(Achado(
                alvo, "nome_em_certificado",
                Entidade("dominio", nome,
                         atributos={"crtsh_primeiro": info["inicio"]}),
                fonte, "mesmo certificado/log publico"))
        return achados


@registrar
class Wayback(Coletor):
    nome = "wayback"
    descricao = ("Primeiro registro de um dominio ou URL no Internet "
                 "Archive: idade real da presenca publica.")
    tipos_alvo = ("dominio", "url")
    requer_rede = True
    admiralty = "B2"
    reserva = ("O Wayback so conhece o que foi arquivado: ausencia de captura "
               "nao prova que o endereco e novo, e a primeira captura pode ser "
               "bem posterior ao primeiro uso.")

    URL = "https://archive.org/wayback/available?url={u}&timestamp=19960101"

    def coletar(self, alvo: Entidade, ctx: Contexto) -> list[Achado]:
        status, dados = ctx.http().get_json(
            self.URL.format(u=urllib.parse.quote(alvo.valor, safe="")), self.nome)
        if status != 200 or not isinstance(dados, dict):
            return []
        snap = (dados.get("archived_snapshots") or {}).get("closest") or {}
        if not snap.get("available"):
            alvo.atributos["wayback_primeiro"] = None
            return []
        ts = str(snap.get("timestamp", ""))
        alvo.atributos["wayback_primeiro"] = ts
        link = snap.get("url", "")
        return [Achado(
            alvo, "arquivado_em",
            Entidade("url", link, rotulo=f"Wayback {ts[:8]}",
                     atributos={"captura": ts, "host": "web.archive.org"}),
            Fonte(self.nome, self.admiralty, url=link,
                  nota=f"captura mais antiga conhecida: {ts[:4]}-{ts[4:6]}-{ts[6:8]}"),
            "primeira captura mais proxima de 1996")]
