"""Gera o GIF de demonstracao da bancada (docs/img/demo.gif).

Sobe a bancada com o caso de demonstracao (ficticio, offline), percorre a
jornada de um leigo com o Playwright e monta o GIF com o ffmpeg. Nao faz
parte do pacote: so quem mantem a documentacao precisa disto.

    pip install playwright && python tools/gerar_midia.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from playwright.sync_api import sync_playwright  # noqa: E402

DESTINO = RAIZ / "docs" / "img" / "demo.gif"
LARGURA = 1280
# (rotulo, duracao em segundos)
QUADROS: list[tuple[str, float]] = []


def main() -> int:
    if not shutil.which("ffmpeg"):
        print("ffmpeg nao encontrado", file=sys.stderr)
        return 1
    tmp = Path(tempfile.mkdtemp())
    os.environ["FIO_HOME"] = str(tmp / "home")
    from fio.lab.bancada.servidor import servir, Estado
    srv = servir(porta=8791, abrir=False, token="midia", bloquear=False)
    time.sleep(0.4)
    quadros = tmp / "q"
    quadros.mkdir()
    n = [0]

    def foto(pg, dur: float) -> None:
        pg.wait_for_timeout(350)
        n[0] += 1
        pg.screenshot(path=str(quadros / f"{n[0]:03d}.png"))
        QUADROS.append((f"{n[0]:03d}.png", dur))

    exe = os.environ.get("FIO_CHROMIUM")
    try:
        with sync_playwright() as pw:
            nav = pw.chromium.launch(**({"executable_path": exe, "args": ["--no-sandbox"]} if exe else {}))
            pg = nav.new_page(viewport={"width": LARGURA, "height": 900}, color_scheme="light")
            pg.goto("http://127.0.0.1:8791/#t=midia")
            pg.wait_for_selector("text=Bem-vindo ao F.I.O. Lab")
            foto(pg, 2.2)
            pg.click("#bvdemo")
            pg.wait_for_selector("#g circle", timeout=20000)
            pg.wait_for_timeout(1800)               # deixa o layout de forcas assentar
            pg.locator("#gcv").scroll_into_view_if_needed()
            foto(pg, 2.6)
            pg.locator("#g circle").nth(0).click(force=True)
            pg.locator("#gcv").scroll_into_view_if_needed()
            foto(pg, 2.8)
            for aba, dur in (("vínculos", 2.2), ("observações", 2.6), ("custódia", 2.2)):
                pg.click(f".tab[data-t='{aba}']")
                foto(pg, dur)
            pg.click(".tab[data-t='grafo']")
            pg.wait_for_timeout(1200)
            pg.click("#tema")
            pg.locator("#gcv").scroll_into_view_if_needed()
            foto(pg, 2.8)
            nav.close()
    finally:
        Estado.fila.parar()
        srv.shutdown()
        srv.server_close()

    lista = tmp / "lista.txt"
    with lista.open("w") as fh:
        for nome, dur in QUADROS:
            fh.write(f"file '{quadros / nome}'\nduration {dur}\n")
        fh.write(f"file '{quadros / QUADROS[-1][0]}'\n")
    paleta = tmp / "paleta.png"
    filtro = f"fps=10,scale={LARGURA * 3 // 4}:-1:flags=lanczos"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lista), "-vf", f"{filtro},palettegen=max_colors=96", str(paleta)], check=True)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lista), "-i", str(paleta), "-lavfi",
                    f"{filtro}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4",
                    "-loop", "0", str(DESTINO)], check=True)
    print(f"{DESTINO} ({DESTINO.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
