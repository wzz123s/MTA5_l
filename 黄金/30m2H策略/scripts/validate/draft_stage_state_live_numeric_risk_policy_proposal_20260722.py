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
AUTO_TRADE = ROOT / "auto_trade"
OUT_DIR = VALIDATION_DIR / "stage_state_live_numeric_risk_policy_proposal_20260722"

DEMO_DECISION = (
    VALIDATION_DIR
    / "stage_state_demo_manual_confirmation_package_20260721"
    / "demo_manual_confirmation_decision.json"
)
REHEARSAL_DECISION = (
    VALIDATION_DIR
    / "stage_state_nonprod_mt5_rehearsal_execution_20260721"
    / "nonprod_mt5_rehearsal_decision.json"
)
BROKER_SPEC = (
    VALIDATION_DIR
    / "stage_state_broker_symbol_spec_read_only_20260721"
    / "broker_symbol_spec.csv"
)
FROZEN_SET = AUTO_TRADE / "30m2H_Strategy_EA.stage_state_frozen_20260718.set"
EA_MQ5 = AUTO_TRADE / "30m2H_Strategy_EA.mq5"


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
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def parse_set(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(";") or "=" not in stripped:
            continue
        key, raw = stripped.split("=", 1)
        values[key] = raw.split("||", 1)[0]
    return values


def has_pattern(text: str, pattern: str) -> bool:
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


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


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().isoformat(timespec="seconds")

    demo = read_json(DEMO_DECISION)
    rehearsal = read_json(REHEARSAL_DECISION)
    broker = read_rows(BROKER_SPEC)[0]
    set_values = parse_set(FROZEN_SET)
    ea_text = EA_MQ5.read_text(encoding="utf-8-sig", errors="ignore")

    balance_cap = float(demo.get("starting_balance_cap", 2000))
    strategy_risk_pct = float(set_values.get("InpRiskPct", "3.0"))
    observed_max_lot = float(rehearsal.get("max_lot", "0.05"))
    set_max_lot = float(set_values.get("InpMaxLots", "10.0"))
    proposed_max_lot = min(set_max_lot, max(0.10, round(observed_max_lot * 2, 2)))
    current_spread = int(float(broker.get("spread_points_current", "0") or 0))
    proposed_max_spread = max(300, current_spread + 60)

    policy = {
        "gap_id": "LIVE-GAP-006",
        "policy_status": "proposal_pending_user_confirmation",
        "scope": "live_numeric_risk_limits_candidate",
        "account_alias": demo.get("account_alias", ""),
        "account_type_source": demo.get("account_type", ""),
        "symbol": demo.get("symbol", "XAUUSDm"),
        "balance_cap": balance_cap,
        "leverage": demo.get("leverage", ""),
        "strategy_risk_pct": strategy_risk_pct,
        "max_daily_loss_usd": round(balance_cap * 0.06, 2),
        "max_daily_loss_pct": 6.0,
        "max_drawdown_usd": round(balance_cap * 0.10, 2),
        "max_drawdown_pct": 10.0,
        "max_open_positions": int(set_values.get("InpMaxPos", "3")),
        "max_new_positions_per_day": 9,
        "max_spread_points": proposed_max_spread,
        "margin_guard_pct": 500,
        "min_lot": float(set_values.get("InpMinLots", "0.01")),
        "max_lot": proposed_max_lot,
        "set_InpMaxLots": set_max_lot,
        "observed_rehearsal_max_lot": observed_max_lot,
        "stop_new_entries_if_limits_breached": True,
        "force_manual_review_if_limits_breached": True,
        "close_positions_rule": "strategy_defined_until_emergency_rehearsal_is_completed",
        "requires_user_confirmation": True,
        "requires_ea_guard_implementation_or_external_monitor": True,
        "ready_to_live_trade": False,
        "generated_at": generated_at,
    }

    support_rows = [
        {
            "risk_control": "per_trade_strategy_risk_pct",
            "proposal_value": strategy_risk_pct,
            "current_ea_support": "supported_by_InpRiskPct_dynamic_lots",
            "current_set_value": set_values.get("InpRiskPct", ""),
            "implementation_gap": "none_for_strategy_lot_calculation",
        },
        {
            "risk_control": "max_open_positions",
            "proposal_value": policy["max_open_positions"],
            "current_ea_support": "supported_by_InpMaxPos",
            "current_set_value": set_values.get("InpMaxPos", ""),
            "implementation_gap": "none_for_concurrent_position_count",
        },
        {
            "risk_control": "min_lot",
            "proposal_value": policy["min_lot"],
            "current_ea_support": "supported_by_InpMinLots",
            "current_set_value": set_values.get("InpMinLots", ""),
            "implementation_gap": "none",
        },
        {
            "risk_control": "max_lot",
            "proposal_value": policy["max_lot"],
            "current_ea_support": "supported_by_InpMaxLots_but_current_set_is_broader",
            "current_set_value": set_values.get("InpMaxLots", ""),
            "implementation_gap": "live set should lower InpMaxLots or external monitor must enforce cap",
        },
        {
            "risk_control": "max_daily_loss",
            "proposal_value": policy["max_daily_loss_usd"],
            "current_ea_support": "not_found",
            "current_set_value": "",
            "implementation_gap": "requires EA guard or external account monitor",
        },
        {
            "risk_control": "max_drawdown",
            "proposal_value": policy["max_drawdown_usd"],
            "current_ea_support": "not_found",
            "current_set_value": "",
            "implementation_gap": "requires EA guard or external account monitor",
        },
        {
            "risk_control": "max_spread_points",
            "proposal_value": policy["max_spread_points"],
            "current_ea_support": "not_found",
            "current_set_value": broker.get("spread_points_current", ""),
            "implementation_gap": "requires EA spread check before entries or external monitor",
        },
        {
            "risk_control": "margin_guard_pct",
            "proposal_value": policy["margin_guard_pct"],
            "current_ea_support": "partial_pre_trade_margin_check",
            "current_set_value": "hardcoded_estimate_leverage_1_500_in_source",
            "implementation_gap": "EA should use ACCOUNT_LEVERAGE or explicit InpLeverage before live",
        },
    ]

    checks = [
        check("demo_balance_cap_2000", balance_cap == 2000, balance_cap, 2000),
        check("rehearsal_passed", rehearsal.get("status") == "nonprod_mt5_rehearsal_passed", rehearsal.get("status"), "nonprod_mt5_rehearsal_passed"),
        check("symbol_xauusdm", demo.get("symbol") == "XAUUSDm", demo.get("symbol"), "XAUUSDm"),
        check("strategy_risk_pct_present", strategy_risk_pct > 0, strategy_risk_pct, "> 0"),
        check("max_daily_loss_positive", policy["max_daily_loss_usd"] > 0, policy["max_daily_loss_usd"], "> 0"),
        check("max_drawdown_positive", policy["max_drawdown_usd"] > 0, policy["max_drawdown_usd"], "> 0"),
        check("max_spread_at_or_above_current", proposed_max_spread >= current_spread, proposed_max_spread, f">= current {current_spread}"),
        check("max_lot_not_above_set_cap", proposed_max_lot <= set_max_lot, proposed_max_lot, f"<= {set_max_lot}"),
        check("ea_has_inp_risk_pct", has_pattern(ea_text, r"\bInpRiskPct\b"), "present" if has_pattern(ea_text, r"\bInpRiskPct\b") else "missing", "present"),
        check("ea_has_inp_max_pos", has_pattern(ea_text, r"\bInpMaxPos\b"), "present" if has_pattern(ea_text, r"\bInpMaxPos\b") else "missing", "present"),
        check("ea_lacks_daily_loss_guard_expected", not has_pattern(ea_text, r"MaxDaily|DailyLoss"), "not found", "not found"),
        check("ea_lacks_drawdown_guard_expected", not has_pattern(ea_text, r"MaxDrawdown|Drawdown"), "not found", "not found"),
        check("ea_lacks_spread_guard_expected", not has_pattern(ea_text, r"MaxSpread|SYMBOL_SPREAD"), "not found", "not found"),
        check("margin_estimate_hardcoded_500_detected", " / 500.0" in ea_text or "/500.0" in ea_text, "detected" if (" / 500.0" in ea_text or "/500.0" in ea_text) else "missing", "detected", "warning", "Conservative but mismatched with 1:2000 leverage."),
        check("proposal_not_live_approval", policy["ready_to_live_trade"] is False and policy["requires_user_confirmation"] is True, "ready=false confirmation=true", "ready=false confirmation=true"),
    ]
    blocker_failures = [row for row in checks if row["severity"] == "blocker" and not row["pass"]]
    warning_failures = [row for row in checks if row["severity"] == "warning" and not row["pass"]]

    decision = {
        "decision_time": generated_at,
        "check_id": "stage_state_live_numeric_risk_policy_proposal",
        "status": "live_numeric_risk_policy_proposal_pending_user_confirmation" if not blocker_failures else "live_numeric_risk_policy_proposal_invalid",
        "max_daily_loss_usd": policy["max_daily_loss_usd"],
        "max_drawdown_usd": policy["max_drawdown_usd"],
        "max_open_positions": policy["max_open_positions"],
        "max_new_positions_per_day": policy["max_new_positions_per_day"],
        "max_spread_points": policy["max_spread_points"],
        "margin_guard_pct": policy["margin_guard_pct"],
        "min_lot": policy["min_lot"],
        "max_lot": policy["max_lot"],
        "requires_user_confirmation": True,
        "requires_ea_guard_implementation_or_external_monitor": True,
        "live_gap_006_closed": False,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "warning_count": len(warning_failures),
        "recommended_next_action": "user_confirm_or_adjust_numeric_risk_limits_then_decide_ea_guard_or_external_monitor",
    }

    write_json(OUT_DIR / "live_risk_policy_proposal.json", policy)
    write_csv(
        OUT_DIR / "live_risk_policy_ea_support_matrix.csv",
        support_rows,
        ["risk_control", "proposal_value", "current_ea_support", "current_set_value", "implementation_gap"],
    )
    write_csv(
        OUT_DIR / "live_risk_policy_proposal_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(OUT_DIR / "live_risk_policy_proposal_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "live_risk_policy_proposal_decision.json", decision)

    confirm_lines = [
        "# Live Numeric Risk Policy Confirmation Required",
        "",
        "## Proposed Values",
        "",
        f"- max_daily_loss_usd: `{policy['max_daily_loss_usd']}`",
        f"- max_drawdown_usd: `{policy['max_drawdown_usd']}`",
        f"- max_open_positions: `{policy['max_open_positions']}`",
        f"- max_new_positions_per_day: `{policy['max_new_positions_per_day']}`",
        f"- max_spread_points: `{policy['max_spread_points']}`",
        f"- margin_guard_pct: `{policy['margin_guard_pct']}`",
        f"- min_lot: `{policy['min_lot']}`",
        f"- max_lot: `{policy['max_lot']}`",
        f"- balance_cap: `{policy['balance_cap']}`",
        "",
        "## Required Human Decision",
        "",
        "- Confirm these values exactly, or provide replacement values.",
        "- Decide whether risk guards are implemented inside the EA or enforced by an external monitor before live trading.",
        "- This proposal does not close `LIVE-GAP-006` and does not approve live trading.",
        "",
    ]
    (OUT_DIR / "live_risk_policy_confirmation_required.md").write_text(
        "\n".join(confirm_lines), encoding="utf-8-sig"
    )

    report_lines = [
        "# Live Numeric Risk Policy Proposal",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- live_gap_006_closed: `{decision['live_gap_006_closed']}`",
        f"- requires_user_confirmation: `{decision['requires_user_confirmation']}`",
        f"- requires_ea_guard_implementation_or_external_monitor: `{decision['requires_ea_guard_implementation_or_external_monitor']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        "",
        "## Proposed Values",
        "",
    ]
    for key in [
        "max_daily_loss_usd",
        "max_drawdown_usd",
        "max_open_positions",
        "max_new_positions_per_day",
        "max_spread_points",
        "margin_guard_pct",
        "min_lot",
        "max_lot",
    ]:
        report_lines.append(f"- `{key}`: `{decision[key]}`")
    report_lines.extend(
        [
            "",
            "## Implementation Reality",
            "",
            "- Current EA supports dynamic risk sizing, max concurrent positions, min lot, max lot, and partial margin checks.",
            "- Current EA does not expose live max daily loss, max drawdown, or max spread guards.",
            "- Current EA margin estimate uses a hardcoded 1:500 assumption, while the demo parameter is 1:2000.",
            "",
            "## Support Matrix",
            "",
        ]
    )
    for row in support_rows:
        report_lines.append(
            f"- `{row['risk_control']}`: {row['current_ea_support']}; gap: {row['implementation_gap']}"
        )
    report_lines.extend(["", "## Checks", ""])
    for row in checks:
        report_lines.append(f"- `{row['check_id']}`: `{row['pass']}` - actual `{row['actual']}`, expected `{row['expected']}`")
    report_lines.append("")
    (OUT_DIR / "live_numeric_risk_policy_proposal.md").write_text(
        "\n".join(report_lines), encoding="utf-8-sig"
    )

    for key, value in decision.items():
        print(f"{key}={value}")
    return 1 if blocker_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
