# Bancada web

A bancada é a interface gráfica do F.I.O.: servidor local (`http.server`, **só biblioteca padrão**) com uma página única, sem fonte nem script externo.

![Painel](../img/painel-claro.png)

## Subir

```bash
fio lab bancada                  # http://127.0.0.1:8765, abre o navegador
fio lab bancada --porta 9000
fio lab bancada --sem-navegador  # só imprime o endereço
```

O endereço impresso tem a forma `http://127.0.0.1:8765/#t=<token>`. **O token é a única credencial da sessão**: um novo é gerado a cada execução. Ele vai no *fragmento* da URL (que não chega a logs nem ao cabeçalho `Referer`) e a página o remove da barra de endereço.

Sem token (por exemplo, abrir `http://127.0.0.1:8765/` em outra aba depois de fechar a original) a página avisa **"Token ausente"** em vez de quebrar: reabra pelo endereço completo.

### Segurança

- escuta **só em loopback** (`127.0.0.1`);
- confere o cabeçalho `Host` contra DNS rebinding;
- **não envia CORS**: outra página aberta no navegador não consegue disparar coleta nem ler dado do caso;
- exige o token em **toda** rota `/api`;
- `X-Frame-Options: DENY` e CSP restrita (`default-src 'self'`), exceto no modo Colab, que precisa de iframe;
- para acessar por outro nome de host (proxy, contêiner), declare-o: `--permitir-host sufixo.exemplo.com` ou `FIO_HOSTS_PERMITIDOS`. O token continua obrigatório.

## Primeira vez

1. **Verificar conexões**: consulta neutra a cada fonte online (nenhuma pessoa). Mostra o que sua rede alcança.
2. **Abrir caso de demonstração**: monta `DEMO-FRAUDE-BOLETO` (tudo fictício, offline) e abre direto no grafo. **Recriar** apaga e refaz.
3. **Novo caso**: base legal, finalidade, responsável e escopo.

## Telas

| Tela | O que tem |
|---|---|
| **Painel** | boas-vindas, demonstração, verificação das fontes, lista de casos |
| **Caso** | cabeçalho com selos (modo passivo, offline ou "consultou a rede"), métricas, abas abaixo e os três relatórios (técnico, laudo, RELINT) |
| **Resumo** | distribuição de confiança, entidades por tipo, **adicionar alvo**, executar pipeline |
| **Grafo** | veja abaixo |
| **Vínculos** | tabela ordenável e filtrável; cada linha tem **No grafo** |
| **Agrupamentos** | âncoras, força e ressalva; **Destacar no grafo** |
| **Observações** | cartões por gravidade (cor + ícone), filtros por gravidade e analisador, **Destacar no grafo** |
| **Custódia** | ledger com a verificação da cadeia (**Cadeia íntegra**) |
| **Experimentos** | execuções do pipeline e comparação entre duas |
| **Quesitos** | perguntas e respostas do laudo |
| **Avaliação sintética** | mundos fictícios, precisão/revocação/F1 |
| **Fontes e diagnóstico** | estado de cada fonte, inventário de coletores e plugins |
| **Ferramentas BR** | análise de número, documentos (CPF, CNPJ, boleto…) sem abrir caso |

![Grafo](../img/grafo-detalhe.png)

## O grafo

| Ação | Como |
|---|---|
| **Mover / zoom** | arraste o fundo; roda do mouse, botões `+ −` ou pinça no celular |
| **Reorganizar** | arraste os nós; o botão ⟳ refaz o layout |
| **Detalhe** | clique num nó (atributos, observações, fontes, vínculos) ou numa aresta (proveniência) |
| **Cor do nó** | tipo da entidade; a legenda é clicável e filtra por tipo |
| **Aresta** | espessura e opacidade pela confiança Admiralty. **Tracejada** = baixa; **pontilhada** = indiciária |
| **Filtro** | por nível de confiança (alta, média, baixa, indiciária) com contagem |
| **Busca** | caixa de busca ou tecla `/` |
| **Caminho** | escolha origem e destino (ou use **Origem do caminho** / **Destino** no detalhe de um nó) e **Destacar caminho**: mostra o caminho mais forte entre dois nós |
| **Exportar** | **PNG**, **SVG** ou **JSON**; o rodapé do arquivo repete o aviso de que a confiança nunca é 100% |

Cada fonte, no detalhe, mostra o código **Admiralty**, a nota do coletor, a URL, a data da coleta e o **SHA-256** do artefato bruto no ledger.

![Observações](../img/observacoes.png)

## Tema, teclado, celular

- **Tema** claro/escuro: segue o sistema; o botão no cabeçalho alterna e **lembra** a escolha.
- Teclado: `Tab`/`Shift+Tab`, abas por setas, `/` busca no grafo, link "pular para o conteúdo".
- No celular, a barra lateral vira **gaveta** (menu ☰). O layout é responsivo (sem rolagem horizontal a partir de 360 px).
- Respeita `prefers-reduced-motion`.

## Tarefas assíncronas

Pipeline, avaliação sintética e construção do índice da Receita rodam numa **fila** (SQLite + 2 *workers* em *threads*) para a página não travar. O estado aparece na barra de tarefa e em toasts. A fila fica em `FIO_HOME/lab/fila.sqlite`.

## A bancada no Colab

No Colab, `fio lab bancada` não se aplica: use a célula "Abrir a bancada" (veja [Colab](colab.md)). Ela sobe o servidor em **modo Colab** (aceita o `Host` do proxy do Google e o iframe) e abre **esta mesma interface completa**. Há uma tela mínima opcional (`interface: simples`, ou o caminho `/simples/`).

## API (para scripts)

A página usa uma API JSON local, e a base é **relativa à página**, o que permite rodar atrás de proxy com prefixo. Toda chamada leva o cabeçalho `X-FIO-Token` (ou `?t=` em links de download).

| Método e rota | Faz |
|---|---|
| `GET /api/estado` | versão, bases legais, ambiente |
| `GET /api/casos` · `POST /api/casos` | lista / cria casos |
| `GET /api/diagnostico` | sonda as fontes online |
| `GET /api/indice` · `POST /api/indice` | estado / constrói o índice da Receita |
| `GET /api/modelo-relatorio` | modelo vazio de relatório |
| `GET /api/avaliacao` · `POST /api/avaliar` | avaliação sintética |
| `POST /api/numero` · `POST /api/documento` | análise avulsa |
| `POST /api/demo` | monta o caso de demonstração |
| `GET /api/casos/<id>` | metadados do caso |
| `GET /api/casos/<id>/grafo` · `/ledger` · `/experimentos` · `/comparar` | grafo, cadeia de custódia, experimentos, comparação |
| `GET /api/casos/<id>/relatorio?modelo=tecnico\|laudo\|relint` | relatório HTML (`&download=1` baixa) |
| `POST /api/casos/<id>/alvos` · `/pipeline` · `/quesitos` | adiciona alvo, enfileira pipeline, gerencia quesitos |

A API é **interna** e pode mudar entre versões; para automação estável, prefira a [CLI](referencia-cli.md).
