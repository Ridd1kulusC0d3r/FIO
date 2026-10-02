"""Manifesto do caso: SHA-256 de cada peca entregue, amarrado ao ledger.

O ledger prova que o material coletado nao mudou. O manifesto estende a
garantia ao que sai do caso: grafo, relatorios, experimentos. Ele grava o
hash de cada arquivo, o ultimo hash do ledger e o hash do proprio corpo do
manifesto. `verificar` refaz tudo e aponta o que mudou.

Fica de fora de proposito: `cache.sqlite` (derivavel) e `manifesto.json`
(auto-referencia). Os artefatos brutos ja estao cobertos pelo ledger.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

from .ledger import Ledger
from .. import __version__

NOME = "manifesto.json"
# ledger.jsonl cresce a cada acao (inclusive a de gerar o manifesto); ele e
# verificado pela cadeia de hashes, nao pelo hash do arquivo inteiro.
IGNORAR = {"cache.sqlite", "ledger.jsonl", NOME}


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _pecas(dir_caso: Path, extras: list[Path]) -> list[Path]:
    achados = []
    for p in sorted(dir_caso.rglob("*")):
        if not p.is_file() or p.name in IGNORAR:
            continue
        rel = p.relative_to(dir_caso)
        if rel.parts[0] in ("artefatos", "__pycache__"):
            continue
        achados.append(p)
    for e in extras:
        e = Path(e)
        if e.is_file() and e not in achados:
            achados.append(e)
    return achados


def _corpo_sha(corpo: dict) -> str:
    base = {k: v for k, v in corpo.items() if k != "manifesto_sha256"}
    return hashlib.sha256(json.dumps(base, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def gerar(dir_caso: str | Path, caso_id: str = "",
          extras: list[Path] | None = None) -> dict:
    d = Path(dir_caso)
    led = Ledger(d, caso_id or d.name)
    regs = led.registros()
    pecas = {}
    for p in _pecas(d, extras or []):
        try:
            chave = str(p.relative_to(d))
        except ValueError:
            chave = f"externo/{p.name}"
        pecas[chave] = {"sha256": _sha(p), "bytes": p.stat().st_size,
                        "origem": str(p) if chave.startswith("externo/") else ""}
    corpo = {
        "caso": caso_id or d.name,
        "gerado_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "versao_fio": __version__,
        "ledger": {"registros": len(regs),
                   "ultimo_hash": regs[-1].hash if regs else ""},
        "artefatos_brutos": len(list((d / "artefatos").glob("*.bin")))
        if (d / "artefatos").exists() else 0,
        "pecas": pecas,
    }
    corpo["manifesto_sha256"] = _corpo_sha(corpo)
    return corpo


def gravar(dir_caso: str | Path, caso_id: str = "",
           extras: list[Path] | None = None) -> Path:
    d = Path(dir_caso)
    m = gerar(d, caso_id, extras)
    destino = d / NOME
    destino.write_text(json.dumps(m, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    Ledger(d, m["caso"]).registrar(
        "manifesto.gerado", alvo=m["caso"],
        resumo=f"{len(m['pecas'])} pecas; manifesto {m['manifesto_sha256'][:16]}")
    return destino


def verificar(dir_caso: str | Path) -> tuple[bool, list[str]]:
    d = Path(dir_caso)
    arq = d / NOME
    if not arq.exists():
        return False, [f"{NOME} ausente: gere com 'fio manifesto gerar'"]
    m = json.loads(arq.read_text(encoding="utf-8"))
    problemas: list[str] = []
    if _corpo_sha(m) != m.get("manifesto_sha256"):
        problemas.append("o proprio manifesto foi alterado")
    for chave, info in m.get("pecas", {}).items():
        p = Path(info["origem"]) if chave.startswith("externo/") else d / chave
        if not p.exists():
            problemas.append(f"peca ausente: {chave}")
        elif _sha(p) != info["sha256"]:
            problemas.append(f"peca alterada: {chave}")
    led = Ledger(d, m.get("caso", d.name))
    ok_led, probs_led = led.verificar()
    problemas += [f"ledger: {x}" for x in probs_led]
    regs = led.registros()
    # o ledger so cresce: o hash do manifesto precisa estar na cadeia atual
    alvo_n = m.get("ledger", {}).get("registros", 0)
    if alvo_n > len(regs):
        problemas.append("ledger tem menos registros do que na emissao do manifesto")
    elif alvo_n and regs[alvo_n - 1].hash != m["ledger"]["ultimo_hash"]:
        problemas.append("ledger reescrito: o hash da emissao nao esta na cadeia")
    return (not problemas, problemas)
