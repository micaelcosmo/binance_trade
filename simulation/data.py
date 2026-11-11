"""Downloader + cache de klines PÚBLICOS da Binance (sem autenticação).

- Endpoint: https://api.binance.com/api/v3/klines (limit=1000 por chamada).
- Respeita rate limit: pausa entre chamadas e lê X-MBX-USED-WEIGHT-1M.
- Cache em data/sim/<SYMBOL>_<interval>.csv.gz (gitignored). Downloads são
  incrementais: se o arquivo existe, só busca o que falta no fim.

Uso:
    python -m simulation.data                      # baixa o conjunto padrão
    python -m simulation.data --symbols BTCUSDT ETHUSDT --intervals 15m 1h
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT, "data", "sim")
API = "https://api.binance.com/api/v3/klines"

# Perfis diferentes: majors (BTC/ETH/BNB), L1 voláteis (SOL/AVAX/ADA),
# payments (XRP), memes (DOGE/TRUMP), oráculo (LINK), L2 (POL — também em
# supported_coin_list.exemple).
DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "POLUSDT", "TRUMPUSDT",
]
DEFAULT_INTERVALS = ["15m", "1h", "4h", "1d"]
# 15m/1h/4h: jul/2024 → nov/2026 (inclui a alta do fim de 2024 e as quedas de
# 2025/2026). 1d começa antes para aquecer a SMA200 diária.
DEFAULT_START = {"15m": "2024-07-01", "1h": "2024-07-01", "4h": "2024-07-01", "1d": "2023-06-01"}
DEFAULT_END = "2026-11-01"

INTERVAL_MS = {"15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
COLUMNS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
           "quote_volume", "trades", "taker_base", "taker_quote", "ignore"]
KEEP = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades"]


def _ms(date_str: str) -> int:
    return int(datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def cache_path(symbol: str, interval: str) -> str:
    return os.path.join(DATA_DIR, f"{symbol}_{interval}.csv.gz")


def _get(params: dict, retries: int = 5):
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "sim-klines-downloader"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                weight = int(resp.headers.get("x-mbx-used-weight-1m") or 0)
                data = json.loads(resp.read())
            if weight > 3000:  # limite público é 6000/min; folga grande
                time.sleep(20)
            return data
        except urllib.error.HTTPError as err:
            if err.code in (418, 429):
                wait = int(err.headers.get("Retry-After") or 60)
                time.sleep(wait)
            elif err.code == 400:
                return []  # símbolo inexistente no período
            else:
                time.sleep(2 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"falha ao baixar {params}")


def fetch(symbol: str, interval: str, start_ms: int, end_ms: int, pause: float = 0.25) -> pd.DataFrame:
    rows = []
    cur = start_ms
    while cur < end_ms:
        batch = _get({"symbol": symbol, "interval": interval, "startTime": cur,
                      "endTime": end_ms - 1, "limit": 1000})
        if not batch:
            break
        rows.extend(batch)
        nxt = int(batch[-1][0]) + INTERVAL_MS[interval]
        if nxt <= cur:
            break
        cur = nxt
        time.sleep(pause)
    if not rows:
        return pd.DataFrame(columns=KEEP)
    df = pd.DataFrame(rows, columns=COLUMNS)[KEEP]
    for c in ["open", "high", "low", "close", "volume", "quote_volume"]:
        df[c] = df[c].astype(float)
    for c in ["open_time", "close_time", "trades"]:
        df[c] = df[c].astype("int64")
    return df


def download(symbol: str, interval: str, start: str, end: str, verbose: bool = True) -> pd.DataFrame:
    os.makedirs(DATA_DIR, exist_ok=True)
    path = cache_path(symbol, interval)
    start_ms, end_ms = _ms(start), _ms(end)
    old = None
    if os.path.exists(path):
        old = pd.read_csv(path)
        if len(old):  # incremental: só busca o que falta no fim
            start_ms = max(start_ms, int(old.open_time.iloc[-1]) + INTERVAL_MS[interval])
    if start_ms < end_ms:
        new = fetch(symbol, interval, start_ms, end_ms)
        df = pd.concat([old, new]) if old is not None else new
    else:
        df = old
    df = df.drop_duplicates("open_time").sort_values("open_time").reset_index(drop=True)
    # só velas FECHADAS (close_time no passado e < end)
    df = df[df.close_time < min(end_ms, int(time.time() * 1000))]
    df.to_csv(path, index=False, compression="gzip")
    if verbose:
        span = ""
        if len(df):
            a = datetime.fromtimestamp(df.open_time.iloc[0] / 1000, timezone.utc).date()
            b = datetime.fromtimestamp(df.open_time.iloc[-1] / 1000, timezone.utc).date()
            span = f"{a} -> {b}"
        print(f"{symbol:>10} {interval:>3}: {len(df):>6} velas {span}", flush=True)
    return df


def load(symbol: str, interval: str) -> pd.DataFrame:
    """Lê do cache (sem rede). Lança FileNotFoundError se não baixado."""
    df = pd.read_csv(cache_path(symbol, interval))
    return df.sort_values("open_time").reset_index(drop=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS)
    ap.add_argument("--intervals", nargs="*", default=DEFAULT_INTERVALS)
    ap.add_argument("--end", default=DEFAULT_END)
    args = ap.parse_args(argv)
    for sym in args.symbols:
        for itv in args.intervals:
            download(sym, itv, DEFAULT_START[itv], args.end)
    return 0


if __name__ == "__main__":
    sys.exit(main())
