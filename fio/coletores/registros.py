"""Registros publicos oficiais: cadastro de CNPJ e RDAP de dominios.

Sao as duas fontes autoritativas realmente abertas no Brasil para ligar um
numero a uma entidade nomeada. Tudo aqui e dado publico por determinacao
legal -- cadastro de pessoa juridica e registro de dominio.
"""

from __future__ import annotations

import re

from .base import Coletor, Contexto, Achado, registrar
from ..grafo.modelo import Entidade, Fonte
from ..core.normalize import normalizar
from ..indice import IndiceCNPJ


def _so_digitos(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _entidade_pessoa(nome: str, mascara: str | None, **atrib) -> Entidade:
    """Chave de pessoa = nome + mascara do CPF, quando houver.

    Nome sozinho funde homonimos: dois 'JOSE DA SILVA' socios de empresas
    diferentes virariam uma pessoa so, e o grafo inventaria um grupo. A
    Receita publica o CPF mascarado de cada socio; nome + mascara separa
    homonimos e ainda junta a mesma pessoa em empresas diferentes.
    """
    nome = (nome or "").strip().upper()
    m = (mascara or "").strip()
    valido = bool(re.fullmatch(r"\*{3}\d{6}\*{2}", m))
    return Entidade("pessoa", f"{nome} [{m}]" if valido else nome, rotulo=nome,
                    atributos={**atrib, "doc_parcial": m if valido else None})


SITUACAO = {"01": "nula", "02": "ativa", "03": "suspensa", "04": "inapta", "08": "baixada"}


def credibilidade_telefone(n_raizes: int, situacao: str | None) -> tuple[str, str]:
    """Grau Admiralty do vinculo telefone<->cadastro, com a nota explicativa.

    Mesma fonte (Receita, letra A), credibilidade variavel:
    - raridade: telefone declarado por 1 empresa e forte; por 4 ou mais
      raizes distintas, e tipico de contador, despachante ou central;
    - situacao: cadastro baixado, inapto ou suspenso envelhece -- a linha
      pode ter sido devolvida e reatribuida (numero reciclado).
    """
    nivel = 2 if n_raizes <= 1 else 3 if n_raizes <= 3 else 4 if n_raizes <= 9 else 5
    notas = [f"declarado por {n_raizes} raiz(es) de CNPJ"]
    sit = SITUACAO.get((situacao or "").strip().zfill(2)) if situacao else None
    if sit and sit != "ativa":
        nivel = min(5, nivel + 1)
        notas.append(f"cadastro {sit}: telefone pode estar desatualizado")
    return f"A{nivel}", "; ".join(notas)


def _entidade_cep(cep: str) -> Entidade:
    from ..core.documentos import cep_uf, cep_formatar
    d = _so_digitos(cep)
    return Entidade("cep", d, rotulo=f"CEP {cep_formatar(d)}",
                    atributos={"uf": cep_uf(d)})


@registrar
class ReversoCNPJ(Coletor):
    nome = "cnpj-reverso"
    descricao = ("Telefone -> cadastro de CNPJ usando indice local dos Dados "
                 "Abertos da Receita Federal; expande para socios e demais "
                 "estabelecimentos da mesma empresa.")
    tipos_alvo = ("telefone", "email")
    requer_rede = False
    admiralty = "A2"
    reserva = ("Alcanca apenas linhas declaradas por pessoa juridica a "
               "Receita. Telefone pessoal de pessoa fisica nao consta -- e "
               "nao deveria. O dado e autodeclarado pela empresa e pode "
               "estar desatualizado: confira a data da base.")

    def coletar(self, alvo: Entidade, ctx: Contexto) -> list[Achado]:
        caminho = ctx.segredos.get("indice_cnpj")
        if not caminho:
            ctx.ledger.registrar(
                "coletor.pulado", alvo=alvo.valor, coletor=self.nome,
                resumo="indice local de CNPJ nao configurado "
                       "(fio indice construir)")
            return []
        idx = IndiceCNPJ(caminho)
        if not idx.ok:
            return []

        if alvo.tipo == "telefone":
            regs = idx.por_telefone(alvo.atributos.get("e164") or alvo.valor)
        else:
            regs = idx.por_email(alvo.valor)

        base_url = ("https://arquivos.receitafederal.gov.br/dados/cnpj/"
                    "dados_abertos_cnpj/")
        achados: list[Achado] = []
        n_raizes = len({r["cnpj_basico"] for r in regs})
        if alvo.tipo == "telefone":
            alvo.atributos["raizes_que_declaram"] = n_raizes
        for r in regs[:50]:
            grau, nota = credibilidade_telefone(n_raizes, r.get("situacao"))
            fonte_tel = Fonte(coletor=self.nome, admiralty=grau, url=base_url,
                              nota=f"indice local, CNPJ {r['cnpj']}; {nota}")
            fonte = Fonte(coletor=self.nome, admiralty=self.admiralty,
                          url=base_url,
                          nota=f"indice local, CNPJ {r['cnpj']}")
            emp = idx.empresa(r["cnpj_basico"]) or {}
            razao = emp.get("razao_social") or r.get("nome_fantasia") or r["cnpj"]

            org = Entidade("organizacao", r["cnpj"], rotulo=razao, atributos={
                "cnpj": r["cnpj"], "cnpj_basico": r["cnpj_basico"],
                "razao_social": razao, "nome_fantasia": r.get("nome_fantasia"),
                "situacao_cadastral": r.get("situacao"),
                "uf": r.get("uf"), "municipio": r.get("municipio"),
                "logradouro": r.get("logradouro"), "cep": r.get("cep"),
                "matriz": bool(r.get("matriz")), "cnae": r.get("cnae"),
                "inicio_atividade": r.get("inicio"),
            })
            achados.append(Achado(alvo, "telefone_declarado_por", org,
                                  fonte_tel if alvo.tipo == "telefone" else fonte,
                                  "telefone consta no cadastro do estabelecimento"))
            if r.get("cep"):
                achados.append(Achado(org, "endereco_no_cep",
                                      _entidade_cep(r["cep"]), fonte,
                                      r.get("logradouro") or ""))

            if r.get("email"):
                achados.append(Achado(
                    org, "email_declarado", Entidade("email", r["email"]),
                    fonte, "e-mail do cadastro"))

            for outro in ("e164_1", "e164_2"):
                v = r.get(outro)
                if v and v != alvo.atributos.get("e164"):
                    t = normalizar(v)
                    g2, n2 = credibilidade_telefone(idx.contar_telefone(v), r.get("situacao"))
                    achados.append(Achado(
                        org, "telefone_declarado",
                        Entidade("telefone", t.chave, rotulo=t.formatado(),
                                 atributos={"ddd": t.ddd, "assinante": t.assinante,
                                            "faixa": t.faixa, "uf": t.uf,
                                            "e164": t.e164}),
                        Fonte(coletor=self.nome, admiralty=g2, url=base_url,
                              nota=f"indice local, CNPJ {r['cnpj']}; {n2}"),
                        "segunda linha do mesmo cadastro"))

            for s in idx.socios(r["cnpj_basico"]):
                pessoa = _entidade_pessoa(s["nome"], s.get("doc"),
                                          qualificacao=s.get("qualificacao"),
                                          entrada=s.get("entrada"))
                achados.append(Achado(
                    org, "tem_socio", pessoa, fonte,
                    f"quadro societario ({s.get('qualificacao')})"))
                if s.get("doc"):
                    achados.append(Achado(
                        pessoa, "documento_parcial",
                        Entidade("cpf-parcial", s["doc"]), fonte,
                        "CPF mascarado conforme publicado pela Receita"))

            for irmao in idx.irmaos(r["cnpj_basico"])[:25]:
                if irmao["cnpj"] == r["cnpj"]:
                    continue
                achados.append(Achado(
                    org, "mesmo_grupo_cadastral",
                    Entidade("organizacao", irmao["cnpj"],
                             rotulo=irmao.get("nome_fantasia") or razao,
                             atributos={"uf": irmao.get("uf"),
                                        "municipio": irmao.get("municipio"),
                                        "cnpj_basico": irmao["cnpj_basico"]}),
                    fonte, "mesma raiz de CNPJ (filial/matriz)"))
        return achados


@registrar
class ConsultaCNPJ(Coletor):
    nome = "cnpj-api"
    descricao = ("CNPJ -> razao social, telefones, e-mail e quadro societario "
                 "via BrasilAPI (espelho da Receita Federal).")
    tipos_alvo = ("cnpj", "organizacao")
    requer_rede = True
    admiralty = "B2"      # espelho, nao a fonte primaria
    reserva = ("BrasilAPI e um espelho de conveniencia. Para uso em peca "
               "formal, confirme na consulta oficial da Receita e guarde o "
               "comprovante.")

    def coletar(self, alvo: Entidade, ctx: Contexto) -> list[Achado]:
        cnpj = _so_digitos(alvo.atributos.get("cnpj") or alvo.valor)
        if len(cnpj) != 14:
            return []
        url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
        status, dados = ctx.http().get_json(url, self.nome)
        if status != 200 or not isinstance(dados, dict):
            return []

        fonte = Fonte(coletor=self.nome, admiralty=self.admiralty, url=url,
                      nota="BrasilAPI /cnpj/v1")
        org = Entidade("organizacao", cnpj,
                       rotulo=dados.get("razao_social") or cnpj,
                       atributos={k: dados.get(k) for k in (
                           "razao_social", "nome_fantasia", "uf", "municipio",
                           "bairro", "logradouro", "numero", "cep",
                           "descricao_situacao_cadastral", "data_inicio_atividade",
                           "cnae_fiscal_descricao", "capital_social")})
        achados = [Achado(alvo, "mesma_entidade", org, fonte)] if alvo.id != org.id else []
        if dados.get("cep"):
            achados.append(Achado(org, "endereco_no_cep",
                                  _entidade_cep(str(dados["cep"])), fonte))

        for campo_ddd, campo_tel in (("ddd_telefone_1", None), ("ddd_telefone_2", None)):
            bruto = dados.get(campo_ddd)
            if not bruto:
                continue
            t = normalizar(bruto)
            if not t.valido:
                continue
            achados.append(Achado(
                org, "telefone_declarado",
                Entidade("telefone", t.chave, rotulo=t.formatado(),
                         atributos={"ddd": t.ddd, "assinante": t.assinante,
                                    "faixa": t.faixa, "uf": t.uf, "e164": t.e164}),
                fonte, "telefone do cadastro na Receita"))

        if dados.get("email"):
            achados.append(Achado(org, "email_declarado",
                                  Entidade("email", dados["email"].lower()), fonte))

        for s in dados.get("qsa") or []:
            pessoa = _entidade_pessoa(s.get("nome_socio"), s.get("cnpj_cpf_do_socio"),
                                      qualificacao=s.get("qualificacao_socio"),
                                      entrada=s.get("data_entrada_sociedade"))
            achados.append(Achado(org, "tem_socio", pessoa, fonte,
                                  s.get("qualificacao_socio") or ""))
        return achados


@registrar
class RDAP(Coletor):
    nome = "rdap"
    descricao = ("Dominio -> titular, contatos e telefones via RDAP "
                 "(registro.br para .br, rdap.org para gTLD).")
    tipos_alvo = ("dominio",)
    requer_rede = True
    admiralty = "A2"
    reserva = ("Desde a LGPD e o GDPR, a maioria dos registros retorna "
               "contatos redigidos. Quando o telefone aparece, costuma ser "
               "de pessoa juridica ou do provedor -- confira o handle antes "
               "de atribuir a uma pessoa.")

    def coletar(self, alvo: Entidade, ctx: Contexto) -> list[Achado]:
        dominio = alvo.valor.lower().strip().rstrip(".")
        url = (f"https://rdap.registro.br/domain/{dominio}" if dominio.endswith(".br")
               else f"https://rdap.org/domain/{dominio}")
        status, dados = ctx.http().get_json(url, self.nome)
        if status != 200 or not isinstance(dados, dict):
            return []

        fonte = Fonte(coletor=self.nome, admiralty=self.admiralty, url=url,
                      nota="RDAP")
        achados: list[Achado] = []
        alvo.atributos.setdefault("status_rdap", dados.get("status"))
        for ev in dados.get("events") or []:
            alvo.atributos[f"rdap_{ev.get('eventAction','evento')}"] = ev.get("eventDate")

        for ent in dados.get("entities") or []:
            papeis = ",".join(ent.get("roles") or []) or "contato"
            nome = handle = ent.get("handle") or ""
            emails, telefones = [], []
            vcard = (ent.get("vcardArray") or [None, []])[1]
            for campo in vcard:
                if not isinstance(campo, list) or len(campo) < 4:
                    continue
                chave, valor = campo[0], campo[3]
                if chave == "fn" and isinstance(valor, str):
                    nome = valor
                elif chave == "email" and isinstance(valor, str):
                    emails.append(valor.lower())
                elif chave == "tel" and isinstance(valor, str):
                    telefones.append(valor)

            if nome:
                tipo = "organizacao" if papeis in ("registrant", "registrar") else "pessoa"
                ent_e = Entidade(tipo, nome.strip(), rotulo=nome.strip(),
                                 atributos={"handle": handle, "papel_rdap": papeis})
                achados.append(Achado(alvo, f"rdap_{papeis}", ent_e, fonte,
                                      f"handle {handle}"))
            else:
                ent_e = alvo

            for e in emails:
                achados.append(Achado(ent_e, "email_registrado",
                                      Entidade("email", e), fonte, papeis))
            for tel in telefones:
                t = normalizar(tel.replace("tel:", ""))
                if t.valido:
                    achados.append(Achado(
                        ent_e, "telefone_registrado",
                        Entidade("telefone", t.chave, rotulo=t.formatado(),
                                 atributos={"ddd": t.ddd, "assinante": t.assinante,
                                            "faixa": t.faixa, "uf": t.uf,
                                            "e164": t.e164}),
                        fonte, f"contato {papeis} no RDAP"))
        return achados
