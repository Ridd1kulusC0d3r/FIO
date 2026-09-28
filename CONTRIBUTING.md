# Como contribuir

Obrigado pelo interesse. Três regras fazem o F.I.O. ser o que é:

1. **Só biblioteca padrão do Python** no código do pacote `fio/`. Ferramentas de teste
   (Playwright, coverage, nbclient) podem ser usadas nos testes e no CI, nunca no pacote.
2. **Toda aresta nasce com fonte e grau Admiralty.** Coletor novo declara `admiralty`,
   `reserva` (o que a fonte NÃO prova) e `estagio`.
3. **Nada do que está em [USO-RESPONSAVEL.md](USO-RESPONSAVEL.md) como recusado entra.**

## Preparar o ambiente

```bash
git clone https://github.com/Ridd1kulusC0d3r/FIO && cd fio-lab
python -m unittest discover -s testes -v
python testes/fumaca.py
```

## Tipos de contribuição mais úteis

| Contribuição | Onde | Precisa de código? |
|---|---|---|
| Nova fonte tabular de dados abertos | receita JSON em `exemplos/` (veja `receita_exemplo.json`) | não |
| Fonte online nova | `fio/coletores/` + teste com servidor simulado em `testes/test_integracao_http.py` | sim |
| Analisador | `fio/analise/` ou plugin em `exemplos/` | sim |
| Heurística avaliável | `fio/lab/avaliacao.py` e `fio/lab/benchmark_real.py` | sim |
| Fonte que mudou de formato | abra uma issue "Fonte quebrada" com a saída de `python testes/ao_vivo.py` | não |

## Antes do pull request

- `python -m unittest discover -s testes` passa.
- `python testes/fumaca.py` passa.
- Mudou algo em `fio/`? Rode `python tools/gerar_notebook.py` para atualizar o caderno do Colab.
- Texto voltado ao usuário em português do Brasil.
