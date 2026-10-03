"""Normalizacao e canonicalizacao de numeros de telefone brasileiros.

Duas funcoes carregam o peso do framework inteiro:

- normalizar(): transforma qualquer grafia em uma chave canonica E.164.
  Sem isso, "(31) 9 8888-7777" e "+5531988887777" viram duas entidades
  diferentes no grafo e o vinculo se perde.
- variantes(): faz o caminho inverso, gerando as grafias plausiveis do
  mesmo numero. E o que alimenta busca em indice publico: quem publicou o
  numero escreveu de UMA forma, e voce nao sabe qual.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

from . import anatel

_SO_DIGITOS = re.compile(r"\D+")
# CSP no formato 0 + CSP(2) + DDD(2) + assinante
_COM_CSP = re.compile(r"^0(\d{2})(\d{2})(\d{8,9})$")


@dataclass
class Telefone:
    """Numero canonicalizado com tudo o que a estrutura revela."""

    original: str
    valido: bool
    e164: str | None = None
    pais: str = "55"
    ddd: str | None = None
    assinante: str | None = None
    tipo: str = "indefinido"          # movel | fixo | nao-geografico | especial
    justificativa: str = ""
    uf: str | None = None
    area: str | None = None
    faixa: str | None = None
    csp: str | None = None
    avisos: list[str] = field(default_factory=list)

    @property
    def chave(self) -> str:
        """Chave de identidade no grafo."""
        return self.e164 or f"raw:{_SO_DIGITOS.sub('', self.original)}"

    def formatado(self) -> str:
        if not self.valido or not self.ddd:
            return self.original
        a = self.assinante or ""
        if len(a) == 9:
            return f"({self.ddd}) {a[0]} {a[1:5]}-{a[5:]}"
        return f"({self.ddd}) {a[:4]}-{a[4:]}"

    def dict(self) -> dict:
        d = asdict(self)
        d["chave"] = self.chave
        d["formatado"] = self.formatado()
        return d


def normalizar(bruto: str, ddd_padrao: str | None = None) -> Telefone:
    """Canonicaliza um numero. Nunca levanta excecao: retorna invalido."""
    if bruto is None:
        return Telefone(original="", valido=False, justificativa="entrada nula")

    texto = str(bruto).strip()
    d = _SO_DIGITOS.sub("", texto)
    avisos: list[str] = []

    if not d:
        return Telefone(original=texto, valido=False,
                        justificativa="nenhum digito na entrada")

    # Servicos de emergencia e utilidade publica
    if d in anatel.SERVICOS_ESPECIAIS:
        return Telefone(original=texto, valido=True, e164=d, ddd=None,
                        assinante=d, tipo="especial",
                        justificativa=anatel.SERVICOS_ESPECIAIS[d])

    # Nao geograficos: 0800 / 0300 / 4004 ...
    for prefixo, desc in anatel.NAO_GEOGRAFICOS.items():
        if d.startswith(prefixo) and len(d) in (10, 11):
            # nao sao discaveis do exterior: chave canonica e o proprio
            # numero nacional, sem +55
            return Telefone(original=texto, valido=True, e164=d,
                            assinante=d, tipo="nao-geografico",
                            justificativa=desc,
                            avisos=["numero corporativo nacional: nao "
                                    "individualiza pessoa fisica"])

    csp = None
    # 0 + CSP + DDD + assinante
    m = _COM_CSP.match(d)
    if m:
        csp = m.group(1)
        avisos.append(f"CSP {csp} removido ({anatel.CSP.get(csp, 'prestadora nao mapeada')})")
        d = m.group(2) + m.group(3)

    # prefixo internacional / DDI
    if d.startswith("0055"):
        d = d[4:]
    elif d.startswith("55") and len(d) in (12, 13):
        d = d[2:]
    elif d.startswith("0") and len(d) in (11, 12):
        avisos.append("prefixo 0 de discagem removido")
        d = d[1:]

    if len(d) in (8, 9) and ddd_padrao:
        avisos.append(f"numero sem DDD; assumido DDD {ddd_padrao} do escopo do caso")
        d = ddd_padrao + d

    if len(d) not in (10, 11):
        return Telefone(original=texto, valido=False, avisos=avisos,
                        justificativa=f"{len(d)} digitos apos limpeza; "
                                      f"esperado 10 (fixo) ou 11 (movel) com DDD")

    ddd, assinante = d[:2], d[2:]

    if not anatel.ddd_valido(ddd):
        return Telefone(original=texto, valido=False, ddd=ddd,
                        assinante=assinante, avisos=avisos,
                        justificativa=f"DDD {ddd} nao existe no plano nacional")

    tipo, just = anatel.classificar(assinante)

    # Correcao do 9o digito: movel de 8 digitos e legado
    if tipo == "movel" and len(assinante) == 8:
        avisos.append("movel sem o 9o digito; forma atual seria 9" + assinante)

    uf, area = anatel.DDD_INFO[ddd]
    t = Telefone(
        original=texto, valido=(tipo != "indefinido"), e164=f"+55{ddd}{assinante}",
        ddd=ddd, assinante=assinante, tipo=tipo, justificativa=just,
        uf=uf, area=area, faixa=anatel.faixa_numeracao(ddd, assinante),
        csp=csp, avisos=avisos,
    )
    if tipo == "indefinido":
        t.avisos.append("estrutura fora do plano vigente: tratar como nao confirmado")
    return t


def variantes(t: Telefone, limite: int = 24) -> list[str]:
    """Grafias plausiveis do mesmo numero, para busca em indice publico."""
    if not t.ddd or not t.assinante:
        return []
    ddd, a = t.ddd, t.assinante
    saida: list[str] = []

    def add(v: str) -> None:
        if v and v not in saida:
            saida.append(v)

    corpos = [a]
    # movel com e sem o 9o digito: quem publicou pode ter usado a forma antiga
    if len(a) == 9 and a[0] == "9":
        corpos.append(a[1:])
    elif len(a) == 8 and a[0] in "6789":
        corpos.append("9" + a)

    for c in corpos:
        meio = 5 if len(c) == 9 else 4
        p1, p2 = c[:meio], c[meio:]
        add(f"+55{ddd}{c}")
        add(f"55{ddd}{c}")
        add(f"{ddd}{c}")
        add(f"({ddd}){c}")
        add(f"({ddd}) {p1}-{p2}")
        add(f"({ddd}){p1}-{p2}")
        add(f"({ddd}) {p1}{p2}")
        add(f"{ddd} {p1}-{p2}")
        add(f"{ddd} {p1} {p2}")
        add(f"+55 {ddd} {p1}-{p2}")
        add(f"+55 ({ddd}) {p1}-{p2}")
        add(f"0{ddd}{c}")
        add(f"{p1}-{p2}")
        add(f"{p1}{p2}")
    return saida[:limite]


def extrair_de_texto(texto: str, ddd_padrao: str | None = None) -> list[Telefone]:
    """Varre texto livre e devolve telefones normalizados e deduplicados.

    Util para processar paginas coletadas, PDFs ja convertidos, respostas
    de API e qualquer material bruto do caso.
    """
    padrao = re.compile(
        r"(?:\+?55[\s.-]?)?(?:\(?\d{2}\)?[\s.-]?)?(?:9[\s.-]?)?\d{4}[\s.-]?\d{4}"
    )
    vistos: dict[str, Telefone] = {}
    for m in padrao.finditer(texto or ""):
        t = normalizar(m.group(0), ddd_padrao=ddd_padrao)
        if t.valido and t.chave not in vistos:
            vistos[t.chave] = t
    return list(vistos.values())
