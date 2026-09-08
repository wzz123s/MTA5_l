# -*- coding: utf-8 -*-
"""Diagnose M30 CLOSE post_n alignment after MT5 ledger closure."""
from __future__ import annotations


import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
DYNAMIC_DIR = DATA_DIR / "validation" / "dynamic_risk_alignment_magic0fix_20260713"
MAPPED_DIR = DATA_DIR / "validation" / "mapped_trade_alignment_20260713"
CAUSE_DIR = DATA_DIR / "validation" / "unmatched_signal_cause_20260713"
OUT_DIR = DATA_DIR / "validation" / "m30_postn_alignment_diag_20260713"

NEAR_WINDOW_MINUTES = 24 * 60


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"S", "SELL"}:
        return "SELL"
    if text in {"B", "BUY", "L"}:
        return "BUY"
    return text


def post_n_num(value: object) -> int | None:
    match = re.search(r"post_n(\d+)", str(value))
    if not match:
        return None
    return int(match.group(1))


def time_bucket(minutes: object) -> str:
    try:
        value = abs(float(minutes))
    except Exception:
        return "none"
    if value == 0:
        return "0"
    if value <= 30:
        return "<=30"
    if value <= 60:
        return "<=60"
    if value <= 180:
        return "<=180"
    if value <= 1440:
        return "<=1d"
    return ">1d"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def load_mt5() -> pd.DataFrame:
    df = read_csv(DYNAMIC_DIR / "mt5_ledger_unique_signals.csv")
    df = df.copy()
    df["mt5_trade_id"] = [f"mt5_{i + 1:04d}" for i in range(len(df))]
    df["signal_anchor_time"] = pd.to_datetime(df["signal_anchor_time"], errors="coerce")
    df["aligned_time"] = df["signal_anchor_time"] + pd.Timedelta(minutes=90)
    df["dir_norm"] = df["dir"].map(normalize_dir)
    df["post_n"] = df["signal_src"].map(post_n_num)
    return df


def load_python(source: str) -> pd.DataFrame:
    filename = f"{source}_dynamic_risk_trades.csv"
    df = read_csv(DYNAMIC_DIR / filename)
    df = df.copy()
    df["py_trade_id"] = [f"{source}_{i + 1:04d}" for i in range(len(df))]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["dir_norm"] = df["dir"].map(normalize_dir)
    df["post_n"] = df["mode"].map(post_n_num)
    return df


def load_match_maps(source: str) -> tuple[dict[str, pd.Series], dict[str, pd.Series], set[str], set[str]]:
    matches = read_csv(MAPPED_DIR / "all_unique_matches.csv")
    src = matches[matches["source"] == source].copy()
    mt5_map = {str(row["mt5_trade_id"]): row for _, row in src.iterrows()}
    py_map = {str(row["py_trade_id"]): row for _, row in src.iterrows()}
    reliable = set(src[src["is_reliable_tier"].astype(str) == "True"]["mt5_trade_id"].astype(str))
    relaxed = set(src["mt5_trade_id"].astype(str)) - reliable
    return mt5_map, py_map, reliable, relaxed


def nearest_python(row: pd.Series, py: pd.DataFrame) -> dict[str, object]:
    candidates = py[
        (py["dir_norm"] == row["dir_norm"])
        & (py["trigger_family"] == "M30 CLOSE")
        & (py["mode_family"] == "post_n")
    ].copy()
    if candidates.empty:
        return {}
    candidates["signed_minutes"] = (candidates["date"] - row["aligned_time"]).dt.total_seconds() / 60.0
    candidates["abs_minutes"] = candidates["signed_minutes"].abs()
    candidates = candidates[candidates["abs_minutes"] <= NEAR_WINDOW_MINUTES]
    if candidates.empty:
        return {}
    best = candidates.sort_values(["abs_minutes", "py_trade_id"]).iloc[0]
    return {
        "nearest_py_trade_id": best["py_trade_id"],
        "nearest_py_date": best["date"],
        "nearest_py_mode": best["mode"],
        "nearest_py_post_n": best["post_n"],
        "nearest_py_signed_minutes": round(float(best["signed_minutes"]), 6),
        "nearest_py_abs_minutes": round(float(best["abs_minutes"]), 6),
        "nearest_py_profit": best["dynamic_total_$"],
    }


def nearest_mt5(row: pd.Series, mt5: pd.DataFrame) -> dict[str, object]:
    candidates = mt5[
        (mt5["dir_norm"] == row["dir_norm"])
        & (mt5["trigger_family"] == "M30 CLOSE")
        & (mt5["mode_family"] == "post_n")
    ].copy()
    if candidates.empty:
        return {}
    candidates["signed_minutes"] = (candidates["aligned_time"] - row["date"]).dt.total_seconds() / 60.0
    candidates["abs_minutes"] = candidates["signed_minutes"].abs()
    candidates = candidates[candidates["abs_minutes"] <= NEAR_WINDOW_MINUTES]
    if candidates.empty:
        return {}
    best = candidates.sort_values(["abs_minutes", "mt5_trade_id"]).iloc[0]
    return {
        "nearest_mt5_trade_id": best["mt5_trade_id"],
        "nearest_mt5_time": best["aligned_time"],
        "nearest_mt5_signal_src": best["signal_src"],
        "nearest_mt5_post_n": best["post_n"],
        "nearest_mt5_signed_minutes": round(float(best["signed_minutes"]), 6),
        "nearest_mt5_abs_minutes": round(float(best["abs_minutes"]), 6),
        "nearest_mt5_profit": best["net_profit"],
    }


