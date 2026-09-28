# Relatório de testes em nuvem — F.I.O. Lab 2.2.0

Execução em ambiente Linux na nuvem (x86_64), 28/09/2026, a partir do pacote descompactado do zero.

## Matriz de versões do Python

| Python | Resultado |
|---|---|
| 3.10.20 | 82 testes, OK (1 pulado: navegador) |
| 3.11.15 | 82 testes, OK |
| 3.12.3 | 82 testes, OK (1 pulado: navegador) |
| 3.13.13 | 82 testes, OK (1 pulado: navegador) |
| 3.14.0rc2 | 82 testes, OK (1 pulado: navegador) |

O teste de navegador só roda onde o Playwright está instalado (3.11 neste ambiente). Ele não é
dependência do F.I.O., só do ambiente de teste.

## Baterias

| Bateria | Arquivo | Resultado | Cobre |
|---|---|---|---|
| Unitários | `testes/test_fio.py`, `testes/test_lab.py` | OK | normalização, documentos BR, política, ledger, grafo, analisadores, receitas, sintético, avaliação, reprodutibilidade, API da bancada |
| Receita por UF | `testes/test_receita.py` | OK | repositório da Receita simulado: descoberta do mês mais recente, queda no meio do download com retomada, filtro por UF em duas passagens, arquivos apagados após processar, benchmark real sem nomes na saída, modo Colab da bancada |
| Integração HTTP | `testes/test_integracao_http.py` | OK | servidor local que imita BrasilAPI, ViaCEP, Querido Diário, RDAP, busca e HIBP; gzip, cache, 404, ledger com artefato bruto; coletores locais; plugins; relatórios; CLI em processo |
| Navegador | `testes/test_e2e_bancada.py` | OK | jornada completa em Chromium, desktop claro e celular escuro, sem erro de JavaScript; token some da barra de endereço; página sem token avisa |
| Fumaça da CLI | `testes/fumaca.py` | 23/23 | fluxo completo em subprocesso, recusa de finalidade vaga, detecção de ledger adulterado, bancada respondendo com token |
| Cobertura | coverage.py | 85% das linhas | a CLI é exercitada também pela fumaça, que roda fora da medição |

## O que NÃO foi testado aqui

- **Fontes reais na internet.** A rede do ambiente de teste bloqueia essas APIs
  (`connect_rejected` no proxy de saída). Os nomes de campo da resposta da BrasilAPI foram
  conferidos na documentação publicada da API. `testes/ao_vivo.py` faz o teste real com alvos
  neutros e roda no CI.
- **Windows e macOS.** Não havia máquina com esses sistemas. O workflow
  `.github/workflows/testes.yml` roda a mesma bateria em Windows, macOS e Linux, com Python
  3.10 a 3.14, a cada envio ao GitHub, e toda segunda-feira testa as fontes reais.

## Como repetir

```bash
python -m unittest discover -s testes -v
python testes/fumaca.py
python testes/ao_vivo.py          # precisa de internet
```

## Caderno do Google Colab (3.0)

`colab/FIO_Lab_Colab.ipynb` é gerado por `tools/gerar_notebook.py` (só biblioteca padrão) e
foi executado de ponta a ponta com nbclient fora do Colab, apontando a seção 5 para um
repositório da Receita simulado: 11 de 11 células sem erro, índice montado, benchmark real
rodado, suíte 82/82 de dentro do caderno. O CI repete a execução a cada push e falha se o
caderno não corresponder ao código.

Na validação 2.2.0, precisavam de uma sessão real do Colab: túnel da bancada (iframe e nova aba), montagem do Drive e download de arquivos. Na 2.2.1 o Drive foi removido; continuam dependentes de uma sessão real o proxy/iframe, os downloads pelo navegador e, principalmente, a base real da Receita e as APIs públicas, que a rede deste ambiente de teste bloqueia.

## Efeito medido da nova nota de confiança

Avaliação sintética, 10 mundos × 15 grupos:

| Configuração | Precisão | Revocação | F1 |
|---|---|---|---|
| 2.1, melhor caso (poda de intermediários) | 0,774 ± 0,184 | 0,857 ± 0,084 | 0,796 ± 0,133 |
| 2.2, confiança mínima 0,4, sem poda | 0,878 ± 0,058 | 0,857 ± 0,084 | 0,865 ± 0,055 |


## Validação incremental — F.I.O. Lab 2.2.1

A correção do Colab foi validada isoladamente em Python 3.13 com `FIO_SEM_E2E=1`: **84 testes, OK (1 pulado: navegador/Playwright)**. O conjunto adicional cobre a descoberta direta por mês quando a listagem raiz da Receita falha, o frontend simplificado do Colab, a exigência de token e o download do modelo de relatório.

A edição Colab 2.2.1 é **somente efêmera**: não monta Google Drive. Casos, fila e índice ficam em `/content/fio-runtime`; persistem apenas os relatórios/modelos baixados explicitamente. A validação contra a base real da Receita e o proxy/iframe do Colab continua dependendo de uma sessão real com acesso externo.
