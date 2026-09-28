"""Troca o marcador SEU-USUARIO/fio-lab pelo seu repositorio real e
regenera o caderno do Colab.

    python tools/configurar_repositorio.py seu-usuario/fio-lab
"""

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ARQUIVOS = ["README.md", "CITATION.cff", "CONTRIBUTING.md", "pyproject.toml",
            "COMECE-AQUI.md", "tools/repositorio.txt"]


def main() -> int:
    if len(sys.argv) != 2 or not re.fullmatch(r"[\w.-]+/[\w.-]+", sys.argv[1]):
        print(__doc__)
        return 2
    novo = sys.argv[1]
    atual = (RAIZ / "tools" / "repositorio.txt").read_text(encoding="utf-8").strip()
    for nome in ARQUIVOS:
        p = RAIZ / nome
        if p.exists():
            texto = p.read_text(encoding="utf-8")
            dono_a, nome_a = atual.split("/")
            dono_n, nome_n = novo.split("/")
            troca = texto.replace(f"{dono_a}.github.io/{nome_a}", f"{dono_n}.github.io/{nome_n}")
            troca = troca.replace(atual, novo)
            if troca != texto:
                p.write_text(troca, encoding="utf-8")
                print("atualizado:", nome)
    subprocess.run([sys.executable, str(RAIZ / "tools" / "gerar_notebook.py")], check=True)
    print(f"\nPronto. Badge do Colab: https://colab.research.google.com/github/{novo}/blob/main/colab/FIO_Lab_Colab.ipynb")
    return 0


if __name__ == "__main__":
    sys.exit(main())
