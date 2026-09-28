# Vinculo entre linhas usadas em fraude de boleto

Caso `CASO-2026-014` · relatorio de analise de vinculo · 25/09/2026 02:04 · responsavel: Deivison Lourenco

## 1. Mandato e limites

- **Base legal:** Art. 7, VI LGPD - exercicio regular de direitos em processo
- **Finalidade:** instruir notificacao extrajudicial e representacao criminal por estelionato contra cliente corporativo
- **Escopo autorizado:** +5531988887777, +5521988887778, +5531988887779, auroratech.com.br, demo/relatorio_interno.txt, 3198888, 11222333000181, 30120010, +553133334444, MARIA CLARA PEREIRA [***456789**], ***456789**, JOAO BATISTA SOUZA [***112233**], ***112233**, 11222333000262, 2198888, 20040002, 44555666000109, RENATA LIMA CAMPOS [***998877**], ***998877**, ***982247**, 12ABC34501DE35, QRS1A23, 3133334
- **Validade:** 2026-12-24T02:03:56+00:00

> Material obtido de fontes abertas e registros publicos, sem contato com as pessoas analisadas e sem acesso a sistema protegido. Vinculo = coocorrencia documentada entre identificadores, nao relacao comprovada. Verifique na fonte primaria antes de qualquer decisao.

## 2. Panorama

| metrica | valor |
|---|---|
| alvos primarios | 4 |
| entidades | 25 |
| vinculos | 41 |
| alta confianca | 28 |
| agrupamentos | 4 |

## 3. O que liga os alvos

- `documento:demo/relatorio_interno.txt` ⟷ `telefone:+5521988887778` (1 salto(s), elo mais fraco 0.64) via **ligacao direta**
- `documento:demo/relatorio_interno.txt` ⟷ `telefone:+5531988887777` (1 salto(s), elo mais fraco 0.64) via **ligacao direta**
- `documento:demo/relatorio_interno.txt` ⟷ `telefone:+5531988887779` (1 salto(s), elo mais fraco 0.64) via **ligacao direta**
- `telefone:+5521988887778` ⟷ `telefone:+5531988887777` (2 salto(s), elo mais fraco 0.64) via **demo/relatorio_interno.txt**
- `telefone:+5521988887778` ⟷ `telefone:+5531988887779` (2 salto(s), elo mais fraco 0.64) via **demo/relatorio_interno.txt**
- `telefone:+5531988887777` ⟷ `telefone:+5531988887779` (2 salto(s), elo mais fraco 0.64) via **demo/relatorio_interno.txt**

## 4. Agrupamentos

### ancora-organizacao — `11222333000181` (forca 0.88)

2 telefones ligados a mesma entidade organizacao 'AURORA TECH SOLUCOES LTDA', confianca media das arestas 0.76.

> Ressalva: Verifique se a ancora nao e um intermediario generico (escritorio de contabilidade, central de atendimento, provedor de hospedagem) antes de tratar como grupo.

Membros: `organizacao:11222333000181`, `telefone:+553133334444`, `telefone:+5531988887777`

### dominio-email — `auroratech.com.br` (forca 0.7)

3 enderecos no dominio auroratech.com.br. Dominio proprio: os titulares compartilham a mesma infraestrutura de correio, logo a mesma organizacao ou o mesmo responsavel.

> Ressalva: Confirme o titular do dominio via RDAP antes de afirmar a relacao.

Membros: `email:contato@auroratech.com.br`, `email:filial.rj@auroratech.com.br`, `email:financeiro@auroratech.com.br`

### numeracao-sequencial — `31-988887777` (forca 0.55)

2 numeros contiguos no DDD 31 (intervalo de 2 posicoes). Contratacao corporativa em lote e a explicacao mais economica para numeros adjacentes.

> Ressalva: Pode tambem indicar numeros gerados artificialmente em fraude ou lista sintetica.

Membros: `telefone:+5531988887777`, `telefone:+5531988887779`

### bloco-numeracao — `3198888` (forca 0.35)

2 numeros no mesmo bloco de numeracao 3198888. Blocos sao destinados em lote as prestadoras e linhas corporativas de uma mesma contratacao costumam cair no mesmo bloco.

> Ressalva: Indicio fraco isolado: um bloco atende milhares de assinantes sem relacao entre si. So tem valor somado a outro vinculo.

Membros: `telefone:+5531988887777`, `telefone:+5531988887779`

## 5. Tabela de correlacao

