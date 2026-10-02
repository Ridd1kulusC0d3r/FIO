"""Gera docs/guia/referencia-cli.md a partir do argparse real da CLI.

A referencia nunca fica defasada: o CI roda `--checar` e falha se o
arquivo nao bater com o que `fio --help` realmente aceita.

    python tools/gerar_referencia_cli.py            # grava
    python tools/gerar_referencia_cli.py --checar   # so confere
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from fio.cli import construir_parser  # noqa: E402

DESTINO = RAIZ / "docs" / "guia" / "referencia-cli.md"

CABECALHO = """# Referência da linha de comando

> Gerada automaticamente a partir do `argparse` da CLI por
> `tools/gerar_referencia_cli.py`. Não edite à mão: o CI confere que ela
> bate com `fio --help`. Para exemplos de uso, veja o
> [guia de primeiros passos](primeiros-passos.md) e as
> [receitas de uso](receitas-de-uso.md).

Forma geral: `fio [--ator NOME] <comando> [subcomando] [opções]`.
`--ator` identifica quem opera e vai para o ledger. Sem ele, o F.I.O. usa o
usuário do sistema. Todos os dados do caso ficam em `FIO_HOME`
(padrão `~/.fio`).

"""


def _subparsers(p: argparse.ArgumentParser):
    for a in p._actions:
        if isinstance(a, argparse._SubParsersAction):
            return a
    return None


def _ajuda_de(sp: argparse._SubParsersAction) -> dict[str, str]:
    return {ca.dest: (ca.help or "") for ca in sp._choices_actions}


def _opcao(a: argparse.Action) -> str:
    if a.option_strings:
        nome = ", ".join(f"`{o}`" for o in a.option_strings)
        if a.nargs != 0 and not isinstance(a, (argparse._StoreTrueAction,
                                               argparse._StoreFalseAction)):
            nome += f" `{a.metavar or a.dest.upper()}`"
    else:
        nome = f"`{a.metavar or a.dest}` (posicional)"
    return nome


def _linha(a: argparse.Action) -> str:
    obrig = "sim" if (a.required or (not a.option_strings and a.nargs not in ("?", "*"))) else "não"
    extra = []
    if a.choices:
        extra.append("valores: " + ", ".join(f"`{c}`" for c in a.choices))
    if a.default not in (None, False, argparse.SUPPRESS) and a.option_strings:
        extra.append(f"padrão: `{a.default}`")
    desc = (a.help or "").replace("|", "\\|")
    if extra:
        desc = (desc + " " if desc else "") + f"({'; '.join(extra)})"
    return f"| {_opcao(a)} | {obrig} | {desc} |"


def _secao(nome: str, p: argparse.ArgumentParser, ajuda: str, nivel: int) -> list[str]:
    L = [f"{'#' * nivel} `{nome}`", ""]
    if ajuda:
        L += [ajuda[0].upper() + ajuda[1:] + ".", ""]
    L += ["```text", p.format_usage().replace("usage: ", "").strip(), "```", ""]
    itens = [a for a in p._actions
             if not isinstance(a, (argparse._HelpAction, argparse._SubParsersAction,
                                   argparse._VersionAction))]
    if itens:
        L += ["| Opção | Obrigatória | Descrição |", "|---|---|---|"]
        L += [_linha(a) for a in itens]
        L.append("")
    if p.epilog:
        L += [f"> {p.epilog}", ""]
    sp = _subparsers(p)
    if sp:
        ajudas = _ajuda_de(sp)
        for sub, pp in sp.choices.items():
            L += _secao(f"{nome} {sub}", pp, ajudas.get(sub, ""), nivel + 1)
    return L


def gerar() -> str:
    p = construir_parser()
    sp = _subparsers(p)
    ajudas = _ajuda_de(sp)
    L = [CABECALHO.rstrip(), "", "## Índice", ""]
    for nome in sp.choices:
        L.append(f"- [`fio {nome}`](#fio-{nome.replace(' ', '-')}) — {ajudas.get(nome, '')}")
    L.append("")
    for nome, pp in sp.choices.items():
        L += _secao(f"fio {nome}", pp, ajudas.get(nome, ""), 2)
    return "\n".join(L).rstrip() + "\n"


def main() -> int:
    novo = gerar()
    if "--checar" in sys.argv:
        atual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
        if atual != novo:
            print(f"{DESTINO.relative_to(RAIZ)} desatualizado: rode "
                  f"python tools/gerar_referencia_cli.py")
            return 1
        print("referencia da CLI em dia")
        return 0
    DESTINO.write_text(novo, encoding="utf-8")
    print(f"{DESTINO.relative_to(RAIZ)} ({len(novo.splitlines())} linhas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
