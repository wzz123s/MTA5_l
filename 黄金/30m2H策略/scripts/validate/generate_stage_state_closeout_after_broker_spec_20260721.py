from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
PENDING_PLAN = VALIDATION_DIR / "stage_state_pending_auto_evidence_prerequisite_plan_20260721" / "pending_auto_evidence_prerequisite_plan.csv"
BROKER_REVIEW = VALIDATION_DIR / "stage_state_broker_symbol_spec_read_only_review_20260721" / "broker_symbol_spec_read_only_review_decision.json"
OUT_DIR = VALIDATION_DIR / "stage_state_closeout_after_broker_spec_20260721"


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
    pending_rows = read_rows(PENDING_PLAN)
    broker_review = read_json(BROKER_REVIEW)
    collected_file = "broker_symbol_spec.csv" if broker_review.get("status") == "pass_broker_symbol_spec_read_only_live_blocked" else ""
    remaining_rows = [row for row in pending_rows if row.get("file_name") != collected_file]
    decision = {
        "decision_time": generated_at,
        "check_id": "stage_state_closeout_after_broker_spec",
        "status": "closeout_updated_after_broker_spec_live_blocked",
        "broker_symbol_spec_collected": collected_file == "broker_symbol_spec.csv",
        "pending_auto_items_before": len(pending_rows),
        "pending_auto_items_remaining": len(remaining_rows),
        "remaining_pending_auto_files": ";".join(row["file_name"] for row in remaining_rows),
        "live_trade_blocked": True,
        "ready_to_live_trade": False,
        "runner_executed": False,
        "orders_placed": False,
        "live_set_switched": False,
        "recommended_next_action": "collect_live_package_hashes_and_parsed_live_set_only_after_real_approvals",
    }
    write_csv(OUT_DIR / "closeout_after_broker_spec_remaining_pending.csv", remaining_rows, list(pending_rows[0].keys()) if pending_rows else [])
    write_csv(OUT_DIR / "closeout_after_broker_spec_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "closeout_after_broker_spec_decision.json", decision)
    lines = [
        "# Closeout After Broker Symbol Spec",
        "",
        f"- status: `{decision['status']}`",
        f"- broker_symbol_spec_collected: `{decision['broker_symbol_spec_collected']}`",
        f"- pending_auto_items_before: `{decision['pending_auto_items_before']}`",
        f"- pending_auto_items_remaining: `{decision['pending_auto_items_remaining']}`",
        f"- remaining_pending_auto_files: `{decision['remaining_pending_auto_files']}`",
        "- live_trade_blocked: `True`",
        "- ready_to_live_trade: `False`",
        "",
        "## Remaining Pending Auto Evidence",
        "",
    ]
    for row in remaining_rows:
        lines.append(f"- `{row['file_name']}`: {row['manual_prerequisite']}")
    lines.append("")
    (OUT_DIR / "closeout_after_broker_spec.md").write_text("\n".join(lines), encoding="utf-8-sig")
    for key, value in decision.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
