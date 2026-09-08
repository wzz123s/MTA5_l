# -*- coding: utf-8 -*-
"""Evaluate M15 SLOT1 price-proxy variants against cached MT5 shared mismatches."""
from __future__ import annotations


import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
ROOT_SCRIPTS_DIR = ROOT / "scripts"

sys.path.insert(0, str(STRATEGY_SCRIPTS_DIR))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT_SCRIPTS_DIR))

from strategy_30m2h_common import VALIDATION_DIR, export_csv, write_text  # noqa: E402
import _current_baseline as cb  # type: ignore  # noqa: E402


def render_markdown(summary: pd.DataFrame, detail: pd.DataFrame) -> str:
    lines = [
        "# M15 SLOT1 价格代理变体诊断",
        "",
        "## 代理汇总",
        "",
        summary.to_markdown(index=False),
        "",
        "## 逐笔结果",
        "",
        detail.to_markdown(index=False),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    output_dir = VALIDATION_DIR / "mt5_log_session_diag" / "session_02"
    detail_path = output_dir / "slot1_proxy_variant_detail.csv"
    summary_path = output_dir / "slot1_proxy_variant_summary.csv"
    md_path = output_dir / "slot1代理变体诊断_20260708.md"

    _, _, m15 = cb.load_market_context()
    m15["date"] = pd.to_datetime(m15["date"])

    result = cb.summarize_strategy(
        spec_lo=5.0,
        spec_hi=35.0,
        top_pct=30.0,
        bias55_threshold=3.0,
        stage1_r=1.2,
        stage2_trail_r=2.0,
        stage2_force_r=3.0,
        ea_executable_diag=True,
    )
    picked = result["picked"].copy()
    picked["date"] = pd.to_datetime(picked["date"])
    picked_map = {(pd.Timestamp(row["date"]), row["dir"]): row for _, row in picked.iterrows()}

    mismatch = pd.read_csv(
        VALIDATION_DIR / "mt5_log_session_diff" / "session_02" / "shared_mismatch.csv",
        encoding="utf-8-sig",
    )
    mismatch["anchor_time_mt5"] = pd.to_datetime(mismatch["anchor_time_mt5"])
    mismatch = mismatch[mismatch["trigger_mt5"] == "M15 SLOT1"].copy()

    rows: list[dict] = []
    for _, row in mismatch.iterrows():
        key = (pd.Timestamp(row["anchor_time_mt5"]), row["dir_mt5"])
        meta = picked_map.get(key)
        if meta is None:
            continue

        anchor_time = key[0]
        stop = float(meta["stop"])
        mt5_sd = float(row["mt5_stop_dist"])
        seg = m15[
            (m15["date"] > anchor_time - pd.Timedelta(minutes=30))
            & (m15["date"] <= anchor_time)
        ].sort_values("date")
        if seg.empty:
            continue
        slot1 = seg.iloc[0]
        proxies = {
            "slot1_open": float(slot1["open"]),
            "slot1_high": float(slot1["high"]),
            "slot1_low": float(slot1["low"]),
            "slot1_close": float(slot1["close"]),
            "slot1_hlc3": (float(slot1["high"]) + float(slot1["low"]) + float(slot1["close"])) / 3.0,
            "slot1_ohlc4": (
                float(slot1["open"]) + float(slot1["high"]) + float(slot1["low"]) + float(slot1["close"])
            )
            / 4.0,
        }
        errors = {name: abs(abs(price - stop) - mt5_sd) for name, price in proxies.items()}
        best_proxy = min(errors, key=errors.get)
        rows.append(
            {
                "anchor_time": anchor_time,
                "dir": key[1],
                "python_variant": str(meta.get("variant", "")),
                "python_entry_time": pd.Timestamp(meta["entry_time"]),
                "python_stop": stop,
                "mt5_stop_dist": mt5_sd,
                "python_stop_dist": float(row["python_stop_dist_1dp"]),
                "best_proxy": best_proxy,
                **errors,
            }
        )

    detail = pd.DataFrame(rows).sort_values("anchor_time").reset_index(drop=True)
    proxy_cols = [
        "slot1_open",
        "slot1_high",
        "slot1_low",
        "slot1_close",
        "slot1_hlc3",
        "slot1_ohlc4",
    ]

    summary_rows = []
    for proxy in proxy_cols:
        if proxy not in detail.columns:
            continue
        series = detail[proxy].astype(float)
        summary_rows.append(
            {
                "proxy": proxy,
                "count": int(series.notna().sum()),
                "mean_abs_error": round(float(series.mean()), 6),
                "median_abs_error": round(float(series.median()), 6),
                "max_abs_error": round(float(series.max()), 6),
            }
        )
    summary = pd.DataFrame(summary_rows).sort_values(
        ["mean_abs_error", "median_abs_error", "max_abs_error"],
        ascending=[True, True, True],
    ).reset_index(drop=True)

    export_csv(detail, detail_path)
    export_csv(summary, summary_path)
    write_text(md_path, render_markdown(summary, detail))
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
