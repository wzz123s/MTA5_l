# -*- coding: utf-8 -*-
"""转换 MT5 拉取数据为参考实现工程 base_data 格式（GBK 10 列，时间=UTC naive）。

服务器实测为 UTC（偏移 0），参考 CSV 亦为 UTC。prepare/load_m15 的 +2h
时区偏移是历史错误口径，本次迁移一并修正为 +0（见代码修改）。
"""
from __future__ import annotations


from pathlib import Path
import pandas as pd

MT5_DIR = Path(r"F:\use_code\MTA5_l\黄金\30m2H策略\data\raw\mt5_history\30m2h_mt5_20260811")
BASE_DIR = Path(r"F:\use_code\MTA5_l\黄金\30m2H策略\参考实现工程\base_data")


def convert(timeframe: str, out_name: str) -> None:
    src = MT5_DIR / f"XAUUSDm_{timeframe}.csv"
    out = BASE_DIR / out_name
    df = pd.read_csv(src, encoding="utf-8-sig")
    df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)  # UTC naive
    out_df = pd.DataFrame({
        "date": df["time"].dt.strftime("%Y-%m-%d %H:%M:%S"),
        "open": df["open"],
        "high": df["high"],
        "low": df["low"],
        "close": df["close"],
        "volume": df["tick_volume"],
        "spread": df["spread"],
        "real_volume": df["real_volume"],
        "symbol": "XAUUSDm",
        "time_diff": 0.0,
    })
    out_df.to_csv(out, index=False, encoding="gbk")
    print(f"{out_name}: {len(out_df)} rows, {out_df['date'].iloc[0]} ~ {out_df['date'].iloc[-1]}")


if __name__ == "__main__":
    convert("M30", "XAUUSDm30.csv")
    convert("M15", "XAUUSDm15.csv")
    print("转换完成")
