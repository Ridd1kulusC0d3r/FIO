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
