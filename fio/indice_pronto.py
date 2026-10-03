"""Indice do CNPJ pronto: baixa em segundos o que levaria 30 minutos para montar.

Montar o indice a partir da Receita exige baixar alguns GB (os arquivos de
Estabelecimentos nao sao divididos por UF) e processar milhoes de linhas. Alem
de lento, o servidor da Receita costuma recusar IPs de nuvem (Colab, GitHub
Actions). A saida e montar **uma vez**, num computador que alcance a Receita,
publicar o resultado enxuto e comprimido, e fazer os demais ambientes apenas
**baixa-lo**:

    fio indice baixar --uf MG --leve      # onde a Receita responde (1x por mes)
    fio indice exportar --uf MG           # cnpj-MG.sqlite.xz + .json (manifesto)
    # publique os dois arquivos numa Release (ou qualquer URL https)
    fio indice baixar --uf MG --pronto    # em qualquer lugar: segundos

O manifesto traz o SHA-256 do arquivo comprimido e do banco, a UF, o mes e se
e "leve". O download retoma se cair e so e aceito depois de conferido.

So biblioteca padrao (sqlite3, lzma, hashlib, urllib).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import lzma
import os
import shutil
import sqlite3
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import __version__
from .receita_download import baixar, _ctx, UA

REPOSITORIO = "Ridd1kulusC0d3r/FIO"
TAG = "indice-latest"
BLOCO = 1 << 20


class IndiceProntoIndisponivel(RuntimeError):
    """Nao ha indice pronto publicado para o que foi pedido."""


def url_base(repositorio: str = REPOSITORIO, tag: str = TAG) -> str:
    return f"https://github.com/{repositorio}/releases/download/{tag}/"


def nome_arquivo(uf: str) -> str:
    return f"cnpj-{uf.upper()}.sqlite.xz"


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as fh:
        for b in iter(lambda: fh.read(BLOCO), b""):
            h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------- exportar
def _recortar_uf(db: Path, uf: str) -> None:
    """Deixa no banco so uma UF (e as empresas/socios das raizes que sobram)."""
    con = sqlite3.connect(str(db))
    try:
        con.execute("DELETE FROM estabelecimento WHERE uf != ?", (uf.upper(),))
        con.execute("DELETE FROM empresa WHERE cnpj_basico NOT IN "
                    "(SELECT DISTINCT cnpj_basico FROM estabelecimento)")
        con.execute("DELETE FROM socio WHERE cnpj_basico NOT IN "
                    "(SELECT DISTINCT cnpj_basico FROM estabelecimento)")
        con.execute("INSERT OR REPLACE INTO meta VALUES ('ufs', ?)", (uf.upper(),))
        con.commit()
        con.execute("ANALYZE")
        con.commit()
    finally:
        con.close()


def exportar(origem_db: str | Path, destino_xz: str | Path, uf: str | None = None,
             preset: int = 6, log=print) -> dict:
    """Compacta o indice (VACUUM + xz) e grava o manifesto ao lado.

    `uf` recorta um banco que tenha varias UFs: um unico download da Receita
    alimenta todos os arquivos `cnpj-UF.sqlite.xz`.
    """
    origem, destino = Path(origem_db), Path(destino_xz)
    if not origem.exists():
        raise FileNotFoundError(f"indice nao encontrado: {origem}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with tempfile.TemporaryDirectory(dir=destino.parent) as tmp:
        copia = Path(tmp) / "indice.sqlite"
        con = sqlite3.connect(str(origem))
        try:
            con.execute("VACUUM INTO ?", (str(copia),))     # copia compacta
        finally:
            con.close()
        if uf:
            _recortar_uf(copia, uf)
            c2 = sqlite3.connect(str(copia))
            try:
                c2.execute("VACUUM")
            finally:
                c2.close()
        meta = {}
        c3 = sqlite3.connect(str(copia))
        try:
            meta = {k: v for k, v in c3.execute("SELECT k, v FROM meta")}
            n_est = c3.execute("SELECT COUNT(*) FROM estabelecimento").fetchone()[0]
        finally:
            c3.close()
        sha_db = _sha256(copia)
        bytes_db = copia.stat().st_size
        log(f"banco compacto: {bytes_db / 1e6:,.1f} MB ({n_est:,} estabelecimentos); comprimindo...")
        parcial = destino.with_suffix(destino.suffix + ".parcial")
        with copia.open("rb") as src, lzma.open(parcial, "wb", preset=preset) as dst:
            for b in iter(lambda: src.read(BLOCO), b""):
                dst.write(b)
        os.replace(parcial, destino)
    manifesto = {
        "arquivo": destino.name,
        "sha256": _sha256(destino),
        "bytes": destino.stat().st_size,
        "sha256_banco": sha_db,
        "bytes_banco": bytes_db,
        "uf": (uf or meta.get("ufs") or "todas").upper() if (uf or meta.get("ufs")) else "todas",
        "mes": meta.get("mes", ""),
        "leve": meta.get("leve", "0") == "1",
        "estabelecimentos": n_est,
        "gerado_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "fio": __version__,
    }
    Path(str(destino) + ".json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"{destino.name}: {manifesto['bytes'] / 1e6:,.1f} MB "
        f"(banco {bytes_db / 1e6:,.1f} MB) em {time.time() - t0:.0f} s")
    return manifesto


# ----------------------------------------------------------------- importar
def _ler_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise IndiceProntoIndisponivel(
                f"nao ha indice pronto em {url} (404). Publique um com "
                "'fio indice exportar' ou monte pela Receita.") from e
        raise


def _validador(sha256_esperado: str | None):
    def ok(caminho: Path) -> bool:
        try:
            with lzma.open(caminho, "rb") as f:         # estrutura xz inteira
                while f.read(BLOCO):
                    pass
        except (lzma.LZMAError, EOFError, OSError):
            return False
        return sha256_esperado is None or _sha256(caminho) == sha256_esperado
    return ok


def _descomprimir(xz: Path, destino: Path) -> None:
    with lzma.open(xz, "rb") as src, destino.open("wb") as dst:
        shutil.copyfileobj(src, dst, BLOCO)


def _conferir(db: Path) -> int:
    con = sqlite3.connect(str(db))
    try:
        n = con.execute("SELECT COUNT(*) FROM estabelecimento").fetchone()[0]
    except sqlite3.Error as e:
        raise ValueError(f"o arquivo nao e um indice do F.I.O.: {e}") from e
    finally:
        con.close()
    if not n:
        raise ValueError("o indice baixado esta vazio")
    return n


def _mesclar(destino: Path, outro: Path) -> None:
    con = sqlite3.connect(str(destino))
    try:
        con.execute("ATTACH DATABASE ? AS o", (str(outro),))
        for t in ("estabelecimento", "empresa"):
            con.execute(f"INSERT OR REPLACE INTO main.{t} SELECT * FROM o.{t}")
        con.execute("INSERT INTO main.socio SELECT * FROM o.socio")
        ufs = {r[0] for r in con.execute("SELECT DISTINCT uf FROM main.estabelecimento")}
        con.execute("INSERT OR REPLACE INTO main.meta VALUES ('ufs', ?)", (",".join(sorted(ufs)),))
        con.commit()
        con.execute("DETACH DATABASE o")
    finally:
        con.close()


def importar(destino_db: str | Path, ufs: list[str], base: str | None = None,
             log=print, pasta_tmp: str | Path | None = None) -> dict:
    """Baixa o indice pronto de cada UF, confere o SHA-256 e instala em `destino_db`.

    Com varias UFs, os bancos sao mesclados num so. Se o arquivo ja instalado
    e identico ao publicado (mesmo SHA-256 do banco), nao baixa de novo.
    """
    destino = Path(destino_db)
    base = (base or url_base()).rstrip("/") + "/"
    tmp = Path(pasta_tmp or destino.parent / "indice-pronto-tmp")
    tmp.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    bancos: list[Path] = []
    manifestos = []
    try:
        for uf in ufs:
            nome = nome_arquivo(uf)
            man = _ler_json(base + nome + ".json")
            manifestos.append(man)
            est = man.get("estabelecimentos")
            log(f"{nome}: {man['bytes'] / 1e6:,.1f} MB comprimido "
                f"({f'{est:,}' if isinstance(est, int) else '?'} estabelecimentos, "
                f"mes {man.get('mes') or '?'})")
            xz = baixar(base + nome, tmp / nome, log=log, validar=_validador(man["sha256"]))
            db = tmp / f"{uf.upper()}.sqlite"
            _descomprimir(xz, db)
            if _sha256(db) != man["sha256_banco"]:
                raise ValueError(f"{nome}: o banco descomprimido nao confere com o manifesto")
            _conferir(db)
            bancos.append(db)
            xz.unlink(missing_ok=True)
        provisorio = destino.with_suffix(destino.suffix + ".instalando")
        provisorio.unlink(missing_ok=True)
        shutil.copy(bancos[0], provisorio)
        for extra in bancos[1:]:
            _mesclar(provisorio, extra)
        n = _conferir(provisorio)
        os.replace(provisorio, destino)
    finally:
        for b in bancos:
            b.unlink(missing_ok=True)
        shutil.rmtree(tmp, ignore_errors=True)
    res = {"estado": "pronto", "arquivo": str(destino), "ufs": ",".join(u.upper() for u in ufs),
           "estabelecimentos": n, "origem": "indice pronto",
           "mes": ",".join(sorted({m.get("mes", "") for m in manifestos} - {""})),
           "segundos": round(time.time() - t0, 1)}
    log(f"indice instalado: {destino} ({n:,} estabelecimentos) em {res['segundos']} s")
    return res


# ------------------------------------------------------------------ instalar
def instalar(destino_db: str | Path, ufs: set[str] | list[str] | None, mes: str | None = None,
             fonte: str = "auto", leve: bool = True, log=print,
             pasta_tmp: str | Path | None = None) -> dict:
    """Coloca um indice do CNPJ em `destino_db`, do jeito mais rapido possivel.

    fonte:
      "auto"    tenta o indice PRONTO (segundos) e, se nao houver ou a rede
                falhar, monta pela Receita (lento) em modo `leve`;
      "pronto"  so o pronto (erro se nao houver);
      "receita" monta direto pela Receita.
    Sem UF nao existe indice pronto (e preciso saber qual baixar).
    """
    from .receita_download import montar
    destino = Path(destino_db)
    lista = sorted({u.upper() for u in ufs}) if ufs else []
    if fonte in ("auto", "pronto") and lista:
        try:
            log(f"indice pronto: UF={','.join(lista)} (baixa o arquivo ja montado)")
            return importar(destino, lista, log=log, pasta_tmp=pasta_tmp)
        except (IndiceProntoIndisponivel, urllib.error.URLError, OSError, ValueError) as e:
            if fonte == "pronto":
                raise
            log(f"indice pronto indisponivel ({type(e).__name__}: {e}); "
                "montando pela Receita, o que e lento")
    elif fonte == "pronto":
        raise ValueError("o indice pronto precisa de UF (ex.: MG)")
    log(f"indice Receita: UF={','.join(lista) if lista else 'todas'} mes={mes or 'automatico'}"
        f"{' (leve)' if leve else ''}")
    res = montar(destino, ufs=set(lista) or None, mes=mes,
                 pasta_tmp=pasta_tmp or destino.parent / "receita-tmp", log=log, leve=leve)
    return {"estado": "pronto", "arquivo": str(destino), "origem": "Receita", **res}
