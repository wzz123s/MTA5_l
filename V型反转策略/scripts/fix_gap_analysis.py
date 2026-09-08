# -*- coding: utf-8 -*-
"""修复缺口分析：非周末缺口统计 + manifest 更新"""
from pathlib import Path
import pandas as pd
import json

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
NORMAL = {"M30": 1800, "H1": 3600, "H2": 7200, "H4": 14400, "H6": 21600, "D1": 86400}

def analyze(symbol, tf):
    path = RAW / f"{symbol}_{tf}.csv"
    df = pd.read_csv(path)
    dt = pd.to_datetime(df["date_utc"], utc=True)
    diff = dt.diff().dt.total_seconds().dropna()
    normal = NORMAL[tf]
    prev_dt = dt.shift(1)
    # 周末缺口：前一 bar 为周五 20:00 之后、当前 bar 为周一
    is_weekend = prev_dt.dt.dayofweek.eq(4) & (prev_dt.dt.hour >= 20) & dt.dt.dayofweek.eq(0)
    non_weekend_gap = (diff > normal * 1.5) & ~is_weekend
    return int(len(df)), str(dt.iloc[0]), str(dt.iloc[-1]), int(non_weekend_gap.sum()), int(diff.max())

report = ["# 数据质量检查报告", "", "| 品种 | 周期 | 行数 | 首bar(UTC) | 末bar(UTC) | 非周末缺口 | 最大间隔(秒) |", "|---|---|---|---|---|---|---|"]
for symbol in ["XAUUSDm", "USOILm"]:
    entries = []
    for tf in ["M30", "H1", "H2", "H4", "H6", "D1"]:
        try:
            rows, first, last, gaps, maxgap = analyze(symbol, tf)
            report.append(f"| {symbol} | {tf} | {rows} | {first} | {last} | {gaps} | {maxgap} |")
            entries.append({"timeframe": tf, "rows": rows, "first_utc": first, "last_utc": last, "non_weekend_gaps": gaps})
        except Exception as e:
            report.append(f"| {symbol} | {tf} | ERROR: {e} |")
    mpath = RAW / f"manifest_{symbol}.json"
    m = json.loads(mpath.read_text(encoding="utf-8"))
    m["files"] = entries
    mpath.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")

(RAW / "quality_check.md").write_text("\n".join(report) + "\n", encoding="utf-8")
print("\n".join(report))
