"""Indice reverso local a partir dos Dados Abertos do CNPJ (Receita Federal).

Esta e a peca que resolve de verdade "telefone -> cadastro" no Brasil sem
tocar em base vazada. A Receita Federal publica o cadastro completo de
CNPJ em dados abertos (arquivos Estabelecimentos, Empresas e Socios, em
CSV, atualizados mensalmente e de download livre em
dados.gov.br / arquivos.receitafederal.gov.br). Cada estabelecimento traz
DDD e telefone declarados. Invertendo a chave, o telefone passa a apontar
para o cadastro -- que por sua vez aponta para o quadro societario.

O caminho completo fica: telefone -> estabelecimento -> CNPJ basico ->
socios (pessoas) e demais estabelecimentos da mesma empresa (o grupo).

Tudo local, reproduzivel, citavel e licito. A contrapartida e que so
alcanca linhas declaradas a Receita por pessoa juridica -- telefone
pessoal de pessoa fisica nao esta aqui, e nao deve estar.

Construcao:
    fio indice construir --origem /dados/cnpj/ --saida ~/.fio/cnpj.sqlite
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS estabelecimento (
  cnpj TEXT PRIMARY KEY, cnpj_basico TEXT, matriz INTEGER, nome_fantasia TEXT,
  situacao TEXT, uf TEXT, municipio TEXT, bairro TEXT, logradouro TEXT,
  cep TEXT, email TEXT, e164_1 TEXT, e164_2 TEXT, inicio TEXT, cnae TEXT);
CREATE INDEX IF NOT EXISTS ix_tel1 ON estabelecimento(e164_1);
CREATE INDEX IF NOT EXISTS ix_tel2 ON estabelecimento(e164_2);
CREATE INDEX IF NOT EXISTS ix_email ON estabelecimento(email);
CREATE INDEX IF NOT EXISTS ix_basico ON estabelecimento(cnpj_basico);

CREATE TABLE IF NOT EXISTS empresa (
  cnpj_basico TEXT PRIMARY KEY, razao_social TEXT, natureza TEXT,
  capital TEXT, porte TEXT);

CREATE TABLE IF NOT EXISTS socio (
  cnpj_basico TEXT, nome TEXT, doc TEXT, qualificacao TEXT,
  entrada TEXT, representante TEXT);
CREATE INDEX IF NOT EXISTS ix_socio_basico ON socio(cnpj_basico);
CREATE INDEX IF NOT EXISTS ix_socio_nome ON socio(nome);
"""


def _e164(ddd: str, num: str) -> str | None:
    ddd = "".join(ch for ch in (ddd or "") if ch.isdigit())
    num = "".join(ch for ch in (num or "") if ch.isdigit())
    if len(ddd) != 2 or len(num) not in (8, 9):
        return None
    return f"+55{ddd}{num}"


def _linhas(caminho: Path):
    """Le o CSV da Receita direto do arquivo ou de dentro do .zip baixado
    (quem esta comecando nao deveria ter de descompactar 30 arquivos)."""
    if caminho.suffix.lower() == ".zip":
        import io
        import zipfile
        with zipfile.ZipFile(caminho) as z:
            for nome in z.namelist():
                with z.open(nome) as bruto:
                    fh = io.TextIOWrapper(bruto, encoding="latin-1", errors="replace", newline="")
                    yield from csv.reader(fh, delimiter=";", quotechar='"')
        return
    with caminho.open(encoding="latin-1", errors="replace", newline="") as fh:
        for linha in csv.reader(fh, delimiter=";", quotechar='"'):
            yield linha


