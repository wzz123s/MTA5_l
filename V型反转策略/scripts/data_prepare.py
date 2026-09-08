# -*- coding: utf-8 -*-
"""V反策略：数据统一与 D1 重采样（P0 收尾 + P1 数据层）

步骤：
1. 统一列名与时间解析（黄金 date 列 / 原油 time 列）
2. 从 H1 重采样生成 D1（按 UTC 日边界）
3. 输出 manifest_<symbol>.json（行数/时间范围/sha256）
4. 输出质量检查 quality_check.md
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

FILES = {
    "XAUUSDm": ["M15", "M30", "H1", "H2", "H4", "H6", "H8", "W1"],
    "USOILm": ["M15", "H1", "H2", "H4", "H6", "H8", "W1"],
}

def read_bars(symbol: str, tf: str) -> pd.DataFrame:
    path = RAW / f"{symbol}_{tf}.csv"
    df = pd.read_csv(path)
    # 统一时间列与列名
    if "date" in df.columns:
        df["dt"] = pd.to_datetime(df["date"], utc=True)
    elif "date_utc" in df.columns:
        df["dt"] = pd.to_datetime(df["date_utc"], utc=True)
    elif "time" in df.columns:
        df["dt"] = pd.to_datetime(df["time"], unit="s", utc=True)
    else:
        raise ValueError(f"no time column in {path}")
    out = pd.DataFrame({
        "dt": df["dt"],
        "open": df["open"].astype(float),
        "high": df["high"].astype(float),
        "low": df["low"].astype(float),
        "close": df["close"].astype(float),
        "tick_volume": df["tick_volume"].fillna(0).astype(int),
        "spread": df["spread"].fillna(0).astype(int),
    })
    out = out.drop_duplicates(subset=["dt"]).sort_values("dt").reset_index(drop=True)
    return out

def resample_d1(h1: pd.DataFrame) -> pd.DataFrame:
    """从 H1 按 UTC 日边界重采样 D1"""
    h1 = h1.set_index("dt")
    daily = h1.resample("D").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "tick_volume": "sum",
        "spread": "mean",
    }).dropna(subset=["open", "high", "low", "close"]).reset_index()
    return daily

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    report: list[str] = []
    report.append("# 数据质量检查报告")
    report.append("")
    report.append("| 品种 | 周期 | 行数 | 首bar(UTC) | 末bar(UTC) | 缺口数 |")
    report.append("|---|---|---|---|---|---|")

    for symbol, tfs in FILES.items():
        entries = []
        h1 = None
        for tf in tfs:
            df = read_bars(symbol, tf)
            # 缺口检查（相邻 bar 间隔超出该周期容忍）
            tol = {"M15": 60, "M30": 120, "H1": 240, "H2": 480, "H4": 960, "H6": 1440, "H8": 1920, "W1": 20160}[tf]
            gaps = int((df["dt"].diff().dt.total_seconds() > tol * 60).sum())
            out_path = RAW / f"{symbol}_{tf}.csv"
            # 统一列名写回（覆盖原文件，保留 dt 与 date_utc 两列）
            df_out = df.copy()
            df_out["date_utc"] = df_out["dt"].dt.strftime("%Y-%m-%d %H:%M:%S%z")
            df_out = df_out[["dt", "date_utc", "open", "high", "low", "close", "tick_volume", "spread"]]
            df_out.to_csv(out_path, index=False)
            entries.append({
                "timeframe": tf, "path": str(out_path), "rows": int(len(df)),
                "first_utc": str(df["dt"].iloc[0]), "last_utc": str(df["dt"].iloc[-1]),
                "gaps": int(gaps), "sha256": sha256(out_path),
            })
            report.append(f"| {symbol} | {tf} | {len(df)} | {df['dt'].iloc[0]} | {df['dt'].iloc[-1]} | {gaps} |")
            if tf == "H1":
                h1 = df
        # D1 重采样
        if h1 is not None:
            d1 = resample_d1(h1)
            d1_out = RAW / f"{symbol}_D1.csv"
            d1_out_df = d1.copy()
            d1_out_df["date_utc"] = d1_out_df["dt"].dt.strftime("%Y-%m-%d %H:%M:%S%z")
            d1_out_df = d1_out_df[["dt", "date_utc", "open", "high", "low", "close", "tick_volume", "spread"]]
            d1_out_df.to_csv(d1_out, index=False)
            entries.append({
                "timeframe": "D1", "path": str(d1_out), "rows": int(len(d1)),
                "first_utc": str(d1["dt"].iloc[0]), "last_utc": str(d1["dt"].iloc[-1]),
                "gaps": -1, "note": "resampled from H1", "sha256": sha256(d1_out),
            })
            report.append(f"| {symbol} | D1 | {len(d1)} | {d1['dt'].iloc[0]} | {d1['dt'].iloc[-1]} | (重采样) |")
        manifest = {
            "source": "MTA5_l_existing_mt5_history",
            "symbol": symbol,
            "note": "数据来自 MTA5_l 项目已下载的 MT5 历史数据（2026-08-15 窗口），D1 由 H1 重采样",
            "files": entries,
        }
        mpath = RAW / f"manifest_{symbol}.json"
        mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{symbol}] manifest -> {mpath}")

    report_path = RAW / "quality_check.md"
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("quality_check ->", report_path)

if __name__ == "__main__":
    main()
