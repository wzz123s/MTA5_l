from __future__ import annotations


import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
AUTO_TRADE = ROOT / "auto_trade"
OUT_DIR = VALIDATION_DIR / "stage_state_nonprod_mt5_rehearsal_package_20260721"

DEMO_DECISION = (
    VALIDATION_DIR
    / "stage_state_demo_manual_confirmation_package_20260721"
    / "demo_manual_confirmation_decision.json"
)
FROZEN_SET = AUTO_TRADE / "30m2H_Strategy_EA.stage_state_frozen_20260718.set"
EX5 = AUTO_TRADE / "30m2H_Strategy_EA.ex5"
BASELINE_LEDGER = (
    VALIDATION_DIR
    / "mt5_stage_state_full_2018_20260707_20260716"
    / "30m2H_strategy_trade_ledger.csv"
)

TERMINAL_EXE = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")
TERMINAL_DATA = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16"
)
TESTER_AGENT_FILES = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\B695BCB6C1E6864B6D96307B87B29F16\Agent-127.0.0.1-3000\MQL5\Files"
)

FROM_DATE = "2026.06.01"
TO_DATE = "2026.07.07"
FROM_PREFIX = "2026.06.01"
TO_PREFIX = "2026.07.07"
DEPOSIT = 2000
LEVERAGE = 2000
SYMBOL = "XAUUSDm"
PERIOD = "M30"
REPORT = AUTO_TRADE / "nonprod_demo_rehearsal_20260601_20260707_20260721_report.xml"
INI = AUTO_TRADE / "30m2H_Strategy_EA.nonprod_demo_rehearsal_20260601_20260707_20260721.ini"


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


def normalize_time(value: str) -> str:
    return value.replace("-", ".")


def in_window(row: Dict[str, str]) -> bool:
    t = normalize_time(row.get("open_time", ""))
    return FROM_PREFIX <= t[:10] <= TO_PREFIX


def safe_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


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


