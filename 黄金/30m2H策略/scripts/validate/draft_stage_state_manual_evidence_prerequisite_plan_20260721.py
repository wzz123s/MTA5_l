from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
FILL_PLAN_DIR = VALIDATION_DIR / "stage_state_live_gate_evidence_fill_plan_20260721"
AUTO_SAFE_DIR = VALIDATION_DIR / "stage_state_live_gate_auto_safe_evidence_20260721"
OUT_DIR = VALIDATION_DIR / "stage_state_manual_evidence_prerequisite_plan_20260721"

FILL_PLAN = FILL_PLAN_DIR / "live_gate_evidence_fill_plan.csv"
AUTO_SAFE_PLAN = AUTO_SAFE_DIR / "auto_safe_evidence_collection_plan.csv"


def read_rows(path: Path) -> List[Dict[str, str]]:
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


def boolish(value: object) -> bool:
    return str(value).strip().lower() == "true"


def collected_auto_keys(auto_rows: List[Dict[str, str]]) -> set[Tuple[str, str]]:
    return {
        (row.get("gap_id", ""), row.get("file_name", ""))
        for row in auto_rows
        if row.get("auto_safe_status") == "collected"
    }


def prerequisite_type(row: Dict[str, str]) -> str:
    method = row.get("collection_method", "")
    if method == "rehearsal":
        return "nonprod_rehearsal"
    if method == "auto":
        return "deferred_auto_after_manual_approval"
    if boolish(row.get("contains_secret_risk")):
        return "manual_secret_safe_document"
    if boolish(row.get("live_action_risk")):
        return "manual_live_action_approval"
    return "manual_confirmation"


def confirmer(row: Dict[str, str]) -> str:
    role = row.get("owner_role", "") or "operator"
    if row.get("priority") == "P0" and boolish(row.get("requires_user_approval")):
        return f"user plus {role}"
    if boolish(row.get("requires_user_approval")):
        return f"user or delegated {role}"
    return role


def prerequisite_source(row: Dict[str, str]) -> str:
    method = row.get("collection_method", "")
    if method == "rehearsal":
        return "demo account, strategy tester, or SIM_ONLY-only rehearsal artifacts"
    if method == "auto":
        return "only after the related manual approval/package/source prerequisite is complete"
    return row.get("allowed_source", "") or "manual evidence document"


def forbidden_content(row: Dict[str, str]) -> str:
    forbidden = [row.get("blocked_action", "").strip()]
    if boolish(row.get("contains_secret_risk")):
        forbidden.append("real account numbers, passwords, tokens, API keys, or secret values")
    if boolish(row.get("live_action_risk")):
        forbidden.append("real-money order placement, live chart attachment, or live set switching")
    if row.get("file_name") == "parsed_live_set_template.json":
        forbidden.append("InpSimMode=false until explicit transition approval exists")
    if row.get("file_name") == "broker_symbol_spec.csv":
        forbidden.append("MT5 order actions while collecting read-only symbol/account specs")
    return "; ".join(part for part in forbidden if part)


def next_allowed_action(row: Dict[str, str]) -> str:
    file_name = row.get("file_name", "")
    method = row.get("collection_method", "")
    if file_name == "live_package_hashes.csv":
        return "hash only the user-approved package manifest paths"
    if file_name == "parsed_live_set_template.json":
        return "parse only a reviewed set template after transition approval exists"
    if file_name == "broker_symbol_spec.csv":
        return "request explicit read-only MT5 approval, then collect symbol spec without orders"
    if method == "rehearsal":
        return "prepare demo/tester rehearsal steps and expected evidence files"
    return "fill the template with redacted/manual confirmation data only"


def build_prerequisites(
    fill_rows: List[Dict[str, str]],
    auto_rows: List[Dict[str, str]],
    generated_at: str,
) -> List[Dict[str, object]]:
    collected = collected_auto_keys(auto_rows)
    rows: List[Dict[str, object]] = []
    sequence = 0
    for row in fill_rows:
        key = (row.get("gap_id", ""), row.get("file_name", ""))
        if key in collected:
            continue
        sequence += 1
        rows.append(
            {
                "prerequisite_sequence": sequence,
                "fill_sequence": row.get("fill_sequence", ""),
                "gap_id": row.get("gap_id", ""),
                "priority": row.get("priority", ""),
                "category": row.get("category", ""),
                "severity": row.get("severity", ""),
                "file_name": row.get("file_name", ""),
                "collection_method": row.get("collection_method", ""),
                "prerequisite_type": prerequisite_type(row),
                "confirmer": confirmer(row),
                "owner_role": row.get("owner_role", ""),
                "required_fields": row.get("required_fields", ""),
                "prerequisite_source": prerequisite_source(row),
                "forbidden_content": forbidden_content(row),
                "next_allowed_action": next_allowed_action(row),
                "contains_secret_risk": row.get("contains_secret_risk", "False"),
                "live_action_risk": row.get("live_action_risk", "False"),
                "requires_user_approval": row.get("requires_user_approval", "False"),
                "completion_state": "open_prerequisite",
                "gate_status": "open",
                "ready_to_live_trade": False,
                "generated_at": generated_at,
            }
        )
    return rows


