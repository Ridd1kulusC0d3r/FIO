"""Coletor offline: tudo o que o proprio numero informa, sem tocar a rede.

E sempre o primeiro a rodar. Numero invalido, servico especial ou linha
nao-geografica sao descartados aqui, antes de qualquer requisicao -- o que
evita queimar reputacao de IP e tempo com alvo que nunca foi pessoa.
"""

from __future__ import annotations

from .base import Coletor, Contexto, Achado, registrar
from ..core.normalize import normalizar, variantes, extrair_de_texto
from ..grafo.modelo import Entidade, Fonte


@registrar
class NucleoTelefone(Coletor):
    nome = "nucleo"
    estagio = "normalizacao"
    descricao = ("Plano de numeracao: valida, classifica, situa "
                 "geograficamente e identifica o bloco de numeracao.")
    tipos_alvo = ("telefone",)
    requer_rede = False
    admiralty = "A2"       # tabela oficial, interpretacao deterministica
    reserva = ("O DDD indica a area de habilitacao original da linha, nao "
               "onde a pessoa esta. Com portabilidade e numero movel, a "
               "geografia e pista de origem, nunca de localizacao atual.")

    def coletar(self, alvo: Entidade, ctx: Contexto) -> list[Achado]:
        t = normalizar(alvo.valor)
        alvo.atributos.update({
            "e164": t.e164, "ddd": t.ddd, "assinante": t.assinante,
            "tipo_linha": t.tipo, "uf": t.uf, "area": t.area,
            "faixa": t.faixa, "valido": t.valido,
            "justificativa": t.justificativa, "avisos": t.avisos,
            "formatado": t.formatado(),
            "variantes": variantes(t),
        })
        alvo.rotulo = alvo.rotulo or t.formatado()

        fonte = Fonte(coletor=self.nome, admiralty=self.admiralty,
                      nota="plano de numeracao brasileiro (tabela local)")
        achados: list[Achado] = []

        if t.faixa:
            # A tabela e autoritativa (A), mas "mesmo bloco" como indicador
            # de vinculo e duvidoso (4): a aresta nasce fraca de proposito.
            fraca = Fonte(coletor=self.nome, admiralty="A4",
                          nota="bloco de numeracao; indicador fraco de origem comum")
            achados.append(Achado(
                origem=alvo, relacao="pertence_ao_bloco",
                destino=Entidade("faixa", t.faixa,
                                 rotulo=f"bloco {t.faixa}",
                                 atributos={"ddd": t.ddd, "uf": t.uf}),
                fonte=fraca,
                observacao=("Bloco de numeracao destinado em lote; util para "
                            "agrupar linhas de uma mesma contratacao.")))

        ctx.ledger.registrar(
            "analise.numero", alvo=alvo.valor, coletor=self.nome,
            resumo=f"{t.tipo} / {t.uf or '-'} / {t.justificativa}",
            metadados={"valido": t.valido, "avisos": t.avisos})
        return achados


@registrar
class ExtratorDocumento(Coletor):
    nome = "extrator"
    estagio = "ingestao"
    descricao = ("Varre um documento ja em posse do caso e extrai telefones "
                 "e e-mails, ligando-os a origem.")
    tipos_alvo = ("documento",)
    requer_rede = False
    admiralty = "B2"
    reserva = ("A confianca do vinculo nao passa da confianca do documento "
               "de origem: um PDF encaminhado por terceiro e material de "
               "segunda mao ate que a origem seja verificada.")

    def coletar(self, alvo: Entidade, ctx: Contexto) -> list[Achado]:
        import re
        from pathlib import Path

        caminho = Path(alvo.atributos.get("caminho", alvo.valor))
        if not caminho.exists():
            return []
        texto = caminho.read_text(encoding="utf-8", errors="replace")
        fonte = Fonte(coletor=self.nome, admiralty=self.admiralty,
                      url=str(caminho), nota=f"extracao de {caminho.name}")
        achados = []
        for t in extrair_de_texto(texto):
            achados.append(Achado(
                origem=alvo, relacao="menciona",
                destino=Entidade("telefone", t.chave, rotulo=t.formatado(),
                                 atributos={"ddd": t.ddd,
                                            "assinante": t.assinante,
                                            "faixa": t.faixa, "uf": t.uf}),
                fonte=fonte, observacao=f"grafia no documento: {t.original}"))
        for m in set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", texto)):
            achados.append(Achado(
                origem=alvo, relacao="menciona",
                destino=Entidade("email", m.lower()), fonte=fonte))
        from ..core.documentos import extrair_documentos
        mapa = {"cnpj": "organizacao"}
        for doc in extrair_documentos(texto):
            if doc.tipo == "cpf":
                # Minimizacao (LGPD art. 6, III): o CPF completo nao entra no
                # grafo -- nem no rotulo, nem nos atributos. Fica so a mascara
                # no formato publicado pela Receita, que ainda permite casar
                # com o quadro societario e extrair a regiao fiscal.
                valor, tipo = f"***{doc.valor[3:9]}**", "cpf-parcial"
                rotulo = valor
                atributos = {"regiao_fiscal": doc.atributos.get("regiao_fiscal"),
                             "origem": "CPF completo no documento; armazenado mascarado"}
            else:
                valor, tipo = doc.valor, mapa.get(doc.tipo, doc.tipo)
                rotulo = doc.atributos.get("formatado", valor)
                atributos = {**doc.atributos,
                             "cnpj": doc.valor if doc.tipo == "cnpj" else None}
            achados.append(Achado(
                origem=alvo, relacao="menciona",
                destino=Entidade(tipo, valor, rotulo=rotulo, atributos=atributos),
                fonte=fonte,
                observacao="ambiguo: " + doc.atributos.get("ambiguidade", "")
                if doc.ambiguo else f"{doc.tipo} extraido do documento"))
        return achados
