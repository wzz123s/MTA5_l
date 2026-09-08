# -*- coding: utf-8 -*-
"""
stage2_fullchain.py —— 阶段2 全链路主回测（V1 验收）

黄金：D1 13x55 穿越（LONG-only，阶段1 G2 结论）→ H4 入场（sub_struct 止损）→ tp 退出
原油：D1 13x55 穿越（双向，G1 通过）→ H4 入场 → tp 退出
样本：IS 黄金 2017-03~2022-12 / 原油 2021-07~2023-12；OOS 2023+/2024+
验收（V1）：样本内 PF≥1.5；年正收益 ≥80%
输出: data/processed/S2_主回测_<品种>_逐笔.csv + S2_主回测汇总.md
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


def run_symbol(sym, long_only, costs, spec, is_end, label):
    d1 = C.analyze_tf(sym, "D1")
    h4 = C.analyze_tf(sym, "H4")
    cr = C.find_cross13_55(d1)
    eff = pd.Timestamp("2017-03-01") if sym == "XAUUSDm" else pd.Timestamp("2021-07-01")
    cr = cr[pd.to_datetime(cr["time"]) >= eff].reset_index(drop=True)

    spread, swap = costs
    res = {}
    windows = {
        "IS": (eff.strftime("%Y-%m-%d"), is_end.strftime("%Y-%m-%d")),
        "OOS": ((is_end + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), None),
    }
    for name, (s, e) in windows.items():
        tr = B2.fullchain_backtest(d1, h4, cr, sym, "D1", "H4",
                                   glue_thresh=0.003, bias_floor=0.0,
                                   stop_mode="sub_struct", stop_spec=spec,
                                   exit_mode="tp", time_exit_bars=120,
                                   long_only=long_only,
                                   spread_price=spread, swap_per_bar=swap,
                                   start=s, end=e)
        res[name] = (tr, B2.summary(tr, f"{sym} {name}"))
    # 全程（IS+OOS）
    tr_all = B2.fullchain_backtest(d1, h4, cr, sym, "D1", "H4",
                                   glue_thresh=0.003, bias_floor=0.0,
                                   stop_mode="sub_struct", stop_spec=spec,
                                   exit_mode="tp", time_exit_bars=120,
                                   long_only=long_only,
                                   spread_price=spread, swap_per_bar=swap,
                                   start=eff.strftime("%Y-%m-%d"))
    res["ALL"] = (tr_all, B2.summary(tr_all, f"{sym} ALL"))
    return cr, res


def main():
    print("== 阶段2 全链路主回测 ==")
    lines = ["# 阶段2 全链路主回测（V1 验收）", ""]
    all_trades = []

    # 黄金 LONG-only
    print()
    print("===== 黄金 XAUUSDm（LONG-only，H4 入场，sub_struct 0.3%~2.0%，tp 退出）=====")
    cr_g, res_g = run_symbol("XAUUSDm", True, (0.10, 0.002),
                             ("pct", 0.003, 0.02), pd.Timestamp("2022-12-31"), "gold")
    for k, (tr, s) in res_g.items():
        print(f"  {k}: n={s['n']} (L={s['n_long']}) EV_R={s['EV_R']} PF_R={s['PF_R']} "
              f"胜率={s['winrate']}% 年正={s['ann_pos']}% 总R={s['total_R']}")
        if len(tr):
            tr["symbol"] = "XAUUSDm"; tr["sample"] = k
            all_trades.append(tr)
    ys_g = B2.yearly_summary(res_g["ALL"][0])

    # 原油双向
    print()
    print("===== 原油 USOILm（双向，H4 入场，sub_struct 0.8%~2.5%，tp 退出）=====")
    cr_o, res_o = run_symbol("USOILm", False, (0.03, 0.0005),
                             ("pct", 0.008, 0.025), pd.Timestamp("2023-12-31"), "oil")
    for k, (tr, s) in res_o.items():
        print(f"  {k}: n={s['n']} (L={s['n_long']}/S={s['n_short']}) EV_R={s['EV_R']} PF_R={s['PF_R']} "
              f"胜率={s['winrate']}% 年正={s['ann_pos']}% 总R={s['total_R']}")
        if len(tr):
            tr["symbol"] = "USOILm"; tr["sample"] = k
            all_trades.append(tr)
    ys_o = B2.yearly_summary(res_o["ALL"][0])

    if all_trades:
        pd.concat(all_trades, ignore_index=True).to_csv(
            PROC / "S2_主回测_逐笔.csv", index=False, encoding="utf-8-sig")

    # 汇总
    lines += ["| 品种 | 样本 | n | L/S | EV_R | PF_R | 胜率 | 年正收益 | 总R |",
              "|---|---|---|---|---|---|---|---|---|"]
    for sym, res in [("XAUUSDm", res_g), ("USOILm", res_o)]:
        for k in ["IS", "OOS", "ALL"]:
            s = res[k][1]
            lines.append(f"| {sym} | {k} | {s['n']} | {s['n_long']}/{s['n_short']} "
                         f"| {s['EV_R']} | {s['PF_R']} | {s['winrate']}% | {s['ann_pos']}% | {s['total_R']} |")
    lines += ["", "### 年度明细（全程）", "", "| 品种 | 年 | n | ΣR | PF_R | 胜率 |", "|---|---|---|---|---|---|"]
    for sym, ys in [("XAUUSDm", ys_g), ("USOILm", ys_o)]:
        for _, r in ys.iterrows():
            lines.append(f"| {sym} | {r['year']} | {r['n']} | {r['sum_R']} | {r['PF_R']} | {r['winrate']}% |")

    # V1 验收
    g_is = res_g["IS"][1]
    o_is = res_o["IS"][1]
    gate_g = g_is["PF_R"] >= 1.5 and g_is["ann_pos"] >= 80
    gate_o = o_is["PF_R"] >= 1.5 and o_is["ann_pos"] >= 80
    lines += ["", "## V1 验收", "",
              f"- 黄金 IS：PF_R={g_is['PF_R']}、年正收益={g_is['ann_pos']}% → "
              f"{'✅ 通过' if gate_g else '❌ 未通过'}（PF≥1.5 且年正≥80%）",
              f"- 原油 IS：PF_R={o_is['PF_R']}、年正收益={o_is['ann_pos']}% → "
              f"{'✅ 通过' if gate_o else '❌ 未通过'}（PF≥1.5 且年正≥80%）"]
    (PROC / "S2_主回测汇总.md").write_text("\n".join(lines), encoding="utf-8")
    print()
    print("V1 验收：", "黄金", "✅" if gate_g else "❌",
          f"(PF_R={g_is['PF_R']}, 年正={g_is['ann_pos']}%)",
          "| 原油", "✅" if gate_o else "❌",
          f"(PF_R={o_is['PF_R']}, 年正={o_is['ann_pos']}%)")
    print("  已保存 S2_主回测_逐笔.csv / S2_主回测汇总.md")


if __name__ == "__main__":
    main()
