"""Confere os links relativos e as ancoras dos arquivos Markdown.

Link quebrado em documentacao e o jeito mais barato de perder a confianca de
quem esta aprendendo a ferramenta. So biblioteca padrao; roda no CI.

    python tools/checar_links.py
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ARQUIVOS = [*RAIZ.glob("*.md"), *(RAIZ / "docs").rglob("*.md")]
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)|!\[[^\]]*\]\(([^)\s]+)\)")
CODIGO = re.compile(r"```.*?```", re.S)


def _ancora(titulo: str) -> str:
    """Slug no estilo do GitHub: minusculas, sem pontuacao, espacos viram hifens."""
    t = re.sub(r"[`*_]", "", titulo.strip().lower())
    t = re.sub(r"[^\w\s-]", "", t, flags=re.U)
    return re.sub(r"\s", "-", t)


def _ancoras(arq: Path) -> set[str]:
    texto = CODIGO.sub("", arq.read_text(encoding="utf-8"))
    vistos: dict[str, int] = {}
    saida = set()
    for m in re.finditer(r"^#{1,6}\s+(.+?)\s*$", texto, re.M):
        a = _ancora(m.group(1))
        n = vistos.get(a, 0)
        vistos[a] = n + 1
        saida.add(a if n == 0 else f"{a}-{n}")
    return saida


def main() -> int:
    problemas = []
    cache: dict[Path, set[str]] = {}
    for arq in sorted(ARQUIVOS):
        texto = CODIGO.sub("", arq.read_text(encoding="utf-8"))
        for m in LINK.finditer(texto):
            alvo = m.group(1) or m.group(2)
            if re.match(r"^[a-z]+:", alvo) or alvo.startswith("#") and False:
                continue
            caminho, _, ancora = alvo.partition("#")
            destino = arq if not caminho else (arq.parent / caminho).resolve()
            rel = arq.relative_to(RAIZ)
            if not destino.exists():
                problemas.append(f"{rel}: arquivo inexistente -> {alvo}")
                continue
            if ancora and destino.suffix == ".md":
                if destino not in cache:
                    cache[destino] = _ancoras(destino)
                a = unicodedata.normalize("NFC", ancora.lower())
                if a not in {unicodedata.normalize("NFC", x) for x in cache[destino]}:
                    problemas.append(f"{rel}: ancora inexistente -> {alvo}")
    for p in problemas:
        print(p)
    print(f"{len(ARQUIVOS)} arquivos Markdown; "
          + (f"{len(problemas)} link(s) quebrado(s)" if problemas else "todos os links relativos ok"))
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
