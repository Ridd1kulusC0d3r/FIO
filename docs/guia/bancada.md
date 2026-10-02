# Bancada web

```bash
fio lab bancada --porta 8765
```

Abre `http://127.0.0.1:8765/#t=<token>`. O token vai no *fragmento* da URL,
que não chega a logs nem ao cabeçalho `Referer`, e é exigido em toda rota
`/api`. O servidor escuta só em loopback, confere o cabeçalho `Host` (contra
DNS rebinding) e não envia cabeçalho CORS: outra página aberta no mesmo
navegador não consegue disparar coleta nem ler dado do caso.

Telas: painel, caso, grafo (arrastável, com detalhe por nó), vínculos, agrupamentos,
observações, custódia, experimentos (com comparação entre dois) e quesitos. A
bancada também traz ferramentas BR avulsas, a avaliação sintética e o
inventário de plugins.
