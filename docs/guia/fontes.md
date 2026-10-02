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

## Detalhe por coletor

Gerado a partir do código (`fio coletores` imprime o mesmo). A **reserva** é o limite conhecido da fonte e vai para o relatório.

### `cnpj-api`

- **O que faz:** CNPJ -> razao social, telefones, e-mail e quadro societario via BrasilAPI (espelho da Receita Federal).
- **Alvos aceitos:** cnpj, organizacao
- **Grau Admiralty:** B2 · **Modo:** rede · **Estágio:** enriquecimento
- **Reserva:** BrasilAPI e um espelho de conveniencia. Para uso em peca formal, confirme na consulta oficial da Receita e guarde o comprovante.

### `cnpj-reverso`

- **O que faz:** Telefone -> cadastro de CNPJ usando indice local dos Dados Abertos da Receita Federal; expande para socios e demais estabelecimentos da mesma empresa.
- **Alvos aceitos:** telefone, email
- **Grau Admiralty:** A2 · **Modo:** offline · **Estágio:** enriquecimento
- **Reserva:** Alcanca apenas linhas declaradas por pessoa juridica a Receita. Telefone pessoal de pessoa fisica nao consta -- e nao deveria. O dado e autodeclarado pela empresa e pode estar desatualizado: confira a data da base.

### `crtsh`

- **O que faz:** Subdominios e nomes irmaos de um dominio, a partir dos logs publicos de Certificate Transparency (crt.sh).
- **Alvos aceitos:** dominio
- **Grau Admiralty:** B3 · **Modo:** rede · **Estágio:** enriquecimento
- **Reserva:** Certificado emitido prova que alguem controlava o nome na emissao, nao que ainda controla nem quem e. Certificados compartilhados (CDN, hospedagem) listam dominios de terceiros sem relacao entre si: confira o emissor e as datas antes de tratar dois nomes como do mesmo operador.

### `dados-abertos`

- **O que faz:** Consulta offline todos os indices de dados abertos construidos por receita (CNES, Cadastur, TSE, faixas...).
- **Alvos aceitos:** telefone, email, cnpj, organizacao
- **Grau Admiralty:** B2 · **Modo:** offline · **Estágio:** enriquecimento
- **Só Brasil**
- **Reserva:** Cada indice herda a reserva da sua receita (ver tabela de fontes do relatorio). Registro autodeclarado envelhece: confira a data de construcao do indice.

### `exposicao-local`

- **O que faz:** Checa o identificador contra um indice local de hashes de corpus que a organizacao ja detem legitimamente.
- **Alvos aceitos:** telefone, email
- **Grau Admiralty:** B2 · **Modo:** offline · **Estágio:** enriquecimento
- **Exige configuração:** `indice_exposicao` (veja [configuração](configuracao.md))
- **Reserva:** So responde 'consta' ou 'nao consta'. Por construcao nao devolve o registro correspondente: o indice guarda apenas hashes, nunca o dado em claro.

### `extrator`

- **O que faz:** Varre um documento ja em posse do caso e extrai telefones e e-mails, ligando-os a origem.
- **Alvos aceitos:** documento
- **Grau Admiralty:** B2 · **Modo:** offline · **Estágio:** ingestao
- **Reserva:** A confianca do vinculo nao passa da confianca do documento de origem: um PDF encaminhado por terceiro e material de segunda mao ate que a origem seja verificada.

### `hibp`

- **O que faz:** E-mail -> incidentes catalogados no Have I Been Pwned.
- **Alvos aceitos:** email
- **Grau Admiralty:** B2 · **Modo:** rede · **Estágio:** enriquecimento
- **Exige configuração:** `hibp_api_key` (veja [configuração](configuracao.md))
- **Reserva:** Informa que o endereco esteve em um incidente, nao que a senha siga valida nem que a conta seja da pessoa investigada. O HIBP indexa e-mail; numero de telefone so aparece como classe de dado exposta no incidente.

