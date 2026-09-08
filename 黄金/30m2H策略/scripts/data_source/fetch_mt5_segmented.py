# -*- coding: utf-8 -*-
"""30m2H MT5 分段拉取脚本（避免单次 copy_rates_range 条数上限）。

Exness 模拟服务器数据边界（2026-08-11 探测）:
  - M30: 2018-02-22 起（完整）
  - H2:  2018-01-01 起（完整）
  - M15: 2022-05-17 起（服务器限制，更早无数据）

单次 copy_rates_range 请求在 ~10万 bars 时报 -2 (Invalid params)，
因此按 2 年（M15 按 1 年）分段拉取后合并。
"""
from __future__ import annotations


import json
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys

ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_DIR = Path(__file__).resolve().parents[2]
STRATEGY = "30m2H"
SOURCE_ID = "30m2h_mt5_20260811"
SYMBOL = "XAUUSDm"

sys.path.insert(0, str(ROOT / "scripts"))

from mt5.mt5_connection import initialize_mt5, shutdown_mt5, ensure_symbol, timeframe_constant  # noqa: E402
from mt5.mt5_history import (  # noqa: E402
    bars_to_frame,
    summarize_frame,
    file_sha256,
    build_bundle_sha,
)
from mt5.mt5_connection import public_terminal_snapshot, public_account_snapshot, public_symbol_snapshot  # noqa: E402

# 每个时间周期的 (起始日期, 分段年数)
FRAME_PLAN = {
    "M30": ("2018-01-01", 2),
    "H2": ("2018-01-01", 2),
    "M15": ("2022-05-01", 1),
}
DATE_TO = "2026-08-11"


def chunk_ranges(start_str: str, years: int, end_str: str):
    """生成 [start, end) 分段，每段 years 年。"""
    start = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end = datetime.strptime(end_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    chunks = []
    cur = start
    while cur < end:
        nxt = datetime(cur.year + years, cur.month, cur.day, tzinfo=timezone.utc)
        if nxt > end:
            nxt = end
        chunks.append((cur, nxt))
        cur = nxt
    return chunks


def main() -> None:
    bundle_dir = STRATEGY_DIR / "data" / "raw" / "mt5_history" / SOURCE_ID
    bundle_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = STRATEGY_DIR / "data" / "raw"

    mt5 = initialize_mt5()
    try:
        ensure_symbol(mt5, SYMBOL)
        files: list[dict] = []
        m30_path: Path | None = None

        for tf, (start_str, years) in FRAME_PLAN.items():
            chunks = chunk_ranges(start_str, years, DATE_TO)
            print(f"[{tf}] {len(chunks)} chunks: {start_str} ~ {DATE_TO}")
            frames = []
            for s, e in chunks:
                rates = mt5.copy_rates_range(SYMBOL, timeframe_constant(mt5, tf), s, e)
                if rates is None or len(rates) == 0:
                    print(f"  WARN: {tf} {s.date()}~{e.date()} 无数据: {mt5.last_error()}")
                    continue
                frames.append(bars_to_frame(rates, SYMBOL, tf))
                print(f"  {s.date()}~{e.date()}: {len(rates)} bars")
            if not frames:
                print(f"  ERROR: {tf} 无任何数据")
                continue
            import pandas as pd
            merged = pd.concat(frames, ignore_index=True)
            # 去重 + 排序（分段边界可能重叠）
            merged = merged.drop_duplicates(subset=["time"], keep="last").sort_values("time").reset_index(drop=True)
            out_path = bundle_dir / f"{SYMBOL}_{tf}.csv"
            merged.to_csv(out_path, index=False, encoding="utf-8-sig")
            files.append(summarize_frame(merged, out_path, tf))
            print(f"  => {len(merged)} bars -> {out_path.name}")
            if tf == "M30":
                m30_path = out_path
        if m30_path is None:
            raise RuntimeError("M30 数据缺失")

        # 兼容文件 XAUUSDm30.csv（prepare 消费入口）
        compatibility_raw_file = raw_dir / "XAUUSDm30.csv"
        shutil.copy2(m30_path, compatibility_raw_file)

        snapshot = {
            "terminal": public_terminal_snapshot(mt5),
            "account": public_account_snapshot(mt5),
            "symbol": public_symbol_snapshot(mt5, SYMBOL),
        }
    finally:
        shutdown_mt5(mt5)

    now = datetime.now(timezone.utc).isoformat()
    seed = {
        "strategy": STRATEGY,
        "source_type": "mt5_api_history",
        "source_id": SOURCE_ID,
        "symbol": SYMBOL,
        "timeframes": list(FRAME_PLAN.keys()),
        "date_from_utc": "2018-01-01T00:00:00+00:00",
        "date_to_utc": f"{DATE_TO}T00:00:00+00:00",
        "files": files,
        "compatibility_raw_sha256": file_sha256(compatibility_raw_file),
    }
    manifest = {
        **seed,
        "generated_at_utc": now,
        "bundle_dir": str(bundle_dir.resolve()),
        "bundle_sha256": build_bundle_sha(seed),
        "compatibility_raw_file": str(compatibility_raw_file.resolve()),
        "terminal_path_arg": "",
        "server_arg": "",
        "portable": False,
        "snapshot": snapshot,
        "rule": "strategy_dedicated_raw_source_required; direct_mt5_api_required",
        "notes": "M15 数据受 Exness 服务器限制，仅 2022-05-17 起；M30/H2 自 2018 起。分段拉取避免单次请求上限。",
    }
    (bundle_dir / "mt5_history_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig"
    )
    (raw_dir / "raw_source_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig"
    )
    print(f"\nDONE: {len(files)} timeframes exported to {bundle_dir}")
    print(f"bundle_sha256={manifest['bundle_sha256']}")


if __name__ == "__main__":
    main()
