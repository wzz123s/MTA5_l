from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_final_closeout_report_20260721"

SIM_DECISION = VALIDATION_DIR / "stage_state_sim_only_post_observation_readiness_gate_20260720" / "sim_only_post_observation_readiness_decision.json"
LIVE_GAP_DECISION = VALIDATION_DIR / "stage_state_live_trade_readiness_gap_audit_20260720" / "live_trade_readiness_gap_decision.json"
AUTO_SAFE_DECISION = VALIDATION_DIR / "stage_state_live_gate_auto_safe_evidence_review_20260721" / "auto_safe_evidence_review_decision.json"
PENDING_AUTO_DECISION = VALIDATION_DIR / "stage_state_pending_auto_evidence_prerequisite_plan_review_20260721" / "pending_auto_evidence_prerequisite_review_decision.json"
PENDING_AUTO_PLAN = VALIDATION_DIR / "stage_state_pending_auto_evidence_prerequisite_plan_20260721" / "pending_auto_evidence_prerequisite_plan.csv"
MANUAL_PREREQ_DECISION = VALIDATION_DIR / "stage_state_manual_evidence_prerequisite_plan_review_20260721" / "manual_evidence_prerequisite_plan_review_decision.json"
P0_MANUAL_DECISION = VALIDATION_DIR / "stage_state_p0_manual_template_fill_dry_run_review_20260721" / "p0_manual_template_fill_dry_run_review_decision.json"
P0_REHEARSAL_DECISION = VALIDATION_DIR / "stage_state_p0_rehearsal_prerequisite_dry_run_review_20260721" / "p0_rehearsal_prerequisite_dry_run_review_decision.json"
P1_MANUAL_DECISION = VALIDATION_DIR / "stage_state_p1_manual_template_fill_dry_run_review_20260721" / "p1_manual_template_fill_dry_run_review_decision.json"
P1_REHEARSAL_DECISION = VALIDATION_DIR / "stage_state_p1_rehearsal_prerequisite_dry_run_review_20260721" / "p1_rehearsal_prerequisite_dry_run_review_decision.json"


def read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def build_status_rows() -> List[Dict[str, object]]:
    decisions = [
        ("SIM_ONLY post-observation", SIM_DECISION, "sim_only_complete"),
        ("Live-trade gap audit", LIVE_GAP_DECISION, "live_blocked"),
        ("Manual prerequisite plan", MANUAL_PREREQ_DECISION, "dry_run_complete"),
        ("P0 manual dry-run", P0_MANUAL_DECISION, "dry_run_complete"),
        ("P0 rehearsal dry-run", P0_REHEARSAL_DECISION, "dry_run_complete"),
        ("P1 manual dry-run", P1_MANUAL_DECISION, "dry_run_complete"),
        ("P1 rehearsal dry-run", P1_REHEARSAL_DECISION, "dry_run_complete"),
        ("Auto-safe evidence review", AUTO_SAFE_DECISION, "partial_auto_collected"),
        ("Pending auto prerequisites", PENDING_AUTO_DECISION, "prerequisites_drafted"),
    ]
    rows: List[Dict[str, object]] = []
    for label, path, closeout_state in decisions:
        decision = read_json(path)
        rows.append(
            {
                "area": label,
                "closeout_state": closeout_state,
                "status": decision.get("status", ""),
                "ready_to_live_trade": decision.get("ready_to_live_trade", False),
                "blocker_failure_count": decision.get("blocker_failure_count", ""),
                "review_completed": decision.get("review_completed", decision.get("audit_completed", "")),
                "source_decision": str(path.relative_to(ROOT)),
            }
        )
    return rows


def build_shortest_path_rows(pending_rows: List[Dict[str, str]], generated_at: str) -> List[Dict[str, object]]:
    return [
        {
            "sequence": 1,
            "step": "Human approval pack",
            "owner": "user / release reviewer / operator",
            "required_action": "Replace dry-run placeholders with reviewed manual approvals and redacted real evidence where appropriate.",
            "remaining_blocker": "No real approval package exists yet.",
            "live_action_allowed": False,
            "ready_to_live_trade": False,
            "generated_at": generated_at,
        },
        {
            "sequence": 2,
            "step": "Collect pending auto evidence after approval",
            "owner": "release reviewer / operator",
            "required_action": "Collect live_package_hashes.csv, parsed_live_set_template.json, and broker_symbol_spec.csv only after their approval phrases are provided.",
            "remaining_blocker": "; ".join(row["file_name"] for row in pending_rows),
            "live_action_allowed": False,
            "ready_to_live_trade": False,
            "generated_at": generated_at,
        },
        {
            "sequence": 3,
            "step": "Final live gate review",
            "owner": "user / reviewer",
            "required_action": "Run final gate review over all real evidence; only then decide whether any live start is allowed.",
            "remaining_blocker": "All 10 live gates must close together; SIM_ONLY result cannot approve live trading.",
            "live_action_allowed": False,
            "ready_to_live_trade": False,
            "generated_at": generated_at,
        },
    ]


