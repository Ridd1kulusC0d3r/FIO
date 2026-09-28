"""Exemplo de plugin do F.I.O. Lab.

Copie para FIO_HOME/plugins/ (padrao ~/.fio/plugins/). O lab carrega no
proximo pipeline e registra o SHA-256 deste arquivo em cada experimento.

Este exemplo implementa um analisador (sem rede) que sinaliza telefones
nao-geograficos (0800/4004) ligados a pessoa fisica -- combinacao rara,
que costuma indicar erro de cadastro ou numero de central usado como
contato pessoal.
"""

from fio.analise.base import Analisador, registrar_analisador


@registrar_analisador
class NaoGeograficoEmPessoa(Analisador):
    nome = "exemplo-nao-geografico-pessoa"
    descricao = "Telefone 0800/400x ligado diretamente a pessoa fisica."

    def analisar(self, g) -> int:
        antes = len(g.observacoes)
        for tel in g.por_tipo("telefone"):
            if not tel.valor.startswith(("0800", "0300", "400")):
                continue
            for _, vid in g.vizinhos(tel.id):
                if g.entidades[vid].tipo == "pessoa":
                    g.observar("nao-geografico-em-pessoa",
                               f"{tel.valor} (numero corporativo nacional) ligado "
                               f"a pessoa {g.entidades[vid].rotulo}.",
                               [tel.id, vid], "atencao", self.nome)
        return len(g.observacoes) - antes
