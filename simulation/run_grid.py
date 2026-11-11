"""Grade de calibração da profit_gain (épico E2 / T-022).

Uso:
    python -m simulation.run_grid                 # grade completa (estágio 1 + 2)
    python -m simulation.run_grid --quick         # só BASE em 3 moedas (smoke)

Saídas em simulation/reports/:
    sim-001-grid.csv          métricas por variação × modo × segmento (IS/OOS/ALL)
    sim-001-por-moeda.csv     métricas por variação × moeda × segmento
    sim-001-trades-<var>.csv  trades da baseline e da recomendada

Metodologia: split temporal — IS (calibração) = primeiros 70% do período,
OOS (validação) = 30% finais. A seleção usa SÓ o IS; o OOS é reportado.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from simulation import data as D
from simulation import engine as E
from simulation.engine import BASELINE, Params

ROOT = D.ROOT
REPORTS = os.path.join(os.path.dirname(__file__), "reports")
SIM_START = "2024-07-15"   # 2 semanas de aquecimento dos indicadores
SIM_END = "2026-11-01"
IS_FRACTION = 0.70
MIN_TRADES_IS = 30         # abaixo disso a variação é penalizada


def ms(d: str) -> int:
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def iso(t: int) -> str:
    return datetime.fromtimestamp(t / 1000, timezone.utc).strftime("%Y-%m-%d")


def load_features(symbols) -> dict:
    btc_d = D.load("BTCUSDT", "1d")
    feats = {}
    for s in symbols:
        try:
            feats[s] = E.build_features(s, D.load(s, "15m"), D.load(s, "1h"), D.load(s, "4h"),
                                        D.load(s, "1d"), btc_d)
        except FileNotFoundError:
            print(f"[aviso] sem dados para {s}; ignorado", flush=True)
    return feats


def track(*args):
    """Heartbeat no devpanel (best effort; nunca derruba a grade)."""
    try:
        subprocess.run([sys.executable, os.path.join(ROOT, "devpanel", "track.py"), *args],
                       cwd=ROOT, timeout=30, capture_output=True)
    except Exception:
        pass


# ------------------------------------------------------------------ grade
def stage1() -> list:
    B = BASELINE
    v = [B]
    add = lambda name, **kw: v.append(B.with_(name=name, **kw))
    # --- Porteiro
    for x in (1.0, 1.5, 2.5, 3.0):
        add(f"atr_mult={x}", atr_mult=x)
    for x in (1.5, 1.8, 2.2, 2.5):
        add(f"bb_std={x}", bb_std=x)
    for x in (0.0, 50.0, 120.0, 150.0):
        add(f"vol_min={x:g}", vol_min_pct=x)
    for x in (-0.5, -2.0, -3.0):
        add(f"ema_dist<{x}", ema_dist_max=x)
    for g in ("asset", "btc", "both"):
        add(f"sma200={g}", gate_sma200=g)
    for x in (25.0, 30.0, 40.0):
        add(f"adx4h_veto>{x:g}", gate_adx4h=x)
    add("rsi2_turn<10", require_rsi2_turn=True, rsi2_level=10.0)
    add("rsi2_turn<20", require_rsi2_turn=True, rsi2_level=20.0)
    for x in (2, 3, 4, 5, 6, 7):
        add(f"score>={x}", score_min=float(x))
    add("sem_limite_diario", max_daily_trades=99, daily_target_pct=999.0)
    # --- Stopwin
    for x in (0.8, 1.0, 2.0, 2.5, 3.0):
        add(f"trail_act={x}", trail_act=x)
    for x in (0.2, 0.5, 0.75, 1.0):
        add(f"trail_drop={x}", trail_drop=x)
    for a, d in ((1.0, 0.5), (1.2, 0.4), (2.0, 0.5), (2.0, 1.0), (3.0, 1.0), (4.0, 1.5)):
        add(f"trail={a}/{d}", trail_act=a, trail_drop=d)
    for x in (1.0, 1.5, 2.0, 3.0):
        add(f"tp_fixo={x}", exit_mode="fixed", tp_pct=x)
    for x in (2.0, 3.0):
        add(f"tp_avwap<={x}", exit_mode="avwap", tp_pct=x)
    # --- Stoploss
    for x in (2.0, 3.0, 5.0, 6.0):
        add(f"stop_mult={x}", stop_mult=x)
    for lo, hi in ((2.0, 5.0), (3.0, 5.0), (5.0, 10.0), (4.0, 12.0)):
        add(f"clamp_alt={lo}-{hi}", stop_lo=lo, stop_hi=hi)
    add("clamp_btc=3-6", btc_stop_lo=3.0, btc_stop_hi=6.0)
    for lo, hi in ((2.5, 6.0), (2.0, 4.0)):
        add(f"clamp_all={lo}-{hi}", stop_lo=lo, stop_hi=hi, btc_stop_lo=lo, btc_stop_hi=hi)
    add("clamp_all=2-4,mult=3", stop_lo=2.0, stop_hi=4.0, btc_stop_lo=2.0, btc_stop_hi=4.0, stop_mult=3.0)
    add("disaster=5", disaster=5.0)
    for x in (12.0, 24.0, 48.0, 72.0):
        add(f"max_hold={x:g}h", max_hold_h=x)
    return v


def stage2(ranked_s1: pd.DataFrame) -> list:
    """Combinações dos melhores ajustes do estágio 1 (escolhidos SÓ pelo IS)."""
    B = BASELINE
    v = []
    best = {}
    groups = {
        "entry": ["atr_mult", "bb_std", "vol_min", "ema_dist", "sma200", "adx4h", "rsi2", "score"],
        "win": ["trail", "tp_fixo", "tp_avwap"],
        "loss": ["stop_mult", "clamp", "disaster", "max_hold"],
    }
    s1 = ranked_s1.set_index("variation")
    base_score = s1.loc["BASE", "score_is"]
    for grp, prefixes in groups.items():
        rows = s1[[any(n.startswith(px) for px in prefixes) for n in s1.index]]
        rows = rows[rows.score_is > base_score].sort_values("score_is", ascending=False)
        best[grp] = list(rows.index[:3])
    lookup = {p.name: p for p in stage1()}

    def merge(names, label):
        kw = {}
        for nm in names:
            p = lookup[nm]
            for k, val in asdict(p).items():
                if k != "name" and val != getattr(B, k):
                    kw[k] = val
        v.append(B.with_(name=label, **kw))

    E_, W_, L_ = best["entry"] or [None], best["win"] or [None], best["loss"] or [None]
    seen = set()
    for e in E_:
        for w in W_:
            for lo in L_:
                names = [x for x in (e, w, lo) if x]
                key = tuple(names)
                if not names or key in seen:
                    continue
                seen.add(key)
                merge(names, "C:" + "+".join(names))
    # pares de filtros de entrada (os 3 melhores, 2 a 2) + melhor saída
    ent = best["entry"]
    for a in range(len(ent)):
        for b in range(a + 1, len(ent)):
            fa = {k for k, x in asdict(lookup[ent[a]]).items() if k != "name" and x != getattr(B, k)}
            fb = {k for k, x in asdict(lookup[ent[b]]).items() if k != "name" and x != getattr(B, k)}
            if fa & fb:  # mesmo parâmetro (ex.: score>=4 e score>=5) — não combina
                continue
            names = [ent[a], ent[b]] + ([W_[0]] if W_[0] else []) + ([L_[0]] if L_[0] else [])
            merge(names, "C:" + "+".join(names))
    return v, best


# --------------------------------------------------------------- execução
def evaluate(p: Params, feats: dict, split_ms: int, start_ms: int, end_ms: int, years: dict):
    rows, coin_rows, all_trades = [], [], {}
    seg = lambda tr: {"IS": [t for t in tr if t.entry_ts < split_ms],
                      "OOS": [t for t in tr if t.entry_ts >= split_ms], "ALL": tr}
    # modo carteira (fiel ao live: 1 posição por vez entre todas as moedas)
    port = E.run(p, feats, start_ms, end_ms)
    all_trades["portfolio"] = port
    for sname, tr in seg(port).items():
        rows.append({"variation": p.name, "mode": "portfolio", "segment": sname,
                     **E.metrics(tr, years[sname])})
    # modo por moeda (uma conta por moeda) → robustez entre perfis
    pooled = {"IS": [], "OOS": [], "ALL": []}
    for s, f in feats.items():
        tr = E.run(p, {s: f}, start_ms, end_ms)
        for sname, t2 in seg(tr).items():
            pooled[sname] += t2
            coin_rows.append({"variation": p.name, "symbol": s, "segment": sname,
                              **E.metrics(t2, years[sname])})
    for sname, tr in pooled.items():
        m = E.metrics(tr, years[sname])
        cr = [r for r in coin_rows if r["variation"] == p.name and r["segment"] == sname and r["n"] > 0]
        m["coins_positive"] = sum(r["ret_total_pct"] > 0 for r in cr)
        m["coins_traded"] = len(cr)
        m["median_coin_ret_pct"] = float(np.median([r["ret_total_pct"] for r in cr])) if cr else np.nan
        rows.append({"variation": p.name, "mode": "per_coin", "segment": sname, **m})
    return rows, coin_rows, all_trades


def score_is(df: pd.DataFrame) -> pd.DataFrame:
    """Score de seleção (só IS): expectância pooled por moeda × sqrt(n) / desvio,
    penalizada por poucos trades e por moedas negativas; exige carteira IS > 0
    para não ser rebaixada."""
    pc = df[(df["mode"] == "per_coin") & (df.segment == "IS")].set_index("variation")
    pf = df[(df["mode"] == "portfolio") & (df.segment == "IS")].set_index("variation")
    s = pc["sqn"].fillna(-9).copy()
    few = pc["n"] < MIN_TRADES_IS
    s[few] = s[few] * (pc["n"][few] / MIN_TRADES_IS) - 1
    frac_pos = pc["coins_positive"] / pc["coins_traded"].replace(0, np.nan)
    s = s + (frac_pos.fillna(0) - 0.5)
    s = s - (pf["ret_total_pct"] <= 0).astype(float) * 0.5
    out = pd.DataFrame({"variation": s.index, "score_is": s.values})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--symbols", nargs="*", default=D.DEFAULT_SYMBOLS)
    args = ap.parse_args(argv)
    os.makedirs(REPORTS, exist_ok=True)
    syms = args.symbols[:3] if args.quick else args.symbols
    t0 = time.time()
    feats = load_features(syms)
    start_ms, end_ms = ms(SIM_START), ms(SIM_END)
    split_ms = int(start_ms + (end_ms - start_ms) * IS_FRACTION)
    yr = lambda a, b: (b - a) / (365.25 * 86_400_000)
    years = {"IS": yr(start_ms, split_ms), "OOS": yr(split_ms, end_ms), "ALL": yr(start_ms, end_ms)}
    print(f"features: {len(feats)} moedas em {time.time() - t0:.1f}s | IS {SIM_START}→{iso(split_ms)} "
          f"| OOS {iso(split_ms)}→{SIM_END}", flush=True)

    variations = [BASELINE] if args.quick else stage1()
    rows, coin_rows = [], []
    keep_trades = {}

    def run_list(vlist, label):
        for k, p in enumerate(vlist, 1):
            r, cr, tr = evaluate(p, feats, split_ms, start_ms, end_ms, years)
            for x in r:
                x["stage"] = label
            rows.extend(r)
            coin_rows.extend(cr)
            if p.name == "BASE":
                keep_trades["BASE"] = tr["portfolio"]
            if k % 5 == 0 or k == len(vlist):
                msg = f"{label}: variação {k}/{len(vlist)} ({time.time() - t0:.0f}s)"
                print(msg, flush=True)
                track("agent", "ag-sim", "--task", "T-022", "--step", msg)

    run_list(variations, "stage1")
    df = pd.DataFrame(rows)
    if not args.quick:
        ranked = score_is(df)
        s2, best = stage2(ranked)
        print("melhores por grupo (IS):", json.dumps(best, ensure_ascii=False), flush=True)
        run_list(s2, "stage2")
        # variações de checagem: BASE e top-5 combinadas no modo 'close' (latência)
        df = pd.DataFrame(rows)
        ranked = score_is(df).sort_values("score_is", ascending=False)
        all_p = {p.name: p for p in stage1() + s2}
        top = [n for n in ranked.variation if n != "BASE"][:5]
        chk = [BASELINE.with_(name="BASE@close", check="close")]
        chk += [all_p[n].with_(name=f"{n}@close", check="close") for n in top]
        chk += [BASELINE.with_(name="BASE@slip0.2%", slippage=0.002)]
        chk += [all_p[n].with_(name=f"{n}@slip0.2%", slippage=0.002) for n in top]
        run_list(chk, "check")
        for n in top[:1]:
            r, cr, tr = evaluate(all_p[n], feats, split_ms, start_ms, end_ms, years)
            keep_trades[n] = tr["portfolio"]
    df = pd.DataFrame(rows)
    ranked = score_is(df)
    df = df.merge(ranked, on="variation", how="left")
    df.to_csv(os.path.join(REPORTS, "sim-001-grid.csv"), index=False, float_format="%.4f")
    pd.DataFrame(coin_rows).to_csv(os.path.join(REPORTS, "sim-001-por-moeda.csv"), index=False,
                                   float_format="%.4f")
    for name, tr in keep_trades.items():
        safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in name)[:80]
        pd.DataFrame([asdict(t) for t in tr]).to_csv(
            os.path.join(REPORTS, f"sim-001-trades-{safe}.csv"), index=False, float_format="%.6f")
    with open(os.path.join(REPORTS, "sim-001-params.json"), "w", encoding="utf-8") as fh:
        allp = stage1() + (s2 if not args.quick else [])
        json.dump({p.name: asdict(p) for p in allp}, fh, indent=1, ensure_ascii=False)
    print(f"ok: {df.variation.nunique()} variações em {time.time() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
