# -*- coding: utf-8 -*-
"""Inspect stop-source construction for MT5-only M15 SLOT1 samples."""
from __future__ import annotations


import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
ROOT_SCRIPTS_DIR = ROOT / "scripts"

sys.path.insert(0, str(STRATEGY_SCRIPTS_DIR))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT_SCRIPTS_DIR))

from strategy_30m2h_common import VALIDATION_DIR, export_csv, write_text  # noqa: E402
import _current_baseline as cb  # type: ignore  # noqa: E402
from evaluate_mt5_only_slot1_all_low import pick_candidate, normalize_mode  # noqa: E402


def prior_segment_bounds(i: int, direction: np.ndarray) -> tuple[int | None, int | None]:
    k = i - 1
    while k >= 0 and direction[k] not in ("good", "bad"):
        k -= 1
    if k < 0:
        return None, None
    return k, i - 1


def render_markdown(detail: pd.DataFrame) -> str:
    lines = [
        "# MT5独有 M15 SLOT1 stop 源头复核",
        "",
        "## 逐笔结果",
        "",
        detail.to_markdown(index=False),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    output_dir = VALIDATION_DIR / "mt5_log_session_diag" / "session_02"
    detail_path = output_dir / "mt5_only_slot1_stop_source_detail.csv"
    md_path = output_dir / "mt5独有_slot1_stop源头复核_20260708.md"

    df, h2, _ = cb.load_market_context()
    q2_pass_set, q2_factor_map, _, _ = cb.h2t.early_precompute(h2, df, 2, False)
    raw_df, _ = cb.combo.build_candidate_frames(df, q2_pass_set, q2_factor_map)
    raw_df = raw_df.copy()
    raw_df["date"] = pd.to_datetime(raw_df["date"])

    df = df.copy().reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    direction = df["方向"].values
    sma13 = df["SMA_13"].values

    mt5_only = pd.read_csv(
        VALIDATION_DIR / "mt5_log_session_diff" / "session_02" / "mt5_only_signals.csv",
        encoding="utf-8-sig",
    )
    mt5_only["anchor_time"] = pd.to_datetime(mt5_only["anchor_time"])
    mt5_only = mt5_only[mt5_only["trigger"] == "M15 SLOT1"].copy()

    rows: list[dict] = []
    for _, row in mt5_only.iterrows():
        anchor_time = pd.Timestamp(row["anchor_time"])
        direction_side = str(row["dir"])
        mode_raw = str(row["mode_raw"])
        candidate, source = pick_candidate(raw_df, anchor_time, direction_side, mode_raw)
        if candidate is None:
            rows.append(
                {
                    "anchor_time": anchor_time,
                    "dir": direction_side,
                    "mode_raw": mode_raw,
                    "candidate_source": source,
                    "result_note": "未找到候选",
                }
            )
            continue

        i = int(candidate["i"])
        is_long = direction_side == "L"
        seg_start_i, seg_end_i = prior_segment_bounds(i, direction)
        if seg_start_i is None:
            rows.append(
                {
                    "anchor_time": anchor_time,
                    "dir": direction_side,
                    "mode_raw": mode_raw,
                    "candidate_source": source,
                    "candidate_time": pd.Timestamp(candidate["date"]),
                    "candidate_stop": float(candidate["stop"]),
                    "result_note": "无法找到 prior segment",
                }
            )
            continue

        seg = sma13[seg_start_i:i]
        seg = seg[~np.isnan(seg)]
        seg_min = float(np.nanmin(seg)) if len(seg) else np.nan
        seg_max = float(np.nanmax(seg)) if len(seg) else np.nan
        expected_stop = seg_min if is_long else seg_max
        rows.append(
            {
                "anchor_time": anchor_time,
                "dir": direction_side,
                "mode_raw": mode_raw,
                "candidate_source": source,
                "candidate_time": pd.Timestamp(candidate["date"]),
                "candidate_entry": round(float(candidate["entry"]), 6),
                "candidate_stop": round(float(candidate["stop"]), 6),
                "candidate_sd": round(float(candidate["sd"]), 6),
                "candidate_spec_reason": str(candidate["spec_reason"]),
                "candidate_mode_norm": normalize_mode(str(candidate["mode"])),
                "seg_start_time": pd.Timestamp(df.iloc[seg_start_i]["date"]),
                "seg_end_time": pd.Timestamp(df.iloc[seg_end_i]["date"]),
                "seg_len": int(seg_end_i - seg_start_i + 1),
                "seg_sma13_min": round(seg_min, 6),
                "seg_sma13_max": round(seg_max, 6),
                "expected_stop_by_formula": round(expected_stop, 6),
                "stop_matches_formula": abs(float(candidate["stop"]) - expected_stop) < 1e-9,
                "result_note": "prior_segment_stop=max(SMA13)" if not is_long else "prior_segment_stop=min(SMA13)",
            }
        )

    detail = pd.DataFrame(rows).sort_values("anchor_time").reset_index(drop=True)
    export_csv(detail, detail_path)
    write_text(md_path, render_markdown(detail))
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
