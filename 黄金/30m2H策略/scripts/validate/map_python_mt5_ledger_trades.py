# -*- coding: utf-8 -*-
"""Map Python dynamic-risk trades to the fixed MT5 trade ledger.

This script is diagnostic only. It does not change strategy logic; it builds
strict and relaxed candidate mappings after applying the EA anchor offset.
"""
from __future__ import annotations


from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
INPUT_DIR = STRATEGY_DIR / "data" / "validation" / "dynamic_risk_alignment_magic0fix_20260713"
OUT_DIR = STRATEGY_DIR / "data" / "validation" / "mapped_trade_alignment_20260713"

EA_ALIGN_DELTA_MINUTES = 90
MAX_CANDIDATE_WINDOW_MINUTES = 7 * 24 * 60


@dataclass(frozen=True)
class SourceConfig:
    name: str
    filename: str


SOURCES = [
    SourceConfig("python_only", "python_only_dynamic_risk_trades.csv"),
    SourceConfig("python_mt5", "python_mt5_dynamic_risk_trades.csv"),
]

TIER_ORDER = {
    "exact_align90_all": 1,
    "nearby_60_all": 2,
    "nearby_180_all": 3,
    "nearby_1d_all": 4,
    "nearby_7d_all": 5,
    "nearby_60_trigger_relaxed": 6,
    "nearby_60_mode_relaxed": 7,
    "nearby_7d_trigger_relaxed": 8,
    "nearby_7d_mode_relaxed": 9,
    "same_dir_7d_unclassified": 99,
}

RELIABLE_TIERS = {
    "exact_align90_all",
    "nearby_60_all",
    "nearby_180_all",
    "nearby_1d_all",
    "nearby_7d_all",
}


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"S", "SELL", "-1"}:
        return "SELL"
    if text in {"B", "BUY", "L", "LONG", "1"}:
        return "BUY"
    return text


def parse_bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def coerce_numeric(frame: pd.DataFrame, columns: list[str]) -> None:
    for col in columns:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")