def safe_exists(path: Path) -> Tuple[bool, str]:
    try:
        return path.exists(), "ok"
    except PermissionError:
        return False, "permission_denied"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().isoformat(timespec="seconds")
    demo = read_json(DEMO_DECISION)
    set_lines, set_values = parse_set_lines(FROZEN_SET)
    ledger = [row for row in read_rows(BASELINE_LEDGER) if in_window(row)]

    exit_counts = Counter(row.get("local_exit_reason", "") for row in ledger)
    stage_counts = Counter(row.get("stage", "") for row in ledger)
    min_lot = min((safe_float(row.get("lots", "")) for row in ledger), default=0.0)
    max_lot = max((safe_float(row.get("lots", "")) for row in ledger), default=0.0)
    sl_rows = sum(1 for row in ledger if row.get("deal_reason") == "SL" or row.get("local_exit_reason") == "deal_exit")
    expert_rows = sum(1 for row in ledger if row.get("deal_reason") == "EXPERT")

    tester_inputs: List[str] = []
    for line in set_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            continue
        if "=" not in stripped:
            continue
        tester_inputs.append(stripped)
    if not any(line.startswith("InpSimMode=") for line in tester_inputs):
        tester_inputs.append("InpSimMode=false||false||0||true||N")

    ini_lines = [
        "; 30m2H non-production MT5 Strategy Tester rehearsal config",
        "; Scope: demo/tester order lifecycle only; not real-money live trading.",
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
        f"Leverage={LEVERAGE}",
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

    sample_rows = [
        {
            "metric": "baseline_rehearsal_window_rows",
            "value": len(ledger),
            "note": "Historical MT5 baseline rows in selected non-production rehearsal window.",
        },
        {"metric": "sl_or_deal_exit_rows", "value": sl_rows, "note": "Rows that exercise SL/deal-exit behavior."},
        {"metric": "expert_exit_rows", "value": expert_rows, "note": "Rows that exercise EA-driven exits."},
        {"metric": "min_lot", "value": min_lot, "note": "Historical baseline minimum lots in window."},
        {"metric": "max_lot", "value": max_lot, "note": "Historical baseline maximum lots in window."},
    ]
    for key, value in sorted(exit_counts.items()):
        sample_rows.append({"metric": f"exit_reason_{key or 'blank'}", "value": value, "note": ""})
    for key, value in sorted(stage_counts.items()):
        sample_rows.append({"metric": f"stage_{key or 'blank'}", "value": value, "note": ""})

    terminal_data_exists, terminal_data_probe = safe_exists(TERMINAL_DATA)
    checks = [
        check("demo_confirmation_ready", demo.get("ready_to_nonprod_rehearsal") is True, demo.get("ready_to_nonprod_rehearsal"), True),
        check("demo_confirmation_not_live", demo.get("ready_to_live_trade") is False, demo.get("ready_to_live_trade"), False),
        check("terminal_exe_exists", TERMINAL_EXE.exists(), str(TERMINAL_EXE), "exists"),
        check("ex5_exists", EX5.exists(), str(EX5), "exists"),
        check("frozen_set_exists", FROZEN_SET.exists(), str(FROZEN_SET), "exists"),
        check("symbol_matches", set_values.get("InpSymbol") == SYMBOL, set_values.get("InpSymbol"), SYMBOL),
        check("risk_pct_present", bool(set_values.get("InpRiskPct")), set_values.get("InpRiskPct", ""), "present"),
        check("dynamic_lots_enabled", set_values.get("InpUseDynamicLots", "").lower() == "true", set_values.get("InpUseDynamicLots", ""), "true"),
        check("inp_sim_mode_false_for_tester_only", set_values.get("InpSimMode", "").lower() == "false", set_values.get("InpSimMode", ""), "false"),
        check("deposit_2000", DEPOSIT == 2000, DEPOSIT, 2000),
        check("leverage_2000", LEVERAGE == 2000, LEVERAGE, 2000),
        check("baseline_window_has_rows", len(ledger) >= 6, len(ledger), ">= 6"),
        check("baseline_window_has_sl", sl_rows > 0, sl_rows, "> 0"),
        check("baseline_window_has_expert_exit", expert_rows > 0, expert_rows, "> 0"),
        check("tester_ini_written", INI.exists(), str(INI), "exists"),
        check(
            "terminal_data_path_known",
            terminal_data_exists or terminal_data_probe == "permission_denied",
            f"{TERMINAL_DATA}; probe={terminal_data_probe}",
            "exists or permission_denied",
            "Exact AppData log collection may require elevated read after tester run.",
        ),
    ]
    failures = [row for row in checks if not row["pass"]]

    decision = {
        "decision_time": generated_at,
        "check_id": "stage_state_nonprod_mt5_rehearsal_package",
        "status": "ready_to_execute_nonprod_mt5_rehearsal" if not failures else "nonprod_mt5_rehearsal_package_invalid",
        "tester_ini": str(INI),
        "terminal_exe": str(TERMINAL_EXE),
        "symbol": SYMBOL,
        "period": PERIOD,
        "from_date": FROM_DATE,
        "to_date": TO_DATE,
        "deposit": DEPOSIT,
        "leverage": LEVERAGE,
        "inp_sim_mode": set_values.get("InpSimMode", ""),
        "risk_pct": set_values.get("InpRiskPct", ""),
        "use_dynamic_lots": set_values.get("InpUseDynamicLots", ""),
        "baseline_window_rows": len(ledger),
        "ready_to_execute_nonprod_rehearsal": not failures,
        "ready_to_live_trade": False,
        "runner_executed": False,
        "orders_placed": False,
        "live_set_switched": False,
        "blocker_failure_count": len(failures),
        "recommended_next_action": "run_terminal64_config_bounded_nonprod_tester" if not failures else "fix_preflight_failures",
    }

    write_csv(OUT_DIR / "nonprod_mt5_rehearsal_sample_metrics.csv", sample_rows, ["metric", "value", "note"])
    write_csv(
        OUT_DIR / "nonprod_mt5_rehearsal_package_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(OUT_DIR / "nonprod_mt5_rehearsal_package_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "nonprod_mt5_rehearsal_package_decision.json", decision)

    report_lines = [
        "# Non-production MT5 Rehearsal Package",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- tester_ini: `{decision['tester_ini']}`",
        f"- terminal_exe: `{decision['terminal_exe']}`",
        f"- symbol: `{decision['symbol']}`",
        f"- period: `{decision['period']}`",
        f"- window: `{decision['from_date']} -> {decision['to_date']}`",
        f"- deposit: `{decision['deposit']}`",
        f"- leverage: `1:{decision['leverage']}`",
        f"- InpSimMode: `{decision['inp_sim_mode']}`",
        f"- risk_pct: `{decision['risk_pct']}`",
        f"- use_dynamic_lots: `{decision['use_dynamic_lots']}`",
        f"- baseline_window_rows: `{decision['baseline_window_rows']}`",
        f"- ready_to_execute_nonprod_rehearsal: `{decision['ready_to_execute_nonprod_rehearsal']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        "",
        "## Boundary",
        "",
        "- This package is for MT5 Strategy Tester or demo non-production order lifecycle rehearsal only.",
        "- It does not approve real-money live trading.",
        "- The Python runner remains blocked.",
        "- `InpSimMode=false` is confined to this non-production tester config.",
        "",
        "## Sample Metrics",
        "",
    ]
    for row in sample_rows:
        report_lines.append(f"- `{row['metric']}`: `{row['value']}`")
    report_lines.extend(["", "## Checks", ""])
    for row in checks:
        report_lines.append(f"- `{row['check_id']}`: `{row['pass']}` - actual `{row['actual']}`, expected `{row['expected']}`")
    report_lines.append("")
    (OUT_DIR / "nonprod_mt5_rehearsal_package.md").write_text("\n".join(report_lines), encoding="utf-8-sig")

    for key, value in decision.items():
        print(f"{key}={value}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
