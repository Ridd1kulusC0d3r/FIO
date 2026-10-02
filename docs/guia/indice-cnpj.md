# Índice reverso dos Dados Abertos do CNPJ

O índice liga **telefone → empresa → sócios → filiais** sem internet depois de pronto. Há três jeitos de tê-lo, do mais rápido ao mais lento:

| Jeito | Tempo | Download | Quando usar |
|---|---|---|---|
| **Índice pronto** (`--pronto`) | **segundos** | poucas centenas de MB, comprimido | quase sempre; funciona de qualquer ambiente, **inclusive Colab** |
| **Direto da Receita, leve** (`--leve`) | 10 a 40 min | alguns GB (a Receita não divide por UF) | para **gerar** o índice pronto, ou se não houver um publicado |
| **Direto da Receita, completo** | 10 a 40 min | alguns GB | se precisar de endereço completo e CNAE |

```bash
fio indice baixar --uf MG --pronto        # rápido: baixa o arquivo ja montado (SHA-256 conferido)
fio indice baixar --uf MG,SP --pronto     # varias UFs: mescla num so banco
fio indice baixar --uf MG --leve          # lento, mas enxuto
fio indice baixar --uf MG                 # lento e completo
fio indice status
```

## Índice pronto

O arquivo `cnpj-UF.sqlite.xz` (e o manifesto `.json` ao lado, com o SHA-256) vem da Release **`indice-latest`** do repositório. O download **retoma** se cair e só é aceito depois de conferido: se o arquivo vier truncado ou adulterado, nada é instalado.

- **UF sem arquivo publicado:** `erro: nao ha indice pronto em … (404)`; monte pela Receita ou publique um.
- **Outro endereço:** `fio indice baixar --uf MG --pronto --de https://meu.servidor/indices/` (qualquer URL https que sirva os dois arquivos).
- **No Colab e na bancada:** o padrão já é `auto`: tenta o pronto e, se não existir, monta pela Receita em modo leve.

### Publicar o seu

Num computador que **alcance a Receita** (a Receita costuma bloquear IPs de nuvem):

```bash
fio indice baixar --uf MG,SP --leve                       # um download serve a todas as UFs
fio indice exportar --uf MG --para cnpj-MG.sqlite.xz      # um arquivo por UF
fio indice exportar --uf SP --para cnpj-SP.sqlite.xz
gh release upload indice-latest cnpj-MG.sqlite.xz* cnpj-SP.sqlite.xz* --clobber
```

O workflow **`indice`** (`.github/workflows/indice.yml`) faz isso todo dia 8 do mês e sob demanda (*Actions › indice › Run workflow*, com as UFs). Se o servidor da Receita não aceitar conexão do runner, ele **avisa e termina verde**, e você publica pelo seu computador como acima.

## Modo leve

`--leve` guarda só o que a **busca por telefone e e-mail** usa:

- estabelecimentos **com telefone ou e-mail** (e a **matriz**, que ancora a razão social e as filiais); os sem contato não têm como ser achados por busca reversa;
- sem logradouro, bairro e CNAE (ficam CEP, município e UF);
- empresas e sócios só das raízes que sobraram.

A busca por telefone devolve **os mesmos CNPJs** que o índice completo (há teste automatizado que compara). O que se perde: a observação textual do endereço e o CNAE. O tamanho final depende dos dados reais de cada mês; num mundo sintético a redução foi de ~44% no SQLite e a compressão xz ainda divide por ~5.

## Índice completo, por UF

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
