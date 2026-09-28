"""Fila de tarefas em sqlite com workers em thread.

Pequena e suficiente: a bancada enfileira, um worker executa, o navegador
consulta o estado. Sobrevive a reinicio do servidor (tarefas 'rodando'
orfas voltam para 'falhou' na abertura).
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
import threading
import time
import traceback
from contextlib import contextmanager
from pathlib import Path


def _agora() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


class Fila:
    def __init__(self, caminho: Path):
        self.caminho = str(caminho)
        self._trava = threading.Lock()
        self.manipuladores: dict = {}
        self._parar = threading.Event()
        with self._con() as c:
            c.execute("CREATE TABLE IF NOT EXISTS tarefa (id INTEGER PRIMARY KEY,"
                      " tipo TEXT, caso TEXT, params TEXT, estado TEXT, criada TEXT,"
                      " iniciada TEXT, concluida TEXT, resultado TEXT, erro TEXT,"
                      " progresso TEXT)")
            c.execute("UPDATE tarefa SET estado='falhou', erro='servidor reiniciado'"
                      " WHERE estado='rodando'")

    @contextmanager
    def _con(self):
        """Conexao curta e realmente fechada ao sair do bloco.

        O context manager nativo de sqlite3 faz commit/rollback, mas nao fecha
        o descritor. Linux permite apagar o arquivo aberto; Windows nao.
        """
        con = sqlite3.connect(self.caminho, timeout=30)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def registrar(self, tipo: str, fn) -> None:
        self.manipuladores[tipo] = fn

    def enfileirar(self, tipo: str, caso: str, params: dict) -> int:
        with self._trava, self._con() as c:
            cur = c.execute("INSERT INTO tarefa (tipo, caso, params, estado, criada)"
                            " VALUES (?,?,?,?,?)",
                            (tipo, caso, json.dumps(params), "fila", _agora()))
            return cur.lastrowid

    def obter(self, tid: int) -> dict | None:
        with self._con() as c:
            r = c.execute("SELECT * FROM tarefa WHERE id=?", (tid,)).fetchone()
        if not r:
            return None
        d = dict(r)
        for k in ("params", "resultado"):
            d[k] = json.loads(d[k]) if d[k] else None
        return d

    def listar(self, limite: int = 30) -> list[dict]:
        with self._con() as c:
            rows = c.execute("SELECT id, tipo, caso, estado, criada, concluida, erro,"
                             " progresso FROM tarefa ORDER BY id DESC LIMIT ?",
                             (limite,)).fetchall()
        return [dict(r) for r in rows]

    def _progresso(self, tid: int, texto: str) -> None:
        with self._con() as c:
            c.execute("UPDATE tarefa SET progresso=? WHERE id=?", (texto[-400:], tid))

    def _pegar(self) -> dict | None:
        with self._trava, self._con() as c:
            r = c.execute("SELECT * FROM tarefa WHERE estado='fila' ORDER BY id LIMIT 1").fetchone()
            if not r:
                return None
            c.execute("UPDATE tarefa SET estado='rodando', iniciada=? WHERE id=?",
                      (_agora(), r["id"]))
            return dict(r)

    def _worker(self) -> None:
        while not self._parar.is_set():
            try:
                t = self._pegar()
            except sqlite3.Error:
                # base removida ou indisponivel (fim de sessao, disco): encerra
                if not Path(self.caminho).exists():
                    return
                time.sleep(1)
                continue
            if not t:
                time.sleep(0.4)
                continue
            fn = self.manipuladores.get(t["tipo"])
            linhas: list[str] = []

            def log(s: str, _tid=t["id"]):
                linhas.append(s)
                self._progresso(_tid, "\n".join(linhas[-12:]))
            try:
                if not fn:
                    raise KeyError(f"tipo de tarefa sem manipulador: {t['tipo']}")
                res = fn(t["caso"], json.loads(t["params"] or "{}"), log)
                with self._con() as c:
                    c.execute("UPDATE tarefa SET estado='concluida', concluida=?,"
                              " resultado=? WHERE id=?",
                              (_agora(), json.dumps(res, default=str), t["id"]))
            except Exception as e:
                with self._con() as c:
                    c.execute("UPDATE tarefa SET estado='falhou', concluida=?, erro=?"
                              " WHERE id=?",
                              (_agora(), f"{type(e).__name__}: {e}\n"
                                         f"{traceback.format_exc()[-800:]}", t["id"]))

    def iniciar(self, n: int = 1) -> None:
        for i in range(n):
            threading.Thread(target=self._worker, daemon=True,
                             name=f"fio-worker-{i}").start()

    def parar(self) -> None:
        self._parar.set()
