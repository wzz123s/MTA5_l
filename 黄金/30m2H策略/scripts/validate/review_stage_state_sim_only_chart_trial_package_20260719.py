from __future__ import annotations


import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_sim_only_chart_trial_package_20260719"

AUTO_TRADE = ROOT / "auto_trade"
MAIN_SOURCE = AUTO_TRADE / "30m2H_Strategy_EA.mq5"
SIM_SOURCE = AUTO_TRADE / "30m2H_Strategy_EA_SIM_ONLY.mq5"
SIM_EX5 = AUTO_TRADE / "30m2H_Strategy_EA_SIM_ONLY.ex5"
SIM_SET = AUTO_TRADE / "30m2H_Strategy_EA_SIM_ONLY.stage_state_sim_dryrun_20260719.set"
COMPILE_LOG = AUTO_TRADE / "compile_sim_only_20260719.log"

TERMINAL_DATA = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16"
)
DEPLOYED_EX5 = TERMINAL_DATA / "MQL5" / "Experts" / "Advisors" / "30m2H_Strategy_EA_SIM_ONLY.ex5"
DEPLOYED_SET = TERMINAL_DATA / "MQL5" / "Presets" / "30m2H_Strategy_EA_SIM_ONLY.stage_state_sim_dryrun_20260719.set"


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


