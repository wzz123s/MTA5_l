# -*- coding: utf-8 -*-
import pandas as pd
from pathlib import Path

# 回测推荐组合的交易明细（v5 黄金做空侧）
f = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\data\validation\bias_reversal_v5_XAUUSDm.csv")
if f.exists():
    tr = pd.read_csv(f, parse_dates=["signal_time", "exit_time"])
    tr = tr.sort_values("signal_time").reset_index(drop=True)
    tr["gap_hours"] = tr["signal_time"].diff().dt.total_seconds() / 3600
    print("=== v5 黄金做空侧 交易间隔 ===")
    print("n =", len(tr))
    print("间隔(小时): min=%.1f 中位=%.1f 均值=%.1f max=%.1f" % (
        tr["gap_hours"].min(), tr["gap_hours"].median(), tr["gap_hours"].mean(), tr["gap_hours"].max()))
    close_gap = tr[tr["gap_hours"] <= 24]
    print("间隔<=24h 的相邻笔数:", len(close_gap), "（占比 %.0f%%）" % (len(close_gap) / len(tr) * 100))
    print()
    print("全部交易（signal_time / exit / 间隔h / pnl）:")
    for _, r in tr.iterrows():
        g = "%.0f" % r["gap_hours"] if pd.notna(r["gap_hours"]) else "-"
        print("  %s -> %s  间隔%s h  %s  %+.1f" % (r["signal_time"].strftime('%Y-%m-%d %H:%M'), r["exit_time"].strftime('%Y-%m-%d %H:%M'), g, r["exit_reason"], r["pnl_points"]))
else:
    print("v5 file missing")
