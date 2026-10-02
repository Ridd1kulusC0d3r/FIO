# Interpretando resultados

O F.I.O. produz **indícios documentados**, não conclusões. Este guia mostra como ler cada saída e o que **não** concluir dela.

## A regra de ouro

> **Vínculo = coocorrência documentada entre identificadores, não relação comprovada.**
> Verifique na fonte primária antes de qualquer decisão que afete uma pessoa.

Dois telefones na mesma empresa dizem que a empresa os declarou. Não dizem quem os usa, desde quando, nem se ainda os usa.

## Lendo a confiança

| Nível | Faixa | Leitura prudente |
|---|---|---|
| **alta** | ≥ 0,75 | bem sustentado pelas fontes consultadas; ainda sujeito à reserva de cada fonte |
| **média** | 0,50–0,75 | vale investigar; não vale afirmar |
| **baixa** | 0,25–0,50 | pista; precisa de outra evidência independente |
| **indiciária** | < 0,25 | só ordena o trabalho de quem investiga |

Três coisas que surpreendem:

1. **"Alta" é 0,76 com uma fonte só.** A confiança máxima de fonte única na Receita é A2 ≈ 0,76. Para passar disso é preciso **outra fonte independente** corroborando; duas leituras do mesmo coletor valem uma.
2. **A confiança nunca passa de 99%.** Se aparecer 100%, é bug; abra uma issue.
3. **A confiança mede a fonte, não a conclusão.** Uma aresta "alta" entre um telefone e um escritório de contabilidade é um fato sólido (o escritório declarou o número) e uma péssima base para concluir que as empresas atendidas são do mesmo grupo.

Medimos o quanto esses números significam: em mundos sintéticos, o escalonamento **ordena** corretamente, mas é grosseiro e conservador. Veja [Avaliação e calibração](avaliacao.md). **Não cite números absolutos de precisão sem validar em casos reais rotulados.**

## Lendo um agrupamento

Cada agrupamento traz **explicação** e **ressalva**. Os tipos:

| Tipo | Significa | Ressalva embutida |
|---|---|---|
| `ancora-organizacao` / `ancora-pessoa` / … | entidades ligadas à mesma âncora | verifique se a âncora não é intermediário genérico |
| `dominio-email` | e-mails no mesmo domínio | domínio próprio: força 0,70, confirme o titular via RDAP. Provedor gratuito (gmail, hotmail, uol…): força 0,25 e a ressalva diz que **não vincula ninguém** |
| `bloco-numeracao` | linhas no mesmo bloco da Anatel | indício fraco isolado: um bloco atende milhares de assinantes |
| `numeracao-sequencial` | números numericamente contíguos | pode indicar compra em lote por empresa **ou** geração em massa |

Bloco e sequência são **indícios, não vínculos**: na avaliação sintética, têm precisão razoável e revocação de ~9%.

## Lendo as observações

Cada observação tem **gravidade** (`alta`, `atenção`, `info`) e vem de um [analisador](analisadores.md). A gravidade indica prioridade de revisão, **não culpa**.

| Observação | Explicações inocentes que o texto já lista |
|---|---|
| `incoerencia-geografica` | filial, linha móvel habilitada em outra UF, portabilidade, cadastro desatualizado |
| `regiao-fiscal-divergente` | mudança de domicílio é comum |
| `intermediario-provavel` | contabilidade, coworking, despachante |
| `lote-de-registro` | grupo que se expandiu; serviço de abertura de empresas |
| `linha-possivelmente-reciclada` | a operadora revendeu o número depois que a empresa fechou |
| `sancao-no-componente` | proximidade no grafo **não** transfere responsabilidade: verifique o caminho |

## Armadilhas clássicas (e como o F.I.O. se defende)

| Armadilha | O que acontece | Defesa |
|---|---|---|
| **Contabilidade** | um telefone de escritório em empresas de grupos diferentes funde tudo | analisador `intermediarios`; poda opcional |
| **Homônimo** | mesmo nome, pessoas diferentes | pessoa identificada por nome **+ máscara do CPF** |
| **Número reciclado** | cadastro antigo ainda declara linha que hoje é de outro | credibilidade cai com cadastro encerrado; `reuso-de-linha` |
| **Provedor gratuito** | o domínio `gmail.com` não liga ninguém | cluster de e-mail de provedor gratuito sai com força 0,25 e ressalva explícita |
| **Rede de fachada** | empresas de raízes distintas abertas em lote | `lote-de-registro` |
| **Soft-404** | a fonte responde "200 OK" a qualquer consulta | baseline diferencial |
| **Eco da mesma base** | cinco leituras da Receita parecem cinco confirmações | confiança agrupa por coletor |

## Lendo o relatório

O relatório (HTML ou Markdown) segue sempre esta ordem:

1. **Mandato e limites**: base legal, finalidade, escopo, validade.
2. **Panorama**: contagens.
3. **O que liga os alvos**: pontes, com o elo mais fraco.
4. **Agrupamentos** com ressalvas.
5. **Tabela de correlação**: vínculos, do mais ao menos confiável, com as fontes.
6. **Observações analíticas.**
7. **Conclusões rastreáveis**: cada uma com a aresta que a sustenta (só no Markdown).
8. **Reservas das fontes.**
9. **Cadeia de custódia** com a verificação do ledger.

Se a cadeia estiver comprometida, o relatório avisa na seção 9 e o terminal avisa ao gerar. **Não entregue um relatório com a cadeia comprometida sem explicar o porquê.**

## O que o F.I.O. não faz e você não deve concluir

- **Não identifica o titular de um telefone.** Associa o número a cadastros públicos que o declararam.
- **Não prova autoria, dolo ou participação em fraude.** Um número ligado a uma empresa não torna a empresa autora.
- **Não vê o conteúdo de mensagens nem o uso de aplicativos.** E recusa consultar mensageria.
- **Não mede reputação nem atribui "score de risco" a pessoas.**
- **Não substitui perícia, advogado nem o contraditório.** O [laudo](laudo-e-plugins.md) sai com limitações declaradas e conclusão graduada, nunca categórica.
