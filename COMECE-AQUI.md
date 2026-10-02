# Comece aqui

**Manual completo, com figuras:** abra `docs/MANUAL.html` no navegador (dois cliques).

## Instalar em 3 passos

1. **Instale o Python 3.10 ou mais novo** em <https://www.python.org/downloads/>.
   No Windows, marque a caixa **“Add python.exe to PATH”** na primeira tela do instalador.
2. **Descompacte** o arquivo `fio-lab-3.0.1.zip`.
3. **Dê dois cliques** no lançador do seu sistema, dentro da pasta `fio`:

| Sistema | Arquivo | Observação |
|---|---|---|
| Windows | `Iniciar F.I.O. (Windows).bat` | se aparecer “O Windows protegeu o computador”: *Mais informações* › *Executar assim mesmo* |
| macOS | `Iniciar F.I.O. (Mac).command` | na primeira vez: botão direito › *Abrir* › *Abrir* |
| Linux | `iniciar-fio-linux.sh` | ou, no terminal: `python3 -m fio lab bancada` |

Uma janela preta (ou o Terminal) se abre e o navegador mostra a bancada. **Deixe essa janela
aberta** enquanto usa o programa; para sair, feche-a.

Na primeira vez, o programa monta um **caso de demonstração** com dados inventados. Explore
à vontade: ele não usa internet.

## Quer só testar, sem instalar?

Clique no botão **Abrir no Colab** do repositório no GitHub. Sem GitHub: abra
<https://colab.research.google.com/>, vá em *Arquivo › Fazer upload de notebook*, envie
`colab/FIO_Lab_Colab.ipynb` e use *Ambiente de execução › Executar tudo*. No Colab os dados
ficam em servidores do Google: use para teste e alvos institucionais, não para caso real.

## Antes do seu primeiro caso de verdade

- Todo caso exige **base legal** e **finalidade específica** (LGPD).
- O programa só consulta **fontes públicas** e nunca bases vazadas, senhas de terceiros ou mensagens.
- Uma ligação no mapa indica que duas informações **apareceram juntas numa fonte**. Não é prova de relação entre pessoas.

## Se algo der errado

| Sintoma | O que fazer |
|---|---|
| “Python 3.10 ou mais novo não foi encontrado” | reinstale o Python marcando “Add python.exe to PATH” |
| o navegador não abriu | copie o endereço `http://127.0.0.1:8765/#t=...` que aparece na janela preta |
| a página diz “Token ausente” | use o endereço completo da janela preta; a senha muda a cada início |
| porta ocupada | `python -m fio lab bancada --porta 8770` |
| fontes com ✗ em “Verificar conexões” | a rede bloqueia a fonte; as fontes offline continuam funcionando |

Seus dados ficam em `.fio`, na sua pasta de usuário. Nada é enviado a servidores do F.I.O.

## Quer a fonte mais forte?

Monte o índice da Receita Federal do seu estado (baixa e processa sozinho; pode levar horas):

```bash
python -m fio indice baixar --uf MG
```