def summarize(rows: List[Dict[str, object]], fill_rows: List[Dict[str, str]], auto_rows: List[Dict[str, str]], generated_at: str) -> Dict[str, object]:
    return {
        "decision_time": generated_at,
        "check_id": "stage_state_manual_evidence_prerequisite_plan",
        "status": "manual_prerequisites_drafted_live_blocked",
        "fill_plan_items_total": len(fill_rows),
        "auto_safe_items_total": len(auto_rows),
        "auto_safe_collected_items": sum(1 for row in auto_rows if row.get("auto_safe_status") == "collected"),
        "remaining_prerequisite_items": len(rows),
        "pending_auto_items": sum(1 for row in rows if row.get("collection_method") == "auto"),
        "manual_items": sum(1 for row in rows if row.get("collection_method") == "manual"),
        "rehearsal_items": sum(1 for row in rows if row.get("collection_method") == "rehearsal"),
        "p0_items": sum(1 for row in rows if row.get("priority") == "P0"),
        "p1_items": sum(1 for row in rows if row.get("priority") == "P1"),
        "secret_risk_items": sum(1 for row in rows if boolish(row.get("contains_secret_risk"))),
        "live_action_risk_items": sum(1 for row in rows if boolish(row.get("live_action_risk"))),
        "requires_user_approval_items": sum(1 for row in rows if boolish(row.get("requires_user_approval"))),
        "gate_status": "open",
        "ready_to_live_trade": False,
        "recommended_next_action": "review_manual_evidence_prerequisite_plan",
    }


def build_report(decision: Dict[str, object], rows: List[Dict[str, object]]) -> str:
    lines = [
        "# Manual Evidence Prerequisite Plan",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- remaining_prerequisite_items: `{decision['remaining_prerequisite_items']}`",
        f"- pending_auto_items: `{decision['pending_auto_items']}`",
        f"- manual_items: `{decision['manual_items']}`",
        f"- rehearsal_items: `{decision['rehearsal_items']}`",
        f"- p0_items: `{decision['p0_items']}`",
        f"- p1_items: `{decision['p1_items']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        "",
        "## Boundary",
        "",
        "- This plan defines prerequisites only; it does not fill production evidence.",
        "- Real credentials, passwords, tokens, and account secret values remain forbidden.",
        "- Live chart attachment, real-money orders, and live set switching remain forbidden.",
        "- All gates remain open and live trading remains blocked.",
        "",
        "## Execution Order",
        "",
    ]
    for row in rows:
        lines.append(
            f"{row['prerequisite_sequence']}. `{row['priority']}` `{row['gap_id']}` `{row['file_name']}` "
            f"- {row['prerequisite_type']}; confirmer: {row['confirmer']}; next: {row['next_allowed_action']}."
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().isoformat(timespec="seconds")
    fill_rows = read_rows(FILL_PLAN)
    auto_rows = read_rows(AUTO_SAFE_PLAN)
    prerequisite_rows = build_prerequisites(fill_rows, auto_rows, generated_at)
    decision = summarize(prerequisite_rows, fill_rows, auto_rows, generated_at)

    fieldnames = [
        "prerequisite_sequence",
        "fill_sequence",
        "gap_id",
        "priority",
        "category",
        "severity",
        "file_name",
        "collection_method",
        "prerequisite_type",
        "confirmer",
        "owner_role",
        "required_fields",
        "prerequisite_source",
        "forbidden_content",
        "next_allowed_action",
        "contains_secret_risk",
        "live_action_risk",
        "requires_user_approval",
        "completion_state",
        "gate_status",
        "ready_to_live_trade",
        "generated_at",
    ]
    write_csv(OUT_DIR / "manual_evidence_prerequisite_plan.csv", prerequisite_rows, fieldnames)
    write_csv(OUT_DIR / "manual_evidence_prerequisite_plan_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "manual_evidence_prerequisite_plan_decision.json", decision)
    (OUT_DIR / "manual_evidence_prerequisite_plan.md").write_text(build_report(decision, prerequisite_rows), encoding="utf-8-sig")

    for key, value in decision.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
