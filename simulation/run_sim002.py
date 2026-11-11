"""sim-002 — variações ESTRUTURAIS de saída/entrada/custos (T-024).

Todas as variações têm o gate SMA200 diária do ativo ligado (novo default do
live). Referência = REF (configuração atual + SMA200).

    python -m simulation.run_sim002

Saídas: simulation/reports/sim-002-grid.csv, sim-002-por-moeda.csv,
sim-002-params.json, sim-002-robustez.csv. Mesma metodologia da sim-001
(IS 70% / OOS 30%, seleção só no IS; checagens de latência e custos).
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict

import pandas as pd

from simulation import data as D
from simulation.engine import BASELINE
from simulation.run_grid import (REPORTS, SIM_END, SIM_START, evaluate, iso, load_features, ms,
                                 score_is, track)

REF = BASELINE.with_(name="REF", gate_sma200="asset")


def variations() -> list:
    v = [REF]

    def add(name, **kw):
        v.append(REF.with_(name=name, **kw))

    # --- A. R:R explícito: stop fixo apertado × trailing maior
    for sl in (1.5, 2.0, 3.0):
        for a, d in ((2.0, 0.5), (3.0, 1.0), (5.0, 1.5)):
            add(f"A:sl{sl}+tr{a}/{d}", stop_mode="fixed", stop_fixed_pct=sl, trail_act=a, trail_drop=d)
        add(f"A:sl{sl}+tr1.5/0.3", stop_mode="fixed", stop_fixed_pct=sl)
    # stop ATR apertado (clamp 1,5–3%)
    for m in (1.5, 2.0):
        for a, d in ((2.0, 0.5), (3.0, 1.0)):
            add(f"A:atr{m}[1.5-3]+tr{a}/{d}", stop_mult=m, stop_lo=1.5, stop_hi=3.0,
                btc_stop_lo=1.5, btc_stop_hi=3.0, trail_act=a, trail_drop=d)
    # trailing maior com o stop atual
    for a, d in ((2.0, 0.5), (3.0, 1.0), (4.0, 1.0), (5.0, 1.5)):
        add(f"A:tr{a}/{d}", trail_act=a, trail_drop=d)
    # alvo fixo com R:R
    for sl, tp in ((1.5, 3.0), (2.0, 3.0), (2.0, 4.0), (3.0, 6.0)):
        add(f"A:sl{sl}+tp{tp}", stop_mode="fixed", stop_fixed_pct=sl, exit_mode="fixed", tp_pct=tp)
    # --- B. breakeven
    for be in (1.0, 1.5):
        add(f"B:be{be}", be_trigger=be)
    add("B:sl2+tr3/1+be1.5", stop_mode="fixed", stop_fixed_pct=2.0, trail_act=3.0, trail_drop=1.0, be_trigger=1.5)
    add("B:sl3+tr2/0.5+be1", stop_mode="fixed", stop_fixed_pct=3.0, trail_act=2.0, trail_drop=0.5, be_trigger=1.0)
    add("B:tr3/1+be1", trail_act=3.0, trail_drop=1.0, be_trigger=1.0)
    # --- C. saída parcial (50% no alvo 1, resto em trailing)
    for tp1 in (1.5, 2.0):
        add(f"C:p50@{tp1}+tr3/1", partial_frac=0.5, partial_tp=tp1, trail_act=3.0, trail_drop=1.0)
    add("C:p50@1.5+tr3/1+beP", partial_frac=0.5, partial_tp=1.5, trail_act=3.0, trail_drop=1.0, be_after_partial=True)
    add("C:p50@2+tr4/1+beP", partial_frac=0.5, partial_tp=2.0, trail_act=4.0, trail_drop=1.0, be_after_partial=True)
    add("C:sl2+p50@2+tr4/1+beP", stop_mode="fixed", stop_fixed_pct=2.0, partial_frac=0.5, partial_tp=2.0,
        trail_act=4.0, trail_drop=1.0, be_after_partial=True)
    # --- D. time-stop curto (sai se não andou)
    for h in (6.0, 12.0, 24.0):
        add(f"D:ts{h:g}h", time_stop_h=h, time_stop_min_pct=0.5)
    add("D:sl2+tr3/1+ts12h", stop_mode="fixed", stop_fixed_pct=2.0, trail_act=3.0, trail_drop=1.0, time_stop_h=12.0)
    # --- E. entrada com confirmação
    for n in (2, 4, 8):
        add(f"E:brk{n}", confirm="break_high", confirm_bars=n)
    for n in (4, 8):
        add(f"E:ema9_{n}", confirm="above_ema9", confirm_bars=n)
    add("E:brk4+sl2+tr3/1", confirm="break_high", confirm_bars=4, stop_mode="fixed", stop_fixed_pct=2.0,
        trail_act=3.0, trail_drop=1.0)
    add("E:brk4+p50@1.5+tr3/1+beP", confirm="break_high", confirm_bars=4, partial_frac=0.5, partial_tp=1.5,
        trail_act=3.0, trail_drop=1.0, be_after_partial=True)
    # --- F. custos / execução
    add("F:fee0.075", fee=0.00075)
    add("F:slip0.2", slippage=0.002)
    for off, nb in ((0.0, 2), (0.3, 2), (0.3, 4), (0.6, 4)):
        add(f"F:limit-{off}%x{nb}", entry_type="limit", limit_offset_pct=off, limit_bars=nb)
    add("F:limit-0.3%x4+fee0.075", entry_type="limit", limit_offset_pct=0.3, limit_bars=4, fee=0.00075)
    return v


def combos(ranked: pd.DataFrame, lookup: dict) -> list:
    """Estágio 2: melhores do IS por grupo (saída A–D, entrada E, execução F)."""
    r = ranked.set_index("variation").score_is
    ref = r["REF"]
    def best(prefixes, k):
        rows = r[[any(n.startswith(px) for px in prefixes) for n in r.index]]
        rows = rows[rows > ref].sort_values(ascending=False)
        return list(rows.index[:k])
    ex_, en_, co_ = best(["A:", "B:", "C:", "D:"], 3), best(["E:"], 2), best(["F:limit"], 1)
    out = []
    for x in ex_ or [None]:  # sem vencedora de saída → combina entrada × execução
        for e in en_ + [None]:
            for c in co_ + [None]:
                names = [n for n in (x, e, c) if n]
                if len(names) < 2:
                    continue
                kw = {}
                for nm in names:
                    for k, val in asdict(lookup[nm]).items():
                        if k != "name" and val != getattr(REF, k):
                            kw[k] = val
                out.append(REF.with_(name="S2:" + "+".join(names), **kw))
    return out, {"saida": ex_, "entrada": en_, "execucao": co_}


def main():
    t0 = time.time()
    feats = load_features(D.DEFAULT_SYMBOLS)
    start_ms, end_ms = ms(SIM_START), ms(SIM_END)
    split_ms = int(start_ms + (end_ms - start_ms) * 0.70)
    yr = lambda a, b: (b - a) / (365.25 * 86_400_000)
    years = {"IS": yr(start_ms, split_ms), "OOS": yr(split_ms, end_ms), "ALL": yr(start_ms, end_ms)}
    print(f"features {time.time() - t0:.0f}s | IS {SIM_START}→{iso(split_ms)} | OOS →{SIM_END}", flush=True)
    rows, coin_rows = [], []

    def run_list(vlist, label):
        for k, p in enumerate(vlist, 1):
            r, cr, _ = evaluate(p, feats, split_ms, start_ms, end_ms, years)
            for x in r:
                x["stage"] = label
            rows.extend(r)
            coin_rows.extend(cr)
            if k % 5 == 0 or k == len(vlist):
                msg = f"sim-002 {label}: variação {k}/{len(vlist)} ({time.time() - t0:.0f}s)"
                print(msg, flush=True)
                track("agent", "ag-sim", "--task", "T-024", "--step", msg)

    v1 = variations()
    run_list(v1, "stage1")
    lookup = {p.name: p for p in v1}
    v2, best = combos(score_is(pd.DataFrame(rows)), lookup)
    print("melhores IS:", json.dumps(best, ensure_ascii=False), flush=True)
    run_list(v2, "stage2")
    lookup.update({p.name: p for p in v2})
    # robustez do top-6 por score IS + REF: latência, slippage 0,2%, taxa BNB
    ranked = score_is(pd.DataFrame(rows)).sort_values("score_is", ascending=False)
    top = [n for n in ranked.variation if n != "REF"][:6]
    chk = []
    for n in ["REF"] + top:
        p = lookup[n]
        chk += [p.with_(name=f"{n}@close", check="close"), p.with_(name=f"{n}@slip0.2", slippage=0.002),
                p.with_(name=f"{n}@close+slip0.2", check="close", slippage=0.002),
                p.with_(name=f"{n}@fee0.075", fee=0.00075)]
    run_list(chk, "check")
    df = pd.DataFrame(rows).merge(score_is(pd.DataFrame(rows)), on="variation", how="left")
    df.to_csv(os.path.join(REPORTS, "sim-002-grid.csv"), index=False, float_format="%.4f")
    pd.DataFrame(coin_rows).to_csv(os.path.join(REPORTS, "sim-002-por-moeda.csv"), index=False,
                                   float_format="%.4f")
    allp = v1 + v2 + chk
    with open(os.path.join(REPORTS, "sim-002-params.json"), "w", encoding="utf-8") as fh:
        json.dump({p.name: asdict(p) for p in allp}, fh, indent=1, ensure_ascii=False)
    # tabela de robustez: expectância por condição
    rob = []
    for n in ["REF"] + top:
        row = {"variation": n, "score_is": float(ranked.set_index("variation").score_is.get(n, float("nan")))}
        for suf in ["", "@close", "@slip0.2", "@close+slip0.2", "@fee0.075"]:
            for mode in ("portfolio", "per_coin"):
                for seg in ("IS", "OOS"):
                    x = df[(df.variation == n + suf) & (df["mode"] == mode) & (df.segment == seg)]
                    tag = f"{mode[:4]}_{seg}{suf}"
                    row[f"exp_{tag}"] = float(x.expectancy_pct.iloc[0]) if len(x) else float("nan")
                    row[f"n_{tag}"] = int(x.n.iloc[0]) if len(x) else 0
                    if mode == "portfolio":
                        row[f"ret_{tag}"] = float(x.ret_total_pct.iloc[0]) if len(x) else float("nan")
        rob.append(row)
    pd.DataFrame(rob).to_csv(os.path.join(REPORTS, "sim-002-robustez.csv"), index=False, float_format="%.4f")
    print(f"ok: {df.variation.nunique()} variações em {time.time() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
