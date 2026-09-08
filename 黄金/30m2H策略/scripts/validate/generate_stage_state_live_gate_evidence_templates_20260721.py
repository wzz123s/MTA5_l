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
OUT_DIR = VALIDATION_DIR / "stage_state_live_gate_evidence_templates_20260721"
TEMPLATE_DIR = OUT_DIR / "evidence_templates"

CHECKLIST = CHECKLIST_DIR / "live_trade_gate_checklist_draft.csv"
MANUAL_TEMPLATE = CHECKLIST_DIR / "live_trade_gate_manual_confirmation_template.csv"


TEMPLATE_SPECS: Dict[str, List[Dict[str, object]]] = {
    "LIVE-GAP-001": [
        {
            "file_name": "live_trade_approval_record.md",
            "kind": "markdown",
            "required_fields": [
                "approval_id",
                "approval_date",
                "approver",
                "account_alias",
                "symbol",
                "max_risk",
                "allowed_runner",
                "rollback_owner",
                "approval_scope",
            ],
        }
    ],
    "LIVE-GAP-002": [
        {"file_name": "live_package_manifest.json", "kind": "json", "required_fields": ["package_id", "ex5_path", "set_path", "startup_config_path", "deployment_path", "package_is_sim_only"]},
        {"file_name": "live_package_hashes.csv", "kind": "csv", "headers": ["artifact", "path", "sha256", "verified_by", "verified_at"]},
        {"file_name": "live_package_deployment_proof.md", "kind": "markdown", "required_fields": ["deployed_ex5_path", "deployed_set_path", "deployed_startup_config_path", "reviewer"]},
    ],
    "LIVE-GAP-003": [
        {"file_name": "sim_mode_transition_approval.md", "kind": "markdown", "required_fields": ["approval_id", "required_phrase", "prior_gate_statuses", "approver", "approval_date"]},
        {"file_name": "parsed_live_set_template.json", "kind": "json", "required_fields": ["set_path", "InpSimMode", "InpExportCSV", "InpExportTradeLedger"]},
    ],
    "LIVE-GAP-004": [
        {"file_name": "secret_policy.md", "kind": "markdown", "required_fields": ["secret_source", "allowed_runtime", "forbidden_locations", "operator"]},
        {"file_name": "credential_scan_report.csv", "kind": "csv", "headers": ["path", "scan_status", "hardcoded_account_pattern", "hardcoded_password_pattern", "reviewed_at"]},
        {"file_name": "env_example_review.md", "kind": "markdown", "required_fields": [".env.example_status", "real_values_present", "reviewer"]},
    ],
    "LIVE-GAP-005": [
        {"file_name": "production_runner_decision.md", "kind": "markdown", "required_fields": ["runner_mode", "order_source_count", "blocked_runner_files", "approver"]},
        {"file_name": "runner_source_audit.csv", "kind": "csv", "headers": ["runner_path", "allowed", "reason", "reviewed_by", "reviewed_at"]},
    ],
    "LIVE-GAP-006": [
        {"file_name": "live_risk_policy.json", "kind": "json", "required_fields": ["max_daily_loss", "max_drawdown", "max_orders", "max_spread_points", "margin_guard_pct", "min_lot", "max_lot", "balance_cap"]},
        {"file_name": "risk_policy_manual_confirmation.md", "kind": "markdown", "required_fields": ["account_size", "leverage", "operator", "confirmed_at"]},
    ],
    "LIVE-GAP-007": [
        {"file_name": "emergency_runbook.md", "kind": "markdown", "required_fields": ["disable_auto_trading_steps", "close_position_steps", "rollback_steps", "owner", "backup_owner"]},
        {"file_name": "emergency_rehearsal_report.csv", "kind": "csv", "headers": ["rehearsal_id", "environment", "action", "status", "evidence_path", "reviewed_at"]},
    ],
    "LIVE-GAP-008": [
        {"file_name": "live_monitoring_policy.json", "kind": "json", "required_fields": ["order_alert", "position_alert", "pnl_alert", "margin_alert", "disconnect_alert", "stale_tick_alert", "ledger_mismatch_alert"]},
        {"file_name": "reconciliation_checklist.csv", "kind": "csv", "headers": ["check_id", "frequency", "source_a", "source_b", "owner", "fail_closed_action"]},
    ],
    "LIVE-GAP-009": [
        {"file_name": "live_account_spec_snapshot.json", "kind": "json", "required_fields": ["account_alias", "account_type", "leverage", "balance_cap", "allowed_symbol", "captured_at"]},
        {"file_name": "broker_symbol_spec.csv", "kind": "csv", "headers": ["symbol", "contract_size", "min_lot", "lot_step", "margin_initial", "digits", "spread_policy"]},
    ],
    "LIVE-GAP-010": [
        {"file_name": "nonprod_order_rehearsal_report.md", "kind": "markdown", "required_fields": ["environment", "rehearsal_id", "open_order_status", "close_order_status", "sl_tp_status", "emergency_status", "reviewer"]},
        {"file_name": "rehearsal_ledger.csv", "kind": "csv", "headers": ["event_time", "event_type", "symbol", "lots", "price", "reason", "status"]},
        {"file_name": "rehearsal_alert_log.csv", "kind": "csv", "headers": ["event_time", "alert_type", "channel", "status", "owner"]},
    ],
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


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def markdown_template(gap: Dict[str, str], spec: Dict[str, object]) -> str:
    fields = spec.get("required_fields", [])
    lines = [
        f"# {gap['gap_id']} Evidence Template",
        "",
        f"- gate_item: `{gap['gate_item']}`",
        f"- priority: `{gap['priority']}`",
        f"- severity: `{gap['severity']}`",
        "- template_status: `template_only`",
        "- gate_status: `open`",
        "- contains_real_credentials: `false`",
        "",
        "## Required Fields",
        "",
    ]
    for field in fields:
        lines.append(f"- `{field}`: `TEMPLATE_PLACEHOLDER`")
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            "TEMPLATE_PLACEHOLDER",
            "",
            "## Manual Confirmation",
            "",
            f"{gap['manual_confirmation']}",
            "",
            "## Fail Closed",
            "",
            f"{gap['fail_closed_action']}",
            "",
        ]
    )
    return "\n".join(lines)


