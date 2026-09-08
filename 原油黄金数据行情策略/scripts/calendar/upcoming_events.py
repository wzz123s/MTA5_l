# -*- coding: utf-8 -*-
"""事件预告：查询未来 N 小时内的白名单高影响事件（模拟盘监测用）。
用法: python upcoming_events.py [hours=12]
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / "data" / "processed" / "calendar_events.csv"


def main() -> None:
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
    df = pd.read_csv(EV, parse_dates=["event_time_utc"])
    df["event_time_utc"] = pd.to_datetime(df["event_time_utc"], utc=True)
    now = pd.Timestamp.utcnow()
    upcoming = df[(df["is_blackout_event"] == True) & (df["event_time_utc"] >= now) & (df["event_time_utc"] <= now + pd.Timedelta(hours=hours))]
    upcoming = upcoming.sort_values("event_time_utc")
    print(f"未来 {hours:g}h 白名单高影响事件: {len(upcoming)} 条")
    for _, r in upcoming.iterrows():
        print(f"  {r['event_time_utc']} [{r['currency']}] {r['category']} | {r['event_name']}")


if __name__ == "__main__":
    main()
