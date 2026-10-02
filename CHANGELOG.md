# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versões semânticas.

## [3.0.2] — 2026-10-02

### Corrigido
- **Colab: a tela completa da bancada não carregava atrás do proxy do Colab.** `ui.html` chamava `/api` com caminho absoluto e lia `sessionStorage` sem proteção; dentro do iframe, com armazenamento bloqueado ou prefixo de caminho, o script parava e a página ficava em branco. A base da API agora é relativa à página e o armazenamento é protegido. Coberto por teste E2E que simula proxy com prefixo, iframe de outra origem e `sessionStorage` bloqueado.
- **CI no Windows:** o helper dos testes da 3.0 deixava o SQLite do cache aberto e o Windows não apagava a pasta temporária.
- **Contrato das fontes:** `fio diagnostico` tenta uma segunda vez antes de reprovar (reset de conexão, 5xx, corpo truncado) e fontes comunitárias conhecidas por oscilar (`crt.sh`, Querido Diário) aparecem como "instável" sem reprovar o job.

### Adicionado
- **Colab:** a célula "Preparar sessão" informa Python, CPUs, RAM e disco e avisa quando os recursos não bastam para o índice da Receita.

## [3.0.1] — 2026-10-02

### Alterado
- **Colab com runtime efêmero:** nada é montado no Google Drive; o caderno e a tela simplificada (`ui_colab.html`) recebem o telefone diretamente, constroem o índice por UF e oferecem modelo e relatórios para download.
- **Downloader do índice resiliente** (`receita_download`) e testes ajustados para Windows (índices SQLite fechados antes da limpeza).
- Mesclado com a 3.0.0 (bancada redesenhada, claims, manifesto, baseline); caderno regenerado.

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