def json_template(gap: Dict[str, str], spec: Dict[str, object]) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "gap_id": gap["gap_id"],
        "gate_item": gap["gate_item"],
        "template_status": "template_only",
        "gate_status": "open",
        "ready_to_live_trade": False,
        "contains_real_credentials": False,
        "fields": {},
        "manual_confirmation": gap["manual_confirmation"],
        "fail_closed_action": gap["fail_closed_action"],
    }
    fields = {}
    for field in spec.get("required_fields", []):
        fields[str(field)] = "TEMPLATE_PLACEHOLDER"
    payload["fields"] = fields
    return payload


def csv_template(path: Path, headers: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerow({header: "TEMPLATE_PLACEHOLDER" for header in headers})


def write_template_file(gap: Dict[str, str], spec: Dict[str, object], path: Path) -> None:
    kind = str(spec["kind"])
    if kind == "markdown":
        path.write_text(markdown_template(gap, spec), encoding="utf-8-sig")
    elif kind == "json":
        write_json(path, json_template(gap, spec))
    elif kind == "csv":
        csv_template(path, [str(item) for item in spec.get("headers", [])])
    else:
        raise ValueError(f"unsupported template kind: {kind}")


def build_report(decision: Dict[str, object], index_rows: List[Dict[str, object]]) -> str:
    lines = [
        "# Live Gate Evidence Templates",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- evidence_template_count: `{decision['evidence_template_count']}`",
        f"- gate_count: `{decision['gate_count']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        f"- all_gate_status: `{decision['all_gate_status']}`",
        "",
        "## Boundary",
        "",
        "- These are blank evidence templates only.",
        "- They do not contain real credentials.",
        "- They do not close any live gate.",
        "- They do not authorize `InpSimMode=false`.",
        "",
        "## Templates",
        "",
    ]
    for row in index_rows:
        lines.append(f"- `{row['gap_id']}`: `{row['file_name']}` ({row['file_kind']})")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

    checklist = read_rows(CHECKLIST)
    manual_rows = read_rows(MANUAL_TEMPLATE)
    manual_by_gap = {row["gap_id"]: row for row in manual_rows}

    index_rows: List[Dict[str, object]] = []
    schema_rows: List[Dict[str, object]] = []
    for gap in checklist:
        gap_id = gap["gap_id"]
        gap_dir = TEMPLATE_DIR / gap_id
        gap_dir.mkdir(parents=True, exist_ok=True)
        specs = TEMPLATE_SPECS[gap_id]
        for spec in specs:
            file_name = str(spec["file_name"])
            path = gap_dir / file_name
            write_template_file(gap, spec, path)
            index_rows.append(
                {
                    "gap_id": gap_id,
                    "priority": gap["priority"],
                    "category": gap["category"],
                    "severity": gap["severity"],
                    "file_name": file_name,
                    "file_kind": spec["kind"],
                    "relative_path": str(path.relative_to(OUT_DIR)),
                    "template_status": "template_only",
                    "gate_status": "open",
                    "contains_real_credentials": False,
                    "manual_confirmation_id": manual_by_gap.get(gap_id, {}).get("confirmation_id", ""),
                }
            )
            schema_rows.append(
                {
                    "gap_id": gap_id,
                    "file_name": file_name,
                    "file_kind": spec["kind"],
                    "required_fields": ";".join(str(item) for item in spec.get("required_fields", spec.get("headers", []))),
                    "ready_to_live_trade_default": False,
                    "gate_status_default": "open",
                }
            )

    write_csv(
        OUT_DIR / "live_gate_evidence_index.csv",
        index_rows,
        [
            "gap_id",
            "priority",
            "category",
            "severity",
            "file_name",
            "file_kind",
            "relative_path",
            "template_status",
            "gate_status",
            "contains_real_credentials",
            "manual_confirmation_id",
        ],
    )
    write_csv(
        OUT_DIR / "live_gate_evidence_schema.csv",
        schema_rows,
        ["gap_id", "file_name", "file_kind", "required_fields", "ready_to_live_trade_default", "gate_status_default"],
    )
    write_json(
        OUT_DIR / "live_gate_evidence_schema.json",
        {
            "schema_version": 1,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "gate_count": len(checklist),
            "template_count": len(index_rows),
            "templates": schema_rows,
        },
    )
    decision = {
        "decision_time": datetime.now().isoformat(timespec="seconds"),
        "check_id": "stage_state_live_gate_evidence_templates",
        "status": "templates_generated",
        "gate_count": len(checklist),
        "evidence_template_count": len(index_rows),
        "ready_to_live_trade": False,
        "all_gate_status": "open",
        "contains_real_credentials": False,
        "recommended_next_action": "run_evidence_template_review_default_open",
    }
    write_json(OUT_DIR / "live_gate_evidence_templates_decision.json", decision)
    write_csv(OUT_DIR / "live_gate_evidence_templates_decision.csv", [decision], list(decision.keys()))
    (OUT_DIR / "live_gate_evidence_templates.md").write_text(build_report(decision, index_rows), encoding="utf-8-sig")

    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
