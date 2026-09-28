"""Indexador universal de dados abertos por receita.

A maior parte do dado aberto brasileiro util para vinculo e tabular e
chega como CSV ou JSON com nomes de coluna imprevisiveis. Em vez de um
coletor por base, o lab usa receitas: um mapeamento declarativo de colunas
para tipos de entidade. Qualquer arquivo aberto vira um indice reverso
local (telefone/e-mail/CNPJ -> registro), consultado offline pelo coletor
`dados-abertos`.

Receitas embutidas cobrem CNES, Cadastur, despesas eleitorais do TSE,
faixas de numeracao e uma receita generica que detecta colunas sozinha.
Receitas proprias vao em FIO_HOME/receitas/*.json com o mesmo formato.

Cada indice guarda o SHA-256 do arquivo de origem e a data de construcao:
e isso que o rastreador de experimentos registra como "versao da fonte".
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import re
import sqlite3
import unicodedata
import zipfile
from pathlib import Path

from .core.normalize import normalizar
from .core.documentos import cnpj_limpar, cnpj_valido, cep_uf

RECEITAS: dict[str, dict] = {
    "cnes": {
        "titulo": "CNES - Cadastro Nacional de Estabelecimentos de Saude",
        "fonte": "https://dadosabertos.saude.gov.br/dataset/cnes-cadastro-nacional-de-estabelecimentos-de-saude",
        "admiralty": "A2", "tipo": "registro", "entidade": "organizacao",
        "relacao": "telefone_de_estabelecimento_de_saude",
        "colunas": {
            "chave": ["co_cnes", "codigo_cnes", "cnes"],
            "rotulo": ["no_fantasia", "nome_fantasia", "no_razao_social", "nome_razao_social"],
            "telefone": ["nu_telefone", "numero_telefone_estabelecimento", "telefone"],
            "fax": ["nu_fax", "numero_fax_estabelecimento"],
            "email": ["no_email", "endereco_email_estabelecimento", "email"],
            "cnpj": ["nu_cnpj", "numero_cnpj", "nu_cnpj_mantenedora", "numero_cnpj_entidade"],
            "cep": ["co_cep", "codigo_cep_estabelecimento"],
            "uf": ["co_uf", "sg_uf", "codigo_uf"],
            "municipio": ["co_municipio_gestor", "codigo_municipio", "no_municipio"],
        },
        "reserva": ("Telefone declarado pelo gestor do estabelecimento de "
                    "saude; frequentemente e o numero da recepcao ou da "
                    "mantenedora, nao de profissional individual."),
    },
    "cadastur": {
        "titulo": "Cadastur - prestadores de servicos turisticos (MTur)",
        "fonte": "https://dados.gov.br/dados/conjuntos-dados/cadastur",
        "admiralty": "B2", "tipo": "registro", "entidade": "organizacao",
        "relacao": "telefone_de_prestador_turistico",
        "colunas": {
            "chave": ["numero_do_certificado", "certificado", "cnpj"],
            "rotulo": ["nome_fantasia", "razao_social", "nome"],
            "telefone": ["telefone", "telefone_comercial", "celular"],
            "email": ["email", "e_mail", "email_comercial"],
            "cnpj": ["cnpj", "cpf_cnpj"],
            "cep": ["cep"], "uf": ["uf"], "municipio": ["municipio"],
        },
        "reserva": "Autodeclarado pelo prestador no cadastro do MTur.",
    },
    "tse-despesas": {
        "titulo": "TSE - despesas contratadas de campanha",
        "fonte": "https://dadosabertos.tse.jus.br/dataset/?q=prestacao+de+contas",
        "admiralty": "A2", "tipo": "registro", "entidade": "organizacao",
        "relacao": "fornecedor_de_campanha",
        "colunas": {
            "chave": ["sq_despesa", "sq_prestador_contas"],
            "rotulo": ["nm_fornecedor", "nm_fornecedor_rfb"],
            "cnpj": ["nr_cpf_cnpj_fornecedor"],
            "uf": ["sg_uf"], "municipio": ["nm_ue"],
        },
        "relacionados": [
            {"coluna": ["nm_candidato"], "tipo": "pessoa",
             "relacao": "contratou_fornecedor"},
        ],
        "reserva": ("Prestacao de contas declarada pela campanha. Liga "
                    "fornecedor a candidato; nao contem telefone."),
    },
    "anatel-faixas": {
        "titulo": "Faixas de numeracao por prestadora (arquivo fornecido pelo analista)",
        "fonte": "nSAPN / ABR Telecom - arquivo obtido pelo analista",
        "admiralty": "B3", "tipo": "faixa", "entidade": "prestadora",
        "relacao": "faixa_destinada_a",
        "colunas": {
            "ddd": ["cn", "ddd", "codigo_nacional"],
            "prefixo": ["prefixo"],
            "inicio": ["faixa_inicial", "inicio", "mcdu_inicial", "numero_inicial"],
            "fim": ["faixa_final", "fim", "mcdu_final", "numero_final"],
            "prestadora": ["prestadora", "operadora", "nome_prestadora", "razao_social"],
        },
        "reserva": ("Indica a prestadora a que a faixa foi DESTINADA, nao a "
                    "operadora atual da linha: com portabilidade, as duas "
                    "divergem com frequencia. Portabilidade so pela ABR Telecom."),
    },
    "generica": {
        "titulo": "Deteccao automatica de colunas",
        "fonte": "arquivo fornecido pelo analista",
        "admiralty": "C3", "tipo": "registro", "entidade": "organizacao",
        "relacao": "consta_em_registro",
        "colunas": {},   # detectadas em tempo de construcao
        "reserva": ("Mapeamento de colunas inferido automaticamente; "
                    "revise a amostra antes de citar em relatorio."),
    },
}

_PADROES_GENERICOS = {
    "telefone": re.compile(r"(tel|fone|celular|whats|contato_?num)"),
    "email": re.compile(r"(e_?mail|correio)"),
    "cnpj": re.compile(r"cnpj"),
    "cep": re.compile(r"^(co_|nu_|codigo_)?cep"),
    "rotulo": re.compile(r"(fantasia|razao|nome|^no_)"),
    "uf": re.compile(r"^(sg_|co_)?uf$"),
    "municipio": re.compile(r"munic"),
}


# ------------------------------------------------------------ utilidades
def _norm_col(c: str) -> str:
    c = unicodedata.normalize("NFKD", c or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", c.lower()).strip("_")


def _achar(cols: list[str], candidatos: list[str]) -> str | None:
    for cand in candidatos:
        if cand in cols:
            return cand
    return None


def _ler_linhas(caminho: Path):
    """Gera dicts com chaves normalizadas, de CSV/JSON soltos ou em ZIP."""
    def de_bytes(nome: str, dados: bytes):
        if nome.lower().endswith(".json"):
            obj = json.loads(dados.decode("utf-8-sig", "replace"))
            if isinstance(obj, dict):
                obj = next((v for v in obj.values() if isinstance(v, list)), [])
            for item in obj:
                if isinstance(item, dict):
                    yield {_norm_col(k): ("" if v is None else str(v)) for k, v in item.items()}
            return
        try:
            texto = dados.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = dados.decode("latin-1")
        amostra = texto[:20000]
        try:
            dialeto = csv.Sniffer().sniff(amostra, delimiters=";,|\t")
        except csv.Error:
            dialeto = csv.excel
            dialeto.delimiter = ";" if amostra.count(";") > amostra.count(",") else ","
        leitor = csv.reader(io.StringIO(texto), dialeto)
        cab = [_norm_col(c) for c in next(leitor, [])]
        for linha in leitor:
            if linha:
                yield dict(zip(cab, linha))

    if caminho.suffix.lower() == ".zip":
        with zipfile.ZipFile(caminho) as z:
            for nome in z.namelist():
                if nome.lower().endswith((".csv", ".json", ".txt")):
                    yield from de_bytes(nome, z.read(nome))
    else:
        yield from de_bytes(caminho.name, caminho.read_bytes())


def _sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def diretorio_indices(raiz: Path) -> Path:
    d = raiz / "indices"
    d.mkdir(parents=True, exist_ok=True)
    return d


def carregar_receitas(raiz: Path | None = None) -> dict[str, dict]:
    todas = dict(RECEITAS)
    if raiz:
        pasta = raiz / "receitas"
        if pasta.exists():
            for arq in sorted(pasta.glob("*.json")):
                try:
                    r = json.loads(arq.read_text(encoding="utf-8"))
                    todas[r.get("id", arq.stem)] = r
                except (json.JSONDecodeError, OSError):
                    continue
    return todas


# ------------------------------------------------------------- construcao
ESQUEMA = """
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS registro (id INTEGER PRIMARY KEY, chave TEXT,
  rotulo TEXT, dados TEXT);
