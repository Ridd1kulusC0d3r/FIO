"""Busca em um passo: do identificador ao resultado, sem montar caso a mao.

Antes, uma pesquisa exigia cinco passos (abrir caso, escolher base legal,
incluir alvo, rodar o pipeline, abrir o resultado). Este modulo e o caminho
curto, compartilhado pela CLI (`fio buscar`), pela bancada (`POST /api/busca`)
e pelo Colab:

    reconhecer("(31) 98888-7777")  -> telefone, ja normalizado
    preparar(...)                  -> abre o caso e inclui o alvo
    executar(...)                  -> roda o pipeline com orcamento de tempo
    resumo(caso)                   -> o que achou e o que faltou

A busca NAO afrouxa a politica do caso: base legal, finalidade, escopo e
prazo continuam obrigatorios; so deixam de ser burocracia repetida. A base
legal nao tem valor padrao: quem busca declara.
"""

from __future__ import annotations

import datetime as dt
import re
import secrets
from dataclasses import dataclass, field

from .caso import CasoEmDisco
from .core.documentos import cnpj_limpar, cnpj_valido, cep_valido
from .core.normalize import normalizar
from .grafo.modelo import Entidade
from .politica import Caso

FINALIDADE_PADRAO = ("Verificar, em fontes publicas e dentro do escopo autorizado, "
                     "vinculos cadastrais associados ao identificador informado.")
ORCAMENTO_PADRAO = 45.0          # segundos de coleta na busca rapida


@dataclass
class Alvo:
    tipo: str
    valor: str                   # forma canonica (a chave da entidade)
    rotulo: str = ""
    atributos: dict = field(default_factory=dict)

    def entidade(self) -> Entidade:
        return Entidade(self.tipo, self.valor, rotulo=self.rotulo,
                        atributos=dict(self.atributos))


def reconhecer(texto: str, ddd: str | None = None) -> Alvo:
    """Descobre o tipo do identificador e o normaliza.

    e-mail (tem @), CNPJ (DV valido), CEP (8 digitos, com hifen), dominio
    (letras e ponto) e, por exclusao, telefone. Levanta ValueError com a
    razao quando nao ha como aproveitar o valor.
    """
    v = (texto or "").strip()
    if not v:
        raise ValueError("informe um telefone, CNPJ, e-mail, dominio ou CEP")
    if "@" in v:
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
            raise ValueError(f"e-mail invalido: {v}")
        return Alvo("email", v.lower())
    if cnpj_valido(v):
        c = cnpj_limpar(v)
        return Alvo("cnpj", c, atributos={"cnpj": c})
    if re.fullmatch(r"\d{5}-\d{3}", v) and cep_valido(v):
        return Alvo("cep", re.sub(r"\D", "", v))
    if re.search(r"[a-zA-Z]", v) and "." in v and " " not in v:
        return Alvo("dominio", v.lower().removeprefix("http://").removeprefix("https://")
                    .removeprefix("www.").split("/")[0])
    t = normalizar(v, ddd_padrao=ddd or None)
    if not t.valido:
        raise ValueError(f"telefone invalido: {t.justificativa}")
    return Alvo("telefone", t.chave, t.formatado(),
                {"ddd": t.ddd, "assinante": t.assinante, "faixa": t.faixa,
                 "uf": t.uf, "e164": t.e164})


def novo_id() -> str:
    return dt.datetime.now().strftime("BUSCA-%Y%m%d-%H%M%S-") + secrets.token_hex(2)


def preparar(valor: str, base_legal: str, ator: str, finalidade: str | None = None,
             responsavel: str | None = None, ddd: str | None = None, dias: int = 30,
             caso_id: str | None = None, titulo: str | None = None
             ) -> tuple[CasoEmDisco, Alvo]:
    """Abre o caso e inclui o alvo. Falha cedo, e com mensagem util, se a
    base legal, a finalidade ou o identificador nao servem."""
    alvo = reconhecer(valor, ddd)
    if not base_legal:
        raise ValueError("escolha a base legal: ela define o que pode ser coletado")
    cid = caso_id or novo_id()
    agora = dt.datetime.now(dt.timezone.utc)
    caso = Caso(id=cid, titulo=titulo or f"Busca: {alvo.rotulo or alvo.valor}",
                base_legal=base_legal, finalidade=(finalidade or FINALIDADE_PADRAO).strip(),
                responsavel=(responsavel or ator or "analista").strip(),
                escopo=[alvo.valor],
                expira_em=(agora + dt.timedelta(days=dias)).isoformat(timespec="seconds"))
    cd = CasoEmDisco(cid)
    if cd.existe:
        raise ValueError(f"o caso '{cid}' ja existe")
    cd.criar(caso, ator)
    cd.add_alvo(alvo.entidade(), ator)
    return cd, alvo


