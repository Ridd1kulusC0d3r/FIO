"""Pegada publica: onde o identificador ja foi publicado por alguem.

Duas partes. A primeira gera o conjunto de consultas -- e a parte que mais
importa, porque um numero publicado em anuncio, contrato ou pagina
institucional foi escrito de UMA grafia entre muitas, e buscar so a forma
canonica perde a maioria dos casos. A segunda executa as consultas contra
indice publico e recolhe os enderecos, sem se autenticar em nada.

Nada aqui interroga plataforma de mensageria nem consulta perfil por
numero: isso avisa o alvo e, em volume, e tratamento irregular de dado
pessoal.
"""

from __future__ import annotations

import re
import urllib.parse

from .base import Coletor, Contexto, Achado, registrar
from ..grafo.modelo import Entidade, Fonte
from ..core.normalize import normalizar, variantes, extrair_de_texto

SITES = [
    ("institucional", ""),
    ("linkedin", "site:linkedin.com"),
    ("facebook", "site:facebook.com"),
    ("instagram", "site:instagram.com"),
    ("classificados", "(site:olx.com.br OR site:mercadolivre.com.br)"),
    ("empresarial", "(site:econodata.com.br OR site:cnpj.biz OR site:empresascnpj.com)"),
    ("juridico", "(site:jusbrasil.com.br OR site:escavador.com)"),
    ("oficial", "(site:gov.br OR site:jus.br OR site:leg.br)"),
    ("documentos", "(filetype:pdf OR filetype:xlsx OR filetype:docx)"),
    ("codigo", "(site:github.com OR site:pastebin.com OR site:gitlab.com)"),
]

MOTORES = {
    "google": "https://www.google.com/search?q={q}",
    "bing": "https://www.bing.com/search?q={q}",
    "duckduckgo": "https://duckduckgo.com/?q={q}",
    "yandex": "https://yandex.com/search/?text={q}",
}

_LINK = re.compile(r'href="(https?://[^"]+)"')
_RUIDO = ("duckduckgo.com", "google.com", "bing.com", "yandex.",
          "w3.org", "schema.org", "gstatic", "wikipedia.org/wiki/Special")


def montar_dorks(alvo: Entidade) -> list[dict]:
    """Consultas prontas, uma por combinacao de grafia e recorte."""
    if alvo.tipo == "telefone":
        t = normalizar(alvo.valor)
        formas = variantes(t)[:8] or [alvo.valor]
    else:
        formas = [alvo.valor]

    alvo_aspas = " OR ".join(f'"{f}"' for f in formas)
    saida = []
    for rotulo, filtro in SITES:
        q = f"({alvo_aspas}){(' ' + filtro) if filtro else ''}"
        saida.append({
            "recorte": rotulo, "consulta": q,
            "urls": {m: url.format(q=urllib.parse.quote_plus(q))
                     for m, url in MOTORES.items()},
        })
    return saida


@registrar
class PegadaWeb(Coletor):
    nome = "web"
    descricao = ("Gera as consultas em todas as grafias do identificador e "
                 "recolhe as paginas publicas que o mencionam.")
    tipos_alvo = ("telefone", "email", "pessoa", "organizacao", "dominio")
    requer_rede = True
    admiralty = "C3"
    reserva = ("Indice publico e material de terceiros: a pagina pode estar "
               "desatualizada, ser copia de outra ou ter sido plantada. "
               "Trate cada URL como afirmacao a verificar, nunca como fato. "
               "Numero em anuncio de classificado costuma ser de "
               "intermediario, nao do anunciante.")

    def coletar(self, alvo: Entidade, ctx: Contexto) -> list[Achado]:
        dorks = montar_dorks(alvo)
        alvo.atributos["dorks"] = dorks
        ctx.ledger.registrar(
            "analise.dorks", alvo=alvo.valor, coletor=self.nome,
            resumo=f"{len(dorks)} consultas geradas",
            artefato="\n".join(d["consulta"] for d in dorks))

        achados: list[Achado] = []
        vistos: set[str] = set()
        cliente = ctx.http()

        for d in dorks:
            url = ("https://lite.duckduckgo.com/lite/?q="
                   + urllib.parse.quote_plus(d["consulta"]))
            status, corpo = cliente.get(url, self.nome, aceitar_json=False)
            if status != 200 or not corpo:
                continue
            html = corpo.decode("utf-8", "replace")

            for bruto in _LINK.findall(html):
                link = urllib.parse.unquote(bruto)
                m = re.search(r"uddg=([^&]+)", bruto)
                if m:
                    link = urllib.parse.unquote(m.group(1))
                if any(r in link for r in _RUIDO) or link in vistos:
                    continue
                vistos.add(link)
                host = urllib.parse.urlparse(link).netloc
                fonte = Fonte(coletor=self.nome, admiralty=self.admiralty,
                              url=link,
                              nota=f"indice publico, recorte {d['recorte']}")
                pagina = Entidade("url", link, rotulo=host,
                                  atributos={"host": host, "recorte": d["recorte"]})
                achados.append(Achado(alvo, "mencionado_em", pagina, fonte,
                                      f"consulta: {d['consulta'][:120]}"))
                achados.append(Achado(
                    pagina, "hospedado_em",
                    Entidade("dominio", host.lower().lstrip("www.")), fonte))

            # identificadores que aparecem no proprio trecho indexado
            for t in extrair_de_texto(re.sub(r"<[^>]+>", " ", html)):
                if t.chave == alvo.valor:
                    continue
                achados.append(Achado(
                    alvo, "cocorre_com",
                    Entidade("telefone", t.chave, rotulo=t.formatado(),
                             atributos={"ddd": t.ddd, "assinante": t.assinante,
                                        "faixa": t.faixa, "uf": t.uf,
                                        "e164": t.e164}),
                    Fonte(coletor=self.nome, admiralty="D3", url=url,
                          nota="coocorrencia no resultado de busca"),
                    "aparece no mesmo resultado; coocorrencia nao e vinculo"))

            for e in set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+",
                                    re.sub(r"<[^>]+>", " ", html))):
                if e.endswith((".png", ".jpg", ".gif")):
                    continue
                achados.append(Achado(
                    alvo, "cocorre_com", Entidade("email", e.lower()),
                    Fonte(coletor=self.nome, admiralty="D3", url=url,
                          nota="coocorrencia no resultado de busca")))
        return achados
