#!/bin/bash
cd "$(dirname "$0")"
echo ""
echo " F.I.O. Lab - abrindo a bancada no seu navegador..."
echo " (esta janela precisa ficar aberta enquanto voce usa o programa)"
echo ""
if ! command -v python3 >/dev/null || ! python3 -c 'import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)'; then
  echo " [!] Python 3.10 ou mais novo nao foi encontrado."
  echo "     Instale em https://www.python.org/downloads/ e abra este arquivo de novo."
  read -n 1 -s -r -p " Pressione qualquer tecla para fechar."
  exit 1
fi
python3 -m fio demo
python3 -m fio lab bancada
