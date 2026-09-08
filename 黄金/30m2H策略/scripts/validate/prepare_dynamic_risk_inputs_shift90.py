# -*- coding: utf-8 -*-
"""Prepare dynamic-risk inputs with the shift90 Python-MT5 signal set."""
from __future__ import annotations


import math
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
OUT_DIR = DATA_DIR / "validation" / "dynamic_risk_inputs_shift90_20260713"
SHIFT90_SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_20260712" / "python_h2_context_q2early"
SHIFT90_M30 = DATA_DIR / "signals_mt5_shift90_20260712" / "m30_prepared_with_mt5_shift90.csv"


@dataclass(frozen=True)
class SourceConfig:
    name: str
    signals_dir: Path
    m30_counter_path: Path | None = None


SOURCES = [
    SourceConfig("python_only", DATA_DIR / "signals"),
    SourceConfig("python_mt5", SHIFT90_SIGNAL_DIR, SHIFT90_M30),
]


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


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


def counter_alignment_stats(layer3: pd.DataFrame, m30_path: Path | None) -> dict[str, int | str]:
    if m30_path is None:
        return {
            "m30_postn_signals": "",
            "postn_counter_t_abs_matches": "",
            "postn_counter_t_signed_matches": "",
        }
    m30 = load_csv(m30_path).copy()
    if "Unnamed: 0" in m30.columns:
        m30 = m30.drop(columns=["Unnamed: 0"])
    m30["date"] = pd.to_datetime(m30["date"], errors="coerce")
    m30["merged_post_cross_n"] = pd.to_numeric(m30["merged_post_cross_n"], errors="coerce")
    m30 = m30.dropna(subset=["date"]).drop_duplicates("date", keep="last").set_index("date")

    signals = layer3.copy()
    signals["date"] = pd.to_datetime(signals["date"], errors="coerce")
    signals["mode_post_n"] = signals["mode"].map(post_n_num)
    target = signals[signals["mode_post_n"].notna()].copy()
    signed_matches = 0
    abs_matches = 0
    for _, row in target.iterrows():
        date = row["date"]
        if pd.isna(date) or date not in m30.index:
            continue
        counter = float(m30.at[date, "merged_post_cross_n"])
        expected = signed_mode_counter(row["dir"], row["mode"])
        if math.isnan(expected):
            continue
        if int(counter) == int(expected):
            signed_matches += 1
        if abs(int(counter)) == abs(int(expected)):
            abs_matches += 1
    return {
        "m30_postn_signals": int(len(target)),
        "postn_counter_t_abs_matches": int(abs_matches),
        "postn_counter_t_signed_matches": int(signed_matches),
    }


def prepare_source(cfg: SourceConfig) -> tuple[pd.DataFrame, dict[str, int | str]]:
    layer3_path = cfg.signals_dir / "最终信号_Layer3入选.csv"
    stage_path = cfg.signals_dir / "执行交易_Stage结果.csv"

    layer3 = load_csv(layer3_path).copy()
    stage = load_csv(stage_path).copy()

    if "信号层级" in layer3.columns:
        layer3 = layer3.drop(columns=["信号层级"])
    if "信号层级" in stage.columns:
        stage = stage.drop(columns=["信号层级"])
    if "year" in stage.columns and "year" in layer3.columns:
        stage = stage.drop(columns=["year"])

    key_cols = ["date", "mode", "dir"]
    layer3["date"] = pd.to_datetime(layer3["date"])
    stage["date"] = pd.to_datetime(stage["date"])

    layer3_dupes = int(layer3.duplicated(subset=key_cols).sum())
    stage_dupes = int(stage.duplicated(subset=key_cols).sum())

    merged = layer3.merge(
        stage,
        on=key_cols,
        how="outer",
        indicator=True,
        suffixes=("_signal", "_stage"),
    )

    merged["source"] = cfg.name
    merged["source_variant"] = "shift90_python_h2_context_q2early" if cfg.name == "python_mt5" else "baseline"
    merged["stop_price_diff"] = (merged["entry"] - merged["stop"]).abs()
    merged["stop_pts_spec"] = merged["stop_price_diff"]
    merged["stop_pts_mql5"] = merged["stop_price_diff"] * 1000.0
    merged["signal_stage_pnl_gap"] = merged["pnl"] - merged["total_$"]

    stats: dict[str, int | str] = {
        "source": cfg.name,
        "source_variant": "shift90_python_h2_context_q2early" if cfg.name == "python_mt5" else "baseline",
        "layer3_rows": int(len(layer3)),
        "stage_rows": int(len(stage)),
        "merged_rows": int(len(merged)),
        "signal_only_rows": int((merged["_merge"] == "left_only").sum()),
        "stage_only_rows": int((merged["_merge"] == "right_only").sum()),
        "matched_rows": int((merged["_merge"] == "both").sum()),
        "layer3_dupe_keys": layer3_dupes,
        "stage_dupe_keys": stage_dupes,
        "min_stop_pts_spec": round(float(merged["stop_pts_spec"].dropna().min()), 6) if merged["stop_pts_spec"].notna().any() else "",
        "max_stop_pts_spec": round(float(merged["stop_pts_spec"].dropna().max()), 6) if merged["stop_pts_spec"].notna().any() else "",
    }
    stats.update(counter_alignment_stats(layer3, cfg.m30_counter_path))
    return merged, stats


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    stats_rows: list[dict[str, int | str]] = []
    for cfg in SOURCES:
        merged, stats = prepare_source(cfg)
        stats_rows.append(stats)
        export_csv(merged, OUT_DIR / f"{cfg.name}_dynamic_risk_inputs.csv")

    stats_df = pd.DataFrame(stats_rows)
    export_csv(stats_df, OUT_DIR / "dynamic_risk_input_prepare_summary.csv")

    report_lines = [
        "# Dynamic Risk Input Preparation - shift90",
        "",
        "## Summary",
        "",
        stats_df.to_markdown(index=False),
        "",
        "## Notes",
        "- Python-only remains the baseline `data/signals` source.",
        "- Python-MT5 now uses `signals_mt5_shift90_20260712/python_h2_context_q2early`.",
        "- This output intentionally does not overwrite `dynamic_risk_inputs_20260712`.",
    ]
    write_text(OUT_DIR / "dynamic_risk_input_prepare_report.md", "\n".join(report_lines))
    print(stats_df.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
