from __future__ import annotations


import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_live_trade_readiness_gap_audit_20260720"

SIM_READINESS_DIR = VALIDATION_DIR / "stage_state_sim_only_post_observation_readiness_gate_20260720"
SIM_READINESS_DECISION = SIM_READINESS_DIR / "sim_only_post_observation_readiness_decision.json"
SIM_READINESS_CHECKS = SIM_READINESS_DIR / "sim_only_post_observation_readiness_checks.csv"
OBSERVATION_DIR = VALIDATION_DIR / "stage_state_sim_continuous_runner_observation_window_20260720"
OBSERVATION_DECISION = OBSERVATION_DIR / "finite_runner_trial_decision.json"
OBSERVATION_CYCLES = OBSERVATION_DIR / "finite_runner_trial_cycles.csv"
SIM_CONFIG = VALIDATION_DIR / "stage_state_sim_only_chart_trial_package_20260719" / "sim_continuous_runner_config_20260720.json"

AUTO_TRADE = ROOT / "auto_trade"
SIM_ONLY_EX5 = AUTO_TRADE / "30m2H_Strategy_EA_SIM_ONLY.ex5"
SIM_ONLY_SET = AUTO_TRADE / "30m2H_Strategy_EA_SIM_ONLY.stage_state_sim_dryrun_20260719.set"
MAIN_EA_EX5 = AUTO_TRADE / "30m2H_Strategy_EA.ex5"
MAIN_EA_SET = AUTO_TRADE / "30m2H_Strategy_EA.stage_state_frozen_20260718.set"
AUTO_TRADER = AUTO_TRADE / "auto_trader.py"
VERIFY_CONNECTION = AUTO_TRADE / "verify_connection.py"
SIGNAL_VALIDATOR = AUTO_TRADE / "signal_validator.py"
STOP_FLAG = AUTO_TRADE / "RUNNER_STOP.flag"
TERMINAL_EXE = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")


