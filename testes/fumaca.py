"""Teste de fumaca da linha de comando, como um usuario usaria.

Roda cada comando em subprocesso, num FIO_HOME temporario, e confere codigo
de saida e trecho esperado da saida. Uso:  python testes/fumaca.py
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CASO = "FUMACA-1"


def rodar(tmp: str, *args, esperado: str = "", codigo: int = 0) -> tuple[bool, str]:
    env = {**os.environ, "FIO_HOME": tmp, "PYTHONPATH": str(RAIZ)}
    t = time.perf_counter()
    p = subprocess.run([sys.executable, "-m", "fio", "--ator", "fumaca", *args],
                       capture_output=True, text=True, env=env, cwd=tmp,
                       encoding="utf-8", errors="replace")
    ok = p.returncode == codigo and esperado in (p.stdout + p.stderr)
    return ok, f"{time.perf_counter() - t:5.2f}s", p.stdout + p.stderr


def main() -> int:
    resultados = []
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "planilha.csv").write_text(
            "nome;telefone;email\nClinica Exemplo;(31) 3333-4444;a@exemplo.test\n", encoding="utf-8")
        passos = [
            ("versao", ["--versao"], "fio 2."),
            ("numero", ["numero", "0 21 31 9 8888-7777"], "+5531988887777"),
            ("doc cnpj alfanumerico", ["doc", "cnpj", "12.ABC.345/01DE-35"], '"valido": true'),
            ("doc cpf-parcial", ["doc", "cpf-parcial", "***456789**"], "PR"),
            ("dorks", ["dorks", "--valor", "31988887777"], "(31) 98888-7777"),
            ("bases legais", ["bases"], "lgpd-7-vi"),
            ("caso novo", ["caso", "novo", "--id", CASO, "--titulo", "Fumaca",
                           "--base-legal", "pesquisa-academica",
                           "--finalidade", "teste de fumaca automatizado",
                           "--responsavel", "ci", "--escopo", "+5531988887777"], "criado"),
            ("caso sem base legal e recusado", ["caso", "novo", "--id", "X", "--titulo", "x",
                                                "--base-legal", "lgpd-7-vi", "--finalidade", "curta",
                                                "--responsavel", "ci"], "finalidade", 2),
            ("alvo", ["alvo", "--caso", CASO, "--tipo", "telefone", "--valor", "(31) 98888-7777"], "adicionado"),
            ("investigar offline", ["investigar", "--caso", CASO, "--offline",
                                    "--coletores", "nucleo"], "coletores executados"),
            ("quesito", ["quesito", "add", "--caso", CASO, "--texto", "Pergunta de teste?"], "registrado"),
            ("pipeline", ["lab", "pipeline", "--caso", CASO, "--offline", "--coletores", "nucleo"], "concluido"),
            ("experimentos", ["lab", "experimentos", "--caso", CASO], "EXP-"),
            ("relatorio", ["relatorio", "--caso", CASO, "--saida", "r.html", "--markdown", "r.md"], "relatorio HTML"),
            ("laudo", ["laudo", "--caso", CASO, "--saida", "l.html"], "laudo"),
            ("relint", ["laudo", "--caso", CASO, "--modelo", "relint", "--saida", "i.html"], "relint"),
            ("ledger integro", ["ledger", "verificar", "--caso", CASO], "cadeia integra"),
            ("receita generica", ["receita", "construir", "--id", "generica", "--origem", "planilha.csv"], '"chaves": "2"'),
            ("demo", ["demo"], "montado"),
            ("plugins", ["lab", "plugins"], "cnpj-reverso"),
            ("avaliacao sintetica", ["lab", "avaliar", "--sementes", "1,2", "--grupos", "6",
                                     "--saida", "aval"], "Avaliacao em lote"),
        ]
        for nome, args, esperado, *cod in passos:
            ok, tempo, saida = rodar(tmp, *args, esperado=esperado, codigo=cod[0] if cod else 0)
            resultados.append({"passo": nome, "ok": ok, "tempo": tempo})
            print(f"[{'OK   ' if ok else 'FALHA'}] {tempo}  {nome}")
            if not ok:
                print("        " + saida.strip().replace("\n", "\n        ")[:900])

        # adulteracao: editar o ledger tem de ser detectado
        led = Path(tmp) / "casos" / CASO / "ledger.jsonl"
        led.write_text(led.read_text(encoding="utf-8").replace("Fumaca", "FUMACA"), encoding="utf-8")
        ok, tempo, _ = rodar(tmp, "ledger", "verificar", "--caso", CASO, esperado="COMPROMETIDA", codigo=4)
        resultados.append({"passo": "ledger adulterado e detectado", "ok": ok, "tempo": tempo})
        print(f"[{'OK   ' if ok else 'FALHA'}] {tempo}  ledger adulterado e detectado")

        # bancada sobe e responde com token
        env = {**os.environ, "FIO_HOME": tmp, "PYTHONPATH": str(RAIZ)}
        proc = subprocess.Popen([sys.executable, "-m", "fio", "lab", "bancada", "--porta", "8791",
                                 "--sem-navegador"], env=env, stdout=subprocess.PIPE, text=True)
        try:
            linha = proc.stdout.readline()
            token = linha.split("#t=")[-1].strip()
            time.sleep(0.4)
            req = urllib.request.Request("http://127.0.0.1:8791/api/casos",
                                         headers={"X-FIO-Token": token})
            with urllib.request.urlopen(req, timeout=10) as r:
                casos = json.loads(r.read())
            ok = any(c["id"] == CASO for c in casos)
        except Exception as e:
            ok = False
            print("        ", e)
        finally:
            proc.terminate()
        resultados.append({"passo": "bancada web responde", "ok": ok, "tempo": "-"})
        print(f"[{'OK   ' if ok else 'FALHA'}]   -    bancada web responde")

    falhas = [r for r in resultados if not r["ok"]]
    print(f"\n{len(resultados) - len(falhas)}/{len(resultados)} passos ok")
    if os.environ.get("FIO_FUMACA_JSON"):
        Path(os.environ["FIO_FUMACA_JSON"]).write_text(json.dumps(resultados, indent=2))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