| entidade | relacao | vinculada a | confianca | nivel | fontes |
|---|---|---|---|---|---|
| `+5521988887778` | telefone_declarado_por | `11222333000262` | 0.76 | alta | cnpj-reverso |
| `+553133334444` | telefone_declarado_por | `11222333000181` | 0.76 | alta | cnpj-reverso |
| `+5531988887777` | telefone_declarado_por | `11222333000181` | 0.76 | alta | cnpj-reverso |
| `+5531988887779` | telefone_declarado_por | `44555666000109` | 0.76 | alta | cnpj-reverso |
| `11222333000181` | endereco_no_cep | `30120010` | 0.76 | alta | cnpj-reverso |
| `11222333000181` | email_declarado | `contato@auroratech.com.br` | 0.76 | alta | cnpj-reverso |
| `11222333000181` | telefone_declarado | `+553133334444` | 0.76 | alta | cnpj-reverso |
| `11222333000181` | tem_socio | `MARIA CLARA PEREIRA [***456789**]` | 0.76 | alta | cnpj-reverso |
| `11222333000181` | tem_socio | `JOAO BATISTA SOUZA [***112233**]` | 0.76 | alta | cnpj-reverso |
| `11222333000181` | mesmo_grupo_cadastral | `11222333000262` | 0.76 | alta | cnpj-reverso |
| `11222333000181` | telefone_declarado | `+5531988887777` | 0.76 | alta | cnpj-reverso |
| `11222333000262` | endereco_no_cep | `20040002` | 0.76 | alta | cnpj-reverso |
| `11222333000262` | email_declarado | `filial.rj@auroratech.com.br` | 0.76 | alta | cnpj-reverso |
| `11222333000262` | tem_socio | `MARIA CLARA PEREIRA [***456789**]` | 0.76 | alta | cnpj-reverso |
| `11222333000262` | tem_socio | `JOAO BATISTA SOUZA [***112233**]` | 0.76 | alta | cnpj-reverso |
| `11222333000262` | mesmo_grupo_cadastral | `11222333000181` | 0.76 | alta | cnpj-reverso |
| `11222333000262` | telefone_declarado | `+5521988887778` | 0.76 | alta | cnpj-reverso |
| `44555666000109` | endereco_no_cep | `30120010` | 0.76 | alta | cnpj-reverso |
| `44555666000109` | email_declarado | `financeiro@auroratech.com.br` | 0.76 | alta | cnpj-reverso |
| `44555666000109` | tem_socio | `MARIA CLARA PEREIRA [***456789**]` | 0.76 | alta | cnpj-reverso |
| `44555666000109` | tem_socio | `RENATA LIMA CAMPOS [***998877**]` | 0.76 | alta | cnpj-reverso |
| `44555666000109` | telefone_declarado | `+5531988887779` | 0.76 | alta | cnpj-reverso |
| `JOAO BATISTA SOUZA [***112233**]` | documento_parcial | `***112233**` | 0.76 | alta | cnpj-reverso |
| `MARIA CLARA PEREIRA [***456789**]` | documento_parcial | `***456789**` | 0.76 | alta | cnpj-reverso |
| `RENATA LIMA CAMPOS [***998877**]` | documento_parcial | `***998877**` | 0.76 | alta | cnpj-reverso |
| `contato@auroratech.com.br` | telefone_declarado_por | `11222333000181` | 0.76 | alta | cnpj-reverso |
| `filial.rj@auroratech.com.br` | telefone_declarado_por | `11222333000262` | 0.76 | alta | cnpj-reverso |
| `financeiro@auroratech.com.br` | telefone_declarado_por | `44555666000109` | 0.76 | alta | cnpj-reverso |
| `demo/relatorio_interno.txt` | menciona | `+5531988887777` | 0.64 | media | extrator |
| `demo/relatorio_interno.txt` | menciona | `+5531988887779` | 0.64 | media | extrator |
| `demo/relatorio_interno.txt` | menciona | `+5521988887778` | 0.64 | media | extrator |
| `demo/relatorio_interno.txt` | menciona | `financeiro@auroratech.com.br` | 0.64 | media | extrator |
| `demo/relatorio_interno.txt` | menciona | `***982247**` | 0.64 | media | extrator |
| `demo/relatorio_interno.txt` | menciona | `11222333000181` | 0.64 | media | extrator |
| `demo/relatorio_interno.txt` | menciona | `12ABC34501DE35` | 0.64 | media | extrator |
| `demo/relatorio_interno.txt` | menciona | `30120010` | 0.64 | media | extrator |
| `demo/relatorio_interno.txt` | menciona | `QRS1A23` | 0.64 | media | extrator |
| `+5521988887778` | pertence_ao_bloco | `2198888` | 0.38 | baixa | nucleo |
| `+553133334444` | pertence_ao_bloco | `3133334` | 0.38 | baixa | nucleo |
| `+5531988887777` | pertence_ao_bloco | `3198888` | 0.38 | baixa | nucleo |
| `+5531988887779` | pertence_ao_bloco | `3198888` | 0.38 | baixa | nucleo |

## 6. Reservas das fontes

- **cnpj-reverso** (A2): Alcanca apenas linhas declaradas por pessoa juridica a Receita. Telefone pessoal de pessoa fisica nao consta -- e nao deveria. O dado e autodeclarado pela empresa e pode estar desatualizado: confira a data da base.
- **extrator** (B2): A confianca do vinculo nao passa da confianca do documento de origem: um PDF encaminhado por terceiro e material de segunda mao ate que a origem seja verificada.
- **nucleo** (A2): O DDD indica a area de habilitacao original da linha, nao onde a pessoa esta. Com portabilidade e numero movel, a geografia e pista de origem, nunca de localizacao atual.

## 7. Cadeia de custodia

166 registros encadeados. Verificacao: integra.

Hash do ultimo registro: `b82c69aab3a29a6ebc3e259d6ae463b37efef3055188cf8ebb3a7ef73335bc16`
