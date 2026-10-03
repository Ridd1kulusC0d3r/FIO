"""Modelo exportável de relatório analítico do F.I.O.

O modelo é intencionalmente neutro: separa observação, avaliação e conclusão,
registra limitações e preserva a rastreabilidade da evidência. Pode ser baixado
antes de qualquer caso para servir como roteiro de trabalho.
"""

from __future__ import annotations

import html


def modelo_markdown() -> str:
    return """# F.I.O. — Modelo de Relatório de Investigação em Fontes Abertas

> **Uso responsável.** Este documento é um modelo. Preencha somente com dados
> obtidos de forma lícita e pertinente à finalidade registrada no caso. Uma
> associação observada em fonte pública não prova relação pessoal, autoria ou
> prática ilícita.

## 1. Identificação do caso

- **ID:**
- **Título:**
- **Responsável:**
- **Data/hora (UTC):**
- **Base legal:**
- **Finalidade:**
- **Escopo autorizado:**

## 2. Quesito / objetivo analítico

Descreva a pergunta que o trabalho tenta responder. Evite conclusões embutidas
na pergunta.

## 3. Fontes e método

| Fonte | Tipo | Data/hora | Alvo | Resultado | Limitação |
|---|---|---|---|---|---|
| | | | | | |

### 3.1 Critérios de confiança

Registre como a confiabilidade da fonte, a credibilidade da informação,
recência, corroboração e possíveis intermediários influenciaram a avaliação.

## 4. Observações verificáveis

Liste somente fatos diretamente observados nas fontes. Para cada item, indique
origem e momento da coleta.

1. 
2. 
3. 

## 5. Vínculos e correlações

| Entidade A | Relação observada | Entidade B | Confiança | Fontes | Ressalva |
|---|---|---|---|---|---|
| | | | | | |

## 6. Hipóteses / avaliação analítica

Separe inferência de observação. Para cada hipótese, registre evidências a favor,
evidências contrárias e o grau de confiança.

### Hipótese A
- **Avaliação:**
- **Confiança:** baixa / média / alta
- **A favor:**
- **Contra / alternativas:**
- **O que faltaria para confirmar ou refutar:**

## 7. Lacunas e limitações

- Fontes indisponíveis ou com erro:
- Dados possivelmente desatualizados:
- Identificadores ambíguos ou compartilhados:
- Possíveis falsos positivos:
- Restrições de escopo:

## 8. Conclusão

Responda ao quesito apenas no nível sustentado pelas evidências. Não transforme
correlação em causalidade ou associação cadastral em vínculo pessoal.

## 9. Integridade e cadeia de custódia

- **Hash/estado do ledger:**
- **Arquivos exportados:**
- **Hash dos artefatos principais:**
- **Observações sobre reprodutibilidade:**

## 10. Anexos

- Tabela de vínculos
- Mapa/grafo
- Linha do tempo de coleta
- Evidências selecionadas
- Registro de erros e fontes não consultadas
"""


def modelo_html() -> str:
    """Versão HTML simples do modelo, alinhada à identidade visual do manual."""
    md = modelo_markdown()
    # O HTML é deliberadamente simples e sem dependências externas para poder
    # ser aberto offline. Mantemos a hierarquia do Markdown em um bloco legível.
    corpo = html.escape(md)
    return f"""<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>F.I.O. — Modelo de Relatório</title><style>
:root{{--papel:#F3F5F4;--sup:#fff;--tinta:#17212B;--texto:#2C3740;--mudo:#5B6770;
--linha:#D2D9D6;--fio:#0E7C6B;--cod:#EEF2F0}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--papel);color:var(--texto);
font:16px/1.65 Verdana,'Segoe UI',sans-serif}}main{{max-width:900px;margin:0 auto;padding:36px 20px 80px}}
header{{margin-bottom:22px}}.chapeu{{color:var(--fio);font-weight:700;text-transform:uppercase;
letter-spacing:.1em;font-size:12px}}h1{{font:700 40px/1.1 Georgia,serif;color:var(--tinta);margin:8px 0}}
pre{{white-space:pre-wrap;background:var(--sup);border:1px solid var(--linha);border-radius:14px;
padding:22px;font:14px/1.65 ui-monospace,Menlo,Consolas,monospace;box-shadow:0 1px 2px #17212b0f}}
</style></head><body><main><header><div class='chapeu'>F.I.O. · modelo exportável</div>
<h1>Relatório de investigação em fontes abertas</h1></header><pre>{corpo}</pre></main></body></html>"""
