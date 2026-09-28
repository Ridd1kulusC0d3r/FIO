# Segurança

## Como reportar uma vulnerabilidade

Não abra issue pública. Use **Security › Report a vulnerability** neste repositório
(relato privado do GitHub). Respondemos em até 7 dias.

## Superfície conhecida

| Componente | Proteção |
|---|---|
| Bancada web | escuta só em 127.0.0.1; token aleatório por sessão exigido em toda rota `/api`; checagem de `Host` contra DNS rebinding; sem CORS; CSP restritiva; `X-Frame-Options: DENY` |
| Modo Colab da bancada | aceita o Host do proxy autenticado do Google e exibição em iframe; o token continua obrigatório |
| Ledger | append-only, encadeado por SHA-256; alteração e remoção detectadas por `fio ledger verificar` |
| Plugins | código de terceiros roda com os mesmos privilégios do usuário; o SHA-256 de cada plugin entra no registro do experimento. Só instale plugins que você leu |

## Fora do escopo

Bloqueio de coleta por fontes externas, limites de taxa de APIs públicas e indisponibilidade
de serviços de terceiros.
