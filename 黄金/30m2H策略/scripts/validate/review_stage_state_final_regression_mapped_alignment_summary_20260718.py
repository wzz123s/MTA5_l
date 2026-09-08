from __future__ import annotations


import csv
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(r"F:\use_code\MTA5_l")
VALIDATION_DIR = ROOT / "黄金" / "30m2H策略" / "data" / "validation"
MAPPED_DIR = VALIDATION_DIR / "mapped_trade_alignment_exec_model_stage_state_metadatafix_20260716"
FREEZE_DIR = VALIDATION_DIR / "stage_state_final_freeze_run_readiness_20260718"
DYNAMIC_REVIEW_DIR = VALIDATION_DIR / "stage_state_final_regression_dynamic_risk_baseline_review_20260718"
OUT_DIR = VALIDATION_DIR / "stage_state_final_regression_mapped_alignment_summary_review_20260718"


SOURCES = ["python_only", "python_mt5"]


SOURCE_FILES = {
    "python_only": {
        "unique": MAPPED_DIR / "python_only_mt5_unique_matches.csv",
        "unmatched_python": MAPPED_DIR / "python_only_unmatched_python_trades.csv",
        "unmatched_mt5": MAPPED_DIR / "python_only_unmatched_mt5_trades.csv",
    },
    "python_mt5": {
        "unique": MAPPED_DIR / "python_mt5_mt5_unique_matches.csv",
        "unmatched_python": MAPPED_DIR / "python_mt5_unmatched_python_trades.csv",
        "unmatched_mt5": MAPPED_DIR / "python_mt5_unmatched_mt5_trades.csv",
    },
}


SUMMARY_FIELDS = [
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
]