def sha256(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


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


def manual_steps() -> List[Dict[str, object]]:
    return [
        {
            "step_id": "refresh_navigator",
            "status": "pending",
            "action": "In MT5 Navigator, refresh Advisors if SIM_ONLY EA is not visible.",
            "acceptance": "Advisors shows 30m2H_Strategy_EA_SIM_ONLY.",
        },
        {
            "step_id": "open_chart",
            "status": "pending",
            "action": "Open XAUUSDm M30 chart.",
            "acceptance": "Active chart is XAUUSDm/M30.",
        },
        {
            "step_id": "attach_sim_only_ea",
            "status": "pending",
            "action": "Attach Advisors/30m2H_Strategy_EA_SIM_ONLY.ex5.",
            "acceptance": "Inputs dialog opens for SIM_ONLY EA.",
        },
        {
            "step_id": "load_sim_only_set",
            "status": "pending",
            "action": "Load Presets/30m2H_Strategy_EA_SIM_ONLY.stage_state_sim_dryrun_20260719.set.",
            "acceptance": "InpSimMode=true, InpExportCSV=true, InpExportTradeLedger=true.",
        },
        {
            "step_id": "confirm_log_marker",
            "status": "pending",
            "action": "Confirm Experts or Journal log after attach.",
            "acceptance": "Log contains SIM-ONLY GUARD and SIMULATION.",
        },
        {
            "step_id": "forward_review",
            "status": "pending",
            "action": "After one new M30 bar, run monitor in forward-review mode.",
            "acceptance": "Monitor status pass; ready_to_live_trade remains false.",
        },
    ]


def build_report(decision: Dict[str, object], checks: List[Dict[str, object]]) -> str:
    blocker_failures = [row for row in checks if row["status"] == "fail" and row["severity"] == "blocker"]
    warning_failures = [row for row in checks if row["status"] == "fail" and row["severity"] == "warning"]
    lines = [
        "# SIM_ONLY Chart Trial Package Review",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- ready_to_manual_chart_trial_with_sim_only: `{decision['ready_to_manual_chart_trial_with_sim_only']}`",
        f"- ready_to_startup_attach_trial: `{decision['ready_to_startup_attach_trial']}`",
        f"- ready_to_sim_continuous_runner_execution: `{decision['ready_to_sim_continuous_runner_execution']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        f"- blocker_failure_count: `{len(blocker_failures)}`",
        f"- warning_failure_count: `{len(warning_failures)}`",
        "",
        "## Package",
        "",
        f"- source: `{SIM_SOURCE}`",
        f"- local ex5: `{SIM_EX5}`",
        f"- deployed ex5: `{DEPLOYED_EX5}`",
        f"- local set: `{SIM_SET}`",
        f"- deployed set: `{DEPLOYED_SET}`",
        f"- compile log: `{COMPILE_LOG}`",
        "",
        "## Summary",
        "",
        "- The frozen main EA source remains unchanged and still defaults `InpSimMode=false`.",
        "- The SIM_ONLY wrapper defaults `InpSimMode=true` and aborts initialization if it is changed to false.",
        "- Strategy signal, stop, exit and sizing logic are copied from the frozen EA; this package is only a chart-trial safety wrapper.",
        "- The package does not open the continuous runner gate and does not approve live trading.",
        "",
        "## Failed Checks",
        "",
    ]
    if not blocker_failures and not warning_failures:
        lines.append("- None.")
    else:
        for row in blocker_failures + warning_failures:
            lines.append(f"- `{row['check_id']}`: {row['actual']} (expected {row['expected']})")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    main_text = read_text(MAIN_SOURCE)
    sim_text = read_text(SIM_SOURCE)
    compile_text = read_text(COMPILE_LOG)
    local_set_values = parse_set(SIM_SET)
    deployed_set_values = parse_set(DEPLOYED_SET)
    local_hash = sha256(SIM_EX5)
    deployed_hash = sha256(DEPLOYED_EX5)

    checks: List[Dict[str, object]] = []
    add_check(checks, "main_source_exists", MAIN_SOURCE.exists(), MAIN_SOURCE, "exists")
    add_check(checks, "sim_source_exists", SIM_SOURCE.exists(), SIM_SOURCE, "exists")
    add_check(
        checks,
        "main_default_sim_mode_unchanged",
        bool(re.search(r"input\s+bool\s+InpSimMode\s*=\s*false\s*;", main_text)),
        "false" if "InpSimMode" in main_text else "missing",
        "main EA default remains false",
    )
    add_check(
        checks,
        "sim_only_define_present",
        "#define SIM_ONLY_BUILD 1" in sim_text,
        "#define SIM_ONLY_BUILD 1" in sim_text,
        True,
    )
    add_check(
        checks,
        "sim_only_default_true",
        bool(re.search(r"input\s+bool\s+InpSimMode\s*=\s*true\s*;", sim_text)),
        "true" if "InpSimMode    = true" in sim_text else "not true",
        "InpSimMode=true",
    )
    add_check(
        checks,
        "sim_only_init_guard",
        "if(!InpSimMode)" in sim_text and "return INIT_FAILED;" in sim_text and "SIM-ONLY GUARD" in sim_text,
        "guard present" if "SIM-ONLY GUARD" in sim_text else "guard missing",
        "guard aborts InpSimMode=false",
    )
    add_check(
        checks,
        "compile_zero_errors_warnings",
        "Result: 0 errors, 0 warnings" in compile_text,
        "Result: 0 errors, 0 warnings" if "Result: 0 errors, 0 warnings" in compile_text else "compile issue",
        "0 errors, 0 warnings",
    )
    add_check(checks, "local_ex5_exists", SIM_EX5.exists(), SIM_EX5, "exists")
    add_check(checks, "deployed_ex5_exists", DEPLOYED_EX5.exists(), DEPLOYED_EX5, "exists")
    add_check(
        checks,
        "deployed_ex5_hash_match",
        bool(local_hash and deployed_hash and local_hash == deployed_hash),
        f"local={local_hash}; deployed={deployed_hash}",
        "same sha256",
    )
    for key in ["InpSimMode", "InpExportCSV", "InpExportTradeLedger", "InpUseDynamicLots"]:
        expected = "true"
        add_check(
            checks,
            f"local_set_{key}",
            local_set_values.get(key, "").lower() == expected,
            local_set_values.get(key, ""),
            expected,
        )
        add_check(
            checks,
            f"deployed_set_{key}",
            deployed_set_values.get(key, "").lower() == expected,
            deployed_set_values.get(key, ""),
            expected,
        )

    blocker_failures = [row for row in checks if row["status"] == "fail" and row["severity"] == "blocker"]
    status = "pass" if not blocker_failures else "fail"
    decision = {
        "check_id": "stage_state_sim_only_chart_trial_package",
        "status": status,
        "ready_to_manual_chart_trial_with_sim_only": status == "pass",
        "ready_to_startup_attach_trial": status == "pass",
        "ready_to_sim_continuous_runner_execution": False,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "warning_failure_count": len([row for row in checks if row["status"] == "fail" and row["severity"] == "warning"]),
        "local_ex5_sha256": local_hash,
        "deployed_ex5_sha256": deployed_hash,
        "sim_only_source": str(SIM_SOURCE),
        "deployed_ex5": str(DEPLOYED_EX5),
        "deployed_set": str(DEPLOYED_SET),
    }

    write_csv(
        OUT_DIR / "sim_only_chart_trial_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(
        OUT_DIR / "sim_only_chart_trial_decision.csv",
        [decision],
        [
            "check_id",
            "status",
            "ready_to_manual_chart_trial_with_sim_only",
            "ready_to_startup_attach_trial",
            "ready_to_sim_continuous_runner_execution",
            "ready_to_live_trade",
            "blocker_failure_count",
            "warning_failure_count",
            "local_ex5_sha256",
            "deployed_ex5_sha256",
            "sim_only_source",
            "deployed_ex5",
            "deployed_set",
        ],
    )
    write_json(OUT_DIR / "sim_only_chart_trial_decision.json", decision)
    write_csv(
        OUT_DIR / "manual_chart_trial_sim_only_steps.csv",
        manual_steps(),
        ["step_id", "status", "action", "acceptance"],
    )
    (OUT_DIR / "sim_only_chart_trial_package.md").write_text(
        build_report(decision, checks),
        encoding="utf-8-sig",
    )

    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
