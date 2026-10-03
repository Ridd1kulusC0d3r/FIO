# Pesquisa rápida e leve

Como o F.I.O. evita baixar muito e esperar muito, e como pedir ainda menos.

## Resumo

| O que pesa | Antes | Agora |
|---|---|---|
| **Ter o índice da Receita** | baixar alguns GB e processar milhões de linhas: 10 a 40 min (e a Receita bloqueia IPs de nuvem) | **índice pronto**: um arquivo pequeno, **segundos**, de qualquer ambiente |
| **Tamanho do índice** | completo (endereço, CNAE, estabelecimentos sem contato) | **leve**: só o que a busca por telefone/e-mail usa; mesmos resultados |
| **Fontes online de um alvo** | uma de cada vez | até 4 **em paralelo** (o intervalo por host continua valendo) |
| **Gravar a cadeia de custódia** | relia o arquivo inteiro a cada registro | só o final: custo constante |
| **Calcular pontes/caminhos no grafo** | varria todas as arestas a cada passo | vizinhança em cache |
| **Busca na web** | 10 recortes por alvo | `--rapido`: 3 recortes |

Medição (mundo sintético de 60 grupos, 163 telefones, 936 entidades, **tudo offline**, Python 3.11): o pipeline completo foi de **40,4 s para 3,8 s** (10,6×). Em coleta online o ganho depende das fontes: com 4 fontes de rede de ~0,4 s cada, a coleta de um alvo foi de ~1,6 s para ~0,4 s (teste automatizado).

## Do jeito mais rápido

```bash
fio indice baixar --uf MG --pronto                 # segundos
fio lab pipeline --caso MEU --rapido --orcamento 60
```

- **`--rapido`**: fontes lentas fazem menos consultas (a busca na web usa 3 recortes de maior retorno).
- **`--orcamento SEGUNDOS`**: limite de tempo de coleta. Esgotado, o F.I.O. **não abre novas consultas**, registra `orcamento.esgotado` no ledger e entrega o que já tem. Consultas já em andamento terminam no próprio tempo limite.
- **`--paralelo N`** (padrão 4): quantos coletores de **rede** de um mesmo alvo rodam juntos. `1` volta ao modo em sequência. Os coletores **locais** (plano de numeração, índice, documentos) sempre rodam em sequência: são rápidos.
- **`--offline`**: nenhuma consulta de rede; só índice local e documentos.
- **`--intervalo S`**: pausa por host (padrão 1,5 s). Não baixe sem necessidade: é a educação com a fonte.

## O que continua igual

- **Resultado idêntico:** o grafo é montado na thread principal, na ordem declarada dos coletores; quem termina primeiro não muda o resultado. Há teste que compara o grafo sequencial com o paralelo.
- **Cadeia de custódia íntegra:** a gravação do ledger é serializada por arquivo; `fio ledger verificar` passa depois de coleta concorrente (também testado).
- **Escopo:** conferido a cada alvo, como sempre.
- **Cache:** respostas de fontes ficam 24 h em `cache.sqlite` por caso; a segunda execução não repete a requisição.

## Se ainda estiver lento

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Caso demora minutos com fontes online | fontes lentas ou bloqueando | `--rapido --orcamento 60`; veja `fio ledger listar` para saber qual fonte demora |
| `web` quase sempre vazia | índice público bloqueou (anti-robô) | o baseline descarta a página de bloqueio; use `fio dorks --urls` |
| Índice pronto não existe para a UF | ninguém publicou | [publique](indice-cnpj.md#publicar-o-seu) ou monte com `--leve` |
| `fio indice baixar` (sem `--pronto`) lento | é o caminho pela Receita | use `--pronto`; veja [índice do CNPJ](indice-cnpj.md) |
