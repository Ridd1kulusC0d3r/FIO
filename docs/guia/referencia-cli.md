# Referência da linha de comando

> Gerada automaticamente a partir do `argparse` da CLI por
> `tools/gerar_referencia_cli.py`. Não edite à mão: o CI confere que ela
> bate com `fio --help`. Para exemplos de uso, veja o
> [guia de primeiros passos](primeiros-passos.md) e as
> [receitas de uso](receitas-de-uso.md).

Forma geral: `fio [--ator NOME] <comando> [subcomando] [opções]`.
`--ator` identifica quem opera e vai para o ledger. Sem ele, o F.I.O. usa o
usuário do sistema. Todos os dados do caso ficam em `FIO_HOME`
(padrão `~/.fio`).

## Índice

- [`fio caso`](#fio-caso) — abrir, listar e inspecionar casos
- [`fio alvo`](#fio-alvo) — incluir alvo primario no caso
- [`fio buscar`](#fio-buscar) — busca em um passo: abre o caso, consulta as fontes e resume
- [`fio investigar`](#fio-investigar) — rodar os coletores e pivotar
- [`fio grafo`](#fio-grafo) — exportar o grafo
- [`fio clusters`](#fio-clusters) — agrupamentos e pontes entre alvos
- [`fio tabela`](#fio-tabela) — tabela de correlacao
- [`fio relatorio`](#fio-relatorio) — gerar relatorio final
- [`fio ledger`](#fio-ledger) — cadeia de custodia
- [`fio numero`](#fio-numero) — analise offline avulsa de um numero
- [`fio dorks`](#fio-dorks) — gerar consultas para busca manual
- [`fio coletores`](#fio-coletores) — listar coletores e suas reservas
- [`fio indice`](#fio-indice) — indice reverso dos Dados Abertos do CNPJ
- [`fio exposicao`](#fio-exposicao) — indexar por hash um corpus ja detido legitimamente
- [`fio bases`](#fio-bases) — bases legais aceitas
- [`fio manifesto`](#fio-manifesto) — SHA-256 de cada peca do caso, amarrado ao ledger
- [`fio claims`](#fio-claims) — conclusoes do caso, cada uma com a evidencia que a sustenta
- [`fio diagnostico`](#fio-diagnostico) — testar conexao com as fontes online
- [`fio demo`](#fio-demo) — montar o caso de demonstracao (ficticio, offline)
- [`fio doc`](#fio-doc) — validar/estruturar documentos BR ou extrair de texto
- [`fio receita`](#fio-receita) — indexador universal de dados abertos
- [`fio quesito`](#fio-quesito) — quesitos do laudo
- [`fio caso-editar`](#fio-caso-editar) — metadados do laudo (solicitante, referencia...)
- [`fio laudo`](#fio-laudo) — gerar laudo tecnico ou RELINT
- [`fio lab`](#fio-lab) — pipeline, experimentos, avaliacao e bancada web

## `fio caso`

Abrir, listar e inspecionar casos.

```text
fio caso {novo,listar,ver} ...
```

### `fio caso novo`

```text
fio caso novo --id ID --titulo TITULO --base-legal BASE_LEGAL --finalidade FINALIDADE --responsavel RESPONSAVEL [--escopo ESCOPO ...] [--dias DIAS]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `--id` `ID` | sim |  |
| `--titulo` `TITULO` | sim |  |
| `--base-legal` `BASE_LEGAL` | sim | (valores: `contrato-pentest`, `judicial`, `lgpd-4-iii`, `lgpd-7-i`, `lgpd-7-ii`, `lgpd-7-ix`, `lgpd-7-v`, `lgpd-7-vi`, `pesquisa-academica`, `resposta-incidente`) |
| `--finalidade` `FINALIDADE` | sim | descricao especifica: delimita o que pode ser coletado |
| `--responsavel` `RESPONSAVEL` | sim |  |
| `--escopo` `ESCOPO` | não | identificadores autorizados |
| `--dias` `DIAS` | não | validade do escopo |

### `fio caso listar`

```text
fio caso listar
```

### `fio caso ver`

```text
fio caso ver --caso CASO
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `--caso` `CASO` | sim |  |

## `fio alvo`

Incluir alvo primario no caso.

```text
fio alvo --caso CASO --tipo TIPO --valor VALOR [--ddd DDD]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `--caso` `CASO` | sim |  |
| `--tipo` `TIPO` | sim | (valores: `telefone`, `email`, `dominio`, `cnpj`, `pessoa`, `organizacao`, `documento`) |
| `--valor` `VALOR` | sim |  |
| `--ddd` `DDD` | não | DDD assumido para numero sem DDD |

## `fio buscar`

Busca em um passo: abre o caso, consulta as fontes e resume.

```text
fio buscar valor --base-legal BASE_LEGAL [--finalidade FINALIDADE] [--ddd DDD] [--dias DIAS] [--completo] [--orcamento SEGUNDOS] [--offline] [-v]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `valor` (posicional) | sim | telefone, CNPJ, e-mail, dominio ou CEP |
| `--base-legal` `BASE_LEGAL` | sim | base legal (ver `fio bases`) |
| `--finalidade` `FINALIDADE` | não | finalidade da consulta (ha um texto padrao) |
| `--ddd` `DDD` | não | DDD assumido para telefone sem DDD |
| `--dias` `DIAS` | não | validade do escopo (padrao 30) (padrão: `30`) |
| `--completo` | não | busca completa, sem orcamento de tempo |
| `--orcamento` `SEGUNDOS` | não | limite de tempo da busca rapida (padrao 45) (padrão: `45.0`) |
| `--offline` | não | so fontes locais |
| `-v`, `--verboso` | não |  |

## `fio investigar`

Rodar os coletores e pivotar.

```text
fio investigar --caso CASO [--coletores COLETORES] [--profundidade PROFUNDIDADE] [--offline] [--paralelo PARALELO] [--orcamento SEGUNDOS] [--rapido] [--intervalo INTERVALO] [--expandir-escopo] [-v]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `--caso` `CASO` | sim |  |
| `--coletores` `COLETORES` | não | lista separada por virgula |
| `--profundidade` `PROFUNDIDADE` | não | (padrão: `1`) |
| `--offline` | não | so coletores locais |
| `--paralelo` `PARALELO` | não | coletores de rede simultaneos por alvo (1 = em sequencia) (padrão: `4`) |
| `--orcamento` `SEGUNDOS` | não | limite de tempo de coleta; esgotado, nao abre novas consultas |
| `--rapido` | não | modo leve: fontes lentas fazem menos consultas (ex.: 3 recortes de busca) |
| `--intervalo` `INTERVALO` | não | segundos entre requisicoes ao mesmo host (padrão: `1.5`) |
| `--expandir-escopo` | não | autoriza pivotar sobre entidades derivadas da coleta; cada inclusao fica registrada no ledger |
| `-v`, `--verboso` | não |  |

## `fio grafo`

Exportar o grafo.

```text
fio grafo --caso CASO [--formato FORMATO]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `--caso` `CASO` | sim |  |
| `--formato` `FORMATO` | não | (valores: `json`, `csv`; padrão: `json`) |

## `fio clusters`

Agrupamentos e pontes entre alvos.

```text
fio clusters --caso CASO [--json]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `--caso` `CASO` | sim |  |
| `--json` | não |  |

## `fio tabela`

Tabela de correlacao.

```text
fio tabela --caso CASO [--csv CSV] [--limite LIMITE]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `--caso` `CASO` | sim |  |
| `--csv` `CSV` | não | grava em arquivo em vez da tela |
| `--limite` `LIMITE` | não | (padrão: `40`) |

## `fio relatorio`

Gerar relatorio final.

```text
fio relatorio --caso CASO --saida SAIDA [--markdown MARKDOWN] [--csv CSV] [--manifesto]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `--caso` `CASO` | sim |  |
| `--saida` `SAIDA` | sim | arquivo .html |
| `--markdown` `MARKDOWN` | não | tambem gravar .md |
| `--csv` `CSV` | não | tambem gravar vinculos em .csv |
| `--manifesto` | não | gravar o manifesto SHA-256 do caso e dos relatorios gerados |

## `fio ledger`

Cadeia de custodia.

```text
fio ledger acao --caso CASO
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `acao` (posicional) | sim | (valores: `listar`, `verificar`) |
| `--caso` `CASO` | sim |  |

## `fio numero`

Analise offline avulsa de um numero.

```text
fio numero valor [--ddd DDD] [--json]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `valor` (posicional) | sim |  |
| `--ddd` `DDD` | não |  |
| `--json` | não |  |

## `fio dorks`

Gerar consultas para busca manual.

```text
fio dorks [--tipo TIPO] --valor VALOR [--urls]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `--tipo` `TIPO` | não | (valores: `telefone`, `email`, `pessoa`, `organizacao`, `dominio`; padrão: `telefone`) |
| `--valor` `VALOR` | sim |  |
| `--urls` | não |  |

## `fio coletores`

Listar coletores e suas reservas.

```text
fio coletores
```

## `fio indice`

Indice reverso dos Dados Abertos do CNPJ.

```text
fio indice acao [--uf UF] [--mes MES] [--base BASE] [--origem ORIGEM] [--saida SAIDA] [--tmp TMP] [--manter-zips] [--leve] [--pronto] [--de URL] [--para ARQUIVO]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `acao` (posicional) | sim | (valores: `baixar`, `construir`, `status`, `exportar`) |
| `--uf` `UF` | não | filtrar por UF, ex.: MG ou MG,SP; reduz o indice final e a RAM, nao o trafego da Receita |
| `--mes` `MES` | não | AAAA-MM; padrao: o mais recente publicado |
| `--base` `BASE` | não | URL base da Receita, se o endereco mudar |
| `--origem` `ORIGEM` | não | diretorio com os CSV da Receita Federal |
| `--saida` `SAIDA` | não | arquivo sqlite de destino |
| `--tmp` `TMP` | não | pasta temporaria dos ZIPs baixados |
| `--manter-zips` | não | nao apagar os ZIPs depois de processar |
| `--leve` | não | indice enxuto: so estabelecimentos com telefone/e-mail (ou matriz), sem endereco completo nem CNAE |
| `--pronto` | não | baixar: em vez de montar pela Receita, baixa o indice ja pronto (segundos; precisa de --uf) |
| `--de` `URL` | não | baixar --pronto: URL base dos arquivos (padrao: Release do repositorio) |
| `--para` `ARQUIVO` | não | exportar: arquivo .sqlite.xz de saida (padrao: cnpj-UF.sqlite.xz) |

## `fio exposicao`

Indexar por hash um corpus ja detido legitimamente.

```text
fio exposicao --origem ORIGEM --saida SAIDA [--id ID] [--titulo TITULO] [--descricao DESCRICAO]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `--origem` `ORIGEM` | sim |  |
| `--saida` `SAIDA` | sim |  |
| `--id` `ID` | não | (padrão: `corpus`) |
| `--titulo` `TITULO` | não | (padrão: `corpus interno`) |
| `--descricao` `DESCRICAO` | não | (padrão: ``) |

## `fio bases`

Bases legais aceitas.

```text
fio bases
```

## `fio manifesto`

SHA-256 de cada peca do caso, amarrado ao ledger.

```text
fio manifesto acao --caso CASO
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `acao` (posicional) | sim | (valores: `gerar`, `verificar`) |
| `--caso` `CASO` | sim |  |

## `fio claims`

Conclusoes do caso, cada uma com a evidencia que a sustenta.

```text
fio claims --caso CASO [--confianca-minima CONFIANCA_MINIMA] [--json]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `--caso` `CASO` | sim |  |
| `--confianca-minima` `CONFIANCA_MINIMA` | não | (padrão: `0.5`) |
| `--json` | não |  |

## `fio diagnostico`

Testar conexao com as fontes online.

```text
fio diagnostico
```

## `fio demo`

Montar o caso de demonstracao (ficticio, offline).

```text
fio demo [--recriar] [--abrir]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `--recriar` | não |  |
| `--abrir` | não | abrir a bancada em seguida |

## `fio doc`

Validar/estruturar documentos BR ou extrair de texto.

```text
fio doc tipo valor
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `tipo` (posicional) | sim | (valores: `cpf`, `cpf-parcial`, `cnpj`, `cep`, `placa`, `titulo`, `pis`, `renavam`, `boleto`, `pix-evp`, `cnh`, `cns`, `extrair`) |
| `valor` (posicional) | sim | documento, ou arquivo/texto para 'extrair' |

## `fio receita`

Indexador universal de dados abertos.

```text
fio receita acao [--id ID] [--origem ORIGEM]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `acao` (posicional) | sim | (valores: `listar`, `construir`, `status`) |
| `--id` `ID` | não |  |
| `--origem` `ORIGEM` | não |  |

## `fio quesito`

Quesitos do laudo.

```text
fio quesito acao --caso CASO [--texto TEXTO] [--n N] [--entidades ENTIDADES ...]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `acao` (posicional) | sim | (valores: `add`, `responder`, `listar`) |
| `--caso` `CASO` | sim |  |
| `--texto` `TEXTO` | não | (padrão: ``) |
| `--n` `N` | não |  |
| `--entidades` `ENTIDADES` | não | ids de entidade (tipo:valor) de suporte |

## `fio caso-editar`

Metadados do laudo (solicitante, referencia...).

```text
fio caso-editar --caso CASO [--solicitante SOLICITANTE] [--referencia REFERENCIA] [--registro-profissional REGISTRO_PROFISSIONAL] [--conclusao CONCLUSAO] [--classificacao CLASSIFICACAO]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `--caso` `CASO` | sim |  |
| `--solicitante` `SOLICITANTE` | não |  |
| `--referencia` `REFERENCIA` | não |  |
| `--registro-profissional` `REGISTRO_PROFISSIONAL` | não |  |
| `--conclusao` `CONCLUSAO` | não |  |
| `--classificacao` `CLASSIFICACAO` | não |  |

## `fio laudo`

Gerar laudo tecnico ou RELINT.

```text
fio laudo --caso CASO --saida SAIDA [--modelo MODELO]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `--caso` `CASO` | sim |  |
| `--saida` `SAIDA` | sim |  |
| `--modelo` `MODELO` | não | (valores: `laudo`, `relint`; padrão: `laudo`) |

## `fio lab`

Pipeline, experimentos, avaliacao e bancada web.

```text
fio lab acao [--indice INDICE] [--municipio MUNICIPIO] [--max-raizes MAX_RAIZES] [--caso CASO] [--coletores COLETORES] [--profundidade PROFUNDIDADE] [--offline] [--expandir-escopo] [--intervalo INTERVALO] [--paralelo PARALELO] [--orcamento SEGUNDOS] [--rapido] [--relatorio RELATORIO] [--laudo LAUDO] [--modelo MODELO] [--descricao DESCRICAO] [--a A] [--b B] [--semente SEMENTE] [--sementes SEMENTES] [--grupos GRUPOS] [--saida SAIDA] [--porta PORTA] [--sem-navegador] [--permitir-host PERMITIR_HOST] [-v]
```

| Opção | Obrigatória | Descrição |
|---|---|---|
| `acao` (posicional) | sim | (valores: `plugins`, `pipeline`, `experimentos`, `comparar`, `sintetico`, `avaliar`, `calibrar`, `bancada`, `benchmark-real`) |
| `--indice` `INDICE` | não | indice da Receita (benchmark-real) |
| `--municipio` `MUNICIPIO` | não | codigo do municipio na Receita (benchmark-real) |
| `--max-raizes` `MAX_RAIZES` | não | (padrão: `800`) |
| `--caso` `CASO` | não |  |
| `--coletores` `COLETORES` | não |  |
| `--profundidade` `PROFUNDIDADE` | não | (padrão: `1`) |
| `--offline` | não |  |
| `--expandir-escopo` | não |  |
| `--intervalo` `INTERVALO` | não | (padrão: `1.5`) |
| `--paralelo` `PARALELO` | não | pipeline: coletores de rede simultaneos por alvo (padrão: `4`) |
| `--orcamento` `SEGUNDOS` | não | pipeline: limite de tempo de coleta |
| `--rapido` | não | pipeline: modo leve (menos consultas por fonte) |
| `--relatorio` `RELATORIO` | não |  |
| `--laudo` `LAUDO` | não |  |
| `--modelo` `MODELO` | não | (valores: `laudo`, `relint`; padrão: `laudo`) |
| `--descricao` `DESCRICAO` | não |  |
| `--a` `A` | não |  |
| `--b` `B` | não |  |
| `--semente` `SEMENTE` | não | (padrão: `7`) |
| `--sementes` `SEMENTES` | não | (padrão: `1,2,3,4,5`) |
| `--grupos` `GRUPOS` | não | (padrão: `12`) |
| `--saida` `SAIDA` | não | (padrão: `./lab-saida`) |
| `--porta` `PORTA` | não | (padrão: `8765`) |
| `--sem-navegador` | não |  |
| `--permitir-host` `PERMITIR_HOST` | não | sufixos de Host aceitos alem de localhost (ex.: colab.googleusercontent.com); o token continua obrigatorio |
| `-v`, `--verboso` | não |  |
