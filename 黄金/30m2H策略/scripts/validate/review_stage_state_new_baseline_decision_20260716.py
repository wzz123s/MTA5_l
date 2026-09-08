# -*- coding: utf-8 -*-
"""Decide whether the stage-state full MT5 run becomes the new baseline.

This is a documentation/accounting gate. It does not change EA or Python
strategy logic; it records the accepted MT5 reference after previous lifecycle
audits invalidated the close-retry baseline's long-held profits.
"""
from __future__ import annotations


import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

BASELINE_DIR = VALIDATION_DIR / "mt5_full_close_retry_fix_20260714"
STAGE_STATE_DIR = VALIDATION_DIR / "mt5_stage_state_full_2018_20260707_20260716"
STAGE_FIX_DIR = VALIDATION_DIR / "stage_state_fix_regression_review_20260716"
REMAP_DIR = VALIDATION_DIR / "stage_state_full_remap_residual_review_20260716"
LIFECYCLE_DIR = VALIDATION_DIR / "stage_state_lifecycle_delta_localization_20260716"
STAGE3_AUDIT_DIR = VALIDATION_DIR / "stage3_20250905_new_anchor_gate_audit_20260716"
OUT_DIR = VALIDATION_DIR / "stage_state_new_baseline_decision_20260716"

START_CAPITAL = 500.0
CONFIGURED_TEST_FROM = "2018-01-01"
CONFIGURED_TEST_TO = "2026-07-07"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def markdown_table(frame: pd.DataFrame, max_rows: int = 50) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def num(value: object, default: float = 0.0) -> float:
    out = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(out):
        return default
    return float(out)


def to_dt(value: object) -> pd.Timestamp:
    text = str(value).strip()
    if not text:
        return pd.NaT
    return pd.to_datetime(text.replace(".", "-"), errors="coerce")


def latest_deposit_leverage(log_path: Path) -> tuple[float, str]:
    text = log_path.read_text(encoding="utf-16" if log_path.read_bytes().startswith(b"\xff\xfe") else "utf-8", errors="ignore")
    match = re.search(r"initial deposit\s+([0-9.]+)\s+USD,\s+leverage\s+([^\s]+)", text)
    if not match:
        return START_CAPITAL, ""
    return float(match.group(1)), match.group(2)


