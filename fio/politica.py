"""Politica do caso: base legal, escopo autorizado e fontes vedadas.

Este modulo e um portao, nao um enfeite. Nenhum coletor roda sem um caso
aberto com base legal declarada, e alvos fora do escopo sao recusados.
A razao e pratica, nao moral: investigacao sem escopo documentado nao
sobrevive a contestacao e contamina o resto do material.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field, asdict

BASES_LEGAIS = {
    "lgpd-7-i": "Art. 7, I LGPD - consentimento do titular",
    "lgpd-7-ii": "Art. 7, II LGPD - cumprimento de obrigacao legal ou regulatoria",
    "lgpd-7-v": "Art. 7, V LGPD - execucao de contrato",
    "lgpd-7-vi": "Art. 7, VI LGPD - exercicio regular de direitos em processo",
    "lgpd-7-ix": "Art. 7, IX LGPD - legitimo interesse do controlador",
    "lgpd-4-iii": "Art. 4, III LGPD - seguranca publica / investigacao penal (regime proprio)",
    "contrato-pentest": "Contrato de teste de intrusao / red team com escopo assinado",
    "resposta-incidente": "Resposta a incidente em ativo proprio ou sob mandato do titular",
    "judicial": "Determinacao judicial ou requisicao de autoridade competente",
    "pesquisa-academica": "Pesquisa academica com aprovacao em comite de etica",
}

# Categorias que o framework recusa por construcao. Nao ha flag para ligar.
FONTES_VEDADAS = {
    "bases-vazadas": (
        "Consulta a bases de dados cadastrais vazadas ou comercializadas "
        "irregularmente (bots de CPF, 'consulta cadastral', dumps de "
        "operadoras). Acesso constitui ilicito e contamina toda a cadeia "
        "probatoria do caso."
    ),
    "credenciais-terceiros": (
        "Uso de credenciais de terceiros, contas falsas em plataformas ou "
        "qualquer acesso que dependa de burlar autenticacao."
    ),
    "interceptacao": (
        "Interceptacao de comunicacao, captura de trafego alheio ou acesso "
        "a conteudo de mensagens (Lei 9.296/96 e art. 10 do Marco Civil)."
    ),
    "engenharia-social": (
        "Contato ativo com o alvo ou terceiros sob pretexto. Fora do escopo "
        "de coleta passiva: deixa rastro no alvo e muda a natureza do ato."
    ),
    "enumeracao-plataforma": (
        "Sondagem de plataformas de mensageria para confirmar existencia de "
        "conta por numero em massa. Viola termos de uso e, em volume, "
        "caracteriza tratamento irregular de dados pessoais."
    ),
}


class ViolacaoDeEscopo(Exception):
    """Alvo, fonte ou acao fora do que o caso autoriza."""


@dataclass
class Caso:
    id: str
    titulo: str
    base_legal: str
    finalidade: str
    responsavel: str
    escopo: list[str] = field(default_factory=list)
    criado_em: str = ""
    expira_em: str = ""
    modo: str = "passivo"
    observacoes: str = ""
    # campos do laudo / relatorio de inteligencia
    solicitante: str = ""
    referencia: str = ""          # processo, oficio, contrato, ticket
    registro_profissional: str = ""
    quesitos: list = field(default_factory=list)   # [{n, texto, resposta, entidades}]
    conclusao: str = ""
    classificacao: str = "ACESSO RESTRITO - contem dados pessoais (LGPD)"

    def __post_init__(self) -> None:
        if self.base_legal not in BASES_LEGAIS:
            raise ViolacaoDeEscopo(
                f"base legal '{self.base_legal}' nao reconhecida. "
                f"Use uma de: {', '.join(sorted(BASES_LEGAIS))}"
            )
        if not self.finalidade or len(self.finalidade) < 10:
            raise ViolacaoDeEscopo(
                "finalidade deve ser descrita de forma especifica: e ela que "
                "delimita o que pode ser coletado (LGPD art. 6, I e III)"
            )
        agora = dt.datetime.now(dt.timezone.utc)
        self.criado_em = self.criado_em or agora.isoformat(timespec="seconds")
        if not self.expira_em:
            self.expira_em = (agora + dt.timedelta(days=90)).isoformat(timespec="seconds")

    @property
    def expirado(self) -> bool:
        return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds") > self.expira_em

    def base_legal_texto(self) -> str:
        return BASES_LEGAIS[self.base_legal]

    def autorizar(self, alvo: str) -> None:
        """Levanta ViolacaoDeEscopo se o alvo nao esta autorizado."""
        if self.expirado:
            raise ViolacaoDeEscopo(
                f"caso {self.id} expirou em {self.expira_em}; renove antes de coletar"
            )
        if not self.escopo:
            raise ViolacaoDeEscopo("escopo vazio: nenhum identificador autorizado")
        alvo_l = alvo.lower()
        for item in self.escopo:
            i = item.lower()
            if i == alvo_l or alvo_l.endswith("." + i) or i in alvo_l:
                return
        raise ViolacaoDeEscopo(
            f"'{alvo}' fora do escopo do caso {self.id}. "
            f"Autorizados: {', '.join(self.escopo)}"
        )

    def dict(self) -> dict:
        d = asdict(self)
        d["base_legal_texto"] = self.base_legal_texto()
        d["expirado"] = self.expirado
        return d

    def json(self) -> str:
        return json.dumps(self.dict(), ensure_ascii=False, indent=2)
