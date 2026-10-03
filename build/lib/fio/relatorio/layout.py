"""Layout de grafo por forcas (Fruchterman-Reingold), em Python puro.

Semente fixa: o mesmo caso desenha o mesmo grafo em qualquer maquina, o
que importa quando o relatorio e anexado a uma peca e precisa ser
reproduzido depois.
"""

from __future__ import annotations

import math
import random


def posicionar(ids: list[str], arestas: list[tuple[str, str]],
               largura: int = 1100, altura: int = 680,
               iteracoes: int = 320, semente: int = 42) -> dict[str, tuple[float, float]]:
    if not ids:
        return {}
    rnd = random.Random(semente)
    n = len(ids)
    pos = {}
    for i, k in enumerate(ids):
        ang = 2 * math.pi * i / n
        raio = min(largura, altura) * 0.32
        pos[k] = [largura / 2 + raio * math.cos(ang) + rnd.uniform(-9, 9),
                  altura / 2 + raio * math.sin(ang) + rnd.uniform(-9, 9)]

    area = largura * altura
    k = math.sqrt(area / n) * 0.85
    temp = largura / 8.0
    resfria = temp / (iteracoes + 1)
    validas = [(a, b) for a, b in arestas if a in pos and b in pos and a != b]

    for _ in range(iteracoes):
        desl = {i: [0.0, 0.0] for i in ids}
        for i in range(n):
            for j in range(i + 1, n):
                a, b = ids[i], ids[j]
                dx = pos[a][0] - pos[b][0]
                dy = pos[a][1] - pos[b][1]
                d2 = dx * dx + dy * dy
                if d2 < 0.01:
                    dx, dy, d2 = rnd.uniform(-1, 1), rnd.uniform(-1, 1), 1.0
                d = math.sqrt(d2)
                f = (k * k) / d
                desl[a][0] += dx / d * f
                desl[a][1] += dy / d * f
                desl[b][0] -= dx / d * f
                desl[b][1] -= dy / d * f
        for a, b in validas:
            dx = pos[a][0] - pos[b][0]
            dy = pos[a][1] - pos[b][1]
            d = math.sqrt(dx * dx + dy * dy) or 0.01
            f = (d * d) / k
            desl[a][0] -= dx / d * f
            desl[a][1] -= dy / d * f
            desl[b][0] += dx / d * f
            desl[b][1] += dy / d * f
        for i in ids:
            dx, dy = desl[i]
            d = math.sqrt(dx * dx + dy * dy) or 0.01
            pos[i][0] += dx / d * min(d, temp)
            pos[i][1] += dy / d * min(d, temp)
            pos[i][0] = min(largura - 60, max(60, pos[i][0]))
            pos[i][1] = min(altura - 40, max(40, pos[i][1]))
        temp -= resfria
    return {i: (round(p[0], 1), round(p[1], 1)) for i, p in pos.items()}
