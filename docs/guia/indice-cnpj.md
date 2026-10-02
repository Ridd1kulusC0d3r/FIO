# Índice reverso dos Dados Abertos do CNPJ

```bash
# baixa o mês mais recente, retoma quedas e mantém só MG no SQLite final
fio indice baixar --uf MG --saida ~/.fio/cnpj-mg.sqlite

# múltiplas UFs; use --manter-zips só quando realmente quiser gastar disco
fio indice baixar --uf MG,SP --tmp /caminho/temporario
```

O downloader processa **um ZIP por vez** e remove o arquivo depois. A Receita não
distribui Estabelecimentos por estado, então `--uf` **reduz o índice final e a RAM,
não o volume baixado**. As raízes aceitas ficam numa tabela SQLite auxiliar durante
a construção; Empresas e Sócios são filtrados em lotes contra esse escopo, sem
manter milhões de CNPJs em um `set` Python. Downloads parciais usam `Range` +
`If-Range` e reiniciam apenas o arquivo atual se o objeto remoto mudar. Antes do
rename atômico, o `.parcial` é aberto e validado como ZIP; resposta HTTP completa
mas corrompida nunca vira cache definitivo. Os índices SQLite de telefone, e-mail,
raiz e sócio são criados **depois** da carga filtrada e então recebem `ANALYZE`,
evitando manter seis B-trees atualizadas durante milhões de inserts.

## A Receita não responde de dentro de nuvem

O servidor dos Dados Abertos do CNPJ (`dadosabertos.rfb.gov.br`) costuma **recusar conexões de faixas de IP de nuvem** (Google Colab, GitHub Actions, provedores de hospedagem). O sintoma é `tempo esgotado` / `Failed to connect ... Timeout was reached`. O F.I.O. detecta isso e **para na hora**, em vez de sondar mês a mês, com a mensagem do que fazer:

1. no **seu computador**: `fio indice baixar --uf MG` (gera `cnpj.sqlite`);
2. leve o arquivo ao ambiente em nuvem (no Colab, a célula **Enviar índice pronto**) ou aponte `FIO_INDICE_CNPJ` para ele;
3. ou siga sem o índice: as demais fontes continuam funcionando.

Reset de conexão e erros HTTP são tratados de outra forma: continuam sendo tentados em outros transportes e pastas.
