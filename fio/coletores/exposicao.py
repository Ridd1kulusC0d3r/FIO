"""Exposicao do identificador em incidentes ja catalogados.

Distincao que o framework nao abre mao: verificar SE um identificador
aparece em um vazamento conhecido e avaliacao de exposicao -- util,
legitima e ate devida. CONSULTAR o conteudo do vazamento para extrair
dados cadastrais de alguem e outra coisa, e nao esta implementado aqui
nem sera.

O indice local existe para o caso em que a organizacao ja detem
legitimamente um corpus (o proprio vazamento que sofreu, por exemplo): ele
guarda apenas SHA-256 dos identificadores, de modo que consultar nao
reintroduz o dado pessoal em claro no ambiente de analise.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .base import Coletor, Contexto, Achado, registrar
from ..grafo.modelo import Entidade, Fonte


@registrar
class HIBP(Coletor):
    nome = "hibp"
    descricao = "E-mail -> incidentes catalogados no Have I Been Pwned."
    tipos_alvo = ("email",)
    requer_rede = True
    requer_segredo = "hibp_api_key"
    admiralty = "B2"
    reserva = ("Informa que o endereco esteve em um incidente, nao que a "
               "senha siga valida nem que a conta seja da pessoa investigada. "
               "O HIBP indexa e-mail; numero de telefone so aparece como "
               "classe de dado exposta no incidente.")

    def coletar(self, alvo: Entidade, ctx: Contexto) -> list[Achado]:
        chave = ctx.segredos.get("hibp_api_key")
        url = ("https://haveibeenpwned.com/api/v3/breachedaccount/"
               f"{alvo.valor}?truncateResponse=false")
        status, dados = ctx.http().get_json(
            url, self.nome,
            cabecalhos={"hibp-api-key": chave, "Accept": "application/json"})
        if status == 404:
            alvo.atributos["exposicao_hibp"] = "sem incidente conhecido"
            return []
        if status != 200 or not isinstance(dados, list):
            return []

        fonte = Fonte(coletor=self.nome, admiralty=self.admiralty, url=url,
                      nota="HIBP API v3")
        achados = []
        for b in dados:
            inc = Entidade("documento", f"incidente:{b.get('Name')}",
                           rotulo=b.get("Title") or b.get("Name"),
                           atributos={"data": b.get("BreachDate"),
                                      "contas": b.get("PwnCount"),
                                      "classes": b.get("DataClasses"),
                                      "verificado": b.get("IsVerified")})
            achados.append(Achado(alvo, "exposto_em", inc, fonte,
                                  f"classes: {', '.join(b.get('DataClasses') or [])[:120]}"))
            if "Phone numbers" in (b.get("DataClasses") or []):
                alvo.atributos["telefone_possivelmente_exposto"] = True
        return achados


@registrar
class IndiceExposicaoLocal(Coletor):
    nome = "exposicao-local"
    descricao = ("Checa o identificador contra um indice local de hashes de "
                 "corpus que a organizacao ja detem legitimamente.")
    tipos_alvo = ("telefone", "email")
    requer_rede = False
    requer_segredo = "indice_exposicao"
    admiralty = "B2"
    reserva = ("So responde 'consta' ou 'nao consta'. Por construcao nao "
               "devolve o registro correspondente: o indice guarda apenas "
               "hashes, nunca o dado em claro.")

    def coletar(self, alvo: Entidade, ctx: Contexto) -> list[Achado]:
        caminho = Path(ctx.segredos["indice_exposicao"])
        if not caminho.exists():
            return []
        manifesto = {}
        man_path = caminho.with_suffix(".json")
        if man_path.exists():
            manifesto = json.loads(man_path.read_text(encoding="utf-8"))

        valor = (alvo.atributos.get("e164") or alvo.valor).lower()
        h = hashlib.sha256(valor.encode()).hexdigest()
        encontrado = False
        with caminho.open(encoding="utf-8") as fh:
            for linha in fh:
                if linha.strip()[:64] == h:
                    encontrado = True
                    break
        alvo.atributos["exposicao_local"] = "consta" if encontrado else "nao consta"
        if not encontrado:
            return []

        fonte = Fonte(coletor=self.nome, admiralty=self.admiralty,
                      url=str(caminho),
                      nota=f"indice local de hashes ({manifesto.get('origem','origem nao declarada')})")
        inc = Entidade("documento",
                       f"corpus:{manifesto.get('id', caminho.stem)}",
                       rotulo=manifesto.get("titulo", caminho.stem),
                       atributos=manifesto)
        return [Achado(alvo, "consta_em_corpus", inc, fonte,
                       "presenca confirmada por hash; conteudo nao consultado")]


def construir_indice(origem: str | Path, saida: str | Path,
                     manifesto: dict | None = None) -> int:
    """Converte uma lista de identificadores em indice de hashes.

    Destroi o dado em claro no processo: o que fica em disco nao permite
    reconstruir a lista original.
    """
    from ..core.normalize import normalizar
    origem, saida = Path(origem), Path(saida)
    vistos = set()
    for linha in origem.read_text(encoding="utf-8", errors="replace").splitlines():
        v = linha.strip().lower()
        if not v:
            continue
        if "@" not in v:
            t = normalizar(v)
            v = (t.e164 or v).lower()
        vistos.add(hashlib.sha256(v.encode()).hexdigest())
    saida.write_text("\n".join(sorted(vistos)), encoding="utf-8")
    if manifesto:
        saida.with_suffix(".json").write_text(
            json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(vistos)
