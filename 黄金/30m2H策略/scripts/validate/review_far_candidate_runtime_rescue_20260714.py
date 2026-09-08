# -*- coding: utf-8 -*-
"""Review the largest far-candidate runtime_rescue Python-unmatched cases."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"
OUT_DIR = VALIDATION_DIR / "far_candidate_runtime_rescue_review_20260714"

SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "python_h2_context_q2early"
FILTERED_TOP = VALIDATION_DIR / "duplicate_filtered_full_chain_review_20260714" / "filtered_top_python_unmatched.csv"
MT5_UNIQUE = VALIDATION_DIR / "dynamic_risk_alignment_shift90_metadatafix_close_retry_20260714" / "mt5_ledger_unique_signals.csv"
MT5_LEDGER = VALIDATION_DIR / "ea_stage2_trail_ledger_full_20260714" / "30m2H_strategy_trade_ledger.csv"
MT5_SIGNAL_LOG = (
    VALIDATION_DIR
    / "mt5_log_session_diff_v326_full_20260712_m30postn_strict_veto_initfix_ea_diag"
    / "session_03"
    / "mt5_signals.csv"
)

TARGETS = [
    {
        "stable_case": "far_runtime_rescue_20251021_postn6",
        "target_time": "2025-10-21 10:00:00",
        "dir_norm": "SELL",
        "trigger_family": "M15 SLOT1",
        "mode_family": "post_n",
        "mode": "post_n6",
        "original_trade_id": "python_mt5_0079",
    },
    {
        "stable_case": "far_runtime_rescue_20251017_precross",
        "target_time": "2025-10-17 11:00:00",
        "dir_norm": "SELL",
        "trigger_family": "M15 SLOT1",
        "mode_family": "pre_cross",
        "mode": "pre_cross",
        "original_trade_id": "python_mt5_0073",
    },
]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def to_dt(value: object) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT
    text = str(value).strip()
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        parsed = pd.to_datetime(text.replace(".", "-"), errors="coerce")
    return parsed


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"S", "SELL", "-1"}:
        return "SELL"
    if text in {"B", "BUY", "L", "LONG", "1"}:
        return "BUY"
    return text


def mode_family(value: object) -> str:
    text = str(value)
    if "post_n" in text:
        return "post_n"
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    return text


def trigger_family_from_variant(value: object) -> str:
    text = str(value)
    if any(tag in text for tag in ["slot1", "replace", "rescue"]):
        return "M15 SLOT1"
    return "M30 CLOSE"


def signal_layer(path: Path, layer: str) -> pd.DataFrame:
    df = read_csv(path).copy()
    df["layer"] = layer
    df["date_dt"] = df["date"].map(to_dt)
    df["dir_norm"] = df["dir"].map(normalize_dir)
    if "trigger" not in df.columns:
        df["trigger"] = ""
    if "trigger_family" not in df.columns:
        if "variant" not in df.columns:
            df["variant"] = ""
        df["trigger_family"] = df["variant"].map(trigger_family_from_variant)
    df["mode_family"] = df["mode"].map(mode_family)
    return df


def load_signal_layers() -> pd.DataFrame:
    frames = [
        signal_layer(SIGNAL_DIR / "raw_candidates.csv", "raw"),
        signal_layer(SIGNAL_DIR / "候选信号_Layer1_Layer2通过.csv", "accepted"),
        signal_layer(SIGNAL_DIR / "最终信号_Layer3入选.csv", "picked"),
        signal_layer(SIGNAL_DIR / "执行交易_Stage结果.csv", "stage"),
    ]
    return pd.concat(frames, ignore_index=True, sort=False)


def load_mt5_unique() -> pd.DataFrame:
    df = read_csv(MT5_UNIQUE).copy()
    df["signal_anchor_dt"] = df["signal_anchor_time"].map(to_dt)
    df["aligned_dt"] = df["signal_anchor_dt"] + pd.Timedelta(minutes=90)
    df["dir_norm"] = df["dir"].map(normalize_dir)
    return df


def load_mt5_ledger() -> pd.DataFrame:
    df = read_csv(MT5_LEDGER).copy()
    df["open_dt"] = df["open_time"].map(to_dt)
    df["exit_dt"] = df["exit_time"].map(to_dt)
    df["signal_anchor_dt"] = df["signal_anchor_time"].map(to_dt)
    df["aligned_dt"] = df["signal_anchor_dt"] + pd.Timedelta(minutes=90)
    df["dir_norm"] = df["dir"].map(normalize_dir)
    return df


def load_mt5_signal_log() -> pd.DataFrame:
    if not MT5_SIGNAL_LOG.exists():
        return pd.DataFrame()
    df = read_csv(MT5_SIGNAL_LOG).copy()
    for col in ["anchor_time", "entry_time", "log_time"]:
        if col in df.columns:
            df[f"{col}_dt"] = df[col].map(to_dt)
    if "dir" in df.columns:
        df["dir_norm"] = df["dir"].map(normalize_dir)
    return df


def window_rows(frame: pd.DataFrame, time_col: str, target: pd.Timestamp, minutes: int) -> pd.DataFrame:
    cur = frame.copy()
    cur["minutes_from_target"] = (cur[time_col] - target).dt.total_seconds() / 60.0
    return cur[cur["minutes_from_target"].abs() <= minutes].sort_values("minutes_from_target").reset_index(drop=True)


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_No rows._"
    cols = [col for col in columns if col in frame.columns]
    if not cols:
        return "_No columns._"
    return frame[cols].to_markdown(index=False)


def classify_case(py_target: pd.Series, mt5_near: pd.DataFrame, active: pd.DataFrame) -> tuple[str, str]:
    if not active.empty:
        return (
            "mt5_position_occupancy_candidate",
            "MT5 had active positions at the raw target time; review whether Python max-position/lifecycle simulation admits extra rescue trades.",
        )
    same_dir_near = mt5_near[mt5_near["dir_norm"] == py_target["dir_norm"]]
    if same_dir_near.empty:
        return (
            "python_runtime_rescue_without_mt5_nearby_signal",
            "No same-direction MT5 signal is near this target; review Python runtime_rescue admission or mark accounting-only.",
        )
    return (
        "mt5_nearby_signal_family_or_timing_drift",
        "A same-direction MT5 signal exists nearby but not as a close same trigger/mode match; inspect trigger family and timing.",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    signals = load_signal_layers()
    mt5_unique = load_mt5_unique()
    ledger = load_mt5_ledger()
    mt5_log = load_mt5_signal_log()
    filtered_top = read_csv(FILTERED_TOP)

    summary_rows = []
    signal_windows = []
    mt5_windows = []
    active_rows = []

    for target_def in TARGETS:
        target_time = pd.Timestamp(target_def["target_time"])
        raw_time = target_time - pd.Timedelta(minutes=90)
        py_rows = filtered_top[
            (filtered_top["date"].astype(str) == target_def["target_time"])
            & (filtered_top["dir_norm"].astype(str) == target_def["dir_norm"])
            & (filtered_top["trigger_family"].astype(str) == target_def["trigger_family"])
            & (filtered_top["mode_family"].astype(str) == target_def["mode_family"])
        ].copy()
        py_target = py_rows.iloc[0] if not py_rows.empty else pd.Series(target_def)

        sig_win = window_rows(signals[signals["dir_norm"] == target_def["dir_norm"]], "date_dt", target_time, 240)
        sig_win.insert(0, "stable_case", target_def["stable_case"])
        signal_windows.append(sig_win)

        mt5_near = window_rows(mt5_unique, "aligned_dt", target_time, 7 * 24 * 60)
        mt5_near.insert(0, "stable_case", target_def["stable_case"])
        mt5_windows.append(mt5_near)

        active = ledger[(ledger["open_dt"] <= raw_time) & (ledger["exit_dt"] >= raw_time)].copy()
        active.insert(0, "stable_case", target_def["stable_case"])
        active["target_time"] = target_time
        active["raw_target_time"] = raw_time
        active_rows.append(active)

        log_near_count = 0
        if not mt5_log.empty and "anchor_time_dt" in mt5_log.columns:
            log_near_count = int(len(window_rows(mt5_log, "anchor_time_dt", raw_time, 240)))

        classification, next_action = classify_case(py_target, mt5_near, active)
        same_trigger_mode_240 = mt5_near[
            (mt5_near["dir_norm"] == target_def["dir_norm"])
            & (mt5_near["trigger_family"].astype(str) == target_def["trigger_family"])
            & (mt5_near["mode_family"].astype(str) == target_def["mode_family"])
            & (mt5_near["minutes_from_target"].abs() <= 240)
        ]
        summary_rows.append(
            {
                "stable_case": target_def["stable_case"],
                "original_trade_id": target_def["original_trade_id"],
                "target_time": target_time,
                "raw_target_time_minus90": raw_time,
                "dir_norm": target_def["dir_norm"],
                "trigger_family": target_def["trigger_family"],
                "mode_family": target_def["mode_family"],
                "mode": target_def["mode"],
                "filtered_trade_profit": py_target.get("dynamic_total_$", ""),
                "python_signal_rows_within_240m": int(len(sig_win)),
                "python_picked_rows_within_240m": int((sig_win["layer"] == "picked").sum()) if not sig_win.empty else 0,
                "mt5_unique_rows_within_7d": int(len(mt5_near)),
                "mt5_same_trigger_mode_rows_within_240m": int(len(same_trigger_mode_240)),
                "mt5_active_stage_rows_at_raw_time": int(len(active)),
                "mt5_active_unique_signal_anchors": int(active["signal_anchor_time"].nunique()) if not active.empty else 0,
                "mt5_log_rows_within_240m_raw": log_near_count,
                "classification": classification,
                "next_action": next_action,
            }
        )

    summary = pd.DataFrame(summary_rows)
    signal_window = pd.concat(signal_windows, ignore_index=True) if signal_windows else pd.DataFrame()
    mt5_window = pd.concat(mt5_windows, ignore_index=True) if mt5_windows else pd.DataFrame()
    active_all = pd.concat(active_rows, ignore_index=True) if active_rows else pd.DataFrame()

    export_csv(summary, OUT_DIR / "far_candidate_runtime_rescue_summary.csv")
    export_csv(signal_window, OUT_DIR / "far_candidate_python_signal_windows.csv")
    export_csv(mt5_window, OUT_DIR / "far_candidate_mt5_signal_windows.csv")
    export_csv(active_all, OUT_DIR / "far_candidate_mt5_active_positions.csv")

    report = [
        "# Far Candidate Runtime Rescue Review 20260714",
        "",
        "## Summary",
        "",
        markdown_table(
            summary,
            [
                "stable_case",
                "target_time",
                "mode",
                "filtered_trade_profit",
                "python_picked_rows_within_240m",
                "mt5_same_trigger_mode_rows_within_240m",
                "mt5_active_stage_rows_at_raw_time",
                "classification",
            ],
        ),
        "",
        "## Active MT5 Positions",
        "",
        markdown_table(
            active_all,
            [
                "stable_case",
                "raw_target_time",
                "signal_anchor_time",
                "stage",
                "dir",
                "trigger_tag",
                "signal_src",
                "open_time",
                "exit_time",
                "net_profit",
            ],
        ),
        "",
        "## Decision",
        "",
        "- These rows are no longer ordinary unique-match conflicts; they are far-candidate Python runtime_rescue admissions.",
        "- If MT5 had active positions at the raw target time, the next repair candidate is Python lifecycle/max-position simulation, not EA price-side behavior.",
        "- If no MT5 position or signal evidence exists, keep the row in Python-only signal review before changing strategy generation.",
    ]
    write_text(OUT_DIR / "far_candidate_runtime_rescue_review.md", "\n".join(report))
    write_text(OUT_DIR / "README.md", "# far_candidate_runtime_rescue_review_20260714\n\nReview of largest far-candidate Python-MT5 runtime_rescue unmatched cases.")

    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
