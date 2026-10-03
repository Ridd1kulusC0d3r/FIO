"""Plano de numeracao brasileiro (Resolucao Anatel 741/2020 e correlatas).

Tabelas embutidas, zero rede. O objetivo aqui nao e "descobrir o dono" do
numero -- isso nao e publico -- e sim extrair tudo o que a estrutura do
numero revela por si: regiao, tipo de servico, bloco de numeracao e
plausibilidade. E o que sustenta hipotese de vinculo organizacional.
"""

from __future__ import annotations

# DDD -> (UF, regiao/area principal)
DDD_INFO: dict[str, tuple[str, str]] = {
    "11": ("SP", "Sao Paulo e Grande SP"),
    "12": ("SP", "Vale do Paraiba / Litoral Norte"),
    "13": ("SP", "Baixada Santista"),
    "14": ("SP", "Bauru / Marilia"),
    "15": ("SP", "Sorocaba"),
    "16": ("SP", "Ribeirao Preto / Sao Carlos"),
    "17": ("SP", "Sao Jose do Rio Preto"),
    "18": ("SP", "Presidente Prudente / Aracatuba"),
    "19": ("SP", "Campinas / Piracicaba"),
    "21": ("RJ", "Rio de Janeiro e Regiao Metropolitana"),
    "22": ("RJ", "Campos / Regiao dos Lagos"),
    "24": ("RJ", "Volta Redonda / Petropolis"),
    "27": ("ES", "Vitoria e Grande Vitoria"),
    "28": ("ES", "Cachoeiro de Itapemirim"),
    "31": ("MG", "Belo Horizonte e Regiao Metropolitana"),
    "32": ("MG", "Juiz de Fora"),
    "33": ("MG", "Governador Valadares"),
    "34": ("MG", "Uberlandia / Triangulo"),
    "35": ("MG", "Pocos de Caldas / Varginha"),
    "37": ("MG", "Divinopolis / Centro-Oeste"),
    "38": ("MG", "Montes Claros / Norte"),
    "41": ("PR", "Curitiba e Regiao Metropolitana"),
    "42": ("PR", "Ponta Grossa / Guarapuava"),
    "43": ("PR", "Londrina"),
    "44": ("PR", "Maringa"),
    "45": ("PR", "Foz do Iguacu / Cascavel"),
    "46": ("PR", "Pato Branco / Francisco Beltrao"),
    "47": ("SC", "Joinville / Blumenau / Itajai"),
    "48": ("SC", "Florianopolis / Criciuma"),
    "49": ("SC", "Chapeco / Lages"),
    "51": ("RS", "Porto Alegre e Regiao Metropolitana"),
    "53": ("RS", "Pelotas / Rio Grande"),
    "54": ("RS", "Caxias do Sul / Serra"),
    "55": ("RS", "Santa Maria / Fronteira Oeste"),
    "61": ("DF", "Distrito Federal e Entorno"),
    "62": ("GO", "Goiania"),
    "63": ("TO", "Palmas e todo o Tocantins"),
    "64": ("GO", "Rio Verde / Sul de Goias"),
    "65": ("MT", "Cuiaba"),
    "66": ("MT", "Rondonopolis / Sinop"),
    "67": ("MS", "Campo Grande e todo o MS"),
    "68": ("AC", "Rio Branco e todo o Acre"),
    "69": ("RO", "Porto Velho e toda Rondonia"),
    "71": ("BA", "Salvador e Regiao Metropolitana"),
    "73": ("BA", "Itabuna / Ilheus / Porto Seguro"),
    "74": ("BA", "Juazeiro / Norte"),
    "75": ("BA", "Feira de Santana"),
    "77": ("BA", "Vitoria da Conquista / Barreiras"),
    "79": ("SE", "Aracaju e todo Sergipe"),
    "81": ("PE", "Recife e Regiao Metropolitana"),
    "82": ("AL", "Maceio e todo Alagoas"),
    "83": ("PB", "Joao Pessoa / Campina Grande"),
    "84": ("RN", "Natal / Mossoro"),
    "85": ("CE", "Fortaleza e Regiao Metropolitana"),
    "86": ("PI", "Teresina"),
    "87": ("PE", "Petrolina / Caruaru / Sertao"),
    "88": ("CE", "Juazeiro do Norte / Sobral"),
    "89": ("PI", "Picos / Floriano"),
    "91": ("PA", "Belem e Regiao Metropolitana"),
    "92": ("AM", "Manaus"),
    "93": ("PA", "Santarem / Oeste do Para"),
    "94": ("PA", "Maraba / Sudeste do Para"),
    "95": ("RR", "Boa Vista e todo Roraima"),
    "96": ("AP", "Macapa e todo Amapa"),
    "97": ("AM", "Interior do Amazonas"),
    "98": ("MA", "Sao Luis"),
    "99": ("MA", "Imperatriz / Sul do Maranhao"),
}

