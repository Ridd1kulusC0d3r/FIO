"""Baixa os Dados Abertos do CNPJ direto da Receita Federal e monta o índice.

Pensado para Google Colab e máquinas com pouco disco livre: descobre o mês
mais recente, baixa um arquivo por vez, processa e remove antes do próximo.
O filtro por UF reduz o SQLite final e o uso de RAM, mas não reduz o tráfego:
a Receita distribui Estabelecimentos por partes, não por estado.

O downloader usa arquivo parcial, ``Range`` e ``If-Range`` (ETag ou
Last-Modified) para retomar com segurança. Se o servidor ignorar a retomada
ou o objeto remoto mudar, reinicia somente aquele arquivo em vez de juntar
duas versões no mesmo ZIP.
"""

from __future__ import annotations

import http.client
import json
import os
import re
import shutil
import ssl
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from .indice import Construtor, _ordem

BASES = [
    "https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/",
    "https://arquivos.receitafederal.gov.br/cnpj/dados_abertos_cnpj/",
    "https://dadosabertos.rfb.gov.br/CNPJ/dados_abertos_cnpj/",
]
UA = "Mozilla/5.0 FIO-OSINT/2.2 (download de dados abertos do CNPJ)"
_MES = re.compile(r'href="(\d{4}-\d{2})/?"')
_ZIP = re.compile(r'href="([A-Za-z]+\d*\.zip)"', re.I)
_CONTENT_RANGE = re.compile(r"bytes\s+(\d+)-(\d+)/(\d+|\*)", re.I)
UFS_BR = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT",
    "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO",
    "RR", "SC", "SP", "SE", "TO",
}


def _ctx():
    b = os.environ.get("FIO_CA_BUNDLE") or os.environ.get("REQUESTS_CA_BUNDLE")
    return ssl.create_default_context(cafile=b) if b and os.path.exists(b) else None


