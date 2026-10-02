# Configuração

O F.I.O. funciona sem configurar nada. Esta página lista o que **pode** ser ajustado.

## Onde ficam os dados: `FIO_HOME`

| Sistema | Padrão |
|---|---|
| Linux / macOS | `~/.fio` |
| Windows | `C:\Users\<você>\.fio` |

Mude com a variável de ambiente `FIO_HOME`. No Colab ela aponta para `/content/fio-runtime` (efêmero). A estrutura está em [primeiros passos](primeiros-passos.md#5-onde-ficam-os-arquivos).

> Os dados de um caso são **sensíveis** (LGPD). Se `FIO_HOME` fica numa pasta sincronizada (Drive, Dropbox, OneDrive), os casos vão junto. Prefira um disco cifrado.

## Variáveis de ambiente

| Variável | Para quê |
|---|---|
| `FIO_HOME` | pasta de dados (casos, índices, plugins, config) |
| `FIO_INDICE_CNPJ` | caminho do índice reverso do CNPJ; sem ela, usa `FIO_HOME/cnpj.sqlite` se existir |
| `FIO_INDICE_EXPOSICAO` | caminho do índice de exposição por hash (`fio exposicao`) |
| `FIO_HIBP_API_KEY` | chave do Have I Been Pwned (coletor `hibp`) |
| `FIO_RECEITA_BASE` | URL base dos Dados Abertos do CNPJ, se a Receita mudar o endereço |
| `FIO_RECEITA_MES` | mês fixo do índice (`AAAA-MM`), pula a listagem raiz |
| `FIO_HOSTS_PERMITIDOS` | sufixos de `Host` aceitos pela bancada além de `localhost` (separados por vírgula); o token continua obrigatório |
| `FIO_CA_BUNDLE` | bundle de certificados da CA, para redes com inspeção TLS (proxy corporativo). Também aceita `REQUESTS_CA_BUNDLE` |
| `FIO_SEM_E2E` | `1` pula os testes de navegador (só para quem desenvolve) |

## `config.json`

`FIO_HOME/config.json` guarda chaves e caminhos. **As variáveis de ambiente têm prioridade.**

```json
{
  "transparencia_api_key": "SUA-CHAVE-DO-PORTAL-DA-TRANSPARENCIA",
  "hibp_api_key": "SUA-CHAVE-DO-HIBP",
  "indice_cnpj": "/dados/cnpj-mg.sqlite",
  "indice_exposicao": "/dados/exposicao.sqlite",
  "querido_diario_territorios": ["3106200"]
}
```

| Chave | Efeito |
|---|---|
| `transparencia_api_key` | habilita o coletor `transparencia` (CEIS/CNEP). Chave gratuita no Portal da Transparência |
| `hibp_api_key` | habilita o coletor `hibp` |
| `indice_cnpj` | índice do CNPJ |
| `indice_exposicao` | índice de exposição por hash |
| `querido_diario_territorios` | restringe o Querido Diário a municípios (códigos IBGE) |

Coletor que precisa de chave e não a encontra **não falha**: é pulado, com `coletor.pulado` no ledger. `fio diagnostico` mostra `sem chave` e qual chave configurar.

> Não versione o `config.json`. Ele contém segredos.

## Índice da Receita

Veja [índice do CNPJ](indice-cnpj.md). Resumo:

```bash
fio indice baixar --uf MG                  # baixa o mês mais recente, filtra MG, salva em FIO_HOME/cnpj.sqlite
fio indice baixar --uf MG,SP --mes 2026-08 --tmp /disco/grande
fio indice status
```

## Cache HTTP

Cada caso guarda `cache.sqlite` com as respostas das fontes. O **TTL padrão é de 24 horas**: a segunda execução do caso reproduz o mesmo material e é educada com a fonte. Intervalo entre requisições ao mesmo host: **1,5 s** (`--intervalo`).

## Plugins

Solte um `.py` em `FIO_HOME/plugins/`. `fio lab plugins` lista; cada plugin tem o **SHA-256** registrado em todo experimento que o usou. Modelo em `exemplos/plugin_exemplo.py`. Veja [laudo e plugins](laudo-e-plugins.md).

## Receitas próprias

JSON em `FIO_HOME/receitas/*.json` (modelo em `exemplos/receita_exemplo.json`). Veja [fontes](fontes.md).

## Proxy e rede corporativa

O F.I.O. usa `urllib` e respeita `HTTPS_PROXY`/`HTTP_PROXY`. Com inspeção TLS (certificado da empresa), aponte `FIO_CA_BUNDLE` para o `.pem` da CA. **Nunca desative a verificação TLS.**

## Desenvolvimento

```bash
python -m unittest discover -s testes -v      # suíte
python tools/gerar_notebook.py --checar       # caderno do Colab em dia?
python tools/gerar_referencia_cli.py --checar # referência da CLI em dia?
python tools/gerar_midia.py                   # regenera docs/img/demo.gif (precisa de Playwright e ffmpeg)
ruff check fio testes tools                   # lint (E9, F)
```
