# Analisadores

Coletor pergunta ao mundo; analisador pergunta ao grafo. Não há rede aqui: só leitura do que já foi coletado e produção de **observações**, que vão para o relatório numa seção própria, separadas dos vínculos.

| Analisador | O que sinaliza | Cuidado embutido |
|---|---|---|
| `coerencia-geografica` | DDD do telefone × UF do cadastro/CEP × região fiscal do CPF mascarado | cita filial, portabilidade e linha móvel entre as explicações |
| `intermediarios` | telefone, CEP ou e-mail em 4+ empresas sem sócio em comum | trata como ponte fraca, **não** como vínculo de grupo |
| `lote-de-registro` | 3+ empresas de raízes distintas abertas em 30 dias e ligadas por telefone, e-mail, sócio ou CEP | ponte fraca + lote = atenção; sócio em comum = grupo que se expandiu |
| `reuso-de-linha` | telefone declarado por empresa encerrada (baixada/inapta) e por outra ativa | cadastro antigo não é vínculo atual |
| `alerta-sancao` | sanção (CEIS/CNEP) no mesmo componente de um alvo | proximidade no grafo não transfere responsabilidade |

Nenhum acusa. Cada observação descreve o padrão e as explicações concorrentes. Para escrever o seu, subclasse de `Analisador` com `@registrar_analisador` (veja [plugins](laudo-e-plugins.md)).

## Claims e manifesto

- `fio claims --caso ID` lista as conclusões do caso. Cada uma cita a aresta (ou as entidades) do grafo que a sustenta; claim sem evidência, ou com evidência inexistente, é inválido. O relatório Markdown traz a tabela na seção 7.
- `fio manifesto gerar --caso ID` grava o SHA-256 de cada peça (grafo, caso, experimentos, relatórios) amarrado ao último hash do ledger. `fio manifesto verificar` aponta peça alterada, manifesto adulterado e ledger reescrito. `fio relatorio --manifesto` já inclui os relatórios gerados.
