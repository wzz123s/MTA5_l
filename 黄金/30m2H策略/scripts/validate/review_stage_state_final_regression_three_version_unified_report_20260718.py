from __future__ import annotations


import csv
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(r"F:\use_code\MTA5_l")
VALIDATION_DIR = ROOT / "黄金" / "30m2H策略" / "data" / "validation"
DYNAMIC_REVIEW_DIR = VALIDATION_DIR / "stage_state_final_regression_dynamic_risk_baseline_review_20260718"
MAPPED_REVIEW_DIR = VALIDATION_DIR / "stage_state_final_regression_mapped_alignment_summary_review_20260718"
MT5_CLOSURE_DIR = VALIDATION_DIR / "stage_state_final_regression_mt5_ledger_closure_review_20260718"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
MAPPED_DIR = VALIDATION_DIR / "mapped_trade_alignment_exec_model_stage_state_metadatafix_20260716"
MT5_BASELINE_DIR = VALIDATION_DIR / "mt5_stage_state_full_2018_20260707_20260716"
OUT_DIR = VALIDATION_DIR / "stage_state_final_regression_three_version_unified_report_20260718"

TESTER_CONFIG = ROOT / "auto_trade" / "30m2H_Strategy_EA.stage_state_full_2018_20260707.ini"


SOURCE_LABELS = {
    "python_only": "Python-only 基础版",
    "python_mt5": "Python-MT5 数据版",
    "mt5_ledger": "MT5-only EA 单独版",
}


PYTHON_DETAIL_FILES = {
    "python_only": DYNAMIC_DIR / "python_only_dynamic_risk_trades.csv",
    "python_mt5": DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv",
}


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def fnum(value: object) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return 0.0


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def parse_tester_config(path: Path) -> Dict[str, str]:
    config: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        text = line.strip()
        if not text or text.startswith(";") or text.startswith("[") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        config[key.strip()] = value.strip().split("||", 1)[0]
    return config


def parse_lots_list(value: str) -> List[float]:
    return [fnum(part) for part in str(value).replace('"', "").split(",") if part.strip()]


def lot_stats_for_python(path: Path) -> Dict[str, object]:
    rows = read_rows(path)
    total_lots = [fnum(row.get("dynamic_total_lot")) for row in rows]
    stage1 = [fnum(row.get("stage1_lot")) for row in rows]
    stage2 = [fnum(row.get("stage2_lot")) for row in rows]
    stage3 = [fnum(row.get("stage3_lot")) for row in rows]
    return {
        "realized_total_lot_min": round(min(total_lots), 6) if total_lots else "",
        "realized_total_lot_avg": round(sum(total_lots) / len(total_lots), 6) if total_lots else "",
        "realized_total_lot_max": round(max(total_lots), 6) if total_lots else "",
        "stage1_lot_range": f"{min(stage1):.2f}-{max(stage1):.2f}" if stage1 else "",
        "stage2_lot_range": f"{min(stage2):.2f}-{max(stage2):.2f}" if stage2 else "",
        "stage3_lot_range": f"{min(stage3):.2f}-{max(stage3):.2f}" if stage3 else "",
        "initial_balance": round(fnum(rows[0].get("balance_before")), 6) if rows else "",
    }


def lot_stats_for_mt5(path: Path) -> Dict[str, object]:
    rows = read_rows(path)
    total_lots: List[float] = []
    stage_lots: Dict[int, List[float]] = {1: [], 2: [], 3: []}
    for row in rows:
        lots = parse_lots_list(row.get("lots_list", ""))
        if lots:
            total_lots.append(sum(lots))
        for idx, lot in enumerate(lots[:3], start=1):
            stage_lots[idx].append(lot)
    return {
        "realized_total_lot_min": round(min(total_lots), 6) if total_lots else "",
        "realized_total_lot_avg": round(sum(total_lots) / len(total_lots), 6) if total_lots else "",
        "realized_total_lot_max": round(max(total_lots), 6) if total_lots else "",
        "stage1_lot_range": f"{min(stage_lots[1]):.2f}-{max(stage_lots[1]):.2f}" if stage_lots[1] else "",
        "stage2_lot_range": f"{min(stage_lots[2]):.2f}-{max(stage_lots[2]):.2f}" if stage_lots[2] else "",
        "stage3_lot_range": f"{min(stage_lots[3]):.2f}-{max(stage_lots[3]):.2f}" if stage_lots[3] else "",
        "initial_balance": round(fnum(rows[0].get("balance_before")), 6) if rows else "",
    }


