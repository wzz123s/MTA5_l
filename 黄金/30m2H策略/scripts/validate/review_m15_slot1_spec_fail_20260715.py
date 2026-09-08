# -*- coding: utf-8 -*-
"""Review the 2025-10-21 M15 SLOT1 SPEC_FAIL against Python slot selection."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"

SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "python_h2_context_q2early"
DIAG_REVIEW_DIR = VALIDATION_DIR / "ea_m15_entry_diag_full_review_20260715"
OUT_DIR = VALIDATION_DIR / "m15_slot1_spec_fail_review_20260715"

RAW_M15_FILE = DATA_DIR / "raw" / "XAUUSDm15.csv"
PROCESSED_M15_FILE = DATA_DIR / "processed" / "m15_context_bars.csv"
PY_DYNAMIC_INPUTS = (
    VALIDATION_DIR
    / "dynamic_risk_inputs_shift90_metadatafix_20260714"
    / "python_mt5_dynamic_risk_inputs.csv"
)

PY_TARGET_TIME = pd.Timestamp("2025-10-21 10:00:00")
EA_RAW_ANCHOR = pd.Timestamp("2025-10-21 08:30:00")
EA_COMPLETED_M15_RAW = pd.Timestamp("2025-10-21 08:00:00")
TARGET_CASE = "far_runtime_rescue_20251021_postn6"
SPEC_LO = 5.0
SPEC_HI = 35.0


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


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None) -> str:
    if frame.empty:
        return "_No rows._"
    if columns is not None:
        frame = frame[[col for col in columns if col in frame.columns]]
    return frame.to_markdown(index=False)


def spec_reason(sd: float) -> str:
    if SPEC_LO <= sd <= SPEC_HI:
        return "ok"
    if sd > SPEC_HI:
        return "too_wide"
    return "too_tight"


def load_python_signal_chain() -> dict[str, pd.DataFrame]:
    files = {
        "raw_candidates": SIGNAL_DIR / "raw_candidates.csv",
        "layer12_accepted": SIGNAL_DIR / "候选信号_Layer1_Layer2通过.csv",
        "layer3_picked": SIGNAL_DIR / "最终信号_Layer3入选.csv",
        "stage_results": SIGNAL_DIR / "执行交易_Stage结果.csv",
        "dynamic_inputs": PY_DYNAMIC_INPUTS,
    }
    out: dict[str, pd.DataFrame] = {}
    for name, path in files.items():
        df = read_csv(path)
        if "date" in df.columns:
            df["date_dt"] = parse_dt_series(df["date"])
        if "entry_time" in df.columns:
            df["entry_time_dt"] = parse_dt_series(df["entry_time"])
        out[name] = df
    return out


def window_by_date(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    if "date_dt" not in df.columns:
        return pd.DataFrame()
    return df[df["date_dt"].between(pd.Timestamp(start), pd.Timestamp(end), inclusive="both")].copy()


def load_ea_diag() -> tuple[pd.DataFrame, pd.DataFrame]:
    target = read_csv(DIAG_REVIEW_DIR / "target_m15_entry_diag_rows.csv")
    window = read_csv(DIAG_REVIEW_DIR / "target_m15_entry_diag_windows.csv")
    return (
        target[target["stable_case"].eq(TARGET_CASE)].copy(),
        window[window["stable_case"].eq(TARGET_CASE)].copy(),
    )


def load_m15_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = read_csv(RAW_M15_FILE, encoding="gbk")
    raw = raw.rename(
        columns={
            "交易日期": "raw_time",
            "开盘价": "open",
            "最高价": "high",
            "最低价": "low",
            "收盘价": "close",
        }
    )
    raw["raw_time_dt"] = parse_dt_series(raw["raw_time"])
    processed = read_csv(PROCESSED_M15_FILE)
    processed["date_dt"] = parse_dt_series(processed["date"])
    return raw, processed


def python_chain_window(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    cols = [
        "layer",
        "date",
        "entry_time",
        "mode",
        "dir",
        "variant",
        "trigger",
        "entry",
        "stop",
        "sd",
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
    ]
    for layer, df in frames.items():
        window = window_by_date(df, "2025-10-21 06:00:00", "2025-10-21 10:30:00")
        if window.empty:
            continue
        window.insert(0, "layer", layer)
        rows.append(window)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    return out[[col for col in cols if col in out.columns]].copy()


def build_slot_comparison(frames: dict[str, pd.DataFrame], raw_m15: pd.DataFrame, processed_m15: pd.DataFrame, ea_diag: pd.DataFrame) -> pd.DataFrame:
    dyn = frames["dynamic_inputs"]
    py_row = dyn[(dyn["date_dt"].eq(PY_TARGET_TIME)) & dyn["variant"].eq("ea_slot1_runtime_rescue")].iloc[0]
    stop = float(py_row["stop"])

    processed_window = processed_m15[
        processed_m15["date_dt"].between(PY_TARGET_TIME - pd.Timedelta(minutes=30), PY_TARGET_TIME, inclusive="right")
    ].sort_values("date_dt")

    rows: list[dict[str, object]] = []
    for label, row in [
        ("python_current_selected_first", processed_window.iloc[0]),
        ("ea_equivalent_latest_completed", processed_window.iloc[-1]),
    ]:
        entry = float(row["close"])
        sd = abs(entry - stop)
        rows.append(
            {
                "source": label,
                "axis_time": row["date_dt"].strftime("%Y-%m-%d %H:%M:%S"),
                "raw_time_inferred": (row["date_dt"] - pd.Timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
                "entry_close": round(entry, 6),
                "stop_used": round(stop, 6),
                "sd_to_python_stop": round(sd, 6),
                "spec_reason_to_python_stop": spec_reason(sd),
                "sma13": round(float(row["SMA_13"]), 6) if "SMA_13" in row else "",
            }
        )

    raw_window = raw_m15[
        raw_m15["raw_time_dt"].between(EA_COMPLETED_M15_RAW - pd.Timedelta(minutes=15), EA_COMPLETED_M15_RAW, inclusive="both")
    ].sort_values("raw_time_dt")
    for _, row in raw_window.iterrows():
        entry = float(row["close"])
        sd = abs(entry - stop)
        rows.append(
            {
                "source": "raw_m15_reference",
                "axis_time": "",
                "raw_time_inferred": row["raw_time_dt"].strftime("%Y-%m-%d %H:%M:%S"),
                "entry_close": round(entry, 6),
                "stop_used": round(stop, 6),
                "sd_to_python_stop": round(sd, 6),
                "spec_reason_to_python_stop": spec_reason(sd),
                "sma13": "",
            }
        )

    if not ea_diag.empty:
        ea = ea_diag.iloc[0]
        rows.append(
            {
                "source": "ea_diag_actual",
                "axis_time": "",
                "raw_time_inferred": str(ea.get("completed_m15_open", "")),
                "entry_close": round(float(ea["m15_close"]), 6),
                "stop_used": round(float(ea["stop_price"]), 6),
                "sd_to_python_stop": "",
                "spec_reason_to_python_stop": "",
                "sma13": round(float(ea["m15_sma13"]), 6),
                "ea_stop_pts_spec": round(float(ea["stop_pts_spec"]), 6),
                "ea_result": ea.get("result", ""),
                "ea_detail": ea.get("detail", ""),
            }
        )

    return pd.DataFrame(rows)


def code_evidence() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "file": "scripts/_m15_early_entry_test.py",
                "line": "256-259",
                "evidence": "m15_window returns rows in (anchor_time-30m, anchor_time] sorted ascending.",
            },
            {
                "file": "scripts/_m15_early_entry_test.py",
                "line": "304-314",
                "evidence": "choose_slot1_by_distance uses seg.iloc[0], the earliest row in that 30-minute window.",
            },
            {
                "file": "auto_trade/30m2H_Strategy_EA.mq5",
                "line": "2655, 2699-2711, 2731",
                "evidence": "EA uses iTime(M15,1), maps it to slot_in_m30, and sets anchor_time=slot_m30_open+M30.",
            },
            {
                "file": "auto_trade/30m2H_Strategy_EA.mq5",
                "line": "2742-2763, 2935-2975",
                "evidence": "EA stop/spec uses completed M15 close and M30 ctx SMA13, then blocks outside InpStopLo/InpStopHi.",
            },
        ]
    )


def build_report(py_chain: pd.DataFrame, ea_diag: pd.DataFrame, slot_cmp: pd.DataFrame, evidence: pd.DataFrame) -> str:
    py_cols = [
        "layer",
        "date",
        "entry_time",
        "mode",
        "dir",
        "variant",
        "trigger",
        "entry",
        "stop",
        "sd",
        "spec_pass",
        "spec_reason",
        "layer3_eval_time",
        "layer3_pass_ea",
        "total_$",
    ]
    ea_cols = [
        "diag_time",
        "completed_m15_open",
        "anchor_time",
        "signal_src",
        "m15_close",
        "m15_sma13",
        "stop_price",
        "stop_pts_spec",
        "result",
        "detail",
    ]
    lines = [
        "# M15 SLOT1 SPEC_FAIL review - 2025-10-21",
        "",
        "## 结论",
        "",
        "- Python-MT5 当前接受的是 `date=2025-10-21 10:00:00`、`entry_time=2025-10-21 09:45:00`、`sd=32.32603` 的 `ea_slot1_runtime_rescue`。",
        "- EA full-history diag 对应 raw anchor `2025-10-21 08:30:00` 的 M15 slot1 使用 `completed_m15_open=2025.10.21 08:00`，`m15_close=4244.872`，`stop_pts_spec=84.189`，结果 `SPEC_FAIL_PROXY`。",
        "- 在当前 Python shifted M15 数据中，EA 对应的 completed bar 是 `date=2025-10-21 10:00:00`；当前 Python `choose_slot1_by_distance()` 取的是窗口内第一根 `09:45`，不是 EA 对应的 latest completed bar `10:00`。",
        "- 因此该 SPEC_FAIL 的主要原因是 Python-MT5 M15 SLOT1 选 bar 语义与 EA 不一致；不应改 EA spec gate。",
        "- 后续应先做版本化 prototype：把 `ea_slot1_replace` 和 `ea_slot1_runtime_rescue` 的 slot1 chooser 从 `seg.iloc[0]` 改为 EA-equivalent latest completed bar，再重跑 dynamic risk / mapping / remaining diff。",
        "",
        "## Python signal chain",
        "",
        markdown_table(py_chain, py_cols),
        "",
        "## EA target diagnostic row",
        "",
        markdown_table(ea_diag, ea_cols),
        "",
        "## Slot candidate comparison",
        "",
        markdown_table(slot_cmp),
        "",
        "## Code evidence",
        "",
        markdown_table(evidence),
    ]
    return "\n".join(lines)


def write_readme() -> None:
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# m15_slot1_spec_fail_review_20260715",
                "",
                "Purpose: explain why Python accepted the 2025-10-21 M15 SLOT1 runtime_rescue while EA blocked the raw anchor with SPEC_FAIL_PROXY.",
                "",
                "Primary report: `m15_slot1_spec_fail_review.md`.",
            ]
        ),
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frames = load_python_signal_chain()
    ea_diag, ea_window = load_ea_diag()
    raw_m15, processed_m15 = load_m15_frames()

    py_chain = python_chain_window(frames)
    slot_cmp = build_slot_comparison(frames, raw_m15, processed_m15, ea_diag)
    evidence = code_evidence()

    export_csv(py_chain, OUT_DIR / "python_signal_chain_20251021.csv")
    export_csv(ea_diag, OUT_DIR / "ea_target_diag_20251021.csv")
    export_csv(ea_window, OUT_DIR / "ea_diag_window_20251021.csv")
    export_csv(slot_cmp, OUT_DIR / "m15_slot_candidate_comparison_20251021.csv")
    export_csv(evidence, OUT_DIR / "code_evidence.csv")
    write_text(OUT_DIR / "m15_slot1_spec_fail_review.md", build_report(py_chain, ea_diag, slot_cmp, evidence))
    write_readme()

    print(f"Wrote {OUT_DIR}")
    print(slot_cmp.to_string(index=False))


if __name__ == "__main__":
    main()