def read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def int_value(value: object, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def parse_set(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith(";") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.split("||", 1)[0].strip()
    return values


def add_check(
    checks: List[Dict[str, object]],
    check_id: str,
    category: str,
    passed: bool,
    actual: object,
    expected: object,
    severity: str = "info",
    note: str = "",
) -> None:
    checks.append(
        {
            "check_id": check_id,
            "category": category,
            "status": "pass" if passed else "fail",
            "pass": passed,
            "actual": actual,
            "expected": expected,
            "severity": severity,
            "note": note,
        }
    )


def add_gap(
    gaps: List[Dict[str, object]],
    gap_id: str,
    category: str,
    requirement: str,
    current_state: str,
    severity: str,
    required_action: str,
) -> None:
    gaps.append(
        {
            "gap_id": gap_id,
            "category": category,
            "requirement": requirement,
            "current_state": current_state,
            "severity": severity,
            "required_action": required_action,
            "status": "open",
        }
    )


def file_contains_hardcoded_credential(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    password_pattern = re.compile(r"['\"]password['\"]\s*:\s*['\"][^'\"]+['\"]", re.IGNORECASE)
    account_pattern = re.compile(r"['\"]account['\"]\s*:\s*\d+", re.IGNORECASE)
    login_pattern = re.compile(r"\blogin\s*=\s*CONFIG\[['\"]account['\"]\]", re.IGNORECASE)
    return bool(password_pattern.search(text) and account_pattern.search(text) and login_pattern.search(text))


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


def all_rows_pass(rows: List[Dict[str, str]]) -> bool:
    return bool(rows) and all(row.get("status") == "pass" for row in rows)


def build_report(decision: Dict[str, object], gaps: List[Dict[str, object]]) -> str:
    lines = [
        "# Live Trade Readiness Gap Audit",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- audit_completed: `{decision['audit_completed']}`",
        f"- ready_to_continue_sim_only_monitoring: `{decision['ready_to_continue_sim_only_monitoring']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        f"- open_gap_count: `{decision['open_gap_count']}`",
        f"- critical_gap_count: `{decision['critical_gap_count']}`",
        f"- current_positions_count: `{decision['positions_count']}`",
        f"- current_orders_count: `{decision['orders_count']}`",
        "",
        "## Summary",
        "",
        "- SIM_ONLY monitoring is ready to continue.",
        "- Live trading is blocked by design in this audit.",
        "- The existing Python auto trader remains blocked and must not be used as the live runner.",
        "- A separate live package, live risk policy, credential policy, emergency handling, and manual approval are still required.",
        "",
        "## Open Gaps",
        "",
    ]
    for row in gaps:
        lines.append(
            f"- `{row['gap_id']}` [{row['severity']}] {row['requirement']} | current: {row['current_state']} | action: {row['required_action']}"
        )
    lines.extend(
        [
            "",
            "## Not Approved",
            "",
            "- Do not run `auto_trade/auto_trader.py`.",
            "- Do not set `InpSimMode=false`.",
            "- Do not enable live trading.",
            "- Do not treat SIM_ONLY observation pass as live approval.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    sim_readiness = read_json(SIM_READINESS_DECISION)
    sim_readiness_checks = read_rows(SIM_READINESS_CHECKS)
    observation = read_json(OBSERVATION_DECISION)
    observation_cycles = read_rows(OBSERVATION_CYCLES)
    sim_config = read_json(SIM_CONFIG)
    sim_set = parse_set(SIM_ONLY_SET)
    main_set = parse_set(MAIN_EA_SET)
    counts = mt5_counts()

    checks: List[Dict[str, object]] = []
    gaps: List[Dict[str, object]] = []

    add_check(checks, "sim_readiness_pass", "sim_only_evidence", sim_readiness.get("status") == "pass", sim_readiness.get("status"), "pass")
    add_check(checks, "sim_readiness_checks_pass", "sim_only_evidence", all_rows_pass(sim_readiness_checks), "all pass" if all_rows_pass(sim_readiness_checks) else "has failed checks", "all pass")
    add_check(checks, "observation_pass", "sim_only_evidence", observation.get("status") == "pass", observation.get("status"), "pass")
    add_check(checks, "observation_12_cycles", "sim_only_evidence", int_value(observation.get("cycles_completed")) == 12, observation.get("cycles_completed"), 12)
    add_check(checks, "observation_all_cycles_pass", "sim_only_evidence", all(row.get("status") == "pass" for row in observation_cycles), "all pass", "all pass")
    add_check(checks, "observation_ledger_zero", "sim_only_evidence", int_value(observation.get("last_trade_ledger_rows"), -1) == 0, observation.get("last_trade_ledger_rows"), 0)
    add_check(checks, "sim_only_ex5_exists", "artifact", SIM_ONLY_EX5.exists(), SIM_ONLY_EX5, "exists")
    add_check(checks, "sim_only_set_exists", "artifact", SIM_ONLY_SET.exists(), SIM_ONLY_SET, "exists")
    add_check(checks, "main_ea_ex5_exists", "artifact", MAIN_EA_EX5.exists(), MAIN_EA_EX5, "exists")
    add_check(checks, "main_frozen_set_exists", "artifact", MAIN_EA_SET.exists(), MAIN_EA_SET, "exists")
    add_check(checks, "sim_config_live_disabled", "current_safety_lock", sim_config.get("live_trade_enabled") is False, sim_config.get("live_trade_enabled"), False)
    add_check(checks, "sim_config_execution_disabled", "current_safety_lock", sim_config.get("execution_enabled") is False, sim_config.get("execution_enabled"), False)
    add_check(checks, "sim_only_lock_enabled", "current_safety_lock", sim_config.get("sim_only_lock") is True, sim_config.get("sim_only_lock"), True)
    add_check(checks, "sim_set_inp_sim_mode_true", "current_safety_lock", sim_set.get("InpSimMode") == "true", sim_set.get("InpSimMode", ""), "true")
    add_check(checks, "mt5_counts_available", "runtime", truthy(counts.get("ok")), counts.get("error") or counts.get("ok"), True)
    add_check(checks, "mt5_positions_zero_now", "runtime", counts.get("positions_count") == 0, counts.get("positions_count"), 0)
    add_check(checks, "mt5_orders_zero_now", "runtime", counts.get("orders_count") == 0, counts.get("orders_count"), 0)

    hardcoded_files = [
        str(path.relative_to(ROOT))
        for path in [AUTO_TRADER, VERIFY_CONNECTION, SIGNAL_VALIDATOR]
        if file_contains_hardcoded_credential(path)
    ]
    add_check(
        checks,
        "hardcoded_credential_files_detected",
        "credential",
        len(hardcoded_files) == 0,
        ";".join(hardcoded_files) if hardcoded_files else "",
        "no source files with hardcoded live credentials",
        "live_blocker",
        "File names only; values are intentionally not reported.",
    )

    add_gap(
        gaps,
        "LIVE-GAP-001",
        "approval",
        "Explicit human approval for live trading",
        "No live approval record; latest gates keep ready_to_live_trade=false",
        "critical",
        "Create a signed/dated approval gate before any live enablement.",
    )
    add_gap(
        gaps,
        "LIVE-GAP-002",
        "execution_package",
        "Separate live package with reviewed EX5, set file, hashes, and deployment path",
        "Current approved package is SIM_ONLY; live config is absent",
        "critical",
        "Build a live package audit that does not reuse SIM_ONLY approval as live approval.",
    )
    add_gap(
        gaps,
        "LIVE-GAP-003",
        "sim_mode",
        "Independent gate before `InpSimMode=false`",
        f"SIM_ONLY set has InpSimMode={sim_set.get('InpSimMode', '')}; main frozen set has InpSimMode={main_set.get('InpSimMode', '')}",
        "critical",
        "Require a dedicated live gate and manual confirmation before changing sim mode.",
    )
    add_gap(
        gaps,
        "LIVE-GAP-004",
        "credential",
        "Externalized credential and secret handling",
        f"Hardcoded credential pattern files detected: {len(hardcoded_files)}",
        "critical",
        "Move credentials out of source and verify no live runner prints or stores secrets.",
    )
    add_gap(
        gaps,
        "LIVE-GAP-005",
        "runner",
        "Approved production runner path",
        "Current approved runner is SIM_ONLY monitor; `auto_trade/auto_trader.py` remains blocked",
        "critical",
        "Define whether live execution is EA-only or a new audited runner; do not use stale Python runner.",
    )
    add_gap(
        gaps,
        "LIVE-GAP-006",
        "risk",
        "Live risk limits and account guardrails",
        "Current config sets max real positions/orders/loss to 0",
        "critical",
        "Define max daily loss, max drawdown, max orders, max spread, margin guard, and lot caps.",
    )
    add_gap(
        gaps,
        "LIVE-GAP-007",
        "emergency",
        "Emergency stop and rollback plan",
        "RUNNER_STOP.flag stops bounded monitor; it is not an emergency close-position mechanism",
        "critical",
        "Create and test an emergency close/disable procedure on a non-live environment.",
    )
    add_gap(
        gaps,
        "LIVE-GAP-008",
        "monitoring",
        "Live monitoring, alerts, and reconciliation",
        "SIM_ONLY observation exists; live alerting/reconciliation is not defined",
        "major",
        "Define alerts for order, position, P/L, margin, disconnect, stale tick, and ledger mismatch.",
    )
    add_gap(
        gaps,
        "LIVE-GAP-009",
        "account",
        "Broker/account/spec confirmation",
        "Current audit does not validate live account type, leverage, contract size, margin, or balance limit",
        "major",
        "Record allowed account, leverage, symbol spec, balance cap, and market-hours policy.",
    )
    add_gap(
        gaps,
        "LIVE-GAP-010",
        "trial",
        "Non-production order-placement rehearsal",
        "Only SIM_ONLY ledger-zero runs have passed; no demo/live-like tiny-order rehearsal is approved",
        "major",
        "Run a separate demo or tester order-placement gate before any real-money enablement.",
    )

    critical_gap_count = sum(1 for row in gaps if row["severity"] == "critical")
    major_gap_count = sum(1 for row in gaps if row["severity"] == "major")
    sim_ready = sim_readiness.get("status") == "pass" and observation.get("status") == "pass"
    decision = {
        "decision_time": datetime.now().isoformat(timespec="seconds"),
        "check_id": "stage_state_live_trade_readiness_gap_audit",
        "status": "blocked",
        "audit_completed": True,
        "ready_to_continue_sim_only_monitoring": sim_ready,
        "ready_to_live_trade": False,
        "open_gap_count": len(gaps),
        "critical_gap_count": critical_gap_count,
        "major_gap_count": major_gap_count,
        "positions_count": counts.get("positions_count", ""),
        "orders_count": counts.get("orders_count", ""),
        "sim_readiness_status": sim_readiness.get("status", ""),
        "observation_status": observation.get("status", ""),
        "hardcoded_credential_file_count": len(hardcoded_files),
        "recommended_next_action": "draft_live_trade_gate_checklist_without_enabling_live",
    }

    write_csv(
        OUT_DIR / "live_trade_readiness_gap_checks.csv",
        checks,
        ["check_id", "category", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(
        OUT_DIR / "live_trade_readiness_gap_checklist.csv",
        gaps,
        ["gap_id", "category", "requirement", "current_state", "severity", "required_action", "status"],
    )
    write_csv(OUT_DIR / "live_trade_readiness_gap_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "live_trade_readiness_gap_decision.json", decision)
    (OUT_DIR / "live_trade_readiness_gap_audit.md").write_text(build_report(decision, gaps), encoding="utf-8-sig")

    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
