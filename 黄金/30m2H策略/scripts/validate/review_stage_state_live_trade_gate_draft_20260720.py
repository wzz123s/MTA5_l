from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
CHECKLIST_DIR = VALIDATION_DIR / "stage_state_live_trade_gate_checklist_draft_20260720"
OUT_DIR = VALIDATION_DIR / "stage_state_live_trade_gate_draft_review_20260720"

CHECKLIST = CHECKLIST_DIR / "live_trade_gate_checklist_draft.csv"
CHECKLIST_DECISION = CHECKLIST_DIR / "live_trade_gate_checklist_draft_decision.json"
MANUAL_TEMPLATE = CHECKLIST_DIR / "live_trade_gate_manual_confirmation_template.csv"
GAP_AUDIT_DECISION = VALIDATION_DIR / "stage_state_live_trade_readiness_gap_audit_20260720" / "live_trade_readiness_gap_decision.json"
SIM_READINESS_DECISION = VALIDATION_DIR / "stage_state_sim_only_post_observation_readiness_gate_20260720" / "sim_only_post_observation_readiness_decision.json"
TERMINAL_EXE = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")
AUTO_TRADER = ROOT / "auto_trade" / "auto_trader.py"
STOP_FLAG = ROOT / "auto_trade" / "RUNNER_STOP.flag"

EXPECTED_GAPS = {
    "LIVE-GAP-001",
    "LIVE-GAP-002",
    "LIVE-GAP-003",
    "LIVE-GAP-004",
    "LIVE-GAP-005",
    "LIVE-GAP-006",
    "LIVE-GAP-007",
    "LIVE-GAP-008",
    "LIVE-GAP-009",
    "LIVE-GAP-010",
}


def read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def add_check(
    checks: List[Dict[str, object]],
    check_id: str,
    passed: bool,
    actual: object,
    expected: object,
    severity: str = "blocker",
    note: str = "",
) -> None:
    checks.append(
        {
            "check_id": check_id,
            "status": "pass" if passed else "fail",
            "pass": passed,
            "actual": actual,
            "expected": expected,
            "severity": severity,
            "note": note,
        }
    )


def mt5_counts() -> Dict[str, object]:
    try:
        import MetaTrader5 as mt5  # type: ignore
    except Exception as exc:
        return {"ok": False, "positions_count": "", "orders_count": "", "error": f"import failed: {exc}"}
    ok = mt5.initialize(path=str(TERMINAL_EXE))
    if not ok:
        return {"ok": False, "positions_count": "", "orders_count": "", "error": str(mt5.last_error())}
    try:
        positions = mt5.positions_get() or []
        orders = mt5.orders_get() or []
        return {"ok": True, "positions_count": len(positions), "orders_count": len(orders), "error": ""}
    finally:
        mt5.shutdown()


