from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_operator_approval_manual_form_20260723"

APPROVAL_TEMPLATE_JSON = (
    VALIDATION_DIR
    / "stage_state_final_live_approval_package_draft_20260723"
    / "final_live_operator_approval_template.json"
)
SIGNOFF_REQUIREMENTS_CSV = (
    VALIDATION_DIR
    / "stage_state_final_live_approval_package_draft_20260723"
    / "final_live_signoff_requirements.csv"
)
FINAL_REVIEW_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_final_live_gate_review_from_operator_approval_20260723"
    / "final_live_gate_review_decision.json"
)


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


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


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().isoformat(timespec="seconds")

    approval = read_json(APPROVAL_TEMPLATE_JSON)
    signoffs = read_rows(SIGNOFF_REQUIREMENTS_CSV)
    final_review = read_json(FINAL_REVIEW_DECISION_JSON)

    approval_items = approval.get("approval_items", {})
    if not isinstance(approval_items, dict):
        approval_items = {}

    approval_rows: List[Dict[str, object]] = []
    for idx, (key, value) in enumerate(approval_items.items(), start=1):
        approval_rows.append(
            {
                "item_no": idx,
                "approval_key": key,
                "current_value": value,
                "required_value_for_next_gate": True,
                "human_confirmation_required": True,
                "note": "Only set true after the operator genuinely approves this non-secret item.",
            }
        )

    operator_alias_ready = str(approval.get("operator_alias", "")).strip() not in {"", "manual_pending"}
    signed_count = sum(1 for row in approval_rows if str(row["current_value"]).lower() == "true")
    all_approvals_signed = signed_count == len(approval_rows) and len(approval_rows) > 0
    latest_final_gate_status = final_review.get("status", "")
    if operator_alias_ready and all_approvals_signed and latest_final_gate_status == (
        "final_live_gate_approval_preconditions_satisfied_loading_package_pending"
    ):
        status = "operator_approval_confirmed_final_gate_loading_package_pending"
        recommended_next_action = "prepare_exact_mt5_ea_live_loading_package_keep_stop_flags_until_explicit_approval"
    elif operator_alias_ready and all_approvals_signed:
        status = "operator_approval_confirmed_ready_for_final_live_gate_review"
        recommended_next_action = "rerun_final_live_gate_review"
    else:
        status = "operator_approval_manual_form_ready_waiting_for_human_confirmation"
        recommended_next_action = (
            "operator_supplies_non_secret_alias_and_approval_values_then_rerun_final_live_gate_review"
        )
    decision = {
        "decision_time": generated_at,
        "check_id": "stage_state_operator_approval_manual_form",
        "status": status,
        "operator_alias": approval.get("operator_alias", "manual_pending"),
        "operator_alias_ready": operator_alias_ready,
        "approval_boolean_count": len(approval_rows),
        "signed_approval_boolean_count": signed_count,
        "required_signoff_count": len(signoffs),
        "latest_final_gate_status": latest_final_gate_status,
        "ready_to_live_trade": False,
        "recommended_next_action": recommended_next_action,
    }

    write_csv(
        OUT_DIR / "operator_approval_items.csv",
        approval_rows,
        [
            "item_no",
            "approval_key",
            "current_value",
            "required_value_for_next_gate",
            "human_confirmation_required",
            "note",
        ],
    )
    write_csv(
        OUT_DIR / "operator_approval_signoff_requirements.csv",
        signoffs,
        ["signoff_id", "gap_id", "required_action", "minimum_evidence", "current_status", "blocks_live"],
    )
    write_csv(
        OUT_DIR / "operator_approval_manual_form_decision.csv",
        [decision],
        list(decision.keys()),
    )
    write_json(OUT_DIR / "operator_approval_manual_form_decision.json", decision)

    approval_lines = "\n".join(
        f"- [ ] `{row['approval_key']}`: 当前 `{row['current_value']}`，批准后应为 `true`"
        for row in approval_rows
    )
    signoff_lines = "\n".join(
        f"- `{row['signoff_id']}` / `{row['gap_id']}`: {row['required_action']}；最低证据：{row['minimum_evidence']}"
        for row in signoffs
    )

    response_template = {
        "operator_alias": "填一个非秘密别名，例如 owner_local",
        "approve_all_10_boolean_items": False,
        "or_approval_items": {key: False for key in approval_items},
        "do_not_include": approval.get("do_not_include", []),
    }
    write_json(OUT_DIR / "operator_approval_response_template.json", response_template)

    report = f"""# Operator Approval Manual Form

Generated: {generated_at}

## Current Gate State

- Latest final gate status: `{final_review.get("status", "")}`
- Operator alias ready: `{operator_alias_ready}`
- Approval booleans: `{signed_count} / {len(approval_rows)}`
- Ready to live trade: `false`

## How To Use

This form is only for non-secret operator approval. Do not write full account numbers, passwords, investor passwords, API tokens, or secret keys.

The next gate can only be rerun after:

1. `operator_alias` is changed from `manual_pending` to a non-secret alias.
2. Each genuinely approved item below is set to `true`.
3. The final live gate review is rerun.

## Approval Items

{approval_lines}

## Signoff Requirements

{signoff_lines}

## Safe Reply Shape

You can reply with a short non-secret confirmation, for example:

```text
operator_alias: owner_local
批准以上 10 个 approval boolean，继续 rerun final live gate review。
```

This does not authorize removing stop flags or loading the EA. Those remain separate steps after the gate review.
"""
    (OUT_DIR / "operator_approval_manual_form.md").write_text(report, encoding="utf-8-sig")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
