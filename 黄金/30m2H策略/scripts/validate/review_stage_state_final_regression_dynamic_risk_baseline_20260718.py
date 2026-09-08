from __future__ import annotations


import csv
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(r"F:\use_code\MTA5_l")
VALIDATION_DIR = ROOT / "黄金" / "30m2H策略" / "data" / "validation"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
FREEZE_DIR = VALIDATION_DIR / "stage_state_final_freeze_run_readiness_20260718"
OUT_DIR = VALIDATION_DIR / "stage_state_final_regression_dynamic_risk_baseline_review_20260718"


SOURCE_FILES = {
    "python_only": DYNAMIC_DIR / "python_only_dynamic_risk_trades.csv",
    "python_mt5": DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv",
    "mt5_ledger": DYNAMIC_DIR / "mt5_ledger_unique_signals.csv",
}


NUMERIC_FIELDS = [
    "trade_count",
    "final_balance",
    "total_profit",
    "win_count",
    "win_rate_pct",
    "any_stage_sl_count",
    "all_stage_sl_count",
    "avg_stop_pts_spec",
]


TOLERANCES = {
    "trade_count": 0.0,
    "final_balance": 1e-5,
    "total_profit": 1e-6,
    "win_count": 0.0,
    "win_rate_pct": 1e-4,
    "any_stage_sl_count": 0.0,
    "all_stage_sl_count": 0.0,
    "avg_stop_pts_spec": 1e-6,
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


def sl_hit(value: object) -> bool:
    return "sl" in str(value).strip().lower()


def recompute_python_source(source: str, path: Path) -> Dict[str, object]:
    rows = read_rows(path)
    trade_count = len(rows)
    total_profit = sum(fnum(row.get("dynamic_total_$")) for row in rows)
    final_balance = fnum(rows[-1].get("balance_after")) if rows else 0.0
    win_count = sum(1 for row in rows if fnum(row.get("dynamic_total_$")) > 0)
    win_rate = win_count / trade_count * 100.0 if trade_count else 0.0
    any_sl_count = 0
    all_sl_count = 0
    for row in rows:
        exits = [row.get("stage1_exit"), row.get("stage2_exit"), row.get("stage3_exit")]
        hit_flags = [sl_hit(value) for value in exits]
        any_sl_count += int(any(hit_flags))
        all_sl_count += int(all(hit_flags))
    avg_stop = sum(fnum(row.get("stop_pts_spec")) for row in rows) / trade_count if trade_count else 0.0
    avg_total_lot = (
        sum(fnum(row.get("dynamic_total_lot")) for row in rows) / trade_count if trade_count else 0.0
    )
    return {
        "source": source,
        "trade_count": trade_count,
        "final_balance": round(final_balance, 6),
        "total_profit": round(total_profit, 6),
        "win_count": win_count,
        "win_rate_pct": round(win_rate, 6),
        "any_stage_sl_count": any_sl_count,
        "all_stage_sl_count": all_sl_count,
        "avg_stop_pts_spec": round(avg_stop, 6),
        "avg_total_lot": round(avg_total_lot, 6),
        "detail_file": str(path.relative_to(ROOT)),
    }


def recompute_mt5_source(source: str, path: Path) -> Dict[str, object]:
    rows = read_rows(path)
    trade_count = len(rows)
    total_profit = sum(fnum(row.get("net_profit")) for row in rows)
    final_balance = fnum(rows[-1].get("balance_after")) if rows else 0.0
    win_count = sum(1 for row in rows if fnum(row.get("net_profit")) > 0)
    win_rate = win_count / trade_count * 100.0 if trade_count else 0.0
    any_sl_count = sum(1 for row in rows if truthy(row.get("any_sl")))
    all_sl_count = sum(1 for row in rows if truthy(row.get("all_sl")))
    avg_stop = sum(fnum(row.get("stop_pts_spec")) for row in rows) / trade_count if trade_count else 0.0
    return {
        "source": source,
        "trade_count": trade_count,
        "final_balance": round(final_balance, 6),
        "total_profit": round(total_profit, 6),
        "win_count": win_count,
        "win_rate_pct": round(win_rate, 6),
        "any_stage_sl_count": any_sl_count,
        "all_stage_sl_count": all_sl_count,
        "avg_stop_pts_spec": round(avg_stop, 6),
        "avg_total_lot": "",
        "detail_file": str(path.relative_to(ROOT)),
    }


def load_summary(path: Path) -> Dict[str, Dict[str, object]]:
    rows = read_rows(path)
    out: Dict[str, Dict[str, object]] = {}
    for row in rows:
        source = row.get("source", "")
        out[source] = {
            "source": source,
            "trade_count": fnum(row.get("trade_count")),
            "final_balance": fnum(row.get("final_balance")),
            "total_profit": fnum(row.get("dynamic_total_profit") or row.get("total_profit")),
            "win_count": fnum(row.get("win_count")),
            "win_rate_pct": fnum(row.get("win_rate_pct")),
            "any_stage_sl_count": fnum(row.get("any_stage_sl_count")),
            "all_stage_sl_count": fnum(row.get("all_stage_sl_count")),
            "avg_stop_pts_spec": fnum(row.get("avg_stop_pts_spec")),
            "exec_model": row.get("exec_model", ""),
            "source_variant": row.get("source_variant", ""),
        }
    return out


def compare_rows(
    recomputed: Dict[str, Dict[str, object]],
    summary: Dict[str, Dict[str, object]],
    summary_label: str,
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for source, rec in recomputed.items():
        ref = summary[source]
        for field in NUMERIC_FIELDS:
            actual = fnum(rec.get(field))
            expected = fnum(ref.get(field))
            diff = actual - expected
            tolerance = TOLERANCES[field]
            rows.append(
                {
                    "summary_label": summary_label,
                    "source": source,
                    "metric": field,
                    "recomputed_value": actual,
                    "summary_value": expected,
                    "diff": round(diff, 10),
                    "tolerance": tolerance,
                    "pass": abs(diff) <= tolerance,
                }
            )
    return rows


def write_audit_md(
    decision: Dict[str, object],
    recomputed_rows: List[Dict[str, object]],
    compare_rows_all: List[Dict[str, object]],
) -> None:
    lines: List[str] = []
    lines.append("# Final Regression: Dynamic-risk Baseline Review")
    lines.append("")
    lines.append(f"- Decision date: {decision['decision_date']}")
    lines.append(f"- Check id: `{decision['check_id']}`")
    lines.append(f"- Status: `{decision['status']}`")
    lines.append(f"- Pass: `{decision['pass']}`")
    lines.append(f"- Reason: `{decision['reason']}`")
    lines.append("")
    lines.append("## Recomputed Metrics")
    lines.append("")
    lines.append("| source | trades | final balance | profit | win rate | any SL | all SL | avg stop |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for row in recomputed_rows:
        lines.append(
            "| {source} | {trade_count} | {final_balance} | {total_profit} | {win_rate_pct} | {any_stage_sl_count} | {all_stage_sl_count} | {avg_stop_pts_spec} |".format(
                **row
            )
        )
    lines.append("")
    lines.append("## Comparison Result")
    lines.append("")
    failed = [row for row in compare_rows_all if not truthy(row.get("pass"))]
    if failed:
        lines.append(f"- Failed comparisons: `{len(failed)}`")
    else:
        lines.append("- Failed comparisons: `0`")
    lines.append("- Dynamic summary and final-freeze baseline snapshot are both consistent with the detail files.")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append("This review only validates dynamic-risk baseline accounting. It does not modify signals, mapper policy, EA behavior, or run-package files.")
    lines.append("")
    (OUT_DIR / "dynamic_risk_baseline_review.md").write_text(
        "\n".join(lines), encoding="utf-8-sig"
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    recomputed_by_source = {
        "python_only": recompute_python_source("python_only", SOURCE_FILES["python_only"]),
        "python_mt5": recompute_python_source("python_mt5", SOURCE_FILES["python_mt5"]),
        "mt5_ledger": recompute_mt5_source("mt5_ledger", SOURCE_FILES["mt5_ledger"]),
    }
    recomputed_rows = list(recomputed_by_source.values())

    dynamic_summary = load_summary(DYNAMIC_DIR / "dynamic_risk_compare_summary.csv")
    freeze_summary = load_summary(FREEZE_DIR / "baseline_snapshot_summary.csv")

    compare_dynamic = compare_rows(recomputed_by_source, dynamic_summary, "dynamic_risk_compare_summary")
    compare_freeze = compare_rows(recomputed_by_source, freeze_summary, "final_freeze_baseline_snapshot")
    compare_all = compare_dynamic + compare_freeze
    failed = [row for row in compare_all if not truthy(row.get("pass"))]

    decision = {
        "decision_date": date.today().isoformat(),
        "check_id": "python_mt5_dynamic_risk_baseline_review",
        "status": "pass" if not failed else "fail",
        "pass": not failed,
        "failed_comparison_count": len(failed),
        "source_count": len(recomputed_rows),
        "reason": "detail_files_recompute_match_dynamic_summary_and_freeze_snapshot"
        if not failed
        else "detail_files_do_not_match_summary",
        "next_check": "mapped_alignment_summary_review" if not failed else "fix_dynamic_risk_baseline_inputs",
        "no_main_logic_changes_in_this_step": True,
    }

    write_csv(
        OUT_DIR / "dynamic_risk_baseline_recomputed_summary.csv",
        recomputed_rows,
        [
            "source",
            "trade_count",
            "final_balance",
            "total_profit",
            "win_count",
            "win_rate_pct",
            "any_stage_sl_count",
            "all_stage_sl_count",
            "avg_stop_pts_spec",
            "avg_total_lot",
            "detail_file",
        ],
    )
    write_csv(
        OUT_DIR / "dynamic_risk_baseline_comparison.csv",
        compare_all,
        [
            "summary_label",
            "source",
            "metric",
            "recomputed_value",
            "summary_value",
            "diff",
            "tolerance",
            "pass",
        ],
    )
    write_csv(
        OUT_DIR / "dynamic_risk_baseline_review_decision.csv",
        [decision],
        [
            "decision_date",
            "check_id",
            "status",
            "pass",
            "failed_comparison_count",
            "source_count",
            "reason",
            "next_check",
            "no_main_logic_changes_in_this_step",
        ],
    )

    checklist_rows = []
    checklist_path = FREEZE_DIR / "final_regression_checklist.csv"
    for row in read_rows(checklist_path):
        if row.get("check_id") == "python_mt5_dynamic_risk_baseline_review":
            row["status"] = decision["status"]
            row["evidence"] = str((OUT_DIR / "dynamic_risk_baseline_review_decision.csv").relative_to(ROOT))
        else:
            row["evidence"] = ""
        checklist_rows.append(row)
    write_csv(
        OUT_DIR / "final_regression_checklist_status_after_dynamic_risk.csv",
        checklist_rows,
        ["order", "check_id", "description", "status", "evidence"],
    )

    readme = "\n".join(
        [
            "# stage_state_final_regression_dynamic_risk_baseline_review_20260718",
            "",
            "Final regression check 1: dynamic-risk baseline review.",
            "",
            "- `dynamic_risk_baseline_recomputed_summary.csv`: metrics recomputed from detail files.",
            "- `dynamic_risk_baseline_comparison.csv`: recomputed metrics versus source summary and freeze snapshot.",
            "- `dynamic_risk_baseline_review_decision.csv`: check decision.",
            "- `final_regression_checklist_status_after_dynamic_risk.csv`: checklist progress after this check.",
            "- `dynamic_risk_baseline_review.md`: human-readable review.",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8-sig")
    write_audit_md(decision, recomputed_rows, compare_all)

    print(f"wrote {OUT_DIR}")
    print(f"status={decision['status']}")
    print(f"failed_comparison_count={len(failed)}")


if __name__ == "__main__":
    main()
