"""Motor de simulação candle-a-candle da profit_gain (Porteiro + saídas).

Princípios
----------
* **Sem look-ahead.** A decisão acontece no FECHAMENTO de cada vela de 15m
  (instante ``T = open_time + 15m``). Indicadores de 1h/4h/1d usam só velas
  cujo fechamento ``open_time + intervalo <= T`` (alinhamento por timestamp de
  fechamento, ``searchsorted(..., 'right') - 1``). A ordem é executada no
  ``open`` da vela de 15m seguinte.
  Diferença conhecida para o live: o bot real calcula os indicadores incluindo
  a vela AINDA ABERTA (o último item de ``get_klines``). Aqui usamos só velas
  fechadas — é o que dá para reproduzir sem look-ahead.
* **A IA (Gemini) NÃO é simulada.** No lugar dela há um ORÁCULO MOCK
  determinístico: um score de confluência das técnicas do doc 001 (RSI(2)
  virando, divergência RSI/MACD, IBS, estocástico, rejeição de fundo, regime
  SMA200, ADX/DI). Ele serve para medir se confluência técnica melhora o
  Porteiro; não reproduz o julgamento do LLM. ``score_min=None`` = oráculo
  aprova tudo que passa no Porteiro (limite superior de permissividade).
* **Saída conservadora.** Modo ``intrabar``: se a mínima da vela toca o stop,
  sai NO stop (ou na abertura, se abriu abaixo — gap), mesmo que a máxima da
  mesma vela tenha batido o alvo (pior caso). Sem stop, percorre o caminho
  O→L→H→C (vela de alta) ou O→H→L→C (vela de baixa) para trailing/alvo.
  Modo ``close``: só checa no fechamento de cada vela de 15m (latência do
  scout) e executa no fechamento.
* Fills via :class:`simulation.mock_exchange.MockExchange` (taxa 0,1% por lado
  + slippage). Entrada all-in de 99% do USDT, como ``execute_real_trade``.
* Regras de disciplina: limite de trades/dia e meta diária (soma de % por
  trade, como o live), dia em UTC−3; cooldown de 45 min após veto do oráculo.
* NÃO simulado: Tribunal de Swap (depende da IA e de ≥4 candidatas
  simultâneas; ver parecer 000 §5), flags da UI, recuperação de estado.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict, replace
from typing import Optional

import numpy as np
import pandas as pd

from simulation import indicators as ind
from simulation.mock_exchange import MockExchange

MS = {"15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
DAY_OFFSET_MS = -3 * 3_600_000  # America/Sao_Paulo (UTC−3, sem horário de verão)

# pesos do oráculo mock (soma máx = SCORE_MAX)
SCORE_WEIGHTS = {
    "rsi2_turn_15m": 2, "rsi_div_1h": 2, "macd_div_1h": 1, "ibs_1h_low": 1,
    "stoch_cross_15m": 1, "macd_1h_shifting_up": 1, "bottom_rejection_1h": 1,
    "bullish_15m": 1, "touch_both": 1, "above_sma200": 1, "btc_above_sma200": 1,
}
SCORE_PENALTY_STRONG_DOWN = 3  # ADX 4h > 30 com DI− dominante
SCORE_MAX = sum(SCORE_WEIGHTS.values())


@dataclass(frozen=True)
class Params:
    name: str = "BASE"
    # ---- Porteiro (entrada) — valores atuais da profit_gain
    atr_mult: float = 2.0          # min_24h_change <= -atr_mult × ATR%(1h)
    bb_std: float = 2.0
    bb_touch: bool = True          # exige toque na BB inferior (15m últimas 3 ou 1h últimas 2)
    vol_min_pct: float = 80.0      # volume 15m vs média das 10 anteriores
    ema_dist_max: float = -1.0     # preço vs EMA21 1h (%) deve ser < isto
    chg24_min: float = -15.0       # = -disaster_stop_pct
    chg24_max: float = 2.5
    gate_sma200: str = "none"      # none | asset | btc | both (diário, vela fechada)
    gate_adx4h: Optional[float] = None  # veta se ADX4h > x e DI− > DI+
    require_rsi2_turn: bool = False
    rsi2_level: float = 10.0
    score_min: Optional[float] = None   # limiar do oráculo mock (None = aprova tudo)
    veto_cooldown_bars: int = 3    # 45 min após veto (ai_cooldown_minutes)
    max_daily_trades: int = 3
    daily_target_pct: float = 5.0
    # ---- Saída
    exit_mode: str = "trail"       # trail | fixed | avwap
    trail_act: float = 1.5
    trail_drop: float = 0.3
    tp_pct: float = 1.5            # alvo fixo (fixed) / teto do alvo (avwap)
    tp_floor: float = 0.6          # piso do alvo AVWAP (cobre taxas)
    stop_mult: float = 4.0         # stop = ATR%(1h) × mult, com clamp
    stop_lo: float = 4.0
    stop_hi: float = 7.0           # = base_stop_loss_pct
    btc_stop_lo: float = 6.0
    btc_stop_hi: float = 10.5
    disaster: float = 15.0
    max_hold_h: Optional[float] = None
    check: str = "intrabar"        # intrabar | close
    fee: float = 0.001
    slippage: float = 0.0005
    # ---- sim-002: variações estruturais (defaults = comportamento da sim-001)
    stop_mode: str = "atr"         # atr | fixed
    stop_fixed_pct: float = 2.0
    be_trigger: Optional[float] = None   # pico >= x% → stop vai para breakeven
    be_offset: float = 0.2         # breakeven = ref × (1 + be_offset%) (cobre taxas)
    partial_frac: float = 0.0      # fração vendida no alvo 1 (0 = sem parcial)
    partial_tp: float = 1.5        # alvo 1 (%)
    be_after_partial: bool = False
    time_stop_h: Optional[float] = None  # após x h, sai se o pico < time_stop_min_pct
    time_stop_min_pct: float = 0.5
    confirm: str = "none"          # none | break_high | above_ema9
    confirm_bars: int = 4          # confirmação até N velas de 15m após o sinal
    entry_type: str = "market"     # market | limit
    limit_offset_pct: float = 0.0  # limite = close do scan × (1 − x%)
    limit_bars: int = 2            # validade da ordem limit (velas de 15m)
    limit_through_pct: float = 0.05  # exige a mínima ATRAVESSAR o limite em x% (conservador)

    def with_(self, **kw) -> "Params":
        return replace(self, **kw)


BASELINE = Params()


# =============================================================== features
def _align(avail_ms: np.ndarray, target_ms: np.ndarray) -> np.ndarray:
    """Índice da última vela do TF maior FECHADA até ``target_ms`` (−1 se nenhuma)."""
    return np.searchsorted(avail_ms, target_ms, side="right") - 1


def _take(arr: np.ndarray, idx: np.ndarray) -> np.ndarray:
    out = np.full(idx.shape, np.nan)
    ok = idx >= 0
    out[ok] = np.asarray(arr, dtype=float)[idx[ok]]
    return out


@dataclass
class Features:
    symbol: str
    open_time: np.ndarray
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    cols: dict                      # arrays alinhados ao índice 15m
    d15: pd.DataFrame = field(repr=False, default=None)
    d1h: pd.DataFrame = field(repr=False, default=None)
    idx1h: np.ndarray = field(repr=False, default=None)
    _bb_cache: dict = field(default_factory=dict, repr=False)
    _lists: tuple = field(default=None, repr=False)

    @property
    def is_btc(self) -> bool:
        return self.symbol.startswith("BTC")

    def touches(self, k: float):
        """(toque BB 15m nas últimas 3 velas, toque BB 1h nas últimas 2)."""
        if k not in self._bb_cache:
            t15 = (self.d15["low"] <= self.d15["bb_mid"] - k * self.d15["bb_sd"]).astype(float)
            t15_3 = t15.rolling(3, min_periods=1).max().to_numpy() > 0
            t1 = (self.d1h["low"] <= self.d1h["bb_mid"] - k * self.d1h["bb_sd"]).astype(float)
            t1_2 = t1.rolling(2, min_periods=1).max().to_numpy()
            t1h = _take(t1_2, self.idx1h) > 0
            self._bb_cache[k] = (t15_3, t1h)
        return self._bb_cache[k]

    def lists(self):
        if self._lists is None:
            self._lists = (self.open_time.tolist(), self.o.tolist(), self.h.tolist(),
                           self.l.tolist(), self.c.tolist(), self.cols["avwap_1h"].tolist())
        return self._lists


def build_features(symbol: str, d15: pd.DataFrame, d1h: pd.DataFrame, d4h: pd.DataFrame,
                   d1d: pd.DataFrame, btc_d1d: Optional[pd.DataFrame] = None) -> Features:
    d15 = d15.sort_values("open_time").reset_index(drop=True).copy()
    d1h = d1h.sort_values("open_time").reset_index(drop=True).copy()
    d4h = d4h.sort_values("open_time").reset_index(drop=True).copy()
    d1d = d1d.sort_values("open_time").reset_index(drop=True).copy()
    T = d15["open_time"].to_numpy() + MS["15m"]  # instante de decisão

    # ---- 15m
    d15["bb_mid"], d15["bb_sd"] = ind.bbands(d15["close"], 20)
    rsi2 = ind.rsi(d15["close"], 2)
    k, d = ind.stoch(d15)
    vol = d15["volume"]
    vol_avg10 = vol.shift(1).rolling(10, min_periods=10).mean()
    o95 = d15["open"].shift(95)
    low96 = d15["low"].rolling(96, min_periods=96).min()

    # ---- 1h
    d1h["ema9"] = ind.ema(d1h["close"], 9)
    d1h["ema21"] = ind.ema(d1h["close"], 21)
    d1h["macdh"] = ind.macd_hist(d1h["close"])
    d1h["rsi14"] = ind.rsi(d1h["close"], 14)
    d1h["atr14"] = ind.atr(d1h, 14)
    d1h["bb_mid"], d1h["bb_sd"] = ind.bbands(d1h["close"], 20)
    d1h["ibs"] = ind.ibs(d1h)
    body = (d1h["close"] - d1h["open"]).abs()
    wick = np.minimum(d1h["open"], d1h["close"]) - d1h["low"]
    d1h["rejection"] = (wick > body * 1.5).astype(float)
    d1h["macd_up"] = (d1h["macdh"] > d1h["macdh"].shift(1)).astype(float)
    d1h["rsi_div"] = ind.bullish_divergence(d1h["low"], d1h["rsi14"], 6).astype(float)
    d1h["macd_div"] = ind.bullish_divergence(d1h["low"], d1h["macdh"], 12).astype(float)
    d1h["avwap"] = ind.avwap_from_swing_high(d1h, 48)
    idx1h = _align(d1h["open_time"].to_numpy() + MS["1h"], T)

    # ---- 4h
    d4h["rsi14"] = ind.rsi(d4h["close"], 14)
    d4h["adx"], d4h["pdi"], d4h["mdi"] = ind.adx(d4h, 14)
    idx4h = _align(d4h["open_time"].to_numpy() + MS["4h"], T)

    # ---- 1d
    def daily_above(dd):
        dd = dd.sort_values("open_time").reset_index(drop=True)
        s200 = ind.sma(dd["close"], 200)
        above = np.where(s200.notna(), (dd["close"] > s200).astype(float), np.nan)
        return _take(above, _align(dd["open_time"].to_numpy() + MS["1d"], T))

    c = d15["close"].to_numpy()
    ema21 = _take(d1h["ema21"].to_numpy(), idx1h)
    atr1h = _take(d1h["atr14"].to_numpy(), idx1h)
    cols = {
        "chg24": ((d15["close"] - o95) / o95 * 100).to_numpy(),
        "min24": ((low96 - o95) / o95 * 100).to_numpy(),
        "atr_pct": atr1h / c * 100,
        "ema21_dist": (c - ema21) / ema21 * 100,
        "vol_pct": (vol / vol_avg10 * 100).to_numpy(),
        "rsi2_15m": rsi2.to_numpy(),
        "rsi2_15m_prev": rsi2.shift(1).to_numpy(),
        "stoch_k": k.to_numpy(), "stoch_d": d.to_numpy(),
        "stoch_k_prev": k.shift(1).to_numpy(), "stoch_d_prev": d.shift(1).to_numpy(),
        "bullish_15m": (d15["close"] > d15["open"]).to_numpy(),
        "ema9_15m": ind.ema(d15["close"], 9).to_numpy(),
        "prev_high_15m": d15["high"].shift(1).to_numpy(),
        "ibs_1h": _take(d1h["ibs"].to_numpy(), idx1h),
        "rejection_1h": _take(d1h["rejection"].to_numpy(), idx1h),
        "macd_up_1h": _take(d1h["macd_up"].to_numpy(), idx1h),
        "rsi_div_1h": _take(d1h["rsi_div"].to_numpy(), idx1h),
        "macd_div_1h": _take(d1h["macd_div"].to_numpy(), idx1h),
        "rsi14_1h": _take(d1h["rsi14"].to_numpy(), idx1h),
        "avwap_1h": _take(d1h["avwap"].to_numpy(), idx1h),
        "rsi14_4h": _take(d4h["rsi14"].to_numpy(), idx4h),
        "adx_4h": _take(d4h["adx"].to_numpy(), idx4h),
        "pdi_4h": _take(d4h["pdi"].to_numpy(), idx4h),
        "mdi_4h": _take(d4h["mdi"].to_numpy(), idx4h),
        "above_sma200": daily_above(d1d),
        "btc_above_sma200": daily_above(btc_d1d if btc_d1d is not None else d1d),
    }
    return Features(symbol, d15["open_time"].to_numpy(), d15["open"].to_numpy(),
                    d15["high"].to_numpy(), d15["low"].to_numpy(), c, cols, d15, d1h, idx1h)


# ================================================================ sinais
def oracle_score(f: Features, p: Params) -> np.ndarray:
    """Score de confluência do ORÁCULO MOCK (substituto determinístico da IA)."""
    x = f.cols
    t15, t1h = f.touches(p.bb_std)
    comp = {
        "rsi2_turn_15m": (x["rsi2_15m_prev"] < p.rsi2_level) & (x["rsi2_15m"] > x["rsi2_15m_prev"]),
        "rsi_div_1h": x["rsi_div_1h"] > 0,
        "macd_div_1h": x["macd_div_1h"] > 0,
        "ibs_1h_low": x["ibs_1h"] < 0.2,
        "stoch_cross_15m": (x["stoch_k_prev"] < 20) & (x["stoch_k"] > x["stoch_d"])
                           & (x["stoch_k_prev"] <= x["stoch_d_prev"]),
        "macd_1h_shifting_up": x["macd_up_1h"] > 0,
        "bottom_rejection_1h": x["rejection_1h"] > 0,
        "bullish_15m": x["bullish_15m"],
        "touch_both": t15 & t1h,
        "above_sma200": x["above_sma200"] > 0,
        "btc_above_sma200": x["btc_above_sma200"] > 0,
    }
    s = np.zeros(len(f.c))
    for key, w in SCORE_WEIGHTS.items():
        s += w * comp[key].astype(float)
    strong_down = (x["adx_4h"] > 30) & (x["mdi_4h"] > x["pdi_4h"])
    s -= SCORE_PENALTY_STRONG_DOWN * strong_down.astype(float)
    return s


def porteiro(f: Features, p: Params) -> np.ndarray:
    """Máscara de candidatas (filtro matemático da profit_gain, parametrizado)."""
    x = f.cols
    with np.errstate(invalid="ignore"):
        ok = x["min24"] <= -p.atr_mult * x["atr_pct"]
        ok &= (x["chg24"] >= p.chg24_min) & (x["chg24"] <= p.chg24_max)
        if p.bb_touch:
            t15, t1h = f.touches(p.bb_std)
            ok &= t15 | t1h
        ok &= x["vol_pct"] >= p.vol_min_pct
        ok &= x["ema21_dist"] < p.ema_dist_max
        if p.gate_sma200 in ("asset", "both"):
            ok &= x["above_sma200"] > 0
        if p.gate_sma200 in ("btc", "both"):
            ok &= x["btc_above_sma200"] > 0
        if p.gate_adx4h is not None:
            ok &= ~((x["adx_4h"] > p.gate_adx4h) & (x["mdi_4h"] > x["pdi_4h"]))
        if p.require_rsi2_turn:
            ok &= (x["rsi2_15m_prev"] < p.rsi2_level) & (x["rsi2_15m"] > x["rsi2_15m_prev"])
        ok &= np.isfinite(x["atr_pct"]) & np.isfinite(x["chg24"])
    return ok


def entry_mask(f: Features, p: Params) -> np.ndarray:
    """Porteiro + (opcional) confirmação: entra na vela k se houve sinal do
    Porteiro em alguma das ``confirm_bars`` velas anteriores e a vela k fechou
    acima da máxima da anterior (break_high) ou acima da EMA9 15m."""
    base = porteiro(f, p)
    if p.confirm == "none":
        return base
    recent = pd.Series(base.astype(float)).shift(1).rolling(p.confirm_bars, min_periods=1).max()
    recent = recent.fillna(0).to_numpy() > 0
    x = f.cols
    with np.errstate(invalid="ignore"):
        if p.confirm == "break_high":
            cond = f.c > x["prev_high_15m"]
        elif p.confirm == "above_ema9":
            cond = f.c > x["ema9_15m"]
        else:
            raise ValueError(p.confirm)
        ok = recent & cond
        if p.gate_sma200 in ("asset", "both"):
            ok &= x["above_sma200"] > 0
        if p.gate_sma200 in ("btc", "both"):
            ok &= x["btc_above_sma200"] > 0
    return ok & np.isfinite(x["atr_pct"])


def stop_pct(f: Features, p: Params) -> np.ndarray:
    if p.stop_mode == "fixed":
        return np.full(len(f.c), float(p.stop_fixed_pct))
    raw = f.cols["atr_pct"] * p.stop_mult
    lo, hi = (p.btc_stop_lo, p.btc_stop_hi) if f.is_btc else (p.stop_lo, p.stop_hi)
    return np.clip(np.nan_to_num(raw, nan=hi), lo, hi)


# ================================================================= saída
def simulate_position(f: Features, i: int, sl_pct: float, p: Params, start: Optional[int] = None,
                      ref: Optional[float] = None, fill_bar_stop_only: bool = False):
    """Simula a posição decidida na vela ``i``.

    Mercado: entrada no open de ``i+1``; gatilhos relativos ao close[i] (como o
    live). Limit: ``start`` = vela do fill, ``ref`` = preço limite e, na vela do
    fill, só o stop é checado (pior caso: a mínima que executou a compra pode
    ter batido o stop; e a alta da vela do fill é ignorada).

    Retorna (pernas, mae_pct); cada perna é (fração, j, preço_ref, motivo).
    """
    ot, O, H, L, C, AV = f.lists()
    n = len(C)
    if start is None:
        start = i + 1
    if ref is None:
        ref = C[i]
    use_disaster = p.disaster <= sl_pct
    be_level = ref * (1 + p.be_offset / 100)
    tp_level = None
    if p.exit_mode == "fixed":
        tp_level = ref * (1 + p.tp_pct / 100)
    elif p.exit_mode == "avwap":
        av = AV[i]
        cap = ref * (1 + p.tp_pct / 100)
        tgt = cap if not (av == av) else min(av, cap)
        tp_level = max(tgt, ref * (1 + p.tp_floor / 100))
    trail = p.exit_mode == "trail"
    act, drop = p.trail_act, p.trail_drop
    max_hold_ms = None if p.max_hold_h is None else p.max_hold_h * 3_600_000
    ts_ms = None if p.time_stop_h is None else p.time_stop_h * 3_600_000
    tp1 = ref * (1 + p.partial_tp / 100)
    entry_t = ot[start] if start < n else ot[n - 1]
    st = {
        "stop": ref * (1 - min(sl_pct, p.disaster) / 100),
        "reason": "STOP_DESASTRE" if use_disaster else "STOP_LOSS_DINAMICO",
        "rem": 1.0, "partial": p.partial_frac > 0, "peak": 0.0, "mae": 0.0,
    }
    legs = []

    def arm_be():
        if be_level > st["stop"]:
            st["stop"] = be_level
            st["reason"] = "BREAKEVEN"

    def new_peak(pk):
        if pk > st["peak"]:
            st["peak"] = pk
            if p.be_trigger is not None and pk >= p.be_trigger:
                arm_be()

    def do_partial(j, px):
        legs.append((p.partial_frac, j, px, "PARCIAL"))
        st["rem"] -= p.partial_frac
        st["partial"] = False
        if p.be_after_partial:
            arm_be()

    def done(j, px, reason):
        legs.append((st["rem"], j, px, reason))
        return legs, st["mae"]

    def mae_at(px):
        st["mae"] = min(st["mae"], (px - ref) / ref * 100)

    j0 = start
    if fill_bar_stop_only and start < n:
        if L[start] <= st["stop"]:
            mae_at(st["stop"])
            return done(start, st["stop"], st["reason"])
        mae_at(L[start])
        j0 = start + 1

    if p.check == "close":
        for j in range(j0, n):
            held = ot[j] + 900_000 - entry_t
            if max_hold_ms is not None and held >= max_hold_ms:
                mae_at(L[j])
                return done(j, C[j], "TIMEOUT")
            cj = C[j]
            pct = (cj - ref) / ref * 100
            mae_at(L[j])
            new_peak(pct)
            if pct <= -p.disaster:
                return done(j, cj, "STOP_DESASTRE")
            if cj <= st["stop"]:
                return done(j, cj, st["reason"])
            if trail and st["peak"] >= act and (st["peak"] - pct) >= drop:
                return done(j, cj, "TAKE_PROFIT")
            if tp_level is not None and cj >= tp_level:
                return done(j, cj, "TP_ALVO")
            if st["partial"] and cj >= tp1:
                do_partial(j, cj)
            if ts_ms is not None and held >= ts_ms and st["peak"] < p.time_stop_min_pct:
                return done(j, cj, "TIME_STOP")
        return done(n - 1, C[n - 1], "FIM_DADOS")

    for j in range(j0, n):
        o, h, lo, c = O[j], H[j], L[j], C[j]
        held = ot[j] - entry_t
        if max_hold_ms is not None and held >= max_hold_ms:
            return done(j, o, "TIMEOUT")
        if ts_ms is not None and held >= ts_ms and st["peak"] < p.time_stop_min_pct:
            return done(j, o, "TIME_STOP")
        if o <= st["stop"]:
            mae_at(o)
            return done(j, o, st["reason"])
        if lo <= st["stop"]:  # pior caso: stop vence qualquer alvo na mesma vela
            mae_at(st["stop"])
            return done(j, st["stop"], st["reason"])
        if trail and st["peak"] >= act:
            lvl = ref * (1 + (st["peak"] - drop) / 100)
            if o <= lvl:
                return done(j, o, "TAKE_PROFIT")
        if tp_level is not None and o >= tp_level:
            return done(j, o, "TP_ALVO")
        if st["partial"] and o >= tp1:
            do_partial(j, o)
        path = (lo, h, c) if c >= o else (h, lo, c)
        prev = o
        for px in path:
            if px > prev:
                if st["partial"] and px >= tp1:
                    do_partial(j, tp1)
                if tp_level is not None and px >= tp_level:
                    return done(j, tp_level, "TP_ALVO")
                new_peak((px - ref) / ref * 100)
            elif px < prev:
                mae_at(px)
                # na descida, o primeiro nível cruzado é o mais alto
                lvl, why = st["stop"], st["reason"]
                if trail and st["peak"] >= act:
                    tl = ref * (1 + (st["peak"] - drop) / 100)
                    if tl > lvl:
                        lvl, why = tl, "TAKE_PROFIT"
                if px <= lvl:
                    return done(j, min(lvl, prev), why)
            prev = px
    return done(n - 1, C[n - 1], "FIM_DADOS")


def simulate_exit(f: Features, i: int, sl_pct: float, p: Params):
    """Compatível com a sim-001: (j, preço médio de saída, motivo, mae)."""
    legs, mae = simulate_position(f, i, sl_pct, p)
    px = sum(fr * x for fr, _, x, _ in legs) / sum(fr for fr, _, _, _ in legs)
    return legs[-1][1], px, legs[-1][3], mae


# ============================================================ simulação
@dataclass
class Trade:
    symbol: str
    signal_ts: int
    entry_ts: int
    exit_ts: int
    entry_price: float
    exit_price: float
    ret_pct: float          # retorno líquido do trade (taxas+slippage), sobre o valor alocado
    gross_pct: float        # % vs preço do scan (o que o live soma no diário)
    equity_factor: float    # equity_depois / equity_antes
    mae_pct: float
    reason: str
    score: float
    stop_pct: float


def run(p: Params, feats: dict, start_ms: int, end_ms: int, initial: float = 1000.0) -> list:
    """Roda a estratégia sobre 1 (modo por moeda) ou N moedas (modo carteira:
    uma posição por vez, all-in, escolhendo a candidata de maior score)."""
    syms = list(feats)
    sig = {}
    for s in syms:
        f = feats[s]
        cand = entry_mask(f, p)
        win = (f.open_time >= start_ms) & (f.open_time < end_ms)
        cand &= win
        sig[s] = (cand, oracle_score(f, p), stop_pct(f, p))
    grid = np.unique(np.concatenate([feats[s].open_time[(feats[s].open_time >= start_ms)
                                                        & (feats[s].open_time < end_ms)] for s in syms]))
    if len(grid) == 0:
        return []
    G = len(grid)
    cand_g = np.zeros((len(syms), G), bool)
    score_g = np.full((len(syms), G), -np.inf)
    loc_g = np.full((len(syms), G), -1, np.int64)
    for k, s in enumerate(syms):
        f = feats[s]
        pos = np.searchsorted(grid, f.open_time)
        okp = (pos < G) & (pos >= 0)
        okp[okp] &= grid[pos[okp]] == f.open_time[okp]
        idx_local = np.flatnonzero(okp)
        cand_g[k, pos[idx_local]] = sig[s][0][idx_local]
        score_g[k, pos[idx_local]] = sig[s][1][idx_local]
        loc_g[k, pos[idx_local]] = idx_local
    any_idx = np.flatnonzero(cand_g.any(axis=0))
    day_of = (grid + MS["15m"] + DAY_OFFSET_MS) // MS["1d"]

    ex = MockExchange.with_balance(initial, fee_rate=p.fee, slippage=p.slippage)
    trades = []
    t = 0
    cur_day, d_trades, d_pct = None, 0, 0.0
    while True:
        kk = np.searchsorted(any_idx, t)
        if kk >= len(any_idx):
            break
        g = int(any_idx[kk])
        day = day_of[g]
        if day != cur_day:
            cur_day, d_trades, d_pct = day, 0, 0.0
        if d_trades >= p.max_daily_trades or d_pct >= p.daily_target_pct:
            t = int(np.searchsorted(day_of, day, side="right"))  # hiberna até meia-noite
            continue
        rows = np.flatnonzero(cand_g[:, g])
        best = rows[np.argmax(score_g[rows, g])]
        sc = score_g[best, g]
        if p.score_min is not None and sc < p.score_min:
            t = g + max(1, p.veto_cooldown_bars)  # veto → cooldown
            continue
        s = syms[best]
        f = feats[s]
        i = int(loc_g[best, g])
        if i + 1 >= len(f.c):
            break
        sl = float(sig[s][2][i])
        eq0 = ex.balance(ex.quote_asset)
        if p.entry_type == "limit":
            lim = f.c[i] * (1 - p.limit_offset_pct / 100)
            need = lim * (1 - p.limit_through_pct / 100)
            last = min(i + 1 + p.limit_bars, len(f.c))
            e = next((k for k in range(i + 1, last) if f.l[k] <= need), None)
            if e is None:  # não executou: ordem cancelada, volta a escanear
                t = g + p.limit_bars + 1
                continue
            legs, mae = simulate_position(f, i, sl, p, start=e, ref=lim, fill_bar_stop_only=True)
            buy = ex.limit_buy_quote(s, eq0 * 0.99, lim, int(f.open_time[e]), reason="ENTRADA_LIMIT")
            ref_scan = lim
        else:
            legs, mae = simulate_position(f, i, sl, p)
            buy = ex.buy_all_in(s, f.o[i + 1], int(f.open_time[i + 1]), reason="ENTRADA")
            ref_scan = f.c[i]
        base_asset = s[: -len(ex.quote_asset)]
        qty = ex.balance(base_asset)
        proceeds, sold = 0.0, 0.0
        for k_leg, (fr, jl, px_l, why) in enumerate(legs):
            q = ex.balance(base_asset) if k_leg == len(legs) - 1 else qty * fr
            sell = ex.market_sell_qty(s, q, px_l, int(f.open_time[jl]), reason=why)
            proceeds += sell.quote - sell.fee
            sold += q
        j, reason = legs[-1][1], legs[-1][3]
        if len(legs) > 1:
            reason = "PARCIAL+" + reason
        px_out = sum(fr * x for fr, _, x, _ in legs) / sum(fr for fr, _, _, _ in legs)
        eq1 = ex.balance(ex.quote_asset)
        net = proceeds / buy.quote - 1
        gross = (px_out - ref_scan) / ref_scan * 100
        trades.append(Trade(s, int(f.open_time[i]), int(buy.ts), int(f.open_time[j]),
                            buy.price, px_out * (1 - p.slippage), net * 100, gross, eq1 / eq0, mae,
                            reason, float(sc), sl))
        # contadores diários contam no dia da venda (como o live)
        gx = int(np.searchsorted(grid, f.open_time[j]))
        exit_day = day_of[min(gx, G - 1)]
        if exit_day != cur_day:
            cur_day, d_trades, d_pct = exit_day, 0, 0.0
        d_trades += 1
        d_pct += gross
        t = gx + 1
        if reason == "FIM_DADOS":
            break
    return trades


# ============================================================== métricas
def metrics(trades: list, years: Optional[float] = None) -> dict:
    n = len(trades)
    if n == 0:
        return {"n": 0, "win_rate": np.nan, "ret_total_pct": 0.0, "expectancy_pct": np.nan,
                "profit_factor": np.nan, "max_dd_pct": 0.0, "avg_hold_h": np.nan, "sqn": np.nan,
                "pct_stop": np.nan, "pct_trail": np.nan, "pct_tp": np.nan, "pct_timeout": np.nan}
    r = np.array([t.ret_pct for t in trades])
    eq, peak, dd = 1.0, 1.0, 0.0
    for t in trades:
        trough = eq * (1 + 0.99 * t.mae_pct / 100)
        dd = max(dd, 1 - trough / peak)
        eq *= t.equity_factor
        peak = max(peak, eq)
        dd = max(dd, 1 - eq / peak)
    wins, losses = r[r > 0].sum(), -r[r <= 0].sum()
    reasons = [t.reason for t in trades]
    hold = np.mean([(t.exit_ts - t.entry_ts) / 3_600_000 for t in trades])
    sd = r.std(ddof=1) if n > 1 else np.nan
    out = {
        "n": n,
        "win_rate": float((r > 0).mean() * 100),
        "ret_total_pct": float((eq - 1) * 100),
        "expectancy_pct": float(r.mean()),
        "profit_factor": float(wins / losses) if losses > 0 else np.inf,
        "max_dd_pct": float(dd * 100),
        "avg_hold_h": float(hold),
        "sqn": float(r.mean() / sd * np.sqrt(min(n, 100))) if sd and sd > 0 else np.nan,
        "pct_stop": 100 * sum(x.startswith("STOP") for x in reasons) / n,
        "pct_trail": 100 * sum(x == "TAKE_PROFIT" for x in reasons) / n,
        "pct_tp": 100 * sum(x == "TP_ALVO" for x in reasons) / n,
        "pct_timeout": 100 * sum(x in ("TIMEOUT", "FIM_DADOS") for x in reasons) / n,
    }
    if years:
        out["trades_per_month"] = n / (years * 12)
    return out


def params_dict(p: Params) -> dict:
    return asdict(p)
