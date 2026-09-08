# -*- coding: utf-8 -*-
"""Evaluate stop-distance-only proxy policies on the fixed shared M15 SLOT1 mismatch set."""
from __future__ import annotations


import itertools
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


PROXIES = ["slot1_open", "slot1_high", "slot1_low", "slot1_close", "slot1_hlc3", "slot1_ohlc4"]


def render_markdown(summary: pd.DataFrame, detail: pd.DataFrame) -> str:
    lines = [
        "# 诊断型 Stop-Distance 代理扫描",
        "",
        "## 最优策略汇总",
        "",
        summary.head(12).to_markdown(index=False),
        "",
        "## 固定共享样本逐笔结果",
        "",
        detail.to_markdown(index=False),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    output_dir = VALIDATION_DIR / "mt5_log_session_diag" / "session_02"
    detail_path = output_dir / "stop_distance_proxy_policy_detail.csv"
    summary_path = output_dir / "stop_distance_proxy_policy_summary.csv"
    md_path = output_dir / "止损距离代理扫描_20260708.md"

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
        proxy_prices = {
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
        errors = {name: abs(abs(price - stop) - mt5_sd) for name, price in proxy_prices.items()}
        rows.append(
            {
                "anchor_time": anchor_time,
                "dir": key[1],
                "mt5_stop_dist": mt5_sd,
                "python_stop_dist": float(row["python_stop_dist_1dp"]),
                **errors,
            }
        )

    detail = pd.DataFrame(rows).sort_values("anchor_time").reset_index(drop=True)

    policy_rows = []
    for long_proxy, short_proxy in itertools.product(PROXIES, repeat=2):
        policy_errors = []
        for _, row in detail.iterrows():
            proxy = long_proxy if row["dir"] == "L" else short_proxy
            policy_errors.append(float(row[proxy]))
        s = pd.Series(policy_errors, dtype=float)
        policy_rows.append(
            {
                "long_proxy": long_proxy,
                "short_proxy": short_proxy,
                "count": int(len(s)),
                "mean_abs_error": round(float(s.mean()), 6),
                "median_abs_error": round(float(s.median()), 6),
                "max_abs_error": round(float(s.max()), 6),
            }
        )

    summary = pd.DataFrame(policy_rows).sort_values(
        ["mean_abs_error", "median_abs_error", "max_abs_error"],
        ascending=[True, True, True],
    ).reset_index(drop=True)

    export_csv(detail, detail_path)
    export_csv(summary, summary_path)
    write_text(md_path, render_markdown(summary, detail))
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
