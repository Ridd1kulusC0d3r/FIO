"""Ledger de custodia encadeado por hash.

Cada acao do caso vira uma linha JSONL cujo hash inclui o hash da linha
anterior. Alterar ou remover qualquer registro anterior quebra a cadeia e
verificar() aponta exatamente onde. O artefato bruto de cada coleta e
gravado em disco e referenciado pelo seu proprio SHA-256, de modo que o
relatorio final sempre pode ser reconferido contra o material original.

Nao e assinatura digital nem carimbo de tempo qualificado: prova que o
material nao mudou desde a coleta, nao que a coleta ocorreu naquela hora.
Para a segunda garantia, ancore periodicamente o hash da ultima linha em
um servico de timestamping (RFC 3161) -- o campo ancora existe para isso.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path

GENESE = "0" * 64


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _canonico(d: dict) -> bytes:
    return json.dumps(d, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


@dataclass
class RegistroLedger:
    seq: int
    ts: str
    caso: str
    ator: str
    acao: str
    alvo: str = ""
    coletor: str = ""
    resumo: str = ""
    artefato_sha256: str = ""
    artefato_bytes: int = 0
    metadados: dict = field(default_factory=dict)
    ancora: str = ""
    anterior: str = GENESE
    hash: str = ""

    def calcular_hash(self) -> str:
        corpo = asdict(self)
        corpo.pop("hash", None)
        return _sha256(_canonico(corpo))


class Ledger:
    """Append-only. Nao ha metodo de edicao ou remocao, de proposito."""

    def __init__(self, diretorio: str | Path, caso: str, ator: str = "desconhecido"):
        self.dir = Path(diretorio)
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "artefatos").mkdir(exist_ok=True)
        self.caminho = self.dir / "ledger.jsonl"
        self.caso = caso
        self.ator = ator

    # ---------------------------------------------------------- leitura
    def registros(self) -> list[RegistroLedger]:
        if not self.caminho.exists():
            return []
        saida = []
        for linha in self.caminho.read_text(encoding="utf-8").splitlines():
            if linha.strip():
                saida.append(RegistroLedger(**json.loads(linha)))
        return saida

    def ultimo_hash(self) -> str:
        regs = self.registros()
        return regs[-1].hash if regs else GENESE

    def __len__(self) -> int:
        return len(self.registros())

    # ---------------------------------------------------------- escrita
    def registrar(self, acao: str, alvo: str = "", coletor: str = "",
                  resumo: str = "", artefato: bytes | str | None = None,
                  metadados: dict | None = None) -> RegistroLedger:
        regs = self.registros()
        sha, tam = "", 0
        if artefato is not None:
            dados = artefato.encode("utf-8") if isinstance(artefato, str) else artefato
            sha, tam = _sha256(dados), len(dados)
            destino = self.dir / "artefatos" / f"{sha}.bin"
            if not destino.exists():
                destino.write_bytes(dados)

        r = RegistroLedger(
            seq=len(regs) + 1,
            ts=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            caso=self.caso, ator=self.ator, acao=acao, alvo=alvo,
            coletor=coletor, resumo=resumo, artefato_sha256=sha,
            artefato_bytes=tam, metadados=metadados or {},
            anterior=regs[-1].hash if regs else GENESE,
        )
        r.hash = r.calcular_hash()
        with self.caminho.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
        return r

    # ------------------------------------------------------- verificacao
    def verificar(self) -> tuple[bool, list[str]]:
        """Revalida a cadeia inteira e os artefatos em disco."""
        problemas: list[str] = []
        anterior = GENESE
        for i, r in enumerate(self.registros(), start=1):
            if r.seq != i:
                problemas.append(f"linha {i}: seq={r.seq}, esperado {i}")
            if r.anterior != anterior:
                problemas.append(
                    f"seq {r.seq}: elo quebrado -- anterior={r.anterior[:12]}..., "
                    f"esperado {anterior[:12]}... (registro inserido ou removido)"
                )
            recalc = r.calcular_hash()
            if recalc != r.hash:
                problemas.append(
                    f"seq {r.seq}: conteudo alterado apos a gravacao "
                    f"(hash {r.hash[:12]}... != {recalc[:12]}...)"
                )
            if r.artefato_sha256:
                arq = self.dir / "artefatos" / f"{r.artefato_sha256}.bin"
                if not arq.exists():
                    problemas.append(f"seq {r.seq}: artefato ausente {r.artefato_sha256[:12]}...")
                elif _sha256(arq.read_bytes()) != r.artefato_sha256:
                    problemas.append(f"seq {r.seq}: artefato adulterado em disco")
            anterior = r.hash
        return (not problemas, problemas)

    def artefato(self, sha: str) -> bytes | None:
        arq = self.dir / "artefatos" / f"{sha}.bin"
        return arq.read_bytes() if arq.exists() else None
