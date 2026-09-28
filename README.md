# F.I.O. Lab — edição BR

[![testes](https://github.com/Ridd1kulusC0d3r/FIO/actions/workflows/testes.yml/badge.svg)](https://github.com/Ridd1kulusC0d3r/FIO/actions/workflows/testes.yml)
[![Abrir no Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Ridd1kulusC0d3r/FIO/blob/main/colab/FIO_Lab_Colab.ipynb)
![Python 3.10–3.14](https://img.shields.io/badge/python-3.10%E2%80%933.14-3776AB)
![só biblioteca padrão](https://img.shields.io/badge/depend%C3%AAncias-nenhuma-0E7C6B)
[![licença MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-555)](LICENSE)

**Fontes, Identificadores e Origens.** Laboratório de OSINT, em Python, para análise de
vínculos a partir de números de telefone e registros públicos brasileiros. Usa só a
biblioteca padrão: nenhuma dependência externa, nem na bancada web.

## Três jeitos de usar

| Jeito | Para quem | Como |
|---|---|---|
| **Google Colab** | quem quer testar sem instalar | botão *Abrir no Colab* acima › *Ambiente de execução › Executar tudo* |
| **Dois cliques** | leigos, no próprio computador | baixe a última [Release](https://github.com/Ridd1kulusC0d3r/FIO/releases), descompacte e abra o lançador do seu sistema ([COMECE-AQUI.md](COMECE-AQUI.md)) |
| **Linha de comando** | técnicos | `pip install git+https://github.com/Ridd1kulusC0d3r/FIO` e depois `fio --help` |

Manual ilustrado: [docs/MANUAL.html](https://Ridd1kulusC0d3r.github.io/FIO/) (publicado no GitHub Pages).
Arquitetura no Colab: [docs/ARQUITETURA-COLAB.html](docs/ARQUITETURA-COLAB.html).
Uso responsável: [USO-RESPONSAVEL.md](USO-RESPONSAVEL.md).

> *Estes números pertencem à mesma pessoa, à mesma empresa ou ao mesmo
> grupo? Com que confiança? E com que frequência essa resposta erra?*

### Publicar o seu repositório

```bash
python tools/configurar_repositorio.py seu-usuario/fio-lab   # troca os marcadores e regenera o caderno
git init && git add . && git commit -m "F.I.O. Lab"
git remote add origin https://github.com/seu-usuario/fio-lab && git push -u origin main
git tag v2.2.0 && git push --tags        # gera Release com zip, caderno e manual
```

Depois, em *Settings › Pages*, escolha **GitHub Actions** como fonte para publicar o manual.

---

## O que há de novo na v2

| Camada | O que faz |
|---|---|
| **Documentos BR** | CPF (DV + região fiscal), **CNPJ alfanumérico** (IN RFB 2.229/2024), CEP→UF, placa antiga↔Mercosul, título de eleitor (UF), PIS, RENAVAM, extração de texto com aviso de ambiguidade CPF×telefone |
| **Fontes BR** | Querido Diário (diários oficiais municipais), ViaCEP/IBGE, Portal da Transparência (CEIS/CNEP) |
| **Indexador universal** | Qualquer CSV/JSON/ZIP de dado aberto vira índice reverso local por *receita* (CNES, Cadastur, TSE, faixas de numeração, genérica) |
| **Analisadores** | Coerência geográfica (DDD × CEP × região fiscal do CPF), intermediários prováveis (contabilidade/coworking), sanção no componente |
| **Pipeline em estágios** | preparação → coleta (ingestão/normalização/enriquecimento) → análise → relatório |
| **Plugins** | Soltou um `.py` em `~/.fio/plugins/`, o lab carrega (com SHA-256 registrado) |
| **Experimentos** | Cada execução registra parâmetros, hash do código, versão das fontes, métricas e hash do grafo; `comparar` mostra o que mudou |
| **Avaliação sintética** | Mundos fictícios com gabarito e armadilhas; precisão/revocação/F1 de cada heurística, com média ± desvio |
| **Laudo / RELINT** | Modelos jurídicos BR com quesitos e cadeia de custódia mapeada nas 10 etapas do art. 158-B do CPP |
| **Bancada web** | `http.server` local, token por sessão, grafo interativo, tarefas assíncronas |

## Instalação

```bash
unzip fio-lab-2.2.0.zip && cd fio
python3 -m fio --help            # Python 3.10+, nada para instalar
pip install -e .                 # opcional: comando `fio`
```

## Uso em 8 comandos

```bash
# caso com base legal, finalidade e metadados do laudo
fio caso novo --id CASO-2026-020 --titulo "..." --base-legal lgpd-7-vi \
  --finalidade "instruir notificação extrajudicial ..." --responsavel "Fulano" \
  --escopo "+5531988887777" "exemplo.com.br"
fio caso-editar --caso CASO-2026-020 --solicitante "Jurídico" --referencia "Proc. 0001234-..."

# alvos e quesitos
fio alvo --caso CASO-2026-020 --tipo telefone --valor "(31) 98888-7777"
fio quesito add --caso CASO-2026-020 --texto "As linhas pertencem ao mesmo grupo?"

# pipeline completo, virando experimento
fio lab pipeline --caso CASO-2026-020 --profundidade 2 --expandir-escopo \
  --relatorio tecnico.html --laudo laudo.html

# responder, emitir laudo ou RELINT
fio quesito responder --caso CASO-2026-020 --n 1 --texto "Sim, com confiança alta ..."
fio laudo --caso CASO-2026-020 --modelo relint --saida relint.html

# bancada web
fio lab bancada
```

## Bancada web

```bash
fio lab bancada --porta 8765
```

Abre `http://127.0.0.1:8765/#t=<token>`. O token vai no *fragmento* da URL,
que não chega a logs nem ao cabeçalho `Referer`, e é exigido em toda rota
`/api`. O servidor escuta só em loopback, confere o cabeçalho `Host` (contra
DNS rebinding) e não envia cabeçalho CORS: outra página aberta no mesmo
navegador não consegue disparar coleta nem ler dado do caso.

Abas: grafo (arrastável, com detalhe por nó), vínculos, agrupamentos,
observações, custódia, experimentos (com comparação entre dois) e quesitos. A
bancada também traz ferramentas BR avulsas, a avaliação sintética e o
inventário de plugins.

## Índice da Receita por UF

```bash
# baixa o mês mais recente, retoma quedas e mantém só MG no SQLite final
fio indice baixar --uf MG --saida ~/.fio/cnpj-mg.sqlite

# múltiplas UFs; use --manter-zips só quando realmente quiser gastar disco
fio indice baixar --uf MG,SP --tmp /caminho/temporario
```

O downloader processa **um ZIP por vez** e remove o arquivo depois. A Receita não
distribui Estabelecimentos por estado, então `--uf` **reduz o índice final e a RAM,
não o volume baixado**. As raízes aceitas ficam numa tabela SQLite auxiliar durante
a construção; Empresas e Sócios são filtrados em lotes contra esse escopo, sem
manter milhões de CNPJs em um `set` Python. Downloads parciais usam `Range` +
`If-Range` e reiniciam apenas o arquivo atual se o objeto remoto mudar. Antes do
rename atômico, o `.parcial` é aberto e validado como ZIP; resposta HTTP completa
mas corrompida nunca vira cache definitivo. Os índices SQLite de telefone, e-mail,
raiz e sócio são criados **depois** da carga filtrada e então recebem `ANALYZE`,
evitando manter seis B-trees atualizadas durante milhões de inserts.

## Fontes

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

## Documentos BR

```bash
fio doc cnpj 12.ABC.345/01DE-35          # alfanumérico, exemplo oficial RFB
fio doc cpf-parcial '***456789**'        # região fiscal a partir da máscara
fio doc placa ABC1234                     # -> ABC1C34
fio doc extrair ata.txt                   # tudo o que houver no texto
```

O 9º dígito do CPF indica a região fiscal de emissão, e **a máscara com que
a Receita publica o CPF de sócios (`***456789**`) deixa esse dígito
visível**. Dá para situar regionalmente um sócio sem ver o CPF completo.

## Avaliação sintética

```bash
fio lab avaliar --sementes 1,2,3,4,5,6,7,8,9,10 --grupos 15 --saida ./aval
```

O gerador fabrica um Brasil fictício (TLD reservado `.test`, sempre offline)
com gabarito e as armadilhas que derrubam análise de vínculo na vida real:

| Armadilha | O que simula |
|---|---|
| contabilidade | mesmo telefone declarado por empresas de 5 grupos |
| bloco-isca | linhas de grupos distintos no mesmo bloco de numeração |
| sequência-isca | linhas de grupos distintos numericamente contíguas |
| número reciclado | cadastro antigo ainda declara linha que hoje é de outro grupo |
| laranja | mesma pessoa (mesmo CPF mascarado) sócia em dois grupos |
| homônimo | mesmo nome, outra pessoa, em outro grupo |
| parente | empresa irmã em nome de parente: vínculo real, invisível no cadastro |
| sócio oculto | empresas do grupo com raízes de CNPJ diferentes |

Resultado em 10 mundos × 15 grupos (média ± desvio):

| Configuração | Precisão | Revocação | F1 |
|---|---|---|---|
| combinado, **sem** poda de intermediários | 0,395 ± 0,152 | 0,863 ± 0,079 | 0,528 ± 0,147 |
| combinado, **com** poda de intermediários | **0,774 ± 0,184** | 0,857 ± 0,084 | **0,796 ± 0,133** |
| sócio por nome + máscara do CPF | 0,395 ± 0,152 | 0,863 ± 0,079 | 0,528 ± 0,147 |
| sócio só por nome (ablação) | 0,349 ± 0,140 | 0,863 ± 0,079 | 0,484 ± 0,147 |
| bloco de numeração isolado | 0,671 ± 0,087 | 0,104 ± 0,040 | 0,177 ± 0,061 |

O que se lê daí:

1. **A poda de intermediários praticamente dobra a precisão sem custo de
   revocação.** Um único telefone de escritório contábil funde grupos
   inteiros, e é o erro mais caro da análise de vínculo.
2. **Desambiguar sócio pela máscara do CPF** elimina os falsos positivos de
   homônimo.
3. **O limiar de confiança não discrimina quando há uma fonte só.** Todas as
   arestas da Receita valem A2 (0,76), então o que separa vínculo forte de
   fraco é corroboração entre fontes independentes, não o limiar.
4. **Bloco e sequência são indícios, não vínculos:** precisão razoável e
   revocação de 10%.

Os valores absolutos dependem dos parâmetros do gerador. O que tem valor são
as **comparações relativas** (ablações). Valide com casos reais rotulados
antes de citar números absolutos.

## Laudo e RELINT

`fio laudo --modelo laudo|relint` gera um documento para quem vai **ler** o
trabalho numa peça: preâmbulo, quesitos, material, metodologia (ISO/IEC
27037, escala Admiralty, reprodutibilidade), exames, **cadeia de custódia
mapeada nas 10 etapas do art. 158-B do CPP**, respostas aos quesitos,
limitações e conclusão graduada. O texto declara que a aplicação dos arts.
158-A a 158-F a vestígio digital é analógica e nunca redige conclusão
categórica.

## Plugins

```bash
cp exemplos/plugin_exemplo.py ~/.fio/plugins/
fio lab plugins
```

Coletor: subclasse de `Coletor` com `@registrar`. Analisador: subclasse de
`Analisador` com `@registrar_analisador`. O SHA-256 de cada plugin entra em
todo experimento que o usou.

## Limites

O framework **recusa por construção**, sem flag para ligar: bases vazadas ou
comercializadas irregularmente, credenciais de terceiros, interceptação,
engenharia social e enumeração de mensageria. Todo caso exige base legal,
finalidade específica, escopo verificado a cada pivô e prazo de validade.
CPF completo encontrado em documento entra no grafo **só mascarado**
(LGPD, art. 6º, III).

## Testes

```bash
python3 -m unittest discover -s testes -v     # 82 testes
python3 testes/fumaca.py                     # fumaça da CLI
python3 testes/ao_vivo.py                    # fontes reais (precisa de internet)
```

Veja `ARQUITETURA.md` para o desenho interno.