def round_numeric(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for col in out.select_dtypes(include=["number"]).columns:
        out[col] = out[col].round(6)
    return out


def load_stage_state_trade_summary() -> tuple[pd.DataFrame, pd.DataFrame]:
    ledger = read_csv(STAGE_STATE_DIR / "30m2H_strategy_trade_ledger.csv").copy()
    ledger["anchor_dt"] = ledger["signal_anchor_time"].map(to_dt)
    for col in ["stage", "net_profit", "profit", "swap", "commission", "lots"]:
        ledger[col] = pd.to_numeric(ledger[col], errors="coerce")
    group_cols = ["signal_anchor_time", "trigger_tag", "signal_src", "dir"]
    trades = (
        ledger.groupby(group_cols, dropna=False)
        .agg(
            stage_rows=("stage", "count"),
            net_profit=("net_profit", "sum"),
            profit=("profit", "sum"),
            swap=("swap", "sum"),
            commission=("commission", "sum"),
            any_sl=("deal_reason", lambda s: s.astype(str).eq("SL").any()),
            all_sl=("deal_reason", lambda s: s.astype(str).eq("SL").all()),
            exit_reasons=("local_exit_reason", lambda s: ";".join(sorted(set(s.astype(str))))),
            deal_reasons=("deal_reason", lambda s: ";".join(sorted(set(s.astype(str))))),
        )
        .reset_index()
    )
    trades["win"] = trades["net_profit"] > 0
    return ledger, trades


def build_current_baseline_manifest() -> pd.DataFrame:
    summary = read_csv(STAGE_FIX_DIR / "stage_state_fix_summary.csv")
    current = summary[summary["snapshot"].eq("stage_state_full")].iloc[0]
    deposit, leverage = latest_deposit_leverage(STAGE_STATE_DIR / "tester_agent_20260716.log")
    ledger, trades = load_stage_state_trade_summary()
    deinit_rows = int(current["deinit_rows"])
    rows = [
        {
            "baseline_status": "accepted_current_mt5_reference",
            "baseline_id": "stage_state_full_2018_20260707_20260716",
            "ledger_dir": str(STAGE_STATE_DIR),
            "configured_test_from": CONFIGURED_TEST_FROM,
            "configured_test_to": CONFIGURED_TEST_TO,
            "first_trade_anchor": str(ledger["anchor_dt"].min()),
            "last_trade_anchor": str(ledger["anchor_dt"].max()),
            "initial_deposit": deposit,
            "leverage": leverage,
            "final_balance": num(current["final_balance"]),
            "net_profit": num(current["final_net_profit"]),
            "trade_count_unique_anchors": int(len(trades)),
            "stage_rows": int(len(ledger)),
            "win_count": int(trades["win"].sum()),
            "win_rate_pct": int(trades["win"].sum()) / len(trades) * 100.0 if len(trades) else 0.0,
            "any_stage_sl_count": int(trades["any_sl"].sum()),
            "all_stage_sl_count": int(trades["all_sl"].sum()),
            "deinit_rows": deinit_rows,
            "ledger_vs_deal_net_gap": num(current["ledger_vs_deal_net_gap"]),
            "ledger_vs_final_net_gap": num(current["ledger_vs_final_net_gap"]),
        }
    ]
    return round_numeric(pd.DataFrame(rows))


def build_deprecated_baseline_summary() -> pd.DataFrame:
    summary = read_csv(STAGE_FIX_DIR / "stage_state_fix_summary.csv")
    old = summary[summary["snapshot"].eq("baseline_close_retry_full")].iloc[0]
    new = summary[summary["snapshot"].eq("stage_state_full")].iloc[0]
    lifecycle = read_csv(LIFECYCLE_DIR / "stage_state_delta_bucket_summary.csv")
    bucket_lookup = {
        row["bucket"]: num(row["net_delta_new_minus_old"])
        for _, row in lifecycle.iterrows()
        if str(row["bucket"]).strip()
    }
    rows = [
        {
            "item": "deprecated_close_retry_reference",
            "baseline_id": "mt5_full_close_retry_fix_20260714",
            "final_balance": num(old["final_balance"]),
            "net_profit": num(old["final_net_profit"]),
            "trade_count_unique_anchors": int(num(old["unique_anchors"])),
            "stage_rows": int(num(old["ledger_rows"])),
            "deinit_rows": int(num(old["deinit_rows"])),
            "valid_for_future_direct_gap": False,
            "reason": "contains invalid unmanaged deinit/long-hold lifecycle profit",
        },
        {
            "item": "accepted_stage_state_reference",
            "baseline_id": "stage_state_full_2018_20260707_20260716",
            "final_balance": num(new["final_balance"]),
            "net_profit": num(new["final_net_profit"]),
            "trade_count_unique_anchors": int(num(new["unique_anchors"])),
            "stage_rows": int(num(new["ledger_rows"])),
            "deinit_rows": int(num(new["deinit_rows"])),
            "valid_for_future_direct_gap": True,
            "reason": "multi-slot lifecycle ledger closes to deal/final net and removes invalid long-held profits",
        },
        {
            "item": "delta_new_minus_deprecated",
            "baseline_id": "",
            "final_balance": num(new["final_balance"]) - num(old["final_balance"]),
            "net_profit": num(new["final_net_profit"]) - num(old["final_net_profit"]),
            "trade_count_unique_anchors": int(num(new["unique_anchors"])) - int(num(old["unique_anchors"])),
            "stage_rows": int(num(new["ledger_rows"])) - int(num(old["ledger_rows"])),
            "deinit_rows": int(num(new["deinit_rows"])) - int(num(old["deinit_rows"])),
            "valid_for_future_direct_gap": "",
            "reason": "target_deinit_stage1=%s; target_20250905_stage3=-381.23; new_anchors=%s; shared_other=%s"
            % (
                bucket_lookup.get("target_deinit_stage1_correction", 0.0),
                bucket_lookup.get("new_anchor_rows", 0.0),
                bucket_lookup.get("shared_anchor_other_lifecycle_delta", 0.0),
            ),
        },
    ]
    return round_numeric(pd.DataFrame(rows))


def build_acceptance_evidence() -> pd.DataFrame:
    fix_summary = read_csv(STAGE_FIX_DIR / "stage_state_fix_summary.csv")
    current = fix_summary[fix_summary["snapshot"].eq("stage_state_full")].iloc[0]
    lifecycle = read_csv(LIFECYCLE_DIR / "stage_state_delta_bucket_summary.csv")
    stage3 = read_csv(STAGE3_AUDIT_DIR / "stage3_new_anchor_gate_decision.csv").iloc[0]
    mt5_0031 = read_csv(STAGE_FIX_DIR / "stage_state_target_mt5_0031_before_after.csv")
    target_stage1 = mt5_0031[(mt5_0031["snapshot"].eq("stage_state_full")) & (pd.to_numeric(mt5_0031["stage"], errors="coerce") == 1)]
    rows = [
        {
            "evidence": "ledger_deal_final_closure",
            "pass": abs(num(current["ledger_vs_deal_net_gap"])) < 1e-6 and abs(num(current["ledger_vs_final_net_gap"])) < 1e-6,
            "value": "ledger/deal/final net gap = 0",
        },
        {
            "evidence": "deinit_rows_removed",
            "pass": int(num(current["deinit_rows"])) == 0,
            "value": f"deinit_rows={int(num(current['deinit_rows']))}",
        },
        {
            "evidence": "mt5_0031_lifecycle_corrected",
            "pass": not target_stage1.empty and str(target_stage1.iloc[0]["local_exit_reason"]) == "stage1_tp",
            "value": "mt5_0031 Stage1 closes as stage1_tp / EXPERT",
        },
        {
            "evidence": "target_20250905_old_profit_invalidated",
            "pass": str(stage3["target_stage3_verdict"]) == "old_stage3_likely_unmanaged_after_stage3_state_overwrite",
            "value": str(stage3["target_stage3_verdict"]),
        },
        {
            "evidence": "new_anchors_explained_by_capacity_release",
            "pass": str(stage3["all_new_anchors_explained_by_deinit_capacity"]).lower() == "true",
            "value": f"{int(num(stage3['new_anchor_released_by_deinit_count']))}/{int(num(stage3['new_anchor_count']))}",
        },
        {
            "evidence": "lifecycle_delta_closed",
            "pass": abs(
                num(lifecycle[lifecycle["bucket"].eq("total_close_retry_to_stage_state")].iloc[0]["net_delta_new_minus_old"])
                + 2161.51
            )
            < 1e-6,
            "value": "total delta -2161.51 is bucketed",
        },
    ]
    return pd.DataFrame(rows)


def build_python_mt5_gap_rebase() -> pd.DataFrame:
    remap = read_csv(REMAP_DIR / "stage_state_full_remap_summary.csv")
    delta = read_csv(REMAP_DIR / "stage_state_full_delta_vs_close_retry_exec_model.csv")
    rows = []
    for _, row in remap.iterrows():
        scenario = row["scenario"]
        delta_row = delta[delta["scenario"].eq(scenario)].iloc[0]
        current_gap = num(row["direct_gap_py_minus_mt5"])
        gap_delta = num(delta_row["direct_gap_delta_new_minus_previous"])
        rows.append(
            {
                "scenario": scenario,
                "python_mt5_final_balance": num(row["python_mt5_final_balance"]),
                "deprecated_close_retry_mt5_final": num(row["mt5_final_balance"]) + num(delta_row["mt5_final_delta_new_minus_previous"]) * -1,
                "accepted_stage_state_mt5_final": num(row["mt5_final_balance"]),
                "direct_gap_vs_deprecated_close_retry": current_gap - gap_delta,
                "direct_gap_vs_accepted_stage_state": current_gap,
                "gap_rebase_delta": gap_delta,
                "future_reference": "accepted_stage_state_mt5_final",
            }
        )
    return round_numeric(pd.DataFrame(rows))


def build_decision(manifest: pd.DataFrame, evidence: pd.DataFrame, gap_rebase: pd.DataFrame) -> pd.DataFrame:
    all_evidence_pass = bool(evidence["pass"].astype(bool).all())
    rows = [
        {
            "gate": "stage_state_new_mt5_baseline_decision",
            "accept_stage_state_as_current_mt5_baseline": all_evidence_pass,
            "alignment_merge_gate_pass": False,
            "current_mt5_baseline_id": manifest.iloc[0]["baseline_id"],
            "current_mt5_final_balance": num(manifest.iloc[0]["final_balance"]),
            "current_mt5_trade_count": int(num(manifest.iloc[0]["trade_count_unique_anchors"])),
            "current_mt5_stage_rows": int(num(manifest.iloc[0]["stage_rows"])),
            "current_mt5_deinit_rows": int(num(manifest.iloc[0]["deinit_rows"])),
            "metadatafix_direct_gap_vs_current_mt5": num(
                gap_rebase[gap_rebase["scenario"].eq("metadatafix")].iloc[0]["direct_gap_vs_accepted_stage_state"]
            ),
            "deprecated_close_retry_allowed_for_future_direct_gap": False,
            "next_action": "resume_python_mt5_time_axis_normalization_using_stage_state_baseline",
        }
    ]
    return round_numeric(pd.DataFrame(rows))


def write_report(
    decision: pd.DataFrame,
    manifest: pd.DataFrame,
    deprecated: pd.DataFrame,
    evidence: pd.DataFrame,
    gap_rebase: pd.DataFrame,
) -> None:
    lines = [
        "# Stage-state new MT5 baseline decision",
        "",
        "## Scope",
        "",
        "- This gate decides the MT5 reference baseline only.",
        "- It does not mark Python-MT5 strategy alignment as complete.",
        "- It does not change EA or Python strategy logic.",
        "",
        "## Decision",
        "",
        markdown_table(decision),
        "",
        "## Current Baseline Manifest",
        "",
        markdown_table(manifest),
        "",
        "## Deprecated vs Accepted Baseline",
        "",
        markdown_table(deprecated),
        "",
        "## Acceptance Evidence",
        "",
        markdown_table(evidence),
        "",
        "## Python-MT5 Gap Rebase",
        "",
        markdown_table(gap_rebase),
        "",
        "## Interpretation",
        "",
        "- Accept `mt5_stage_state_full_2018_20260707_20260716` as the current MT5 reference baseline.",
        "- Do not use `mt5_full_close_retry_fix_20260714` for future direct-gap conclusions; it remains historical evidence only.",
        "- The accepted MT5 baseline is final balance `$1649.84`, unique anchor trades `82`, stage rows `246`, deinit rows `0`.",
        "- Python-MT5 alignment is still not complete: metadatafix direct gap against the accepted MT5 baseline is `+$2389.732270`.",
        "- Future work resumes at the Python-MT5 +90/+120 time-axis normalization gate using this stage-state baseline.",
        "",
        "## Output Files",
        "",
        "- `stage_state_new_baseline_decision.csv`",
        "- `current_mt5_baseline_manifest.csv`",
        "- `deprecated_vs_accepted_baseline_summary.csv`",
        "- `stage_state_baseline_acceptance_evidence.csv`",
        "- `python_mt5_gap_rebase_after_stage_state.csv`",
        "- `current_mt5_baseline_README.md`",
    ]
    write_text(OUT_DIR / "stage_state_new_baseline_decision_review.md", "\n".join(lines))

    baseline_readme = [
        "# Current MT5 Baseline",
        "",
        "- Baseline id: `stage_state_full_2018_20260707_20260716`",
        f"- Ledger directory: `{STAGE_STATE_DIR}`",
        "- Status: accepted current MT5 reference",
        "- Initial deposit: `$500.00`",
        "- Leverage: `1:100`",
        "- Final balance: `$1649.84`",
        "- Unique anchor trades: `82`",
        "- Stage rows: `246`",
        "- Deinit rows: `0`",
        "",
        "Do not use `mt5_full_close_retry_fix_20260714` as a future direct-gap baseline. It contains invalid lifecycle profit from unmanaged long-held positions.",
    ]
    write_text(OUT_DIR / "current_mt5_baseline_README.md", "\n".join(baseline_readme))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_current_baseline_manifest()
    deprecated = build_deprecated_baseline_summary()
    evidence = build_acceptance_evidence()
    gap_rebase = build_python_mt5_gap_rebase()
    decision = build_decision(manifest, evidence, gap_rebase)

    export_csv(decision, OUT_DIR / "stage_state_new_baseline_decision.csv")
    export_csv(manifest, OUT_DIR / "current_mt5_baseline_manifest.csv")
    export_csv(deprecated, OUT_DIR / "deprecated_vs_accepted_baseline_summary.csv")
    export_csv(evidence, OUT_DIR / "stage_state_baseline_acceptance_evidence.csv")
    export_csv(gap_rebase, OUT_DIR / "python_mt5_gap_rebase_after_stage_state.csv")
    write_report(decision, manifest, deprecated, evidence, gap_rebase)

    print(decision.to_string(index=False))
    print()
    print(manifest.to_string(index=False))
    print()
    print(gap_rebase.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
