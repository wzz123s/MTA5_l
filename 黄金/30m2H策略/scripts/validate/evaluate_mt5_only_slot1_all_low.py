# -*- coding: utf-8 -*-
"""Recheck MT5-only M15 SLOT1 samples with the diagnostic all-low stop-distance proxy."""
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
import _m15_early_entry_test as m15t  # type: ignore  # noqa: E402


SPEC_LO = 5.0
SPEC_HI = 35.0


def normalize_mode(mode: str) -> str:
    if mode.startswith("pre_cross"):
        return "pre_cross"
    if mode.startswith("cross"):
        return "cross"
    if mode.startswith("post_n"):
        return mode.split("_", 2)[0] if "_" in mode else mode
    return mode


def pick_candidate(raw_df: pd.DataFrame, anchor_time: pd.Timestamp, direction: str, mode_raw: str) -> tuple[pd.Series | None, str]:
    target_norm = normalize_mode(mode_raw)
    exact = raw_df[
        (pd.to_datetime(raw_df["date"]) == anchor_time)
        & (raw_df["dir"] == direction)
    ].copy()
    if not exact.empty:
        exact["mode_norm"] = exact["mode"].astype(str).map(normalize_mode)
        exact = exact[exact["mode_norm"] == target_norm]
        if not exact.empty:
            return exact.sort_values("date").iloc[0], "exact"

    future = raw_df[
        (pd.to_datetime(raw_df["date"]) > anchor_time)
        & (pd.to_datetime(raw_df["date"]) <= anchor_time + pd.Timedelta(hours=2))
        & (raw_df["dir"] == direction)
    ].copy()
    if not future.empty:
        future["mode_norm"] = future["mode"].astype(str).map(normalize_mode)
        future = future[future["mode_norm"] == target_norm]
        if not future.empty:
            return future.sort_values("date").iloc[0], "nearest_after"
    return None, "none"


def render_markdown(summary: pd.DataFrame, detail: pd.DataFrame) -> str:
    lines = [
        "# MT5独有 M15 SLOT1 all-low 复核",
        "",
        "## 汇总",
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
    detail_path = output_dir / "mt5_only_slot1_all_low_detail.csv"
    summary_path = output_dir / "mt5_only_slot1_all_low_summary.csv"
    md_path = output_dir / "mt5独有_slot1_all_low复核_20260708.md"

    df, h2, m15 = cb.load_market_context()
    q2_pass_set, q2_factor_map, _, _ = cb.h2t.early_precompute(h2, df, 2, False)
    raw_df, _ = cb.combo.build_candidate_frames(df, q2_pass_set, q2_factor_map)
    raw_df = raw_df.copy()
    raw_df["date"] = pd.to_datetime(raw_df["date"])

    m15 = m15.copy()
    m15["date"] = pd.to_datetime(m15["date"])

    mt5_only = pd.read_csv(
        VALIDATION_DIR / "mt5_log_session_diff" / "session_02" / "mt5_only_signals.csv",
        encoding="utf-8-sig",
    )
    mt5_only["anchor_time"] = pd.to_datetime(mt5_only["anchor_time"])
    mt5_only = mt5_only[mt5_only["trigger"] == "M15 SLOT1"].copy()

    rows: list[dict] = []
    for _, row in mt5_only.iterrows():
        anchor_time = pd.Timestamp(row["anchor_time"])
        direction = str(row["dir"])
        mode_raw = str(row["mode_raw"])
        mt5_sd = float(row["mt5_stop_dist"])

        candidate, candidate_source = pick_candidate(raw_df, anchor_time, direction, mode_raw)
        if candidate is None:
            rows.append(
                {
                    "anchor_time": anchor_time,
                    "dir": direction,
                    "mode_raw": mode_raw,
                    "mt5_stop_dist": mt5_sd,
                    "candidate_source": candidate_source,
                    "all_low_can_rescue": False,
                    "result_note": "未找到同模式候选",
                }
            )
            continue

        seg = m15t.m15_window(m15, anchor_time)
        if seg.empty:
            rows.append(
                {
                    "anchor_time": anchor_time,
                    "dir": direction,
                    "mode_raw": mode_raw,
                    "mt5_stop_dist": mt5_sd,
                    "candidate_source": candidate_source,
                    "candidate_time": pd.Timestamp(candidate["date"]),
                    "candidate_sd": float(candidate["sd"]),
                    "candidate_spec_reason": str(candidate["spec_reason"]),
                    "all_low_can_rescue": False,
                    "result_note": "缺少 slot1 K线",
                }
            )
            continue

        slot1 = seg.iloc[0]
        stop = float(candidate["stop"])
        slot1_low_sd = abs(float(slot1["low"]) - stop)
        is_long = direction == "L"
        same_side = bool(m15t.m15_same_side(slot1, is_long))
        slot1_low_pass = same_side and (SPEC_LO <= slot1_low_sd <= SPEC_HI)
        current_sd = float(candidate["sd"])
        current_reason = str(candidate["spec_reason"])
        current_pass = bool(candidate["spec_pass"])
        all_low_error = abs(slot1_low_sd - mt5_sd)
        current_error = abs(current_sd - mt5_sd)

        result_note = "仍不通过"
        if (not current_pass) and slot1_low_pass:
            result_note = "all-low 可把距离拉回有效区间"
        elif current_pass and all_low_pass:
            result_note = "当前已通过，all-low 仅更接近MT5距离"
        elif current_pass and (not slot1_low_pass):
            result_note = "当前通过，但 all-low 反而失败"

        rows.append(
            {
                "anchor_time": anchor_time,
                "dir": direction,
                "mode_raw": mode_raw,
                "mt5_stop_dist": mt5_sd,
                "candidate_source": candidate_source,
                "candidate_time": pd.Timestamp(candidate["date"]),
                "candidate_sd": round(current_sd, 6),
                "candidate_spec_pass": current_pass,
                "candidate_spec_reason": current_reason,
                "slot1_low_sd": round(slot1_low_sd, 6),
                "slot1_low_pass": slot1_low_pass,
                "slot1_low_error": round(all_low_error, 6),
                "current_error": round(current_error, 6),
                "all_low_can_rescue": bool((not current_pass) and slot1_low_pass),
                "result_note": result_note,
            }
        )

    detail = pd.DataFrame(rows).sort_values("anchor_time").reset_index(drop=True)
    summary = pd.DataFrame(
        [
            {
                "总样本数": int(len(detail)),
                "当前too_tight/too_wide样本数": int((~detail["candidate_spec_pass"].fillna(False)).sum()) if "candidate_spec_pass" in detail.columns else 0,
                "all_low可救回样本数": int(detail["all_low_can_rescue"].fillna(False).sum()) if "all_low_can_rescue" in detail.columns else 0,
                "完全无候选样本数": int((detail["candidate_source"] == "none").sum()) if "candidate_source" in detail.columns else 0,
            }
        ]
    )

    export_csv(detail, detail_path)
    export_csv(summary, summary_path)
    write_text(md_path, render_markdown(summary, detail))
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