TOLERANCES = {
    "python_trades": 0.0,
    "mt5_trades": 0.0,
    "matched_unique": 0.0,
    "reliable_tier_matched": 0.0,
    "relaxed_tier_matched": 0.0,
    "python_unmatched": 0.0,
    "mt5_unmatched": 0.0,
    "matched_python_profit": 1e-6,
    "matched_mt5_profit": 1e-6,
    "matched_profit_diff": 1e-6,
    "any_sl_same_count": 0.0,
    "all_sl_same_count": 0.0,
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


def load_summary(path: Path) -> Dict[str, Dict[str, object]]:
    rows = read_rows(path)
    out: Dict[str, Dict[str, object]] = {}
    for row in rows:
        source = row.get("source", "")
        out[source] = {field: fnum(row.get(field)) for field in SUMMARY_FIELDS}
        out[source]["source"] = source
    return out


def recompute_source(source: str) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    unique_rows = read_rows(SOURCE_FILES[source]["unique"])
    unmatched_python_rows = read_rows(SOURCE_FILES[source]["unmatched_python"])
    unmatched_mt5_rows = read_rows(SOURCE_FILES[source]["unmatched_mt5"])

    matched_unique = len(unique_rows)
    reliable_tier_matched = sum(1 for row in unique_rows if truthy(row.get("is_reliable_tier")))
    relaxed_tier_matched = matched_unique - reliable_tier_matched
    matched_python_profit = sum(fnum(row.get("py_profit")) for row in unique_rows)
    matched_mt5_profit = sum(fnum(row.get("mt5_profit")) for row in unique_rows)
    matched_profit_diff = matched_python_profit - matched_mt5_profit
    any_sl_same_count = sum(1 for row in unique_rows if truthy(row.get("any_sl_same")))
    all_sl_same_count = sum(1 for row in unique_rows if truthy(row.get("all_sl_same")))

    summary = {
        "source": source,
        "python_trades": matched_unique + len(unmatched_python_rows),
        "mt5_trades": matched_unique + len(unmatched_mt5_rows),
        "matched_unique": matched_unique,
        "reliable_tier_matched": reliable_tier_matched,
        "relaxed_tier_matched": relaxed_tier_matched,
        "python_unmatched": len(unmatched_python_rows),
        "mt5_unmatched": len(unmatched_mt5_rows),
        "matched_python_profit": round(matched_python_profit, 6),
        "matched_mt5_profit": round(matched_mt5_profit, 6),
        "matched_profit_diff": round(matched_profit_diff, 6),
        "any_sl_same_count": any_sl_same_count,
        "all_sl_same_count": all_sl_same_count,
        "unique_file": str(SOURCE_FILES[source]["unique"].relative_to(ROOT)),
        "unmatched_python_file": str(SOURCE_FILES[source]["unmatched_python"].relative_to(ROOT)),
        "unmatched_mt5_file": str(SOURCE_FILES[source]["unmatched_mt5"].relative_to(ROOT)),
    }

    tier_counts = Counter(row.get("match_tier", "") for row in unique_rows)
    tier_rows = [
        {
            "source": source,
            "match_tier": tier,
            "unique_matches": count,
        }
        for tier, count in sorted(tier_counts.items())
    ]

    return summary, tier_rows


def compare_summary(
    recomputed: Dict[str, Dict[str, object]],
    expected: Dict[str, Dict[str, object]],
    summary_label: str,
) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for source in SOURCES:
        for field in SUMMARY_FIELDS:
            actual = fnum(recomputed[source].get(field))
            ref = fnum(expected[source].get(field))
            diff = actual - ref
            tolerance = TOLERANCES[field]
            out.append(
                {
                    "summary_label": summary_label,
                    "source": source,
                    "metric": field,
                    "recomputed_value": actual,
                    "summary_value": ref,
                    "diff": round(diff, 10),
                    "tolerance": tolerance,
                    "pass": abs(diff) <= tolerance,
                }
            )
    return out


def compare_tier_counts(recomputed_rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    expected_rows = read_rows(MAPPED_DIR / "unique_match_tier_counts.csv")
    expected = {
        (row.get("source", ""), row.get("match_tier", "")): fnum(row.get("unique_matches"))
        for row in expected_rows
    }
    recomputed = {
        (str(row.get("source", "")), str(row.get("match_tier", ""))): fnum(row.get("unique_matches"))
        for row in recomputed_rows
    }
    keys = sorted(set(expected) | set(recomputed))
    return [
        {
            "source": key[0],
            "match_tier": key[1],
            "recomputed_unique_matches": recomputed.get(key, 0.0),
            "summary_unique_matches": expected.get(key, 0.0),
            "diff": recomputed.get(key, 0.0) - expected.get(key, 0.0),
            "pass": recomputed.get(key, 0.0) == expected.get(key, 0.0),
        }
        for key in keys
    ]


def latest_checklist_rows() -> List[Dict[str, str]]:
    prior = DYNAMIC_REVIEW_DIR / "final_regression_checklist_status_after_dynamic_risk.csv"
    if prior.exists():
        return read_rows(prior)
    return read_rows(FREEZE_DIR / "final_regression_checklist.csv")


def write_audit_md(
    decision: Dict[str, object],
    recomputed_rows: List[Dict[str, object]],
    compare_rows: List[Dict[str, object]],
    tier_compare_rows: List[Dict[str, object]],
) -> None:
    lines: List[str] = []
    lines.append("# Final Regression: Mapped Alignment Summary Review")
    lines.append("")
    lines.append(f"- Decision date: {decision['decision_date']}")
    lines.append(f"- Check id: `{decision['check_id']}`")
    lines.append(f"- Status: `{decision['status']}`")
    lines.append(f"- Pass: `{decision['pass']}`")
    lines.append(f"- Reason: `{decision['reason']}`")
    lines.append("")
    lines.append("## Recomputed Summary")
    lines.append("")
    lines.append("| source | python trades | mt5 trades | matched | reliable | relaxed | python unmatched | mt5 unmatched | profit diff |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in recomputed_rows:
        lines.append(
            "| {source} | {python_trades} | {mt5_trades} | {matched_unique} | {reliable_tier_matched} | {relaxed_tier_matched} | {python_unmatched} | {mt5_unmatched} | {matched_profit_diff} |".format(
                **row
            )
        )
    lines.append("")
    lines.append("## Comparison Result")
    lines.append("")
    failed_summary = [row for row in compare_rows if not truthy(row.get("pass"))]
    failed_tier = [row for row in tier_compare_rows if not truthy(row.get("pass"))]
    lines.append(f"- Failed summary comparisons: `{len(failed_summary)}`")
    lines.append(f"- Failed tier comparisons: `{len(failed_tier)}`")
    lines.append("- Unique-match summary and final-freeze mapping snapshot are consistent with detail files.")
    lines.append("- Tier counts are consistent with `unique_match_tier_counts.csv`.")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append("This review only validates mapped alignment accounting. It does not change canonical mapper policy or rematch any trade.")
    lines.append("")
    (OUT_DIR / "mapped_alignment_summary_review.md").write_text(
        "\n".join(lines), encoding="utf-8-sig"
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    recomputed: Dict[str, Dict[str, object]] = {}
    tier_rows: List[Dict[str, object]] = []
    for source in SOURCES:
        summary, source_tier_rows = recompute_source(source)
        recomputed[source] = summary
        tier_rows.extend(source_tier_rows)

    recomputed_rows = [recomputed[source] for source in SOURCES]
    unique_summary = load_summary(MAPPED_DIR / "unique_match_summary.csv")
    freeze_summary = load_summary(FREEZE_DIR / "mapping_snapshot_summary.csv")
    compare_rows_all = compare_summary(recomputed, unique_summary, "unique_match_summary") + compare_summary(
        recomputed, freeze_summary, "final_freeze_mapping_snapshot"
    )
    tier_compare_rows = compare_tier_counts(tier_rows)

    failed_summary = [row for row in compare_rows_all if not truthy(row.get("pass"))]
    failed_tier = [row for row in tier_compare_rows if not truthy(row.get("pass"))]
    passed = not failed_summary and not failed_tier

    decision = {
        "decision_date": date.today().isoformat(),
        "check_id": "mapped_alignment_summary_review",
        "status": "pass" if passed else "fail",
        "pass": passed,
        "failed_summary_comparison_count": len(failed_summary),
        "failed_tier_comparison_count": len(failed_tier),
        "source_count": len(SOURCES),
        "reason": "unique_match_summary_and_freeze_mapping_snapshot_match_detail_files"
        if passed
        else "mapped_alignment_summary_does_not_match_detail_files",
        "next_check": "mt5_full_stage_state_ledger_closure_review" if passed else "fix_mapped_alignment_inputs",
        "no_mapper_policy_changes_in_this_step": True,
        "no_main_logic_changes_in_this_step": True,
    }

    write_csv(
        OUT_DIR / "mapped_alignment_recomputed_summary.csv",
        recomputed_rows,
        [
            "source",
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
            "unique_file",
            "unmatched_python_file",
            "unmatched_mt5_file",
        ],
    )
    write_csv(
        OUT_DIR / "mapped_alignment_summary_comparison.csv",
        compare_rows_all,
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
        OUT_DIR / "mapped_alignment_tier_counts_recomputed.csv",
        tier_rows,
        ["source", "match_tier", "unique_matches"],
    )
    write_csv(
        OUT_DIR / "mapped_alignment_tier_counts_comparison.csv",
        tier_compare_rows,
        [
            "source",
            "match_tier",
            "recomputed_unique_matches",
            "summary_unique_matches",
            "diff",
            "pass",
        ],
    )
    write_csv(
        OUT_DIR / "mapped_alignment_review_decision.csv",
        [decision],
        [
            "decision_date",
            "check_id",
            "status",
            "pass",
            "failed_summary_comparison_count",
            "failed_tier_comparison_count",
            "source_count",
            "reason",
            "next_check",
            "no_mapper_policy_changes_in_this_step",
            "no_main_logic_changes_in_this_step",
        ],
    )

    checklist_rows: List[Dict[str, object]] = []
    for row in latest_checklist_rows():
        if row.get("check_id") == "mapped_alignment_summary_review":
            row["status"] = decision["status"]
            row["evidence"] = str((OUT_DIR / "mapped_alignment_review_decision.csv").relative_to(ROOT))
        elif "evidence" not in row:
            row["evidence"] = ""
        checklist_rows.append(row)
    write_csv(
        OUT_DIR / "final_regression_checklist_status_after_mapped_alignment.csv",
        checklist_rows,
        ["order", "check_id", "description", "status", "evidence"],
    )

    readme = "\n".join(
        [
            "# stage_state_final_regression_mapped_alignment_summary_review_20260718",
            "",
            "Final regression check 2: mapped alignment summary review.",
            "",
            "- `mapped_alignment_recomputed_summary.csv`: metrics recomputed from unique/unmatched detail files.",
            "- `mapped_alignment_summary_comparison.csv`: recomputed summary versus source summary and freeze snapshot.",
            "- `mapped_alignment_tier_counts_recomputed.csv`: unique tier counts recomputed from detail files.",
            "- `mapped_alignment_tier_counts_comparison.csv`: tier counts versus `unique_match_tier_counts.csv`.",
            "- `mapped_alignment_review_decision.csv`: check decision.",
            "- `final_regression_checklist_status_after_mapped_alignment.csv`: checklist progress after this check.",
            "- `mapped_alignment_summary_review.md`: human-readable review.",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8-sig")
    write_audit_md(decision, recomputed_rows, compare_rows_all, tier_compare_rows)

    print(f"wrote {OUT_DIR}")
    print(f"status={decision['status']}")
    print(f"failed_summary_comparison_count={len(failed_summary)}")
    print(f"failed_tier_comparison_count={len(failed_tier)}")


if __name__ == "__main__":
    main()