class Construtor:
    """Monta o índice em etapas, com baixo uso de RAM e filtro por UF.

    A UF só existe em ``Estabelecimentos``. Quando há filtro, as raízes de
    CNPJ aceitas são persistidas numa tabela auxiliar SQLite em vez de um
    ``set`` Python. Isso evita que um estado grande consuma centenas de MB
    (ou mais) de RAM no Colab. ``Empresas`` e ``Sócios`` são filtrados em
    lotes contra esse escopo local.

    Estabelecimentos precisa vir antes de Empresas/Sócios. Os chamadores
    públicos (`construir` e `receita_download.montar`) já impõem essa ordem.
    """

    LOTE_EST = 20_000
    LOTE_DIM = 50_000
    LOTE_SQL_IN = 800  # abaixo do limite de variáveis do SQLite mais antigo

    def __init__(self, saida: str | Path, ufs: set[str] | None = None,
                 log=lambda s: print(s, file=sys.stderr)):
        self.saida = Path(saida)
        self.con = sqlite3.connect(str(self.saida))
        # O arquivo é provisório durante a construção. Priorizar throughput é
        # seguro aqui porque só renomeamos para o destino após finalizar.
        self.con.execute("PRAGMA synchronous=OFF")
        self.con.execute("PRAGMA temp_store=FILE")
        self.con.execute("PRAGMA cache_size=-65536")  # ~64 MiB
        self.con.executescript(ESQUEMA)
        self.con.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
        self.ufs = {u.upper() for u in ufs} if ufs else None
        self.log = log
        self._viu_estabelecimentos = False
        if self.ufs:
            self.con.execute(
                "CREATE TABLE IF NOT EXISTS escopo_uf (cnpj_basico TEXT PRIMARY KEY) WITHOUT ROWID"
            )
        self.contagem = {"estabelecimentos": 0, "empresas": 0, "socios": 0,
                         "telefones": 0, "descartados_por_uf": 0,
                         "raizes_uf": 0}

    def estabelecimentos(self, arq: Path) -> None:
        self.log(f"estabelecimentos: {arq.name}")
        self._viu_estabelecimentos = True
        lote = []
        raizes = set()
        for c in _linhas(arq):
            if len(c) < 28:
                continue
            if self.ufs and c[19].upper() not in self.ufs:
                self.contagem["descartados_por_uf"] += 1
                continue
            if self.ufs:
                raizes.add(c[0])
            t1, t2 = _e164(c[21], c[22]), _e164(c[23], c[24])
            lote.append((f"{c[0]}{c[1]}{c[2]}", c[0], 1 if c[3] == "1" else 0, c[4], c[5],
                         c[19], c[20], c[17], f"{c[13]} {c[14]}, {c[15]}".strip(),
                         c[18], (c[27] or "").lower().strip(), t1, t2, c[10], c[11]))
            self.contagem["telefones"] += bool(t1) + bool(t2)
            if len(lote) >= self.LOTE_EST:
                self._gravar_est(lote, raizes)
                lote, raizes = [], set()
        if lote:
            self._gravar_est(lote, raizes)
        self.con.commit()

    def _gravar_est(self, lote, raizes) -> None:
        self.con.executemany("INSERT OR REPLACE INTO estabelecimento "
                             "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", lote)
        self.contagem["estabelecimentos"] += len(lote)
        if self.ufs and raizes:
            self.con.executemany("INSERT OR IGNORE INTO escopo_uf VALUES (?)",
                                 ((r,) for r in raizes))

    def _garantir_escopo(self) -> None:
        if self.ufs and not self._viu_estabelecimentos:
            raise RuntimeError(
                "filtro por UF exige processar Estabelecimentos antes de Empresas/Socios"
            )

    def _filtrar_escopo(self, lote):
        """Filtra um lote por raízes aceitas sem manter o escopo inteiro em RAM."""
        if not self.ufs or not lote:
            return lote
        self._garantir_escopo()
        chaves = list({r[0] for r in lote})
        aceitas = set()
        for i in range(0, len(chaves), self.LOTE_SQL_IN):
            fatia = chaves[i:i + self.LOTE_SQL_IN]
            marcas = ",".join("?" for _ in fatia)
            cur = self.con.execute(
                f"SELECT cnpj_basico FROM escopo_uf WHERE cnpj_basico IN ({marcas})",
                fatia,
            )
            aceitas.update(r[0] for r in cur)
        return [r for r in lote if r[0] in aceitas]

    def _gravar_empresas(self, lote) -> None:
        lote = self._filtrar_escopo(lote)
        if lote:
            self.con.executemany("INSERT OR REPLACE INTO empresa VALUES (?,?,?,?,?)", lote)
            self.contagem["empresas"] += len(lote)

    def empresas(self, arq: Path) -> None:
        self.log(f"empresas: {arq.name}")
        self._garantir_escopo()
        lote = []
        for c in _linhas(arq):
            if len(c) < 6:
                continue
            lote.append((c[0], c[1], c[2], c[4], c[5]))
            if len(lote) >= self.LOTE_DIM:
                self._gravar_empresas(lote)
                lote = []
        self._gravar_empresas(lote)
        self.con.commit()

    def _gravar_socios(self, lote) -> None:
        lote = self._filtrar_escopo(lote)
        if lote:
            self.con.executemany("INSERT INTO socio VALUES (?,?,?,?,?,?)", lote)
            self.contagem["socios"] += len(lote)

    def socios(self, arq: Path) -> None:
        self.log(f"socios: {arq.name}")
        self._garantir_escopo()
        lote = []
        for c in _linhas(arq):
            if len(c) < 6:
                continue
            lote.append((c[0], c[2], c[3], c[4], c[5], c[8] if len(c) > 8 else ""))
            if len(lote) >= self.LOTE_DIM:
                self._gravar_socios(lote)
                lote = []
        self._gravar_socios(lote)
        self.con.commit()

    def processar(self, arq: Path) -> None:
        n = arq.name.lower()
        if "estabele" in n:
            self.estabelecimentos(arq)
        elif "empre" in n:
            self.empresas(arq)
        elif "socio" in n:
            self.socios(arq)

    def finalizar(self, **meta) -> dict:
        import datetime as _dt
        if self.ufs:
            self.contagem["raizes_uf"] = self.con.execute(
                "SELECT COUNT(*) FROM escopo_uf"
            ).fetchone()[0]
        info = {"ufs": ",".join(sorted(self.ufs)) if self.ufs else "todas",
                "construido_em": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
                **{k: str(v) for k, v in self.contagem.items()},
                **{k: str(v) for k, v in meta.items()}}
        self.con.executemany("INSERT OR REPLACE INTO meta VALUES (?,?)", info.items())
        if self.ufs:
            self.con.execute("DROP TABLE IF EXISTS escopo_uf")
        self.con.execute("ANALYZE")
        self.con.commit()
        self.con.close()
        return self.contagem

