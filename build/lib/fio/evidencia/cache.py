"""Cache HTTP em sqlite: nao repita requisicao que ja foi feita.

Alem de educado com a fonte, o cache e requisito metodologico -- a
segunda execucao do caso precisa reproduzir o mesmo material.
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path


class CacheHTTP:
    def __init__(self, caminho: str | Path, ttl_segundos: int = 86400):
        self.caminho = str(caminho)
        self.ttl = ttl_segundos
        self._con = sqlite3.connect(self.caminho)
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS cache ("
            " chave TEXT PRIMARY KEY, url TEXT, status INTEGER,"
            " corpo BLOB, ts REAL)"
        )
        self._con.commit()

    @staticmethod
    def _k(url: str, extra: str = "") -> str:
        return hashlib.sha256((url + "|" + extra).encode()).hexdigest()

    def obter(self, url: str, extra: str = "") -> tuple[int, bytes] | None:
        cur = self._con.execute(
            "SELECT status, corpo, ts FROM cache WHERE chave=?", (self._k(url, extra),)
        )
        linha = cur.fetchone()
        if not linha:
            return None
        status, corpo, ts = linha
        if self.ttl and (time.time() - ts) > self.ttl:
            return None
        return (status, corpo)

    def guardar(self, url: str, status: int, corpo: bytes, extra: str = "") -> None:
        self._con.execute(
            "INSERT OR REPLACE INTO cache VALUES (?,?,?,?,?)",
            (self._k(url, extra), url, status, corpo, time.time()),
        )
        self._con.commit()

    def fechar(self) -> None:
        self._con.close()
