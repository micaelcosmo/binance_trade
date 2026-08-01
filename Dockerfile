FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="binance-trade-bot"
LABEL org.opencontainers.image.description="Binance Trade Bot Pro - AI Edition (GUI via noVNC)"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3-pip \
    python3-tk \
    xvfb \
    x11vnc \
    fluxbox \
    novnc \
    websockify \
    git \
    tzdata \
    ca-certificates \
    openssl \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-docker.txt .
RUN python3.11 -m pip install --upgrade pip setuptools wheel \
    && python3.11 -m pip install --no-cache-dir -r requirements-docker.txt \
    && python3.11 -c "import pathlib, site; p=pathlib.Path(site.getsitepackages()[0])/'pandas_ta.py'; p.write_text('import pandas_ta_classic\\nfrom pandas_ta_classic import *\\n')" \
    && python3.11 -m pip install --no-cache-dir --no-deps unicorn_binance_websocket_api==2.10.2 \
    && python3.11 -m pip install --no-cache-dir \
        colorama websocket-client cheroot pyopenssl requests flask_restful aniso8601 pytz six \
        orjson psutil simplejson "unicorn-fy>=0.15.0"

COPY binance_trade_bot/ ./binance_trade_bot/
COPY painel.py backtest.py ./
COPY user.cfg.exemple supported_coin_list.exemple ./
COPY docker/entrypoint.sh ./docker/entrypoint.sh

RUN chmod +x /app/docker/entrypoint.sh \
    && mkdir -p /app/data /app/runtime /app/logs \
    && groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --create-home --shell /usr/sbin/nologin app \
    && chown -R app:app /app

USER app

EXPOSE 6080

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD pgrep -f "painel.py" >/dev/null || exit 1

ENTRYPOINT ["/app/docker/entrypoint.sh"]