def build_report(decision: Dict[str, object], status_rows: List[Dict[str, object]], pending_rows: List[Dict[str, str]], shortest_path_rows: List[Dict[str, object]]) -> str:
    lines = [
        "# Final Strategy Closeout Report",
        "",
        "## Current State",
        "",
        "- Python/EA alignment and SIM_ONLY execution path have enough evidence to continue bounded simulation monitoring.",
        "- SIM_ONLY post-observation gate passed; this means simulation monitoring can continue, not that live trading is approved.",
        "- Live trading remains blocked because approval, live package, live set, broker/spec, risk, monitoring, rehearsal, and final gate evidence are still not real closed evidence.",
        "- No runner execution, MT5 order action, live set switch, or real credential output is approved by this closeout.",
        "",
        "## What Can Run",
        "",
        "- Bounded SIM_ONLY monitoring can run using the already prepared SIM_ONLY runner path.",
        "- Dry-run evidence generation and static reviews can run.",
        "",
        "## What Cannot Run",
        "",
        "- `auto_trade/auto_trader.py` cannot run as a live runner.",
        "- `InpSimMode=false` cannot be used.",
        "- Real-money orders, live chart attachment, active live set loading, and live package deployment cannot proceed.",
        "",
        "## Pending Auto Evidence",
        "",
    ]
    for row in pending_rows:
        lines.append(
            f"- `{row['file_name']}`: approval phrase `{row['approval_phrase_required']}`; "
            f"allowed only as `{row['collection_class']}`."
        )
    lines.extend(["", "## Shortest Path Before Any Live Discussion", ""])
    for row in shortest_path_rows:
        lines.append(f"{row['sequence']}. {row['step']}: {row['required_action']}")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- status: `{decision['status']}`",
            f"- sim_only_complete: `{decision['sim_only_complete']}`",
            f"- live_trade_blocked: `{decision['live_trade_blocked']}`",
            f"- dry_run_closeout_complete: `{decision['dry_run_closeout_complete']}`",
            f"- pending_auto_items: `{decision['pending_auto_items']}`",
            f"- shortest_path_steps_before_live_discussion: `{decision['shortest_path_steps_before_live_discussion']}`",
            f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().isoformat(timespec="seconds")
    status_rows = build_status_rows()
    pending_rows = read_rows(PENDING_AUTO_PLAN)
    shortest_path_rows = build_shortest_path_rows(pending_rows, generated_at)
    decision = {
        "decision_time": generated_at,
        "check_id": "stage_state_final_closeout_report",
        "status": "final_closeout_report_generated_live_blocked",
        "sim_only_complete": True,
        "bounded_sim_only_monitoring_optional": True,
        "dry_run_closeout_complete": True,
        "pending_auto_items": len(pending_rows),
        "shortest_path_steps_before_live_discussion": len(shortest_path_rows),
        "live_trade_blocked": True,
        "ready_to_live_trade": False,
        "runner_executed": False,
        "mt5_accessed_by_closeout": False,
        "orders_placed": False,
        "live_set_switched": False,
        "recommended_next_action": "stop_expanding_dry_run_work_and_wait_for_user_real_approval_inputs",
    }
    write_csv(OUT_DIR / "final_closeout_status_matrix.csv", status_rows, ["area", "closeout_state", "status", "ready_to_live_trade", "blocker_failure_count", "review_completed", "source_decision"])
    write_csv(OUT_DIR / "final_closeout_shortest_path.csv", shortest_path_rows, ["sequence", "step", "owner", "required_action", "remaining_blocker", "live_action_allowed", "ready_to_live_trade", "generated_at"])
    write_csv(OUT_DIR / "final_closeout_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "final_closeout_decision.json", decision)
    (OUT_DIR / "final_closeout_report.md").write_text(build_report(decision, status_rows, pending_rows, shortest_path_rows), encoding="utf-8-sig")
    for key, value in decision.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
