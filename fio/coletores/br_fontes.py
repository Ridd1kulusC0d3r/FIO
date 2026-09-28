"""Fontes abertas brasileiras: diarios oficiais, CEP/IBGE e sancoes.

Querido Diario (Open Knowledge Brasil) e a fonte mais subestimada do OSINT
brasileiro para telefone: licitacao, nomeacao, credenciamento, alvara,
edital de citacao -- a administracao publica publica telefone de empresa,
de servidor e de particular o tempo todo, e o QD indexa o texto integral
dos diarios de milhares de municipios.
"""

from __future__ import annotations

import re
import urllib.parse

from .base import Coletor, Contexto, Achado, registrar
from ..grafo.modelo import Entidade, Fonte
from ..core.normalize import normalizar, variantes
from ..core.documentos import (extrair_documentos, cep_uf, cep_formatar,
                               cnpj_limpar, cnpj_valido)


def _so_digitos(s) -> str:
    return re.sub(r"\D", "", str(s or ""))


@registrar
class QueridoDiario(Coletor):
    nome = "querido-diario"
    descricao = ("Busca o identificador no texto integral dos diarios "
                 "oficiais municipais indexados pelo Querido Diario.")
    tipos_alvo = ("telefone", "cnpj", "organizacao", "pessoa", "email")
    requer_rede = True
    admiralty = "A3"
    so_brasil = True
    reserva = ("O diario oficial e fonte autoritativa de que o texto foi "
               "publicado, nao de que o numero pertence a quem aparece ao "
               "lado dele: edital de citacao lista varios particulares no "
               "mesmo paragrafo. A cobertura e parcial -- nem todo municipio "
               "esta indexado, e a extracao de texto de PDF tem ruido.")

    URL = "https://api.queridodiario.ok.org.br/gazettes"

    def _consulta(self, alvo: Entidade) -> str:
        if alvo.tipo == "telefone":
            t = normalizar(alvo.valor)
            formas = [v for v in variantes(t)
                      if "(" in v or "-" in v][:6] or [alvo.valor]
        elif alvo.tipo in ("cnpj", "organizacao") and cnpj_valido(alvo.valor):
            c = cnpj_limpar(alvo.valor)
            formas = [f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}", c]
        else:
            formas = [alvo.rotulo or alvo.valor]
        return " | ".join(f'"{f}"' for f in formas)

    def coletar(self, alvo: Entidade, ctx: Contexto) -> list[Achado]:
        params = {"querystring": self._consulta(alvo), "excerpt_size": 500,
                  "number_of_excerpts": 3, "size": 20}
        terr = ctx.segredos.get("querido_diario_territorios")
        if terr:
            params["territory_ids"] = terr
        url = self.URL + "?" + urllib.parse.urlencode(params, doseq=True)
        status, dados = ctx.http().get_json(url, self.nome)
        if status != 200 or not isinstance(dados, dict):
            return []

        alvo.atributos["querido_diario_total"] = dados.get("total_gazettes")
        achados: list[Achado] = []
        for g in dados.get("gazettes") or []:
            link = g.get("url") or g.get("txt_url") or ""
            rot = (f"DO {g.get('territory_name', '?')}/{g.get('state_code', '?')} "
                   f"{g.get('date', '')}")
            diario = Entidade("diario", link or rot, rotulo=rot, atributos={
                "municipio": g.get("territory_name"),
                "ibge": g.get("territory_id"), "uf": g.get("state_code"),
                "data": g.get("date"), "edicao": g.get("edition"),
                "extra": g.get("is_extra_edition"), "txt_url": g.get("txt_url"),
            })
            trecho = " … ".join(g.get("excerpts") or [])
            fonte = Fonte(self.nome, self.admiralty, url=link,
                          nota=f"trecho: {trecho[:220]}")
            achados.append(Achado(alvo, "publicado_em", diario, fonte,
                                  f"diario oficial de {rot}"))

            # o que mais esta no MESMO trecho: coocorrencia, nao vinculo
            fraca = Fonte(self.nome, "B4", url=link,
                          nota="coocorrencia no mesmo trecho do diario")
            for doc in extrair_documentos(trecho):
                if doc.tipo in ("cnpj", "cpf-parcial", "cep") and doc.valor != alvo.valor:
                    tipo = {"cnpj": "organizacao"}.get(doc.tipo, doc.tipo)
                    achados.append(Achado(
                        diario, "menciona",
                        Entidade(tipo, doc.valor, rotulo=doc.atributos.get("formatado", doc.valor),
                                 atributos=doc.atributos),
                        fraca, "mencionado no mesmo trecho"))
        return achados


