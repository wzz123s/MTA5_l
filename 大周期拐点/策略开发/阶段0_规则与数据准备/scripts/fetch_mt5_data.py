# -*- coding: utf-8 -*-
"""
fetch_mt5_data.py —— MT5 历史数据拉取 + raw_source_manifest.json（MCT 阶段0）

对齐 MTA5 策略生成规则：
  - 独立 MT5 Python API 数据源（source_type=mt5_api_history）
  - 每品种记录 source_id / symbol / timeframes / UTC 范围 / sha256 / 终端快照
  - 密码不落盘

用法：
  python fetch_mt5_data.py --symbol XAUUSDm --timeframes D1 H4 W1 --start 2016-01-01
  python fetch_mt5_data.py --all          # 拉取 XAUUSDm + USOILm 的 D1/H4/W1
输出：
  data/raw/<source_id>/<SYMBOL>_<TF>.csv   +   data/raw/raw_source_manifest.json
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

BASE_DIR = Path(__file__).resolve().parent.parent          # 阶段0_规则与数据准备/
RAW_DIR = BASE_DIR / "data" / "raw"

def timeframe_constant(mt5, label):
    """MT5 ENUM_TIMEFRAMES 常量（H1=16385/H4=16388/D1=16408/W1=16387，非分钟数）"""
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
    """拉取一段历史 K 线并转 DataFrame。"""
    tf = timeframe_constant(mt5, tf_label)
    rates = mt5.copy_rates_range(symbol, tf, utc_from, utc_to)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df[["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]]
    return df


def fetch_symbol(mt5, symbol: str, timeframes: list[str],
                 start: str, end: str, source_id: str) -> dict:
    utc_from = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    utc_to = datetime.fromisoformat(end).replace(tzinfo=timezone.utc)

    # 确保品种可见
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"MT5 无此品种: {symbol}")
    if not info.visible:
        mt5.symbol_select(symbol, True)

    out_dir = RAW_DIR / source_id
    out_dir.mkdir(parents=True, exist_ok=True)

    files = []
    for tf in timeframes:
        df = fetch_history(mt5, symbol, tf, utc_from, utc_to)
        if df is None or len(df) == 0:
            print(f"  [跳过] {symbol} {tf}: 无数据")
            continue
        fname = f"{symbol}_{tf}.csv"
        fpath = out_dir / fname
        df.to_csv(fpath, index=False)
        files.append({"name": fname, "rows": len(df),
                      "sha256": sha256_file(fpath),
                      "timeframe": tf,
                      "first": str(df["time"].iloc[0]),
                      "last": str(df["time"].iloc[-1])})
        print(f"  [OK] {symbol} {tf}: {len(df)} 行 "
              f"({df['time'].iloc[0].date()} ~ {df['time'].iloc[-1].date()})")
    return {"symbol": symbol, "source_id": source_id, "files": files}


def build_manifest(entries: list[dict], snapshot: dict) -> dict:
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_type": "mt5_api_history",
        "note": "MCT 大周期拐点策略 · 阶段0 原始数据包（独立数据源）",
        "terminal_snapshot": snapshot,
        "symbols": entries,
    }
    # 汇总 bundle sha256
    for ent in entries:
        if ent["files"]:
            ent["bundle_sha256"] = hashlib.sha256(
                "|".join(f["sha256"] for f in ent["files"]).encode()
            ).hexdigest()
    return manifest


def main():
    ap = argparse.ArgumentParser(description="MCT 阶段0：MT5 历史数据拉取")
    ap.add_argument("--symbol", default=None, help="品种，如 XAUUSDm")
    ap.add_argument("--timeframes", default="D1,H4,W1", help="周期列表，逗号分隔")
    ap.add_argument("--start", default="2016-01-01", help="开始日期")
    ap.add_argument("--end", default=None, help="结束日期（默认今天）")
    ap.add_argument("--all", action="store_true", help="拉取 XAUUSDm + USOILm")
    args = ap.parse_args()

    end = args.end or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tfs = [t.strip().upper() for t in args.timeframes.split(",")]

    symbols = []
    if args.all:
        symbols = ["XAUUSDm", "USOILm"]
    elif args.symbol:
        symbols = [args.symbol.upper()]
    else:
        ap.error("需要 --symbol 或 --all")

    mt5 = import_mt5()
    if not mt5.initialize():
        print("mt5.initialize 失败:", mt5.last_error(), file=sys.stderr)
        sys.exit(1)
    try:
        snap = terminal_snapshot(mt5)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        source_id = f"mct_mt5_{'_'.join(s.lower() for s in symbols)}_{stamp}"
        entries = []
        for sym in symbols:
            print(f"== 拉取 {sym} {','.join(tfs)} {args.start} ~ {end} ==")
            ent = fetch_symbol(mt5, sym, tfs, args.start, end, source_id)
            entries.append(ent)

        manifest = build_manifest(entries, snap)
        mpath = RAW_DIR / "raw_source_manifest.json"
        with open(mpath, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print("  manifest 已写入:", mpath)
        print(json.dumps(manifest, ensure_ascii=False, indent=2)[:2000])
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
