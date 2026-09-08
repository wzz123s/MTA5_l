# -*- coding: utf-8 -*-
"""V反策略：MT5 历史数据自动下载脚本（独立编写，工作区专用）

用法：
    python download_mt5_data.py --symbol XAUUSDm --timeframes M30,H1,H2,H4,H6,D1 --from 2020-01-01
    python download_mt5_data.py --symbol USOILm --timeframes H2,H4,H6,D1 --from 2020-01-01
输出：V型反转策略/data/raw/<symbol>_<TF>.csv + manifest_<symbol>.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
from datetime import datetime, timedelta, timezone

import pandas as pd

TERMINAL_PATH = r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
OUTPUT_ROOT = Path(__file__).resolve().parents[1] / "data" / "raw"

TIMEFRAME_MAP = {
    "M30": 30, "H1": 60, "H2": 120, "H4": 240, "H6": 360, "D1": 1440,
}

def import_mt5():
    import MetaTrader5 as mt5
    return mt5

def tf_minutes(label: str) -> int:
    key = label.strip().upper()
    if key not in TIMEFRAME_MAP:
        raise ValueError("unsupported timeframe: " + label)
    return TIMEFRAME_MAP[key]

def fetch_bars(mt5, symbol: str, tf_label: str, date_from: datetime, date_to: datetime) -> pd.DataFrame:
    """分批拉取 K 线（MT5 copy_rates_range 每次限制约 5000 根，按月循环）"""
    rows = []
    cursor = date_from
    step = timedelta(days=28) if tf_minutes(tf_label) < 1440 else timedelta(days=365)
    while cursor < date_to:
        chunk_end = min(cursor + step, date_to)
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1 * 0 + _tf_const(mt5, tf_label), cursor, chunk_end)
        if rates is None or len(rates) == 0:
            err = mt5.last_error()
            print(f"  [{tf_label}] {cursor.date()} - {chunk_end.date()}: no data (err={err})")
            cursor = chunk_end
            continue
        rows.extend(rates)
        cursor = chunk_end
        time.sleep(0.1)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["time"]).sort_values("time").reset_index(drop=True)
    return df

def _tf_const(mt5, label: str):
    minutes = tf_minutes(label)
    table = {30: mt5.TIMEFRAME_M30, 60: mt5.TIMEFRAME_H1, 120: mt5.TIMEFRAME_H2,
             240: mt5.TIMEFRAME_H4, 360: mt5.TIMEFRAME_H6, 1440: mt5.TIMEFRAME_D1}
    return table[minutes]

def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--timeframes", required=True, help="逗号分隔，如 M30,H1,H2,H4,H6,D1")
    ap.add_argument("--from", dest="date_from", default="2020-01-01")
    ap.add_argument("--to", dest="date_to", default=None)
    args = ap.parse_args()

    tfs = [t.strip().upper() for t in args.timeframes.split(",") if t.strip()]
    date_from = datetime.strptime(args.date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    date_to = (datetime.now(timezone.utc) if args.date_to is None
               else datetime.strptime(args.date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc))

    mt5 = import_mt5()
    ok = mt5.initialize(path=TERMINAL_PATH)
    if not ok:
        raise RuntimeError("mt5.initialize failed: " + str(mt5.last_error()))
    try:
        info = mt5.symbol_info(args.symbol)
        if info is None:
            raise RuntimeError("symbol not available: " + args.symbol)
        if not info.visible:
            mt5.symbol_select(args.symbol, True)

        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        manifest_entries = []
        for tf in tfs:
            df = fetch_bars(mt5, args.symbol, tf, date_from, date_to)
            if df.empty:
                print(f"[{tf}] EMPTY, skip")
                continue
            df["date_utc"] = pd.to_datetime(df["time"], unit="s", utc=True)
            out = df[["time", "date_utc", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]]
            path = OUTPUT_ROOT / f"{args.symbol}_{tf}.csv"
            out.to_csv(path, index=False)
            digest = file_sha256(path)
            print(f"[{tf}] rows={len(out)} first={out['date_utc'].iloc[0]} last={out['date_utc'].iloc[-1]} sha={digest[:12]}")
            manifest_entries.append({
                "symbol": args.symbol, "timeframe": tf, "path": str(path),
                "rows": int(len(out)),
                "first_utc": str(out["date_utc"].iloc[0]),
                "last_utc": str(out["date_utc"].iloc[-1]),
                "sha256": digest,
            })
        manifest = {
            "source": "mt5_api_history",
            "terminal": TERMINAL_PATH,
            "symbol": args.symbol,
            "date_from_utc": str(date_from),
            "date_to_utc": str(date_to),
            "timeframes": tfs,
            "files": manifest_entries,
            "exported_utc": datetime.now(timezone.utc).isoformat(),
        }
        mpath = OUTPUT_ROOT / f"manifest_{args.symbol}.json"
        mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print("manifest ->", mpath)
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    main()