@registrar
class ViaCEP(Coletor):
    nome = "viacep"
    descricao = ("CEP -> logradouro, municipio (codigo IBGE) e DDD da "
                 "localidade, via ViaCEP.")
    tipos_alvo = ("cep",)
    requer_rede = True
    admiralty = "B2"
    so_brasil = True
    reserva = ("O DDD devolvido e o da localidade do CEP; ele alimenta a "
               "checagem de coerencia geografica, mas CEP e telefone podem "
               "legitimamente divergir (filial, portabilidade, linha movel).")

    def coletar(self, alvo: Entidade, ctx: Contexto) -> list[Achado]:
        d = _so_digitos(alvo.valor)
        if len(d) != 8:
            return []
        url = f"https://viacep.com.br/ws/{d}/json/"
        status, dados = ctx.http().get_json(url, self.nome)
        if status != 200 or not isinstance(dados, dict) or dados.get("erro"):
            return []
        alvo.atributos.update({
            "logradouro": dados.get("logradouro"), "bairro": dados.get("bairro"),
            "municipio": dados.get("localidade"), "uf": dados.get("uf"),
            "ibge": dados.get("ibge"), "ddd_localidade": dados.get("ddd"),
        })
        alvo.rotulo = f"CEP {cep_formatar(d)} ({dados.get('localidade')}/{dados.get('uf')})"
        if not dados.get("ibge"):
            return []
        mun = Entidade("municipio", str(dados["ibge"]),
                       rotulo=f"{dados.get('localidade')}/{dados.get('uf')}",
                       atributos={"uf": dados.get("uf"), "ddd": dados.get("ddd")})
        return [Achado(alvo, "situado_em", mun,
                       Fonte(self.nome, self.admiralty, url=url, nota="ViaCEP"))]


@registrar
class Transparencia(Coletor):
    nome = "transparencia"
    descricao = ("CNPJ -> sancoes no CEIS (inidoneas/suspensas) e no CNEP "
                 "(punidas pela Lei Anticorrupcao), via Portal da "
                 "Transparencia/CGU.")
    tipos_alvo = ("cnpj", "organizacao")
    requer_rede = True
    requer_segredo = "transparencia_api_key"
    admiralty = "A1"
    so_brasil = True
    reserva = ("Registra sancao aplicada, com orgao e periodo; nao informa "
               "o merito nem se a sancao foi suspensa judicialmente depois. "
               "Confira a vigencia na data do relatorio.")

    BASE = "https://api.portaldatransparencia.gov.br/api-de-dados"

    def coletar(self, alvo: Entidade, ctx: Contexto) -> list[Achado]:
        cnpj = cnpj_limpar(alvo.atributos.get("cnpj") or alvo.valor)
        if not cnpj_valido(cnpj):
            return []
        chave = ctx.segredos["transparencia_api_key"]
        achados: list[Achado] = []
        for cadastro in ("ceis", "cnep"):
            url = f"{self.BASE}/{cadastro}?codigoSancionado={cnpj}&pagina=1"
            status, dados = ctx.http().get_json(
                url, self.nome, cabecalhos={"chave-api-dados": chave})
            if status != 200 or not isinstance(dados, list):
                continue
            for s in dados:
                tipo = (s.get("tipoSancao") or {}).get("descricaoResumida") \
                    or (s.get("tipoSancao") or {}).get("descricaoPortal") or "sancao"
                orgao = (s.get("orgaoSancionador") or {}).get("nome", "")
                sid = s.get("id") or f"{cnpj}-{s.get('dataInicioSancao')}"
                sanc = Entidade("sancao", f"{cadastro}:{sid}",
                                rotulo=f"{cadastro.upper()}: {tipo}",
                                atributos={"cadastro": cadastro.upper(),
                                           "tipo": tipo, "orgao": orgao,
                                           "inicio": s.get("dataInicioSancao"),
                                           "fim": s.get("dataFimSancao"),
                                           "processo": s.get("numeroProcesso")})
                achados.append(Achado(
                    alvo, "sancionada_em", sanc,
                    Fonte(self.nome, self.admiralty, url=url,
                          nota=f"{cadastro.upper()} / {orgao}"),
                    f"{tipo} ({s.get('dataInicioSancao')} a {s.get('dataFimSancao')})"))
        return achados