CREATE TABLE IF NOT EXISTS chave (tipo TEXT, valor TEXT, registro_id INTEGER);
CREATE INDEX IF NOT EXISTS ix_chave ON chave(tipo, valor);
CREATE TABLE IF NOT EXISTS faixa (ddd TEXT, inicio INTEGER, fim INTEGER,
  prestadora TEXT);
CREATE INDEX IF NOT EXISTS ix_faixa ON faixa(ddd, inicio, fim);
"""


def construir(receita_id: str, origem: str | Path, raiz: Path,
              receitas: dict | None = None, log=lambda s: None) -> dict:
    receitas = receitas or carregar_receitas(raiz)
    if receita_id not in receitas:
        raise KeyError(f"receita '{receita_id}' inexistente: "
                       f"{', '.join(sorted(receitas))}")
    rec = dict(receitas[receita_id])
    origem = Path(origem)
    saida = diretorio_indices(raiz) / f"{receita_id}.sqlite"
    if saida.exists():
        saida.unlink()
    con = sqlite3.connect(str(saida))
    con.executescript(ESQUEMA)

    linhas = _ler_linhas(origem)
    primeira = next(linhas, None)
    if primeira is None:
        raise ValueError("arquivo vazio ou formato nao reconhecido")
    cols = list(primeira)

    mapa: dict[str, str | None] = {}
    if rec.get("colunas"):
        for campo, cands in rec["colunas"].items():
            mapa[campo] = _achar(cols, cands)
    else:  # generica
        for campo, rx in _PADROES_GENERICOS.items():
            mapa[campo] = next((c for c in cols if rx.search(c)), None)
    log(f"mapeamento de colunas: {mapa}")

    cont = {"linhas": 0, "chaves": 0, "faixas": 0}

    def processar(l: dict) -> None:
        cont["linhas"] += 1
        g = lambda campo: (l.get(mapa.get(campo) or "", "") or "").strip()

        if rec.get("tipo") == "faixa":
            ddd = re.sub(r"\D", "", g("ddd"))[:2]
            prest = g("prestadora")
            ini, fim = re.sub(r"\D", "", g("inicio")), re.sub(r"\D", "", g("fim"))
            pref = re.sub(r"\D", "", g("prefixo"))
            if pref and not ini:
                ini = pref + "0" * (4 if len(pref) >= 4 else 4)
                fim = pref + "9" * 4
            elif pref and len(ini) <= 4:
                ini, fim = pref + ini.zfill(4), pref + fim.zfill(4)
            if ddd and prest and ini and fim:
                con.execute("INSERT INTO faixa VALUES (?,?,?,?)",
                            (ddd, int(ini), int(fim), prest))
                cont["faixas"] += 1
            return

        rotulo = g("rotulo") or g("chave")
        extras = {k: g(k) for k in ("uf", "municipio", "cep") if g(k)}
        for rel in rec.get("relacionados", []):
            col = _achar(cols, rel["coluna"])
            if col and l.get(col):
                extras[f"rel:{rel['tipo']}:{rel['relacao']}"] = l[col].strip()
        cur = con.execute("INSERT INTO registro (chave, rotulo, dados) VALUES (?,?,?)",
                          (g("chave"), rotulo, json.dumps(extras, ensure_ascii=False)))
        rid = cur.lastrowid
        chaves = []
        for campo in ("telefone", "fax"):
            bruto = g(campo)
            if bruto:
                t = normalizar(bruto, ddd_padrao=None)
                if t.valido and t.e164:
                    chaves.append(("telefone", t.e164))
        if "@" in g("email"):
            chaves.append(("email", g("email").lower()))
        c = cnpj_limpar(g("cnpj"))
        if len(c) == 14 and cnpj_valido(c):
            chaves.append(("cnpj", c))
        for tipo, valor in chaves:
            con.execute("INSERT INTO chave VALUES (?,?,?)", (tipo, valor, rid))
            cont["chaves"] += 1

    processar(primeira)
    for n, l in enumerate(linhas, start=2):
        processar(l)
        if n % 50000 == 0:
            con.commit()
            log(f"  {n} linhas")

    meta = {"receita": receita_id, "titulo": rec.get("titulo", ""),
            "fonte": rec.get("fonte", ""), "admiralty": rec.get("admiralty", "C3"),
            "relacao": rec.get("relacao", "consta_em_registro"),
            "entidade": rec.get("entidade", "organizacao"),
            "tipo": rec.get("tipo", "registro"),
            "reserva": rec.get("reserva", ""),
            "arquivo": origem.name, "sha256": _sha256_arquivo(origem),
            "construido_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "mapeamento": json.dumps(mapa), **{k: str(v) for k, v in cont.items()}}
    con.executemany("INSERT OR REPLACE INTO meta VALUES (?,?)", meta.items())
    con.commit()
    con.close()
    return meta


# ---------------------------------------------------------------- consulta
class Indice:
    def __init__(self, caminho: Path):
        self.caminho = caminho
        self.con = sqlite3.connect(str(caminho))
        self.con.row_factory = sqlite3.Row
        self.meta = {r["k"]: r["v"] for r in self.con.execute("SELECT k, v FROM meta")}

    def buscar(self, tipo: str, valor: str, limite: int = 50) -> list[dict]:
        cur = self.con.execute(
            "SELECT r.* FROM chave c JOIN registro r ON r.id = c.registro_id "
            "WHERE c.tipo=? AND c.valor=? LIMIT ?", (tipo, valor, limite))
        out = []
        for r in cur.fetchall():
            d = dict(r)
            d["dados"] = json.loads(d["dados"] or "{}")
            out.append(d)
        return out

    def faixa(self, ddd: str, assinante: str) -> list[dict]:
        try:
            n = int(assinante)
        except (TypeError, ValueError):
            return []
        cur = self.con.execute(
            "SELECT * FROM faixa WHERE ddd=? AND inicio<=? AND fim>=? LIMIT 5",
            (ddd, n, n))
        return [dict(r) for r in cur.fetchall()]

    def fechar(self) -> None:
        if self.con is not None:
            self.con.close()
            self.con = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.fechar()
        return False


def indices_disponiveis(raiz: Path) -> list[Path]:
    return sorted(diretorio_indices(raiz).glob("*.sqlite"))


def versoes_fontes(raiz: Path) -> dict[str, dict]:
    """Assinatura de cada indice local: entra no registro de experimento."""
    out = {}
    for p in indices_disponiveis(raiz):
        try:
            idx = Indice(p)
            out[p.stem] = {k: idx.meta.get(k) for k in
                           ("sha256", "construido_em", "arquivo", "linhas")}
            idx.fechar()
        except sqlite3.Error:
            continue
    cnpj = raiz / "cnpj.sqlite"
    if cnpj.exists():
        st = cnpj.stat()
        out["cnpj-receita"] = {"bytes": st.st_size, "mtime": int(st.st_mtime)}
    return out
