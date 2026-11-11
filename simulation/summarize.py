"""Gera tabelas markdown a partir dos CSVs da grade (apoio ao relatório).

    python -m simulation.summarize [variação ...]
"""
from __future__ import annotations

import os
import sys

import pandas as pd

REPORTS = os.path.join(os.path.dirname(__file__), "reports")
COLS = ["n", "win_rate", "ret_total_pct", "expectancy_pct", "profit_factor", "max_dd_pct",
        "avg_hold_h", "pct_stop", "pct_trail", "pct_tp", "pct_timeout"]


def load():
    g = pd.read_csv(os.path.join(REPORTS, "sim-001-grid.csv"))
    c = pd.read_csv(os.path.join(REPORTS, "sim-001-por-moeda.csv"))
    return g, c


def wide(g, mode):
    x = g[g["mode"] == mode].pivot_table(index="variation", columns="segment",
                                         values=["n", "expectancy_pct", "ret_total_pct", "win_rate",
                                                 "profit_factor", "max_dd_pct"], aggfunc="first")
    x.columns = [f"{a}_{b}" for a, b in x.columns]
    sc = g.drop_duplicates("variation").set_index("variation")["score_is"]
    return x.join(sc)


def md(df, floatfmt=2):
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            df[c] = df[c].map(lambda v: "" if pd.isna(v) else f"{v:.{floatfmt}f}")
    head = "| " + " | ".join([df.index.name or ""] + list(map(str, df.columns))) + " |"
    sep = "|" + "---|" * (len(df.columns) + 1)
    rows = ["| " + " | ".join([str(i)] + list(map(str, r))) + " |" for i, r in zip(df.index, df.values)]
    return "\n".join([head, sep] + rows)


def main(argv):
    g, c = load()
    pc = wide(g, "per_coin")
    pf = wide(g, "portfolio")
    pc = pc.sort_values("score_is", ascending=False)
    cols = ["score_is", "n_IS", "expectancy_pct_IS", "win_rate_IS", "profit_factor_IS",
            "n_OOS", "expectancy_pct_OOS", "win_rate_OOS", "profit_factor_OOS"]
    print("## por moeda (pooled), ordenado por score IS\n")
    print(md(pc[cols]))
    print("\n## carteira\n")
    print(md(pf.loc[pc.index, ["n_IS", "ret_total_pct_IS", "max_dd_pct_IS", "expectancy_pct_IS",
                               "n_OOS", "ret_total_pct_OOS", "max_dd_pct_OOS", "expectancy_pct_OOS"]]))
    for v in argv:
        print(f"\n## {v} por moeda\n")
        x = c[c.variation == v].pivot_table(index="symbol", columns="segment",
                                            values=["n", "expectancy_pct", "ret_total_pct"], aggfunc="first")
        x.columns = [f"{a}_{b}" for a, b in x.columns]
        print(md(x))


if __name__ == "__main__":
    main(sys.argv[1:])
