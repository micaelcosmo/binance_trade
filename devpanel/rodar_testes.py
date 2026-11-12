"""Roda a suíte pytest e grava o placar em devpanel/testes.json (card "Testes" do painel).

    .venv/Scripts/python devpanel/rodar_testes.py [--python CAMINHO]

Por padrão usa o venv 3.13 (mesma versão do Docker) em D:\\binance_trade_work\\venv313;
cai para o Python atual se ele não existir. Só grava números, nomes de teste que falharam
e o commit — nenhuma saída bruta.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SAIDA = os.path.join(ROOT, "devpanel", "testes.json")
VENV313 = r"D:\binance_trade_work\venv313\Scripts\python.exe"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", default=VENV313 if os.path.exists(VENV313) else sys.executable)
    a = ap.parse_args()
    t0 = time.time()
    r = subprocess.run([a.python, "-m", "pytest", "-q", "-rfE", "-p", "no:cacheprovider"], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = r.stdout + r.stderr
    placar = {k: 0 for k in ("passed", "failed", "errors", "skipped")}
    resumo = [ln for ln in out.splitlines() if re.search(r"\d+ (passed|failed|error)", ln)]
    for n, k in re.findall(r"(\d+) (passed|failed|errors?|skipped)", resumo[-1] if resumo else ""):
        placar["errors" if k.startswith("error") else k] = int(n)
    falhas = sorted(set(re.findall(r"^(?:FAILED|ERROR) (\S+)", out, re.M)))[:20]
    versao = subprocess.run([a.python, "-c", "import sys;print(sys.version.split()[0])"],
                            capture_output=True, text=True).stdout.strip()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    agora = time.time()
    dados = {**placar, "falhas": falhas, "python": versao, "commit": commit,
             "duracaoS": round(agora - t0, 1), "quandoEpoch": round(agora, 3),
             "quando": dt.datetime.fromtimestamp(agora).astimezone().isoformat(timespec="seconds"),
             "codigoSaida": r.returncode}
    tmp = SAIDA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
    os.replace(tmp, SAIDA)
    print(f"{placar} em {dados['duracaoS']} s -> devpanel/testes.json")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
