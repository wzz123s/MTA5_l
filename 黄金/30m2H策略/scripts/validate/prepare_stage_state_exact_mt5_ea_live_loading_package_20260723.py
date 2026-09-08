from __future__ import annotations


import csv
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_exact_mt5_ea_live_loading_package_20260723"

EA_MQ5 = ROOT / "auto_trade" / "30m2H_Strategy_EA.mq5"
EA_EX5 = ROOT / "auto_trade" / "30m2H_Strategy_EA.ex5"
SOURCE_SET = ROOT / "auto_trade" / "30m2H_Strategy_EA.live_risk_guard_rehearsal_20260601_20260707_20260722.set"
SOURCE_INI = ROOT / "auto_trade" / "30m2H_Strategy_EA.live_risk_guard_rehearsal_20260601_20260707_20260722.ini"
COMPILE_LOG = ROOT / "auto_trade" / "compile_live_risk_guard_20260722.log"
EMERGENCY_STOP_FLAG = ROOT / "auto_trade" / "EMERGENCY_STOP.flag"
RUNNER_STOP_FLAG = ROOT / "auto_trade" / "RUNNER_STOP.flag"
TERMINAL_PATH = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")

FINAL_GATE_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_final_live_gate_review_from_operator_approval_20260723"
    / "final_live_gate_review_decision.json"
)
ACCOUNT_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_live_account_spec_snapshot_read_only_20260723"
    / "live_account_spec_snapshot_decision.json"
)
AUTOTRADING_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_autotrading_disable_connected_snapshot_20260723"
    / "autotrading_disable_connected_snapshot_decision.json"
)
RISK_REHEARSAL_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_live_risk_guard_rehearsal_execution_20260722"
    / "live_risk_guard_rehearsal_decision.json"
)


REQUIRED_INPUTS = {
    "InpSymbol": "XAUUSDm",
    "InpRiskPct": "3.0",
    "InpUseDynamicLots": "true",
    "InpStageCount": "3",
    "InpStage1Lots": "0.01",
    "InpStage2Lots": "0.02",
    "InpStage3Lots": "0.03",
    "InpSimMode": "false",
    "InpEnableLiveRiskGuards": "true",
    "InpLiveBalanceCap": "2000.0",
    "InpMaxDailyLossUSD": "120.0",
    "InpMaxDrawdownUSD": "200.0",
    "InpMaxNewPositionsPerDay": "9",
    "InpMaxSpreadPoints": "300",
    "InpMarginGuardPct": "500.0",
    "InpLiveMaxLotCap": "0.1",
}


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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_set(path: Path) -> Dict[str, str]:
    inputs: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(";") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        inputs[key.strip()] = value.split("||", 1)[0].strip()
    return inputs


