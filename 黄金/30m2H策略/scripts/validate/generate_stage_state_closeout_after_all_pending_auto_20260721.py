from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_closeout_after_all_pending_auto_20260721"

BROKER_REVIEW = VALIDATION_DIR / "stage_state_broker_symbol_spec_read_only_review_20260721" / "broker_symbol_spec_read_only_review_decision.json"
OFFLINE_REVIEW = VALIDATION_DIR / "stage_state_live_package_hashes_and_set_parse_offline_review_20260721" / "live_package_hashes_and_set_parse_offline_review_decision.json"


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
    broker = read_json(BROKER_REVIEW)
    offline = read_json(OFFLINE_REVIEW)
    all_pending_auto_collected = (
        broker.get("status") == "pass_broker_symbol_spec_read_only_live_blocked"
        and offline.get("status") == "pass_live_package_hashes_and_set_parse_offline_live_blocked"
    )
    evidence_rows: List[Dict[str, object]] = [
        {
            "file_name": "broker_symbol_spec.csv",
            "status": broker.get("status", ""),
            "collected": broker.get("status") == "pass_broker_symbol_spec_read_only_live_blocked",
            "ready_to_live_trade": False,
            "generated_at": generated_at,
        },
        {
            "file_name": "live_package_hashes.csv",
            "status": offline.get("status", ""),
            "collected": offline.get("status") == "pass_live_package_hashes_and_set_parse_offline_live_blocked",
            "ready_to_live_trade": False,
            "generated_at": generated_at,
        },
        {
            "file_name": "parsed_live_set_template.json",
            "status": offline.get("status", ""),
            "collected": offline.get("status") == "pass_live_package_hashes_and_set_parse_offline_live_blocked",
            "ready_to_live_trade": False,
            "generated_at": generated_at,
        },
    ]
    decision = {
        "decision_time": generated_at,
        "check_id": "stage_state_closeout_after_all_pending_auto",
        "status": "all_pending_auto_collected_live_still_blocked" if all_pending_auto_collected else "pending_auto_still_incomplete",
        "all_pending_auto_collected": all_pending_auto_collected,
        "pending_auto_items_remaining": 0 if all_pending_auto_collected else "",
        "live_trade_blocked": True,
        "ready_to_live_trade": False,
        "runner_executed": False,
        "orders_placed": False,
        "live_set_switched": False,
        "recommended_next_action": "run_final_live_gate_review_only_after_real_manual_evidence_package_is_complete",
    }
    write_csv(OUT_DIR / "closeout_after_all_pending_auto_evidence_matrix.csv", evidence_rows, ["file_name", "status", "collected", "ready_to_live_trade", "generated_at"])
    write_csv(OUT_DIR / "closeout_after_all_pending_auto_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "closeout_after_all_pending_auto_decision.json", decision)
    lines = [
        "# Closeout After All Pending Auto Evidence",
        "",
        f"- status: `{decision['status']}`",
        f"- all_pending_auto_collected: `{decision['all_pending_auto_collected']}`",
        f"- pending_auto_items_remaining: `{decision['pending_auto_items_remaining']}`",
        "- live_trade_blocked: `True`",
        "- ready_to_live_trade: `False`",
        "",
        "## Important Boundary",
        "",
        "- Pending auto evidence is now collected/reviewed, but real manual approval evidence and final live gate review still decide live readiness.",
        "- This step does not allow live trading.",
        "",
    ]
    (OUT_DIR / "closeout_after_all_pending_auto.md").write_text("\n".join(lines), encoding="utf-8-sig")
    for key, value in decision.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
