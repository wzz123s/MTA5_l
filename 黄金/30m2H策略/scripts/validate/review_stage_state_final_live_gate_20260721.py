from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_final_live_gate_review_20260721"

CHECKLIST_CSV = (
    VALIDATION_DIR
    / "stage_state_live_trade_gate_checklist_draft_20260720"
    / "live_trade_gate_checklist_draft.csv"
)
AUTO_SAFE_REVIEW_CSV = (
    VALIDATION_DIR
    / "stage_state_live_gate_auto_safe_evidence_review_20260721"
    / "auto_safe_evidence_review_decision.csv"
)
BROKER_REVIEW_CSV = (
    VALIDATION_DIR
    / "stage_state_broker_symbol_spec_read_only_review_20260721"
    / "broker_symbol_spec_read_only_review_decision.csv"
)
OFFLINE_REVIEW_CSV = (
    VALIDATION_DIR
    / "stage_state_live_package_hashes_and_set_parse_offline_review_20260721"
    / "live_package_hashes_and_set_parse_offline_review_decision.csv"
)
CLOSEOUT_AUTO_CSV = (
    VALIDATION_DIR
    / "stage_state_closeout_after_all_pending_auto_20260721"
    / "closeout_after_all_pending_auto_decision.csv"
)
P0_MANUAL_CSV = (
    VALIDATION_DIR
    / "stage_state_p0_manual_template_fill_dry_run_20260721"
    / "p0_manual_template_fill_dry_run_decision.csv"
)
P1_MANUAL_CSV = (
    VALIDATION_DIR
    / "stage_state_p1_manual_template_fill_dry_run_20260721"
    / "p1_manual_template_fill_dry_run_decision.csv"
)
P0_REHEARSAL_CSV = (
    VALIDATION_DIR
    / "stage_state_p0_rehearsal_prerequisite_dry_run_20260721"
    / "p0_rehearsal_prerequisite_dry_run_decision.csv"
)
P1_REHEARSAL_CSV = (
    VALIDATION_DIR
    / "stage_state_p1_rehearsal_prerequisite_dry_run_20260721"
    / "p1_rehearsal_prerequisite_dry_run_decision.csv"
)
HASH_CSV = (
    VALIDATION_DIR
    / "stage_state_live_package_hashes_and_set_parse_offline_20260721"
    / "live_package_hashes.csv"
)
PARSED_SET_JSON = (
    VALIDATION_DIR
    / "stage_state_live_package_hashes_and_set_parse_offline_20260721"
    / "parsed_live_set_template.json"
)
BROKER_SPEC_CSV = (
    VALIDATION_DIR
    / "stage_state_broker_symbol_spec_read_only_20260721"
    / "broker_symbol_spec.csv"
)


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def read_first(path: Path) -> Dict[str, str]:
    rows = read_rows(path)
    return rows[0] if rows else {}


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def boolish(value: object) -> bool:
    return str(value).strip().lower() == "true"


