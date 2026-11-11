"""Indicadores técnicos em pandas/numpy puros (sem pandas_ta, Python 3.14).

As fórmulas seguem as convenções do pandas_ta usadas pela profit_gain:
RSI/ATR/ADX com média de Wilder (RMA), EMA com ``adjust=False``, Bollinger
com desvio-padrão populacional (ddof=0), MACD 12/26/9.

Todas as funções são causais: o valor na linha ``i`` só usa linhas ``<= i``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def rma(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = rma(d.clip(lower=0), n)
    dn = rma((-d).clip(lower=0), n)
    rs = up / dn.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    out = out.where(dn != 0, 100.0)  # sem perdas → RSI 100
    return out.where(up.notna())


def true_range(df: pd.DataFrame) -> pd.Series:
    pc = df["close"].shift(1)
    return pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()],
                     axis=1).max(axis=1)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    return rma(true_range(df), n)


def macd_hist(close: pd.Series, fast=12, slow=26, signal=9) -> pd.Series:
    m = ema(close, fast) - ema(close, slow)
    return m - ema(m, signal)


def bbands(close: pd.Series, n: int = 20):
    """Retorna (média, desvio) — a banda inferior é média − k·desvio."""
    mid = sma(close, n)
    sd = close.rolling(n, min_periods=n).std(ddof=0)
    return mid, sd


def adx(df: pd.DataFrame, n: int = 14):
    """Retorna (ADX, +DI, −DI)."""
    up = df["high"].diff()
    dn = -df["low"].diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    tr = rma(true_range(df), n)
    pdi = 100 * rma(plus_dm, n) / tr
    mdi = 100 * rma(minus_dm, n) / tr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return rma(dx, n), pdi, mdi


def stoch(df: pd.DataFrame, k: int = 14, smooth_k: int = 3, d: int = 3):
    ll = df["low"].rolling(k, min_periods=k).min()
    hh = df["high"].rolling(k, min_periods=k).max()
    raw = 100 * (df["close"] - ll) / (hh - ll).replace(0, np.nan)
    kk = sma(raw, smooth_k)
    return kk, sma(kk, d)


def ibs(df: pd.DataFrame) -> pd.Series:
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    return ((df["close"] - df["low"]) / rng).fillna(0.5)


def bullish_divergence(low: pd.Series, osc: pd.Series, half: int) -> pd.Series:
    """Mínima de preço mais baixa + mínima do oscilador mais alta, comparando a
    janela recente (``half`` velas) com a janela anterior (``half`` velas)."""
    lo_recent = low.rolling(half, min_periods=half).min()
    lo_prev = lo_recent.shift(half)
    o_recent = osc.rolling(half, min_periods=half).min()
    o_prev = o_recent.shift(half)
    return ((lo_recent < lo_prev) & (o_recent > o_prev)).fillna(False)


def avwap_from_swing_high(df: pd.DataFrame, lookback: int = 48) -> pd.Series:
    """VWAP ancorada na máxima mais alta das últimas ``lookback`` velas
    (âncora = vela da máxima, inclusive) até a vela atual. Causal."""
    tp = ((df["high"] + df["low"] + df["close"]) / 3).to_numpy()
    vol = df["volume"].to_numpy()
    high = df["high"].to_numpy()
    n = len(df)
    pv = np.concatenate([[0.0], np.cumsum(tp * vol)])
    vv = np.concatenate([[0.0], np.cumsum(vol)])
    out = np.full(n, np.nan)
    hs = pd.Series(high)
    # índice da máxima na janela [i-lookback+1, i]
    arg = hs.rolling(lookback, min_periods=lookback).apply(np.argmax, raw=True).to_numpy()
    for i in range(n):
        if np.isnan(arg[i]):
            continue
        a = i - lookback + 1 + int(arg[i])
        v = vv[i + 1] - vv[a]
        if v > 0:
            out[i] = (pv[i + 1] - pv[a]) / v
    return pd.Series(out, index=df.index)
