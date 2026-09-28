"""Descoberta de plugins.

Um plugin e um arquivo .py em FIO_HOME/plugins/ que usa os decoradores
@registrar (coletor) ou @registrar_analisador. Nada de entry points nem
pacote instalado: soltou o arquivo, o lab carrega. Cada plugin carregado
entra no registro de experimento com o SHA-256 do arquivo, porque um
resultado produzido por codigo de terceiro precisa dizer QUAL codigo.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

from ..caso import raiz
from ..coletores import REGISTRO
from ..analise import ANALISADORES

_CARREGADOS: dict[str, dict] = {}


def carregar(pasta: Path | None = None) -> dict[str, dict]:
    pasta = pasta or (raiz() / "plugins")
    if not pasta.exists():
        return _CARREGADOS
    for arq in sorted(pasta.glob("*.py")):
        if arq.name.startswith("_") or str(arq) in _CARREGADOS:
            continue
        antes_c, antes_a = set(REGISTRO), set(ANALISADORES)
        sha = hashlib.sha256(arq.read_bytes()).hexdigest()
        info = {"arquivo": str(arq), "sha256": sha, "coletores": [],
                "analisadores": [], "erro": None}
        try:
            spec = importlib.util.spec_from_file_location(f"fio_plugin_{arq.stem}", arq)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
        except Exception as e:           # plugin quebrado nao derruba o lab
            info["erro"] = f"{type(e).__name__}: {e}"
        for n in set(REGISTRO) - antes_c:
            REGISTRO[n].origem = f"plugin:{arq.name}"
            info["coletores"].append(n)
        for n in set(ANALISADORES) - antes_a:
            ANALISADORES[n].origem = f"plugin:{arq.name}"
            info["analisadores"].append(n)
        _CARREGADOS[str(arq)] = info
    return _CARREGADOS


def inventario() -> dict:
    carregar()
    por_estagio: dict[str, list[dict]] = {}
    for n, c in sorted(REGISTRO.items()):
        por_estagio.setdefault(c.estagio, []).append({
            "nome": n, "descricao": c.descricao, "admiralty": c.admiralty,
            "rede": c.requer_rede, "segredo": c.requer_segredo,
            "alvos": list(c.tipos_alvo), "origem": c.origem,
            "reserva": c.reserva})
    return {"coletores": por_estagio,
            "analisadores": [{"nome": n, "descricao": a.descricao, "origem": a.origem}
                             for n, a in sorted(ANALISADORES.items())],
            "plugins": list(_CARREGADOS.values())}


def assinatura_codigo() -> dict:
    """Hash do codigo-fonte do pacote + plugins: 'qual versao produziu isto'."""
    from .. import __version__
    base = Path(__file__).resolve().parents[1]
    h = hashlib.sha256()
    for arq in sorted(base.rglob("*.py")):
        h.update(arq.relative_to(base).as_posix().encode())
        h.update(arq.read_bytes())
    return {"versao": __version__, "sha256_pacote": h.hexdigest(),
            "plugins": {Path(k).name: v["sha256"] for k, v in _CARREGADOS.items()}}
