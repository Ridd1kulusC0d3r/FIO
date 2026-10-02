"""Coletor offline sobre todos os indices construidos por receita."""

from __future__ import annotations

from .base import Coletor, Contexto, Achado, registrar
from ..grafo.modelo import Entidade, Fonte
from ..core.normalize import normalizar
from ..core.documentos import cnpj_limpar, cnpj_valido
from ..receitas import Indice, indices_disponiveis
from ..caso import raiz


@registrar
class DadosAbertos(Coletor):
    nome = "dados-abertos"
    descricao = ("Consulta offline todos os indices de dados abertos "
                 "construidos por receita (CNES, Cadastur, TSE, faixas...).")
    tipos_alvo = ("telefone", "email", "cnpj", "organizacao")
    requer_rede = False
    admiralty = "B2"   # cada indice declara o proprio grau
    so_brasil = True
    reserva = ("Cada indice herda a reserva da sua receita (ver tabela de "
               "fontes do relatorio). Registro autodeclarado envelhece: "
               "confira a data de construcao do indice.")

    def coletar(self, alvo: Entidade, ctx: Contexto) -> list[Achado]:
        if alvo.tipo == "telefone":
            t = normalizar(alvo.atributos.get("e164") or alvo.valor)
            tipo, valor = "telefone", t.e164 or alvo.valor
        elif alvo.tipo == "email":
            tipo, valor, t = "email", alvo.valor.lower(), None
        else:
            c = cnpj_limpar(alvo.atributos.get("cnpj") or alvo.valor)
            if not cnpj_valido(c):
                return []
            tipo, valor, t = "cnpj", c, None

        achados: list[Achado] = []
        for caminho in indices_disponiveis(raiz()):
            try:
                idx = Indice(caminho)
            except Exception:
                continue
            m = idx.meta
            fonte_base = dict(coletor=self.nome, admiralty=m.get("admiralty", "C3"),
                              url=m.get("fonte", ""))

            if m.get("tipo") == "faixa":
                if t and t.ddd and t.assinante:
                    for f in idx.faixa(t.ddd, t.assinante):
                        prest = Entidade("prestadora", f["prestadora"].upper(),
                                         rotulo=f["prestadora"])
                        achados.append(Achado(
                            alvo, m.get("relacao", "faixa_destinada_a"), prest,
                            Fonte(**fonte_base, nota=f"faixa {f['inicio']}-{f['fim']} "
                                                     f"({m.get('arquivo')})"),
                            "destinacao original; portabilidade nao considerada"))
                idx.fechar()
                continue

            for r in idx.buscar(tipo, valor):
                ent = Entidade(m.get("entidade", "organizacao"),
                               f"{caminho.stem}:{r['chave'] or r['id']}",
                               rotulo=r["rotulo"] or r["chave"],
                               atributos={"indice": caminho.stem, **{
                                   k: v for k, v in r["dados"].items()
                                   if not k.startswith("rel:")}})
                fonte = Fonte(**fonte_base,
                              nota=f"{m.get('titulo')} / registro {r['chave']}")
                achados.append(Achado(alvo, m.get("relacao", "consta_em_registro"),
                                      ent, fonte, m.get("titulo", "")))
                for k, v in r["dados"].items():
                    if k.startswith("rel:") and v:
                        _, tipo_rel, relacao = k.split(":", 2)
                        achados.append(Achado(
                            Entidade(tipo_rel, v.upper().strip()), relacao, ent,
                            fonte, m.get("titulo", "")))
            idx.fechar()
        return achados
