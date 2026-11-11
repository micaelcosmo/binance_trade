"""Testes do motor de simulação (dados sintéticos, sem rede)."""
import numpy as np
import pandas as pd
import pytest

from simulation import engine as E
from simulation.engine import Features, Params, simulate_exit

T0 = 1_700_000_000_000 - (1_700_000_000_000 % 86_400_000)  # meia-noite UTC


def synth_15m(n=4000, seed=1, drift=0.0, vol=0.004):
    rng = np.random.default_rng(seed)
    r = rng.normal(drift, vol, n)
    close = 100 * np.exp(np.cumsum(r))
    open_ = np.r_[100.0, close[:-1]]
    spread = np.abs(rng.normal(0, vol, n)) * close
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - spread
    volume = rng.uniform(50, 150, n)
    ot = T0 + np.arange(n) * 900_000
    return pd.DataFrame({"open_time": ot, "open": open_, "high": high, "low": low,
                         "close": close, "volume": volume, "close_time": ot + 899_999})


def resample(d15, ms):
    g = (d15.open_time - T0) // ms
    out = d15.groupby(g).agg(open_time=("open_time", "first"), open=("open", "first"),
                             high=("high", "max"), low=("low", "min"), close=("close", "last"),
                             volume=("volume", "sum")).reset_index(drop=True)
    out["open_time"] = T0 + ((out.open_time - T0) // ms) * ms
    return out


def make_feats(d15, sym="ETHUSDT"):
    return E.build_features(sym, d15, resample(d15, 3_600_000), resample(d15, 14_400_000),
                            resample(d15, 86_400_000))


def bars(rows, ref=100.0):
    """Features mínimas a partir de [(o,h,l,c), ...]; a barra 0 é o scan (close=ref)."""
    rows = [(ref, ref, ref, ref)] + rows
    a = np.array(rows, float)
    n = len(a)
    ot = T0 + np.arange(n) * 900_000
    return Features("ETHUSDT", ot, a[:, 0], a[:, 1], a[:, 2], a[:, 3],
                    {"avwap_1h": np.full(n, np.nan)})


# --------------------------------------------------------------- look-ahead
def test_no_lookahead_features_and_signals():
    d15 = synth_15m(3000, seed=7)
    full = make_feats(d15)
    k = 2000
    tampered = d15.copy()
    rng = np.random.default_rng(99)
    fut = tampered.index > k
    tampered.loc[fut, ["open", "high", "low", "close"]] *= rng.uniform(0.5, 1.5, (fut.sum(), 1))
    tampered.loc[fut, "high"] = tampered.loc[fut, ["open", "high", "low", "close"]].max(axis=1)
    tampered.loc[fut, "low"] = tampered.loc[fut, ["open", "high", "low", "close"]].min(axis=1)
    tampered.loc[fut, "volume"] *= 5
    part = make_feats(tampered)
    for name, arr in full.cols.items():
        np.testing.assert_array_equal(np.asarray(arr[: k + 1], float), np.asarray(part.cols[name][: k + 1], float),
                                      err_msg=f"look-ahead em {name}")
    p = Params(bb_std=1.5, vol_min_pct=50, atr_mult=0.5, ema_dist_max=0.0)
    np.testing.assert_array_equal(E.porteiro(full, p)[: k + 1], E.porteiro(part, p)[: k + 1])
    np.testing.assert_array_equal(E.oracle_score(full, p)[: k + 1], E.oracle_score(part, p)[: k + 1])


def test_higher_tf_uses_only_closed_candle():
    d15 = synth_15m(400, seed=3)
    f = make_feats(d15)
    # vela 15m que abre 01:30 decide às 01:45: a 1h das 01:00 ainda está aberta
    i = 6
    assert f.open_time[i] == T0 + 6 * 900_000
    assert f.d1h.open_time.iloc[f.idx1h[i]] == T0  # última 1h fechada = 00:00–01:00
    # na vela que abre 01:45 (decide 02:00) a 1h das 01:00 acabou de fechar
    assert f.d1h.open_time.iloc[f.idx1h[7]] == T0 + 3_600_000
    assert f.idx1h[0] == -1  # antes de fechar a primeira 1h não há valor


# ------------------------------------------------------------------- saídas
def test_stop_wins_when_stop_and_target_in_same_bar():
    f = bars([(100, 103, 90, 102)])  # bateu +3% e −10% na mesma vela
    j, px, reason, _ = simulate_exit(f, 0, 5.0, Params())
    assert reason == "STOP_LOSS_DINAMICO"
    assert px == pytest.approx(95.0)


def test_gap_below_stop_exits_at_open():
    f = bars([(100, 100.5, 99.5, 100), (90, 91, 89, 90)])
    j, px, reason, _ = simulate_exit(f, 0, 5.0, Params())
    assert (j, px, reason) == (2, 90, "STOP_LOSS_DINAMICO")


def test_trailing_sells_at_peak_minus_drop():
    # vela de baixa: O→H→L→C → sobe a +2% e devolve até +0,5%
    f = bars([(100, 102, 100.5, 100.6)])
    j, px, reason, _ = simulate_exit(f, 0, 5.0, Params(trail_act=1.5, trail_drop=0.3))
    assert reason == "TAKE_PROFIT"
    assert px == pytest.approx(101.7)


def test_trailing_not_armed_below_activation():
    f = bars([(100, 101.4, 100.2, 100.3), (100.3, 100.5, 94.0, 94.5)])
    j, px, reason, _ = simulate_exit(f, 0, 5.0, Params(trail_act=1.5))
    assert reason == "STOP_LOSS_DINAMICO" and j == 2


def test_close_mode_has_latency_and_exits_at_close():
    f = bars([(100, 100.2, 93.0, 94.0)])
    _, px_intra, _, _ = simulate_exit(f, 0, 5.0, Params(check="intrabar"))
    _, px_close, reason, _ = simulate_exit(f, 0, 5.0, Params(check="close"))
    assert px_intra == pytest.approx(95.0)
    assert px_close == pytest.approx(94.0) and reason == "STOP_LOSS_DINAMICO"


def test_disaster_used_when_tighter_than_stop():
    f = bars([(100, 100, 80, 82)])
    _, px, reason, _ = simulate_exit(f, 0, 20.0, Params(disaster=15.0))
    assert reason == "STOP_DESASTRE" and px == pytest.approx(85.0)


def test_fixed_take_profit_and_timeout():
    f = bars([(100, 101, 99.8, 100.9), (100.9, 102.5, 100.8, 102)])
    _, px, reason, _ = simulate_exit(f, 0, 5.0, Params(exit_mode="fixed", tp_pct=2.0))
    assert reason == "TP_ALVO" and px == pytest.approx(102.0)
    flat = bars([(100, 100.5, 99.5, 100)] * 20)
    j, _, reason, _ = simulate_exit(flat, 0, 5.0, Params(max_hold_h=2))
    assert reason == "TIMEOUT" and j == 9  # 8 velas de 15m após a entrada


# --------------------------------------------------------------- simulação
def test_run_respects_daily_limit_and_costs():
    d15 = synth_15m(6000, seed=11, vol=0.006)
    f = make_feats(d15)
    # Porteiro bem permissivo para gerar muitos sinais
    p = Params(atr_mult=0.0, bb_std=0.5, vol_min_pct=0, ema_dist_max=50, chg24_min=-99, chg24_max=99,
               trail_act=0.5, trail_drop=0.2, max_daily_trades=2, daily_target_pct=999)
    trades = E.run(p, {"ETHUSDT": f}, int(f.open_time[200]), int(f.open_time[-1]))
    assert len(trades) > 10
    days = pd.Series([(t.exit_ts + 900_000 + E.DAY_OFFSET_MS) // 86_400_000 for t in trades]).value_counts()
    assert days.max() <= 2
    for t in trades:
        assert t.entry_ts > t.signal_ts                       # executa na vela seguinte
        assert t.exit_ts >= t.entry_ts
        # custo: retorno líquido < movimento bruto entre fills
        assert t.ret_pct < (t.exit_price / t.entry_price - 1) * 100 + 1e-9
    m = E.metrics(trades)
    assert m["n"] == len(trades) and 0 <= m["win_rate"] <= 100


def test_portfolio_mode_single_position_at_a_time():
    fa = make_feats(synth_15m(3000, seed=21, vol=0.006), "AAAUSDT")
    fb = make_feats(synth_15m(3000, seed=22, vol=0.006), "BBBUSDT")
    p = Params(atr_mult=0.0, bb_std=0.5, vol_min_pct=0, ema_dist_max=50, chg24_min=-99, chg24_max=99,
               max_daily_trades=99, daily_target_pct=999)
    trades = E.run(p, {"AAAUSDT": fa, "BBBUSDT": fb}, int(fa.open_time[200]), int(fa.open_time[-1]))
    assert len({t.symbol for t in trades}) == 2
    for a, b in zip(trades, trades[1:]):
        assert b.entry_ts > a.exit_ts  # nunca duas posições abertas
