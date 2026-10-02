# F.I.O. no Google Colab

O Colab é o jeito mais rápido de experimentar: nada para instalar, tudo na nuvem do Google.

[![Abrir no Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Ridd1kulusC0d3r/FIO/blob/main/colab/FIO_Lab_Colab.ipynb)

> **Privacidade.** No Colab os dados passam por servidores do Google. Use para **teste e alvos institucionais**, não para caso real com dado pessoal. Para caso real, [instale localmente](primeiros-passos.md).

## A sessão é efêmera, de propósito

Nada é montado no Google Drive. Casos, fila e índice da Receita ficam **só no runtime** e **somem quando a sessão encerra** (ou após ociosidade). Por isso a última etapa de cada fluxo é **baixar o relatório**. Isso é escolha de projeto: dado de investigação não deve parar num Drive por acidente.

## Passo a passo

**Comece aqui (3 células):** 1. Instalar · 2. Preparar a sessão · **3. Abrir o F.I.O.** A tela do F.I.O. abre **dentro do caderno**; é ali que se trabalha (telefone, índice da Receita com progresso na tela, relatório). Tudo o que vem depois é **avançado e opcional**.

Menu **Ambiente de execução › Executar tudo** é seguro: o que baixa muito dado ou demora (índice, benchmark, avaliação sintética, testes) só roda quando você marca a caixa **executar**.

| Seção | O que faz | Internet |
|---|---|---|
| 1 | Instala o F.I.O. | opcional |
| 2 | Prepara a sessão efêmera e **mostra os recursos da máquina** | não |
| **3** | **Abre o F.I.O. dentro do caderno** | não |
| *Avançado (opcional)* | | |
| 4 | Confere as fontes públicas | sim |
| 5 | Demonstração com mapa interativo | não |
| 6 | Índice da Receita pelo caderno (segundo plano, progresso ao vivo) | sim (alguns GB) |
| 6b | Enviar índice pronto (arquivo ou URL) | não |
| 7 | Caso pontual com fontes reais | sim |
| 8 | Relatório e exportação | não |
| 9 | Benchmark com dados reais e avaliação sintética | índice |
| 10 | Testes | opcional |

### 1. Instalar

O formulário tem três opções de `origem`:

| Valor | Faz |
|---|---|
| `automatico` (padrão) | baixa o código do GitHub (`ramo`, padrão `main`); se o GitHub não responder, usa a **cópia embutida** no caderno |
| `github` | exige o GitHub; falha se ele não responder |
| `embutido` | usa só a cópia que vai dentro do `.ipynb` (funciona sem acesso ao GitHub) |

A cópia embutida é a versão do caderno, que pode ser **mais velha** que o GitHub. A mensagem "F.I.O. Lab X.Y.Z · fonte: …" diz o que foi usado.

### 2. Sessão efêmera e a "máquina"

A célula informa ambiente, Python, CPUs, RAM e disco livre e **avisa** quando os recursos não bastam:

```text
sessao efemera: /content/fio-runtime
ambiente: Google Colab · Python 3.12.x · 2 CPU(s) · RAM 12.7 GB · disco livre 70 GB
recursos suficientes para o fluxo completo.
```

| Aviso | O que fazer |
|---|---|
| disco livre abaixo de 12 GB | reinicie o runtime (**Ambiente de execução › Reiniciar sessão**) para liberar espaço antes do índice da Receita |
| menos de 4 GB de RAM | use **uma UF** no índice e profundidade 1 nos casos |
| Python abaixo de 3.10 | troque o runtime; o F.I.O. exige 3.10+ |

`limpar_sessao_anterior` apaga o `fio-runtime` da sessão atual.

### 3. Abrir o F.I.O. (frontend e bancada)

A célula abre uma tela simples (telefone, índice da Receita, exportação) **dentro do caderno**, num iframe. De lá, o botão **bancada completa** abre a [bancada](bancada.md) na mesma sessão.

| `exibir` | Quando usar |
|---|---|
| `dentro do caderno` (padrão) | sempre que possível; é o caminho suportado |
| `nova aba (experimental)` | se você quer a bancada em tela cheia; o navegador pode bloquear o proxy direto |

O endereço contém o **token da sessão**: não compartilhe a captura de tela da célula.

### 6. Índice da Receita por UF (pelo caderno)

É a fonte mais forte do F.I.O.: **telefone → empresa → sócios → filiais**, sem internet depois de pronto. O downloader trabalha **um arquivo por vez**, filtra pela UF e apaga o ZIP antes do seguinte. O mesmo índice pode ser montado **pela tela da seção 3**, que também mostra o andamento.

**Roda em segundo plano e mostra o progresso ao vivo** (arquivo atual, MB baixados, velocidade, linhas lidas), atualizado a cada 3 segundos. Leva de 10 a 40 minutos conforme a banda. A célula só **acompanha**: **interromper (■) não cancela** o trabalho; rode a célula de novo para voltar a acompanhar. Marque **executar** para iniciar (sem isso, nada é baixado).

- `uf`: uma ou mais, separadas por vírgula (`MG` ou `MG,SP`). **Reduz o SQLite final e a RAM, não o tráfego**: os arquivos de Estabelecimentos não são divididos por UF.
- `mes` (AAAA-MM): pula a listagem raiz da Receita. Útil quando ela reseta a conexão.
- Se a listagem raiz falhar, o F.I.O. tenta `urllib`, depois `curl` e, por fim, sonda diretamente pastas mensais recentes.
- Retoma downloads interrompidos (`Range` + `If-Range`) e só promove o arquivo depois de validá-lo como ZIP.

### 6b. Já tenho o índice (enviar arquivo ou URL)

Para quando a Receita não responde a partir do Colab. No seu computador: `fio indice baixar --uf MG` (gera `cnpj.sqlite`). Na célula **Enviar índice pronto**, marque **executar** e escolha:

- **enviar arquivo**: abre o seletor do navegador e envia o `cnpj.sqlite` para a sessão;
- **baixar de uma URL**: informe uma URL `https://` sua; o download mostra progresso e retoma se cair.

O arquivo é validado (precisa ter estabelecimentos); se não parecer um índice do F.I.O., é descartado. O índice enviado só existe nesta sessão, como tudo no Colab.

### 7. Caso pontual

Os valores de exemplo usam **alvos institucionais públicos** (CNPJ do Banco do Brasil, CEP da Praça da Sé, `registro.br`). Troque pelos seus só se tiver base legal. Tipos reconhecidos sozinhos: e-mail (tem `@`), CNPJ, CEP (8 dígitos com hífen), domínio (tem ponto e letras) e telefone.

### 8. Relatório

Baixe primeiro o **modelo vazio** se quiser usar o F.I.O. só como roteiro. Depois de um caso, exporte **laudo**, **RELINT** ou **relatório técnico**. **Como a sessão é efêmera, o download é a forma de preservar o resultado.**

## Não carrega? Confira nesta ordem

| Sintoma | Causa provável | Solução |
|---|---|---|
| Iframe em branco ou "carregando…" para sempre | célula executada com a versão antiga do F.I.O. em memória | rode a seção 1 de novo e a 3 (o instalador limpa os módulos antigos) |
| "Token da sessão ausente" | iframe aberto sem rodar a célula da seção 3 nesta sessão | rode a célula da seção 3 de novo |
| Navegador bloqueia cookies/armazenamento de terceiros | iframe sem acesso a `sessionStorage` | a versão ≥ 3.0.2 funciona assim; se estiver na 3.0.1 ou antes, atualize (seção 1 com `origem: github`) |
| `tempo esgotado` / `Failed to connect to dadosabertos.rfb.gov.br` | **a Receita bloqueia faixas de IP de nuvem** (Colab incluído); nenhuma configuração do caderno resolve | monte o índice no **seu computador** (`fio indice baixar --uf MG`) e traga-o pela célula **6b: Enviar índice pronto** (enviar arquivo ou baixar de uma URL sua). Ou siga sem índice: as demais fontes funcionam |
| Seção 6 reseta a conexão | listagem raiz da Receita instável | informe `mes` (AAAA-MM) |
| A célula do índice parece travada | antes da 3.0.4 não havia progresso; um arquivo de Estabelecimentos leva minutos | atualize; a célula agora mostra o andamento a cada 3 s. Se o último aviso tiver mais de 2 minutos, rode a célula de novo (retoma o download) |
| Seção 6 estoura o disco | runtime com pouco espaço | reinicie o runtime e use uma UF |
| "GitHub indisponível; usando a versão embutida" | sem acesso ao GitHub | normal; o caderno segue com a cópia embutida |
| Tudo some | o runtime foi encerrado | por design; baixe os relatórios antes |

Mais em [solução de problemas](solucao-de-problemas.md).

## Para mantenedores

O caderno é **gerado**: `python tools/gerar_notebook.py` (e `--checar` no CI). Nunca edite o `.ipynb` à mão. Ele embute o pacote inteiro em base64 (por isso passa de 300 KB). O CI executa as células do caminho rápido fora do Colab com `nbclient`.