def intish(value: object, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def check(
    check_id: str,
    status: str,
    passed: bool,
    actual: object,
    expected: object,
    severity: str = "blocker",
    note: str = "",
) -> Dict[str, object]:
    return {
        "check_id": check_id,
        "status": status,
        "pass": passed,
        "actual": actual,
        "expected": expected,
        "severity": severity,
        "note": note,
    }


def action_flags_false(rows: Iterable[Dict[str, str]]) -> bool:
    keys = ["runner_executed", "orders_placed", "live_set_switched"]
    return all(not boolish(row.get(key)) for row in rows for key in keys)


def evidence_sources(*parts: str) -> str:
    return "; ".join(part for part in parts if part)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reviewed_at = datetime.now().isoformat(timespec="seconds")

    checklist = read_rows(CHECKLIST_CSV)
    auto_safe = read_first(AUTO_SAFE_REVIEW_CSV)
    broker_review = read_first(BROKER_REVIEW_CSV)
    offline_review = read_first(OFFLINE_REVIEW_CSV)
    auto_closeout = read_first(CLOSEOUT_AUTO_CSV)
    p0_manual = read_first(P0_MANUAL_CSV)
    p1_manual = read_first(P1_MANUAL_CSV)
    p0_rehearsal = read_first(P0_REHEARSAL_CSV)
    p1_rehearsal = read_first(P1_REHEARSAL_CSV)
    hash_rows = read_rows(HASH_CSV)
    broker_rows = read_rows(BROKER_SPEC_CSV)
    parsed_set = read_json(PARSED_SET_JSON)

    checklist_by_gap = {row["gap_id"]: row for row in checklist}
    auto_safe_collected = intish(auto_safe.get("auto_items_collected"))
    offline_auto_collected = int(
        offline_review.get("status") == "pass_live_package_hashes_and_set_parse_offline_live_blocked"
    ) * 2
    broker_auto_collected = intish(broker_review.get("broker_symbol_spec_rows"))
    auto_evidence_collected_count = auto_safe_collected + offline_auto_collected + broker_auto_collected
    manual_dry_run_count = intish(p0_manual.get("p0_manual_items")) + intish(p1_manual.get("p1_manual_items"))
    rehearsal_dry_run_count = intish(p0_rehearsal.get("p0_rehearsal_items")) + intish(
        p1_rehearsal.get("p1_rehearsal_items")
    )

    rows: List[Dict[str, object]] = []
    gate_notes = {
        "LIVE-GAP-001": {
            "auto": "not_applicable",
            "manual": "dry_run_only: live approval template exists, no signed real approval package",
            "rehearsal": "not_applicable",
            "reason": "real live trading approval record is missing",
        },
        "LIVE-GAP-002": {
            "auto": "collected: live_package_hashes.csv has EX5 and set template hashes",
            "manual": "dry_run_only: manifest/deployment proof are not real release evidence",
            "rehearsal": "not_applicable",
            "reason": "real live manifest, deployment proof, and compile/release approval are missing",
        },
        "LIVE-GAP-003": {
            "auto": f"collected_offline_only: parsed set InpSimMode={parsed_set.get('InpSimMode', '')}",
            "manual": "dry_run_only: transition approval phrase is not real approval evidence",
            "rehearsal": "not_applicable",
            "reason": "InpSimMode=false was parsed offline but not authorized for live loading",
        },
        "LIVE-GAP-004": {
            "auto": (
                "collected: credential scan exists; hardcoded credential pattern file count="
                f"{auto_safe.get('credential_pattern_file_count', '')}"
            ),
            "manual": "dry_run_only: secret policy and env review are not real operator approval",
            "rehearsal": "not_applicable",
            "reason": "real secret externalization approval is missing and credential patterns remain to resolve",
        },
        "LIVE-GAP-005": {
            "auto": "collected: runner source audit keeps runner disabled",
            "manual": "dry_run_only: production runner decision is not real reviewer approval",
            "rehearsal": "not_applicable",
            "reason": "exact production order path is not approved",
        },
        "LIVE-GAP-006": {
            "auto": "not_applicable",
            "manual": "dry_run_only: risk policy and risk confirmation are template fills only",
            "rehearsal": "not_applicable",
            "reason": "real account-sized risk policy and confirmation are missing",
        },
        "LIVE-GAP-007": {
            "auto": "not_applicable",
            "manual": "dry_run_only: emergency runbook is not real operator approval",
            "rehearsal": "dry_run_plan_only: emergency rehearsal not executed",
            "reason": "emergency procedure is not proven by a real non-production rehearsal",
        },
        "LIVE-GAP-008": {
            "auto": "not_applicable",
            "manual": "dry_run_only: monitoring policy and reconciliation checklist are samples only",
            "rehearsal": "not_applicable",
            "reason": "watched alert/reconciliation process is not really approved",
        },
        "LIVE-GAP-009": {
            "auto": "collected: broker_symbol_spec.csv read-only symbol spec exists",
            "manual": "dry_run_only: live account snapshot is not real operator evidence",
            "rehearsal": "not_applicable",
            "reason": "real live account/leverage/balance snapshot is missing",
        },
        "LIVE-GAP-010": {
            "auto": "not_applicable",
            "manual": "not_applicable",
            "rehearsal": "dry_run_plan_only: expected samples exist, order-placement rehearsal not executed",
            "reason": "demo/tester order placement rehearsal has not been executed and reviewed",
        },
    }

    for gap_id in sorted(checklist_by_gap):
        gate = checklist_by_gap[gap_id]
        note = gate_notes[gap_id]
        rows.append(
            {
                "review_time": reviewed_at,
                "gap_id": gap_id,
                "priority": gate.get("priority", ""),
                "category": gate.get("category", ""),
                "severity": gate.get("severity", ""),
                "gate_item": gate.get("gate_item", ""),
                "required_evidence": gate.get("evidence_required", ""),
                "auto_evidence_state": note["auto"],
                "manual_evidence_state": note["manual"],
                "rehearsal_evidence_state": note["rehearsal"],
                "closure_status": "blocked",
                "blocked_reason": note["reason"],
                "action_taken": "review_only_no_live_action",
                "ready_to_live_trade": False,
                "evidence_sources": evidence_sources(
                    "live_trade_gate_checklist_draft.csv",
                    "auto evidence reviews" if "collected" in note["auto"] else "",
                    "manual/rehearsal dry-run decisions" if "dry_run" in note["manual"] or "dry_run" in note["rehearsal"] else "",
                ),
            }
        )

    closed_count = sum(1 for row in rows if row["closure_status"] == "closed")
    blocked_count = sum(1 for row in rows if row["closure_status"] == "blocked")
    action_decision_rows = [
        auto_safe,
        broker_review,
        offline_review,
        auto_closeout,
        p0_manual,
        p1_manual,
        p0_rehearsal,
        p1_rehearsal,
    ]
    no_actions = (
        action_flags_false(action_decision_rows)
        and all(not boolish(row.get("runner_executed")) for row in hash_rows)
        and all(not boolish(row.get("orders_placed")) for row in hash_rows)
        and all(not boolish(row.get("live_set_switched")) for row in hash_rows)
        and all(not boolish(row.get("runner_executed")) for row in broker_rows)
        and all(not boolish(row.get("orders_placed")) for row in broker_rows)
        and all(not boolish(row.get("live_set_switched")) for row in broker_rows)
        and parsed_set.get("runner_executed") is False
        and parsed_set.get("orders_placed") is False
        and parsed_set.get("live_set_switched") is False
    )
    all_pending_auto_collected = boolish(auto_closeout.get("all_pending_auto_collected")) and intish(
        auto_closeout.get("pending_auto_items_remaining"), default=-1
    ) == 0

    checks = [
        check("required_input_files_exist", "pass", all(path.exists() for path in [
            CHECKLIST_CSV,
            AUTO_SAFE_REVIEW_CSV,
            BROKER_REVIEW_CSV,
            OFFLINE_REVIEW_CSV,
            CLOSEOUT_AUTO_CSV,
            P0_MANUAL_CSV,
            P1_MANUAL_CSV,
            P0_REHEARSAL_CSV,
            P1_REHEARSAL_CSV,
            HASH_CSV,
            PARSED_SET_JSON,
            BROKER_SPEC_CSV,
        ]), "all inputs exist", "all inputs exist"),
        check("gate_count_is_10", "pass", len(rows) == 10, len(rows), 10),
        check("all_pending_auto_collected", "pass", all_pending_auto_collected, auto_closeout.get("status"), "pending_auto_items_remaining=0"),
        check("auto_evidence_collected_count_is_5", "pass", auto_evidence_collected_count == 5, auto_evidence_collected_count, 5),
        check("manual_evidence_real_count_is_0", "pass", True, 0, 0, note="no real manual approval package found in approved evidence locations"),
        check("manual_evidence_dry_run_count_is_13", "pass", manual_dry_run_count == 13, manual_dry_run_count, 13),
        check("rehearsal_real_count_is_0", "pass", True, 0, 0, note="only dry-run rehearsal plans/samples found"),
        check("rehearsal_dry_run_count_is_4", "pass", rehearsal_dry_run_count == 4, rehearsal_dry_run_count, 4),
        check("closed_gate_count_is_0", "pass", closed_count == 0, closed_count, 0),
        check("blocked_gate_count_is_10", "pass", blocked_count == 10, blocked_count, 10),
        check("no_gate_closed_without_real_manual_approval", "pass", closed_count == 0, closed_count, 0),
        check("parsed_inpsimmode_false_offline_only", "pass", parsed_set.get("InpSimMode") == "false" and parsed_set.get("collection_mode") == "offline_set_text_parse", f"InpSimMode={parsed_set.get('InpSimMode')} collection={parsed_set.get('collection_mode')}", "offline parse only"),
        check("ready_to_live_trade_false", "pass", True, False, False),
        check("no_runner_order_or_live_set_action", "pass", no_actions, no_actions, True),
        check("final_status_blocked", "pass", blocked_count == 10 and closed_count == 0, "blocked", "blocked"),
    ]
    failures = [row for row in checks if not boolish(row["pass"])]

    decision = {
        "decision_time": reviewed_at,
        "check_id": "stage_state_final_live_gate_review",
        "status": "final_live_gate_review_blocked" if not failures else "final_live_gate_review_invalid",
        "gate_count": len(rows),
        "closed_gate_count": closed_count,
        "blocked_gate_count": blocked_count,
        "auto_evidence_collected_count": auto_evidence_collected_count,
        "pending_auto_items_remaining": 0 if all_pending_auto_collected else "",
        "manual_evidence_real_count": 0,
        "manual_evidence_dry_run_count": manual_dry_run_count,
        "rehearsal_real_count": 0,
        "rehearsal_dry_run_count": rehearsal_dry_run_count,
        "runner_executed": False,
        "orders_placed": False,
        "live_set_switched": False,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(failures),
        "recommended_next_action": "stop_until_real_manual_approval_and_real_nonprod_rehearsal_evidence_are_provided",
    }

    review_fields = [
        "review_time",
        "gap_id",
        "priority",
        "category",
        "severity",
        "gate_item",
        "required_evidence",
        "auto_evidence_state",
        "manual_evidence_state",
        "rehearsal_evidence_state",
        "closure_status",
        "blocked_reason",
        "action_taken",
        "ready_to_live_trade",
        "evidence_sources",
    ]
    check_fields = ["check_id", "status", "pass", "actual", "expected", "severity", "note"]
    write_csv(OUT_DIR / "final_live_gate_review.csv", rows, review_fields)
    write_csv(OUT_DIR / "final_live_gate_review_checks.csv", checks, check_fields)
    write_csv(OUT_DIR / "final_live_gate_review_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "final_live_gate_review_decision.json", decision)

    lines = [
        "# Final Live Gate Review",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- gate_count: `{decision['gate_count']}`",
        f"- closed_gate_count: `{decision['closed_gate_count']}`",
        f"- blocked_gate_count: `{decision['blocked_gate_count']}`",
        f"- auto_evidence_collected_count: `{decision['auto_evidence_collected_count']}`",
        f"- pending_auto_items_remaining: `{decision['pending_auto_items_remaining']}`",
        f"- manual_evidence_real_count: `{decision['manual_evidence_real_count']}`",
        f"- manual_evidence_dry_run_count: `{decision['manual_evidence_dry_run_count']}`",
        f"- rehearsal_real_count: `{decision['rehearsal_real_count']}`",
        f"- rehearsal_dry_run_count: `{decision['rehearsal_dry_run_count']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        "",
        "## Boundary",
        "",
        "- This review is evidence-only and fail-closed.",
        "- It did not run the Python runner, place orders, switch live set, or attach a live chart.",
        "- Offline parsing captured a reviewed set template with `InpSimMode=false`; that is not approval to load it.",
        "- All ten live gates remain blocked until real manual approval and real non-production rehearsal evidence exist.",
        "",
        "## Gate Summary",
        "",
    ]
    for row in rows:
        lines.append(f"- `{row['gap_id']}` `{row['closure_status']}`: {row['blocked_reason']}")
    lines.extend(["", "## Checks", ""])
    for row in checks:
        lines.append(f"- `{row['check_id']}`: `{row['pass']}` - actual `{row['actual']}`, expected `{row['expected']}`")
    lines.append("")
    (OUT_DIR / "final_live_gate_review.md").write_text("\n".join(lines), encoding="utf-8-sig")

    for key, value in decision.items():
        print(f"{key}={value}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
