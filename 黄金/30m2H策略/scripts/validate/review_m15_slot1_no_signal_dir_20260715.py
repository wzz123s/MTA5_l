# -*- coding: utf-8 -*-
"""Review the 2025-10-17 M15 SLOT1 NO_SIGNAL_DIR mismatch.

This script is diagnostic only. It compares the Python-MT5 runtime_rescue
admission with the EA full-history M15 entry diagnostic for the same target.
"""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"

SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "python_h2_context_q2early"
DIAG_REVIEW_DIR = VALIDATION_DIR / "ea_m15_entry_diag_full_review_20260715"
OUT_DIR = VALIDATION_DIR / "m15_slot1_no_signal_dir_review_20260715"

RAW_M15_FILE = DATA_DIR / "raw" / "XAUUSDm15.csv"
PROCESSED_M15_FILE = DATA_DIR / "processed" / "m15_context_bars.csv"
PROCESSED_M30_FILE = DATA_DIR / "processed" / "m30_mt5.csv"

TARGET_CASE = "far_runtime_rescue_20251017_precross"
PY_TARGET_TIME = pd.Timestamp("2025-10-17 11:00:00")
EA_RAW_ANCHOR = pd.Timestamp("2025-10-17 09:30:00")
SPEC_LO = 5.0
SPEC_HI = 35.0
PRE_GAP_PCT = 0.300


