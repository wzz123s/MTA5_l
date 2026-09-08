# -*- coding: utf-8 -*-
"""
stage2_params.py —— 阶段2 轻量参数收敛扫描

黄金：break 退出；原油：hybrid 退出
参数：glue_thresh {0.001,0.003,0.005,0.01} / bias_floor {0,0.5,1.0} / time_exit {120,240}
评估：IS / OOS / ALL 的 n、EV_R、PF_R、年正收益
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "阶段1_机会层统计" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage1_common as C
import stage2_backtest as B2

PROC = Path(__file__).resolve().parent.parent / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)


def run_config(sym, long_only, costs, spec, eff, is_end, exit_mode, time_exit,
               glue, bias):
    d1 = C.analyze_tf(sym, "D1")
    h4 = C.analyze_tf(sym, "H4")
    cr = C.find_cross13_55(d1)
    cr = cr[pd.to_datetime(cr["time"]) >= eff].reset_index(drop=True)
    spread, swap = costs
    wins = {
        "IS": (eff.strftime("%Y-%m-%d"), is_end.strftime("%Y-%m-%d")),
        "OOS": ((is_end + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), None),
        "ALL": (eff.strftime("%Y-%m-%d"), None),
    }
    res = {}
    for k, (s, e) in wins.items():
        tr = B2.fullchain_backtest(d1, h4, cr, sym, "D1", "H4",
                                   glue_thresh=glue, bias_floor=bias,
                                   stop_mode="sub_struct", stop_spec=spec,
                                   exit_mode=exit_mode, time_exit_bars=time_exit,
                                   long_only=long_only,
                                   spread_price=spread, swap_per_bar=swap,
                                   start=s, end=e)
        res[k] = B2.summary(tr, f"{sym} g{glue} b{bias} t{time_exit} {k}")
    return res


def main():
    rows = []
    print("== 黄金 break 参数扫描 ==")
    for glue in (0.001, 0.003, 0.005, 0.01):
        for bias in (0.0, 0.5, 1.0):
            for te in (120, 240):
                res = run_config("XAUUSDm", True, (0.10, 0.002), ("pct", 0.003, 0.02),
                                 pd.Timestamp("2017-03-01"), pd.Timestamp("2022-12-31"),
                                 "break", te, glue, bias)
                s, si, so = res["ALL"], res["IS"], res["OOS"]
                rows.append({"symbol": "XAUUSDm", "exit": "break", "glue": glue, "bias": bias,
                             "te": te, "n": s["n"], "EV_R": s["EV_R"], "PF_R": s["PF_R"],
                             "ann": s["ann_pos"], "PF_IS": si["PF_R"], "PF_OOS": so["PF_R"]})
    print("  完成 24 组")

    print("== 原油 hybrid 参数扫描 ==")
    for glue in (0.001, 0.003, 0.005, 0.01):
        for bias in (0.0, 0.5, 1.0):
            for te in (120, 240):
                res = run_config("USOILm", False, (0.03, 0.0005), ("pct", 0.008, 0.025),
                                 pd.Timestamp("2021-07-01"), pd.Timestamp("2023-12-31"),
                                 "hybrid", te, glue, bias)
                s, si, so = res["ALL"], res["IS"], res["OOS"]
                rows.append({"symbol": "USOILm", "exit": "hybrid", "glue": glue, "bias": bias,
                             "te": te, "n": s["n"], "EV_R": s["EV_R"], "PF_R": s["PF_R"],
                             "ann": s["ann_pos"], "PF_IS": si["PF_R"], "PF_OOS": so["PF_R"]})
    print("  完成 24 组")

    df = pd.DataFrame(rows)
    df.to_csv(PROC / "S2_参数扫描.csv", index=False, encoding="utf-8-sig")

    # 汇总：每品种 TOP5（按 ALL PF_R 降序，n≥5）
    lines = ["# 阶段2 轻量参数收敛扫描", ""]
    for sym in ["XAUUSDm", "USOILm"]:
        sub = df[df["symbol"] == sym].sort_values("PF_R", ascending=False).head(5)
        lines += [f"## {sym} TOP5（ALL PF_R）", "",
                  "| 退出 | glue | bias | te | n | ALL EV_R | ALL PF_R | ALL年正 | IS PF | OOS PF |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in sub.iterrows():
            lines.append(f"| {r['exit']} | {r['glue']} | {r['bias']} | {r['te']} | {r['n']} "
                         f"| {r['EV_R']} | {r['PF_R']} | {r['ann']}% | {r['PF_IS']} | {r['PF_OOS']} |")
        lines.append("")
    (PROC / "S2_参数扫描汇总.md").write_text("\n".join(lines), encoding="utf-8")
    print("  已保存 S2_参数扫描.csv / S2_参数扫描汇总.md")


if __name__ == "__main__":
    main()
