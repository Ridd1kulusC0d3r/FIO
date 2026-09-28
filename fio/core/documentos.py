"""Documentos brasileiros: validacao, estrutura e extracao de texto.

Tudo aqui e aritmetica sobre o proprio identificador -- nenhum modulo
consulta titular de CPF, dono de placa ou eleitor. O que se extrai e o
que o numero carrega por construcao:

- CPF: o 9o digito indica a regiao fiscal de emissao. A Receita publica o
  CPF de socios mascarado como ***456789** -- e a mascara deixa o 9o
  digito visivel. Da para situar regionalmente um socio sem jamais ver o
  CPF completo.
- CNPJ: raiz (8) identifica a empresa, ordem (4) o estabelecimento.
  Suporta o formato alfanumerico (IN RFB 2.229/2024, vigente desde
  julho/2026): DV por modulo 11 com cada caractere valendo ASCII - 48.
- CEP: faixa do primeiro bloco -> UF, o que permite checar coerencia com
  o DDD do telefone.
- Titulo de eleitor: digitos 9-10 codificam a UF de inscricao.
- Placa: antiga <-> Mercosul (so conversao de formato).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

# --------------------------------------------------------------------- CPF
REGIAO_FISCAL_CPF = {
    "0": ("RS",), "1": ("DF", "GO", "MS", "MT", "TO"),
    "2": ("AC", "AM", "AP", "PA", "RO", "RR"), "3": ("CE", "MA", "PI"),
    "4": ("AL", "PB", "PE", "RN"), "5": ("BA", "SE"), "6": ("MG",),
    "7": ("ES", "RJ"), "8": ("SP",), "9": ("PR", "SC"),
}


def _digitos(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def cpf_dv(base9: str) -> str:
    nums = [int(c) for c in base9]
    d1 = sum(n * p for n, p in zip(nums, range(10, 1, -1))) * 10 % 11 % 10
    nums.append(d1)
    d2 = sum(n * p for n, p in zip(nums, range(11, 1, -1))) * 10 % 11 % 10
    return f"{d1}{d2}"


def cpf_valido(cpf: str) -> bool:
    d = _digitos(cpf)
    return len(d) == 11 and len(set(d)) > 1 and cpf_dv(d[:9]) == d[9:]


def cpf_formatar(cpf: str) -> str:
    d = _digitos(cpf)
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}" if len(d) == 11 else cpf


def cpf_mascarar(cpf: str) -> str:
    """Mascara no mesmo padrao da Receita: ***.456.789-**."""
    d = _digitos(cpf)
    return f"***.{d[3:6]}.{d[6:9]}-**" if len(d) == 11 else "***"


def cpf_regiao(cpf_ou_mascara: str) -> tuple[str, ...] | None:
    """Regiao fiscal a partir do CPF completo OU da mascara da Receita."""
    s = (cpf_ou_mascara or "").strip()
    d = _digitos(s)
    if len(d) == 11:
        return REGIAO_FISCAL_CPF.get(d[8])
    # mascara ***XXXXXX** : os 6 visiveis sao os digitos 4..9
    if len(d) == 6 and "*" in s:
        return REGIAO_FISCAL_CPF.get(d[5])
    return None


def cpf_compativel_com_mascara(cpf: str, mascara: str) -> bool:
    """O CPF completo (que o caso ja detem) bate com a mascara publicada?"""
    d, m = _digitos(cpf), _digitos(mascara)
    return len(d) == 11 and len(m) == 6 and d[3:9] == m


# -------------------------------------------------------------------- CNPJ
_CNPJ_CHARS = re.compile(r"^[0-9A-Z]{12}[0-9]{2}$")


def _val(c: str) -> int:
    return ord(c) - 48


def cnpj_dv(base12: str) -> str:
    base12 = base12.upper()
    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    r = sum(_val(c) * p for c, p in zip(base12, p1)) % 11
    d1 = 0 if r < 2 else 11 - r
    p2 = [6] + p1
    r = sum(_val(c) * p for c, p in zip(base12 + str(d1), p2)) % 11
    d2 = 0 if r < 2 else 11 - r
    return f"{d1}{d2}"


def cnpj_limpar(cnpj: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", cnpj or "").upper()


def cnpj_valido(cnpj: str) -> bool:
    c = cnpj_limpar(cnpj)
    if not _CNPJ_CHARS.match(c) or len(set(c)) == 1:
        return False
    return cnpj_dv(c[:12]) == c[12:]


def cnpj_alfanumerico(cnpj: str) -> bool:
    return any(ch.isalpha() for ch in cnpj_limpar(cnpj))


def cnpj_formatar(cnpj: str) -> str:
    c = cnpj_limpar(cnpj)
    if len(c) != 14:
        return cnpj
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


def cnpj_raiz(cnpj: str) -> str:
    return cnpj_limpar(cnpj)[:8]


def cnpj_matriz(cnpj: str) -> bool:
    return cnpj_limpar(cnpj)[8:12] == "0001"


# --------------------------------------------------------------------- CEP
_FAIXAS_CEP = [
    (1000, 19999, "SP"), (20000, 28999, "RJ"), (29000, 29999, "ES"),
    (30000, 39999, "MG"), (40000, 48999, "BA"), (49000, 49999, "SE"),
    (50000, 56999, "PE"), (57000, 57999, "AL"), (58000, 58999, "PB"),
    (59000, 59999, "RN"), (60000, 63999, "CE"), (64000, 64999, "PI"),
    (65000, 65999, "MA"), (66000, 68899, "PA"), (68900, 68999, "AP"),
    (69000, 69299, "AM"), (69300, 69399, "RR"), (69400, 69899, "AM"),
    (69900, 69999, "AC"), (70000, 72799, "DF"), (72800, 72999, "GO"),
    (73000, 73699, "DF"), (73700, 76799, "GO"), (76800, 76999, "RO"),
    (77000, 77999, "TO"), (78000, 78899, "MT"), (79000, 79999, "MS"),
    (80000, 87999, "PR"), (88000, 89999, "SC"), (90000, 99999, "RS"),
]


def cep_valido(cep: str) -> bool:
    d = _digitos(cep)
    return len(d) == 8 and cep_uf(d) is not None


def cep_uf(cep: str) -> str | None:
    d = _digitos(cep)
    if len(d) != 8:
        return None
    n = int(d[:5])
    for ini, fim, uf in _FAIXAS_CEP:
        if ini <= n <= fim:
            return uf
    return None


def cep_formatar(cep: str) -> str:
    d = _digitos(cep)
    return f"{d[:5]}-{d[5:]}" if len(d) == 8 else cep


# ------------------------------------------------------------------- placa
_PLACA_ANTIGA = re.compile(r"^[A-Z]{3}\d{4}$")
_PLACA_MERCOSUL = re.compile(r"^[A-Z]{3}\d[A-Z]\d{2}$")


def placa_limpar(p: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", p or "").upper()


def placa_tipo(p: str) -> str | None:
    c = placa_limpar(p)
    if _PLACA_ANTIGA.match(c):
        return "antiga"
    if _PLACA_MERCOSUL.match(c):
        return "mercosul"
    return None


def placa_equivalentes(p: str) -> list[str]:
    """Antiga e Mercosul da mesma placa: ABC1234 <-> ABC1C34."""
    c = placa_limpar(p)
    t = placa_tipo(c)
    if t == "antiga":
        return [c, c[:4] + "ABCDEFGHIJ"[int(c[4])] + c[5:]]
    if t == "mercosul":
        idx = "ABCDEFGHIJ".find(c[4])
        return [c] + ([c[:4] + str(idx) + c[5:]] if idx >= 0 else [])
    return []


# ------------------------------------------------------- titulo de eleitor
UF_TITULO = {
    "01": "SP", "02": "MG", "03": "RJ", "04": "RS", "05": "BA", "06": "PR",
    "07": "CE", "08": "PE", "09": "SC", "10": "GO", "11": "MA", "12": "PB",
    "13": "PA", "14": "ES", "15": "PI", "16": "RN", "17": "AL", "18": "MT",
    "19": "MS", "20": "DF", "21": "SE", "22": "AM", "23": "RO", "24": "AC",
    "25": "AP", "26": "RR", "27": "TO", "28": "exterior",
}


def titulo_valido(t: str) -> bool:
    d = _digitos(t).zfill(12)
    if len(d) != 12 or d[8:10] not in UF_TITULO:
        return False
    seq, uf, dv = d[:8], d[8:10], d[10:]
    sp_mg = uf in ("01", "02")
    r1 = sum(int(c) * p for c, p in zip(seq, range(2, 10))) % 11
    d1 = 0 if r1 == 10 else (1 if (r1 == 0 and sp_mg) else r1)
    r2 = (int(uf[0]) * 7 + int(uf[1]) * 8 + d1 * 9) % 11
    d2 = 0 if r2 == 10 else (1 if (r2 == 0 and sp_mg) else r2)
    return dv == f"{d1}{d2}"


def titulo_uf(t: str) -> str | None:
    d = _digitos(t).zfill(12)
    return UF_TITULO.get(d[8:10]) if len(d) == 12 else None


# ---------------------------------------------------------------- PIS/NIS
def pis_valido(p: str) -> bool:
    d = _digitos(p)
    if len(d) != 11 or len(set(d)) == 1:
        return False
    pesos = [3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    dv = 11 - sum(int(c) * w for c, w in zip(d[:10], pesos)) % 11
    return int(d[10]) == (0 if dv in (10, 11) else dv)


# ----------------------------------------------------------------- RENAVAM
def renavam_valido(r: str) -> bool:
    d = _digitos(r).zfill(11)
    if len(d) != 11 or len(set(d)) == 1:
        return False
    base = d[:10][::-1]
    pesos = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3]
    dv = sum(int(c) * w for c, w in zip(base, pesos)) * 10 % 11
    return int(d[10]) == (0 if dv == 10 else dv)


# ------------------------------------------------------------- extracao
@dataclass
class Documento:
    tipo: str            # cpf | cnpj | cep | placa | titulo | cpf-parcial
    valor: str           # canonico
    original: str
    valido: bool
    atributos: dict = field(default_factory=dict)
    ambiguo: bool = False

    def dict(self) -> dict:
        return asdict(self)


_RX = {
    "cpf_fmt": re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
    "cpf_mask": re.compile(r"\*{3}\.?\d{3}\.?\d{3}-?\*{2}"),
    "cnpj_fmt": re.compile(r"\b[0-9A-Z]{2}\.[0-9A-Z]{3}\.[0-9A-Z]{3}/[0-9A-Z]{4}-\d{2}\b"),
    "cnpj_raw": re.compile(r"\b\d{14}\b"),
    "cpf_raw": re.compile(r"\b\d{11}\b"),
    "cep": re.compile(r"\b\d{5}-\d{3}\b|\bCEP[:\s]*\d{8}\b", re.I),
    "placa": re.compile(r"\b[A-Z]{3}-?\d[A-Z0-9]\d{2}\b"),
}


def analisar(tipo: str, valor: str) -> Documento:
    """Analise estrutural de um documento declarado."""
    if tipo == "cpf":
        d = _digitos(valor)
        reg = cpf_regiao(d)
        return Documento("cpf", d, valor, cpf_valido(d),
                         {"formatado": cpf_formatar(d), "mascara": cpf_mascarar(d),
                          "regiao_fiscal": list(reg or [])})
    if tipo == "cpf-parcial":
        reg = cpf_regiao(valor)
        return Documento("cpf-parcial", valor.strip(), valor, reg is not None,
                         {"regiao_fiscal": list(reg or []),
                          "nota": "9o digito visivel na mascara da Receita"})
    if tipo == "cnpj":
        c = cnpj_limpar(valor)
        return Documento("cnpj", c, valor, cnpj_valido(c),
                         {"formatado": cnpj_formatar(c), "raiz": cnpj_raiz(c),
                          "matriz": cnpj_matriz(c),
                          "alfanumerico": cnpj_alfanumerico(c)})
    if tipo == "cep":
        d = _digitos(valor)
        return Documento("cep", d, valor, cep_valido(d),
                         {"formatado": cep_formatar(d), "uf": cep_uf(d)})
    if tipo == "placa":
        c = placa_limpar(valor)
        return Documento("placa", c, valor, placa_tipo(c) is not None,
                         {"formato": placa_tipo(c),
                          "equivalentes": placa_equivalentes(c)})
    if tipo == "titulo":
        d = _digitos(valor).zfill(12)
        return Documento("titulo", d, valor, titulo_valido(d),
                         {"uf_inscricao": titulo_uf(d)})
    if tipo == "pis":
        d = _digitos(valor)
        return Documento("pis", d, valor, pis_valido(d), {})
    if tipo == "renavam":
        d = _digitos(valor).zfill(11)
        return Documento("renavam", d, valor, renavam_valido(d), {})
    raise ValueError(f"tipo de documento desconhecido: {tipo}")


def extrair_documentos(texto: str) -> list[Documento]:
    """Extrai documentos de texto livre, deduplicados e validados.

    Sequencia de 11 digitos sem formatacao pode ser CPF ou telefone movel
    com DDD. So vira CPF se o DV fechar, e mesmo assim sai marcada como
    ambigua -- a decisao fica com o analista.
    """
    texto = texto or ""
    achados: dict[tuple[str, str], Documento] = {}

    def add(doc: Documento) -> None:
        if doc.valido and (doc.tipo, doc.valor) not in achados:
            achados[(doc.tipo, doc.valor)] = doc

    for m in _RX["cpf_fmt"].finditer(texto):
        add(analisar("cpf", m.group(0)))
    for m in _RX["cpf_mask"].finditer(texto):
        v = m.group(0)
        d = _digitos(v)
        add(analisar("cpf-parcial", f"***{d}**"))
    for m in _RX["cnpj_fmt"].finditer(texto):
        add(analisar("cnpj", m.group(0)))
    for m in _RX["cnpj_raw"].finditer(texto):
        add(analisar("cnpj", m.group(0)))
    for m in _RX["cpf_raw"].finditer(texto):
        doc = analisar("cpf", m.group(0))
        if doc.valido:
            doc.ambiguo = True
            doc.atributos["ambiguidade"] = ("11 digitos sem formatacao: pode "
                                            "ser telefone movel com DDD")
            add(doc)
    for m in _RX["cep"].finditer(texto):
        add(analisar("cep", _digitos(m.group(0))))
    for m in _RX["placa"].finditer(texto):
        add(analisar("placa", m.group(0)))
    return list(achados.values())
