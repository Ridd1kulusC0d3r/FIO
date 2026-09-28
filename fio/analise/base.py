from __future__ import annotations

from ..grafo.modelo import Grafo

ANALISADORES: dict[str, "Analisador"] = {}


class Analisador:
    nome = "base"
    descricao = ""
    origem = "interno"

    def analisar(self, g: Grafo) -> int:
        """Acrescenta observacoes ao grafo; devolve quantas."""
        raise NotImplementedError


def registrar_analisador(cls):
    inst = cls()
    ANALISADORES[inst.nome] = inst
    return cls
