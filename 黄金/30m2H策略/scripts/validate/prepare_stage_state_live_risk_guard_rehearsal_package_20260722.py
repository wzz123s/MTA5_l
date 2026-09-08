from __future__ import annotations


import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
AUTO_TRADE = ROOT / "auto_trade"
OUT_DIR = VALIDATION_DIR / "stage_state_live_risk_guard_rehearsal_package_20260722"

POLICY_JSON = (
    VALIDATION_DIR
    / "stage_state_live_numeric_risk_policy_proposal_20260722"
    / "live_risk_policy_proposal.json"
)
IMPLEMENTATION_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_live_risk_guard_implementation_20260722"
    / "live_risk_guard_implementation_decision.json"
)
FROZEN_SET = AUTO_TRADE / "30m2H_Strategy_EA.stage_state_frozen_20260718.set"
LOCAL_EX5 = AUTO_TRADE / "30m2H_Strategy_EA.ex5"
DEPLOYED_EX5 = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Experts\Advisors\30m2H_Strategy_EA.ex5"
)
TERMINAL_EXE = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")

FROM_DATE = "2026.06.01"
TO_DATE = "2026.07.07"
DEPOSIT = 2000
LEVERAGE = 2000
SYMBOL = "XAUUSDm"
PERIOD = "M30"
SET_PATH = AUTO_TRADE / "30m2H_Strategy_EA.live_risk_guard_rehearsal_20260601_20260707_20260722.set"
REPORT = AUTO_TRADE / "live_risk_guard_rehearsal_20260601_20260707_20260722_report.xml"
INI = AUTO_TRADE / "30m2H_Strategy_EA.live_risk_guard_rehearsal_20260601_20260707_20260722.ini"


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


