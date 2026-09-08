# -*- coding: utf-8 -*-
"""Review EA signal gate evidence for far-candidate runtime rescue rows."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "ea_signal_gate_lifecycle_review_20260714"

EA_FILE = ROOT / "auto_trade" / "30m2H_Strategy_EA.mq5"
FAR_DIR = VALIDATION_DIR / "far_candidate_runtime_rescue_review_20260714"
LEDGER_FILE = VALIDATION_DIR / "ea_stage2_trail_ledger_full_20260714" / "30m2H_strategy_trade_ledger.csv"
SIGNALS_EXPORT_FILE = (
    VALIDATION_DIR
    / "ea_stage2_trail_ledger_full_20260714"
    / "30m2H_strategy_signals_export.csv"
)

INP_MAX_POS = 3


TARGETS = [
    {
        "stable_case": "far_runtime_rescue_20251021_postn6",
        "original_trade_id": "python_mt5_0079",
        "filtered_trade_id": "python_mt5_0078",
        "python_target_time": "2025-10-21 10:00:00",
        "mt5_raw_anchor_time": "2025-10-21 08:30:00",
        "trigger_family": "M15 SLOT1",
        "mode_family": "post_n",
        "mode": "post_n6",
        "dir_norm": "SELL",
    },
    {
        "stable_case": "far_runtime_rescue_20251017_precross",
        "original_trade_id": "python_mt5_0073",
        "filtered_trade_id": "python_mt5_0073",
        "python_target_time": "2025-10-17 11:00:00",
        "mt5_raw_anchor_time": "2025-10-17 09:30:00",
        "trigger_family": "M15 SLOT1",
        "mode_family": "pre_cross",
        "mode": "pre_cross",
        "dir_norm": "SELL",
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


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None) -> str:
    if frame.empty:
        return "_No rows._"
    if columns is not None:
        cols = [col for col in columns if col in frame.columns]
        if not cols:
            return "_No columns._"
        frame = frame[cols]
    return frame.to_markdown(index=False)


def load_ledger() -> pd.DataFrame:
    df = read_csv(LEDGER_FILE).copy()
    df["open_dt"] = df["open_time"].map(to_dt)
    df["exit_dt"] = df["exit_time"].map(to_dt)
    df["signal_anchor_dt"] = df["signal_anchor_time"].map(to_dt)
    df["dir_norm"] = df["dir"].map(normalize_dir)
    return df


def load_signals_export() -> pd.DataFrame:
    df = read_csv(SIGNALS_EXPORT_FILE).copy()
    df["bar_dt"] = df["bar_time"].map(to_dt)
    return df


def load_python_windows() -> pd.DataFrame:
    return read_csv(FAR_DIR / "far_candidate_python_signal_windows.csv")


def load_far_summary() -> pd.DataFrame:
    return read_csv(FAR_DIR / "far_candidate_runtime_rescue_summary.csv")


def active_positions_at(ledger: pd.DataFrame, probe_time: pd.Timestamp) -> pd.DataFrame:
    active = ledger[(ledger["open_dt"] <= probe_time) & (ledger["exit_dt"] >= probe_time)].copy()
    active["probe_time"] = probe_time
    return active


def source_line_numbers() -> dict[str, int]:
    lines = EA_FILE.read_text(encoding="utf-8", errors="replace").splitlines()

    def first(pattern: str, start: int = 0) -> int:
        for idx in range(start, len(lines)):
            if pattern in lines[idx]:
                return idx + 1
        return 0

    m15_start = first("bool TryM15EarlyEntry")
    m30_start = first("// --- v3.0 CHECK NEW SIGNAL")
    csv_start = first("string decision  = \"HOLD\"")
    diag_start = first("void DiagLog")
    return {
        "inp_max_pos": first("input int     InpMaxPos"),
        "our_stage_count_start": first("int OurStageCount()"),
        "our_stage_count_end": first("return cnt;", first("int OurStageCount()")),
        "has_pos_dir_start": first("bool HasPosDir"),
        "try_m15_start": m15_start,
        "m15_max_pos_gate": first("if(OurStageCount() >= InpMaxPos)", m15_start),
        "m15_same_anchor_return": first("if(g_signal_anchor_time == anchor_time) return false;", m15_start),
        "m15_signal_dir_silent_return": first("if(signal_dir == 0) return false;", m15_start),
        "m15_candidate_diag_after_signal": first("DiagLog(log_tag, \"Candidate\"", m15_start),
        "signals_export_decision_start": csv_start,
        "signals_export_max_pos": first("else if(OurStageCount() >= InpMaxPos)", csv_start),
        "m30_max_pos_gate": first("if(OurStageCount() >= InpMaxPos)", m30_start),
        "diaglog_print_only": first("Print(tag, \" [DIAG] \", phase, \" | \", detail);", diag_start),
    }


def build_code_evidence() -> pd.DataFrame:
    ln = source_line_numbers()
    rows = [
        {
            "evidence": "InpMaxPos",
            "lines": str(ln["inp_max_pos"]),
            "meaning": "EA input max concurrent stage positions is 3 in current source.",
        },
        {
            "evidence": "OurStageCount",
            "lines": f"{ln['our_stage_count_start']}-{ln['our_stage_count_end']}",
            "meaning": "Counts real open stage positions with magic InpMagic+1..InpMagic+3.",
        },
        {
            "evidence": "HasPosDir",
            "lines": str(ln["has_pos_dir_start"]),
            "meaning": "Checks only InpMagic base positions and is not the M15/M30 signal gate used here.",
        },
        {
            "evidence": "M15 max-pos gate",
            "lines": str(ln["m15_max_pos_gate"]),
            "meaning": "TryM15EarlyEntry returns SKIP_MAX_POS only when OurStageCount() >= InpMaxPos.",
        },
        {
            "evidence": "M15 same-anchor silent return",
            "lines": str(ln["m15_same_anchor_return"]),
            "meaning": "A repeated anchor returns false without CSV evidence.",
        },
        {
            "evidence": "M15 no-signal silent return",
            "lines": str(ln["m15_signal_dir_silent_return"]),
            "meaning": "If M15 pre/cross/post_n mode is absent, the function returns false before Candidate diag.",
        },
        {
            "evidence": "M15 Candidate diag",
            "lines": str(ln["m15_candidate_diag_after_signal"]),
            "meaning": "Candidate diagnostics start only after signal_dir is non-zero.",
        },
        {
            "evidence": "M30 signals_export",
            "lines": f"{ln['signals_export_decision_start']}-{ln['signals_export_max_pos']}",
            "meaning": "Per-bar CSV records coarse M30 decision and max_pos only, not all M15 early-entry silent returns.",
        },
        {
            "evidence": "M30 max-pos gate",
            "lines": str(ln["m30_max_pos_gate"]),
            "meaning": "M30 close also skips when OurStageCount() >= InpMaxPos, after M15 early-entry has already been tried.",
        },
        {
            "evidence": "DiagLog target",
            "lines": str(ln["diaglog_print_only"]),
            "meaning": "Verbose gate diagnostics are printed to tester/journal, not exported to the current CSV set.",
        },
    ]
    return pd.DataFrame(rows)


def signal_window(signals_export: pd.DataFrame, target: pd.Timestamp, stable_case: str) -> pd.DataFrame:
    window = signals_export[
        (signals_export["bar_dt"] >= target - pd.Timedelta(minutes=240))
        & (signals_export["bar_dt"] <= target + pd.Timedelta(minutes=240))
    ].copy()
    window.insert(0, "stable_case", stable_case)
    window["minutes_from_raw_anchor"] = (window["bar_dt"] - target).dt.total_seconds() / 60.0
    return window.sort_values("bar_dt").reset_index(drop=True)


def exact_bar_row(signals_export: pd.DataFrame, target: pd.Timestamp) -> pd.Series:
    exact = signals_export[signals_export["bar_dt"] == target]
    if exact.empty:
        return pd.Series(dtype=object)
    return exact.iloc[0]


def python_target_chain(python_windows: pd.DataFrame, target_def: dict[str, str]) -> pd.DataFrame:
    cur = python_windows[
        (python_windows["stable_case"].astype(str) == target_def["stable_case"])
        & (python_windows["date"].astype(str) == target_def["python_target_time"])
    ].copy()
    return cur.reset_index(drop=True)


def classify_row(active_eval_count: int, decision: str, skip_reason: str) -> tuple[str, str]:
    if active_eval_count >= INP_MAX_POS:
        return (
            "max_pos_gate_supported_by_ledger_proxy",
            "Existing ledger positions already reach InpMaxPos at the M15 evaluation time.",
        )
    if decision == "SIGNAL":
        return (
            "successful_signal_anchor_already_recorded",
            "signals_export says this raw anchor already had a successful signal; inspect mapping.",
        )
    if skip_reason == "max_pos":
        return (
            "csv_max_pos_but_ledger_proxy_disagrees",
            "signals_export reports max_pos while ledger proxy is below threshold; needs tester/journal check.",
        )
    return (
        "m15_candidate_absent_or_silent_gate_unresolved",
        "M30 CSV shows no successful anchor signal and ledger proxy is below max_pos; current exports cannot tell whether M15 candidate was absent or silently gated.",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ledger = load_ledger()
    signals_export = load_signals_export()
    python_windows = load_python_windows()
    far_summary = load_far_summary()

    summary_rows: list[dict[str, object]] = []
    signal_windows: list[pd.DataFrame] = []
    active_frames: list[pd.DataFrame] = []
    python_chain_frames: list[pd.DataFrame] = []

    for target_def in TARGETS:
        stable_case = target_def["stable_case"]
        py_time = pd.Timestamp(target_def["python_target_time"])
        raw_anchor = pd.Timestamp(target_def["mt5_raw_anchor_time"])
        # M15 slot1 uses the first completed M15 bar of the M30 anchor; it is evaluated
        # around raw_anchor - 15 minutes when the next M15 bar opens.
        m15_eval_time = raw_anchor - pd.Timedelta(minutes=15)

        exact = exact_bar_row(signals_export, raw_anchor)
        decision = str(exact.get("decision", "")) if not exact.empty else ""
        skip_reason = str(exact.get("skip_reason", "")) if not exact.empty else ""
        m30_cross = str(exact.get("m30_cross", "")) if not exact.empty else ""
        h2_cross = str(exact.get("h2_cross", "")) if not exact.empty else ""
        h2_dir = str(exact.get("h2_dir", "")) if not exact.empty else ""

        active_anchor = active_positions_at(ledger, raw_anchor)
        active_anchor.insert(0, "stable_case", stable_case)
        active_anchor.insert(1, "probe_kind", "raw_anchor")
        active_frames.append(active_anchor)

        active_eval = active_positions_at(ledger, m15_eval_time)
        active_eval.insert(0, "stable_case", stable_case)
        active_eval.insert(1, "probe_kind", "m15_slot1_eval")
        active_frames.append(active_eval)

        sig_win = signal_window(signals_export, raw_anchor, stable_case)
        signal_windows.append(sig_win)

        py_chain = python_target_chain(python_windows, target_def)
        py_chain.insert(0, "stable_case_key", stable_case)
        python_chain_frames.append(py_chain)

        far = far_summary[far_summary["stable_case"].astype(str) == stable_case]
        same_trigger_240 = (
            int(far["mt5_same_trigger_mode_rows_within_240m"].iloc[0])
            if not far.empty and "mt5_same_trigger_mode_rows_within_240m" in far.columns
            else 0
        )
        filtered_profit = (
            far["filtered_trade_profit"].iloc[0]
            if not far.empty and "filtered_trade_profit" in far.columns
            else ""
        )

        classification, next_action = classify_row(len(active_eval), decision, skip_reason)
        summary_rows.append(
            {
                "stable_case": stable_case,
                "original_trade_id": target_def["original_trade_id"],
                "filtered_trade_id": target_def["filtered_trade_id"],
                "python_target_time": py_time,
                "mt5_raw_anchor_time": raw_anchor,
                "m15_slot1_eval_time": m15_eval_time,
                "dir_norm": target_def["dir_norm"],
                "trigger_family": target_def["trigger_family"],
                "mode": target_def["mode"],
                "filtered_trade_profit": filtered_profit,
                "signals_export_decision_at_raw_anchor": decision,
                "signals_export_skip_reason_at_raw_anchor": skip_reason,
                "m30_cross_at_raw_anchor": m30_cross,
                "h2_cross_at_raw_anchor": h2_cross,
                "h2_dir_at_raw_anchor": h2_dir,
                "mt5_same_trigger_mode_rows_within_240m": same_trigger_240,
                "active_stage_rows_at_raw_anchor": len(active_anchor),
                "active_stage_rows_at_m15_eval": len(active_eval),
                "inp_max_pos": INP_MAX_POS,
                "ledger_proxy_supports_max_pos_gate": len(active_eval) >= INP_MAX_POS,
                "classification": classification,
                "next_action": next_action,
            }
        )

    summary = pd.DataFrame(summary_rows)
    code_evidence = build_code_evidence()
    all_signal_windows = pd.concat(signal_windows, ignore_index=True) if signal_windows else pd.DataFrame()
    active_all = pd.concat(active_frames, ignore_index=True) if active_frames else pd.DataFrame()
    python_chain_all = pd.concat(python_chain_frames, ignore_index=True) if python_chain_frames else pd.DataFrame()

    export_csv(code_evidence, OUT_DIR / "ea_gate_code_evidence.csv")
    export_csv(summary, OUT_DIR / "target_gate_lifecycle_summary.csv")
    export_csv(all_signal_windows, OUT_DIR / "target_signals_export_windows.csv")
    export_csv(active_all, OUT_DIR / "target_active_positions_by_probe_time.csv")
    export_csv(python_chain_all, OUT_DIR / "python_target_signal_chain.csv")

    report = [
        "# EA Signal Gate Lifecycle Review 20260714",
        "",
        "## Summary",
        "",
        markdown_table(
            summary,
            [
                "stable_case",
                "python_target_time",
                "mt5_raw_anchor_time",
                "m15_slot1_eval_time",
                "mode",
                "filtered_trade_profit",
                "signals_export_decision_at_raw_anchor",
                "signals_export_skip_reason_at_raw_anchor",
                "active_stage_rows_at_m15_eval",
                "ledger_proxy_supports_max_pos_gate",
                "classification",
            ],
        ),
        "",
        "## Code Evidence",
        "",
        markdown_table(code_evidence),
        "",
        "## Active Positions At Probe Times",
        "",
        markdown_table(
            active_all,
            [
                "stable_case",
                "probe_kind",
                "probe_time",
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
        "- Current evidence weakens the previous pure position-occupancy explanation: both target M15 evaluation times have 2 active stage rows, below InpMaxPos=3.",
        "- The M30 signals_export rows at the raw anchors are SKIP/no_cross_m30_or_h2, so they only prove no successful signal was registered for that anchor; they do not explain the M15 early-entry path.",
        "- Because TryM15EarlyEntry has silent returns before Candidate diagnostics, current exports cannot distinguish absent M15 mode from same-anchor, slot, Layer, stop/spec, or quote gates.",
        "- Next repair step should add a non-trading M15 early-entry diagnostic export around every new_m15_bar before changing trading behavior.",
    ]
    write_text(OUT_DIR / "ea_signal_gate_lifecycle_review.md", "\n".join(report))
    write_text(
        OUT_DIR / "README.md",
        "# ea_signal_gate_lifecycle_review_20260714\n\nEvidence review for EA signal skip / position gate lifecycle on the two far-candidate runtime_rescue rows.",
    )

    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
