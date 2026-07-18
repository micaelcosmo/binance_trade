# =============================================================================
# Binance Trade Bot Pro — AI Edition (Web)
# Container do PAINEL WEB (app.py). O motor de trading sobe como subprocess
# quando acionado pelo painel (botão RUN) — decisão web-first: painel.py
# (Tkinter) está deprecado e morre na v3.
#
# Segredos (user.cfg) e estado (JSONs) NÃO são copiados para a imagem:
# entram por bind mount do repositório (ver compose.yaml).
# =============================================================================
FROM python:3.13-slim

# git  -> exibição de versão (git describe) e auto-updater do painel
# curl -> healthcheck do compose
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Camada de dependências (cacheável). O lockfile espelha o ambiente local
# comprovadamente funcional (py3.13). Os unicorn-* entram com --no-deps para
# não brigar com o resolver por causa do pin antigo de websockets — a
# coexistência com websockets 16 é a realidade validada em produção local.
COPY requirements-docker.lock .
RUN pip install --no-cache-dir -r requirements-docker.lock \
    && pip install --no-cache-dir --no-deps \
        unicorn-binance-websocket-api==2.13.0 \
        unicorn-binance-rest-api==2.11.0

# O bind mount do compose sobrepõe /app em runtime; este COPY garante que a
# imagem também funcione sozinha (docker run) sem o mount.
COPY . .

# backtest.py (legado) abre SqliteDict("data/...") no import e exige a pasta.
RUN mkdir -p data logs

# O repo montado pertence a outro dono (host) — sem isto o git recusa
# "dubious ownership" e a versão cai no fallback.
RUN git config --global --add safe.directory /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    APP_DEBUG=0

EXPOSE 5000

CMD ["python", "app.py"]