def _ordem(arq: Path) -> tuple:
    n = arq.name.lower()
    return (0 if "estabele" in n else 1 if "empre" in n else 2 if "socio" in n else 9, n)


def construir(origem: str | Path, saida: str | Path,
              log=lambda s: print(s, file=sys.stderr), ufs: set[str] | None = None) -> dict:
    """Le os arquivos da Receita (CSV ou .zip) em `origem` e monta o sqlite."""
    origem = Path(origem)
    c = Construtor(saida, ufs, log)
    for arq in sorted((a for a in origem.glob("*") if a.is_file()), key=_ordem):
        c.processar(arq)
    return c.finalizar(origem=str(origem))


class IndiceCNPJ:
    def __init__(self, caminho: str | Path):
        self.caminho = Path(caminho)
        self.ok = self.caminho.exists()
        self._con = sqlite3.connect(str(self.caminho)) if self.ok else None
        if self._con:
            self._con.row_factory = sqlite3.Row

    def por_telefone(self, e164: str) -> list[dict]:
        if not self._con:
            return []
        cur = self._con.execute(
            "SELECT * FROM estabelecimento WHERE e164_1=? OR e164_2=? LIMIT 200",
            (e164, e164))
        return [dict(r) for r in cur.fetchall()]

    def por_email(self, email: str) -> list[dict]:
        if not self._con:
            return []
        cur = self._con.execute(
            "SELECT * FROM estabelecimento WHERE email=? LIMIT 200",
            (email.lower(),))
        return [dict(r) for r in cur.fetchall()]

    def empresa(self, cnpj_basico: str) -> dict | None:
        if not self._con:
            return None
        cur = self._con.execute(
            "SELECT * FROM empresa WHERE cnpj_basico=?", (cnpj_basico,))
        r = cur.fetchone()
        return dict(r) if r else None

    def socios(self, cnpj_basico: str) -> list[dict]:
        if not self._con:
            return []
        cur = self._con.execute(
            "SELECT * FROM socio WHERE cnpj_basico=? LIMIT 200", (cnpj_basico,))
        return [dict(r) for r in cur.fetchall()]

    def irmaos(self, cnpj_basico: str) -> list[dict]:
        """Demais estabelecimentos da mesma empresa: o 'grupo' cadastral."""
        if not self._con:
            return []
        cur = self._con.execute(
            "SELECT * FROM estabelecimento WHERE cnpj_basico=? LIMIT 200",
            (cnpj_basico,))
        return [dict(r) for r in cur.fetchall()]

    def por_socio(self, nome: str) -> list[dict]:
        """Mesma pessoa em varias empresas: expande o grupo por pessoa."""
        if not self._con:
            return []
        cur = self._con.execute(
            "SELECT * FROM socio WHERE nome LIKE ? LIMIT 200",
            (nome.upper().strip(),))
        return [dict(r) for r in cur.fetchall()]

    def contar_telefone(self, e164: str) -> int:
        """Quantas raizes de CNPJ distintas declaram este telefone."""
        if not self._con:
            return 0
        cur = self._con.execute(
            "SELECT COUNT(DISTINCT cnpj_basico) FROM estabelecimento "
            "WHERE e164_1=? OR e164_2=?", (e164, e164))
        return cur.fetchone()[0]

    def meta(self) -> dict:
        if not self._con:
            return {}
        try:
            return {r[0]: r[1] for r in self._con.execute("SELECT k, v FROM meta")}
        except sqlite3.Error:
            return {}

    def estatisticas(self) -> dict:
        if not self._con:
            return {"indice": "ausente"}
        out = {}
        for t in ("estabelecimento", "empresa", "socio"):
            try:
                out[t] = self._con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except sqlite3.Error:
                out[t] = 0
        return out
