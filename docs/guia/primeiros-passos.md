# Primeiros passos

Neste guia você instala o F.I.O., roda a demonstração, abre um caso seu **offline**, lê o resultado e verifica a integridade do que foi gerado. Tempo estimado: 15 minutos.

> **Antes de qualquer caso real:** o F.I.O. só trabalha com base legal declarada e escopo definido. Leia [USO-RESPONSAVEL.md](../../USO-RESPONSAVEL.md).

## 1. Requisitos

- **Python 3.10 ou mais novo** (testado até 3.14) em Windows, macOS ou Linux.
- Nenhuma biblioteca externa: nem a bancada web precisa de `pip install`.
- Internet só para as fontes online. Telefone, índice da Receita, documentos e relatórios funcionam offline.

Confira: `python3 --version`.

## 2. Instalar

Escolha um:

| Caminho | Comando / ação |
|---|---|
| **Sem instalar** | [Google Colab](colab.md) |
| **Dois cliques** | baixe a [Release](https://github.com/Ridd1kulusC0d3r/FIO/releases), descompacte e abra `Iniciar F.I.O. (Windows).bat`, `Iniciar F.I.O. (Mac).command` ou `iniciar-fio-linux.sh` (veja [COMECE-AQUI.md](../../COMECE-AQUI.md)) |
| **pip** | `pip install git+https://github.com/Ridd1kulusC0d3r/FIO` |
| **A partir do código** | `git clone https://github.com/Ridd1kulusC0d3r/FIO && cd FIO && python3 -m fio --help` |

Depois de instalar com pip, o comando é `fio`. A partir do código, use `python3 -m fio`. Os exemplos abaixo usam `fio`.

```bash
fio --versao        # fio 3.0.6
```

## 3. Rodar a demonstração

```bash
fio demo --abrir
```

Isso monta o caso `DEMO-FRAUDE-BOLETO` (empresas, sócios, telefones e uma ata, **tudo inventado**, nenhuma pessoa real) e abre a [bancada](bancada.md) no navegador. Sem `--abrir`, só monta o caso. Com `--recriar`, apaga e refaz.

Na bancada, clique em **Abrir caso de demonstração** e passe pelas abas **Grafo**, **Vínculos**, **Observações** e **Custódia**. Cada aresta do grafo mostra a fonte que a sustenta.

O que a demonstração tem de propósito: um telefone ligado a uma empresa por duas linhas, filiais da mesma raiz de CNPJ, sócios com CPF mascarado em regiões fiscais diferentes das empresas (gera observações) e uma ata de reunião (`dados_demo/ata_reuniao.txt`) de onde o extrator tira telefones, e-mail, CNPJs (um deles no formato alfanumérico), CEP, CPF e placa.

## 4. Seu primeiro caso (offline)

Para este passo, use o índice da demonstração como se fosse o índice da Receita:

```bash
# onde ficam os dados do F.I.O. (padrão: ~/.fio)
export FIO_HOME=$HOME/.fio
# aponta para o índice de CNPJ montado pela demo
export FIO_INDICE_CNPJ=$FIO_HOME/demo-cnpj.sqlite
```

**4.1. Abra o caso.** Base legal, finalidade e responsável são obrigatórios; a finalidade precisa ser específica (mínimo de 10 caracteres, e é ela que delimita o que pode ser coletado):

```bash
fio --ator "Fulana de Tal" caso novo \
  --id CASO-2026-001 \
  --titulo "Linhas de cobrança suspeitas" \
  --base-legal lgpd-7-vi \
  --finalidade "instruir notificação extrajudicial sobre cobrança fraudulenta" \
  --responsavel "Fulana de Tal" \
  --escopo "+5531988887777" \
  --dias 60
```

`fio bases` lista as bases legais aceitas. O prazo padrão é de 90 dias; `--dias` encurta ou alonga. Depois de expirado, nenhum coletor roda.

**4.2. Inclua o alvo.** O número é normalizado para o formato E.164 (`+5531988887777`) e entra no escopo:

```bash
fio alvo --caso CASO-2026-001 --tipo telefone --valor "(31) 98888-7777"
```

**4.3. Investigue.** Há dois comandos, e a diferença importa:

| Comando | Faz |
|---|---|
| `fio investigar` | **só coleta** e pivota |
| `fio lab pipeline` | prepara → **coleta → análise** → relatório, e registra um **experimento** (parâmetros, hash do código, versão das fontes, hash do grafo) |

As **observações analíticas** (incoerência geográfica, intermediário, lote de registro…) só existem depois do estágio de **análise**, ou seja, depois do `lab pipeline`. Use-o por padrão:

```bash
fio lab pipeline --caso CASO-2026-001 --offline --profundidade 2 --expandir-escopo
```

`--offline` usa só coletores locais; `--profundidade 2` segue os vínculos até dois saltos; `--expandir-escopo` autoriza pivotar sobre o que a coleta descobrir (cada inclusão fica no ledger). Saída típica:

```text
  preparacao  ok    0.00s  {"alvos": 1, "fontes_locais": 0, "plugins": 0}
  coleta      ok    0.01s  {"coletores": ["nucleo", "cnpj-reverso", ...], "entidades_novas": 11, ...}
  analise     ok    0.00s  {"observacoes": {"coerencia-geografica": 2, ...}, "clusters": 1, ...}
experimento EXP-20261002-050014-2197: concluido; grafo f73346f89cfad5b6
```

> Em modo offline, os coletores de rede aparecem na lista mas são **pulados**: cada um deixa um registro `coletor.pulado` no ledger e entra na métrica `coletores_pulados`. Sem `--expandir-escopo`, o F.I.O. lista como *pivôs bloqueados* tudo que descobriu e não pôde seguir.

**4.4. Leia o resultado.**

```bash
fio clusters --caso CASO-2026-001            # agrupamentos e pontes entre alvos
fio tabela   --caso CASO-2026-001 --limite 20 # tabela de correlação, do mais ao menos confiável
fio claims   --caso CASO-2026-001            # conclusões, cada uma com a evidência
```

Exemplo de agrupamento:

```text
[ 0.88] ancora-organizacao · 11222333000181 · 3 membros
        2 telefones ligados a mesma entidade organizacao 'AURORA TECH SOLUCOES LTDA', confianca media das arestas 0.76.
        ressalva: Verifique se a ancora nao e um intermediario generico (escritorio de contabilidade, ...)
```

Toda linha traz uma **ressalva**. Leia [Interpretando resultados](interpretando-resultados.md) antes de citar qualquer número.

**4.5. Gere o relatório e sele o caso.**

```bash
fio relatorio --caso CASO-2026-001 --saida relatorio.html --markdown relatorio.md --csv vinculos.csv --manifesto
```

`--manifesto` grava o SHA-256 de cada peça (grafo, caso, relatórios) amarrado ao último hash do ledger.

**4.6. Verifique a integridade**, agora e sempre que o material mudar de mãos:

```bash
fio ledger verificar  --caso CASO-2026-001   # cadeia de custódia íntegra?
fio manifesto verificar --caso CASO-2026-001 # alguma peça mudou desde a emissão?
```

Se alguém alterar um registro do ledger ou um arquivo do caso, os dois comandos apontam **onde**.

## 5. Onde ficam os arquivos

```text
~/.fio/                      (ou FIO_HOME)
├── casos/CASO-2026-001/
│   ├── caso.json            base legal, finalidade, escopo, prazo, quesitos
│   ├── grafo.json           entidades, arestas, observações
│   ├── ledger.jsonl         cadeia de custódia (append-only, SHA-256 encadeado)
│   ├── artefatos/<sha>.bin  resposta bruta de cada coleta
│   ├── experimentos/        parâmetros, código, fontes e hash do grafo de cada execução
│   ├── cache.sqlite         cache HTTP (TTL de 24 h por padrão)
│   └── manifesto.json       SHA-256 das peças (depois de `fio manifesto gerar`)
├── cnpj.sqlite              índice reverso do CNPJ (depois de `fio indice`)
├── indices/                 índices de dados abertos (receitas)
├── plugins/                 seus plugins .py
└── config.json              chaves de API e caminhos (opcional)
```

## 6. Próximos passos

- Cenário concreto → [Receitas de uso](receitas-de-uso.md).
- Mais cobertura → monte o [índice da Receita](indice-cnpj.md) e configure as [chaves](configuracao.md).
- Interface gráfica → [Bancada web](bancada.md).
- Algo deu errado → [Solução de problemas](solucao-de-problemas.md).
