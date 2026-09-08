# -*- coding: utf-8 -*-
"""
stage3_v3.py —— V3 稳健性：成本敏感性 + 滚动3年窗口 + 年度拆分

候选包：黄金 mct_d1_h4_break_long_sd03-20_g003_b0_t120
        原油 mct_d1_h4_hybrid_both_sd08-25_g003_b0_t120
成本矩阵：黄金 spread 0.05~0.20（0.5~2pt）/ swap 0.001~0.003
          原油 spread 0.01~0.05（1~5pt）/ swap 0.00025~0.001
通过：全部成本组合 EV_R>0 且 PF_R≥1.2；滚动3年窗口多数正
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

CONFIGS = {
    "XAUUSDm": dict(long_only=True, spec=("pct", 0.003, 0.02), exit_mode="break",
                    eff="2017-03-01", spread=(0.05, 0.10, 0.15, 0.20), swap=(0.001, 0.002, 0.003)),
    "USOILm": dict(long_only=False, spec=("pct", 0.008, 0.025), exit_mode="hybrid",
                   eff="2021-07-01", spread=(0.01, 0.03, 0.05), swap=(0.00025, 0.0005, 0.001)),
}


def backtest(sym, cfg, spread, swap, start=None, end=None):
    d1 = C.analyze_tf(sym, "D1")
    h4 = C.analyze_tf(sym, "H4")
    cr = C.find_cross13_55(d1)
    cr = cr[pd.to_datetime(cr["time"]) >= cfg["eff"]].reset_index(drop=True)
    return B2.fullchain_backtest(d1, h4, cr, sym, "D1", "H4",
                                 glue_thresh=0.003, bias_floor=0.0,
                                 stop_mode="sub_struct", stop_spec=cfg["spec"],
                                 exit_mode=cfg["exit_mode"], time_exit_bars=120,
                                 long_only=cfg["long_only"],
                                 spread_price=spread, swap_per_bar=swap,
                                 start=start, end=end)


def main():
    print("== V3-A 成本敏感性 ==")
    rows = []
    for sym, cfg in CONFIGS.items():
        print(f"===== {sym} =====")
        for sp in cfg["spread"]:
            for sw in cfg["swap"]:
                tr = backtest(sym, cfg, sp, sw)
                s = B2.summary(tr, f"{sym} sp{sp} sw{sw}")
                ok = s["EV_R"] > 0 and s["PF_R"] >= 1.2
                rows.append({"symbol": sym, "spread": sp, "swap": sw, "n": s["n"],
                             "EV_R": s["EV_R"], "PF_R": s["PF_R"], "winrate": s["winrate"],
                             "ok": ok})
                print(f"  sp={sp} sw={sw}: n={s['n']} EV_R={s['EV_R']} PF_R={s['PF_R']} "
                      f"胜率={s['winrate']}% {'✅' if ok else '❌'}")
        print()

    # 盈亏平衡点：线性插值找 EV_R=0 的最大点差（保持默认 swap）
    print("== 盈亏平衡点差（默认 swap）==")
    for sym, cfg in CONFIGS.items():
        sw0 = cfg["swap"][1]
        evs = []
        for sp in np.linspace(0.0, 0.5, 21) if sym == "XAUUSDm" else np.linspace(0.0, 0.2, 21):
            s = B2.summary(backtest(sym, cfg, sp, sw0))
            evs.append((sp, s["EV_R"]))
        be = next((sp for sp, ev in evs if ev <= 0), None)
        print(f"  {sym}: 默认 swap={sw0}，盈亏平衡点差 ≈ {be if be is not None else '>上限'} "
              f"（价格单位，{sym=='XAUUSDm' and '1pt=0.1' or '1pt=0.01'}）")

    print()
    print("== V3-B 滚动 3 年窗口（默认成本）==")
    roll_rows = []
    for sym, cfg in CONFIGS.items():
        sw0 = cfg["swap"][1]
        sp0 = cfg["spread"][1]
        eff = pd.Timestamp(cfg["eff"])
        last = pd.Timestamp("2026-09-01")
        wins = []
        t = eff
        while t + pd.Timedelta(days=1095) <= last:
            te = t + pd.Timedelta(days=1095)
            tr = backtest(sym, cfg, sp0, sw0, start=t.strftime("%Y-%m-%d"),
                          end=te.strftime("%Y-%m-%d"))
            s = B2.summary(tr)
            wins.append({"win_start": str(t.date()), "win_end": str(te.date()),
                         "n": s["n"], "EV_R": s["EV_R"], "PF_R": s["PF_R"]})
            t += pd.Timedelta(days=182)
        wdf = pd.DataFrame(wins)
        nneg = int((wdf["EV_R"] < 0).sum())
        print(f"  {sym}: {len(wdf)} 个滚动3年窗口，EV_R<0 的 {nneg} 个，"
              f"PF_R 中位 {wdf['PF_R'].median():.2f}（min {wdf['PF_R'].min():.2f} / max {wdf['PF_R'].max():.2f}）")
        roll_rows.append(wdf.assign(symbol=sym))

    print()
    print("== V3-C 年度拆分（默认成本）==")
    ann_rows = []
    for sym, cfg in CONFIGS.items():
        tr = backtest(sym, cfg, cfg["spread"][1], cfg["swap"][1])
        ys = B2.yearly_summary(tr)
        print(f"  {sym}:")
        print(ys.to_string(index=False))
        ann_rows.append(ys.assign(symbol=sym))

    pd.DataFrame(rows).to_csv(PROC / "V3_成本敏感性.csv", index=False, encoding="utf-8-sig")
    pd.concat(roll_rows, ignore_index=True).to_csv(PROC / "V3_滚动3年窗口.csv", index=False, encoding="utf-8-sig")
    pd.concat(ann_rows, ignore_index=True).to_csv(PROC / "V3_年度拆分.csv", index=False, encoding="utf-8-sig")
    print("  已保存 V3_成本敏感性.csv / V3_滚动3年窗口.csv / V3_年度拆分.csv")


if __name__ == "__main__":
    main()
