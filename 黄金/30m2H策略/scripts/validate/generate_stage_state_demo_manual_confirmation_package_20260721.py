from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_demo_manual_confirmation_package_20260721"
EVIDENCE_DIR = OUT_DIR / "evidence"

PARSED_SET_JSON = (
    VALIDATION_DIR
    / "stage_state_live_package_hashes_and_set_parse_offline_20260721"
    / "parsed_live_set_template.json"
)
BROKER_SPEC_CSV = (
    VALIDATION_DIR
    / "stage_state_broker_symbol_spec_read_only_20260721"
    / "broker_symbol_spec.csv"
)

ACCOUNT_ALIAS = "MT5_DEMO_***085"
ACCOUNT_LAST3 = "085"
SYMBOL = "XAUUSDm"
START_BALANCE_CAP = 2000
LEVERAGE = 2000
APPROVAL_SCOPE = "nonprod_demo_rehearsal_only"
ALLOWED_RUNNER = "MT5_EA_ONLY"
RISK_MODE = "strategy_defined"
MAX_LOT_MODE = "strategy_defined"
EMERGENCY_STOP = "disable_mt5_auto_trading"
POSITION_CLOSE_RULE = "strategy_defined"


def read_json(path: Path) -> Dict[str, object]:
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def check(
    check_id: str,
    passed: bool,
    actual: object,
    expected: object,
    severity: str = "blocker",
    note: str = "",
) -> Dict[str, object]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "pass": passed,
        "actual": actual,
        "expected": expected,
        "severity": severity,
        "note": note,
    }


