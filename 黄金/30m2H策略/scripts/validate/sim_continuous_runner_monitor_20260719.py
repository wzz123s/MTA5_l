from __future__ import annotations


import argparse
import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def current_value(value: str) -> str:
    return value.split("||", 1)[0].strip()


def parse_set(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith(";") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = current_value(value)
    return values


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


def path_from(value: object) -> Optional[Path]:
    text = str(value or "").strip()
    return Path(text) if text else None


def safe_exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def safe_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def existing_latest(paths: Iterable[object]) -> Optional[Path]:
    candidates = [path_from(item) for item in paths]
    existing = [path for path in candidates if path is not None and safe_exists(path)]
    if not existing:
        return None
    return max(existing, key=safe_mtime)


def csv_row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def csv_columns(path: Path) -> List[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        return next(reader, [])


def age_minutes(path: Path) -> float:
    return max(0.0, (datetime.now().timestamp() - path.stat().st_mtime) / 60.0)


def terminal_running() -> bool:
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "if (Get-Process -Name terminal64 -ErrorAction SilentlyContinue) { 'terminal64.exe' }",
            ],
            text=True,
            capture_output=True,
            timeout=10,
        )
    except Exception:
        return False
    text = (result.stdout or "") + (result.stderr or "")
    return "terminal64.exe" in text.lower()