def read_text_any_encoding(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ["utf-8-sig", "utf-16", "utf-16-le", "gb18030"]:
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "Result:" in text or "errors" in text:
            return text
    return raw.decode("utf-8-sig", errors="replace").replace("\x00", "")


def check_row(
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


def file_row(path: Path, role: str) -> Dict[str, object]:
    return {
        "role": role,
        "path": str(path),
        "exists": path.exists(),
        "length": path.stat().st_size if path.exists() else "",
        "last_write_time": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
        if path.exists()
        else "",
        "sha256": sha256(path) if path.exists() else "",
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().isoformat(timespec="seconds")

    final_gate = read_json(FINAL_GATE_DECISION_JSON)
    account = read_json(ACCOUNT_DECISION_JSON)
    autotrading = read_json(AUTOTRADING_DECISION_JSON)
    risk_rehearsal = read_json(RISK_REHEARSAL_DECISION_JSON)

    live_set = OUT_DIR / "30m2H_Strategy_EA.live_loading_owner_local_20260723.set"
    source_set_text = SOURCE_SET.read_text(encoding="utf-8-sig")
    live_set.write_text(
        "; Exact MT5 EA live loading input snapshot.\n"
        "; Generated for manual loading package only; this file is not loaded by this script.\n"
        f"; Generated: {generated_at}\n"
        "; Stop flags must remain until a later explicit loading approval.\n\n"
        + source_set_text,
        encoding="utf-8-sig",
    )

    live_ini = OUT_DIR / "30m2H_Strategy_EA.live_loading_reference_20260723.ini"
    shutil.copyfile(SOURCE_INI, live_ini)

    inputs = parse_set(live_set)
    input_rows = [
        {
            "input_name": name,
            "expected_value": expected,
            "actual_value": inputs.get(name, ""),
            "match": inputs.get(name, "") == expected,
            "ready_to_live_trade": False,
        }
        for name, expected in REQUIRED_INPUTS.items()
    ]

    compile_log_text = read_text_any_encoding(COMPILE_LOG) if COMPILE_LOG.exists() else ""
    compile_ok = "0 errors, 0 warnings" in compile_log_text
    final_gate_passed = (
        final_gate.get("status") == "final_live_gate_approval_preconditions_satisfied_loading_package_pending"
        and final_gate.get("closed_gate_count") == 10
        and final_gate.get("blocked_gate_count") == 0
        and final_gate.get("ready_for_live_loading_package") is True
        and final_gate.get("ready_to_live_trade") is False
    )
    account_ok = (
        account.get("account_alias") == "MT5_ACCOUNT_***085"
        and account.get("server") == "Exness-MT5Trial5"
        and account.get("symbol") == "XAUUSDm"
        and account.get("balance_cap") == 2000.0
        and account.get("account_leverage") == 2000
        and account.get("positions_count") == 0
        and account.get("orders_count") == 0
    )
    rehearsal_ok = (
        risk_rehearsal.get("status") == "live_risk_guard_rehearsal_passed"
        and risk_rehearsal.get("guard_rehearsal_code_path_passed") is True
        and risk_rehearsal.get("nonprod_rehearsal_passed_exact_environment") is True
        and risk_rehearsal.get("runner_executed") is False
    )
    stop_flags_present = EMERGENCY_STOP_FLAG.exists() and RUNNER_STOP_FLAG.exists()
    autotrading_disabled = autotrading.get("terminal_trade_allowed") is False
    inputs_ok = all(row["match"] for row in input_rows)

    package_files = [
        file_row(EA_MQ5, "source_mq5"),
        file_row(EA_EX5, "compiled_ex5"),
        file_row(COMPILE_LOG, "compile_log"),
        file_row(live_set, "live_loading_set_snapshot"),
        file_row(live_ini, "reference_rehearsal_ini_copy"),
        file_row(EMERGENCY_STOP_FLAG, "emergency_stop_flag"),
        file_row(RUNNER_STOP_FLAG, "runner_stop_flag"),
    ]

    manifest = {
        "generated_at": generated_at,
        "package_id": "exact_mt5_ea_live_loading_package_20260723",
        "status": "exact_live_loading_package_ready_fail_closed",
        "operator_alias": "owner_local",
        "terminal_path": str(TERMINAL_PATH),
        "account_alias": account.get("account_alias"),
        "server": account.get("server"),
        "symbol": "XAUUSDm",
        "timeframe": "M30",
        "execution_mode": "MT5_EA_ONLY",
        "ea_ex5": str(EA_EX5),
        "ea_mq5": str(EA_MQ5),
        "compile_log": str(COMPILE_LOG),
        "live_loading_set_snapshot": str(live_set),
        "reference_rehearsal_ini_copy": str(live_ini),
        "critical_inputs": {name: inputs.get(name, "") for name in REQUIRED_INPUTS},
        "final_gate_status": final_gate.get("status"),
        "stop_flags_present": stop_flags_present,
        "terminal_trade_allowed": autotrading.get("terminal_trade_allowed"),
        "orders_placed": False,
        "runner_executed": False,
        "ea_loaded": False,
        "stop_flags_removed": False,
        "ready_for_live_loading_package": True,
        "ready_to_live_trade": False,
    }

    checklist_rows = [
        {
            "step_no": 1,
            "phase": "preload",
            "action": "Verify final live gate review is passed to loading_package_pending",
            "expected": "closed=10, blocked=0, ready_for_live_loading_package=true, ready_to_live_trade=false",
            "status": "prepared",
            "operator_action_required": False,
        },
        {
            "step_no": 2,
            "phase": "preload",
            "action": "Verify EX5/MQ5/compile log hashes in manifest",
            "expected": "compile log has 0 errors and 0 warnings",
            "status": "prepared",
            "operator_action_required": False,
        },
        {
            "step_no": 3,
            "phase": "preload",
            "action": "Review live loading set snapshot",
            "expected": "InpSimMode=false and InpEnableLiveRiskGuards=true with 2000 balance cap",
            "status": "prepared",
            "operator_action_required": True,
        },
        {
            "step_no": 4,
            "phase": "fail_closed",
            "action": "Keep EMERGENCY_STOP.flag and RUNNER_STOP.flag in place",
            "expected": "no EA loading while stop flags are present",
            "status": "prepared",
            "operator_action_required": False,
        },
        {
            "step_no": 5,
            "phase": "manual_loading_later",
            "action": "Only after explicit later approval, remove stop flags and load the EA on XAUUSDm/M30",
            "expected": "separate approval required; not part of this package generation",
            "status": "pending_later_explicit_approval",
            "operator_action_required": True,
        },
    ]

    checks = [
        check_row("final_gate_passed_to_loading_package_pending", final_gate_passed, final_gate.get("status"), "final_live_gate_approval_preconditions_satisfied_loading_package_pending"),
        check_row("account_context_matches_approval", account_ok, account.get("account_alias"), "MT5_ACCOUNT_***085 / Exness-MT5Trial5 / XAUUSDm / 2000 / 1:2000 / no exposure"),
        check_row("risk_guard_rehearsal_passed", rehearsal_ok, risk_rehearsal.get("status"), "live_risk_guard_rehearsal_passed"),
        check_row("compile_log_zero_errors_warnings", compile_ok, "Result: 0 errors, 0 warnings" if compile_ok else "not found", "Result: 0 errors, 0 warnings"),
        check_row("critical_inputs_match", inputs_ok, sum(1 for row in input_rows if row["match"]), len(input_rows)),
        check_row("stop_flags_present_fail_closed", stop_flags_present, stop_flags_present, True),
        check_row("terminal_autotrading_disabled", autotrading_disabled, autotrading.get("terminal_trade_allowed"), False),
        check_row("orders_placed", True, False, False, "blocker", "Package generation does not place orders."),
        check_row("runner_executed", True, False, False, "blocker", "Package generation does not run auto_trade/auto_trader.py."),
        check_row("ea_loaded", True, False, False, "blocker", "Package generation does not load EA into MT5."),
        check_row("ready_to_live_trade_false", True, False, False, "blocker", "Loading package readiness is not trading authorization."),
    ]
    blocker_failures = [row for row in checks if row["severity"] == "blocker" and not row["pass"]]

    decision = {
        "decision_time": generated_at,
        "check_id": "stage_state_exact_mt5_ea_live_loading_package",
        "status": "exact_live_loading_package_ready_fail_closed" if not blocker_failures else "exact_live_loading_package_blocked",
        "final_gate_passed_to_loading_package_pending": final_gate_passed,
        "account_context_matches_approval": account_ok,
        "risk_guard_rehearsal_passed": rehearsal_ok,
        "compile_log_zero_errors_warnings": compile_ok,
        "critical_inputs_match": inputs_ok,
        "stop_flags_present": stop_flags_present,
        "terminal_autotrading_disabled": autotrading_disabled,
        "orders_placed": False,
        "runner_executed": False,
        "ea_loaded": False,
        "stop_flags_removed": False,
        "ready_for_live_loading_package": not blocker_failures,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "recommended_next_action": (
            "request_explicit_stop_flag_removal_and_manual_ea_loading_approval"
            if not blocker_failures
            else "fix_loading_package_blockers_then_regenerate"
        ),
    }

    write_json(OUT_DIR / "exact_mt5_ea_live_loading_manifest.json", manifest)
    write_csv(
        OUT_DIR / "exact_mt5_ea_live_loading_manifest_files.csv",
        package_files,
        ["role", "path", "exists", "length", "last_write_time", "sha256"],
    )
    write_csv(
        OUT_DIR / "exact_mt5_ea_live_loading_inputs.csv",
        input_rows,
        ["input_name", "expected_value", "actual_value", "match", "ready_to_live_trade"],
    )
    write_csv(
        OUT_DIR / "exact_mt5_ea_live_loading_checklist.csv",
        checklist_rows,
        ["step_no", "phase", "action", "expected", "status", "operator_action_required"],
    )
    write_csv(OUT_DIR / "exact_mt5_ea_live_loading_precheck.csv", checks, list(checks[0].keys()))
    write_csv(OUT_DIR / "exact_mt5_ea_live_loading_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "exact_mt5_ea_live_loading_decision.json", decision)

    report = f"""# Exact MT5 EA Live Loading Package

Generated: {generated_at}

## Decision

- Status: `{decision["status"]}`
- Final gate passed to loading package pending: `{final_gate_passed}`
- Account context matches approval: `{account_ok}`
- Risk guard rehearsal passed: `{rehearsal_ok}`
- Compile log zero errors/warnings: `{compile_ok}`
- Critical inputs match: `{inputs_ok}`
- Stop flags present: `{stop_flags_present}`
- Terminal AutoTrading disabled: `{autotrading_disabled}`
- Ready for live loading package: `{decision["ready_for_live_loading_package"]}`
- Ready to live trade: `false`

## Exact Package

- EA source: `{EA_MQ5}`
- EA compiled file: `{EA_EX5}`
- Compile log: `{COMPILE_LOG}`
- Set snapshot: `{live_set}`
- Terminal path: `{TERMINAL_PATH}`
- Symbol/timeframe: `XAUUSDm / M30`
- Account alias/server: `{account.get("account_alias")} / {account.get("server")}`

## Boundary

This package does not remove stop flags, load the EA, enable MT5 AutoTrading, start the Python runner, or place orders. It only prepares the exact manual loading evidence.
"""
    (OUT_DIR / "exact_mt5_ea_live_loading_package.md").write_text(report, encoding="utf-8-sig")
    return 0 if not blocker_failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