def mt5_side_details(source: str) -> pd.DataFrame:
    mt5 = load_mt5()
    py = load_python(source)
    mt5_map, _, reliable, relaxed = load_match_maps(source)
    cause = read_csv(CAUSE_DIR / f"{source}_mt5_unmatched_cause.csv").set_index("trade_id", drop=False)

    rows = []
    target = mt5[(mt5["trigger_family"] == "M30 CLOSE") & (mt5["mode_family"] == "post_n")].copy()
    for _, row in target.iterrows():
        trade_id = str(row["mt5_trade_id"])
        if trade_id in reliable:
            status = "reliable_matched"
        elif trade_id in relaxed:
            status = "relaxed_matched"
        else:
            status = "unmatched"
        near = nearest_python(row, py)
        nearest_n = near.get("nearest_py_post_n")
        postn_diff = ""
        if pd.notna(row["post_n"]) and nearest_n is not None and pd.notna(nearest_n):
            postn_diff = int(row["post_n"]) - int(nearest_n)

        cause_bucket = ""
        layer_hint = ""
        if trade_id in cause.index:
            c = cause.loc[trade_id]
            cause_bucket = str(c.get("cause_bucket", ""))
            if str(c.get("executed_status", "")) == "same_trigger_mode":
                layer_hint = "executed_nearby"
            elif str(c.get("picked_status", "")) == "same_trigger_mode":
                layer_hint = "picked_nearby"
            elif str(c.get("accepted_status", "")) == "same_trigger_mode":
                layer_hint = "accepted_only_layer3_reject"
            elif str(c.get("accepted_status", "")) in {"trigger_drift", "mode_drift", "dir_time_only"}:
                layer_hint = "family_drift"
            else:
                layer_hint = "missing_python_candidate"

        rows.append(
            {
                "source": source,
                "side": "mt5_m30_postn",
                "mt5_trade_id": trade_id,
                "match_status": status,
                "aligned_time": row["aligned_time"],
                "dir_norm": row["dir_norm"],
                "mt5_signal_src": row["signal_src"],
                "mt5_post_n": row["post_n"],
                "mt5_profit": row["net_profit"],
                "cause_bucket": cause_bucket,
                "layer_hint": layer_hint,
                **near,
                "time_bucket": time_bucket(near.get("nearest_py_abs_minutes", "")),
                "postn_diff": postn_diff,
            }
        )
    return pd.DataFrame(rows)


def python_side_details(source: str) -> pd.DataFrame:
    mt5 = load_mt5()
    py = load_python(source)
    _, py_map, _, _ = load_match_maps(source)

    rows = []
    target = py[(py["trigger_family"] == "M30 CLOSE") & (py["mode_family"] == "post_n")].copy()
    for _, row in target.iterrows():
        trade_id = str(row["py_trade_id"])
        if trade_id in py_map:
            status = "matched"
        else:
            status = "unmatched"
        near = nearest_mt5(row, mt5)
        nearest_n = near.get("nearest_mt5_post_n")
        postn_diff = ""
        if pd.notna(row["post_n"]) and nearest_n is not None and pd.notna(nearest_n):
            postn_diff = int(row["post_n"]) - int(nearest_n)
        rows.append(
            {
                "source": source,
                "side": "python_m30_postn",
                "py_trade_id": trade_id,
                "match_status": status,
                "date": row["date"],
                "dir_norm": row["dir_norm"],
                "py_mode": row["mode"],
                "py_post_n": row["post_n"],
                "py_profit": row["dynamic_total_$"],
                **near,
                "time_bucket": time_bucket(near.get("nearest_mt5_abs_minutes", "")),
                "postn_diff": postn_diff,
            }
        )
    return pd.DataFrame(rows)


def summarize(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    cols = ["source", "side", "match_status", "time_bucket", "postn_diff"]
    return (
        frame.groupby(cols, dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["source", "side", "match_status", "time_bucket", "rows"], ascending=[True, True, True, True, False])
    )


def simple_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No data_"
    return frame.to_markdown(index=False)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    details = pd.concat(
        [
            mt5_side_details("python_only"),
            mt5_side_details("python_mt5"),
            python_side_details("python_only"),
            python_side_details("python_mt5"),
        ],
        ignore_index=True,
    )
    summary = summarize(details)

    export_csv(details, OUT_DIR / "m30_postn_alignment_details.csv")
    export_csv(summary, OUT_DIR / "m30_postn_alignment_summary.csv")

    mt5_unmatched = details[(details["side"] == "mt5_m30_postn") & (details["match_status"] == "unmatched")]
    export_csv(mt5_unmatched, OUT_DIR / "m30_postn_mt5_unmatched_details.csv")

    report = [
        "# M30 PostN Alignment Diagnosis",
        "",
        "## Summary",
        simple_table(summary),
        "",
        "## MT5 Unmatched Focus",
        simple_table(
            mt5_unmatched.groupby(["source", "cause_bucket", "layer_hint", "time_bucket", "postn_diff"], dropna=False)
            .size()
            .reset_index(name="rows")
            .sort_values(["source", "rows"], ascending=[True, False])
        ),
        "",
        "## Interpretation",
        "- `time_bucket` is based on the nearest same-direction M30 CLOSE post_n candidate within one day.",
        "- `postn_diff = mt5_post_n - python_post_n` for MT5-side rows and `py_post_n - mt5_post_n` for Python-side rows.",
        "- Rows with `accepted_only_layer3_reject` reached Python accepted but did not survive Layer3.",
        "- Rows with `executed_nearby` are not missing raw signals; they are timing or post_n numbering conflicts.",
        "",
        "## Output Files",
        "- `m30_postn_alignment_details.csv`",
        "- `m30_postn_alignment_summary.csv`",
        "- `m30_postn_mt5_unmatched_details.csv`",
    ]
    write_text(OUT_DIR / "m30_postn_alignment_report.md", "\n".join(report))


if __name__ == "__main__":
    main()
