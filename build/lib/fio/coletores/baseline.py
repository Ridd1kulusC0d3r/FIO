"""Baseline diferencial: descarta o "200 OK" que e so uma pagina padrao.

Muita fonte responde HTTP 200 a qualquer consulta (pagina de "nada
encontrado", redirecionamento para a home, SPA que renderiza no cliente).
Tratar esse 200 como achado e a fonte classica de falso positivo.

O metodo: antes de confiar na resposta a um alvo real, consulta-se um
valor que NAO PODE existir (o *impossivel*) na mesma fonte. Se a resposta
real e quase igual a resposta ao impossivel, ela nao diz nada sobre o alvo.

So biblioteca padrao. A comparacao usa conjuntos de "shingles" de palavras
(Jaccard), insensiveis a numeros, datas e espacos, que e o que muda entre
duas respostas da mesma pagina padrao.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

LIMIAR_PADRAO = 0.90
_TAG = re.compile(r"<(script|style)\b.*?</\1>", re.I | re.S)
_MARCA = re.compile(r"<[^>]+>")
_NUM = re.compile(r"\d+")
_ESPACO = re.compile(r"\s+")


def normalizar_corpo(corpo: bytes | str) -> str:
    """Texto comparavel: sem scripts, sem tags, sem numeros, sem caixa."""
    texto = corpo.decode("utf-8", "replace") if isinstance(corpo, bytes) else corpo
    texto = _TAG.sub(" ", texto)
    texto = _MARCA.sub(" ", texto)
    texto = _NUM.sub("0", texto.lower())
    return _ESPACO.sub(" ", texto).strip()


def _shingles(texto: str, k: int = 3) -> set[str]:
    palavras = texto.split()
    if len(palavras) < k:
        return {texto} if texto else set()
    return {" ".join(palavras[i:i + k]) for i in range(len(palavras) - k + 1)}


def similaridade(a: bytes | str, b: bytes | str) -> float:
    """Jaccard de shingles, de 0 (nada em comum) a 1 (identicas)."""
    sa, sb = _shingles(normalizar_corpo(a)), _shingles(normalizar_corpo(b))
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def impressao(corpo: bytes | str) -> str:
    """Hash curto do corpo normalizado, para registrar no ledger."""
    return hashlib.sha256(normalizar_corpo(corpo).encode()).hexdigest()[:16]


@dataclass
class Veredito:
    soft404: bool
    similaridade: float
    status_real: int
    status_impossivel: int
    motivo: str

    def dict(self) -> dict:
        return {"soft404": self.soft404,
                "similaridade": round(self.similaridade, 4),
                "status_real": self.status_real,
                "status_impossivel": self.status_impossivel,
                "motivo": self.motivo}


def julgar(status_real: int, corpo_real: bytes,
           status_impossivel: int, corpo_impossivel: bytes,
           limiar: float = LIMIAR_PADRAO) -> Veredito:
    """Decide se a resposta real e indistinguivel da resposta ao impossivel."""
    if status_real == 0:
        return Veredito(True, 0.0, status_real, status_impossivel,
                        "sem resposta da fonte")
    if status_real >= 400:
        return Veredito(True, 0.0, status_real, status_impossivel,
                        f"fonte respondeu HTTP {status_real}")
    if status_impossivel == 0 or not corpo_impossivel:
        return Veredito(False, 0.0, status_real, status_impossivel,
                        "sem baseline: resposta aceita, mas nao verificada")
    if status_impossivel >= 400:
        # a fonte distingue existente de inexistente pelo status: baseline ok
        return Veredito(False, 0.0, status_real, status_impossivel,
                        "a fonte devolve erro para valor inexistente")
    s = similaridade(corpo_real, corpo_impossivel)
    if s >= limiar:
        return Veredito(True, s, status_real, status_impossivel,
                        f"resposta {s:.0%} igual a de um valor impossivel "
                        f"(pagina padrao / soft-404)")
    return Veredito(False, s, status_real, status_impossivel,
                    f"resposta difere da de um valor impossivel ({s:.0%})")


def impossivel(tipo: str) -> str:
    """Valor que, por construcao, nao existe, para cada tipo de alvo."""
    return {
        "telefone": "+5500000000000",
        "cnpj": "00000000000000",
        "cep": "00000000",
        "email": "fio-baseline-inexistente-0000@invalid.test",
        "dominio": "fio-baseline-inexistente-0000.invalid",
        "pessoa": "ZZZZZ QQQQQ XXXXX",
        "url": "https://fio-baseline-inexistente-0000.invalid/",
    }.get(tipo, "fio-baseline-inexistente-0000")
