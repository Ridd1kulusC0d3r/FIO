# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versões semânticas.

## [3.0.0] — 2026-10-02

### Adicionado
- **Baseline diferencial** (`fio.coletores.baseline`): a resposta a um alvo real é comparada com a resposta a um valor que não pode existir; página padrão ("200 OK" sem informação) é descartada e o motivo vai para o ledger. Aplicado ao coletor `web`; disponível a qualquer coletor via `ClienteHTTP.get_diferencial`.
- **Fontes declarativas com canário** (`fio/fontes.json`): `fio diagnostico` separa *fonte fora do ar* de *contrato quebrado* (a fonte respondeu, mas mudou de formato).
- **Analisadores** `lote-de-registro` (empresas de raízes distintas abertas na mesma janela de 30 dias que compartilham telefone, e-mail, CEP ou sócio) e `reuso-de-linha` (telefone declarado por empresa encerrada e por outra ativa).
- **Claims rastreáveis** (`fio claims`): cada conclusão cita a aresta ou as entidades do grafo que a sustentam; claim sem evidência é inválido. Seção 7 do relatório Markdown.
- **Manifesto SHA-256** (`fio manifesto gerar|verificar`, `fio relatorio --manifesto`): hash de cada peça do caso amarrado ao último hash do ledger; detecta peça alterada, manifesto adulterado e ledger reescrito.
- **Calibração da confiança** (`fio lab calibrar`): tabela de confiabilidade, ECE e regressão isotônica contra o gabarito sintético.
- **Coletores passivos** `crtsh` (Certificate Transparency) e `wayback` (primeira captura no Internet Archive).
- **Identificadores financeiros** (`fio.core.financeiro`): linha digitável de boleto (DV mód. 10 e 11, banco, valor, vencimento), chave PIX aleatória (EVP) e classificação de chave PIX, CNH e Cartão SUS.
- **Mundo sintético**: armadilha `rede-fachada` e datas de abertura por empresa.
- **Bancada**: interface redesenhada (painel, caso, grafo, observações, experimentos, fontes), tema claro e escuro, responsiva, sem dependências externas.
- Guias por tema em `docs/guia/`; logo e banner em `assets/`; CHANGELOG.

### Alterado
- `fio.lab.avaliacao.executar_mundo` extraído de `avaliar`, compartilhado com a calibração.
- Relatório Markdown ganhou as seções de observações analíticas e de conclusões rastreáveis (cadeia de custódia passa à seção 9).
- Avaliação sintética reexecutada com a nova armadilha; tabelas e leitura atualizadas em `docs/guia/avaliacao.md`.
- Limpeza de imports e variáveis não usados.

### Notas de compatibilidade
- Os números da avaliação sintética mudam em relação à 2.x porque o mundo agora tem mais uma armadilha; não compare diretamente com resultados antigos.
- `diagnostico.SONDAS` continua existindo, derivada de `fontes.json`.

## [2.2.0] — 2026-09-28
Veja o histórico de commits anterior a esta versão.
