from __future__ import annotations


import csv
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(r"F:\use_code\MTA5_l")
VALIDATION_DIR = ROOT / "黄金" / "30m2H策略" / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_post_smoke_decision_gate_20260718"

RUN_PACKAGE_DIR = VALIDATION_DIR / "stage_state_final_regression_run_package_check_20260718"
LIVE_SIM_DIR = VALIDATION_DIR / "stage_state_live_sim_run_gate_20260718"
SMOKE_PACKAGE_DIR = VALIDATION_DIR / "stage_state_sim_dryrun_smoke_package_20260718"
SMOKE_EXECUTION_DIR = VALIDATION_DIR / "stage_state_sim_dryrun_smoke_execution_review_20260718"


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def first_row(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    rows = read_rows(path)
    return rows[0] if rows else {}


def add_check(
    rows: List[Dict[str, object]],
    check_id: str,
    passed: bool,
    actual: object,
    expected: object,
    severity: str = "blocker",
    note: str = "",
) -> None:
    rows.append(
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


def design_tasks() -> List[Dict[str, object]]:
    return [
        {
            "step_id": "runner_scope",
            "status": "pending",
            "owner": "implementation",
            "deliverable": "Define local sim runner scope: MT5 chart/EA signal-only runtime, not Python auto_trader.py and not live trade.",
            "acceptance": "Runner doc states InpSimMode=true, symbol/timeframe, startup/stop path, and evidence outputs.",
        },
        {
            "step_id": "credential_isolation",
            "status": "pending",
            "owner": "safety",
            "deliverable": "Externalize or quarantine hardcoded MT5 credentials from Python helper scripts before any continuous runner.",
            "acceptance": "No account/password literal is required by the runner path; secrets are not committed into strategy code.",
        },
        {
            "step_id": "runtime_risk_controls",
            "status": "pending",
            "owner": "risk",
            "deliverable": "Define sim/live independent guard rails: max daily loss, max session loss, max positions, kill switch, allowed symbol/timeframe.",
            "acceptance": "Config exists and defaults keep live trade disabled.",
        },
        {
            "step_id": "monitoring_restart_alerts",
            "status": "pending",
            "owner": "ops",
            "deliverable": "Define heartbeat, log rotation, restart rule, and alert/report files for local MT5 runner.",
            "acceptance": "A failed heartbeat or missing export is detectable without manual log browsing.",
        },
        {
            "step_id": "forward_dryrun_verification",
            "status": "pending",
            "owner": "validation",
            "deliverable": "Run a short live-market forward dry-run with InpSimMode=true and verify logs/exports.",
            "acceptance": "Post-run review shows terminal active, CSV updates, no real order/deal rows, and no critical errors.",
        },
    ]


def write_md(decision: Dict[str, object], tasks: List[Dict[str, object]], checks: List[Dict[str, object]]) -> None:
    failed = [row for row in checks if row["severity"] == "blocker" and row["status"] == "fail"]
    lines = [
        "# Post-smoke Decision Gate",
        "",
        f"- Decision date: {decision['decision_date']}",
        f"- Status: `{decision['status']}`",
        f"- Ready to sim continuous runner design: `{decision['ready_to_sim_continuous_runner_design']}`",
        f"- Ready to sim continuous runner execution: `{decision['ready_to_sim_continuous_runner_execution']}`",
        f"- Ready to live trade: `{decision['ready_to_live_trade']}`",
        f"- Blocker failure count: `{decision['blocker_failure_count']}`",
        "",
        "## Decision",
        "",
        "- The frozen tester package, live/sim gate, smoke package, and smoke execution all passed their blocker checks.",
        "- The project may move into sim continuous runner design.",
        "- Continuous runner execution is not opened yet because credentials, runtime risk controls, monitoring, and forward dry-run verification are not designed.",
        "- Live trading remains blocked.",
        "",
        "## Required Next Tasks",
        "",
        "| step_id | deliverable | acceptance |",
        "|---|---|---|",
    ]
    for task in tasks:
        lines.append(f"| `{task['step_id']}` | {task['deliverable']} | {task['acceptance']} |")
    if failed:
        lines.extend(["", "## Failed Blockers", "", "| check_id | actual | expected |", "|---|---|---|"])
        for row in failed:
            lines.append(f"| `{row['check_id']}` | {row['actual']} | {row['expected']} |")
    lines.append("")
    (OUT_DIR / "post_smoke_decision_gate.md").write_text("\n".join(lines), encoding="utf-8-sig")
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    run_package = first_row(RUN_PACKAGE_DIR / "run_package_check_decision.csv")
    live_sim = first_row(LIVE_SIM_DIR / "live_sim_run_gate_decision.csv")
    smoke_package = first_row(SMOKE_PACKAGE_DIR / "sim_dryrun_smoke_package_decision.csv")
    smoke_execution = first_row(SMOKE_EXECUTION_DIR / "sim_dryrun_smoke_execution_decision.csv")

    checks: List[Dict[str, object]] = []
    add_check(checks, "frozen_run_package_ready", truthy(run_package.get("ready_to_frozen_tester_run")), run_package.get("ready_to_frozen_tester_run", "missing"), "True")
    add_check(checks, "live_sim_gate_ready_to_sim_dry_run", truthy(live_sim.get("ready_to_sim_dry_run")), live_sim.get("ready_to_sim_dry_run", "missing"), "True")
    add_check(checks, "live_sim_gate_not_live", not truthy(live_sim.get("ready_to_live_trade")), live_sim.get("ready_to_live_trade", "missing"), "False")
    add_check(checks, "smoke_package_ready", truthy(smoke_package.get("ready_to_execute_tester_smoke")), smoke_package.get("ready_to_execute_tester_smoke", "missing"), "True")
    add_check(checks, "smoke_execution_passed", truthy(smoke_execution.get("smoke_execution_passed")), smoke_execution.get("smoke_execution_passed", "missing"), "True")
    add_check(checks, "smoke_execution_no_blockers", str(smoke_execution.get("blocker_failure_count", "")) == "0", smoke_execution.get("blocker_failure_count", "missing"), "0")
    add_check(checks, "smoke_execution_not_live", not truthy(smoke_execution.get("ready_to_live_trade")), smoke_execution.get("ready_to_live_trade", "missing"), "False")
    add_check(checks, "sim_runner_execution_not_opened", True, "not_opened_by_design", "not_opened_until_design_tasks_done")
    add_check(checks, "live_trade_not_opened", True, "blocked_by_design", "blocked")

    blocker_failures = [row for row in checks if row["severity"] == "blocker" and row["status"] == "fail"]
    ready_design = len(blocker_failures) == 0
    tasks = design_tasks()
    decision = {
        "decision_date": date.today().isoformat(),
        "check_id": "stage_state_post_smoke_decision_gate",
        "status": "pass" if ready_design else "fail",
        "pass": ready_design,
        "ready_to_sim_continuous_runner_design": ready_design,
        "ready_to_sim_continuous_runner_execution": False,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "required_design_task_count": len(tasks),
        "reason": "post_smoke_all_blockers_passed_design_gate_opened" if ready_design else "post_smoke_has_blockers",
        "next_action": "build_sim_continuous_runner_design_package" if ready_design else "fix_post_smoke_gate_blockers",
        "no_ea_or_python_strategy_logic_changes_in_this_step": True,
    }

    write_md(decision, tasks, checks)
    write_csv(
        OUT_DIR / "post_smoke_decision_gate_decision.csv",
        [decision],
        [
            "decision_date",
            "check_id",
            "status",
            "pass",
            "ready_to_sim_continuous_runner_design",
            "ready_to_sim_continuous_runner_execution",
            "ready_to_live_trade",
            "blocker_failure_count",
            "required_design_task_count",
            "reason",
            "next_action",
            "no_ea_or_python_strategy_logic_changes_in_this_step",
        ],
    )
    write_csv(
        OUT_DIR / "post_smoke_decision_gate_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(
        OUT_DIR / "sim_continuous_runner_required_tasks.csv",
        tasks,
        ["step_id", "status", "owner", "deliverable", "acceptance"],
    )

    print(f"status={decision['status']}")
    print(f"ready_to_sim_continuous_runner_design={decision['ready_to_sim_continuous_runner_design']}")
    print(f"ready_to_sim_continuous_runner_execution={decision['ready_to_sim_continuous_runner_execution']}")
    print(f"ready_to_live_trade={decision['ready_to_live_trade']}")
    print(f"blocker_failure_count={decision['blocker_failure_count']}")
    print(f"required_design_task_count={decision['required_design_task_count']}")
    print(f"output_dir={OUT_DIR}")


if __name__ == "__main__":
    main()