def load_by_source(path: Path) -> Dict[str, Dict[str, str]]:
    return {row.get("source", ""): row for row in read_rows(path)}


def load_checklist_rows() -> List[Dict[str, str]]:
    return read_rows(MT5_CLOSURE_DIR / "final_regression_checklist_status_after_mt5_ledger_closure.csv")


def make_metrics_rows(config: Dict[str, str]) -> List[Dict[str, object]]:
    dynamic_rows = load_by_source(DYNAMIC_REVIEW_DIR / "dynamic_risk_baseline_recomputed_summary.csv")
    mt5_lot_stats = lot_stats_for_mt5(DYNAMIC_DIR / "mt5_ledger_unique_signals.csv")
    lot_stats = {
        "python_only": lot_stats_for_python(PYTHON_DETAIL_FILES["python_only"]),
        "python_mt5": lot_stats_for_python(PYTHON_DETAIL_FILES["python_mt5"]),
        "mt5_ledger": mt5_lot_stats,
    }

    rows: List[Dict[str, object]] = []
    for source in ["python_only", "python_mt5", "mt5_ledger"]:
        source_row = dynamic_rows[source]
        lots = lot_stats[source]
        is_mt5 = source == "mt5_ledger"
        rows.append(
            {
                "source": source,
                "version_label": SOURCE_LABELS[source],
                "initial_balance": lots["initial_balance"],
                "leverage_setting": config.get("Leverage", "100"),
                "leverage_enforced": "yes_mt5_tester" if is_mt5 else "no_python_accounting_only",
                "risk_pct_setting": config.get("InpRiskPct", "3.0"),
                "use_dynamic_lots": config.get("InpUseDynamicLots", "true"),
                "lot_model": "EA real dynamic lots in MT5 tester"
                if is_mt5
                else "Python dynamic-risk approximation with MT5 value/stage-lot parity",
                "stage_weight_setting": f"{config.get('InpStage1Lots', '0.01')}/{config.get('InpStage2Lots', '0.02')}/{config.get('InpStage3Lots', '0.03')}",
                "realized_total_lot_min": lots["realized_total_lot_min"],
                "realized_total_lot_avg": lots["realized_total_lot_avg"],
                "realized_total_lot_max": lots["realized_total_lot_max"],
                "stage1_lot_range": lots["stage1_lot_range"],
                "stage2_lot_range": lots["stage2_lot_range"],
                "stage3_lot_range": lots["stage3_lot_range"],
                "trade_count": source_row.get("trade_count", ""),
                "final_balance": source_row.get("final_balance", ""),
                "net_profit": source_row.get("total_profit", ""),
                "win_count": source_row.get("win_count", ""),
                "win_rate_pct": source_row.get("win_rate_pct", ""),
                "any_stage_sl_count": source_row.get("any_stage_sl_count", ""),
                "all_stage_sl_count": source_row.get("all_stage_sl_count", ""),
                "avg_stop_pts_spec": source_row.get("avg_stop_pts_spec", ""),
                "data_source": source_row.get("detail_file", ""),
            }
        )
    return rows


