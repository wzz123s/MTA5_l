# -*- coding: utf-8 -*-
"""Diagnose why mapped Python/MT5 trades remain unmatched."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
MAPPED_DIR = DATA_DIR / "validation" / "mapped_trade_alignment_20260713"
DYNAMIC_DIR = DATA_DIR / "validation" / "dynamic_risk_alignment_magic0fix_20260713"
OUT_DIR = DATA_DIR / "validation" / "unmatched_signal_cause_20260713"

MAX_NEAR_MINUTES = 7 * 24 * 60
UNIQUE_MATCH_MAX_MINUTES = 24 * 60
PARENT_WINDOW_MINUTES = 180


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


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def prepare_signal_layer(frame: pd.DataFrame, layer: str, source: str) -> pd.DataFrame:
    df = frame.copy()
    df["source"] = source
    df["layer"] = layer
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["dir_norm"] = df["dir"].map(normalize_dir)
    df["mode_family"] = df["mode"].map(mode_family)
    if "trigger_family" not in df.columns:
        df["trigger_family"] = df.get("variant", "").map(trigger_family_from_variant)
    return df


def load_python_layers(source: str) -> dict[str, pd.DataFrame]:
    if source == "python_only":
        signal_dir = DATA_DIR / "signals"
        exec_file = DYNAMIC_DIR / "python_only_dynamic_risk_trades.csv"
    elif source == "python_mt5":
        signal_dir = DATA_DIR / "signals_mt5"
        exec_file = DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv"
    else:
        raise ValueError(source)

    accepted = prepare_signal_layer(read_csv(signal_dir / "候选信号_Layer1_Layer2通过.csv"), "accepted", source)
    picked = prepare_signal_layer(read_csv(signal_dir / "最终信号_Layer3入选.csv"), "picked", source)
    executed = prepare_signal_layer(read_csv(exec_file), "executed", source)
    return {"accepted": accepted, "picked": picked, "executed": executed}


def load_mt5_ledger() -> pd.DataFrame:
    df = read_csv(DYNAMIC_DIR / "mt5_ledger_unique_signals.csv")
    df["signal_anchor_time"] = pd.to_datetime(df["signal_anchor_time"], errors="coerce")
    df["aligned_time"] = pd.to_datetime(df["aligned_time"], errors="coerce") if "aligned_time" in df.columns else df["signal_anchor_time"] + pd.Timedelta(minutes=90)
    df["dir_norm"] = df["dir"].map(normalize_dir)
    return df


def nearest_candidate(
    frame: pd.DataFrame,
    target_time: pd.Timestamp,
    target_dir: str,
    target_trigger: str,
    target_mode: str,
    max_minutes: int = MAX_NEAR_MINUTES,
) -> dict[str, object]:
    same_dir = frame[frame["dir_norm"] == target_dir].copy()
    if same_dir.empty or pd.isna(target_time):
        return {"status": "none", "abs_minutes": "", "date": "", "trigger_family": "", "mode_family": ""}
    same_dir["time_diff_minutes"] = (same_dir["date"] - target_time).dt.total_seconds() / 60.0
    same_dir["abs_minutes"] = same_dir["time_diff_minutes"].abs()
    same_dir = same_dir[same_dir["abs_minutes"] <= max_minutes]
    if same_dir.empty:
        return {"status": "none", "abs_minutes": "", "date": "", "trigger_family": "", "mode_family": ""}

    same_dir["trigger_same"] = same_dir["trigger_family"].astype(str) == str(target_trigger)
    same_dir["mode_same"] = same_dir["mode_family"].astype(str) == str(target_mode)
    same_dir["rank"] = 10
    same_dir.loc[same_dir["trigger_same"] & same_dir["mode_same"], "rank"] = 1
    same_dir.loc[same_dir["trigger_same"] & ~same_dir["mode_same"], "rank"] = 2
    same_dir.loc[~same_dir["trigger_same"] & same_dir["mode_same"], "rank"] = 3
    best = same_dir.sort_values(["rank", "abs_minutes"]).iloc[0]
    status = {
        1: "same_trigger_mode",
        2: "mode_drift",
        3: "trigger_drift",
        10: "dir_time_only",
    }[int(best["rank"])]
    return {
        "status": status,
        "abs_minutes": round(float(best["abs_minutes"]), 6),
        "signed_minutes": round(float(best["time_diff_minutes"]), 6),
        "date": best["date"],
        "trigger_family": best["trigger_family"],
        "mode_family": best["mode_family"],
        "mode": best.get("mode", ""),
        "variant": best.get("variant", ""),
    }


def parent_m30_candidate(layers: dict[str, pd.DataFrame], row: pd.Series) -> dict[str, object]:
    accepted = layers["accepted"]
    m30 = accepted[
        (accepted["dir_norm"] == row["dir_norm"])
        & (accepted["trigger_family"] == "M30 CLOSE")
        & ((accepted["date"] - row["target_time"]).dt.total_seconds().abs() / 60.0 <= PARENT_WINDOW_MINUTES)
    ].copy()
    if m30.empty:
        return {"parent_status": "missing_raw_parent", "parent_time": "", "parent_mode_family": "", "parent_abs_minutes": ""}
    m30["abs_minutes"] = (m30["date"] - row["target_time"]).dt.total_seconds().abs() / 60.0
    best = m30.sort_values("abs_minutes").iloc[0]
    return {
        "parent_status": "has_nearby_m30_parent",
        "parent_time": best["date"],
        "parent_mode_family": best["mode_family"],
        "parent_abs_minutes": round(float(best["abs_minutes"]), 6),
    }


def classify_mt5_against_python(row: pd.Series) -> str:
    if row["executed_status"] == "same_trigger_mode":
        return "mapping_conflict_or_profit_diff"
    if row["executed_status"] in {"trigger_drift", "mode_drift", "dir_time_only"}:
        return "stage_execution_diff_or_family_drift"
    if row["picked_status"] == "same_trigger_mode":
        return "stage_execution_diff"
    if row["picked_status"] in {"trigger_drift", "mode_drift", "dir_time_only"}:
        return "layer3_family_drift"
    if row["accepted_status"] == "same_trigger_mode":
        return "layer3_reject"
    if row["accepted_status"] in {"trigger_drift", "mode_drift", "dir_time_only"}:
        return "trigger_family_drift"
    if row.get("parent_status") == "missing_raw_parent":
        return "missing_raw_parent"
    return "missing_python_candidate"


def classify_python_against_mt5(row: pd.Series) -> str:
    if row["mt5_status"] == "same_trigger_mode":
        abs_minutes = pd.to_numeric(row.get("mt5_abs_minutes", ""), errors="coerce")
        if pd.notna(abs_minutes) and float(abs_minutes) > UNIQUE_MATCH_MAX_MINUTES:
            return "low_confidence_far_candidate_conflict"
        return "unique_match_conflict"
    if row["mt5_status"] in {"trigger_drift", "mode_drift", "dir_time_only"}:
        return "mt5_family_or_time_drift"
    return "python_signal_not_in_mt5_ledger"


def diagnose_mt5_unmatched(source: str, layers: dict[str, pd.DataFrame]) -> pd.DataFrame:
    path = MAPPED_DIR / f"{source}_unmatched_mt5_trades.csv"
    rows = read_csv(path)
    rows["target_time"] = pd.to_datetime(rows["aligned_time"], errors="coerce")
    rows["dir_norm"] = rows["dir_norm"].map(normalize_dir)

    out_rows: list[dict[str, object]] = []
    for _, row in rows.iterrows():
        base = {
            "source": source,
            "side": "mt5_unmatched",
            "trade_id": row["mt5_trade_id"],
            "target_time": row["target_time"],
            "dir_norm": row["dir_norm"],
            "trigger_family": row["trigger_family"],
            "mode_family": row["mode_family"],
            "profit": row.get("net_profit", ""),
        }
        parent = parent_m30_candidate(layers, row) if row["trigger_family"] == "M15 SLOT1" else {
            "parent_status": "",
            "parent_time": "",
            "parent_mode_family": "",
            "parent_abs_minutes": "",
        }
        layer_results = {}
        for layer_name, frame in layers.items():
            nearest = nearest_candidate(
                frame,
                row["target_time"],
                row["dir_norm"],
                row["trigger_family"],
                row["mode_family"],
            )
            for key, value in nearest.items():
                layer_results[f"{layer_name}_{key}"] = value
        record = {**base, **parent, **layer_results}
        record["cause_bucket"] = classify_mt5_against_python(pd.Series(record))
        out_rows.append(record)
    return pd.DataFrame(out_rows)


def diagnose_python_unmatched(source: str, mt5: pd.DataFrame) -> pd.DataFrame:
    path = MAPPED_DIR / f"{source}_unmatched_python_trades.csv"
    rows = read_csv(path)
    rows["target_time"] = pd.to_datetime(rows["date"], errors="coerce")
    rows["dir_norm"] = rows["dir_norm"].map(normalize_dir)

    mt5_as_layer = mt5.rename(columns={"aligned_time": "date"}).copy()
    out_rows: list[dict[str, object]] = []
    for _, row in rows.iterrows():
        nearest = nearest_candidate(
            mt5_as_layer,
            row["target_time"],
            row["dir_norm"],
            row["trigger_family"],
            row["mode_family"],
        )
        record = {
            "source": source,
            "side": "python_unmatched",
            "trade_id": row["py_trade_id"],
            "target_time": row["target_time"],
            "dir_norm": row["dir_norm"],
            "trigger_family": row["trigger_family"],
            "mode_family": row["mode_family"],
            "profit": row.get("dynamic_total_$", ""),
        }
        for key, value in nearest.items():
            record[f"mt5_{key}"] = value
        record["cause_bucket"] = classify_python_against_mt5(pd.Series(record))
        out_rows.append(record)
    return pd.DataFrame(out_rows)


def simple_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_无数据_"
    return frame.to_markdown(index=False)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mt5 = load_mt5_ledger()

    all_details: list[pd.DataFrame] = []
    for source in ["python_only", "python_mt5"]:
        layers = load_python_layers(source)
        mt5_diag = diagnose_mt5_unmatched(source, layers)
        py_diag = diagnose_python_unmatched(source, mt5)
        export_csv(mt5_diag, OUT_DIR / f"{source}_mt5_unmatched_cause.csv")
        export_csv(py_diag, OUT_DIR / f"{source}_python_unmatched_cause.csv")
        all_details.extend([mt5_diag, py_diag])

    details = pd.concat(all_details, ignore_index=True) if all_details else pd.DataFrame()
    summary = (
        details.groupby(["source", "side", "cause_bucket"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["source", "side", "rows"], ascending=[True, True, False])
        if not details.empty
        else pd.DataFrame(columns=["source", "side", "cause_bucket", "rows"])
    )
    trigger_mode_summary = (
        details.groupby(["source", "side", "trigger_family", "mode_family", "cause_bucket"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["source", "side", "trigger_family", "mode_family", "rows"], ascending=[True, True, True, True, False])
        if not details.empty
        else pd.DataFrame(columns=["source", "side", "trigger_family", "mode_family", "cause_bucket", "rows"])
    )
    m30_postn = details[(details["trigger_family"] == "M30 CLOSE") & (details["mode_family"] == "post_n")].copy()
    m15_slot1_postn = details[(details["trigger_family"] == "M15 SLOT1") & (details["mode_family"] == "post_n")].copy()
    export_csv(details, OUT_DIR / "all_unmatched_signal_causes.csv")
    export_csv(summary, OUT_DIR / "unmatched_signal_cause_summary.csv")
    export_csv(trigger_mode_summary, OUT_DIR / "unmatched_trigger_mode_cause_summary.csv")
    export_csv(m30_postn, OUT_DIR / "m30_postn_unmatched_cause.csv")
    export_csv(m15_slot1_postn, OUT_DIR / "m15_slot1_postn_raw_parent_cause.csv")

    report_lines = [
        "# Unmatched Signal Cause Diagnosis",
        "",
        "## Summary",
        simple_table(summary),
        "",
        "## Trigger/Mode Cause Summary",
        simple_table(trigger_mode_summary),
        "",
        "## Interpretation",
        "- This is a first-pass attribution table. It classifies unmatched trades by nearest accepted/picked/executed candidates.",
        "- `missing_raw_parent` is only assigned when an unmatched MT5 `M15 SLOT1` signal lacks a nearby Python `M30 CLOSE` accepted parent.",
        "- `family_drift` buckets mean a nearby same-direction candidate exists but trigger family or mode family differs.",
        "",
        "## Output Files",
        "- `all_unmatched_signal_causes.csv`",
        "- `unmatched_signal_cause_summary.csv`",
        "- `unmatched_trigger_mode_cause_summary.csv`",
        "- `m30_postn_unmatched_cause.csv`",
        "- `m15_slot1_postn_raw_parent_cause.csv`",
        "- `python_only_mt5_unmatched_cause.csv`",
        "- `python_only_python_unmatched_cause.csv`",
        "- `python_mt5_mt5_unmatched_cause.csv`",
        "- `python_mt5_python_unmatched_cause.csv`",
    ]
    write_text(OUT_DIR / "unmatched_signal_cause_report.md", "\n".join(report_lines))


if __name__ == "__main__":
    main()
