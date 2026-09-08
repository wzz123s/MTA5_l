# -*- coding: utf-8 -*-
"""事件分类与白名单：读取 MT5 日历导出 CSV（|分隔），分类事件、标记高影响与白名单币种。
输入: data/raw/calendar_export.csv
输出: data/processed/calendar_events.csv
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify_events import classify  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "calendar_export.csv"
OUT = ROOT / "data" / "processed" / "calendar_events.csv"

WHITELIST = {"USD", "EUR", "GBP", "CAD"}
HIGH_IMPORTANCE = 3  # MT5 importance>=3 视为高影响（MqlCalendarEvent.importance）


def main() -> None:
    df = pd.read_csv(RAW, sep="|", dtype={"event_id": "Int64", "importance": "Int64",
                                          "time": "Int64", "country_id": "Int64"})
    df["event_time_utc"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df["category"] = df["event_name"].apply(classify)
    df["is_high"] = df["importance"] >= HIGH_IMPORTANCE
    df["is_whitelisted"] = df["currency"].isin(WHITELIST)
    df["is_blackout_event"] = df["is_high"] & df["is_whitelisted"]
    df = df.sort_values("event_time_utc").reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    n_total = len(df)
    n_high = int(df["is_high"].sum())
    n_blackout = int(df["is_blackout_event"].sum())
    print(f"events total={n_total} high={n_high} blackout(high&whitelist)={n_blackout}")
    print(f"categories: {df['category'].value_counts().to_dict()}")
    print(f"whitelist currency counts: {df.loc[df['is_blackout_event'], 'currency'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
