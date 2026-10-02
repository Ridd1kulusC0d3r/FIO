# Solução de problemas

Procure pela **mensagem** que você viu. Se nada servir, abra uma [issue](https://github.com/Ridd1kulusC0d3r/FIO/issues) com o resultado de `fio --versao`, `fio diagnostico` e o trecho do `fio ledger listar`.

## Casos e escopo

| Mensagem | Causa | Solução |
|---|---|---|
| `caso 'X' nao existe. Use: fio caso novo …` | id errado ou `FIO_HOME` diferente | `fio caso listar`; confira `echo $FIO_HOME` |
| `caso 'X' ja existe` | id repetido | use outro id ou `fio caso ver --caso X` |
| `base legal '…' nao reconhecida` | valor fora da lista | `fio bases` |
| `finalidade deve ser descrita de forma especifica` | menos de 10 caracteres | descreva o motivo concreto: ela delimita a coleta |
| `'…' fora do escopo do caso` | alvo não está no escopo | `fio alvo` inclui o alvo; ou `--expandir-escopo` para derivados |
| `caso X expirou em …; renove antes de coletar` | prazo (padrão 90 dias) | abra novo caso com `--dias`; a renovação deve ser uma decisão sua e justificada |
| `escopo vazio: nenhum identificador autorizado` | caso sem `--escopo` e sem alvo | `fio alvo --caso … ` |
| `pivôs bloqueados pelo escopo: N` | a coleta achou entidades que o escopo não cobre | normal; use `--expandir-escopo` se a investigação justifica |

## Resultados vazios ou estranhos

| Sintoma | Causa | Solução |
|---|---|---|
| Nenhuma observação no relatório | só rodou `fio investigar`, que **não analisa** | rode `fio lab pipeline` (inclui o estágio de análise) |
| `indice local de CNPJ nao configurado` no ledger | sem índice da Receita | `fio indice baixar --uf XX` ou defina `FIO_INDICE_CNPJ` |
| Telefone sem nenhuma empresa | não consta no cadastro da UF indexada, ou índice só de outra UF | `fio indice status`; indexe a UF certa. Ausência **não prova** nada |
| Coletores de rede "executados" em `--offline` | eles são **pulados** (`coletor.pulado`) | `fio ledger listar` mostra cada um; métrica `coletores_pulados` |
| `sem chave` no diagnóstico | coletor exige chave (Transparência, HIBP) | [configuração](configuracao.md) |
| Confiança "baixa" para telefone da Receita | linha declarada por várias raízes de CNPJ, ou cadastro encerrado | é o esperado: [conceitos](conceitos.md#como-a-receita-pesa-um-telefone) |
| Resultado diferente entre duas execuções | fonte mudou, índice atualizado ou cache expirou | `fio lab comparar` mostra o que mudou |

## Rede e fontes

| Sintoma | Causa | Solução |
|---|---|---|
| `fio diagnostico` com `FALHA … URLError` | sem acesso à fonte | internet, proxy, firewall; `FIO_CA_BUNDLE` se há inspeção TLS |
| `contrato quebrado: campo 'x' ausente` | a fonte mudou de formato | o coletor correspondente vai quebrar; abra uma issue "fonte quebrada" |
| `fonte instavel (nao conta como falha)` | `crt.sh` e Querido Diário oscilam | normal; o F.I.O. já tenta duas vezes |
| `HTTP 429` | limite da fonte | aguarde; aumente `--intervalo` |
| `DESCARTADA: resposta N% igual a de um valor impossivel` (ledger) | baseline diferencial: a fonte devolve página padrão | é proteção, não erro; a resposta não vale como achado |
| Consulta à web sem resultado nenhum | índice público bloqueou (anti-robô) | o baseline descarta a página de bloqueio; use `fio dorks --urls` e pesquise à mão |

## Índice da Receita

| Sintoma | Solução |
|---|---|
| `tempo esgotado` / `Failed to connect` (de nuvem) | a Receita bloqueia IPs de nuvem: monte o índice no seu computador e leve o arquivo ([indice-cnpj](indice-cnpj.md#a-receita-não-responde-de-dentro-de-nuvem)) |
| Listagem raiz reseta a conexão | informe `--mes AAAA-MM` ou `FIO_RECEITA_MES` |
| Acabou o disco | `--tmp` em disco maior; **um ZIP por vez** já é o padrão; não use `--manter-zips` |
| Download interrompido | rode de novo: retoma com `Range` e só reinicia o arquivo atual |
| `erro: --origem e obrigatorio` | `fio indice construir` exige a pasta com os CSV |
| UF inválida | use siglas (`MG`, `MG,SP`) |

## Integridade

| Mensagem | Significado | O que fazer |
|---|---|---|
| `CADEIA COMPROMETIDA` + `elo quebrado` | registro inserido ou removido no ledger | **não use o material como prova**; descubra quem alterou; refaça a coleta |
| `conteudo alterado apos a gravacao` | um registro foi editado | idem |
| `artefato adulterado em disco` / `artefato ausente` | arquivo bruto mudou ou sumiu | restaure do backup; senão refaça |
| `peça alterada: grafo.json` | o grafo mudou depois do manifesto | normal se você rodou novo pipeline: gere outro manifesto; se não rodou, investigue |
| `o próprio manifesto foi alterado` | `manifesto.json` editado | idem |
| `ledger reescrito: o hash da emissao nao esta na cadeia` | o ledger foi reescrito depois do manifesto | trate como adulteração |

## Bancada

| Sintoma | Solução |
|---|---|
| "Token ausente" | abra pelo endereço **completo** impresso no terminal (com `#t=…`) |
| `host nao permitido` | acesso por nome que não é `localhost`: `--permitir-host` ou `FIO_HOSTS_PERMITIDOS` |
| Porta em uso | `fio lab bancada --porta 9000` |
| Colab: lista de **Base legal** vazia ou "base legal '' nao reconhecida" | bug da tela do Colab até a 3.0.4; atualize e escolha a base legal na lista |
| Página em branco no Colab | veja [Colab](colab.md#não-carrega-confira-nesta-ordem); atualize para ≥ 3.0.2 |
| Janela preta fecha sozinha (Windows) | rode `python -m fio lab bancada` num terminal para ver o erro |
| "O Windows protegeu o computador" | *Mais informações › Executar assim mesmo* (o lançador não é assinado) |
| macOS bloqueia o `.command` | botão direito › *Abrir* › *Abrir* |

## Instalação

| Sintoma | Solução |
|---|---|
| `python: command not found` | instale o Python 3.10+; no Windows marque *Add python.exe to PATH* |
| `requires-python >=3.10` | atualize o Python |
| `fio: command not found` após `pip install` | o diretório de scripts do pip não está no `PATH`; use `python -m fio` |
| Acentos quebrados no terminal do Windows | o F.I.O. força UTF-8 na saída; se persistir, `chcp 65001` ou `set PYTHONUTF8=1` |

## Pedindo ajuda

Anexe: `fio --versao`, sistema operacional, o comando, a saída completa e, **sem dados pessoais reais**, o trecho relevante de `fio ledger listar`. Nunca anexe `config.json`, tokens ou o conteúdo de `casos/`. Para vulnerabilidades, siga [SECURITY.md](../../SECURITY.md).