def load_python_trades(path: Path, source: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df.copy()
    df["source"] = source
    df["py_trade_id"] = [f"{source}_{i + 1:04d}" for i in range(len(df))]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["dir_norm"] = df["dir"].map(normalize_dir)
    coerce_numeric(
        df,
        [
            "entry",
            "stop",
            "stop_pts_spec",
            "stop_pts_mql5",
            "dynamic_total_lot",
            "stage1_lot",
            "stage2_lot",
            "stage3_lot",
            "stage1_dynamic_$",
            "stage2_dynamic_$",
            "stage3_dynamic_$",
            "dynamic_total_$",
            "balance_before",
            "balance_after",
        ],
    )
    stage1_sl = df["stage1_exit"].astype(str).str.contains("SL", regex=False)
    stage2_sl = df["stage2_exit"].astype(str).str.contains("SL", regex=False)
    stage3_sl = df["stage3_exit"].astype(str).str.contains("SL", regex=False)
    df["py_any_sl"] = stage1_sl | stage2_sl | stage3_sl
    df["py_all_sl"] = stage1_sl & stage2_sl & stage3_sl
    return df


def load_mt5_trades(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df.copy()
    df["mt5_trade_id"] = [f"mt5_{i + 1:04d}" for i in range(len(df))]
    df["signal_anchor_time"] = pd.to_datetime(df["signal_anchor_time"], errors="coerce")
    df["aligned_time"] = df["signal_anchor_time"] + pd.Timedelta(minutes=EA_ALIGN_DELTA_MINUTES)
    df["dir_norm"] = df["dir"].map(normalize_dir)
    df["any_sl_bool"] = df["any_sl"].map(parse_bool)
    df["all_sl_bool"] = df["all_sl"].map(parse_bool)
    coerce_numeric(df, ["stop_pts_spec", "net_profit", "balance_before", "balance_after", "stage_rows"])
    return df


def classify_candidate(abs_minutes: float, trigger_same: bool, mode_same: bool) -> str:
    if abs_minutes == 0 and trigger_same and mode_same:
        return "exact_align90_all"
    if abs_minutes <= 60 and trigger_same and mode_same:
        return "nearby_60_all"
    if abs_minutes <= 180 and trigger_same and mode_same:
        return "nearby_180_all"
    if abs_minutes <= 24 * 60 and trigger_same and mode_same:
        return "nearby_1d_all"
    if abs_minutes <= MAX_CANDIDATE_WINDOW_MINUTES and trigger_same and mode_same:
        return "nearby_7d_all"
    if abs_minutes <= 60 and mode_same:
        return "nearby_60_trigger_relaxed"
    if abs_minutes <= 60 and trigger_same:
        return "nearby_60_mode_relaxed"
    if abs_minutes <= MAX_CANDIDATE_WINDOW_MINUTES and mode_same:
        return "nearby_7d_trigger_relaxed"
    if abs_minutes <= MAX_CANDIDATE_WINDOW_MINUTES and trigger_same:
        return "nearby_7d_mode_relaxed"
    return "same_dir_7d_unclassified"


def build_candidates(py: pd.DataFrame, mt5: pd.DataFrame, source: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, mt5_row in mt5.iterrows():
        same_dir = py[py["dir_norm"] == mt5_row["dir_norm"]].copy()
        if same_dir.empty:
            continue
        same_dir["time_diff_minutes"] = (
            (same_dir["date"] - mt5_row["aligned_time"]).dt.total_seconds() / 60.0
        )
        same_dir["abs_time_diff_minutes"] = same_dir["time_diff_minutes"].abs()
        same_dir = same_dir[same_dir["abs_time_diff_minutes"] <= MAX_CANDIDATE_WINDOW_MINUTES]
        for _, py_row in same_dir.iterrows():
            trigger_same = str(py_row["trigger_family"]) == str(mt5_row["trigger_family"])
            mode_same = str(py_row["mode_family"]) == str(mt5_row["mode_family"])
            tier = classify_candidate(float(py_row["abs_time_diff_minutes"]), trigger_same, mode_same)
            rows.append(
                {
                    "source": source,
                    "match_tier": tier,
                    "tier_rank": TIER_ORDER[tier],
                    "is_reliable_tier": tier in RELIABLE_TIERS,
                    "py_trade_id": py_row["py_trade_id"],
                    "mt5_trade_id": mt5_row["mt5_trade_id"],
                    "py_date": py_row["date"],
                    "mt5_signal_anchor_time": mt5_row["signal_anchor_time"],
                    "mt5_aligned_time": mt5_row["aligned_time"],
                    "time_diff_minutes": round(float(py_row["time_diff_minutes"]), 6),
                    "abs_time_diff_minutes": round(float(py_row["abs_time_diff_minutes"]), 6),
                    "dir_norm": py_row["dir_norm"],
                    "trigger_same": trigger_same,
                    "mode_same": mode_same,
                    "py_trigger_family": py_row["trigger_family"],
                    "mt5_trigger_family": mt5_row["trigger_family"],
                    "py_mode_family": py_row["mode_family"],
                    "mt5_mode_family": mt5_row["mode_family"],
                    "py_mode": py_row["mode"],
                    "mt5_signal_src": mt5_row["signal_src"],
                    "py_variant": py_row["variant"],
                    "py_entry": py_row["entry"],
                    "py_stop": py_row["stop"],
                    "mt5_stop_pts_spec": mt5_row["stop_pts_spec"],
                    "py_stop_pts_spec": py_row["stop_pts_spec"],
                    "stop_pts_spec_diff": round(
                        float(py_row["stop_pts_spec"] - mt5_row["stop_pts_spec"]), 6
                    )
                    if pd.notna(py_row["stop_pts_spec"]) and pd.notna(mt5_row["stop_pts_spec"])
                    else "",
                    "py_profit": py_row["dynamic_total_$"],
                    "mt5_profit": mt5_row["net_profit"],
                    "profit_diff": round(float(py_row["dynamic_total_$"] - mt5_row["net_profit"]), 6)
                    if pd.notna(py_row["dynamic_total_$"]) and pd.notna(mt5_row["net_profit"])
                    else "",
                    "py_any_sl": bool(py_row["py_any_sl"]),
                    "mt5_any_sl": bool(mt5_row["any_sl_bool"]),
                    "py_all_sl": bool(py_row["py_all_sl"]),
                    "mt5_all_sl": bool(mt5_row["all_sl_bool"]),
                    "any_sl_same": bool(py_row["py_any_sl"]) == bool(mt5_row["any_sl_bool"]),
                    "all_sl_same": bool(py_row["py_all_sl"]) == bool(mt5_row["all_sl_bool"]),
                    "py_balance_after": py_row["balance_after"],
                    "mt5_balance_after": mt5_row["balance_after"],
                }
            )
    return pd.DataFrame(rows)


def greedy_unique_matches(candidates: pd.DataFrame) -> pd.DataFrame:
    if candidates.empty:
        return candidates.copy()
    eligible = candidates[candidates["match_tier"] != "same_dir_7d_unclassified"].copy()
    eligible["profit_abs_diff"] = pd.to_numeric(eligible["profit_diff"], errors="coerce").abs()
    eligible = eligible.sort_values(
        ["tier_rank", "abs_time_diff_minutes", "profit_abs_diff", "py_trade_id", "mt5_trade_id"],
        ascending=[True, True, True, True, True],
    )

    used_py: set[str] = set()
    used_mt5: set[str] = set()
    selected_rows: list[pd.Series] = []
    for _, row in eligible.iterrows():
        py_id = str(row["py_trade_id"])
        mt5_id = str(row["mt5_trade_id"])
        if py_id in used_py or mt5_id in used_mt5:
            continue
        selected_rows.append(row)
        used_py.add(py_id)
        used_mt5.add(mt5_id)
    if not selected_rows:
        return pd.DataFrame(columns=eligible.columns)
    return pd.DataFrame(selected_rows).reset_index(drop=True)


def summarize_candidates(candidates: pd.DataFrame) -> pd.DataFrame:
    if candidates.empty:
        return pd.DataFrame(columns=["source", "match_tier", "candidate_pairs", "mt5_with_candidate", "python_with_candidate"])
    grouped = candidates.groupby(["source", "match_tier"], dropna=False)
    rows = []
    for (source, tier), grp in grouped:
        rows.append(
            {
                "source": source,
                "match_tier": tier,
                "tier_rank": TIER_ORDER.get(str(tier), 999),
                "candidate_pairs": int(len(grp)),
                "mt5_with_candidate": int(grp["mt5_trade_id"].nunique()),
                "python_with_candidate": int(grp["py_trade_id"].nunique()),
            }
        )
    return pd.DataFrame(rows).sort_values(["source", "tier_rank", "match_tier"]).reset_index(drop=True)


def summarize_final(source: str, py: pd.DataFrame, mt5: pd.DataFrame, final_matches: pd.DataFrame) -> dict[str, object]:
    matched = len(final_matches)
    reliable = int(final_matches["is_reliable_tier"].sum()) if matched else 0
    py_profit = pd.to_numeric(final_matches.get("py_profit", pd.Series(dtype=float)), errors="coerce").sum()
    mt5_profit = pd.to_numeric(final_matches.get("mt5_profit", pd.Series(dtype=float)), errors="coerce").sum()
    any_sl_same = int(final_matches["any_sl_same"].sum()) if matched else 0
    all_sl_same = int(final_matches["all_sl_same"].sum()) if matched else 0
    return {
        "source": source,
        "python_trades": int(len(py)),
        "mt5_trades": int(len(mt5)),
        "matched_unique": int(matched),
        "reliable_tier_matched": reliable,
        "relaxed_tier_matched": int(matched - reliable),
        "python_unmatched": int(len(py) - final_matches["py_trade_id"].nunique()) if matched else int(len(py)),
        "mt5_unmatched": int(len(mt5) - final_matches["mt5_trade_id"].nunique()) if matched else int(len(mt5)),
        "matched_python_profit": round(float(py_profit), 6),
        "matched_mt5_profit": round(float(mt5_profit), 6),
        "matched_profit_diff": round(float(py_profit - mt5_profit), 6),
        "any_sl_same_count": any_sl_same,
        "all_sl_same_count": all_sl_same,
    }


def summarize_unmatched(
    source: str,
    side: str,
    frame: pd.DataFrame,
    trigger_col: str = "trigger_family",
    mode_col: str = "mode_family",
) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["source", "side", "trigger_family", "mode_family", "rows"])
    rows = (
        frame.groupby([trigger_col, mode_col], dropna=False)
        .size()
        .reset_index(name="rows")
        .rename(columns={trigger_col: "trigger_family", mode_col: "mode_family"})
    )
    rows["source"] = source
    rows["side"] = side
    return rows[["source", "side", "trigger_family", "mode_family", "rows"]].sort_values(
        ["source", "side", "rows", "trigger_family", "mode_family"],
        ascending=[True, True, False, True, True],
    )


def unmatched_frames(py: pd.DataFrame, mt5: pd.DataFrame, final_matches: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    matched_py = set(final_matches["py_trade_id"].astype(str)) if not final_matches.empty else set()
    matched_mt5 = set(final_matches["mt5_trade_id"].astype(str)) if not final_matches.empty else set()

    py_cols = [
        "py_trade_id",
        "date",
        "dir_norm",
        "trigger_family",
        "mode_family",
        "mode",
        "variant",
        "dynamic_total_$",
        "balance_after",
        "py_any_sl",
        "py_all_sl",
    ]
    mt5_cols = [
        "mt5_trade_id",
        "signal_anchor_time",
        "aligned_time",
        "dir_norm",
        "trigger_family",
        "mode_family",
        "signal_src",
        "net_profit",
        "balance_after",
        "any_sl_bool",
        "all_sl_bool",
    ]
    return (
        py[~py["py_trade_id"].astype(str).isin(matched_py)][py_cols].copy(),
        mt5[~mt5["mt5_trade_id"].astype(str).isin(matched_mt5)][mt5_cols].copy(),
    )


def simple_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_无数据_"
    return frame.to_markdown(index=False)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mt5 = load_mt5_trades(INPUT_DIR / "mt5_ledger_unique_signals.csv")

    all_candidate_frames: list[pd.DataFrame] = []
    all_final_frames: list[pd.DataFrame] = []
    all_unmatched_breakdowns: list[pd.DataFrame] = []
    summary_rows: list[dict[str, object]] = []

    for cfg in SOURCES:
        py = load_python_trades(INPUT_DIR / cfg.filename, cfg.name)
        candidates = build_candidates(py, mt5, cfg.name)
        final_matches = greedy_unique_matches(candidates)
        py_unmatched, mt5_unmatched = unmatched_frames(py, mt5, final_matches)

        export_csv(candidates, OUT_DIR / f"{cfg.name}_mt5_candidate_matches.csv")
        export_csv(final_matches, OUT_DIR / f"{cfg.name}_mt5_unique_matches.csv")
        export_csv(py_unmatched, OUT_DIR / f"{cfg.name}_unmatched_python_trades.csv")
        export_csv(mt5_unmatched, OUT_DIR / f"{cfg.name}_unmatched_mt5_trades.csv")

        all_candidate_frames.append(candidates)
        all_final_frames.append(final_matches)
        all_unmatched_breakdowns.append(summarize_unmatched(cfg.name, "python_unmatched", py_unmatched))
        all_unmatched_breakdowns.append(summarize_unmatched(cfg.name, "mt5_unmatched", mt5_unmatched))
        summary_rows.append(summarize_final(cfg.name, py, mt5, final_matches))

    all_candidates = pd.concat(all_candidate_frames, ignore_index=True) if all_candidate_frames else pd.DataFrame()
    all_final = pd.concat(all_final_frames, ignore_index=True) if all_final_frames else pd.DataFrame()

    candidate_summary = summarize_candidates(all_candidates)
    final_summary = pd.DataFrame(summary_rows)
    unmatched_breakdown = (
        pd.concat(all_unmatched_breakdowns, ignore_index=True)
        if all_unmatched_breakdowns
        else pd.DataFrame(columns=["source", "side", "trigger_family", "mode_family", "rows"])
    )

    export_csv(candidate_summary, OUT_DIR / "candidate_match_tier_summary.csv")
    export_csv(final_summary, OUT_DIR / "unique_match_summary.csv")
    export_csv(unmatched_breakdown, OUT_DIR / "unmatched_trigger_mode_summary.csv")
    export_csv(all_candidates, OUT_DIR / "all_candidate_matches.csv")
    export_csv(all_final, OUT_DIR / "all_unique_matches.csv")

    tier_counts = (
        all_final.groupby(["source", "match_tier"], dropna=False)
        .size()
        .reset_index(name="unique_matches")
        .sort_values(["source", "match_tier"])
        if not all_final.empty
        else pd.DataFrame(columns=["source", "match_tier", "unique_matches"])
    )
    export_csv(tier_counts, OUT_DIR / "unique_match_tier_counts.csv")

    report = [
        "# Python vs MT5 Ledger Mapped Trade Alignment",
        "",
        f"- EA anchor offset: MT5 `signal_anchor_time + {EA_ALIGN_DELTA_MINUTES} min`.",
        "- Final unique matching excludes `same_dir_7d_unclassified`; those rows remain only as candidate diagnostics.",
        "- Reliable tiers require direction + trigger family + mode family. Relaxed tiers are diagnostic, not final evidence of strategy parity.",
        "",
        "## Unique Match Summary",
        simple_table(final_summary),
        "",
        "## Candidate Tier Summary",
        simple_table(candidate_summary),
        "",
        "## Unique Match Tier Counts",
        simple_table(tier_counts),
        "",
        "## Unmatched Trigger/Mode Summary",
        simple_table(unmatched_breakdown),
        "",
        "## Key Interpretation",
        "- Exact key overlap was zero before anchor correction. After `+90min`, strict exact matches reappear but remain limited.",
        "- The remaining gap is not a ledger completeness issue: fixed MT5 ledger already reconciles to tester final balance.",
        "- The next repair target is signal construction alignment, especially M15/M30 trigger-family drift and post_n raw-parent rules.",
        "",
        "## Output Files",
        "- `candidate_match_tier_summary.csv`",
        "- `unique_match_summary.csv`",
        "- `all_candidate_matches.csv`",
        "- `all_unique_matches.csv`",
        "- `unmatched_trigger_mode_summary.csv`",
        "- `python_only_mt5_unique_matches.csv`",
        "- `python_mt5_mt5_unique_matches.csv`",
        "- `*_unmatched_python_trades.csv`",
        "- `*_unmatched_mt5_trades.csv`",
    ]
    write_text(OUT_DIR / "mapped_trade_alignment_report.md", "\n".join(report))


if __name__ == "__main__":
    main()