def config_pipeline(offline: bool = False, rapido: bool = True,
                    orcamento: float | None = ORCAMENTO_PADRAO,
                    profundidade: int = 1, descricao: str = "busca"):
    from .lab.pipeline import Config
    return Config(profundidade=profundidade, offline=offline, rapido=rapido,
                  orcamento=orcamento if rapido or orcamento else None,
                  expandir_escopo=profundidade > 1, descricao=descricao)


def ha_rede(hosts=("brasilapi.com.br", "duckduckgo.com"), timeout: float = 3.0) -> bool:
    """Teste curto de conectividade (DNS + TCP 443). Evita esperar 20 s por
    fonte quando o ambiente simplesmente nao tem saida para a internet."""
    import socket
    for h in hosts:
        try:
            with socket.create_connection((h, 443), timeout=timeout):
                return True
        except OSError:
            continue
    return False


def executar(cd: CasoEmDisco, ator: str, offline: bool = False, rapido: bool = True,
             orcamento: float | None = ORCAMENTO_PADRAO, profundidade: int = 1,
             log=lambda s: None, verificar_rede: bool = True):
    """Roda o pipeline (coleta + analise) e devolve o experimento.

    Se nao ha rede, cai para offline com aviso registrado na custodia, em vez
    de deixar a busca "rodando" por minutos esperando timeouts."""
    from .lab import pipeline as pl
    if not offline and verificar_rede and not ha_rede():
        offline = True
        log("sem acesso a internet: fontes online puladas")
        cd.ledger(ator).registrar("rede.indisponivel", alvo=cd.caso_id,
                                  resumo="sem saida para a internet; busca feita so com dados locais")
    cfg = config_pipeline(offline, rapido, orcamento, profundidade)
    return pl.executar(cd, ator, cfg, log=log)


# ------------------------------------------------------------------ resumo
def resumo(cd: CasoEmDisco) -> dict:
    """O que a busca achou, o que faltou e o que fazer a seguir."""
    g = cd.grafo()
    regs = cd.ledger().registros()
    alta = [a for a in g.arestas.values() if a.nivel == "alta"]
    alvo = next((e for e in g.entidades.values() if e.alvo_primario), None)

    def rotulos(tipo: str, n: int = 8) -> list[str]:
        itens = [e for e in g.entidades.values() if e.tipo == tipo]
        return [(e.rotulo or e.valor) for e in itens[:n]]

    pulados = [r for r in regs if r.acao == "coletor.pulado"]
    sem_indice = any("indice local de CNPJ nao configurado" in r.resumo for r in pulados)
    sem_rede = any(r.acao == "rede.indisponivel" for r in regs)
    esgotou = any(r.acao == "orcamento.esgotado" for r in regs)
    falhas = sum(1 for r in regs if r.acao in ("coleta.falha", "coletor.erro"))
    descartes = sum(1 for r in regs if r.acao == "coleta.baseline" and r.resumo.startswith("DESCARTADA"))

    avisos, proximo = [], []
    if sem_indice:
        avisos.append("Sem o indice da Receita: o telefone so foi analisado em si (DDD, regiao, "
                      "tipo de linha); nao foi ligado a empresas nem socios.")
        proximo.append("Monte o indice (rapido, segundos): fio indice baixar --uf <UF> --pronto")
    if sem_rede:
        avisos.append("Sem acesso a internet a partir deste ambiente: as fontes online foram puladas.")
    if esgotou:
        avisos.append("O orcamento de tempo acabou antes de consultar tudo; rode de novo sem --rapido para a busca completa.")
    if falhas:
        avisos.append(f"{falhas} consulta(s) falharam (rede ou fonte fora do ar); veja a custodia.")
    if descartes:
        avisos.append(f"{descartes} resposta(s) de busca foram descartadas por serem pagina padrao.")
    if len(g.entidades) <= 1 and not avisos:
        avisos.append("Nada foi encontrado nas fontes consultadas. Ausencia de registro nao prova que nao existe.")
    return {
        "caso": cd.caso_id,
        "alvo": ({"tipo": alvo.tipo, "valor": alvo.valor, "rotulo": alvo.rotulo or alvo.valor,
                  "atributos": {k: alvo.atributos[k] for k in ("ddd", "uf", "area", "tipo_linha", "e164")
                                if k in alvo.atributos}} if alvo else None),
        "entidades": len(g.entidades), "vinculos": len(g.arestas),
        "vinculos_alta": len(alta), "observacoes": len(g.observacoes),
        "organizacoes": rotulos("organizacao"), "pessoas": rotulos("pessoa"),
        "avisos": avisos, "proximo": proximo,
        "sem_indice": sem_indice, "sem_rede": sem_rede,
    }
