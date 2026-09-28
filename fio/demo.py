"""Caso de demonstracao pronto, para quem esta abrindo o programa pela
primeira vez. Tudo ficticio e tudo offline: os CSV em dados_demo imitam o
formato da Receita Federal, com empresas e pessoas inventadas.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .caso import CasoEmDisco, raiz
from .politica import Caso
from .grafo.modelo import Entidade
from .core.normalize import normalizar
from .indice import construir

DADOS = Path(__file__).with_name("dados_demo")
CASO_ID = "DEMO-FRAUDE-BOLETO"


def montar(ator: str = "demonstracao", recriar: bool = False, log=lambda s: None) -> dict:
    from .lab.pipeline import Config, executar
    base = raiz()
    base.mkdir(parents=True, exist_ok=True)
    idx = base / "demo-cnpj.sqlite"
    if recriar or not idx.exists():
        if idx.exists():
            idx.unlink()
        construir(DADOS, idx, log=lambda s: None)

    cd = CasoEmDisco(CASO_ID)
    if cd.existe and not recriar:
        return {"caso": CASO_ID, "ja_existia": True}
    if cd.dir.exists():
        shutil.rmtree(cd.dir)

    ata = base / "demo-ata_reuniao.txt"
    shutil.copy(DADOS / "ata_reuniao.txt", ata)
    telefones = ["(31) 98888-7777", "21988887778", "31 9 8888-7779"]
    c = Caso(id=CASO_ID,
             titulo="[DEMONSTRACAO] Linhas usadas em fraude de boleto",
             base_legal="pesquisa-academica",
             finalidade=("demonstracao do programa com dados ficticios, "
                         "sem pessoa real envolvida"),
             responsavel="Usuario de demonstracao",
             escopo=[normalizar(t).chave for t in telefones] + ["auroratech.com.br"],
             solicitante="Setor juridico ficticio",
             referencia="DEMO-0001",
             observacoes="Dados ficticios. Execucao sempre offline.")
    cd.criar(c, ator)
    for t in telefones:
        n = normalizar(t)
        cd.add_alvo(Entidade("telefone", n.chave, rotulo=n.formatado(),
                             atributos={"ddd": n.ddd, "assinante": n.assinante,
                                        "faixa": n.faixa, "uf": n.uf, "e164": n.e164}),
                    ator)
    cd.add_alvo(Entidade("documento", str(ata), rotulo="Ata de reuniao (demo)",
                         atributos={"caminho": str(ata)}), ator)
    c = cd.caso()
    c.quesitos = [
        {"n": 1, "texto": "As tres linhas estao ligadas a um mesmo grupo empresarial?",
         "resposta": "", "entidades": []},
        {"n": 2, "texto": "Ha pessoa comum ao quadro de socios das empresas encontradas?",
         "resposta": "", "entidades": []},
    ]
    cd.salvar_caso(c)
    exp = executar(cd, ator, Config(
        coletores=["extrator", "nucleo", "cnpj-reverso"], profundidade=2,
        offline=True, expandir_escopo=True, descricao="montagem da demonstracao",
        extras={"segredos": {"indice_cnpj": str(idx)}}), log=log)
    return {"caso": CASO_ID, "experimento": exp.id, "metricas": exp.metricas}