# Prefixos nao geograficos (sem DDD, cobertura nacional)
NAO_GEOGRAFICOS: dict[str, str] = {
    "0300": "Servico de acesso pago pelo chamador (custo local)",
    "0500": "Doacoes / campanhas",
    "0800": "Discagem direta gratuita (pago pelo assinante chamado)",
    "0900": "Servico de valor adicionado (tarifa premium)",
    "4003": "Numero unico nacional (custo de chamada local)",
    "4004": "Numero unico nacional (custo de chamada local)",
    "4007": "Numero unico nacional (custo de chamada local)",
    "4020": "Numero unico nacional (custo de chamada local)",
}

# Codigos de Selecao de Prestadora (CSP) mais comuns, uteis para
# reconhecer o padrao 0 + CSP + DDD + numero em textos coletados.
CSP: dict[str, str] = {
    "12": "Algar/CTBC", "14": "Brasil Telecom/Oi", "15": "Telefonica/Vivo",
    "21": "Claro/Embratel", "23": "Intelig/TIM", "25": "GVT/Vivo",
    "31": "Oi", "41": "TIM", "43": "Sercomtel",
}

SERVICOS_ESPECIAIS: dict[str, str] = {
    "190": "Policia Militar", "192": "SAMU", "193": "Corpo de Bombeiros",
    "197": "Policia Civil", "180": "Central de Atendimento a Mulher",
    "181": "Disque Denuncia", "100": "Direitos Humanos",
    "188": "CVV", "153": "Guarda Municipal",
}


def classificar(assinante: str) -> tuple[str, str]:
    """Classifica pelo numero do assinante (sem DDD).

    Retorna (tipo, justificativa). Tipos: movel, fixo, indefinido.
    """
    if not assinante:
        return ("indefinido", "numero de assinante vazio")
    if len(assinante) == 9 and assinante[0] == "9":
        return ("movel", "9 digitos iniciados em 9: SMP (Servico Movel Pessoal)")
    if len(assinante) == 8 and assinante[0] in "2345":
        return ("fixo", f"8 digitos iniciados em {assinante[0]}: STFC (telefonia fixa)")
    if len(assinante) == 8 and assinante[0] in "6789":
        return ("movel", "8 digitos iniciados em 6-9: movel legado, anterior ao 9o digito")
    if len(assinante) == 9 and assinante[0] in "2345":
        return ("indefinido", "9 digitos iniciados em 2-5: fora do plano vigente, "
                              "possivel erro de digitacao ou numero fabricado")
    return ("indefinido", f"comprimento {len(assinante)} fora do plano de numeracao")


def faixa_numeracao(ddd: str, assinante: str) -> str | None:
    """Bloco de numeracao: DDD + 5 primeiros digitos do assinante.

    Blocos sao destinados em lotes as prestadoras e, dentro de uma empresa,
    ramais e linhas corporativas costumam cair no mesmo bloco. Dois numeros
    no mesmo bloco sao indicio fraco de origem comum -- nunca prova.
    """
    if not ddd or len(assinante) < 6:
        return None
    return f"{ddd}{assinante[:5]}"


def geografia(ddd: str) -> tuple[str, str] | None:
    return DDD_INFO.get(ddd)


def ddd_valido(ddd: str) -> bool:
    return ddd in DDD_INFO
