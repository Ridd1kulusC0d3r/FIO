# Avaliação e calibração

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
| rede de fachada | quatro empresas de raízes distintas abertas em lote, com telefone e CEP em comum e sócios todos diferentes |
| parente | empresa irmã em nome de parente: vínculo real, invisível no cadastro |
| sócio oculto | empresas do grupo com raízes de CNPJ diferentes |

Resultado em 10 mundos × 15 grupos (média ± desvio):

| Configuração | Precisão | Revocação | F1 |
|---|---|---|---|
| combinado, limiar 0,2, **sem** poda | 0,441 ± 0,154 | 0,885 ± 0,068 | 0,575 ± 0,141 |
| combinado, limiar 0,2, **com** poda de intermediários | 0,774 ± 0,184 | 0,714 ± 0,070 | 0,727 ± 0,115 |
| combinado, limiar 0,4 (sem poda) | 0,878 ± 0,058 | 0,714 ± 0,070 | 0,785 ± 0,052 |
| combinado, limiar 0,4 **com** poda | 0,878 ± 0,058 | 0,714 ± 0,070 | 0,785 ± 0,052 |
| sócio por nome + máscara do CPF | 0,441 ± 0,154 | 0,885 ± 0,068 | 0,575 ± 0,141 |
| sócio só por nome (ablação) | 0,389 ± 0,146 | 0,885 ± 0,068 | 0,527 ± 0,145 |
| bloco de numeração isolado | 0,671 ± 0,087 | 0,086 ± 0,033 | 0,151 ± 0,053 |
| sequência numérica isolada | 0,810 ± 0,064 | 0,086 ± 0,033 | 0,154 ± 0,054 |

O que se lê daí:

1. **Corroboração e linhas muito compartilhadas pesam mais que o limiar nominal.** Telefone declarado por várias raízes de CNPJ cai para ~0,38; o limiar 0,4 corta exatamente essas arestas e leva a precisão de 0,44 para 0,88, com perda de revocação de 0,885 para 0,714.
2. **A poda de intermediários troca revocação por precisão em limiar baixo** (precisão 0,44 → 0,77; revocação 0,89 → 0,71), porque um único telefone de escritório contábil funde grupos inteiros: é o erro mais caro da análise de vínculo. Em limiar 0,4 a poda já está implícita no corte e não muda mais nada.
3. **Desambiguar sócio pela máscara do CPF** elimina os falsos positivos de homônimo (0,441 contra 0,389 de precisão na ablação por nome).
4. **Bloco e sequência são indícios, não vínculos:** precisão razoável e revocação de ~9%.
5. **Limiar 0,8 não retorna nada:** nenhuma aresta de fonte única chega lá, e a confiança nunca chega a 1,0 por construção.

Os valores absolutos dependem dos parâmetros do gerador. O que tem valor são
as **comparações relativas** (ablações). Valide com casos reais rotulados
antes de citar números absolutos.

## Calibração da confiança

```bash
fio lab calibrar --sementes 1,2,3,4,5,6,7,8,9,10 --grupos 15 --saida ./cal
```

Para cada aresta entre entidades de grupo conhecido (telefone, organização), o rótulo é "as duas pontas são do mesmo grupo?". Agrupa-se por faixa de confiança, compara-se a confiança declarada com a precisão observada e calcula-se o erro de calibração esperado (ECE). Uma regressão isotônica (PAV) monotônica mapeia a confiança declarada para a precisão observada. Resultado de referência em [`demo/calibracao_10_mundos.md`](../../demo/calibracao_10_mundos.md).

Leitura honesta do resultado: o escalonamento Admiralty **ordena** corretamente (faixas mais altas acertam mais), mas é **conservador e grosseiro**: quase todas as arestas caem em três valores. Calibrar sobre mundos sintéticos valida a coerência interna, não substitui validação em campo.