def _get(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
        return r.read().decode("utf-8", "replace")


def validar_ufs(ufs: set[str] | None) -> set[str] | None:
    if not ufs:
        return None
    normalizadas = {u.strip().upper() for u in ufs if u and u.strip()}
    invalidas = sorted(normalizadas - UFS_BR)
    if invalidas:
        raise ValueError("UF invalida: " + ", ".join(invalidas))
    return normalizadas or None


def descobrir(base: str | None = None, mes: str | None = None,
              log=print) -> tuple[str, str, list[str]]:
    """Devolve ``(base, mês, arquivos .zip do mês)``."""
    erros = []
    base = base or os.environ.get("FIO_RECEITA_BASE")
    for b in ([base] if base else BASES):
        b = b.rstrip("/") + "/"
        try:
            meses = sorted(set(_MES.findall(_get(b))))
            if not meses:
                raise ValueError("indice sem pastas AAAA-MM")
            m = mes or meses[-1]
            if m not in meses:
                raise ValueError(f"mes {m} nao publicado nesta fonte")
            arquivos = sorted(set(_ZIP.findall(_get(b + m + "/"))))
            if not arquivos:
                raise ValueError(f"pasta {m} sem .zip")
            log(f"fonte: {b}{m}/ ({len(arquivos)} arquivos; meses disponiveis: {meses[0]}..{meses[-1]})")
            return b, m, arquivos
        except Exception as e:
            erros.append(f"{b}: {type(e).__name__}: {e}")
    raise RuntimeError("nao encontrei a base da Receita. Tentativas:\n  " + "\n  ".join(erros))


def _meta_path(parcial: Path) -> Path:
    return parcial.with_suffix(parcial.suffix + ".json")


def _ler_meta(parcial: Path) -> dict:
    try:
        return json.loads(_meta_path(parcial).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def _salvar_meta(parcial: Path, url: str, headers) -> None:
    meta = {"url": url}
    for origem, destino in (("ETag", "etag"), ("Last-Modified", "last_modified")):
        v = headers.get(origem)
        if v:
            meta[destino] = v
    _meta_path(parcial).write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def _limpar_parcial(parcial: Path) -> None:
    parcial.unlink(missing_ok=True)
    _meta_path(parcial).unlink(missing_ok=True)


def _zip_ok(caminho: Path) -> bool:
    try:
        with zipfile.ZipFile(caminho) as z:
            return z.testzip() is None
    except (OSError, zipfile.BadZipFile):
        return False


def baixar(url: str, destino: Path, log=print, tentativas: int = 5) -> Path:
    """Baixa ``url`` de forma retomável e grava atomicamente em ``destino``.

    Um ``.parcial`` sobrevivente é retomado com ``Range``. ``If-Range`` evita
    concatenar conteúdo antigo quando a Receita substitui o objeto remoto.
    Ao final, o arquivo parcial é movido atomicamente para o nome definitivo.
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_suffix(destino.suffix + ".parcial")

    if destino.exists():
        if _zip_ok(destino):
            log(f"  usando download ja concluido: {destino.name}")
            return destino
        log(f"  cache invalido: {destino.name}; baixando novamente")
        destino.unlink(missing_ok=True)

    ultimo = None
    for n in range(1, tentativas + 1):
        ja = parcial.stat().st_size if parcial.exists() else 0
        meta = _ler_meta(parcial) if ja else {}
        if meta and meta.get("url") not in (None, url):
            _limpar_parcial(parcial)
            ja, meta = 0, {}

        cab = {"User-Agent": UA, "Accept-Encoding": "identity"}
        if ja:
            cab["Range"] = f"bytes={ja}-"
            if meta.get("etag"):
                cab["If-Range"] = meta["etag"]
            elif meta.get("last_modified"):
                cab["If-Range"] = meta["last_modified"]
        try:
            req = urllib.request.Request(url, headers=cab)
            with urllib.request.urlopen(req, timeout=120, context=_ctx()) as r:
                status = getattr(r, "status", r.getcode())
                # Servidor ignorou Range ou If-Range detectou objeto novo: começa
                # este arquivo do zero. Nunca anexa resposta 200 a um parcial.
                retomou = bool(ja and status == 206)
                if ja and status != 206:
                    log("  objeto remoto mudou ou servidor ignorou Range; reiniciando este arquivo")
                    ja = 0
                    retomou = False

                cr = r.headers.get("Content-Range", "")
                m = _CONTENT_RANGE.match(cr)
                if retomou and m and int(m.group(1)) != ja:
                    raise ConnectionError(f"Content-Range inesperado para retomada: {cr!r}")
                if retomou and not m:
                    log("  retomada 206 sem Content-Range; validando pelo tamanho recebido")

                if m and m.group(3) != "*":
                    total = int(m.group(3))
                else:
                    cl = r.headers.get("Content-Length")
                    total = (int(cl) + ja) if cl else None

                modo = "ab" if retomou else "wb"
                feito = ja if retomou else 0
                _salvar_meta(parcial, url, r.headers)
                proximo = ((feito / total) // 0.1 + 1) * 0.1 if total else 1.1
                t0 = time.time()
                with parcial.open(modo) as fh:
                    while True:
                        bloco = r.read(1 << 20)
                        if not bloco:
                            break
                        fh.write(bloco)
                        feito += len(bloco)
                        if total and feito / total >= proximo:
                            vel = (feito - ja) / max(time.time() - t0, 0.1) / 1e6
                            log(f"  {destino.name}: {feito / 1e6:,.0f} de {total / 1e6:,.0f} MB ({vel:.1f} MB/s)")
                            proximo += 0.1

            if total is not None and feito != total:
                raise ConnectionError(f"recebidos {feito} de {total} bytes")
            os.replace(parcial, destino)
            _meta_path(parcial).unlink(missing_ok=True)
            return destino
        except urllib.error.HTTPError as e:
            ultimo = e
            if e.code == 416:  # parcial incompatível ou já além do objeto remoto
                log("  servidor recusou a retomada (416); descartando parcial")
                _limpar_parcial(parcial)
            if 400 <= e.code < 500 and e.code not in (408, 416, 429):
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError,
                http.client.HTTPException) as e:
            ultimo = e

        if n < tentativas:
            espera = min(60, 5 * n)
            log(f"  falha ({type(ultimo).__name__}: {ultimo}); nova tentativa {n + 1}/{tentativas} em {espera}s")
            time.sleep(espera)

    raise RuntimeError(f"nao consegui baixar {url}: {ultimo}")


def montar(saida: str | Path, ufs: set[str] | None = None, mes: str | None = None,
           base: str | None = None, pasta_tmp: str | Path | None = None,
           manter_zips: bool = False, log=print) -> dict:
    """Descobre, baixa, processa e apaga a base, um ZIP por vez."""
    ufs = validar_ufs(ufs)
    b, m, arquivos = descobrir(base, mes, log)
    alvo = [a for a in arquivos if re.match(r"(estabelecimentos|empresas|socios)\d*\.zip", a, re.I)]
    alvo.sort(key=lambda n: _ordem(Path(n)))
    if not alvo:
        raise RuntimeError("a pasta publicada nao contem Estabelecimentos/Empresas/Socios")

    tmp = Path(pasta_tmp or Path(saida).parent / "receita-tmp")
    tmp.mkdir(parents=True, exist_ok=True)
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    provisoria = saida.with_suffix(saida.suffix + ".construindo")
    provisoria.unlink(missing_ok=True)

    c = Construtor(provisoria, ufs, log)
    t0 = time.time()
    try:
        for i, nome in enumerate(alvo, 1):
            log(f"[{i}/{len(alvo)}] {nome}")
            arq = tmp / nome
            baixar(b + m + "/" + nome, arq, log)
            c.processar(arq)
            if not manter_zips:
                arq.unlink(missing_ok=True)
        cont = c.finalizar(mes=m, fonte=b + m + "/")
    except Exception:
        # fecha a conexão se o construtor ainda estiver vivo; o arquivo
        # .construindo fica descartável e nunca substitui um índice bom.
        try:
            c.con.close()
        except Exception:
            pass
        raise

    os.replace(provisoria, saida)
    cont["minutos"] = round((time.time() - t0) / 60, 1)
    cont["mes"] = m
    cont["tamanho_mb"] = round(saida.stat().st_size / 1e6, 1)
    cont["uf"] = ",".join(sorted(ufs)) if ufs else "todas"
    cont["pico_disco"] = "um ZIP + indice em construcao"
    log(f"indice pronto: {saida} ({cont['tamanho_mb']} MB, {cont['minutos']} min)")
    return cont
