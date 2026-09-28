"""Confianca de vinculo na escala Admiralty (OTAN STANAG 2511).

A escala e a mesma que a analise de inteligencia usa ha decadas: uma letra
para a confiabilidade da fonte, um numero para a credibilidade da
informacao. O framework converte o par em um score numerico so para poder
ordenar e combinar -- o par original continua gravado em cada aresta,
porque e ele que vai para o relatorio.

Combinar fontes independentes usa OU-ruidoso: duas fontes medianas que
apontam o mesmo vinculo valem mais que cada uma isolada, mas nunca chegam
a certeza. E a formalizacao de "corroboracao".
"""

from __future__ import annotations

ADMIRALTY_FONTE: dict[str, tuple[float, str]] = {
    "A": (0.95, "Totalmente confiavel - registro oficial ou autoritativo"),
    "B": (0.80, "Normalmente confiavel - fonte com historico de acerto"),
    "C": (0.60, "Razoavelmente confiavel"),
    "D": (0.40, "Nem sempre confiavel"),
    "E": (0.20, "Nao confiavel"),
    "F": (0.50, "Confiabilidade nao pode ser avaliada"),
}

ADMIRALTY_INFO: dict[str, tuple[float, str]] = {
    "1": (0.95, "Confirmada por outras fontes independentes"),
    "2": (0.80, "Provavelmente verdadeira"),
    "3": (0.60, "Possivelmente verdadeira"),
    "4": (0.40, "Duvidosa"),
    "5": (0.20, "Improvavel"),
    "6": (0.50, "Veracidade nao pode ser avaliada"),
}


def score_admiralty(codigo: str) -> float:
    """'B2' -> 0.64. Codigo invalido cai em F6 (0.25)."""
    codigo = (codigo or "F6").strip().upper()
    if len(codigo) != 2:
        codigo = "F6"
    f = ADMIRALTY_FONTE.get(codigo[0], ADMIRALTY_FONTE["F"])[0]
    i = ADMIRALTY_INFO.get(codigo[1], ADMIRALTY_INFO["6"])[0]
    return round(f * i, 4)


def descrever(codigo: str) -> str:
    codigo = (codigo or "F6").strip().upper()
    f = ADMIRALTY_FONTE.get(codigo[0], ADMIRALTY_FONTE["F"])[1]
    i = ADMIRALTY_INFO.get(codigo[1], ADMIRALTY_INFO["6"])[1]
    return f"{codigo}: {f} / {i}"


def combinar(scores: list[float]) -> float:
    """OU-ruidoso. Corrobora sem jamais atingir 1.0."""
    if not scores:
        return 0.0
    produto = 1.0
    for s in scores:
        produto *= (1.0 - max(0.0, min(1.0, s)))
    return round(min(0.99, 1.0 - produto), 4)


def rotulo(score: float) -> str:
    if score >= 0.75:
        return "alta"
    if score >= 0.50:
        return "media"
    if score >= 0.25:
        return "baixa"
    return "indiciaria"
