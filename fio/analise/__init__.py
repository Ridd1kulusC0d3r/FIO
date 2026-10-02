"""Analisadores: estagio de analise do pipeline.

Coletor pergunta ao mundo; analisador pergunta ao grafo. Nao ha rede aqui
-- so leitura do que ja foi coletado e producao de observacoes, que vao
para o relatorio numa secao propria, separadas dos vinculos.
"""

from .base import Analisador, ANALISADORES, registrar_analisador
from . import padrao  # noqa: F401  (registro)
from . import lote  # noqa: F401  (registro; depois de padrao: usa a marca de intermediario)

__all__ = ["Analisador", "ANALISADORES", "registrar_analisador"]
