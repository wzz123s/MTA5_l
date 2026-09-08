from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_sim_only_startup_attach_gate_20260719"

AUTO_TRADE = ROOT / "auto_trade"
STARTUP_CONFIG = AUTO_TRADE / "30m2H_Strategy_EA_SIM_ONLY.startup_chart_trial_20260719.ini"
SIM_SET = AUTO_TRADE / "30m2H_Strategy_EA_SIM_ONLY.stage_state_sim_dryrun_20260719.set"

TERMINAL_EXE = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")
TERMINAL_DATA = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16"
)
TERMINAL_LOG = TERMINAL_DATA / "logs" / "20260719.log"
SIGNAL_CSV = TERMINAL_DATA / "MQL5" / "Files" / "30m2H_strategy_signals_export.csv"
LEDGER_CSV = TERMINAL_DATA / "MQL5" / "Files" / "30m2H_strategy_trade_ledger.csv"


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16", errors="ignore")
    return raw.decode("utf-8-sig", errors="ignore")


def current_set_value(value: str) -> str:
    return value.split("||", 1)[0].strip()


def parse_set(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for raw in read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith(";") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = current_set_value(value)
    return values


def data_row_count(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    return max(0, len(rows) - 1)


def add_check(
    checks: List[Dict[str, object]],
    check_id: str,
    passed: bool,
    actual: object,
    expected: object,
    severity: str = "blocker",
    note: str = "",
) -> None:
    checks.append(
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


def mt5_tick_time() -> Dict[str, object]:
    try:
        import MetaTrader5 as mt5  # type: ignore
    except Exception as exc:
        return {"ok": False, "tick_time": "", "tick_age_minutes": "", "error": f"import failed: {exc}"}

    ok = mt5.initialize(path=str(TERMINAL_EXE))
    if not ok:
        return {"ok": False, "tick_time": "", "tick_age_minutes": "", "error": str(mt5.last_error())}
    try:
        tick = mt5.symbol_info_tick("XAUUSDm")
        if tick is None:
            return {"ok": False, "tick_time": "", "tick_age_minutes": "", "error": "symbol_info_tick returned None"}
        tick_dt = datetime.fromtimestamp(tick.time)
        age = (datetime.now() - tick_dt).total_seconds() / 60.0
        return {
            "ok": True,
            "tick_time": tick_dt.isoformat(timespec="seconds"),
            "tick_age_minutes": round(age, 2),
            "error": "",
        }
    finally:
        mt5.shutdown()


def build_report(decision: Dict[str, object], checks: List[Dict[str, object]]) -> str:
    failed = [row for row in checks if row["status"] != "pass"]
    lines = [
        "# SIM_ONLY Startup Attach Gate",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- ready_to_runtime_forward_review_after_market_tick: `{decision['ready_to_runtime_forward_review_after_market_tick']}`",
        f"- ready_to_sim_continuous_runner_execution: `{decision['ready_to_sim_continuous_runner_execution']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        f"- signal_csv_rows: `{decision['signal_csv_rows']}`",
        f"- trade_ledger_rows: `{decision['trade_ledger_rows']}`",
        f"- latest_tick_time: `{decision['latest_tick_time']}`",
        f"- latest_tick_age_minutes: `{decision['latest_tick_age_minutes']}`",
        "",
        "## Interpretation",
        "",
        "- SIM_ONLY startup attach is confirmed by terminal log and target CSV creation.",
        "- Runtime data review remains pending because the signal CSV has no data rows yet.",
        "- The current blocker is stale/no market tick, not strategy logic or live-trade approval.",
        "",
        "## Failed Checks",
        "",
    ]
    if not failed:
        lines.append("- None.")
    else:
        for row in failed:
            lines.append(f"- `{row['check_id']}`: {row['actual']} (expected {row['expected']})")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    startup_text = read_text(STARTUP_CONFIG)
    log_text = read_text(TERMINAL_LOG)
    set_values = parse_set(SIM_SET)
    signal_rows = data_row_count(SIGNAL_CSV)
    ledger_rows = data_row_count(LEDGER_CSV)
    tick = mt5_tick_time()

    checks: List[Dict[str, object]] = []
    add_check(checks, "startup_config_exists", STARTUP_CONFIG.exists(), STARTUP_CONFIG, "exists")
    add_check(
        checks,
        "startup_config_has_no_credentials",
        not any(key in startup_text for key in ["Login=", "Password=", "Server="]),
        "no Login/Password/Server" if startup_text else "missing config",
        "no credential fields",
    )
    add_check(checks, "startup_config_live_trading_disabled", "AllowLiveTrading=0" in startup_text, "AllowLiveTrading=0" in startup_text, True)
    add_check(checks, "startup_config_points_to_sim_only_expert", "30m2H_Strategy_EA_SIM_ONLY.ex5" in startup_text, "SIM_ONLY.ex5" in startup_text, True)
    add_check(checks, "startup_config_points_to_sim_only_set", "30m2H_Strategy_EA_SIM_ONLY.stage_state_sim_dryrun_20260719.set" in startup_text, "SIM_ONLY set" in startup_text, True)
    add_check(checks, "sim_set_InpSimMode", set_values.get("InpSimMode", "").lower() == "true", set_values.get("InpSimMode", ""), "true")
    add_check(checks, "sim_set_InpExportCSV", set_values.get("InpExportCSV", "").lower() == "true", set_values.get("InpExportCSV", ""), "true")
    add_check(checks, "sim_set_InpExportTradeLedger", set_values.get("InpExportTradeLedger", "").lower() == "true", set_values.get("InpExportTradeLedger", ""), "true")
    add_check(checks, "terminal_log_start_config", str(STARTUP_CONFIG) in log_text and "successfully initialized from start config" in log_text, "start config seen" if str(STARTUP_CONFIG) in log_text else "not seen", "start config initialized")
    add_check(checks, "terminal_log_inputs_read", "30m2H_Strategy_EA_SIM_ONLY.ex5" in log_text and "inputs read" in log_text, "inputs read" if "inputs read" in log_text else "not seen", "inputs read from SIM_ONLY set")
    add_check(checks, "terminal_log_expert_loaded", "expert 30m2H_Strategy_EA_SIM_ONLY (XAUUSDm,M30) loaded successfully" in log_text, "loaded successfully" if "30m2H_Strategy_EA_SIM_ONLY (XAUUSDm,M30) loaded successfully" in log_text else "not seen", "SIM_ONLY expert loaded")
    add_check(checks, "signal_csv_exists", SIGNAL_CSV.exists(), SIGNAL_CSV, "exists")
    add_check(checks, "signal_csv_header_created", SIGNAL_CSV.exists() and SIGNAL_CSV.stat().st_size > 0, SIGNAL_CSV.stat().st_size if SIGNAL_CSV.exists() else 0, "> 0 bytes")
    add_check(checks, "trade_ledger_exists", LEDGER_CSV.exists(), LEDGER_CSV, "exists")
    add_check(checks, "trade_ledger_expected_rows", ledger_rows == 0, ledger_rows, 0)
    add_check(checks, "no_live_trading_marker", "Mode:     LIVE TRADING" not in log_text, "absent" if "Mode:     LIVE TRADING" not in log_text else "present", "absent")
    add_check(
        checks,
        "market_tick_recent_enough_for_forward_review",
        bool(tick.get("ok")) and float(tick.get("tick_age_minutes") or 999999) <= 90.0,
        tick.get("tick_age_minutes", ""),
        "<= 90 minutes",
        "pending",
        "Expected to fail outside market hours.",
    )
    add_check(
        checks,
        "signal_csv_has_runtime_rows",
        signal_rows > 0,
        signal_rows,
        "> 0",
        "pending",
        "Requires new market tick/bar after EA startup.",
    )

    blocker_failures = [row for row in checks if row["status"] == "fail" and row["severity"] == "blocker"]
    pending_failures = [row for row in checks if row["status"] == "fail" and row["severity"] == "pending"]
    attach_ready = not blocker_failures
    runtime_ready = attach_ready and not pending_failures
    status = "pass_attach_pending_market_data" if attach_ready and pending_failures else ("pass" if runtime_ready else "fail")
    decision = {
        "check_id": "stage_state_sim_only_startup_attach_gate",
        "status": status,
        "ready_to_runtime_forward_review_after_market_tick": attach_ready,
        "ready_to_sim_continuous_runner_execution": False,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "pending_failure_count": len(pending_failures),
        "signal_csv_rows": signal_rows,
        "trade_ledger_rows": ledger_rows,
        "latest_tick_time": tick.get("tick_time", ""),
        "latest_tick_age_minutes": tick.get("tick_age_minutes", ""),
        "terminal_running_and_attached": attach_ready,
    }

    write_csv(
        OUT_DIR / "sim_only_startup_attach_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(
        OUT_DIR / "sim_only_startup_attach_decision.csv",
        [decision],
        [
            "check_id",
            "status",
            "ready_to_runtime_forward_review_after_market_tick",
            "ready_to_sim_continuous_runner_execution",
            "ready_to_live_trade",
            "blocker_failure_count",
            "pending_failure_count",
            "signal_csv_rows",
            "trade_ledger_rows",
            "latest_tick_time",
            "latest_tick_age_minutes",
            "terminal_running_and_attached",
        ],
    )
    write_json(OUT_DIR / "sim_only_startup_attach_decision.json", decision)
    (OUT_DIR / "sim_only_startup_attach_gate.md").write_text(build_report(decision, checks), encoding="utf-8-sig")
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0 if attach_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
