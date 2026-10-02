# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versões semânticas.

## [3.0.6] — 2026-10-02

### Alterado
- **Colab abre a bancada completa por padrão** (painel, grafo, vínculos, observações, custódia: as telas do GIF). Antes abria a tela simplificada e a completa ficava atrás de um botão, então quem chegava pelo Colab não encontrava as telas da demonstração. A tela simples continua disponível (`interface: simples` na célula, ou `/simples/`); a API é a mesma.

## [3.0.5] — 2026-10-02

### Corrigido
- **Colab: a lista de "Base legal" da tela do Colab vinha vazia** (`/api/estado` devolve um dicionário e a tela chamava `.map` nele; o erro abortava a inicialização inteira, e criar o caso falhava com "base legal '' não reconhecida"). A lista agora vem do estado, começa em "Selecione a base legal…" e a tela exige a escolha. Coberto por teste E2E.
- **Receita inacessível a partir de nuvem:** quando o servidor da Receita não aceita conexão (timeout), o F.I.O. agora **falha na hora** com a explicação e as saídas, em vez de sondar mês a mês por vários minutos (3 transportes × 15 s × cada mês). Reset de conexão e erros HTTP continuam sendo tentados.

### Adicionado
- **Colab, célula 6b "Enviar índice pronto":** traz para a sessão um `cnpj.sqlite` montado no seu computador, por upload ou por URL https (com progresso e retomada), validando que é um índice do F.I.O.

## [3.0.4] — 2026-10-02

### Alterado
- **Colab começa pelo frontend:** a ordem do caderno agora é Instalar › Sessão › **Abrir o F.I.O.** (tela dentro do caderno). Demonstração, verificação das fontes, índice pelo caderno, caso pontual, pesquisa e testes viram seção **Avançado (opcional)**.
- **"Executar tudo" não dispara trabalho pesado:** índice, benchmark, avaliação sintética e testes só rodam com a caixa **executar** marcada.

### Corrigido
- **A célula "Montar índice" parecia travada:** baixava alguns GB e processava milhões de linhas sem mostrar nada. Agora roda em segundo plano e a célula **acompanha ao vivo** (arquivo, MB, velocidade, linhas lidas, tempo), a cada 3 s; interromper (■) só para de acompanhar. O downloader avisa a cada 10% **ou a cada 15 s**, e o construtor avisa o progresso a cada ~20 s (`indice.Construtor._pulso`).

## [3.0.3] — 2026-10-02

### Corrigido
- **CI vermelho em todo push:** a referência da CLI era gerada com `format_usage()`, que quebra linhas conforme o terminal e muda de formato entre versões do Python; o `--checar` do CI (Python 3.12) divergia de quem gerou (3.11). A linha de uso agora é montada pelo gerador e a saída é idêntica no Python 3.10 a 3.13.
- **Workflow `publicar` vermelho a cada push:** o GitHub Pages precisa ser habilitado uma vez pelo dono do repositório. O job agora verifica isso, emite um aviso com o passo a passo e segue verde, em vez de falhar.

- **Job "Fumaça da CLI" travava até estourar os 10 minutos:** a bancada imprimia o endereço sem `flush`; com a saída num pipe o Python guarda no buffer e quem lê a primeira linha espera para sempre. O servidor agora faz `flush`, e o teste de fumaça lê com prazo de 20 s (falha rápido em vez de travar) e esperava a versão `fio 2.`.
- **Referência da CLI dependia da pasta de quem gerou** (o padrão de `--saida` era um caminho absoluto); agora é `./lab-saida`.

### Adicionado
- **Site do projeto** (`docs/index.html`): página inicial com demonstração em GIF, capturas de tela, princípios, tema claro/escuro e responsiva, no lugar do redirecionamento para o manual.

## [3.0.2] — 2026-10-02

### Corrigido
- **Colab: a tela completa da bancada não carregava atrás do proxy do Colab.** `ui.html` chamava `/api` com caminho absoluto e lia `sessionStorage` sem proteção; dentro do iframe, com armazenamento bloqueado ou prefixo de caminho, o script parava e a página ficava em branco. A base da API agora é relativa à página e o armazenamento é protegido. Coberto por teste E2E que simula proxy com prefixo, iframe de outra origem e `sessionStorage` bloqueado.
- **CI no Windows:** o helper dos testes da 3.0 deixava o SQLite do cache aberto e o Windows não apagava a pasta temporária.
- **Contrato das fontes:** `fio diagnostico` tenta uma segunda vez antes de reprovar (reset de conexão, 5xx, corpo truncado) e fontes comunitárias conhecidas por oscilar (`crt.sh`, Querido Diário) aparecem como "instável" sem reprovar o job.

### Adicionado
- **Documentação:** home do repositório em inglês (`README.md`) com versão em português (`README.pt-BR.md`); guias novos em `docs/guia/` (primeiros passos, conceitos, interpretando resultados, receitas de uso, Colab, bancada, configuração, solução de problemas, detalhe por coletor); **referência da CLI gerada do `argparse`** (`tools/gerar_referencia_cli.py`) e verificador de links (`tools/checar_links.py`), ambos no CI.
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
