# -*- coding: utf-8 -*-
"""
stage3_v2.py —— V2 参数邻域稳健性

对候选参数包做 ±20% 及邻域扰动，检验 ALL/OOS 的 PF_R 与 EV_R 是否崩溃。
通过标准：ALL PF_R ≥ 1.2 且 OOS EV_R > 0（邻域内不崩溃）
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "阶段1_机会层统计" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "阶段2_全链路回测" / "scripts"))
import stage1_common as C
import stage2_backtest as B2

PROC = Path(__file__).resolve().parent / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)


def run(sym, long_only, costs, spec, eff, exit_mode, glue, bias, te, lb, spread=None, swap=None):
    d1 = C.analyze_tf(sym, "D1")
    h4 = C.analyze_tf(sym, "H4")
    cr = C.find_cross13_55(d1)
    cr = cr[pd.to_datetime(cr["time"]) >= eff].reset_index(drop=True)
    sp, sw = costs if spread is None else (spread, swap)
    tr = B2.fullchain_backtest(d1, h4, cr, sym, "D1", "H4",
                               glue_thresh=glue, bias_floor=bias,
                               stop_mode="sub_struct", stop_spec=spec,
                               exit_mode=exit_mode, time_exit_bars=te,
                               lookback_days=lb, long_only=long_only,
                               spread_price=sp, swap_per_bar=sw,
                               start=eff.strftime("%Y-%m-%d") if eff else None)
    return B2.summary(tr)


def main():
    print("== V2 参数邻域稳健性 ==")
    # 候选包
    cands = [
        ("XAUUSDm", True, (0.10, 0.002), ("pct", 0.003, 0.02), "break", "gold"),
        ("USOILm", False, (0.03, 0.0005), ("pct", 0.008, 0.025), "hybrid", "oil"),
    ]
    rows = []
    for sym, long_only, costs, spec, em, label in cands:
        eff = pd.Timestamp("2017-03-01") if sym == "XAUUSDm" else pd.Timestamp("2021-07-01")
        base = run(sym, long_only, costs, spec, eff, em, 0.003, 0.0, 120, 40)
        print(f"===== {sym} 基线: n={base['n']} EV_R={base['EV_R']} PF_R={base['PF_R']} 年正={base['ann_pos']}% =====")
        rows.append({"symbol": sym, "param": "base", "n": base["n"],
                     "EV_R": base["EV_R"], "PF_R": base["PF_R"], "ann": base["ann_pos"]})

        variants = []
        # glue 邻域
        for g in (0.001, 0.0024, 0.0036, 0.005, 0.01):
            variants.append((f"glue={g}", g, 0.0, 120, 40, em, spec))
        # bias 邻域
        for b in (0.0, 0.2, 0.5):
            variants.append((f"bias={b}", 0.003, b, 120, 40, em, spec))
        # time_exit ±20% + 边界
        for te in (96, 120, 144, 240):
            variants.append((f"te={te}", 0.003, 0.0, te, 40, em, spec))
        # lookback ±20%
        for lb in (32, 40, 48):
            variants.append((f"lb={lb}", 0.003, 0.0, 120, lb, em, spec))
        # 止损带 ±20%（上下界各扰动）
        lo, hi = spec[1], spec[2]
        for tag, nlo, nhi in [("sd-20%", lo*0.8, hi*0.8), ("sd+20%", lo*1.2, hi*1.2),
                              ("sd-lo-", lo*0.6, hi), ("sd-hi+", lo, hi*1.2)]:
            sp2 = ("pct", nlo, nhi)
            variants.append((f"spec{tag}", 0.003, 0.0, 120, 40, em, sp2))
        # 退出模式替换（稳健性参照）
        for em2 in ("tp", "break", "trail", "hybrid"):
            if em2 != em:
                variants.append((f"exit={em2}", 0.003, 0.0, 120, 40, em2, spec))

        n_fail = 0
        for name, g, b, te, lb, emx, spx in variants:
            r = run(sym, long_only, costs, spx, eff, emx, g, b, te, lb)
            fail = r["n"] > 0 and (r["PF_R"] < 1.2)
            if fail:
                n_fail += 1
            rows.append({"symbol": sym, "param": name, "n": r["n"],
                         "EV_R": r["EV_R"], "PF_R": r["PF_R"], "ann": r["ann_pos"],
                         "FAIL": "是" if fail else ""})
            print(f"  {name:<12} n={r['n']:>3} EV_R={r['EV_R']:>7} PF_R={r['PF_R']:>7} "
                  f"年正={r['ann_pos']:>5}% {'❌PF<1.2' if fail else ''}")
        print(f"  -> 失败组合: {n_fail}/{len(variants)}")
        print()

    df = pd.DataFrame(rows)
    df.to_csv(PROC / "V2_参数邻域稳健性.csv", index=False, encoding="utf-8-sig")
    print("  已保存 V2_参数邻域稳健性.csv")


if __name__ == "__main__":
    main()
