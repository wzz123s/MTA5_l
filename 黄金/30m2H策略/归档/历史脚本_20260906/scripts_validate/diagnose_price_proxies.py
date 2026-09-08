# -*- coding: utf-8 -*-
"""Diagnose which entry-price proxy is closest to MT5 stop distances."""
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

from strategy_30m2h_common import VALIDATION_DIR, ensure_dirs, export_csv, write_text  # noqa: E402
import _current_baseline as cb  # type: ignore  # noqa: E402


def render_markdown(detail: pd.DataFrame, summary: pd.DataFrame) -> str:
    lines = [
        "# 价格代理诊断",
        "",
        "## 最优代理计数",
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
    ensure_dirs()
    detail_path = VALIDATION_DIR / "mt5_log_session_diag" / "session_02" / "price_proxy_detail.csv"
    summary_path = VALIDATION_DIR / "mt5_log_session_diag" / "session_02" / "price_proxy_summary.csv"
    md_path = VALIDATION_DIR / "mt5_log_session_diag" / "session_02" / "价格代理诊断_20260708.md"

    df, _, m15 = cb.load_market_context()
    result = cb.summarize_strategy(ea_executable_diag=True)
    picked = result["picked"].copy()
    picked["date"] = pd.to_datetime(picked["date"])
    picked_map = {(pd.Timestamp(row["date"]), row["dir"]): row for _, row in picked.iterrows()}

    mismatch = pd.read_csv(
        VALIDATION_DIR / "mt5_log_session_diff" / "session_02" / "shared_mismatch.csv",
        encoding="utf-8-sig",
    )
    mismatch["anchor_time_mt5"] = pd.to_datetime(mismatch["anchor_time_mt5"])

    rows: list[dict] = []
    for _, row in mismatch.iterrows():
        key = (pd.Timestamp(row["anchor_time_mt5"]), row["dir_mt5"])
        meta = picked_map.get(key)
        if meta is None:
            continue

        stop = float(meta["stop"])
        trigger = str(row["trigger_mt5"])
        mt5_sd = float(row["mt5_stop_dist"])
        anchor_time = key[0]
        direction = key[1]

        if trigger == "M30 CLOSE":
            m30_bar = df[pd.to_datetime(df["date"]) == anchor_time].iloc[0]
            proxies = {
                "m30_close": float(m30_bar["close"]),
                "m30_open": float(m30_bar["open"]),
                "m30_hlc3": (float(m30_bar["high"]) + float(m30_bar["low"]) + float(m30_bar["close"])) / 3.0,
                "m30_ohlc4": (
                    float(m30_bar["open"]) + float(m30_bar["high"]) + float(m30_bar["low"]) + float(m30_bar["close"])
                )
                / 4.0,
            }
        else:
            seg = m15[
                (pd.to_datetime(m15["date"]) > anchor_time - pd.Timedelta(minutes=30))
                & (pd.to_datetime(m15["date"]) <= anchor_time)
            ].sort_values("date")
            if seg.empty:
                continue
            m15_bar = seg.iloc[0]
            m30_anchor = df[pd.to_datetime(df["date"]) == anchor_time].iloc[0]
            proxies = {
                "slot1_close": float(m15_bar["close"]),
                "slot1_open": float(m15_bar["open"]),
                "slot1_high": float(m15_bar["high"]),
                "slot1_low": float(m15_bar["low"]),
                "slot1_hlc3": (float(m15_bar["high"]) + float(m15_bar["low"]) + float(m15_bar["close"])) / 3.0,
                "slot1_ohlc4": (
                    float(m15_bar["open"]) + float(m15_bar["high"]) + float(m15_bar["low"]) + float(m15_bar["close"])
                )
                / 4.0,
                "m30_anchor_close": float(m30_anchor["close"]),
            }

        errors = {name: abs(abs(price - stop) - mt5_sd) for name, price in proxies.items()}
        best_proxy = min(errors, key=errors.get)
        rows.append(
            {
                "anchor_time": anchor_time,
                "trigger": trigger,
                "dir": direction,
                "mt5_stop_dist": mt5_sd,
                "python_stop_dist": float(row["python_stop_dist_1dp"]),
                "best_proxy": best_proxy,
                "best_error": errors[best_proxy],
                **errors,
            }
        )

    detail = pd.DataFrame(rows)
    summary = (
        detail.groupby(["trigger", "best_proxy"], as_index=False)
        .size()
        .rename(columns={"size": "笔数"})
        .sort_values(["trigger", "笔数"], ascending=[True, False])
        .reset_index(drop=True)
    )

    export_csv(detail, detail_path)
    export_csv(summary, summary_path)
    write_text(md_path, render_markdown(detail, summary))
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