def make_direct_gap_rows(metrics_rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    by_source = {row["source"]: row for row in metrics_rows}
    mt5 = by_source["mt5_ledger"]
    rows: List[Dict[str, object]] = []
    for source in ["python_only", "python_mt5"]:
        row = by_source[source]
        rows.append(
            {
                "source": source,
                "version_label": row["version_label"],
                "mt5_reference": "mt5_ledger",
                "trade_count_gap_vs_mt5": int(fnum(row["trade_count"]) - fnum(mt5["trade_count"])),
                "final_balance_gap_vs_mt5": round(fnum(row["final_balance"]) - fnum(mt5["final_balance"]), 6),
                "net_profit_gap_vs_mt5": round(fnum(row["net_profit"]) - fnum(mt5["net_profit"]), 6),
                "win_rate_gap_pct_points_vs_mt5": round(fnum(row["win_rate_pct"]) - fnum(mt5["win_rate_pct"]), 6),
                "any_stage_sl_gap_vs_mt5": int(fnum(row["any_stage_sl_count"]) - fnum(mt5["any_stage_sl_count"])),
                "all_stage_sl_gap_vs_mt5": int(fnum(row["all_stage_sl_count"]) - fnum(mt5["all_stage_sl_count"])),
                "primary_reason": "different_signal_set_and_python_execution_model; final balance is not a direct parity metric",
            }
        )
    return rows


def make_alignment_rows() -> List[Dict[str, object]]:
    rows = read_rows(MAPPED_REVIEW_DIR / "mapped_alignment_recomputed_summary.csv")
    return [
        {
            "source": row.get("source", ""),
            "version_label": SOURCE_LABELS.get(row.get("source", ""), row.get("source", "")),
            "python_trades": row.get("python_trades", ""),
            "mt5_trades": row.get("mt5_trades", ""),
            "matched_unique": row.get("matched_unique", ""),
            "reliable_tier_matched": row.get("reliable_tier_matched", ""),
            "relaxed_tier_matched": row.get("relaxed_tier_matched", ""),
            "python_unmatched": row.get("python_unmatched", ""),
            "mt5_unmatched": row.get("mt5_unmatched", ""),
            "matched_python_profit": row.get("matched_python_profit", ""),
            "matched_mt5_profit": row.get("matched_mt5_profit", ""),
            "matched_profit_diff": row.get("matched_profit_diff", ""),
            "any_sl_same_count": row.get("any_sl_same_count", ""),
            "all_sl_same_count": row.get("all_sl_same_count", ""),
        }
        for row in rows
    ]


def make_unmatched_rows() -> List[Dict[str, object]]:
    rows = read_rows(MAPPED_DIR / "unmatched_trigger_mode_summary.csv")
    out: List[Dict[str, object]] = []
    for row in rows:
        out.append(
            {
                "source": row.get("source", ""),
                "version_label": SOURCE_LABELS.get(row.get("source", ""), row.get("source", "")),
                "side": row.get("side", ""),
                "trigger_family": row.get("trigger_family", ""),
                "mode_family": row.get("mode_family", ""),
                "rows": row.get("rows", ""),
            }
        )
    return out


def make_scope_rows(config: Dict[str, str]) -> List[Dict[str, object]]:
    return [
        {
            "source": "python_only",
            "version_label": SOURCE_LABELS["python_only"],
            "what_it_represents": "Python original data/signal pipeline with dynamic-risk execution normalization.",
            "execution_model": "Python accounting model; no real MT5 order lifecycle, margin, slippage, position management, or broker-side close semantics.",
            "data_scope": "Python-only source data and Python signal calculation outputs.",
            "comparison_boundary": "Useful for signal/data pipeline diagnostics, not a direct replacement for MT5 tester equity.",
        },
        {
            "source": "python_mt5",
            "version_label": SOURCE_LABELS["python_mt5"],
            "what_it_represents": "Python pipeline using MT5-aligned data/metadata inputs where available.",
            "execution_model": "Still Python accounting model with MT5 value/stage-lot parity; not the EA order lifecycle.",
            "data_scope": "Python signal/execution pipeline after MT5 data integration.",
            "comparison_boundary": "Closer to MT5 data than Python-only, but final balance remains affected by Python execution assumptions.",
        },
        {
            "source": "mt5_ledger",
            "version_label": SOURCE_LABELS["mt5_ledger"],
            "what_it_represents": "Frozen MT5 EA full tester ledger.",
            "execution_model": f"Real MT5 tester with Deposit={config.get('Deposit', '500')}, Leverage={config.get('Leverage', '100')}, dynamic lots={config.get('InpUseDynamicLots', 'true')}, risk={config.get('InpRiskPct', '3.0')}%.",
            "data_scope": "EA signals, deals, positions, stage ledger, broker/tick execution from MT5 tester.",
            "comparison_boundary": "Primary frozen run baseline for run-package readiness.",
        },
    ]


def write_report_md(
    decision: Dict[str, object],
    metrics_rows: List[Dict[str, object]],
    gap_rows: List[Dict[str, object]],
    alignment_rows: List[Dict[str, object]],
    scope_rows: List[Dict[str, object]],
) -> None:
    lines: List[str] = []
    lines.append("# Three-version Unified Report Refresh")
    lines.append("")
    lines.append(f"- Decision date: {decision['decision_date']}")
    lines.append(f"- Check id: `{decision['check_id']}`")
    lines.append(f"- Status: `{decision['status']}`")
    lines.append(f"- Pass: `{decision['pass']}`")
    lines.append(f"- Reason: `{decision['reason']}`")
    lines.append("")
    lines.append("## Unified Metrics")
    lines.append("")
    lines.append("| version | initial | leverage | lot model | trades | final | net profit | wins | win rate | any SL | all SL |")
    lines.append("|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|")
    for row in metrics_rows:
        lines.append(
            "| {version_label} | {initial_balance} | {leverage_setting} | {lot_model} | {trade_count} | {final_balance} | {net_profit} | {win_count} | {win_rate_pct} | {any_stage_sl_count} | {all_stage_sl_count} |".format(
                **row
            )
        )
    lines.append("")
    lines.append("## Direct Gap Vs MT5")
    lines.append("")
    lines.append("| version | trade gap | final gap | net profit gap | win-rate gap pp | any SL gap | all SL gap |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for row in gap_rows:
        lines.append(
            "| {version_label} | {trade_count_gap_vs_mt5} | {final_balance_gap_vs_mt5} | {net_profit_gap_vs_mt5} | {win_rate_gap_pct_points_vs_mt5} | {any_stage_sl_gap_vs_mt5} | {all_stage_sl_gap_vs_mt5} |".format(
                **row
            )
        )
    lines.append("")
    lines.append("## Alignment Snapshot")
    lines.append("")
    lines.append("| source | matched | reliable | relaxed | python unmatched | mt5 unmatched | matched profit diff |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for row in alignment_rows:
        lines.append(
            "| {version_label} | {matched_unique} | {reliable_tier_matched} | {relaxed_tier_matched} | {python_unmatched} | {mt5_unmatched} | {matched_profit_diff} |".format(
                **row
            )
        )
    lines.append("")
    lines.append("## Scope Boundary")
    lines.append("")
    for row in scope_rows:
        lines.append(f"- `{row['version_label']}`: {row['comparison_boundary']}")
    lines.append("")
    lines.append("## Conclusion")
    lines.append("")
    lines.append("- The three-version report is refreshed from frozen final-regression inputs.")
    lines.append("- The large final-balance spread is explained by different signal sets plus different execution models, not by a ledger closure failure.")
    lines.append("- MT5-only remains the frozen run baseline; Python-only and Python-MT5 remain diagnostic/parity references.")
    lines.append("")
    (OUT_DIR / "three_version_unified_report.md").write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    config = parse_tester_config(TESTER_CONFIG)
    metrics_rows = make_metrics_rows(config)
    gap_rows = make_direct_gap_rows(metrics_rows)
    alignment_rows = make_alignment_rows()
    unmatched_rows = make_unmatched_rows()
    scope_rows = make_scope_rows(config)

    prior_checklist = load_checklist_rows()
    prior_pass = all(row.get("status") == "pass" for row in prior_checklist[:3])
    generated_files_expected = [
        "three_version_unified_metrics.csv",
        "three_version_direct_gap_vs_mt5.csv",
        "three_version_alignment_snapshot.csv",
        "three_version_unmatched_trigger_mode_summary.csv",
        "three_version_execution_scope.csv",
        "three_version_unified_report.md",
    ]
    decision = {
        "decision_date": date.today().isoformat(),
        "check_id": "three_version_unified_report_refresh",
        "status": "pass" if prior_pass else "fail",
        "pass": prior_pass,
        "prior_regression_checks_passed": prior_pass,
        "source_count": len(metrics_rows),
        "report_file_count": len(generated_files_expected),
        "reason": "three_version_report_refreshed_from_frozen_inputs"
        if prior_pass
        else "prior_regression_checks_not_all_passed",
        "next_check": "ea_ex5_set_run_package_check" if prior_pass else "fix_prior_regression_checks",
        "no_ea_or_python_logic_changes_in_this_step": True,
    }

    write_csv(
        OUT_DIR / "three_version_unified_metrics.csv",
        metrics_rows,
        [
            "source",
            "version_label",
            "initial_balance",
            "leverage_setting",
            "leverage_enforced",
            "risk_pct_setting",
            "use_dynamic_lots",
            "lot_model",
            "stage_weight_setting",
            "realized_total_lot_min",
            "realized_total_lot_avg",
            "realized_total_lot_max",
            "stage1_lot_range",
            "stage2_lot_range",
            "stage3_lot_range",
            "trade_count",
            "final_balance",
            "net_profit",
            "win_count",
            "win_rate_pct",
            "any_stage_sl_count",
            "all_stage_sl_count",
            "avg_stop_pts_spec",
            "data_source",
        ],
    )
    write_csv(
        OUT_DIR / "three_version_direct_gap_vs_mt5.csv",
        gap_rows,
        [
            "source",
            "version_label",
            "mt5_reference",
            "trade_count_gap_vs_mt5",
            "final_balance_gap_vs_mt5",
            "net_profit_gap_vs_mt5",
            "win_rate_gap_pct_points_vs_mt5",
            "any_stage_sl_gap_vs_mt5",
            "all_stage_sl_gap_vs_mt5",
            "primary_reason",
        ],
    )
    write_csv(
        OUT_DIR / "three_version_alignment_snapshot.csv",
        alignment_rows,
        [
            "source",
            "version_label",
            "python_trades",
            "mt5_trades",
            "matched_unique",
            "reliable_tier_matched",
            "relaxed_tier_matched",
            "python_unmatched",
            "mt5_unmatched",
            "matched_python_profit",
            "matched_mt5_profit",
            "matched_profit_diff",
            "any_sl_same_count",
            "all_sl_same_count",
        ],
    )
    write_csv(
        OUT_DIR / "three_version_unmatched_trigger_mode_summary.csv",
        unmatched_rows,
        ["source", "version_label", "side", "trigger_family", "mode_family", "rows"],
    )
    write_csv(
        OUT_DIR / "three_version_execution_scope.csv",
        scope_rows,
        [
            "source",
            "version_label",
            "what_it_represents",
            "execution_model",
            "data_scope",
            "comparison_boundary",
        ],
    )
    write_csv(
        OUT_DIR / "three_version_unified_report_decision.csv",
        [decision],
        [
            "decision_date",
            "check_id",
            "status",
            "pass",
            "prior_regression_checks_passed",
            "source_count",
            "report_file_count",
            "reason",
            "next_check",
            "no_ea_or_python_logic_changes_in_this_step",
        ],
    )

    checklist_rows: List[Dict[str, object]] = []
    for row in prior_checklist:
        if row.get("check_id") == "three_version_unified_report_refresh":
            row["status"] = decision["status"]
            row["evidence"] = str((OUT_DIR / "three_version_unified_report_decision.csv").relative_to(ROOT))
        elif "evidence" not in row:
            row["evidence"] = ""
        checklist_rows.append(row)
    write_csv(
        OUT_DIR / "final_regression_checklist_status_after_three_version_report.csv",
        checklist_rows,
        ["order", "check_id", "description", "status", "evidence"],
    )

    readme = "\n".join(
        [
            "# stage_state_final_regression_three_version_unified_report_20260718",
            "",
            "Final regression check 4: refresh three-version unified report from frozen inputs.",
            "",
            "- `three_version_unified_report_decision.csv`: check decision.",
            "- `three_version_unified_metrics.csv`: unified metrics for Python-only, Python-MT5, and MT5-only.",
            "- `three_version_direct_gap_vs_mt5.csv`: direct gaps versus MT5-only frozen baseline.",
            "- `three_version_alignment_snapshot.csv`: mapped alignment snapshot.",
            "- `three_version_unmatched_trigger_mode_summary.csv`: unmatched trigger/mode buckets.",
            "- `three_version_execution_scope.csv`: version scope and execution-model boundaries.",
            "- `final_regression_checklist_status_after_three_version_report.csv`: checklist progress after this check.",
            "- `three_version_unified_report.md`: human-readable unified report.",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8-sig")
    write_report_md(decision, metrics_rows, gap_rows, alignment_rows, scope_rows)

    print(f"wrote {OUT_DIR}")
    print(f"status={decision['status']}")
    print(f"prior_regression_checks_passed={prior_pass}")
    print(f"source_count={len(metrics_rows)}")


if __name__ == "__main__":
    main()
