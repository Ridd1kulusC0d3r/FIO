"""Analisadores embutidos."""

from __future__ import annotations

from collections import Counter

from .base import Analisador, registrar_analisador
from ..grafo.modelo import Grafo
from ..core.documentos import cep_uf, cpf_regiao


def _uf_de(e) -> str | None:
    a = e.atributos
    if a.get("uf"):
        return str(a["uf"]).upper()
    if e.tipo == "cep":
        return cep_uf(e.valor)
    return None


@registrar_analisador
class CoerenciaGeografica(Analisador):
    nome = "coerencia-geografica"
    descricao = ("Compara a UF do DDD de cada telefone com a UF das "
                 "entidades a que ele se liga (cadastro, CEP) e com a regiao "
                 "fiscal do CPF mascarado dos socios.")

    def analisar(self, g: Grafo) -> int:
        antes = len(g.observacoes)
        for tel in g.por_tipo("telefone"):
            uf_tel = tel.atributos.get("uf")
            if not uf_tel:
                continue
            for aresta, outro_id in g.vizinhos(tel.id):
                outro = g.entidades[outro_id]
                if outro.tipo not in ("organizacao", "cep", "municipio"):
                    continue
                uf_outro = _uf_de(outro)
                if uf_outro and uf_outro != uf_tel:
                    g.observar(
                        "incoerencia-geografica",
                        f"Telefone {tel.rotulo or tel.valor} tem DDD de {uf_tel}, "
                        f"mas esta ligado a {outro.tipo} '{outro.rotulo or outro.valor}' "
                        f"em {uf_outro}. Explicacoes comuns: filial, linha movel "
                        f"habilitada em outra UF, portabilidade ou cadastro "
                        f"desatualizado. Tambem e padrao frequente em fraude "
                        f"com linha de terceiro.",
                        [tel.id, outro.id], "atencao", self.nome)

        # socio: regiao fiscal do CPF mascarado vs UFs das empresas
        for p in g.por_tipo("pessoa"):
            regioes = set()
            ufs_empresas = set()
            for _, vid in g.vizinhos(p.id):
                v = g.entidades[vid]
                if v.tipo == "cpf-parcial":
                    regioes.update(cpf_regiao(v.valor) or ())
                elif v.tipo == "organizacao" and _uf_de(v):
                    ufs_empresas.add(_uf_de(v))
            if regioes and ufs_empresas and not (regioes & ufs_empresas):
                g.observar(
                    "regiao-fiscal-divergente",
                    f"{p.valor}: CPF emitido na regiao fiscal "
                    f"{'/'.join(sorted(regioes))}, empresas em "
                    f"{'/'.join(sorted(ufs_empresas))}. Nao e anomalia por si "
                    f"(mudanca de domicilio e comum); e informacao de "
                    f"trajetoria para confronto com outras fontes.",
                    [p.id], "info", self.nome)
        return len(g.observacoes) - antes


@registrar_analisador
class Intermediarios(Analisador):
    nome = "intermediarios"
    descricao = ("Sinaliza entidades-ponte com grau anomalo: um mesmo "
                 "telefone, CEP ou e-mail em muitas empresas sem socio em "
                 "comum costuma ser contabilidade, coworking ou despachante.")
    limiar = 4

    def analisar(self, g: Grafo) -> int:
        antes = len(g.observacoes)
        for e in g.entidades.values():
            if e.tipo not in ("telefone", "cep", "email", "organizacao", "dominio"):
                continue
            # as duas direcoes da mesma relacao contam uma vez so
            orgs = sorted({vid for _, vid in g.vizinhos(e.id)
                           if g.entidades[vid].tipo == "organizacao"})
            if len(orgs) < self.limiar:
                continue
            # as empresas compartilham socio? se nao, e intermediario
            socios_por_org = []
            for o in orgs:
                socios_por_org.append({vid for _, vid in g.vizinhos(o)
                                       if g.entidades[vid].tipo == "pessoa"})
            contagem = Counter(s for grupo in socios_por_org for s in grupo)
            comum = [s for s, n in contagem.items() if n >= 2]
            if not comum:
                e.atributos["intermediario_provavel"] = True
                g.observar(
                    "intermediario-provavel",
                    f"{e.tipo} '{e.rotulo or e.valor}' aparece em {len(orgs)} "
                    f"empresas sem nenhum socio em comum. Perfil tipico de "
                    f"escritorio contabil, coworking ou despachante: tratar "
                    f"como ponte fraca e NAO como vinculo de grupo.",
                    [e.id] + orgs[:10], "atencao", self.nome)
        return len(g.observacoes) - antes


@registrar_analisador
class AlertaSancao(Analisador):
    nome = "alerta-sancao"
    descricao = "Propaga sancoes (CEIS/CNEP) ao componente conexo."

    def analisar(self, g: Grafo) -> int:
        antes = len(g.observacoes)
        for comp in g.componentes():
            sancoes = [i for i in comp if g.entidades[i].tipo == "sancao"]
            alvos = [i for i in comp if g.entidades[i].alvo_primario]
            if sancoes and alvos:
                g.observar(
                    "sancao-no-componente",
                    f"{len(sancoes)} sancao(oes) no mesmo componente de "
                    f"{len(alvos)} alvo(s) primario(s). Proximidade no grafo "
                    f"nao transfere responsabilidade: verifique o caminho.",
                    sancoes + alvos, "alta", self.nome)
        return len(g.observacoes) - antes