def file_text(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", errors="ignore")
    return data.decode("utf-8-sig", errors="ignore")


def log_scan(paths: Iterable[object]) -> Dict[str, object]:
    candidates = [path_from(item) for item in paths]
    existing = [path for path in candidates if path is not None and safe_exists(path)]
    if not existing:
        return {"path": "", "exists": False, "critical_hits": "", "sim_marker_seen": False}
    critical_patterns = [
        "Mode:     LIVE TRADING",
        "InpSimMode=false",
        "auto_trader.py",
    ]
    hits: List[str] = []
    sim_marker_seen = False
    scanned: List[str] = []
    for path in sorted(existing, key=safe_mtime, reverse=True):
        try:
            text = file_text(path)
        except OSError:
            continue
        scanned.append(str(path))
        for pattern in critical_patterns:
            if pattern in text:
                hits.append(f"{path.name}:{pattern}")
        if "SIMULATION" in text or "InpSimMode=true" in text or "[SIM MODE" in text:
            sim_marker_seen = True
    return {
        "path": ";".join(scanned),
        "exists": True,
        "critical_hits": ";".join(hits),
        "sim_marker_seen": sim_marker_seen,
    }


def append_alert(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8-sig") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def run_monitor(config: Dict[str, object], out_dir: Path, mode: str) -> Dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    checks: List[Dict[str, object]] = []

    ea = dict(config.get("ea", {}) or {})
    chart = dict(config.get("chart", {}) or {})
    risk = dict(config.get("risk_controls", {}) or {})
    monitoring = dict(config.get("monitoring", {}) or {})

    terminal_path = path_from(dict(config.get("terminal", {}) or {}).get("path"))
    ex5_path = path_from(ea.get("local_ex5"))
    set_path = path_from(ea.get("parameter_set"))
    kill_switch = path_from(risk.get("kill_switch_file"))
    signal_paths = monitoring.get("signal_csv_candidates", [])
    ledger_paths = monitoring.get("trade_ledger_candidates", [])
    log_paths = monitoring.get("log_candidates", [])
    if not isinstance(signal_paths, list):
        signal_paths = [signal_paths]
    if not isinstance(ledger_paths, list):
        ledger_paths = [ledger_paths]
    if not isinstance(log_paths, list):
        log_paths = [log_paths]

    add_check(checks, "live_trade_disabled", config.get("live_trade_enabled") is False, config.get("live_trade_enabled"), "False")
    add_check(checks, "sim_only_lock_enabled", config.get("sim_only_lock") is True, config.get("sim_only_lock"), "True")
    add_check(checks, "execution_not_auto_opened", config.get("execution_enabled") is False, config.get("execution_enabled"), "False")
    add_check(checks, "auto_trader_blocked", "auto_trade/auto_trader.py" in (config.get("do_not_run") or []), config.get("do_not_run"), "contains auto_trade/auto_trader.py")
    add_check(checks, "terminal_path_exists", terminal_path is not None and terminal_path.exists(), terminal_path or "", "exists")
    add_check(checks, "local_ex5_exists", ex5_path is not None and ex5_path.exists(), ex5_path or "", "exists")
    add_check(checks, "sim_set_exists", set_path is not None and set_path.exists(), set_path or "", "exists")

    set_values = parse_set(set_path) if set_path else {}
    required_inputs = dict(ea.get("required_inputs", {}) or {})
    for key, expected in required_inputs.items():
        actual = set_values.get(key, "")
        add_check(checks, f"set_{key}", actual == str(expected), actual, expected)

    add_check(checks, "allowed_symbol", chart.get("symbol") == risk.get("allowed_symbol") == "XAUUSDm", f"{chart.get('symbol')}/{risk.get('allowed_symbol')}", "XAUUSDm")
    add_check(checks, "allowed_period", chart.get("period") == risk.get("allowed_period") == "M30", f"{chart.get('period')}/{risk.get('allowed_period')}", "M30")

    stop_exists = bool(kill_switch and kill_switch.exists())
    add_check(checks, "kill_switch_absent", not stop_exists, str(kill_switch) if kill_switch else "", "absent")

    is_runtime_mode = mode in {"monitor", "forward-review"}
    term_running = terminal_running()
    add_check(
        checks,
        "terminal_running",
        term_running if is_runtime_mode else True,
        term_running,
        "True during monitor/forward-review; optional during preflight",
        "blocker" if is_runtime_mode else "warning",
    )

    signal_path = existing_latest(signal_paths)
    signal_rows = csv_row_count(signal_path) if signal_path else 0
    signal_age = age_minutes(signal_path) if signal_path else ""
    add_check(
        checks,
        "signal_csv_exists",
        signal_path is not None if is_runtime_mode else signal_path is not None,
        str(signal_path) if signal_path else "",
        "exists",
        "blocker" if is_runtime_mode else "warning",
    )
    add_check(
        checks,
        "signal_csv_has_rows",
        signal_rows > 0 if signal_path else (not is_runtime_mode),
        signal_rows,
        "> 0",
        "blocker" if is_runtime_mode else "warning",
    )
    if signal_path:
        max_age = float(monitoring.get("signal_csv_max_age_minutes", 90))
        stale_ok = bool(monitoring.get("preflight_allow_stale_archive", False)) and mode == "preflight"
        add_check(
            checks,
            "signal_csv_freshness",
            stale_ok or float(signal_age) <= max_age,
            f"{signal_age:.2f} minutes",
            f"<= {max_age} minutes",
            "blocker" if is_runtime_mode else "warning",
            "Stale archive is acceptable only for implementation preflight.",
        )

    ledger_path = existing_latest(ledger_paths)
    ledger_rows = csv_row_count(ledger_path) if ledger_path else 0
    expected_ledger_rows = int(monitoring.get("ledger_data_rows_expected", 0))
    add_check(
        checks,
        "trade_ledger_exists",
        ledger_path is not None if is_runtime_mode else ledger_path is not None,
        str(ledger_path) if ledger_path else "",
        "exists",
        "blocker" if is_runtime_mode else "warning",
    )
    add_check(
        checks,
        "trade_ledger_expected_rows",
        ledger_rows == expected_ledger_rows if ledger_path else (not is_runtime_mode),
        ledger_rows,
        expected_ledger_rows,
    )

    scan = log_scan(log_paths)
    add_check(
        checks,
        "log_source_exists",
        bool(scan["exists"]) if is_runtime_mode else True,
        scan["path"],
        "exists during monitor/forward-review; optional during preflight",
        "blocker" if is_runtime_mode else "warning",
    )
    add_check(checks, "no_live_mode_log_marker", scan["critical_hits"] == "", scan["critical_hits"], "no live/auto_trader markers")
    add_check(
        checks,
        "sim_marker_seen_in_logs",
        bool(scan["sim_marker_seen"]) if is_runtime_mode else True,
        scan["sim_marker_seen"],
        "True during monitor/forward-review; optional during preflight",
        "blocker" if is_runtime_mode else "warning",
    )

    blocker_failures = [row for row in checks if row["severity"] == "blocker" and row["status"] == "fail"]
    warning_failures = [row for row in checks if row["severity"] == "warning" and row["status"] == "fail"]
    passed = len(blocker_failures) == 0
    decision = {
        "decision_time": datetime.now().isoformat(timespec="seconds"),
        "check_id": "sim_continuous_runner_monitor",
        "mode": mode,
        "status": "pass" if passed else "fail",
        "pass": passed,
        "ready_to_sim_continuous_runner_execution": False,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "warning_count": len(warning_failures),
        "terminal_running": term_running,
        "signal_csv_path": str(signal_path) if signal_path else "",
        "signal_csv_rows": signal_rows,
        "trade_ledger_path": str(ledger_path) if ledger_path else "",
        "trade_ledger_rows": ledger_rows,
        "reason": "monitor_preflight_passed_execution_still_closed" if passed else "monitor_preflight_failed_closed",
    }

    heartbeat_file = path_from(monitoring.get("heartbeat_file"))
    if heartbeat_file:
        heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
        write_json(heartbeat_file, decision)

    alert_file = path_from(monitoring.get("alert_file"))
    if alert_file and not passed:
        append_alert(alert_file, decision)

    write_json(out_dir / "sim_continuous_runner_monitor_decision.json", decision)
    write_csv(out_dir / "sim_continuous_runner_monitor_decision.csv", [decision], list(decision.keys()))
    write_csv(
        out_dir / "sim_continuous_runner_monitor_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    return decision


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--mode", choices=["preflight", "monitor", "forward-review"], default="preflight")
    args = parser.parse_args()

    decision = run_monitor(read_json(Path(args.config)), Path(args.out_dir), args.mode)
    print(f"status={decision['status']}")
    print(f"mode={decision['mode']}")
    print(f"ready_to_sim_continuous_runner_execution={decision['ready_to_sim_continuous_runner_execution']}")
    print(f"ready_to_live_trade={decision['ready_to_live_trade']}")
    print(f"blocker_failure_count={decision['blocker_failure_count']}")
    print(f"warning_count={decision['warning_count']}")


if __name__ == "__main__":
    main()
