# -*- coding: utf-8 -*-
"""Review EA multi-slot stage-state fix smoke/full regression results."""
from __future__ import annotations


import re
from pathlib import Path

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
BASELINE_DIR = VALIDATION_DIR / "mt5_full_close_retry_fix_20260714"
SMOKE_SHORT_DIR = VALIDATION_DIR / "mt5_stage_state_smoke_20221108_20221116_20260716"
SMOKE_EXT_DIR = VALIDATION_DIR / "mt5_stage_state_smoke_20221108_20221125_20260716"
FULL_DIR = VALIDATION_DIR / "mt5_stage_state_full_2018_20260707_20260716"
OUT_DIR = VALIDATION_DIR / "stage_state_fix_regression_review_20260716"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def markdown_table(frame: pd.DataFrame, max_rows: int = 40) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def num_series(frame: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(frame[col], errors="coerce").fillna(0.0)


def deinit_mask(frame: pd.DataFrame) -> pd.Series:
    local = frame.get("local_exit_reason", pd.Series("", index=frame.index)).astype(str).str.lower()
    comment = frame.get("deal_comment", pd.Series("", index=frame.index)).astype(str).str.lower()
    return local.eq("deinit_history") | comment.str.contains("end of test", na=False)


def ledger_summary(name: str, directory: Path, final_balance: float | None = None) -> dict[str, object]:
    ledger = read_csv(directory / "30m2H_strategy_trade_ledger.csv")
    deals = read_csv(directory / "30m2H_strategy_deal_history.csv")
    out = deals[deals["deal_entry"].astype(str).isin(["OUT", "OUT_BY", "INOUT"])].copy()
    out_net = num_series(out, "profit") + num_series(out, "swap") + num_series(out, "commission")
    net = float(num_series(ledger, "net_profit").sum())
    return {
        "snapshot": name,
        "ledger_rows": int(len(ledger)),
        "unique_anchors": int(ledger["signal_anchor_time"].nunique()) if "signal_anchor_time" in ledger.columns else 0,
        "deinit_rows": int(deinit_mask(ledger).sum()),
        "ledger_net_sum": net,
        "deal_out_rows": int(len(out)),
        "deal_out_net_sum": float(out_net.sum()),
        "ledger_vs_deal_net_gap": net - float(out_net.sum()),
        "final_balance": final_balance if final_balance is not None else "",
        "final_net_profit": final_balance - 500.0 if final_balance is not None else "",
        "ledger_vs_final_net_gap": net - (final_balance - 500.0) if final_balance is not None else "",
    }


def latest_final_balance(log_path: Path) -> float | None:
    if not log_path.exists():
        return None
    raw = log_path.read_bytes()
    if raw.startswith(b"\xff\xfe") or b"f\x00i\x00n\x00a\x00l\x00 \x00b\x00a\x00l\x00a\x00n\x00c\x00e" in raw:
        text = raw.decode("utf-16", errors="ignore")
    else:
        text = raw.decode("utf-8", errors="ignore")
    matches = re.findall(r"final balance\s+([0-9.]+)\s+USD", text)
    if not matches:
        return None
    return float(matches[-1])


def compare_full_to_baseline() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    old = read_csv(BASELINE_DIR / "30m2H_strategy_trade_ledger.csv")
    new = read_csv(FULL_DIR / "30m2H_strategy_trade_ledger.csv")
    cols = ["signal_anchor_time", "trigger_tag", "signal_src", "dir", "stage"]
    old_g = (
        old.groupby(cols, dropna=False)
        .agg(old_rows=("stage", "count"), old_net=("net_profit", lambda s: pd.to_numeric(s, errors="coerce").sum()))
        .reset_index()
    )
    new_g = (
        new.groupby(cols, dropna=False)
        .agg(new_rows=("stage", "count"), new_net=("net_profit", lambda s: pd.to_numeric(s, errors="coerce").sum()))
        .reset_index()
    )
    delta = old_g.merge(new_g, on=cols, how="outer").fillna({"old_rows": 0, "old_net": 0, "new_rows": 0, "new_net": 0})
    delta["net_delta_new_minus_old"] = delta["new_net"] - delta["old_net"]
    delta["row_delta_new_minus_old"] = delta["new_rows"] - delta["old_rows"]
    delta = delta.sort_values("net_delta_new_minus_old")

    old_exit = (
        old.groupby(["local_exit_reason", "deal_reason"], dropna=False)
        .agg(old_rows=("stage", "count"), old_net=("net_profit", lambda s: pd.to_numeric(s, errors="coerce").sum()))
        .reset_index()
    )
    new_exit = (
        new.groupby(["local_exit_reason", "deal_reason"], dropna=False)
        .agg(new_rows=("stage", "count"), new_net=("net_profit", lambda s: pd.to_numeric(s, errors="coerce").sum()))
        .reset_index()
    )
    exit_delta = old_exit.merge(new_exit, on=["local_exit_reason", "deal_reason"], how="outer").fillna(
        {"old_rows": 0, "old_net": 0, "new_rows": 0, "new_net": 0}
    )
    exit_delta["net_delta_new_minus_old"] = exit_delta["new_net"] - exit_delta["old_net"]
    exit_delta["row_delta_new_minus_old"] = exit_delta["new_rows"] - exit_delta["old_rows"]
    exit_delta = exit_delta.sort_values("net_delta_new_minus_old")

    old_target = old[old["signal_anchor_time"].astype(str).eq("2022.11.08 16:30")].copy()
    old_target.insert(0, "snapshot", "baseline_close_retry")
    new_target = new[new["signal_anchor_time"].astype(str).eq("2022.11.08 16:30")].copy()
    new_target.insert(0, "snapshot", "stage_state_full")
    target = pd.concat([old_target, new_target], ignore_index=True)

    deinit = new[deinit_mask(new)].copy()
    return delta, exit_delta, target, deinit


def round_numeric(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for col in out.select_dtypes(include=["number"]).columns:
        out[col] = out[col].round(6)
    return out


def write_report(summary: pd.DataFrame, delta: pd.DataFrame, exit_delta: pd.DataFrame, target: pd.DataFrame, deinit: pd.DataFrame) -> None:
    lines = [
        "# EA stage-state tracking fix regression review",
        "",
        "## Scope",
        "",
        "- Reviews the compiled EA after replacing single-slot stage management with active ledger-slot traversal.",
        "- Smoke outputs are used to prove the `mt5_0031` unmanaged Stage1 bug is fixed.",
        "- Full output is used as a merge gate; it is not accepted only because deinit rows disappeared.",
        "",
        "## Summary",
        "",
        markdown_table(summary),
        "",
        "## Target mt5_0031 Before/After",
        "",
        markdown_table(
            target[
                [
                    "snapshot",
                    "signal_anchor_time",
                    "signal_src",
                    "stage",
                    "ticket",
                    "position_id",
                    "open_time",
                    "exit_time",
                    "local_exit_reason",
                    "deal_reason",
                    "profit",
                    "swap",
                    "net_profit",
                    "deal_comment",
                ]
            ]
        ),
        "",
        "## Full Regression Largest Negative Deltas",
        "",
        markdown_table(delta.head(25)),
        "",
        "## Full Regression Largest Positive Deltas",
        "",
        markdown_table(delta.sort_values("net_delta_new_minus_old", ascending=False).head(15)),
        "",
        "## Exit Reason Delta",
        "",
        markdown_table(exit_delta),
        "",
        "## New Full Deinit Rows",
        "",
        markdown_table(deinit),
        "",
        "## Decision",
        "",
        "- Smoke gate passes: the original `2022.11.08 16:30` Stage1 no longer survives to deinit and now closes as `stage1_tp / EXPERT`.",
        "- Extended smoke gate passes: deinit rows are zero after extending the window to remove test-end truncation.",
        "- Full deinit gate passes: full-run deinit rows are zero and ledger net equals deal OUT net.",
        "- Merge gate fails for now: full final balance is materially lower than the close-retry baseline, so this EA behavior change requires a dedicated regression decision before it can replace the baseline.",
        "- The largest expected drop is removal of the invalid `mt5_0031` deinit profit; the remaining drop must be reviewed as normal lifecycle changes from managing previously overwritten positions.",
        "",
        "## Output Files",
        "",
        "- `stage_state_fix_summary.csv`",
        "- `stage_state_full_vs_baseline_anchor_stage_delta.csv`",
        "- `stage_state_full_exit_reason_delta.csv`",
        "- `stage_state_target_mt5_0031_before_after.csv`",
        "- `stage_state_full_deinit_rows.csv`",
    ]
    write_text(OUT_DIR / "stage_state_fix_regression_review.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = pd.DataFrame(
        [
            ledger_summary("baseline_close_retry_full", BASELINE_DIR, 3811.35),
            ledger_summary("stage_state_smoke_short", SMOKE_SHORT_DIR, 713.96),
            ledger_summary("stage_state_smoke_extended", SMOKE_EXT_DIR, 673.54),
            ledger_summary("stage_state_full", FULL_DIR, latest_final_balance(FULL_DIR / "tester_agent_20260716.log")),
        ]
    )
    delta, exit_delta, target, deinit = compare_full_to_baseline()

    export_csv(round_numeric(summary), OUT_DIR / "stage_state_fix_summary.csv")
    export_csv(round_numeric(delta), OUT_DIR / "stage_state_full_vs_baseline_anchor_stage_delta.csv")
    export_csv(round_numeric(exit_delta), OUT_DIR / "stage_state_full_exit_reason_delta.csv")
    export_csv(round_numeric(target), OUT_DIR / "stage_state_target_mt5_0031_before_after.csv")
    export_csv(round_numeric(deinit), OUT_DIR / "stage_state_full_deinit_rows.csv")
    write_report(round_numeric(summary), round_numeric(delta), round_numeric(exit_delta), round_numeric(target), round_numeric(deinit))

    print(round_numeric(summary).to_string(index=False))
    print()
    print(round_numeric(delta.head(12)).to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
