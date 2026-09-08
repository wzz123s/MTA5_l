# -*- coding: utf-8 -*-
"""
fetch_multiperiod_data.py —— MCT 大周期拐点策略 · 多周期验证数据包（阶段1，v2）

按策略验证的周期组合下载 XAUUSDm / USOILm 历史数据：
  1H/4H, 2H/6H/8H, 3H/12H, 4H/16H, 6H/1D, 12H/2D, 1D/1W
去重后共 11 个周期：H1 H2 H3 H4 H6 H8 H12 H16 D1 D2 W1

数据质量处理（v2，实测 Exness-MT5Trial5 服务器）：
  1. 服务器对 H1~H8 的历史深度有限：更早只返回"日线粒度"伪条
     - XAUUSDm: H1~H8 真密度 2017-03-01 起；H12/D1/W1 2016-01-03 起
     - USOILm : H1~H8 真密度 2021-07-01 起；H12/D1/W1 2019-03-01 起
  2. 各原生周期按实测 valid_from 截断，保证包内每根 K 线都是真密度
  3. 派生周期（MT5 无原生）：
     - H16 <- H4 x4 连续合成（交易时段连续，开放时=首根 4H 开放时）
     - D2  <- D1 x2 连续合成（交易日配对，开放时=首日 00:00）
  4. raw_source_manifest.json 记录 per-file valid_from / truncated / sha256 / 终端快照

用法：
  python fetch_multiperiod_data.py                    # XAUUSDm + USOILm，2016-01-01 起
输出：
  阶段1_机会层统计/data/raw/mt5_history/<source_id>/<SYMBOL>_<TF>.csv
  阶段1_机会层统计/data/raw/mt5_history/raw_source_manifest.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent          # 阶段1_机会层统计/
RAW_DIR = BASE_DIR / "data" / "raw" / "mt5_history"

NATIVE_TFS = ["H1", "H2", "H3", "H4", "H6", "H8", "H12", "D1", "W1"]
DERIVED_TFS = {"H16": ("H4", 4), "D2": ("D1", 2)}
ALL_TFS = NATIVE_TFS + list(DERIVED_TFS.keys())

# 月度真密度阈值（bar/月；低于视为日线粒度伪条）
MONTHLY_THRESH = {"H1": 300, "H2": 150, "H3": 100, "H4": 75,
                  "H6": 50, "H8": 35, "H12": 22, "D1": 15, "W1": 3}

COLUMNS = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]


def timeframe_constant(mt5, label):
    attr = "TIMEFRAME_" + label.upper()
    if hasattr(mt5, attr):
        return int(getattr(mt5, attr))
    raise ValueError(f"未知周期: {label}")


def import_mt5():
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise RuntimeError("MetaTrader5 包未安装：pip install MetaTrader5") from exc
    return mt5


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def terminal_snapshot(mt5) -> dict:
    try:
        ti = mt5.terminal_info()
        ai = mt5.account_info()
        return {
            "terminal_name": getattr(ti, "name", None),
            "terminal_path": getattr(ti, "path", None),
            "company": getattr(ti, "company", None),
            "account": getattr(ai, "login", None) if ai else None,
            "account_hash": hashlib.sha256(
                str(getattr(ai, "login", "")).encode()
            ).hexdigest()[:16] if ai else None,
            "leveraged": getattr(ai, "leverage", None) if ai else None,
            "server": getattr(ai, "server", None) if ai else None,
            "currency": getattr(ai, "currency", None) if ai else None,
        }
    except Exception:
        return {}


def fetch_history(mt5, symbol: str, tf_label: str, utc_from, utc_to):
    tf = timeframe_constant(mt5, tf_label)
    rates = mt5.copy_rates_range(symbol, tf, utc_from, utc_to)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    return df[COLUMNS]


def compute_valid_from(df: pd.DataFrame, tf_label: str) -> pd.datetime:
    """返回首个"真密度月"的第一根 K 线时间（排除当前不完整月）。"""
    if df is None or len(df) == 0:
        return None
    thresh = MONTHLY_THRESH[tf_label]
    d = df.copy()
    d["ym"] = pd.to_datetime(d["time"]).dt.tz_convert(None).dt.to_period("M")
    cnt = d.groupby("ym").size()
    cur = cnt.index.max()                       # 当前月（可能不完整）
    dense = cnt[(cnt >= thresh) & (cnt.index < cur)]
    if len(dense) == 0:
        return df["time"].iloc[0]
    first_dense_month = dense.index.min()
    sub = d[d["ym"] >= first_dense_month]
    return sub["time"].iloc[0]


def aggregate_bars(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """按连续 n 根源K线合成目标K线（交易时段连续配对，不丢根）。

    开放时=组内首根 time；high/low=组内极值；close=组内末根 close；
    tick_volume/real_volume 求和；spread 取末根。尾部不足 n 根丢弃。
    """
    df = df.copy().reset_index(drop=True)
    k = len(df) // n
    out_rows = []
    for i in range(k):
        g = df.iloc[i * n:(i + 1) * n]
        out_rows.append({
            "time": g["time"].iloc[0],
            "open": g["open"].iloc[0],
            "high": g["high"].max(),
            "low": g["low"].min(),
            "close": g["close"].iloc[-1],
            "tick_volume": int(g["tick_volume"].sum()),
            "spread": g["spread"].iloc[-1],
            "real_volume": int(g["real_volume"].sum()),
        })
    return pd.DataFrame(out_rows, columns=COLUMNS)


def fetch_symbol(mt5, symbol: str, start: str, end: str, source_id: str) -> dict:
    utc_from = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    utc_to = datetime.fromisoformat(end).replace(tzinfo=timezone.utc)

    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"MT5 无此品种: {symbol}")
    if not info.visible:
        mt5.symbol_select(symbol, True)

    out_dir = RAW_DIR / source_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) 拉取原生周期并截断到真密度
    native = {}
    for tf in NATIVE_TFS:
        df = fetch_history(mt5, symbol, tf, utc_from, utc_to)
        if df is None or len(df) == 0:
            print(f"  [跳过] {symbol} {tf}: 无数据")
            continue
        vf = compute_valid_from(df, tf)
        truncated = vf is not None and df["time"].iloc[0] < vf
        if truncated:
            df = df[df["time"] >= vf].reset_index(drop=True)
        native[tf] = df
        _save_csv(out_dir, symbol, tf, df)
        tail = f"  [已截断] valid_from={vf}" if truncated else ""
        print(f"  [OK] {symbol} {tf}: {len(df)} 行 "
              f"({df['time'].iloc[0]} ~ {df['time'].iloc[-1]}){tail}")

    # 2) 派生周期
    for tf, (src_tf, n) in DERIVED_TFS.items():
        if src_tf not in native:
            print(f"  [跳过] {symbol} {tf}: 源周期 {src_tf} 无数据")
            continue
        df = aggregate_bars(native[src_tf], n)
        if len(df) == 0:
            print(f"  [跳过] {symbol} {tf}: 合成结果为空")
            continue
        _save_csv(out_dir, symbol, tf, df)
        print(f"  [OK] {symbol} {tf} (由 {src_tf} x{n} 合成): {len(df)} 行 "
              f"({df['time'].iloc[0]} ~ {df['time'].iloc[-1]})")

    # 3) 文件清单 + valid_from
    files = []
    for fpath in sorted(out_dir.glob(f"{symbol}_*.csv")):
        d = pd.read_csv(fpath, parse_dates=["time"])
        tf = fpath.stem.replace(f"{symbol}_", "")
        files.append({
            "name": fpath.name,
            "rows": len(d),
            "sha256": sha256_file(fpath),
            "timeframe": tf,
            "derived": tf in DERIVED_TFS,
            "derived_from": DERIVED_TFS.get(tf, [None])[0],
            "valid_from": str(d["time"].iloc[0]),
            "first": str(d["time"].iloc[0]),
            "last": str(d["time"].iloc[-1]),
        })
    return {"symbol": symbol, "source_id": source_id, "files": files}


def _save_csv(out_dir: Path, symbol: str, tf: str, df: pd.DataFrame):
    df = df.copy()
    df["time"] = df["time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df.to_csv(out_dir / f"{symbol}_{tf}.csv", index=False)


def build_manifest(entries: list[dict], snapshot: dict, start: str, end: str,
                   quality: dict) -> dict:
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_type": "mt5_api_history",
        "note": "MCT 大周期拐点策略 · 阶段1 多周期验证数据包（独立数据源，v2 真密度）",
        "period_pairs": ["1H/4H", "2H/6H/8H", "3H/12H", "4H/16H", "6H/1D", "12H/2D", "1D/1W"],
        "timeframes": ALL_TFS,
        "derived_rules": {k: f"{v[0]} x{v[1]} 连续K线合成" for k, v in DERIVED_TFS.items()},
        "quality": quality,
        "requested_range": {"start": start, "end": end},
        "terminal_snapshot": snapshot,
        "symbols": entries,
    }
    for ent in entries:
        if ent["files"]:
            ent["bundle_sha256"] = hashlib.sha256(
                "|".join(f["sha256"] for f in ent["files"]).encode()
            ).hexdigest()
    return manifest


def main():
    ap = argparse.ArgumentParser(description="MCT 阶段1：多周期历史数据拉取")
    ap.add_argument("--symbol", default=None, help="品种，默认 XAUUSDm + USOILm")
    ap.add_argument("--start", default="2016-01-01", help="开始日期")
    ap.add_argument("--end", default=None, help="结束日期（默认今天）")
    args = ap.parse_args()

    end = args.end or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    symbols = [args.symbol.upper()] if args.symbol else ["XAUUSDm", "USOILm"]

    mt5 = import_mt5()
    if not mt5.initialize():
        print("mt5.initialize 失败:", mt5.last_error(), file=sys.stderr)
        sys.exit(1)
    try:
        snap = terminal_snapshot(mt5)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        source_id = f"mct_mt5_multiperiod_{stamp}"
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        entries = []
        for sym in symbols:
            print(f"== 拉取 {sym} {','.join(ALL_TFS)} {args.start} ~ {end} ==")
            entries.append(fetch_symbol(mt5, sym, args.start, end, source_id))

        quality = {
            "server_history_depth": {
                "XAUUSDm": {"H1-H8": "2017-03-01 起真密度", "H12/D1/W1": "2016-01-03 起"},
                "USOILm": {"H1-H8": "2021-07-01 起真密度", "H12/D1/W1": "2019-03-01 起"},
            },
            "note": "实测 Exness-MT5Trial5 对 H1~H8 的历史深度有限，更早返回日线粒度伪条；"
                    "包内所有文件已截断至真密度，valid_from 见各文件。"
                    "H16/D2 为派生周期（MT5 无原生），规则见 derived_rules。",
        }
        manifest = build_manifest(entries, snap, args.start, end, quality)
        mpath = RAW_DIR / "raw_source_manifest.json"
        with open(mpath, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print("  manifest 已写入:", mpath)
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