### `nucleo`

- **O que faz:** Plano de numeracao: valida, classifica, situa geograficamente e identifica o bloco de numeracao.
- **Alvos aceitos:** telefone
- **Grau Admiralty:** A2 · **Modo:** offline · **Estágio:** normalizacao
- **Reserva:** O DDD indica a area de habilitacao original da linha, nao onde a pessoa esta. Com portabilidade e numero movel, a geografia e pista de origem, nunca de localizacao atual.

### `querido-diario`

- **O que faz:** Busca o identificador no texto integral dos diarios oficiais municipais indexados pelo Querido Diario.
- **Alvos aceitos:** telefone, cnpj, organizacao, pessoa, email
- **Grau Admiralty:** A3 · **Modo:** rede · **Estágio:** enriquecimento
- **Só Brasil**
- **Reserva:** O diario oficial e fonte autoritativa de que o texto foi publicado, nao de que o numero pertence a quem aparece ao lado dele: edital de citacao lista varios particulares no mesmo paragrafo. A cobertura e parcial -- nem todo municipio esta indexado, e a extracao de texto de PDF tem ruido.

### `rdap`

- **O que faz:** Dominio -> titular, contatos e telefones via RDAP (registro.br para .br, rdap.org para gTLD).
- **Alvos aceitos:** dominio
- **Grau Admiralty:** A2 · **Modo:** rede · **Estágio:** enriquecimento
- **Reserva:** Desde a LGPD e o GDPR, a maioria dos registros retorna contatos redigidos. Quando o telefone aparece, costuma ser de pessoa juridica ou do provedor -- confira o handle antes de atribuir a uma pessoa.

### `transparencia`

- **O que faz:** CNPJ -> sancoes no CEIS (inidoneas/suspensas) e no CNEP (punidas pela Lei Anticorrupcao), via Portal da Transparencia/CGU.
- **Alvos aceitos:** cnpj, organizacao
- **Grau Admiralty:** A1 · **Modo:** rede · **Estágio:** enriquecimento
- **Exige configuração:** `transparencia_api_key` (veja [configuração](configuracao.md))
- **Só Brasil**
- **Reserva:** Registra sancao aplicada, com orgao e periodo; nao informa o merito nem se a sancao foi suspensa judicialmente depois. Confira a vigencia na data do relatorio.

### `viacep`

- **O que faz:** CEP -> logradouro, municipio (codigo IBGE) e DDD da localidade, via ViaCEP.
- **Alvos aceitos:** cep
- **Grau Admiralty:** B2 · **Modo:** rede · **Estágio:** enriquecimento
- **Só Brasil**
- **Reserva:** O DDD devolvido e o da localidade do CEP; ele alimenta a checagem de coerencia geografica, mas CEP e telefone podem legitimamente divergir (filial, portabilidade, linha movel).

### `wayback`

- **O que faz:** Primeiro registro de um dominio ou URL no Internet Archive: idade real da presenca publica.
- **Alvos aceitos:** dominio, url
- **Grau Admiralty:** B2 · **Modo:** rede · **Estágio:** enriquecimento
- **Reserva:** O Wayback so conhece o que foi arquivado: ausencia de captura nao prova que o endereco e novo, e a primeira captura pode ser bem posterior ao primeiro uso.

### `web`

- **O que faz:** Gera as consultas em todas as grafias do identificador e recolhe as paginas publicas que o mencionam.
- **Alvos aceitos:** telefone, email, pessoa, organizacao, dominio
- **Grau Admiralty:** C3 · **Modo:** rede · **Estágio:** enriquecimento
- **Reserva:** Indice publico e material de terceiros: a pagina pode estar desatualizada, ser copia de outra ou ter sido plantada. Trate cada URL como afirmacao a verificar, nunca como fato. Numero em anuncio de classificado costuma ser de intermediario, nao do anunciante.
