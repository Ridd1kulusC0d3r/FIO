# Conceitos

O vocabulário do F.I.O., em ordem de dependência. Cada termo diz **o que é**, **onde aparece** e **o que não significa**.

## Caso

A unidade de trabalho. Um diretório em `FIO_HOME/casos/<id>/` com tudo dentro. Um caso declara:

| Campo | Para quê |
|---|---|
| **base legal** | uma entre as 10 que `fio bases` lista (LGPD art. 7º e 4º, III, contrato de pentest, resposta a incidente, judicial, pesquisa acadêmica) |
| **finalidade** | texto específico, mínimo de 10 caracteres; delimita o que pode ser coletado (LGPD art. 6º, I e III) |
| **responsável** | quem responde pelo caso |
| **escopo** | identificadores autorizados |
| **prazo** | padrão de 90 dias; depois disso nenhum coletor roda |
| **modo** | sempre `passivo` |

Sem caso, sem coleta. A análise offline avulsa (`fio numero`, `fio doc`, `fio dorks`) não exige caso porque não coleta nada.

## Escopo e pivô

O **escopo** é a lista do que o caso autoriza. Um coletor só roda sobre um alvo cujo valor esteja no escopo: igual a um item, subdomínio de um item (`mail.exemplo.com.br` para `exemplo.com.br`) ou contendo um item. Isso é conferido **a cada salto**.

**Pivotar** é usar uma entidade descoberta como novo alvo (telefone → empresa → sócio → outras empresas). Por padrão, o F.I.O. **não pivota** além do escopo: o que ele descobre e não pode seguir aparece como *pivô bloqueado*. `--expandir-escopo` autoriza pivotar sobre entidades derivadas, e **cada inclusão fica registrada no ledger**. A decisão de alargar o escopo é sua e fica documentada.

## Entidade e aresta

Uma **entidade** é uma coisa identificável: telefone, organização (CNPJ), pessoa, e-mail, domínio, CEP, URL, documento, faixa de numeração, sanção. A identidade é `tipo + valor canônico`:

- telefone pelo E.164 (`+5531988887777`), nunca pela grafia;
- CNPJ pelos 14 caracteres (numéricos ou alfanuméricos);
- pessoa por `NOME [máscara do CPF]`. O nome sozinho não identifica: homônimos são pessoas diferentes.

Uma **aresta** é um vínculo (`telefone_declarado_por`, `tem_socio`, `endereco_no_cep`, `mesmo_grupo_cadastral`…). **Toda aresta nasce com pelo menos uma fonte.** Vínculo sem fonte é opinião, e opinião não entra no grafo.

## Fonte, Admiralty e confiança

Cada fonte de uma aresta traz um código **Admiralty** (escala OTAN STANAG 2511): uma letra para a **confiabilidade da fonte** e um número para a **credibilidade da informação**.

| Letra | Fonte | | Nº | Informação |
|---|---|---|---|---|
| A | totalmente confiável (registro oficial) | | 1 | confirmada por outras fontes |
| B | normalmente confiável | | 2 | provavelmente verdadeira |
| C | razoavelmente confiável | | 3 | possivelmente verdadeira |
| D | nem sempre confiável | | 4 | duvidosa |
| E | não confiável | | 5 | improvável |
| F | não avaliável | | 6 | não avaliável |

O par vira um número para poder ordenar e combinar (`B2` ≈ 0,64; `A2` ≈ 0,76). A **confiança da aresta** combina as fontes por **OU-ruidoso**, com uma regra de independência: as fontes são agrupadas **por coletor**, só a melhor de cada uma conta, e então se combinam. **Cinco leituras da mesma base não são cinco confirmações.** O resultado **nunca chega a 100%** (teto de 99%).

| Confiança | Nível |
|---|---|
| ≥ 0,75 | alta |
| ≥ 0,50 | média |
| ≥ 0,25 | baixa |
| < 0,25 | indiciária |

### Como a Receita pesa um telefone

Na mesma fonte (Receita, letra A), a credibilidade varia com a **raridade** da linha e com a **situação** do cadastro:

| Raízes de CNPJ que declaram o telefone | Grau | Confiança da aresta |
|---|---|---|
| 1 | A2 | 0,76 |
| 2 a 3 | A3 | 0,57 |
| 4 a 9 | A4 | 0,38 |
| 10 ou mais | A5 | 0,19 |

Cadastro **baixado, inapto ou suspenso** desce mais um degrau (a linha pode ter sido devolvida e reatribuída). É por isso que, na [avaliação sintética](avaliacao.md), o limiar 0,4 corta exatamente as linhas compartilhadas por muitas empresas.

