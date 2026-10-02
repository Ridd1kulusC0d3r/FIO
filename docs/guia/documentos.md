# Documentos brasileiros

```bash
fio doc cnpj 12.ABC.345/01DE-35          # alfanumérico, exemplo oficial RFB
fio doc cpf-parcial '***456789**'        # região fiscal a partir da máscara
fio doc placa ABC1234                     # -> ABC1C34
fio doc extrair ata.txt                   # tudo o que houver no texto
```

O 9º dígito do CPF indica a região fiscal de emissão, e **a máscara com que
a Receita publica o CPF de sócios (`***456789**`) deixa esse dígito
visível**. Dá para situar regionalmente um sócio sem ver o CPF completo.

## Identificadores financeiros

```bash
fio doc boleto 00191.23454 67890.123457 67890.123457 9 90000000012345   # linha digitável (47 dígitos)
fio doc pix-evp 123e4567-e89b-42d3-a456-426614174000                    # chave aleatória
fio doc cnh 12345678900
fio doc cns 700000000000000
```

- **Boleto:** valida os três DV de módulo 10 dos campos e o DV geral de módulo 11; devolve banco emissor, valor e as datas de vencimento possíveis (o fator reiniciou em 22/02/2025). `fio doc extrair` acha linha digitável em texto livre sem confundir o último bloco com um CNPJ.
- **Chave PIX:** `classificar_chave_pix` distingue CPF, CNPJ, telefone, e-mail e chave aleatória (EVP). A EVP é um UUID v4 e não identifica o titular.
- **CNH e CNS:** só validação. Não saem da extração de texto porque colidem com CPF e telefone.

Tudo é aritmética sobre o próprio identificador; nada consulta banco, titular ou beneficiário.
