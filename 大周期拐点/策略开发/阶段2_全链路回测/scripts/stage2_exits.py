# -*- coding: utf-8 -*-
"""
stage2_exits.py —— 阶段2 退出变体对比 + 轻量参数收敛

对比：tp(1.5R/3R) / break(反向穿越全出) / trail(高取低移动止损) / hybrid(1.5R后移动)
参数：time_exit {120, 240}；gold 止损带 {0.3-2.0%, 0.2-3.0%}
评估：IS/OOS/ALL 的 n / EV_R / PF_R / 年正收益
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


def run_config(sym, long_only, costs, spec, eff, is_end, exit_mode, time_exit):
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
                                   glue_thresh=0.003, bias_floor=0.0,
                                   stop_mode="sub_struct", stop_spec=spec,
                                   exit_mode=exit_mode, time_exit_bars=time_exit,
                                   long_only=long_only,
                                   spread_price=spread, swap_per_bar=swap,
                                   start=s, end=e)
        res[k] = B2.summary(tr, f"{sym} {exit_mode} t{time_exit} {k}")
    return res


def main():
    lines = ["# 阶段2 退出变体对比与参数收敛", ""]
    rows = []

    configs = [
        # (品种, long_only, costs, spec, eff, is_end, label)
        ("XAUUSDm", True, (0.10, 0.002), ("pct", 0.003, 0.02),
         pd.Timestamp("2017-03-01"), pd.Timestamp("2022-12-31"), "gold"),
        ("USOILm", False, (0.03, 0.0005), ("pct", 0.008, 0.025),
         pd.Timestamp("2021-07-01"), pd.Timestamp("2023-12-31"), "oil"),
    ]
    exit_modes = ["tp", "break", "trail", "hybrid"]
    time_exits = [120, 240]

    for sym, long_only, costs, spec, eff, is_end, label in configs:
        print(f"===== {sym} =====")
        for em in exit_modes:
            for te in time_exits:
                res = run_config(sym, long_only, costs, spec, eff, is_end, em, te)
                s = res["ALL"]
                si = res["IS"]
                so = res["OOS"]
                print(f"  {em:>6} t{te:<4} ALL: n={s['n']:>2} EV_R={s['EV_R']:>7} PF_R={s['PF_R']:>6} "
                      f"年正={s['ann_pos']:>5}% | IS: n={si['n']:>2} PF_R={si['PF_R']:>6} "
                      f"年正={si['ann_pos']:>5}% | OOS: n={so['n']:>2} PF_R={so['PF_R']:>6} 年正={so['ann_pos']:>5}%")
                rows.append({
                    "symbol": sym, "exit": em, "time_exit": te,
                    "n_ALL": s["n"], "EV_R_ALL": s["EV_R"], "PF_R_ALL": s["PF_R"],
                    "ann_ALL": s["ann_pos"], "totalR_ALL": s["total_R"],
                    "n_IS": si["n"], "PF_R_IS": si["PF_R"], "ann_IS": si["ann_pos"],
                    "n_OOS": so["n"], "PF_R_OOS": so["PF_R"], "ann_OOS": so["ann_pos"],
                })
        print()

    df = pd.DataFrame(rows)
    df.to_csv(PROC / "S2_退出变体对比.csv", index=False, encoding="utf-8-sig")
    lines += ["| 品种 | 退出 | 超时bar | ALL n | ALL EV_R | ALL PF_R | ALL年正 | IS n | IS PF_R | IS年正 | OOS n | OOS PF_R | OOS年正 |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in df.iterrows():
        lines.append(f"| {r['symbol']} | {r['exit']} | {r['time_exit']} | {r['n_ALL']} | {r['EV_R_ALL']} "
                     f"| {r['PF_R_ALL']} | {r['ann_ALL']}% | {r['n_IS']} | {r['PF_R_IS']} | {r['ann_IS']}% "
                     f"| {r['n_OOS']} | {r['PF_R_OOS']} | {r['ann_OOS']}% |")
    lines += ["", "> tp=1.5R/3R 三批；break=反向5×13穿越全出；trail=高取低移动止损（4H段SMA13低点）；hybrid=1.5R出1/3后移动。"]
    (PROC / "S2_退出变体汇总.md").write_text("\n".join(lines), encoding="utf-8")
    print("  已保存 S2_退出变体对比.csv / S2_退出变体汇总.md")


if __name__ == "__main__":
    main()
