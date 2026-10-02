"""Identificadores financeiros: chave PIX, boleto, CNH e Cartao SUS.

Mesma regra de `documentos.py`: so aritmetica sobre o proprio identificador.
Nada aqui consulta banco, titular ou beneficiario.

- Chave PIX: classifica o formato (CPF, CNPJ, telefone, e-mail ou chave
  aleatoria EVP). A chave aleatoria e um UUID v4 e nao carrega informacao
  alguma sobre o titular; as demais carregam o proprio dado pessoal.
- Boleto bancario: linha digitavel de 47 digitos, com os tres DV de modulo 10
  dos campos e o DV geral de modulo 11. Da banco emissor, valor e as datas
  de vencimento possiveis (o fator reiniciou em 22/02/2025).
- CNH (registro de 11 digitos) e CNS (Cartao Nacional de Saude, 15 digitos):
  so validacao. Nao saem da extracao de texto porque colidem com CPF e
  telefone.
"""

from __future__ import annotations

import datetime as dt
import re

from .documentos import (cpf_valido, cnpj_valido, cnpj_limpar, _digitos)

_EVP = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)
_EMAIL = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
_FONE = re.compile(r"^\+55\d{10,11}$")

BASE_FATOR_1997 = dt.date(1997, 10, 7)
BASE_FATOR_2025 = dt.date(2025, 2, 22)      # fator 1000 reiniciado


# --------------------------------------------------------------- chave PIX
def classificar_chave_pix(chave: str) -> str | None:
    """'cpf' | 'cnpj' | 'telefone' | 'email' | 'evp' | None."""
    c = (chave or "").strip()
    if not c:
        return None
    if _EVP.match(c):
        return "evp"
    if _EMAIL.match(c):
        return "email"
    if _FONE.match(c):
        return "telefone"
    d = _digitos(c)
    if c == d or re.fullmatch(r"[\d.\-/ ]+", c):
        if len(d) == 11 and cpf_valido(d):
            return "cpf"
        if len(d) == 14 and cnpj_valido(d):
            return "cnpj"
    if re.fullmatch(r"[0-9A-Za-z.\-/]+", c) and len(cnpj_limpar(c)) == 14 \
            and cnpj_valido(c):
        return "cnpj"
    return None


# -------------------------------------------------------------------- boleto
def _dv10(campo: str) -> int:
    soma, peso = 0, 2
    for ch in reversed(campo):
        p = int(ch) * peso
        soma += p // 10 + p % 10
        peso = 1 if peso == 2 else 2
    return (10 - soma % 10) % 10


def _dv11_barras(barras43: str) -> int:
    soma, peso = 0, 2
    for ch in reversed(barras43):
        soma += int(ch) * peso
        peso = 2 if peso == 9 else peso + 1
    dv = 11 - soma % 11
    return 1 if dv in (0, 10, 11) else dv


def linha_para_barras(linha: str) -> str | None:
    d = _digitos(linha)
    if len(d) != 47:
        return None
    return d[0:4] + d[32] + d[33:47] + d[4:9] + d[10:20] + d[21:31]


def boleto_valido(linha: str) -> bool:
    d = _digitos(linha)
    if len(d) != 47:
        return False
    if (_dv10(d[0:9]) != int(d[9]) or _dv10(d[10:20]) != int(d[20])
            or _dv10(d[21:31]) != int(d[31])):
        return False
    barras = linha_para_barras(d)
    return _dv11_barras(barras[:4] + barras[5:]) == int(barras[4])


def montar_linha_digitavel(banco: str, fator: int, valor_centavos: int,
                           campo_livre: str, moeda: str = "9") -> str:
    """Linha digitavel valida a partir dos componentes (uso em testes e no
    mundo sintetico; numeros ficticios)."""
    if len(banco) != 3 or len(campo_livre) != 25:
        raise ValueError("banco tem 3 digitos e campo livre 25")
    resto = f"{fator:04d}{valor_centavos:010d}"
    sem_dv = banco + moeda + resto + campo_livre
    dv = _dv11_barras(sem_dv)
    barras = sem_dv[:4] + str(dv) + sem_dv[4:]
    c1 = barras[0:4] + barras[19:24]
    c2 = barras[24:34]
    c3 = barras[34:44]
    return (c1 + str(_dv10(c1)) + c2 + str(_dv10(c2)) + c3 + str(_dv10(c3))
            + barras[4] + barras[5:19])


def boleto_dados(linha: str) -> dict:
    d = _digitos(linha)
    barras = linha_para_barras(d) or ""
    fator = int(barras[5:9]) if barras else 0
    venc = []
    if fator:
        venc.append((BASE_FATOR_1997 + dt.timedelta(days=fator)).isoformat())
        if fator >= 1000:
            venc.append((BASE_FATOR_2025 + dt.timedelta(days=fator - 1000)).isoformat())
    return {"banco": barras[:3], "moeda": barras[3:4],
            "valor": int(barras[9:19]) / 100 if barras else 0.0,
            "fator_vencimento": fator,
            "vencimentos_possiveis": venc,
            "campo_livre": barras[19:]}


# ------------------------------------------------------------------ CNH, CNS
def cnh_valida(cnh: str) -> bool:
    d = _digitos(cnh)
    if len(d) != 11 or len(set(d)) == 1:
        return False
    soma, dsc = sum(int(d[i]) * (9 - i) for i in range(9)), 0
    dv1 = soma % 11
    if dv1 >= 10:
        dv1, dsc = 0, 2
    soma = sum(int(d[i]) * (1 + i) for i in range(9))
    x = soma % 11
    dv2 = 0 if x - dsc < 0 else (x - dsc if x - dsc < 10 else 0)
    return d[9:] == f"{dv1}{dv2}"


def cns_valido(cns: str) -> bool:
    d = _digitos(cns)
    if len(d) != 15:
        return False
    if d[0] in "12":
        pis = d[:11]
        soma = sum(int(pis[i]) * (15 - i) for i in range(11))
        dv = 11 - soma % 11
        dv = 0 if dv == 11 else dv
        if dv == 10:
            soma += 2
            dv = 11 - soma % 11
            res = f"{pis}001{dv}"
        else:
            res = f"{pis}000{dv}"
        return res == d
    if d[0] in "789":
        soma = sum(int(d[i]) * (15 - i) for i in range(15))
        return soma % 11 == 0
    return False


RX_BOLETO = re.compile(
    r"\b\d{5}\.\d{5}\s\d{5}\.\d{6}\s\d{5}\.\d{6}\s\d\s\d{14}\b|\b\d{47}\b")
RX_EVP = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b", re.I)
