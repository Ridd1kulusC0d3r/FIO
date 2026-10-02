# Fontes e coletores

Cada coletor declara grau Admiralty, se precisa de rede e a **reserva** (o limite conhecido da fonte), que vai para o relatório.

| Coletor | Fonte | Modo | Grau |
|---|---|---|---|
| `nucleo` | plano de numeração (tabela local) | offline | A2 |
| `extrator` | documento do caso: telefones, e-mails, CPF/CNPJ/CEP/placa | offline | B2 |
| `cnpj-reverso` | **Dados Abertos do CNPJ** (Receita), índice local | offline | A2 |
| `dados-abertos` | todos os índices construídos por receita | offline | por receita |
| `cnpj-api` | BrasilAPI (espelho da Receita) | rede | B2 |
| `querido-diario` | texto integral de diários oficiais municipais | rede | A3 |
| `viacep` | CEP → logradouro, IBGE, DDD da localidade | rede | B2 |
| `transparencia` | CEIS e CNEP (CGU); requer chave gratuita | rede | A1 |
| `rdap` | registro.br e RDAP genérico | rede | A2 |
| `web` | consultas em todas as grafias + índice público | rede | C3 |
| `crtsh` | Certificate Transparency (crt.sh): nomes e subdomínios de um domínio | rede | B3 |
| `wayback` | Internet Archive: primeira captura de um domínio ou URL | rede | B2 |
| `hibp` | Have I Been Pwned (e-mail); requer chave | rede | B2 |
| `exposicao-local` | índice por hash de corpus já detido | offline | B2 |

### Receitas de dados abertos

```bash
fio receita listar
fio receita construir --id cnes --origem cnes_estabelecimentos.zip
fio receita construir --id generica --origem qualquer_planilha.csv
fio receita status
```

A receita `generica` detecta sozinha as colunas de telefone, e-mail, CNPJ,
CEP, nome, UF e município. Receitas próprias vão em `~/.fio/receitas/*.json`
(veja `exemplos/receita_exemplo.json`). Cada índice guarda o SHA-256 do
arquivo de origem, que entra no registro do experimento como "versão da
fonte".

**Faixas de numeração:** a Anatel não publica em dados abertos a destinação
de faixas por prestadora. Hoje o nSAPN é operado pela ABR Telecom com acesso
credenciado. A receita `anatel-faixas` existe para quando você tiver o
arquivo por via legítima e, mesmo assim, indica só a prestadora **original**,
sem considerar portabilidade.

## Baseline diferencial

Antes de aceitar uma resposta, o coletor `web` consulta também um valor que **não pode existir** e compara as duas páginas (Jaccard de *shingles* de palavras, insensível a números e datas). Resposta real ≥ 90% igual à do valor impossível é página padrão, bloqueio ou "sem resultados" e é descartada, com o motivo no ledger (`coleta.baseline`). Qualquer coletor novo pode usar `ClienteHTTP.get_diferencial`.

## Contrato das fontes (canários)

`fio/fontes.json` declara, para cada fonte online, um alvo neutro e um **canário**: o campo que a resposta deve ter. `fio diagnostico` consulta todas e distingue *fonte fora do ar* de *contrato quebrado* (a fonte respondeu 200, mas mudou de formato e o coletor correspondente vai quebrar). O workflow `testes` roda isso toda segunda-feira.