def read_csv(path: Path, encoding: str = "utf-8-sig") -> pd.DataFrame:
    return pd.read_csv(path, encoding=encoding, low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def parse_dt_series(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip().str.replace(".", "-", regex=False)
    text = text.mask(text.isin(["", "nan", "NaT", "None"]))
    return pd.to_datetime(text, errors="coerce")


def fmt_ts(value: object) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return ""
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def safe_float(value: object) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return float("nan")
    return float(parsed)


def spec_reason(sd: float) -> str:
    if SPEC_LO <= sd <= SPEC_HI:
        return "ok"
    if sd > SPEC_HI:
        return "too_wide"
    return "too_tight"


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None) -> str:
    if frame.empty:
        return "_No rows._"
    out = frame.copy()
    if columns is not None:
        out = out[[col for col in columns if col in out.columns]]
    return out.to_markdown(index=False)


def normalize_for_export(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for col in list(out.columns):
        if col.endswith("_dt"):
            out[col] = pd.to_datetime(out[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    return out


def load_python_signal_chain() -> dict[str, pd.DataFrame]:
    files = {
        "raw_candidates": SIGNAL_DIR / "raw_candidates.csv",
        "layer12_accepted": SIGNAL_DIR / "候选信号_Layer1_Layer2通过.csv",
        "layer3_picked": SIGNAL_DIR / "最终信号_Layer3入选.csv",
        "stage_results": SIGNAL_DIR / "执行交易_Stage结果.csv",
    }
    out: dict[str, pd.DataFrame] = {}
    for layer, path in files.items():
        df = read_csv(path)
        if "date" in df.columns:
            df["date_dt"] = parse_dt_series(df["date"])
        if "entry_time" in df.columns:
            df["entry_time_dt"] = parse_dt_series(df["entry_time"])
        out[layer] = df
    return out


def python_chain_window(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for layer, df in frames.items():
        if "date_dt" not in df.columns:
            continue
        window = df[df["date_dt"].between("2025-10-17 08:00:00", "2025-10-17 16:00:00", inclusive="both")].copy()
        if window.empty:
            continue
        window.insert(0, "layer", layer)
        rows.append(window)
    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    cols = [
        "layer",
        "date",
        "entry_time",
        "mode",
        "dir",
        "entry",
        "stop",
        "sd",
        "variant",
        "trigger",
        "Bias_5",
        "Bias_55",
        "gap",
        "spec_pass",
        "spec_reason",
        "layer3_eval_time",
        "Bias_5_ea",
        "layer3_threshold_ea",
        "layer3_pass_ea",
        "stage1_pnl",
        "stage2_pnl",
        "stage3_pnl",
        "total_$",
        "equity_$",
    ]
    return out[[col for col in cols if col in out.columns]].copy()


def get_target_rows(frames: dict[str, pd.DataFrame]) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    raw = frames["raw_candidates"]
    accepted = frames["layer12_accepted"]
    picked = frames["layer3_picked"]
    stage = frames["stage_results"]
    raw_row = raw[(raw["date_dt"].eq(PY_TARGET_TIME)) & raw["mode"].astype(str).eq("pre_cross")].iloc[0]
    accepted_row = accepted[
        (accepted["date_dt"].eq(PY_TARGET_TIME))
        & accepted["variant"].astype(str).eq("ea_slot1_runtime_rescue")
    ].iloc[0]
    picked_row = picked[
        (picked["date_dt"].eq(PY_TARGET_TIME))
        & picked["variant"].astype(str).eq("ea_slot1_runtime_rescue")
    ].iloc[0]
    stage_row = stage[(stage["date_dt"].eq(PY_TARGET_TIME)) & stage["mode"].astype(str).eq("pre_cross")].iloc[0]
    return raw_row, accepted_row, picked_row, stage_row


def load_ea_diag() -> tuple[pd.DataFrame, pd.DataFrame]:
    target = read_csv(DIAG_REVIEW_DIR / "target_m15_entry_diag_rows.csv")
    window = read_csv(DIAG_REVIEW_DIR / "target_m15_entry_diag_windows.csv")
    for df in (target, window):
        for col in ["time", "current_m30_bar", "completed_m15_open", "slot_m30_open", "anchor_time"]:
            if col in df.columns:
                df[f"{col}_dt"] = parse_dt_series(df[col])
    return (
        target[target["stable_case"].astype(str).eq(TARGET_CASE)].copy(),
        window[window["stable_case"].astype(str).eq(TARGET_CASE)].copy(),
    )


def load_processed_m15() -> pd.DataFrame:
    m15 = read_csv(PROCESSED_M15_FILE)
    m15["date_dt"] = parse_dt_series(m15["date"])
    m15["raw_time_inferred_dt"] = m15["date_dt"] - pd.Timedelta(hours=2)
    return m15


def detect_m15_mode(window: pd.DataFrame) -> pd.DataFrame:
    out = window.sort_values("date_dt").reset_index(drop=True).copy()
    out["prev_close"] = out["close"].shift(1)
    out["prev_sma5"] = out["SMA_5"].shift(1)
    out["prev_sma13"] = out["SMA_13"].shift(1)
    out["gap_pct"] = (out["SMA_5"] - out["SMA_13"]).abs() / out["SMA_13"] * 100.0
    out["sma5_prev_above"] = out["prev_sma5"] > out["prev_sma13"]
    out["sma5_curr_above"] = out["SMA_5"] > out["SMA_13"]
    out["sma5_crosses_sma13"] = out["sma5_prev_above"] != out["sma5_curr_above"]
    out["long_pre_cross"] = (
        (out["gap_pct"] <= PRE_GAP_PCT)
        & (~out["sma5_crosses_sma13"])
        & (out["prev_close"] <= out["prev_sma13"])
        & (out["close"] > out["SMA_13"])
        & (out["SMA_5"] < out["SMA_13"])
    )
    out["short_pre_cross"] = (
        (out["gap_pct"] <= PRE_GAP_PCT)
        & (~out["sma5_crosses_sma13"])
        & (out["prev_close"] >= out["prev_sma13"])
        & (out["close"] < out["SMA_13"])
        & (out["SMA_5"] > out["SMA_13"])
    )
    out["ea_like_pre_cross"] = out["long_pre_cross"].map({True: 1, False: 0}) + out["short_pre_cross"].map({True: -1, False: 0})
    out["ea_like_is_cross"] = out["sma5_crosses_sma13"].fillna(False)
    out["sell_same_side"] = out["close"] < out["SMA_13"]
    return out


def build_m15_window_comparison(raw_row: pd.Series, accepted_row: pd.Series, ea_diag: pd.DataFrame) -> pd.DataFrame:
    m15 = load_processed_m15()
    window = m15[m15["date_dt"].between(PY_TARGET_TIME - pd.Timedelta(minutes=45), PY_TARGET_TIME + pd.Timedelta(minutes=15), inclusive="both")].copy()
    window = detect_m15_mode(window)
    slot_window_mask = window["date_dt"].between(PY_TARGET_TIME - pd.Timedelta(minutes=30), PY_TARGET_TIME, inclusive="right")
    old_stop = float(raw_row["stop"])
    accepted_stop = float(accepted_row["stop"])
    accepted_entry = float(accepted_row["entry"])

    rows: list[dict[str, object]] = []
    slot_rows = window[slot_window_mask].sort_values("date_dt").reset_index(drop=True)
    selected_first_time = slot_rows.iloc[0]["date_dt"] if not slot_rows.empty else pd.NaT
    selected_latest_time = slot_rows.iloc[-1]["date_dt"] if not slot_rows.empty else pd.NaT

    for _, row in window.iterrows():
        close = float(row["close"])
        sd_to_old = abs(close - old_stop)
        rows.append(
            {
                "source": "python_processed_m15",
                "processed_time": fmt_ts(row["date_dt"]),
                "raw_time_inferred": fmt_ts(row["raw_time_inferred_dt"]),
                "in_python_slot_window": bool(row["date_dt"] in set(slot_rows["date_dt"])),
                "python_current_first_choice": row["date_dt"] == selected_first_time,
                "ea_equivalent_latest_choice": row["date_dt"] == selected_latest_time,
                "close": round(close, 6),
                "SMA_5": round(float(row["SMA_5"]), 6),
                "SMA_13": round(float(row["SMA_13"]), 6),
                "sell_same_side": bool(row["sell_same_side"]),
                "gap_pct": round(float(row["gap_pct"]), 6) if pd.notna(row["gap_pct"]) else "",
                "ea_like_pre_cross": int(row["ea_like_pre_cross"]) if pd.notna(row["ea_like_pre_cross"]) else "",
                "ea_like_is_cross": bool(row["ea_like_is_cross"]),
                "sd_to_raw_stop_before_reanchor": round(sd_to_old, 6),
                "spec_to_raw_stop_before_reanchor": spec_reason(sd_to_old),
                "sell_stop_side_before_reanchor": "valid" if old_stop > close else "invalid",
            }
        )

    if not ea_diag.empty:
        ea = ea_diag.iloc[0]
        rows.append(
            {
                "source": "ea_diag_target_raw_anchor",
                "processed_time": fmt_ts(parse_dt_series(pd.Series([ea["completed_m15_open"]])).iloc[0] + pd.Timedelta(hours=2)),
                "raw_time_inferred": fmt_ts(ea["completed_m15_open_dt"]),
                "in_python_slot_window": "",
                "python_current_first_choice": "",
                "ea_equivalent_latest_choice": "",
                "close": round(float(ea["m15_close"]), 6),
                "SMA_5": "",
                "SMA_13": round(float(ea["m15_sma13"]), 6),
                "sell_same_side": bool(float(ea["m15_close"]) < float(ea["m15_sma13"])),
                "gap_pct": "",
                "ea_like_pre_cross": ea.get("pre_cross", ""),
                "ea_like_is_cross": ea.get("is_cross", ""),
                "sd_to_raw_stop_before_reanchor": "",
                "spec_to_raw_stop_before_reanchor": "",
                "sell_stop_side_before_reanchor": "",
                "ea_merged_post_n_counter": ea.get("merged_post_n_counter", ""),
                "ea_signal_dir": ea.get("signal_dir", ""),
                "ea_result": ea.get("result", ""),
            }
        )

    rows.append(
        {
            "source": "python_final_runtime_rescue",
            "processed_time": fmt_ts(accepted_row["entry_time"]),
            "raw_time_inferred": fmt_ts(pd.Timestamp(accepted_row["entry_time"]) - pd.Timedelta(hours=2)),
            "close": round(accepted_entry, 6),
            "SMA_5": "",
            "SMA_13": "",
            "sell_same_side": "",
            "sd_to_raw_stop_before_reanchor": round(abs(accepted_entry - old_stop), 6),
            "spec_to_raw_stop_before_reanchor": spec_reason(abs(accepted_entry - old_stop)),
            "sell_stop_side_before_reanchor": "valid" if old_stop > accepted_entry else "invalid",
            "accepted_reanchored_stop": round(accepted_stop, 6),
            "accepted_final_sd": round(float(accepted_row["sd"]), 6),
            "accepted_spec_reason": accepted_row.get("spec_reason", ""),
        }
    )
    return pd.DataFrame(rows)


def build_rescue_mechanics(raw_row: pd.Series, accepted_row: pd.Series, picked_row: pd.Series, stage_row: pd.Series, ea_diag: pd.DataFrame) -> pd.DataFrame:
    old_entry = float(raw_row["entry"])
    old_stop = float(raw_row["stop"])
    selected_entry = float(accepted_row["entry"])
    reanchored_stop = float(accepted_row["stop"])
    chooser_sd = abs(selected_entry - old_stop)
    old_stop_side_valid = old_stop > selected_entry
    rows = [
        {
            "step": "raw_m30_candidate",
            "time": fmt_ts(raw_row["date"]),
            "entry_time": fmt_ts(raw_row["entry_time"]),
            "mode": raw_row["mode"],
            "dir": raw_row["dir"],
            "entry": round(old_entry, 6),
            "stop": round(old_stop, 6),
            "sd": round(float(raw_row["sd"]), 6),
            "spec_reason": raw_row["spec_reason"],
            "meaning": "Python raw M30 pre_cross candidate is rejected before rescue.",
        },
        {
            "step": "slot1_chooser_pre_reanchor",
            "time": fmt_ts(accepted_row["date"]),
            "entry_time": fmt_ts(accepted_row["entry_time"]),
            "mode": accepted_row["mode"],
            "dir": accepted_row["dir"],
            "entry": round(selected_entry, 6),
            "stop": round(old_stop, 6),
            "sd": round(chooser_sd, 6),
            "spec_reason": spec_reason(chooser_sd),
            "meaning": "Python chooser checks same-side and absolute distance to the old stop, but not M15 signal mode or stop side.",
        },
        {
            "step": "runtime_rescue_reanchor",
            "time": fmt_ts(accepted_row["date"]),
            "entry_time": fmt_ts(accepted_row["entry_time"]),
            "mode": accepted_row["mode"],
            "dir": accepted_row["dir"],
            "entry": round(selected_entry, 6),
            "stop": round(reanchored_stop, 6),
            "sd": round(float(accepted_row["sd"]), 6),
            "spec_reason": accepted_row["spec_reason"],
            "meaning": "reanchor_stop_by_distance mirrors the stop to the valid SELL side after choosing the M15 entry.",
            "old_stop_side_before_reanchor": "valid" if old_stop_side_valid else "invalid",
        },
        {
            "step": "layer3_and_stage",
            "time": fmt_ts(picked_row["date"]),
            "entry_time": fmt_ts(picked_row["entry_time"]),
            "mode": picked_row["mode"],
            "dir": picked_row["dir"],
            "entry": round(float(picked_row["entry"]), 6),
            "stop": round(float(picked_row["stop"]), 6),
            "sd": round(float(picked_row["sd"]), 6),
            "spec_reason": picked_row["spec_reason"],
            "total_$": round(float(stage_row["total_$"]), 6),
            "meaning": "Python keeps the rescued row and books it as a M15 SLOT1 trade.",
        },
    ]
    if not ea_diag.empty:
        ea = ea_diag.iloc[0]
        rows.append(
            {
                "step": "ea_target_raw_anchor",
                "time": fmt_ts(ea["time_dt"]),
                "entry_time": fmt_ts(ea["completed_m15_open_dt"]),
                "mode": "none",
                "dir": "NONE",
                "entry": round(float(ea["m15_close"]), 6),
                "stop": "",
                "sd": "",
                "spec_reason": "",
                "ea_pre_cross": ea.get("pre_cross", ""),
                "ea_is_cross": ea.get("is_cross", ""),
                "ea_merged_post_n_counter": ea.get("merged_post_n_counter", ""),
                "ea_signal_dir": ea.get("signal_dir", ""),
                "ea_result": ea.get("result", ""),
                "meaning": "EA evaluates M15 signal mode at the raw anchor and writes NO_SIGNAL_DIR before stop/spec checks.",
            }
        )
    return pd.DataFrame(rows)


def build_m30_context() -> pd.DataFrame:
    m30 = read_csv(PROCESSED_M30_FILE)
    m30["date_dt"] = parse_dt_series(m30["date"])
    window = m30[m30["date_dt"].between("2025-10-17 09:30:00", "2025-10-17 11:30:00", inclusive="both")].copy()
    window = window.sort_values("date_dt").reset_index(drop=True)
    window["prev_close"] = window["close"].shift(1)
    window["prev_sma13"] = window["SMA_13"].shift(1)
    window["m30_gap_pct"] = (window["SMA_5"] - window["SMA_13"]).abs() / window["SMA_13"] * 100.0
    window["short_pre_cross_calc"] = (
        (window["prev_close"] >= window["prev_sma13"])
        & (window["close"] < window["SMA_13"])
        & (window["SMA_5"] > window["SMA_13"])
        & (window["m30_gap_pct"] <= PRE_GAP_PCT)
    )
    cols = [
        "date",
        "close",
        "SMA_5",
        "SMA_13",
        "方向",
        "方向_合并后",
        "merged_post_cross_n",
        "prev_close",
        "prev_sma13",
        "m30_gap_pct",
        "short_pre_cross_calc",
    ]
    return window[[col for col in cols if col in window.columns]].copy()


def build_evidence_summary(raw_row: pd.Series, accepted_row: pd.Series, ea_diag: pd.DataFrame) -> pd.DataFrame:
    ea = ea_diag.iloc[0] if not ea_diag.empty else {}
    return pd.DataFrame(
        [
            {
                "finding": "Python rescued a rejected M30 pre_cross, not a fresh EA M15 signal.",
                "evidence": (
                    f"raw spec_reason={raw_row['spec_reason']}; accepted variant={accepted_row['variant']}; "
                    f"accepted entry_time={fmt_ts(accepted_row['entry_time'])}"
                ),
            },
            {
                "finding": "Python chooser admits by same-side/distance before reanchoring stop.",
                "evidence": (
                    f"raw stop={float(raw_row['stop']):.5f}, selected entry={float(accepted_row['entry']):.5f}, "
                    f"reanchored stop={float(accepted_row['stop']):.5f}"
                ),
            },
            {
                "finding": "EA target anchor stops at signal-mode gate.",
                "evidence": (
                    f"pre_cross={ea.get('pre_cross', '')}, is_cross={ea.get('is_cross', '')}, "
                    f"merged_post_n_counter={ea.get('merged_post_n_counter', '')}, signal_dir={ea.get('signal_dir', '')}, "
                    f"result={ea.get('result', '')}"
                ),
            },
            {
                "finding": "This target is not an EA bug candidate.",
                "evidence": "EA does not mirror rejected M30 stops into a new M15 stop, and it does not inherit M30 pre_cross mode inside M15 SLOT1.",
            },
        ]
    )


def build_code_evidence() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "file": "scripts/_current_baseline.py",
                "line": "75-85",
                "evidence": "current mainline rescues all spec-failed runtime rows and passes reanchor_stop_by_distance=True.",
            },
            {
                "file": "scripts/_m15_early_entry_test.py",
                "line": "304-314",
                "evidence": "choose_slot1_by_distance checks same-side and distance only; it does not validate stop side or M15 signal mode.",
            },
            {
                "file": "scripts/_m15_early_entry_test.py",
                "line": "341-349",
                "evidence": "recalc_trade mirrors the stop around the chosen entry when reanchor_stop_by_distance=True.",
            },
            {
                "file": "auto_trade/30m2H_Strategy_EA.mq5",
                "line": "2840-2874",
                "evidence": "EA computes M15 pre_cross/cross/post_n first and writes NO_SIGNAL_DIR when signal_dir remains zero.",
            },
        ]
    )


def build_report(
    mechanics: pd.DataFrame,
    py_chain: pd.DataFrame,
    ea_target: pd.DataFrame,
    m15_cmp: pd.DataFrame,
    m30_ctx: pd.DataFrame,
    evidence: pd.DataFrame,
    code: pd.DataFrame,
) -> str:
    lines = [
        "# 2025-10-17 M15 SLOT1 NO_SIGNAL_DIR review",
        "",
        "## Conclusion",
        "",
        "- `2025-10-17 11:00:00` is a Python-only runtime rescue admission, not an EA-equivalent M15 SLOT1 signal.",
        "- Python starts from a rejected M30 `pre_cross`, chooses the first M15 row in the slot window by same-side/distance, then reanchors the stop around that M15 entry.",
        "- EA evaluates M15 `pre_cross/is_cross/post_n` at the raw anchor. For raw `2025-10-17 09:30:00`, `pre_cross=false`, `is_cross=false`, `merged_post_n_counter=121`, so `signal_dir=0` and `result=NO_SIGNAL_DIR` before stop/spec.",
        "- The repair should be in Python-MT5 runtime_rescue admission rules, not in EA signal_dir logic.",
        "",
        "## Rescue Mechanics",
        "",
        markdown_table(mechanics),
        "",
        "## EA Target Row",
        "",
        markdown_table(
            ea_target,
            [
                "stable_case",
                "python_target_time",
                "mt5_raw_anchor_time",
                "diag_time",
                "completed_m15_open",
                "anchor_time",
                "stage_count",
                "max_pos",
                "pre_cross",
                "is_cross",
                "merged_post_n_counter",
                "signal_dir",
                "dir",
                "signal_src",
                "result",
                "detail",
                "m15_close",
                "m15_sma13",
            ],
        ),
        "",
        "## M15 Window",
        "",
        markdown_table(
            m15_cmp,
            [
                "source",
                "processed_time",
                "raw_time_inferred",
                "in_python_slot_window",
                "python_current_first_choice",
                "ea_equivalent_latest_choice",
                "close",
                "SMA_13",
                "sell_same_side",
                "ea_like_pre_cross",
                "ea_like_is_cross",
                "sd_to_raw_stop_before_reanchor",
                "spec_to_raw_stop_before_reanchor",
                "sell_stop_side_before_reanchor",
                "accepted_reanchored_stop",
                "accepted_final_sd",
                "ea_merged_post_n_counter",
                "ea_signal_dir",
                "ea_result",
            ],
        ),
        "",
        "## M30 Context",
        "",
        markdown_table(m30_ctx),
        "",
        "## Python Chain Window",
        "",
        markdown_table(py_chain),
        "",
        "## Evidence Summary",
        "",
        markdown_table(evidence),
        "",
        "## Code Evidence",
        "",
        markdown_table(code),
        "",
        "## Next Step",
        "",
        "- Prototype a Python-MT5 admission guard for `ea_slot1_runtime_rescue`: require an EA-like M15 mode at the selected slot row, or restrict runtime rescue so it cannot create a signal by inheriting M30 mode and mirroring the stop.",
        "- Run the prototype through the same full-chain dynamic-risk and mapped-ledger comparison before changing the mainline.",
    ]
    return "\n".join(lines)


def main() -> None:
    frames = load_python_signal_chain()
    raw_row, accepted_row, picked_row, stage_row = get_target_rows(frames)
    ea_target, ea_window = load_ea_diag()

    py_chain = python_chain_window(frames)
    mechanics = build_rescue_mechanics(raw_row, accepted_row, picked_row, stage_row, ea_target)
    m15_cmp = build_m15_window_comparison(raw_row, accepted_row, ea_target)
    m30_ctx = build_m30_context()
    evidence = build_evidence_summary(raw_row, accepted_row, ea_target)
    code = build_code_evidence()

    export_csv(py_chain, OUT_DIR / "python_signal_chain_window_20251017.csv")
    export_csv(normalize_for_export(ea_target), OUT_DIR / "ea_target_diag_row_20251017.csv")
    export_csv(normalize_for_export(ea_window), OUT_DIR / "ea_diag_window_20251017.csv")
    export_csv(mechanics, OUT_DIR / "python_runtime_rescue_mechanics_20251017.csv")
    export_csv(m15_cmp, OUT_DIR / "m15_window_mode_comparison_20251017.csv")
    export_csv(m30_ctx, OUT_DIR / "m30_context_20251017.csv")
    export_csv(evidence, OUT_DIR / "root_cause_evidence_20251017.csv")
    export_csv(code, OUT_DIR / "code_evidence_20251017.csv")

    report = build_report(mechanics, py_chain, normalize_for_export(ea_target), m15_cmp, m30_ctx, evidence, code)
    write_text(OUT_DIR / "m15_slot1_no_signal_dir_review.md", report)
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# m15_slot1_no_signal_dir_review_20260715",
                "",
                "Purpose: explain why Python accepts the 2025-10-17 M15 SLOT1 runtime_rescue while EA reports NO_SIGNAL_DIR.",
                "",
                "Primary report: `m15_slot1_no_signal_dir_review.md`.",
            ]
        ),
    )
    print(evidence.to_string(index=False))
    print(f"Wrote {OUT_DIR}")


if __name__ == "__main__":
    main()
