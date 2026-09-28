"""Testes contra as fontes REAIS, com alvos neutros (nenhuma pessoa).

Detecta quando uma API muda de formato ("drift de contrato") -- o tipo de
quebra que teste com resposta simulada nao pega. Roda no CI toda semana e
pode ser rodado a mao:  python testes/ao_vivo.py

Alvos: CNPJ do Banco do Brasil (companhia aberta), CEP da Praca da Se,
dominio nic.br, termo "licitacao" no Querido Diario.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fio.politica import Caso                      # noqa: E402
from fio.grafo.modelo import Grafo, Entidade       # noqa: E402
from fio.evidencia.ledger import Ledger            # noqa: E402
from fio.evidencia.cache import CacheHTTP          # noqa: E402
from fio.coletores import REGISTRO, Contexto       # noqa: E402

CASOS = [
    ("cnpj-api", Entidade("cnpj", "00000000000191"),
     lambda a: any(x.relacao == "tem_socio" or x.relacao == "telefone_declarado" for x in a)),
    ("viacep", Entidade("cep", "01001000"),
     lambda a: any(x.destino.tipo == "municipio" and x.destino.valor == "3550308" for x in a)),
    ("rdap", Entidade("dominio", "nic.br"),
     lambda a: len(a) > 0),
    ("querido-diario", Entidade("organizacao", "licitacao", rotulo="licitacao"),
     lambda a: any(x.relacao == "publicado_em" for x in a)),
]


def main() -> int:
    falhas = 0
    res = []
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        caso = Caso(id="AO-VIVO", titulo="teste de contrato das APIs",
                    base_legal="pesquisa-academica",
                    finalidade="verificar formato das APIs publicas com alvos neutros",
                    responsavel="ci", escopo=["00000000000191", "01001000", "nic.br", "licitacao"])
        ctx = Contexto(caso=caso, grafo=Grafo("AO-VIVO"), ledger=Ledger(d, "AO-VIVO", "ci"),
                       cache=CacheHTTP(d / "c.sqlite", ttl_segundos=0), intervalo=1.0, timeout=25)
        for nome, alvo, criterio in CASOS:
            achados = REGISTRO[nome].executar(alvo, ctx)
            ok = bool(achados) and criterio(achados)
            falhas += not ok
            ultimo = [r for r in ctx.ledger.registros() if r.coletor == nome][-2:]
            detalhe = "; ".join(r.resumo for r in ultimo if r.resumo)
            res.append({"coletor": nome, "ok": ok, "achados": len(achados), "detalhe": detalhe})
            print(f"[{'OK   ' if ok else 'FALHA'}] {nome:<16} {len(achados):>3} achados  {detalhe[:90]}")
        ctx.cache.fechar()
    if os.environ.get("FIO_AO_VIVO_JSON"):
        Path(os.environ["FIO_AO_VIVO_JSON"]).write_text(json.dumps(res, indent=2))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
