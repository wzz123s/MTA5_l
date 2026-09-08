# -*- coding: utf-8 -*-
"""Replay M30 post_n counter/anchor alternatives for MT5-vs-Python cases."""
from __future__ import annotations


import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
ALIGN_DIR = DATA_DIR / "validation" / "m30_postn_alignment_diag_20260713"
OUT_DIR = DATA_DIR / "validation" / "postn_counter_anchor_replay_20260713"

M30_FILES = {
    "python_only": PROCESSED_DIR / "m30_standardized.csv",
    "python_mt5": PROCESSED_DIR / "m30_mt5.csv",
}


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def parse_post_n(value: object) -> float:
    match = re.search(r"post_n(\d+)", str(value))
    if not match:
        return math.nan
    return float(match.group(1))


def signed_post_n(direction: object, n_value: object) -> float:
    try:
        number = float(n_value)
    except Exception:
        return math.nan
    if math.isnan(number):
        return math.nan
    direction_text = str(direction).strip().upper()
    return number if direction_text == "BUY" else -number


def safe_timestamp(value: object) -> pd.Timestamp | pd.NaT:
    return pd.to_datetime(value, errors="coerce")


def load_m30(source: str) -> pd.DataFrame:
    path = M30_FILES[source]
    df = pd.read_csv(path, encoding="utf-8-sig")
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["merged_post_cross_n"] = pd.to_numeric(df["merged_post_cross_n"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").drop_duplicates("date", keep="last")
    return df.set_index("date", drop=False)


def counter_at(m30: pd.DataFrame, timestamp: pd.Timestamp | pd.NaT) -> float:
    if pd.isna(timestamp):
        return math.nan
    if timestamp not in m30.index:
        return math.nan
    value = m30.at[timestamp, "merged_post_cross_n"]
    try:
        return float(value)
    except Exception:
        return math.nan


def matches_counter(counter: float, expected: float) -> bool:
    if math.isnan(counter) or math.isnan(expected):
        return False
    return int(counter) == int(expected)


def abs_matches_counter(counter: float, expected: float) -> bool:
    if math.isnan(counter) or math.isnan(expected):
        return False
    return abs(int(counter)) == abs(int(expected))


def bool_sum(frame: pd.DataFrame, column: str) -> int:
    if column not in frame.columns or frame.empty:
        return 0
    return int(frame[column].fillna(False).astype(bool).sum())


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def build_details() -> pd.DataFrame:
    align = pd.read_csv(ALIGN_DIR / "m30_postn_alignment_details.csv", encoding="utf-8-sig")
    target = align[(align["side"] == "mt5_m30_postn")].copy()
    m30_by_source = {source: load_m30(source) for source in M30_FILES}

    rows: list[dict[str, object]] = []
    for _, row in target.iterrows():
        source = str(row["source"])
        m30 = m30_by_source[source]
        aligned_time = safe_timestamp(row.get("aligned_time"))
        nearest_py_time = safe_timestamp(row.get("nearest_py_date"))
        mt5_n = row.get("mt5_post_n")
        py_n = row.get("nearest_py_post_n")
        mt5_signed = signed_post_n(row.get("dir_norm"), mt5_n)
        py_signed = signed_post_n(row.get("dir_norm"), py_n)

        counter_t_minus_30 = counter_at(m30, aligned_time - pd.Timedelta(minutes=30))
        counter_t = counter_at(m30, aligned_time)
        counter_t_plus_30 = counter_at(m30, aligned_time + pd.Timedelta(minutes=30))
        counter_t_plus_60 = counter_at(m30, aligned_time + pd.Timedelta(minutes=60))
        counter_py_time = counter_at(m30, nearest_py_time)

        mt5_matches_t = matches_counter(counter_t, mt5_signed)
        mt5_matches_prev = matches_counter(counter_t_minus_30, mt5_signed)
        mt5_matches_next = matches_counter(counter_t_plus_30, mt5_signed)
        py_matches_t = matches_counter(counter_t, py_signed)
        py_matches_next = matches_counter(counter_t_plus_30, py_signed)
        py_matches_py_time = matches_counter(counter_py_time, py_signed)

        abs_mt5_matches_t = abs_matches_counter(counter_t, mt5_signed)
        abs_py_matches_next = abs_matches_counter(counter_t_plus_30, py_signed)
        abs_py_matches_py_time = abs_matches_counter(counter_py_time, py_signed)

        observed_30min_n_plus_1 = (
            row.get("nearest_py_signed_minutes") == 30
            and row.get("postn_diff") == -1
        )
        next_bar_explains_numbering = bool(observed_30min_n_plus_1 and abs_mt5_matches_t and abs_py_matches_next)
        py_trade_time_explains_numbering = bool(observed_30min_n_plus_1 and abs_mt5_matches_t and abs_py_matches_py_time)

        rows.append(
            {
                "source": source,
                "mt5_trade_id": row.get("mt5_trade_id"),
                "match_status": row.get("match_status"),
                "cause_bucket": row.get("cause_bucket"),
                "layer_hint": row.get("layer_hint"),
                "aligned_time": aligned_time,
                "nearest_py_date": nearest_py_time,
                "nearest_py_signed_minutes": row.get("nearest_py_signed_minutes"),
                "dir_norm": row.get("dir_norm"),
                "mt5_signal_src": row.get("mt5_signal_src"),
                "mt5_post_n": mt5_n,
                "nearest_py_mode": row.get("nearest_py_mode"),
                "nearest_py_post_n": py_n,
                "postn_diff": row.get("postn_diff"),
                "counter_t_minus_30": counter_t_minus_30,
                "counter_t": counter_t,
                "counter_t_plus_30": counter_t_plus_30,
                "counter_t_plus_60": counter_t_plus_60,
                "counter_py_time": counter_py_time,
                "mt5_matches_counter_t_signed": mt5_matches_t,
                "mt5_matches_counter_t_minus_30_signed": mt5_matches_prev,
                "mt5_matches_counter_t_plus_30_signed": mt5_matches_next,
                "py_matches_counter_t_signed": py_matches_t,
                "py_matches_counter_t_plus_30_signed": py_matches_next,
                "py_matches_counter_py_time_signed": py_matches_py_time,
                "mt5_matches_counter_t_abs": abs_mt5_matches_t,
                "py_matches_counter_t_plus_30_abs": abs_py_matches_next,
                "py_matches_counter_py_time_abs": abs_py_matches_py_time,
                "observed_30min_n_plus_1": observed_30min_n_plus_1,
                "next_bar_explains_numbering": next_bar_explains_numbering,
                "py_trade_time_explains_numbering": py_trade_time_explains_numbering,
            }
        )

    return pd.DataFrame(rows)


def build_summary(details: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for source, group in details.groupby("source", dropna=False):
        observed = group[group["observed_30min_n_plus_1"]]
        unmatched = group[group["match_status"] == "unmatched"]
        reliable = group[group["match_status"] == "reliable_matched"]
        rows.extend(
            [
                {"source": source, "scope": "all_mt5_m30_postn", "metric": "rows", "value": int(len(group))},
                {
                    "source": source,
                    "scope": "all_mt5_m30_postn",
                    "metric": "counter_t_matches_mt5_abs",
                    "value": bool_sum(group, "mt5_matches_counter_t_abs"),
                },
                {
                    "source": source,
                    "scope": "all_mt5_m30_postn",
                    "metric": "counter_t_plus_30_matches_py_abs",
                    "value": bool_sum(group, "py_matches_counter_t_plus_30_abs"),
                },
                {
                    "source": source,
                    "scope": "observed_30min_n_plus_1",
                    "metric": "rows",
                    "value": int(len(observed)),
                },
                {
                    "source": source,
                    "scope": "observed_30min_n_plus_1",
                    "metric": "counter_t_matches_mt5_abs",
                    "value": bool_sum(observed, "mt5_matches_counter_t_abs"),
                },
                {
                    "source": source,
                    "scope": "observed_30min_n_plus_1",
                    "metric": "counter_t_plus_30_matches_py_abs",
                    "value": bool_sum(observed, "py_matches_counter_t_plus_30_abs"),
                },
                {
                    "source": source,
                    "scope": "observed_30min_n_plus_1",
                    "metric": "next_bar_explains_numbering",
                    "value": bool_sum(observed, "next_bar_explains_numbering"),
                },
                {
                    "source": source,
                    "scope": "unmatched",
                    "metric": "rows",
                    "value": int(len(unmatched)),
                },
                {
                    "source": source,
                    "scope": "unmatched",
                    "metric": "observed_30min_n_plus_1",
                    "value": bool_sum(unmatched, "observed_30min_n_plus_1"),
                },
                {
                    "source": source,
                    "scope": "reliable_matched",
                    "metric": "rows",
                    "value": int(len(reliable)),
                },
                {
                    "source": source,
                    "scope": "reliable_matched",
                    "metric": "observed_30min_n_plus_1",
                    "value": bool_sum(reliable, "observed_30min_n_plus_1"),
                },
            ]
        )
    return pd.DataFrame(rows)


def build_policy_summary(details: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["source", "match_status", "cause_bucket", "layer_hint", "observed_30min_n_plus_1"]
    summary = (
        details.groupby(group_cols, dropna=False)
        .agg(
            rows=("mt5_trade_id", "size"),
            counter_t_matches_mt5_abs=("mt5_matches_counter_t_abs", "sum"),
            counter_t_plus_30_matches_py_abs=("py_matches_counter_t_plus_30_abs", "sum"),
            next_bar_explains_numbering=("next_bar_explains_numbering", "sum"),
        )
        .reset_index()
    )
    return summary.sort_values(["source", "match_status", "rows"], ascending=[True, True, False])


def render_report(details: pd.DataFrame, summary: pd.DataFrame, policy_summary: pd.DataFrame) -> str:
    focused = details[details["observed_30min_n_plus_1"]].copy()
    sample_cols = [
        "source",
        "mt5_trade_id",
        "match_status",
        "aligned_time",
        "nearest_py_date",
        "dir_norm",
        "mt5_signal_src",
        "nearest_py_mode",
        "counter_t",
        "counter_t_plus_30",
        "next_bar_explains_numbering",
    ]
    samples = focused[sample_cols].head(20)

    lines = [
        "# PostN Counter Anchor Replay",
        "",
        "## Summary",
        "",
        summary.to_markdown(index=False),
        "",
        "## Cause/Status Breakdown",
        "",
        policy_summary.to_markdown(index=False),
        "",
        "## Observed 30min N+1 Samples",
        "",
        samples.to_markdown(index=False),
        "",
        "## Interpretation",
        "",
        "- `counter_t` is the processed M30 `merged_post_cross_n` at the MT5 aligned signal time.",
        "- `counter_t_plus_30` is the next M30 bar counter.",
        "- `observed_30min_n_plus_1` means the nearest Python M30 post_n trade is 30 minutes after MT5 and has post_n one larger.",
        "- If `counter_t` matches MT5 and `counter_t_plus_30` matches Python, the discrepancy is explained by anchor/counter semantics rather than a missing raw signal.",
        "- In this run, Python-only follows that pattern, while Python-MT5 does not because the currently used `data/signals_mt5` files are not counter-aligned with `data/processed/m30_mt5.csv`; see `python_mt5_signal_source_audit_20260713`.",
        "",
        "## Output Files",
        "",
        "- `postn_counter_anchor_case_details.csv`",
        "- `postn_counter_anchor_summary.csv`",
        "- `postn_counter_anchor_policy_summary.csv`",
    ]
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    details = build_details()
    summary = build_summary(details)
    policy_summary = build_policy_summary(details)

    export_csv(details, OUT_DIR / "postn_counter_anchor_case_details.csv")
    export_csv(summary, OUT_DIR / "postn_counter_anchor_summary.csv")
    export_csv(policy_summary, OUT_DIR / "postn_counter_anchor_policy_summary.csv")
    write_text(OUT_DIR / "postn_counter_anchor_replay_report.md", render_report(details, summary, policy_summary))

    print(summary.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