def build_report(decision: Dict[str, object], checks: List[Dict[str, object]]) -> str:
    failed = [row for row in checks if row["status"] != "pass"]
    lines = [
        "# Live Trade Gate Draft Review",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- draft_review_completed: `{decision['draft_review_completed']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        f"- ready_to_continue_sim_only_monitoring: `{decision['ready_to_continue_sim_only_monitoring']}`",
        f"- checklist_item_count: `{decision['checklist_item_count']}`",
        f"- open_gate_count: `{decision['open_gate_count']}`",
        f"- blocker_failure_count: `{decision['blocker_failure_count']}`",
        f"- positions_count: `{decision['positions_count']}`",
        f"- orders_count: `{decision['orders_count']}`",
        "",
        "## Boundary",
        "",
        "- This draft review intentionally keeps `ready_to_live_trade=false`.",
        "- It validates the checklist structure only.",
        "- It does not close any live gap.",
        "- It does not run `auto_trade/auto_trader.py`.",
        "",
        "## Failed Checks",
        "",
    ]
    if not failed:
        lines.append("- None.")
    else:
        for row in failed:
            lines.append(f"- `{row['check_id']}`: {row['actual']} (expected {row['expected']})")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    checklist_decision = read_json(CHECKLIST_DECISION)
    gap_decision = read_json(GAP_AUDIT_DECISION)
    sim_readiness = read_json(SIM_READINESS_DECISION)
    checklist = read_rows(CHECKLIST)
    manual = read_rows(MANUAL_TEMPLATE)
    counts = mt5_counts()

    gap_ids = {row.get("gap_id", "") for row in checklist}
    open_items = [row for row in checklist if row.get("draft_status") == "open"]
    missing_fields = [
        row.get("gap_id", "")
        for row in checklist
        if not all(
            row.get(field, "").strip()
            for field in ["closure_condition", "evidence_required", "script_check", "manual_confirmation", "fail_closed_action"]
        )
    ]

    checks: List[Dict[str, object]] = []
    add_check(checks, "checklist_exists", CHECKLIST.exists(), CHECKLIST, "exists")
    add_check(checks, "checklist_decision_draft_complete", checklist_decision.get("status") == "draft_complete", checklist_decision.get("status"), "draft_complete")
    add_check(checks, "checklist_covers_10_gaps", len(checklist) == 10, len(checklist), 10)
    add_check(checks, "checklist_gap_ids_complete", gap_ids == EXPECTED_GAPS, ";".join(sorted(gap_ids)), ";".join(sorted(EXPECTED_GAPS)))
    add_check(checks, "all_checklist_items_open", len(open_items) == 10, len(open_items), 10)
    add_check(checks, "all_required_fields_present", not missing_fields, ";".join(missing_fields), "no missing required fields")
    add_check(checks, "manual_template_exists", MANUAL_TEMPLATE.exists(), MANUAL_TEMPLATE, "exists")
    add_check(checks, "manual_template_covers_10_gaps", len(manual) == 10, len(manual), 10)
    add_check(checks, "gap_audit_blocked", gap_decision.get("status") == "blocked", gap_decision.get("status"), "blocked")
    add_check(checks, "sim_readiness_pass", sim_readiness.get("status") == "pass", sim_readiness.get("status"), "pass")
    add_check(checks, "auto_trader_file_not_executed_by_this_review", AUTO_TRADER.exists(), AUTO_TRADER, "exists but not executed")
    add_check(checks, "stop_flag_absent", not STOP_FLAG.exists(), STOP_FLAG, "absent")
    add_check(checks, "mt5_counts_available", truthy(counts.get("ok")), counts.get("error") or counts.get("ok"), True)
    add_check(checks, "mt5_positions_zero_now", counts.get("positions_count") == 0, counts.get("positions_count"), 0)
    add_check(checks, "mt5_orders_zero_now", counts.get("orders_count") == 0, counts.get("orders_count"), 0)
    add_check(checks, "ready_to_live_trade_default_false", checklist_decision.get("ready_to_live_trade") is False, checklist_decision.get("ready_to_live_trade"), False)

    blocker_failures = [row for row in checks if row["status"] == "fail" and row["severity"] == "blocker"]
    structural_pass = not blocker_failures
    decision = {
        "decision_time": datetime.now().isoformat(timespec="seconds"),
        "check_id": "stage_state_live_trade_gate_draft_review",
        "status": "draft_review_pass_live_blocked" if structural_pass else "draft_review_fail",
        "draft_review_completed": structural_pass,
        "ready_to_continue_sim_only_monitoring": sim_readiness.get("status") == "pass",
        "ready_to_live_trade": False,
        "checklist_item_count": len(checklist),
        "open_gate_count": len(open_items),
        "blocker_failure_count": len(blocker_failures),
        "positions_count": counts.get("positions_count", ""),
        "orders_count": counts.get("orders_count", ""),
        "checklist_path": str(CHECKLIST),
        "recommended_next_action": "fill_live_gate_evidence_templates_without_enabling_live",
    }

    write_csv(
        OUT_DIR / "live_trade_gate_draft_review_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(OUT_DIR / "live_trade_gate_draft_review_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "live_trade_gate_draft_review_decision.json", decision)
    (OUT_DIR / "live_trade_gate_draft_review.md").write_text(build_report(decision, checks), encoding="utf-8-sig")

    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0 if structural_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
