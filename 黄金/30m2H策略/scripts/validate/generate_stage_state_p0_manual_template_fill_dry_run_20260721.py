from __future__ import annotations


import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
PREREQ_DIR = VALIDATION_DIR / "stage_state_manual_evidence_prerequisite_plan_20260721"
TEMPLATE_DIR = VALIDATION_DIR / "stage_state_live_gate_evidence_templates_20260721"
OUT_DIR = VALIDATION_DIR / "stage_state_p0_manual_template_fill_dry_run_20260721"
DRY_RUN_ROOT = OUT_DIR / "evidence_dry_run"

PREREQ_PLAN = PREREQ_DIR / "manual_evidence_prerequisite_plan.csv"
EVIDENCE_INDEX = TEMPLATE_DIR / "live_gate_evidence_index.csv"


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


def split_fields(value: str) -> List[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def field_token(field_name: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]+", "_", field_name).strip("_").upper()
    return token or "FIELD"


def placeholder(field_name: str, contains_secret_risk: bool) -> str:
    prefix = "REDACTED" if contains_secret_risk else "PENDING"
    return f"{prefix}_{field_token(field_name)}"


def index_by_key(index_rows: List[Dict[str, str]]) -> Dict[Tuple[str, str], Dict[str, str]]:
    return {(row.get("gap_id", ""), row.get("file_name", "")): row for row in index_rows}


def p0_manual_rows(prereq_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [
        row
        for row in prereq_rows
        if row.get("priority") == "P0"
        and row.get("collection_method") == "manual"
        and row.get("completion_state") == "open_prerequisite"
    ]


def relative_to_root(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def build_markdown(row: Dict[str, str], fields: List[str], generated_at: str) -> str:
    secret_risk = boolish(row.get("contains_secret_risk"))
    lines = [
        f"# {row['gap_id']} P0 Manual Evidence Dry Run",
        "",
        "- dry_run_status: `redacted_placeholder_only`",
        "- priority: `P0`",
        f"- source_file: `{row['file_name']}`",
        f"- gate_status: `{row.get('gate_status', 'open') or 'open'}`",
        "- ready_to_live_trade: `false`",
        "- contains_real_credentials: `false`",
        f"- generated_at: `{generated_at}`",
        "",
        "## Required Fields",
        "",
    ]
    for field in fields:
        lines.append(f"- `{field}`: `{placeholder(field, secret_risk)}`")
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            "PENDING_MANUAL_EVIDENCE_REDACTED_DRY_RUN_ONLY",
            "",
            "## Confirmation Boundary",
            "",
            f"- confirmer: `{row.get('confirmer', '')}`",
            f"- prerequisite_source: `{row.get('prerequisite_source', '')}`",
            f"- next_allowed_action: `{row.get('next_allowed_action', '')}`",
            "",
            "## Forbidden Content",
            "",
            row.get("forbidden_content", "No production values or live actions."),
            "",
            "## Fail Closed",
            "",
            "Keep all live gates open and keep ready_to_live_trade=false.",
            "",
        ]
    )
    return "\n".join(lines)


def build_json(row: Dict[str, str], fields: List[str], generated_at: str) -> Dict[str, object]:
    secret_risk = boolish(row.get("contains_secret_risk"))
    return {
        "gap_id": row["gap_id"],
        "source_file": row["file_name"],
        "dry_run_status": "redacted_placeholder_only",
        "priority": "P0",
        "gate_status": "open",
        "ready_to_live_trade": False,
        "contains_real_credentials": False,
        "generated_at": generated_at,
        "fields": {field: placeholder(field, secret_risk) for field in fields},
        "confirmation_boundary": {
            "confirmer": row.get("confirmer", ""),
            "prerequisite_source": row.get("prerequisite_source", ""),
            "next_allowed_action": row.get("next_allowed_action", ""),
        },
        "forbidden_content": row.get("forbidden_content", ""),
        "fail_closed_action": "Keep all live gates open and keep ready_to_live_trade=false.",
    }


def write_dry_run_file(row: Dict[str, str], index_row: Dict[str, str], fields: List[str], generated_at: str) -> Tuple[Path, str]:
    gap_dir = DRY_RUN_ROOT / row["gap_id"]
    gap_dir.mkdir(parents=True, exist_ok=True)
    out_path = gap_dir / row["file_name"]
    file_kind = index_row.get("file_kind") or Path(row["file_name"]).suffix.lstrip(".")
    if file_kind == "json" or row["file_name"].endswith(".json"):
        write_json(out_path, build_json(row, fields, generated_at))
        return out_path, "json"
    out_path.write_text(build_markdown(row, fields, generated_at), encoding="utf-8-sig")
    return out_path, "markdown"


def build_report(decision: Dict[str, object], manifest_rows: List[Dict[str, object]]) -> str:
    lines = [
        "# P0 Manual Template Fill Dry Run",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- p0_manual_items: `{decision['p0_manual_items']}`",
        f"- dry_run_files_written: `{decision['dry_run_files_written']}`",
        f"- required_fields_total: `{decision['required_fields_total']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        "",
        "## Boundary",
        "",
        "- Generated files are redacted dry-run copies only.",
        "- Original evidence templates are not overwritten.",
        "- No real credentials, account secrets, runner execution, MT5 query, order action, or live set switch is performed.",
        "",
        "## Files",
        "",
    ]
    for row in manifest_rows:
        lines.append(
            f"- `{row['gap_id']}` `{row['file_name']}` -> `{row['dry_run_relative_path']}` "
            f"fields={row['required_field_count']}"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DRY_RUN_ROOT.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().isoformat(timespec="seconds")
    prereq_rows = read_rows(PREREQ_PLAN)
    index_rows = read_rows(EVIDENCE_INDEX)
    index_map = index_by_key(index_rows)
    target_rows = p0_manual_rows(prereq_rows)

    manifest_rows: List[Dict[str, object]] = []
    for row in target_rows:
        key = (row.get("gap_id", ""), row.get("file_name", ""))
        index_row = index_map.get(key, {})
        fields = split_fields(row.get("required_fields", ""))
        out_path, file_kind = write_dry_run_file(row, index_row, fields, generated_at)
        source_relative_path = index_row.get("relative_path", "")
        source_path = TEMPLATE_DIR / source_relative_path if source_relative_path else Path("")
        manifest_rows.append(
            {
                "gap_id": row.get("gap_id", ""),
                "file_name": row.get("file_name", ""),
                "file_kind": file_kind,
                "priority": row.get("priority", ""),
                "collection_method": row.get("collection_method", ""),
                "source_template_relative_path": source_relative_path,
                "source_template_exists": source_path.exists() if source_relative_path else False,
                "dry_run_relative_path": relative_to_root(out_path),
                "required_fields": row.get("required_fields", ""),
                "required_field_count": len(fields),
                "all_fields_placeholder_filled": True,
                "contains_secret_risk": row.get("contains_secret_risk", "False"),
                "live_action_risk": row.get("live_action_risk", "False"),
                "requires_user_approval": row.get("requires_user_approval", "False"),
                "original_template_overwritten": False,
                "gate_status": "open",
                "ready_to_live_trade": False,
                "generated_at": generated_at,
            }
        )

    decision = {
        "decision_time": generated_at,
        "check_id": "stage_state_p0_manual_template_fill_dry_run",
        "status": "p0_manual_dry_run_generated_live_blocked",
        "p0_manual_items": len(target_rows),
        "dry_run_files_written": len(manifest_rows),
        "required_fields_total": sum(int(row["required_field_count"]) for row in manifest_rows),
        "markdown_files": sum(1 for row in manifest_rows if row["file_kind"] == "markdown"),
        "json_files": sum(1 for row in manifest_rows if row["file_kind"] == "json"),
        "original_templates_overwritten": False,
        "credential_values_output": False,
        "runner_executed": False,
        "mt5_accessed": False,
        "live_set_switched": False,
        "gate_status": "open",
        "ready_to_live_trade": False,
        "recommended_next_action": "review_p0_manual_template_fill_dry_run",
    }

    fieldnames = [
        "gap_id",
        "file_name",
        "file_kind",
        "priority",
        "collection_method",
        "source_template_relative_path",
        "source_template_exists",
        "dry_run_relative_path",
        "required_fields",
        "required_field_count",
        "all_fields_placeholder_filled",
        "contains_secret_risk",
        "live_action_risk",
        "requires_user_approval",
        "original_template_overwritten",
        "gate_status",
        "ready_to_live_trade",
        "generated_at",
    ]
    write_csv(OUT_DIR / "p0_manual_template_fill_dry_run_manifest.csv", manifest_rows, fieldnames)
    write_csv(OUT_DIR / "p0_manual_template_fill_dry_run_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "p0_manual_template_fill_dry_run_decision.json", decision)
    (OUT_DIR / "p0_manual_template_fill_dry_run.md").write_text(build_report(decision, manifest_rows), encoding="utf-8-sig")

    for key, value in decision.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
