# -*- coding: utf-8 -*-
"""Audit whether Python-MT5 signal files match their processed M30 counters."""
from __future__ import annotations


import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
OUT_DIR = DATA_DIR / "validation" / "python_mt5_signal_source_audit_20260713"

OLD_SIGNALS = DATA_DIR / "signals_mt5" / "最终信号_Layer3入选.csv"
OLD_M30 = DATA_DIR / "processed" / "m30_mt5.csv"
SHIFT90_ROOT = DATA_DIR / "signals_mt5_shift90_20260712"
SHIFT90_M30 = SHIFT90_ROOT / "m30_prepared_with_mt5_shift90.csv"

SIGNAL_SOURCES = [
    ("old_signals_mt5_vs_processed_m30_mt5", OLD_SIGNALS, OLD_M30),
    ("shift90_mt5_h2_barlevel_direct", SHIFT90_ROOT / "mt5_h2_barlevel_direct" / "最终信号_Layer3入选.csv", SHIFT90_M30),
    ("shift90_mt5_h2_barlevel_q2early", SHIFT90_ROOT / "mt5_h2_barlevel_q2early" / "最终信号_Layer3入选.csv", SHIFT90_M30),
    ("shift90_python_h2_context_q2early", SHIFT90_ROOT / "python_h2_context_q2early" / "最终信号_Layer3入选.csv", SHIFT90_M30),
]


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def post_n_num(value: object) -> float:
    match = re.search(r"post_n(\d+)", str(value))
    if not match:
        return math.nan
    return float(match.group(1))


def signed_mode_counter(direction: object, mode: object) -> float:
    number = post_n_num(mode)
    if math.isnan(number):
        return math.nan
    direction_text = str(direction).strip().upper()
    return number if direction_text in {"L", "BUY", "B"} else -number


def load_m30(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["merged_post_cross_n"] = pd.to_numeric(df["merged_post_cross_n"], errors="coerce")
    return df.dropna(subset=["date"]).drop_duplicates("date", keep="last").set_index("date")


def build_detail(name: str, signal_path: Path, m30_path: Path) -> pd.DataFrame:
    signals = pd.read_csv(signal_path, encoding="utf-8-sig")
    signals = signals.copy()
    signals["date"] = pd.to_datetime(signals["date"], errors="coerce")
    signals["mode_post_n"] = signals["mode"].map(post_n_num)
    signals["mode_signed_post_n"] = [
        signed_mode_counter(direction, mode)
        for direction, mode in zip(signals["dir"], signals["mode"])
    ]
    target = signals[signals["mode_post_n"].notna()].copy()
    m30 = load_m30(m30_path)

    rows: list[dict[str, object]] = []
    for _, row in target.iterrows():
        date = row["date"]
        counter_t = math.nan
        counter_t_plus_30 = math.nan
        if pd.notna(date) and date in m30.index:
            counter_t = float(m30.at[date, "merged_post_cross_n"])
        next_date = date + pd.Timedelta(minutes=30) if pd.notna(date) else pd.NaT
        if pd.notna(next_date) and next_date in m30.index:
            counter_t_plus_30 = float(m30.at[next_date, "merged_post_cross_n"])
        mode_signed = float(row["mode_signed_post_n"])
        rows.append(
            {
                "signal_source": name,
                "date": date,
                "mode": row["mode"],
                "dir": row["dir"],
                "mode_signed_post_n": mode_signed,
                "counter_t": counter_t,
                "counter_t_plus_30": counter_t_plus_30,
                "mode_matches_counter_t_signed": int(counter_t) == int(mode_signed) if not math.isnan(counter_t) else False,
                "mode_matches_counter_t_abs": abs(int(counter_t)) == abs(int(mode_signed)) if not math.isnan(counter_t) else False,
                "mode_matches_counter_t_plus_30_abs": abs(int(counter_t_plus_30)) == abs(int(mode_signed)) if not math.isnan(counter_t_plus_30) else False,
                "variant": row.get("variant", ""),
                "trigger": row.get("trigger", ""),
                "layer3_eval_time": row.get("layer3_eval_time", ""),
            }
        )
    return pd.DataFrame(rows)


def build_summary(details: pd.DataFrame) -> pd.DataFrame:
    if details.empty:
        return pd.DataFrame()
    return (
        details.groupby("signal_source", dropna=False)
        .agg(
            m30_postn_signals=("date", "size"),
            mode_matches_counter_t_signed=("mode_matches_counter_t_signed", "sum"),
            mode_matches_counter_t_abs=("mode_matches_counter_t_abs", "sum"),
            mode_matches_counter_t_plus_30_abs=("mode_matches_counter_t_plus_30_abs", "sum"),
        )
        .reset_index()
    )


def render_report(summary: pd.DataFrame) -> str:
    lines = [
        "# Python-MT5 Signal Source Audit",
        "",
        "## Summary",
        "",
        summary.to_markdown(index=False) if not summary.empty else "_No data_",
        "",
        "## Interpretation",
        "",
        "- `old_signals_mt5_vs_processed_m30_mt5` is the currently used directory for dynamic-risk Python-MT5 runs.",
        "- The shift90 variants are versioned diagnostic outputs and are not used by `prepare_dynamic_risk_inputs.py` yet.",
        "- If a signal file's `post_nN` does not match its M30 `merged_post_cross_n`, downstream trade mapping mixes signal and market-counter semantics.",
        "",
        "## Output Files",
        "",
        "- `python_mt5_signal_source_audit_details.csv`",
        "- `python_mt5_signal_source_audit_summary.csv`",
    ]
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    details = pd.concat(
        [build_detail(name, signal_path, m30_path) for name, signal_path, m30_path in SIGNAL_SOURCES],
        ignore_index=True,
    )
    summary = build_summary(details)
    export_csv(details, OUT_DIR / "python_mt5_signal_source_audit_details.csv")
    export_csv(summary, OUT_DIR / "python_mt5_signal_source_audit_summary.csv")
    write_text(OUT_DIR / "python_mt5_signal_source_audit_report.md", render_report(summary))
    print(summary.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
