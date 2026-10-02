"""Coletores. Cada um declara o que precisa e sob qual reserva opera."""

from .base import Coletor, Contexto, Achado, ClienteHTTP, REGISTRO
from . import (nucleo, registros, web, exposicao, br_fontes,  # noqa: F401
               dados_abertos, passivos)  # registro

__all__ = ["Coletor", "Contexto", "Achado", "ClienteHTTP", "REGISTRO",
           "nucleo", "registros", "web", "exposicao", "br_fontes",
           "dados_abertos", "passivos", "disponiveis", "obter"]


def disponiveis() -> list[str]:
    return sorted(REGISTRO)


def obter(nome: str) -> Coletor:
    if nome not in REGISTRO:
        raise KeyError(f"coletor '{nome}' nao existe. Disponiveis: "
                       f"{', '.join(disponiveis())}")
    return REGISTRO[nome]
