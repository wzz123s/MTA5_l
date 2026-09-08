# -*- coding: utf-8 -*-
"""
stage1_tiers.py —— 周期档位横向验证（多周期数据包）

对 8 个档位对（入场TF/本级别TF）复制"13x55 穿越 → 次级别入场"逻辑：
  (H1,H4) (H2,H6) (H2,H8) (H3,H12) (H4,H16) (H6,D1) (H12,D2) (D1,W1)
输出：各档位 n / 频率 / EV_R / PF_R / 胜率（黄金+原油）
有效窗口：取 home/sub 两腿 valid_from 的较晚者（读 manifest）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage1_common as C
import stage1_backtest as B

TIERS = [("H1", "H4"), ("H2", "H6"), ("H2", "H8"), ("H3", "H12"),
         ("H4", "H16"), ("H6", "D1"), ("H12", "D2"), ("D1", "W1")]

# 成本（价格单位）：黄金 1pt=0.1；原油 1pt=0.01
COSTS = {"XAUUSDm": (0.10, 0.002), "USOILm": (0.03, 0.0005)}
SPEC = {"XAUUSDm": ("pct", 0.003, 0.02), "USOILm": ("pct", 0.008, 0.025)}


def valid_from_map():
    m = json.load(open(C.RAW / "raw_source_manifest.json", encoding="utf-8"))
    vf = {}
    for s in m["symbols"]:
        vf[s["symbol"]] = {f["timeframe"]: f["valid_from"] for f in s["files"]}
    return vf


def main():
    vf = valid_from_map()
    rows = []
    all_tr = []
    for sym in ["XAUUSDm", "USOILm"]:
        spread, swap = COSTS[sym]
        spec = SPEC[sym]
        print(f"===== {sym} 档位验证 =====")
        for sub_tf, home_tf in TIERS:
            eff = pd.Timestamp(max(vf[sym].get(home_tf, "2000-01-01"),
                                   vf[sym].get(sub_tf, "2000-01-01")))
            home = C.analyze_tf(sym, home_tf)
            sub = C.analyze_tf(sym, sub_tf)
            cr = C.find_cross13_55(home)
            cr = cr[pd.to_datetime(cr["time"]) >= eff].reset_index(drop=True)
            tr = B.backtest(cr, home, sub, sym, home_tf, sub_tf,
                            lookback_days=60, stop_mode="sub_struct",
                            stop_spec=spec, exit_mode="1.5R_3R",
                            time_exit_bars=120,
                            spread_price=spread, swap_per_bar=swap)
            s = B.summarize(tr, f"{home_tf}/{sub_tf}")
            years = (pd.to_datetime("2026-09-01") - eff).days / 365.25
            freq = len(cr) / max(years, 0.1)
            rows.append({
                "symbol": sym, "home_tf": home_tf, "sub_tf": sub_tf,
                "eff_from": str(eff.date()), "crossings": len(cr),
                "freq_per_year": round(freq, 1),
                "n_trades": s["n"], "EV_R": s["EV_R"], "PF_R": s["PF_R"],
                "winrate": s["winrate"],
            })
            print(f"  {home_tf}<-{sub_tf}: 穿越={len(cr)}({freq:.1f}/年) "
                  f"交易={s['n']} EV_R={s['EV_R']} PF_R={s['PF_R']} 胜率={s['winrate']}%")
            if len(tr):
                tr["symbol"] = sym
                all_tr.append(tr)
        print()

    df = pd.DataFrame(rows)
    df.to_csv(C.PROC / "T1_周期档位验证.csv", index=False, encoding="utf-8-sig")
    if all_tr:
        pd.concat(all_tr, ignore_index=True).to_csv(
            C.PROC / "T1_周期档位逐笔.csv", index=False, encoding="utf-8-sig")

    lines = ["# 周期档位横向验证（阶段1 · 多周期数据包）", "",
             "逻辑：本级别 13×55 穿越 → 次级别 5×13 同向穿越入场（sub_struct 止损 + 1.5R/3R 退出）。",
             "有效窗口按两腿 valid_from 较晚者。", "",
             "| 品种 | 档位(本/次) | 有效起点 | 穿越/年 | 交易数 | EV_R | PF_R | 胜率 |",
             "|---|---|---|---|---|---|---|---|"]
    for _, r in df.iterrows():
        lines.append(f"| {r['symbol']} | {r['home_tf']}<-{r['sub_tf']} | {r['eff_from']} "
                     f"| {r['freq_per_year']} | {r['n_trades']} | {r['EV_R']} | "
                     f"{r['PF_R']} | {r['winrate']}% |")
    lines += ["", "> EV_R/PF_R 为 R 倍数口径（跨止损距离可比）；PF_R≥1.2 视为该档位有正边际。"]
    (C.PROC / "T1_周期档位汇总.md").write_text("\n".join(lines), encoding="utf-8")
    print("  已保存 T1_周期档位验证.csv / T1_周期档位汇总.md")


if __name__ == "__main__":
    main()
