# Receitas de uso

Cenários completos, do comando ao que ler no resultado. Todos assumem um caso aberto com base legal e escopo (veja [primeiros passos](primeiros-passos.md)). Os exemplos usam dados fictícios.

| # | Cenário | Ferramentas |
|---|---|---|
| 1 | [Um telefone apareceu numa cobrança suspeita](#1-um-telefone-apareceu-numa-cobrança-suspeita) | `numero`, `investigar`, `clusters` |
| 2 | [Estas empresas são do mesmo grupo?](#2-estas-empresas-são-do-mesmo-grupo) | índice da Receita, `tabela`, observações |
| 3 | [Achar uma rede de empresas de fachada](#3-achar-uma-rede-de-empresas-de-fachada) | `lote-de-registro`, `intermediarios` |
| 4 | [Extrair identificadores de uma ata, e-mail ou boleto](#4-extrair-identificadores-de-um-texto) | `doc extrair`, `doc boleto` |
| 5 | [Investigar um domínio suspeito](#5-investigar-um-domínio-suspeito) | `rdap`, `crtsh`, `wayback` |
| 6 | [Conferir se uma empresa tem sanção](#6-conferir-se-uma-empresa-tem-sanção) | `transparencia`, `querido-diario` |
| 7 | [Buscar na web só com consultas prontas (sem rede automática)](#7-buscar-na-web-sem-deixar-o-fio-consultar) | `dorks` |
| 8 | [Entregar um laudo ou RELINT](#8-entregar-um-laudo-ou-relint) | `quesito`, `laudo` |
| 9 | [Provar que nada mudou](#9-provar-que-nada-mudou) | `ledger`, `manifesto` |
| 10 | [Comparar duas execuções](#10-comparar-duas-execuções) | `lab pipeline`, `lab comparar` |
| 11 | [Indexar seus próprios dados abertos](#11-indexar-seus-próprios-dados-abertos) | `receita`, `exposicao` |

---

## 1. Um telefone apareceu numa cobrança suspeita

**Objetivo:** saber que empresas e pessoas declararam publicamente esse número.

```bash
# 1. entenda o número sem abrir caso nem tocar a rede
fio numero "(31) 98888-7777"
#   canonico: +5531988887777 · tipo: movel · regiao: MG / Belo Horizonte · bloco: 3198888
#   grafias: +5531988887777, 31988887777, (31) 98888-7777, 31 98888 7777, ...

# 2. abra o caso e o alvo
fio caso novo --id CASO-0001 --titulo "Cobrança suspeita" --base-legal lgpd-7-vi \
  --finalidade "instruir notificação extrajudicial sobre cobrança fraudulenta" \
  --responsavel "Seu Nome" --escopo "+5531988887777"
fio alvo --caso CASO-0001 --tipo telefone --valor "(31) 98888-7777"

# 3. investigue e analise (com o índice da Receita montado, veja a receita 2)
fio lab pipeline --caso CASO-0001 --profundidade 2 --expandir-escopo -v

# 4. leia
fio clusters --caso CASO-0001
fio tabela   --caso CASO-0001 --limite 20
```

**O que olhar:** a coluna de confiança e o nível; se o telefone é declarado por **uma** raiz de CNPJ (A2, forte) ou por muitas (A4/A5, provável intermediário); as observações de **incoerência geográfica** (DDD de uma UF, empresa em outra: filial? linha de terceiro?).

**O que não concluir:** que a empresa ligada ao número **é** quem cobrou. Confira a data do cadastro e a situação (baixada? o número pode ter sido reaproveitado).

---

## 2. Estas empresas são do mesmo grupo?

**Objetivo:** juntar CNPJs com evidência, sem juntar por coincidência.

Primeiro, o índice da Receita (uma vez; roda offline depois). Veja [índice do CNPJ](indice-cnpj.md):

```bash
fio indice baixar --uf MG                        # baixa o mês mais recente, filtra MG
fio indice status
```

Depois, coloque os identificadores das empresas (CNPJ, telefone ou e-mail) no escopo e investigue:

```bash
fio caso novo --id GRUPO-01 --titulo "Grupo econômico X" --base-legal lgpd-7-ix \
  --finalidade "apurar vínculo societário entre fornecedores para análise de risco contratual" \
  --responsavel "Seu Nome" --escopo 11222333000181 11222333000262 +553133334444
fio alvo --caso GRUPO-01 --tipo cnpj --valor 11222333000181
fio alvo --caso GRUPO-01 --tipo cnpj --valor 11222333000262
fio lab pipeline --caso GRUPO-01 --profundidade 2 --expandir-escopo
fio tabela --caso GRUPO-01 --limite 40
```

**Como o F.I.O. decide "mesmo grupo":** mesma **raiz** de CNPJ (matriz e filiais), **sócio em comum** (pessoa = nome + máscara do CPF), telefone ou e-mail de domínio próprio compartilhados. Cada tipo tem um peso diferente.

**O que olhar:** o caminho entre os alvos (`fio clusters`, seção de pontes) e o **elo mais fraco** dele. Se o único elo é um telefone de contabilidade, **não é grupo**.

**Atenção a:** sócio de mesmo nome e máscara de CPF diferente (homônimo, tratado como pessoas diferentes) e empresa em nome de parente (o vínculo existe no mundo, mas **não aparece** no cadastro; o F.I.O. não o inventa).

---

## 3. Achar uma rede de empresas de fachada

**Objetivo:** empresas formalmente independentes que se comportam como uma só.

O padrão que o F.I.O. procura: **raízes distintas**, **abertas na mesma janela de 30 dias**, **compartilhando** telefone, e-mail, CEP ou sócio.

```bash
fio lab pipeline --caso GRUPO-01 --profundidade 3 --expandir-escopo --descricao "rede de fachada"
fio clusters --caso GRUPO-01
```

As observações só existem depois do estágio de análise, que o `lab pipeline` roda (o `investigar` sozinho não). Procure no relatório (seção de observações) por `lote-de-registro` e `intermediario-provavel`:

| Combinação | Leitura |
|---|---|
| lote + **ponte sem sócio em comum** (gravidade `atenção`) | o que mais se parece com rede de fachada. Também pode ser serviço de abertura de empresas atendendo clientes de uma vez só |
| lote + **sócio em comum** (`info`) | mais provável: um grupo que se expandiu |
| ponte sem lote | contabilidade ou coworking atendendo clientes ao longo do tempo |

**Próximo passo fora do F.I.O.:** confrontar atividade (CNAE), capital, endereços e a quem pertence o telefone **antes** de concluir.

---

## 4. Extrair identificadores de um texto

**Objetivo:** tirar de uma ata, e-mail ou contrato todos os identificadores válidos.

```bash
fio doc extrair ata.txt                 # arquivo ou texto direto
fio doc cnpj 12.ABC.345/01DE-35         # CNPJ alfanumérico (IN RFB 2.229/2024)
fio doc cpf-parcial '***456789**'       # região fiscal a partir da máscara da Receita
fio doc placa ABC1234                   # → ABC1C34 (antiga ↔ Mercosul)
fio doc boleto 00191.23454 67890.123457 67890.123457 9 90000000012345
fio doc pix-evp 123e4567-e89b-42d3-a456-426614174000
```

O extrator valida o dígito verificador de cada documento: sequência de 11 dígitos que fecha o DV de CPF sai marcada **`[AMBIGUO]`** porque também pode ser telefone móvel com DDD, e a decisão é sua. Boleto: devolve banco emissor, valor e **as datas de vencimento possíveis** (o fator reiniciou em 22/02/2025). Detalhes em [documentos](documentos.md).

Para transformar o documento em alvos de um caso: `fio alvo --tipo documento --valor ata.txt`; o coletor `extrator` lê o arquivo e liga cada telefone e e-mail encontrado à origem.

---

## 5. Investigar um domínio suspeito

**Objetivo:** quem registrou, desde quando existe e que outros nomes compartilham a infraestrutura.

```bash
fio caso novo --id DOM-01 --titulo "Domínio de phishing" --base-legal resposta-incidente \
  --finalidade "investigar domínio usado em campanha contra clientes da empresa" \
  --responsavel "Seu Nome" --escopo exemplo-suspeito.com.br
fio alvo --caso DOM-01 --tipo dominio --valor exemplo-suspeito.com.br
fio investigar --caso DOM-01 --coletores rdap,crtsh,wayback --profundidade 1
fio tabela --caso DOM-01
```

| Coletor | Dá | Reserva principal |
|---|---|---|
| `rdap` (A2) | titular, contatos e telefones do registro | dado de registro pode estar protegido ou desatualizado |
| `crtsh` (B3) | nomes e subdomínios em certificados | certificado compartilhado (CDN) lista domínios sem relação |
| `wayback` (B2) | primeira captura conhecida | ausência de captura **não** prova que o domínio é novo |

**Idade importa:** domínio com primeira captura recente e certificado emitido na semana do ataque é um indício, não prova.

---

## 6. Conferir se uma empresa tem sanção

```bash
# chave gratuita do Portal da Transparência (CGU), uma vez:
#   echo '{"transparencia_api_key": "SUA-CHAVE"}' > ~/.fio/config.json
fio investigar --caso GRUPO-01 --coletores transparencia,querido-diario,cnpj-api
```

- `transparencia` (A1): CEIS (inidôneas/suspensas) e CNEP (Lei Anticorrupção).
- `querido-diario` (A3): o CNPJ ou nome no texto integral de diários oficiais municipais (licitação, contrato, credenciamento).
- O analisador `alerta-sancao` propaga a sanção ao **componente** do alvo, com gravidade `alta` e a ressalva: *proximidade no grafo não transfere responsabilidade, verifique o caminho*.

---

## 7. Buscar na web sem deixar o F.I.O. consultar

Quando você prefere pesquisar à mão (ou o ambiente não tem rede liberada):

```bash
fio dorks --tipo telefone --valor "(31) 98888-7777" --urls
```

Gera as consultas **em todas as grafias** do número (um número publicado em anúncio aparece de **uma** grafia entre muitas), em 10 recortes (institucional, LinkedIn, classificados, jurídico, oficial, documentos, código…) e a URL pronta para Google, Bing, DuckDuckGo e Yandex. Não faz nenhuma requisição.

---

## 8. Entregar um laudo ou RELINT

```bash
fio caso-editar --caso CASO-0001 --solicitante "Jurídico" --referencia "Proc. 0001234-..." \
  --registro-profissional "CREA/CRC/OAB..."
fio quesito add --caso CASO-0001 --texto "As linhas pertencem ao mesmo grupo?" \
  --entidades "telefone:+5531988887777" "organizacao:11222333000181"
fio lab pipeline --caso CASO-0001 --profundidade 2 --expandir-escopo --laudo laudo.html
fio quesito responder --caso CASO-0001 --n 1 --texto "Sim, com confiança alta, com base em ..."
fio laudo --caso CASO-0001 --modelo relint --saida relint.html   # ou --modelo laudo
fio manifesto gerar --caso CASO-0001
```

O laudo traz preâmbulo, quesitos, material, metodologia (ISO/IEC 27037, escala Admiralty, reprodutibilidade), exames, **cadeia de custódia mapeada nas 10 etapas do art. 158-B do CPP**, respostas, limitações e conclusão graduada. Veja [laudo e plugins](laudo-e-plugins.md).

---

## 9. Provar que nada mudou

```bash
fio ledger verificar    --caso CASO-0001     # cadeia de hashes e artefatos brutos
fio manifesto gerar     --caso CASO-0001     # sela as peças atuais
# ... meses depois, no outro computador:
fio manifesto verificar --caso CASO-0001
```

Saídas possíveis: `manifesto integro`, ou a lista do que mudou (`peça alterada: grafo.json`, `o próprio manifesto foi alterado`, `ledger reescrito`). O ledger pode crescer depois do manifesto (novas coletas) sem invalidá-lo.

Para provar **quando**: ancore o hash do último registro do ledger num serviço RFC 3161. O F.I.O. não faz carimbo de tempo por você.

---

## 10. Comparar duas execuções

```bash
fio lab pipeline --caso CASO-0001 --descricao "março"
# ... o índice da Receita é atualizado em abril ...
fio lab pipeline --caso CASO-0001 --descricao "abril"
fio lab experimentos --caso CASO-0001
fio lab comparar --caso CASO-0001 --a EXP-20260301-... --b EXP-20260401-...
```

`comparar` informa se o resultado é o **mesmo** (hash do grafo), se o **código** é o mesmo, quais **fontes** mudaram, entidades e vínculos novos/removidos e vínculos cuja **confiança mudou** em 0,05 ou mais.

---

## 11. Indexar seus próprios dados abertos

```bash
fio receita listar                                             # cnes, cadastur, tse-despesas, anatel-faixas, generica
fio receita construir --id cnes --origem cnes_estabelecimentos.zip
fio receita construir --id generica --origem qualquer_planilha.csv   # detecta colunas de telefone, e-mail, CNPJ, CEP...
fio receita status
```

Receitas próprias ficam em `~/.fio/receitas/*.json` (modelo em `exemplos/receita_exemplo.json`). Cada índice guarda o SHA-256 do arquivo de origem, que entra no experimento como *versão da fonte*.

Se a sua organização **já detém legitimamente** um corpus (o próprio vazamento que sofreu, por exemplo), `fio exposicao` o indexa **só por hash**, para consultar sem reintroduzir o dado pessoal em claro. Consultar conteúdo de vazamento de terceiros para obter cadastro **não está implementado e não será**.
