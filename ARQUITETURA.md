# Arquitetura do F.I.O. Lab

```
                      ┌─────────────────────── política do caso ───────────────────────┐
                      │ base legal · finalidade · escopo (checado a cada pivô) · prazo │
                      └───────────────────────────────┬────────────────────────────────┘
                                                      │
 alvos ─► [preparação] ─► [coleta] ──────────────────► [análise] ─► [relatório]
          plugins         ingestão     extrator          coerência      técnico (HTML/MD/CSV)
          versão fontes   normalização nucleo            intermediários laudo (art. 158-B)
          hash código     enriquecimento cnpj-reverso    sanções        RELINT
                                       dados-abertos     plugins
                                       querido-diario
                                       viacep · rdap · transparencia · web · hibp
                               │                 │
                               ▼                 ▼
                     ledger SHA-256 encadeado   grafo (entidades, arestas com Fonte/Admiralty,
                     + artefatos por hash       observações)
                               │                 │
                               └──────► experimento (parâmetros, código, fontes,
                                         métricas por estágio, SHA-256 do grafo)
```

## Pacotes

| Pacote | Responsabilidade |
|---|---|
| `fio.core` | `normalize` (E.164, grafias), `anatel` (plano de numeração), `documentos` (CPF, CNPJ alfanumérico, CEP, placa, título, PIS, RENAVAM) |
| `fio.politica` | `Caso`, bases legais, fontes vedadas, `ViolacaoDeEscopo` |
| `fio.evidencia` | ledger append-only encadeado; cache HTTP sqlite |
| `fio.grafo` | modelo com proveniência obrigatória; Admiralty + OU-ruidoso por fonte independente; clusters, pontes, tabela |
| `fio.coletores` | coletores registrados por decorador, com `estagio`, `admiralty`, `reserva` |
| `fio.receitas` | indexador universal de dados abertos (CSV/JSON/ZIP → sqlite) |
| `fio.indice` | índice reverso dos Dados Abertos do CNPJ; filtro por UF em duas passagens com escopo SQLite (RAM limitada) |
| `fio.receita_download` | descobre o mês mais recente; downloader retomável com Range/If-Range; valida cache, processa e apaga arquivo por arquivo |
| `fio.analise` | analisadores sobre o grafo, sem rede |
| `fio.motor` | pivô por profundidade, com escopo em cada salto |
| `fio.lab.pipeline` | estágios, métricas, experimento |
| `fio.lab.experimentos` | registro, snapshot do grafo, comparação |
| `fio.lab.fila` | tarefas sqlite + workers em thread |
| `fio.lab.plugins` | descoberta, inventário, assinatura do código |
| `fio.lab.sintetico` | mundos fictícios com gabarito e armadilhas |
| `fio.lab.avaliacao` | P/R/F1 pareado por heurística, varredura de limiar, lote |
| `fio.lab.bancada` | servidor local + SPA |
| `fio.relatorio` | relatório técnico, Markdown, laudo/RELINT, mapa interativo para cadernos |
| `fio.lab.benchmark_real` | benchmark com a raiz do CNPJ como gabarito oculto |
| `tools/` | gerador do caderno do Colab e configurador do repositório |

## Decisões de projeto

**Identidade de entidade = tipo + valor canônico.** Telefone por E.164,
CNPJ pelos 14 caracteres (numéricos ou alfanuméricos), pessoa por
`NOME [máscara do CPF]`. A última chave nasceu de um bug que a avaliação
sintética encontrou: com chave só por nome, homônimos viravam uma pessoa só
e o experimento deixava de ser reprodutível, porque o atributo da máscara
dependia da ordem de coleta.

**Corroboração exige independência.** O score de uma aresta agrupa as fontes
por coletor e só então combina. Cinco leituras da mesma base não são cinco
confirmações.

**Reprodutibilidade verificável.** `sha_grafo` ignora timestamps e cobre
entidades, atributos e confiança. Duas execuções com o mesmo código e as
mesmas fontes devem produzir o mesmo hash, e isso é testado.

**Sintético sempre offline.** Números fictícios podem coincidir com linhas
reais. O avaliador força `offline=True`, e o teste confere que o experimento
teve zero requisições.

**Minimização.** CPF completo extraído de documento vira máscara antes de
entrar no grafo. O relatório nunca exibe o que o grafo não guarda.

**Construção do índice CNPJ em três camadas.** Primeiro, `Estabelecimentos`
seleciona a UF e persiste somente as raízes aceitas numa tabela SQLite auxiliar;
depois, `Empresas` e `Sócios` são filtrados em lotes contra esse escopo. Os índices
secundários (`telefone`, `email`, `cnpj_basico`, `socio`) só são materializados no
fim da carga, seguidos de `ANALYZE`. O arquivo final só substitui o anterior após a
construção fechar com sucesso.

**Downloader fail-closed.** Um `.parcial` usa `Range` + `If-Range` para retomada.
Resposta 200 durante retomada reinicia o arquivo, 416 descarta o parcial, tamanho
incompatível falha e, mesmo com tamanho correto, o ZIP é testado antes de
`os.replace`. Assim, um proxy ou origem que entregue conteúdo truncado/corrompido
não contamina o índice seguinte.


## Estendendo

- **Coletor novo:** `Coletor` + `@registrar`; declare `tipos_alvo`,
  `estagio`, `admiralty`, `reserva`; use `ctx.http()` (cache, rate limit e
  ledger já inclusos).
- **Analisador novo:** `Analisador` + `@registrar_analisador`; escreva em
  `g.observar(...)`.
- **Fonte tabular nova:** uma receita JSON; sem código.
- **Heurística nova para avaliar:** acrescente em `avaliacao.prever()`; ela
  entra automaticamente na tabela de ablação.

**Confiança por raridade.** O mesmo registro da Receita vale menos quando o telefone aparece
em muitas raízes de CNPJ (contador, central) ou quando o cadastro não está ativo. A avaliação
sintética mediu o efeito: F1 de 0,796 para 0,865, com metade do desvio.

Detalhes do funcionamento no Colab e no GitHub: `docs/ARQUITETURA-COLAB.html`.