def parse_set_lines(path: Path) -> Tuple[List[str], Dict[str, str]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    values: Dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(";") or "=" not in stripped:
            continue
        key, raw_value = stripped.split("=", 1)
        values[key] = raw_value.split("||", 1)[0]
    return lines, values


def sha256(path: Path) -> str:
    try:
        exists = path.exists()
    except PermissionError:
        return "permission_denied"
    if not exists:
        return ""
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
    except PermissionError:
        return "permission_denied"
    return h.hexdigest()


def safe_exists(path: Path) -> bool:
    try:
        return path.exists()
    except PermissionError:
        return False


def mt5_input_line(key: str, value: object) -> str:
    value_s = str(value).lower() if isinstance(value, bool) else str(value)
    if value_s.lower() in {"true", "false"}:
        return f"{key}={value_s.lower()}||false||0||true||N"
    if key.startswith("InpMaxNewPositions") or key.startswith("InpMaxSpread") or key.startswith("InpLeverage"):
        return f"{key}={value_s}||{value_s}||1||{max(1, int(float(value_s)) * 10)}||N"
    return f"{key}={value_s}||{value_s}||0.100000||{max(1.0, float(value_s) * 10):.6f}||N"


def build_guard_inputs(base_lines: List[str], overrides: Dict[str, object]) -> List[str]:
    out: List[str] = []
    seen = set()
    for line in base_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(";") or "=" not in stripped:
            out.append(line)
            continue
        key = stripped.split("=", 1)[0]
        if key in overrides:
            out.append(mt5_input_line(key, overrides[key]))
            seen.add(key)
        else:
            out.append(line)
            seen.add(key)
    for key, value in overrides.items():
        if key not in seen:
            out.append(mt5_input_line(key, value))
    return out


def check(check_id: str, passed: bool, actual: object, expected: object, note: str = "") -> Dict[str, object]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "pass": passed,
        "actual": actual,
        "expected": expected,
        "severity": "blocker",
        "note": note,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().isoformat(timespec="seconds")

    policy = read_json(POLICY_JSON)
    implementation = read_json(IMPLEMENTATION_DECISION_JSON)
    base_lines, _ = parse_set_lines(FROZEN_SET)

    overrides = {
        "InpEnableLiveRiskGuards": True,
        "InpLiveBalanceCap": float(policy.get("balance_cap", DEPOSIT)),
        "InpMaxDailyLossUSD": float(policy.get("max_daily_loss_usd", 120)),
        "InpMaxDrawdownUSD": float(policy.get("max_drawdown_usd", 200)),
        "InpMaxNewPositionsPerDay": int(policy.get("max_new_positions_per_day", 9)),
        "InpMaxSpreadPoints": int(policy.get("max_spread_points", 300)),
        "InpMarginGuardPct": float(policy.get("margin_guard_pct", 500)),
        "InpLiveMaxLotCap": float(policy.get("max_lot", 0.10)),
        "InpLeverageOverride": 0,
        "InpSimMode": False,
        "InpVerboseDecisionDiag": True,
        "InpExportCSV": True,
        "InpExportTradeLedger": True,
    }

    guard_lines = build_guard_inputs(base_lines, overrides)
    SET_PATH.write_text("\n".join(guard_lines) + "\n", encoding="utf-8-sig")

    tester_inputs = [
        line.strip()
        for line in guard_lines
        if line.strip() and not line.strip().startswith(";") and "=" in line
    ]
    ini_lines = [
        "; 30m2H guard-enabled non-production MT5 Strategy Tester rehearsal config",
        "; Scope: tester/demo rehearsal only; not real-money live trading.",
        f"; Generated: {generated_at}",
        f"; Window: {FROM_DATE} to {TO_DATE}",
        f"; Deposit: {DEPOSIT}; Leverage: 1:{LEVERAGE}",
        "",
        "[Tester]",
        "Expert=Advisors\\30m2H_Strategy_EA.ex5",
        f"Symbol={SYMBOL}",
        f"Period={PERIOD}",
        "Optimization=0",
        "Model=0",
        f"FromDate={FROM_DATE}",
        f"ToDate={TO_DATE}",
        "ForwardMode=0",
        f"Deposit={DEPOSIT}",
        "Currency=USD",
        "ProfitInPips=0",
        f"Leverage=1:{LEVERAGE}",
        "ExecutionMode=0",
        "OptimizationCriterion=0",
        "Visual=0",
        "ReplaceReport=1",
        "ShutdownTerminal=1",
        f"Report={REPORT}",
        "",
        "[TesterInputs]",
        *tester_inputs,
        "",
    ]
    INI.write_text("\n".join(ini_lines), encoding="utf-8-sig")

    local_hash = sha256(LOCAL_EX5)
    deployed_hash = sha256(DEPLOYED_EX5)
    input_rows = [{"input": key, "value": value} for key, value in overrides.items()]
    checks = [
        check("implementation_code_ready", implementation.get("live_gap_006_code_implemented") is True, implementation.get("live_gap_006_code_implemented"), True),
        check("implementation_not_live_ready", implementation.get("ready_to_live_trade") is False, implementation.get("ready_to_live_trade"), False),
        check("terminal_exists", TERMINAL_EXE.exists(), str(TERMINAL_EXE), "exists"),
        check("local_ex5_exists", LOCAL_EX5.exists(), str(LOCAL_EX5), "exists"),
        check("deployed_ex5_exists", safe_exists(DEPLOYED_EX5), str(DEPLOYED_EX5), "exists"),
        check("deployed_hash_matches_local", bool(local_hash) and local_hash == deployed_hash, f"local={local_hash}; deployed={deployed_hash}", "same sha256"),
        check("guard_set_written", SET_PATH.exists(), str(SET_PATH), "exists"),
        check("guard_ini_written", INI.exists(), str(INI), "exists"),
        check("guard_enabled", overrides["InpEnableLiveRiskGuards"] is True, overrides["InpEnableLiveRiskGuards"], True),
        check("sim_mode_false_for_tester", overrides["InpSimMode"] is False, overrides["InpSimMode"], False),
        check("deposit_2000", DEPOSIT == 2000, DEPOSIT, 2000),
        check("leverage_2000", LEVERAGE == 2000, LEVERAGE, 2000),
    ]
    blockers = [row for row in checks if not row["pass"]]

    decision = {
        "decision_time": generated_at,
        "check_id": "stage_state_live_risk_guard_rehearsal_package",
        "status": "live_risk_guard_rehearsal_package_ready" if not blockers else "live_risk_guard_rehearsal_package_blocked",
        "ready_to_execute_nonprod_guard_rehearsal": not blockers,
        "ini": str(INI),
        "set": str(SET_PATH),
        "report": str(REPORT),
        "terminal_exe": str(TERMINAL_EXE),
        "symbol": SYMBOL,
        "period": PERIOD,
        "from_date": FROM_DATE,
        "to_date": TO_DATE,
        "deposit": DEPOSIT,
        "leverage": LEVERAGE,
        "local_ex5_sha256": local_hash,
        "deployed_ex5_sha256": deployed_hash,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blockers),
        "recommended_next_action": "run_terminal64_with_guard_enabled_tester_ini_then_collect_rehearsal_evidence",
    }

    write_csv(OUT_DIR / "live_risk_guard_rehearsal_inputs.csv", input_rows, ["input", "value"])
    write_csv(OUT_DIR / "live_risk_guard_rehearsal_package_checks.csv", checks, ["check_id", "status", "pass", "actual", "expected", "severity", "note"])
    write_csv(OUT_DIR / "live_risk_guard_rehearsal_package_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "live_risk_guard_rehearsal_package_decision.json", decision)

    report = f"""# LIVE-GAP-006 Guard-enabled Non-production Rehearsal Package

Generated: {generated_at}

## Decision

- Status: `{decision["status"]}`
- Ready to execute nonprod guard rehearsal: `{decision["ready_to_execute_nonprod_guard_rehearsal"]}`
- Ready to live trade: `false`

## Tester Config

- INI: `{INI}`
- SET: `{SET_PATH}`
- Report: `{REPORT}`
- Terminal: `{TERMINAL_EXE}`
- Expert: `Advisors\\30m2H_Strategy_EA.ex5`
- Symbol/period: `{SYMBOL}` / `{PERIOD}`
- Window: `{FROM_DATE}` to `{TO_DATE}`
- Deposit/leverage: `{DEPOSIT}` / `1:{LEVERAGE}`

## Guard Inputs

- `InpEnableLiveRiskGuards=true`
- `InpLiveBalanceCap={overrides["InpLiveBalanceCap"]}`
- `InpMaxDailyLossUSD={overrides["InpMaxDailyLossUSD"]}`
- `InpMaxDrawdownUSD={overrides["InpMaxDrawdownUSD"]}`
- `InpMaxNewPositionsPerDay={overrides["InpMaxNewPositionsPerDay"]}`
- `InpMaxSpreadPoints={overrides["InpMaxSpreadPoints"]}`
- `InpMarginGuardPct={overrides["InpMarginGuardPct"]}`
- `InpLiveMaxLotCap={overrides["InpLiveMaxLotCap"]}`
- `InpLeverageOverride={overrides["InpLeverageOverride"]}`
- `InpSimMode=false`

## Boundary

This package is for MT5 Strategy Tester / demo-context rehearsal only. It does not approve real-money live trading.
"""
    (OUT_DIR / "live_risk_guard_rehearsal_package.md").write_text(report, encoding="utf-8-sig")
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