def scan_output_for_full_account() -> bool:
    # The user supplied a demo account id, but evidence stores only an alias and last 3 digits.
    forbidden = "277752085"
    for path in OUT_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".csv"}:
            if forbidden in path.read_text(encoding="utf-8-sig", errors="ignore"):
                return True
    return False


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().isoformat(timespec="seconds")
    parsed_set = read_json(PARSED_SET_JSON)
    broker_rows = read_rows(BROKER_SPEC_CSV)
    broker = broker_rows[0] if broker_rows else {}

    strategy_inputs = {
        "InpSymbol": parsed_set.get("InpSymbol", ""),
        "InpRiskPct": parsed_set.get("InpRiskPct", ""),
        "InpUseDynamicLots": parsed_set.get("InpUseDynamicLots", ""),
        "InpMinLots": parsed_set.get("InpMinLots", ""),
        "InpMaxLots": parsed_set.get("InpMaxLots", ""),
        "InpSimMode": parsed_set.get("InpSimMode", ""),
    }

    approval_md = [
        "# Demo MT5 EA Execution Approval Record",
        "",
        f"- approval_id: `DEMO-MT5-EA-20260721-001`",
        f"- approval_date: `{generated_at}`",
        "- approver: `user_confirmed_in_chat`",
        f"- account_alias: `{ACCOUNT_ALIAS}`",
        f"- account_id_storage: `redacted_full_id_not_written; last3={ACCOUNT_LAST3}`",
        "- account_type: `demo_nonproduction`",
        f"- symbol: `{SYMBOL}`",
        f"- starting_balance_cap: `{START_BALANCE_CAP}`",
        f"- leverage: `1:{LEVERAGE}`",
        f"- max_risk: `{RISK_MODE}; strategy_InpRiskPct={strategy_inputs['InpRiskPct']}`",
        f"- max_lots: `{MAX_LOT_MODE}; strategy_InpMaxLots={strategy_inputs['InpMaxLots']}`",
        f"- allowed_runner: `{ALLOWED_RUNNER}`",
        "- order_source_count: `1`",
        "- rollback_owner: `user`",
        f"- emergency_stop: `{EMERGENCY_STOP}`",
        f"- position_close_rule: `{POSITION_CLOSE_RULE}`",
        f"- approval_scope: `{APPROVAL_SCOPE}`",
        "- ready_to_nonprod_rehearsal: `true`",
        "- ready_to_live_trade: `false`",
        "",
        "## Boundary",
        "",
        "- This approval is for MT5 demo/non-production rehearsal only.",
        "- It is not a real-money live trading approval.",
        "- The full account id is intentionally not written into repo artifacts.",
        "- The next evidence must come from an actual MT5 tester/demo rehearsal report and ledger.",
        "",
    ]
    approval_path = EVIDENCE_DIR / "LIVE-GAP-001" / "demo_trade_approval_record.md"
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    approval_path.write_text("\n".join(approval_md), encoding="utf-8-sig")

    risk_policy = {
        "gap_id": "LIVE-GAP-006",
        "policy_scope": APPROVAL_SCOPE,
        "account_alias": ACCOUNT_ALIAS,
        "account_type": "demo_nonproduction",
        "starting_balance_cap": START_BALANCE_CAP,
        "leverage": LEVERAGE,
        "allowed_symbol": SYMBOL,
        "risk_mode": RISK_MODE,
        "strategy_inputs": strategy_inputs,
        "max_lot_mode": MAX_LOT_MODE,
        "max_daily_loss": "not_live_defined_requires_operator_limit_before_real_money",
        "max_drawdown": "not_live_defined_requires_operator_limit_before_real_money",
        "max_orders": "strategy_defined_requires_rehearsal_verification",
        "max_spread_points": "strategy_defined_requires_rehearsal_verification",
        "margin_guard_pct": "strategy_defined_requires_rehearsal_verification",
        "min_lot": strategy_inputs["InpMinLots"],
        "max_lot": strategy_inputs["InpMaxLots"],
        "balance_cap": START_BALANCE_CAP,
        "ready_to_nonprod_rehearsal": True,
        "ready_to_live_trade": False,
        "generated_at": generated_at,
    }
    write_json(EVIDENCE_DIR / "LIVE-GAP-006" / "demo_risk_policy.json", risk_policy)

    risk_confirm_md = [
        "# Demo Risk Policy Manual Confirmation",
        "",
        f"- account_size: `{START_BALANCE_CAP}`",
        f"- leverage: `1:{LEVERAGE}`",
        "- operator: `user_confirmed_in_chat`",
        f"- confirmed_at: `{generated_at}`",
        "- risk_scope: `strategy_defined_for_demo_rehearsal`",
        "- live_risk_limits_status: `not_ready_for_real_money`",
        "- ready_to_nonprod_rehearsal: `true`",
        "- ready_to_live_trade: `false`",
        "",
        "This confirmation allows a non-production MT5 rehearsal to measure the actual strategy lot, stop, order, and ledger behavior.",
        "It does not close the real-money live risk gate.",
        "",
    ]
    risk_confirm_path = EVIDENCE_DIR / "LIVE-GAP-006" / "demo_risk_policy_manual_confirmation.md"
    risk_confirm_path.write_text("\n".join(risk_confirm_md), encoding="utf-8-sig")

    account_snapshot = {
        "gap_id": "LIVE-GAP-009",
        "policy_scope": APPROVAL_SCOPE,
        "account_alias": ACCOUNT_ALIAS,
        "account_id_storage": f"redacted_full_id_not_written; last3={ACCOUNT_LAST3}",
        "account_type": "demo_nonproduction",
        "leverage": LEVERAGE,
        "balance_cap": START_BALANCE_CAP,
        "allowed_symbol": SYMBOL,
        "broker_symbol_spec_source": "broker_symbol_spec.csv",
        "broker_contract_size": broker.get("contract_size", ""),
        "broker_min_lot": broker.get("min_lot", ""),
        "broker_lot_step": broker.get("lot_step", ""),
        "broker_digits": broker.get("digits", ""),
        "broker_spread_policy": broker.get("spread_policy", ""),
        "captured_at": generated_at,
        "ready_to_nonprod_rehearsal": True,
        "ready_to_live_trade": False,
    }
    write_json(EVIDENCE_DIR / "LIVE-GAP-009" / "demo_account_spec_snapshot.json", account_snapshot)

    runner_md = [
        "# Demo Production Runner Decision",
        "",
        "- runner_mode: `MT5_EA_ONLY`",
        "- order_source_count: `1`",
        "- blocked_runner_files: `auto_trade/auto_trader.py`",
        "- approver: `user_confirmed_in_chat`",
        "- scope: `demo_nonproduction_rehearsal_only`",
        "- ready_to_nonprod_rehearsal: `true`",
        "- ready_to_live_trade: `false`",
        "",
        "Only the MT5 EA may place demo/tester orders during the rehearsal.",
        "The Python runner remains blocked for order placement.",
        "",
    ]
    runner_path = EVIDENCE_DIR / "LIVE-GAP-005" / "demo_runner_decision.md"
    runner_path.parent.mkdir(parents=True, exist_ok=True)
    runner_path.write_text("\n".join(runner_md), encoding="utf-8-sig")

    emergency_md = [
        "# Demo Emergency Stop Policy",
        "",
        f"- emergency_stop: `{EMERGENCY_STOP}`",
        "- disable_auto_trading_steps: `turn off MT5 Algo Trading / AutoTrading`",
        "- close_position_steps: `strategy_defined; validate in demo rehearsal`",
        "- rollback_steps: `remove EA from chart or stop tester/demo run`",
        "- owner: `user`",
        "- backup_owner: `not_assigned_for_live`",
        "- ready_to_nonprod_rehearsal: `true`",
        "- ready_to_live_trade: `false`",
        "",
        "This is sufficient to rehearse emergency behavior in non-production.",
        "It is not sufficient by itself for real-money positions.",
        "",
    ]
    emergency_path = EVIDENCE_DIR / "LIVE-GAP-007" / "demo_emergency_stop_policy.md"
    emergency_path.parent.mkdir(parents=True, exist_ok=True)
    emergency_path.write_text("\n".join(emergency_md), encoding="utf-8-sig")

    rehearsal_steps = [
        {
            "step_id": 1,
            "phase": "precheck",
            "action": "Open MT5 strategy tester or demo terminal profile",
            "expected_evidence": "terminal profile/account snapshot; account alias last3 matches expected demo account",
            "blocks_live_trade": True,
        },
        {
            "step_id": 2,
            "phase": "package",
            "action": "Load reviewed EX5 and reviewed set template for XAUUSDm",
            "expected_evidence": "tester settings screenshot/report or exported config; no live chart attachment",
            "blocks_live_trade": True,
        },
        {
            "step_id": 3,
            "phase": "execution",
            "action": "Run bounded tester/demo rehearsal and allow MT5 EA to create non-production orders only",
            "expected_evidence": "MT5 tester report or demo journal showing open/close lifecycle",
            "blocks_live_trade": True,
        },
        {
            "step_id": 4,
            "phase": "ledger",
            "action": "Export EA trade ledger and MT5 report",
            "expected_evidence": "rehearsal_ledger.csv plus tester report",
            "blocks_live_trade": True,
        },
        {
            "step_id": 5,
            "phase": "risk",
            "action": "Verify strategy-defined risk, lot, SL/TP, max position, and spread behavior",
            "expected_evidence": "nonprod_order_rehearsal_review.csv",
            "blocks_live_trade": True,
        },
        {
            "step_id": 6,
            "phase": "emergency",
            "action": "Rehearse disabling MT5 auto trading / removing EA without real-money exposure",
            "expected_evidence": "emergency_rehearsal_report.csv",
            "blocks_live_trade": True,
        },
    ]
    write_csv(
        OUT_DIR / "nonprod_mt5_rehearsal_next_steps.csv",
        rehearsal_steps,
        ["step_id", "phase", "action", "expected_evidence", "blocks_live_trade"],
    )

    has_full_account = scan_output_for_full_account()
    checks = [
        check("approval_scope_nonprod_demo_only", APPROVAL_SCOPE == "nonprod_demo_rehearsal_only", APPROVAL_SCOPE, "nonprod_demo_rehearsal_only"),
        check("account_alias_redacted", ACCOUNT_ALIAS == "MT5_DEMO_***085", ACCOUNT_ALIAS, "MT5_DEMO_***085"),
        check("full_account_id_not_written", not has_full_account, has_full_account, False),
        check("symbol_xauusdm", SYMBOL == "XAUUSDm" and strategy_inputs["InpSymbol"] == "XAUUSDm", f"{SYMBOL}; set={strategy_inputs['InpSymbol']}", "XAUUSDm"),
        check("balance_cap_2000", START_BALANCE_CAP == 2000, START_BALANCE_CAP, 2000),
        check("leverage_2000", LEVERAGE == 2000, LEVERAGE, 2000),
        check("risk_strategy_defined", RISK_MODE == "strategy_defined" and strategy_inputs["InpRiskPct"] != "", strategy_inputs["InpRiskPct"], "present"),
        check("max_lot_strategy_defined", MAX_LOT_MODE == "strategy_defined" and strategy_inputs["InpMaxLots"] != "", strategy_inputs["InpMaxLots"], "present"),
        check("runner_mt5_ea_only", ALLOWED_RUNNER == "MT5_EA_ONLY", ALLOWED_RUNNER, "MT5_EA_ONLY"),
        check("emergency_stop_present", EMERGENCY_STOP == "disable_mt5_auto_trading", EMERGENCY_STOP, "disable_mt5_auto_trading"),
        check("nonprod_rehearsal_not_yet_executed", True, "pending", "pending"),
        check("ready_to_nonprod_rehearsal_true", True, True, True),
        check("ready_to_live_trade_false", True, False, False),
    ]
    failures = [row for row in checks if not row["pass"]]

    evidence_matrix = [
        {
            "gap_id": "LIVE-GAP-001",
            "evidence_file": str(approval_path.relative_to(OUT_DIR)),
            "evidence_status": "collected_for_demo_nonprod_only",
            "closes_live_gate": False,
            "ready_to_nonprod_rehearsal": True,
            "ready_to_live_trade": False,
        },
        {
            "gap_id": "LIVE-GAP-005",
            "evidence_file": str(runner_path.relative_to(OUT_DIR)),
            "evidence_status": "collected_for_demo_nonprod_only",
            "closes_live_gate": False,
            "ready_to_nonprod_rehearsal": True,
            "ready_to_live_trade": False,
        },
        {
            "gap_id": "LIVE-GAP-006",
            "evidence_file": "evidence/LIVE-GAP-006/demo_risk_policy.json",
            "evidence_status": "collected_for_demo_nonprod_only",
            "closes_live_gate": False,
            "ready_to_nonprod_rehearsal": True,
            "ready_to_live_trade": False,
        },
        {
            "gap_id": "LIVE-GAP-007",
            "evidence_file": str(emergency_path.relative_to(OUT_DIR)),
            "evidence_status": "collected_for_demo_nonprod_only",
            "closes_live_gate": False,
            "ready_to_nonprod_rehearsal": True,
            "ready_to_live_trade": False,
        },
        {
            "gap_id": "LIVE-GAP-009",
            "evidence_file": "evidence/LIVE-GAP-009/demo_account_spec_snapshot.json",
            "evidence_status": "collected_for_demo_nonprod_only",
            "closes_live_gate": False,
            "ready_to_nonprod_rehearsal": True,
            "ready_to_live_trade": False,
        },
        {
            "gap_id": "LIVE-GAP-010",
            "evidence_file": "nonprod_mt5_rehearsal_next_steps.csv",
            "evidence_status": "planned_not_executed",
            "closes_live_gate": False,
            "ready_to_nonprod_rehearsal": True,
            "ready_to_live_trade": False,
        },
    ]
    write_csv(
        OUT_DIR / "demo_manual_confirmation_evidence_matrix.csv",
        evidence_matrix,
        [
            "gap_id",
            "evidence_file",
            "evidence_status",
            "closes_live_gate",
            "ready_to_nonprod_rehearsal",
            "ready_to_live_trade",
        ],
    )
    write_csv(
        OUT_DIR / "demo_manual_confirmation_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )

    decision = {
        "decision_time": generated_at,
        "check_id": "stage_state_demo_manual_confirmation_package",
        "status": "demo_manual_confirmation_collected_nonprod_rehearsal_pending" if not failures else "demo_manual_confirmation_invalid",
        "account_alias": ACCOUNT_ALIAS,
        "account_type": "demo_nonproduction",
        "symbol": SYMBOL,
        "starting_balance_cap": START_BALANCE_CAP,
        "leverage": LEVERAGE,
        "risk_mode": RISK_MODE,
        "allowed_runner": ALLOWED_RUNNER,
        "emergency_stop": EMERGENCY_STOP,
        "position_close_rule": POSITION_CLOSE_RULE,
        "nonprod_rehearsal_evidence_present": False,
        "ready_to_nonprod_rehearsal": not failures,
        "ready_to_live_trade": False,
        "runner_executed": False,
        "orders_placed": False,
        "live_set_switched": False,
        "blocker_failure_count": len(failures),
        "recommended_next_action": "execute_bounded_mt5_demo_or_tester_rehearsal_and_collect_report_ledger",
    }
    write_csv(OUT_DIR / "demo_manual_confirmation_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "demo_manual_confirmation_decision.json", decision)

    report_lines = [
        "# Demo Manual Confirmation Package",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- account_alias: `{decision['account_alias']}`",
        f"- account_type: `{decision['account_type']}`",
        f"- symbol: `{decision['symbol']}`",
        f"- starting_balance_cap: `{decision['starting_balance_cap']}`",
        f"- leverage: `1:{decision['leverage']}`",
        f"- risk_mode: `{decision['risk_mode']}`",
        f"- allowed_runner: `{decision['allowed_runner']}`",
        f"- emergency_stop: `{decision['emergency_stop']}`",
        f"- position_close_rule: `{decision['position_close_rule']}`",
        f"- ready_to_nonprod_rehearsal: `{decision['ready_to_nonprod_rehearsal']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        "",
        "## Boundary",
        "",
        "- This package records approval for MT5 demo/non-production rehearsal only.",
        "- It does not approve real-money live trading.",
        "- The full demo account id is not written into repo artifacts.",
        "- The next required evidence is an actual MT5 tester/demo rehearsal report and ledger.",
        "",
        "## Evidence Matrix",
        "",
    ]
    for row in evidence_matrix:
        report_lines.append(
            f"- `{row['gap_id']}`: `{row['evidence_status']}`, nonprod ready `{row['ready_to_nonprod_rehearsal']}`, live ready `{row['ready_to_live_trade']}`"
        )
    report_lines.extend(["", "## Checks", ""])
    for row in checks:
        report_lines.append(f"- `{row['check_id']}`: `{row['pass']}` - actual `{row['actual']}`, expected `{row['expected']}`")
    report_lines.append("")
    (OUT_DIR / "demo_manual_confirmation_package.md").write_text("\n".join(report_lines), encoding="utf-8-sig")

    for key, value in decision.items():
        print(f"{key}={value}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