> Confiança alta **não** é "provado". É "bem sustentado pelas fontes consultadas, sujeito à reserva de cada uma".

## Reserva

O limite conhecido de cada coletor, escrito pelo próprio coletor (`fio coletores` lista). Vai para o relatório. Exemplo: o diário oficial é autoritativo de que o texto foi publicado, **não** de que o número pertence a quem aparece ao lado dele.

## Observação analítica

O que os [analisadores](analisadores.md) acham no grafo que **não é vínculo**: incoerência geográfica, intermediário provável, lote de registro, linha reciclada, sanção no componente. Tem gravidade (`alta`, `atenção`, `info`), cita as entidades envolvidas e **descreve explicações concorrentes**. Não é acusação.

## Agrupamento e ponte

Um **agrupamento** (cluster) é um conjunto de entidades ligado por uma âncora (uma organização, um sócio, um bloco de numeração). Uma **ponte** é o caminho que liga dois alvos primários, com o elo mais fraco indicado. Ambos trazem a ressalva do que pode estar errado.

## Intermediário

Telefone, CEP ou e-mail que aparece em muitas empresas **sem sócio em comum**: perfil de escritório de contabilidade, coworking ou despachante. O F.I.O. o trata como **ponte fraca, não como vínculo de grupo**. Um único telefone de contabilidade funde grupos inteiros se for tratado como vínculo; é o erro mais caro da análise de vínculo.

## Raiz de CNPJ

Os 8 primeiros caracteres do CNPJ identificam a **empresa**; os 4 seguintes, o **estabelecimento** (matriz `0001`, filiais depois); os 2 últimos são dígitos verificadores. Duas filiais têm a mesma raiz. Empresas **diferentes** têm raízes diferentes, e ligá-las exige outra evidência (sócio, telefone, endereço).

## Ledger (cadeia de custódia)

`ledger.jsonl`: uma linha por ação do caso (abertura, alvo, coleta, falha, relatório…). O hash de cada linha inclui o hash da anterior; alterar ou remover qualquer registro quebra a cadeia, e `fio ledger verificar` aponta onde. A resposta bruta de cada coleta fica em `artefatos/<sha256>.bin`, referenciada pelo próprio hash.

O ledger **prova que o material não mudou desde a coleta**. Não é assinatura digital nem carimbo de tempo qualificado: não prova que a coleta ocorreu naquela hora. Para isso, ancore o hash do último registro num serviço de timestamping (RFC 3161).

## Manifesto

`manifesto.json`: SHA-256 de cada peça que **sai** do caso (grafo, caso, experimentos, relatórios) mais o último hash do ledger. Estende a garantia do ledger ao que você entrega. `fio manifesto verificar` detecta peça alterada, manifesto adulterado e ledger reescrito. O ledger pode **crescer** depois do manifesto sem invalidá-lo; o que não pode é ser reescrito.

## Claim

Uma conclusão do relatório ligada à evidência que a sustenta (`fio claims`). Claim de **vínculo** cita a aresta; claim de **observação** cita as entidades. Claim sem evidência, ou que cita evidência inexistente, é inválido.

## Baseline diferencial

Antes de confiar numa resposta, o coletor `web` consulta também um valor que **não pode existir** e compara as duas respostas. Se a real for ≥ 90% igual à do valor impossível, é página padrão ("sem resultados", bloqueio anti-robô) e é **descartada**, com o motivo no ledger (`coleta.baseline`).

## Experimento

Toda execução do pipeline (`fio lab pipeline`) vira um experimento: parâmetros, assinatura do código, versão de cada fonte local, métricas por estágio e SHA-256 do grafo. Com isso dá para responder meses depois: *"rodando de novo, sai o mesmo resultado?"* (mesmo hash) e *"o que mudou entre março e maio?"* (`fio lab comparar`).

## Receita

Descrição declarativa (JSON) de como transformar um CSV/JSON/ZIP de dados abertos em índice reverso local (CNES, Cadastur, TSE, faixas de numeração, genérica). Veja [fontes](fontes.md).

## Coleta passiva

O F.I.O. nunca toca o alvo: só consulta fontes de terceiros e material publicado. Contato com o alvo o avisa e muda a natureza do ato. Por isso há **fontes vedadas por construção** (bases vazadas, credenciais de terceiros, interceptação, engenharia social, enumeração de mensageria), sem flag para ligar: `fio bases` as lista com a justificativa.
