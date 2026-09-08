from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_stop_flag_removal_manual_loading_approval_request_20260723"

LOADING_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_exact_mt5_ea_live_loading_package_20260723"
    / "exact_mt5_ea_live_loading_decision.json"
)
LOADING_MANIFEST_JSON = (
    VALIDATION_DIR
    / "stage_state_exact_mt5_ea_live_loading_package_20260723"
    / "exact_mt5_ea_live_loading_manifest.json"
)
EMERGENCY_STOP_FLAG = ROOT / "auto_trade" / "EMERGENCY_STOP.flag"
RUNNER_STOP_FLAG = ROOT / "auto_trade" / "RUNNER_STOP.flag"


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


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().isoformat(timespec="seconds")

    loading = read_json(LOADING_DECISION_JSON)
    manifest = read_json(LOADING_MANIFEST_JSON)
    stop_flags_present = EMERGENCY_STOP_FLAG.exists() and RUNNER_STOP_FLAG.exists()
    loading_package_ready = (
        loading.get("status") == "exact_live_loading_package_ready_fail_closed"
        and loading.get("ready_for_live_loading_package") is True
        and loading.get("ready_to_live_trade") is False
        and loading.get("orders_placed") is False
        and loading.get("runner_executed") is False
        and loading.get("ea_loaded") is False
        and loading.get("stop_flags_removed") is False
    )

    approval_template = {
        "source": "stop_flag_removal_manual_ea_loading_approval_template_not_signed",
        "generated_at": generated_at,
        "operator_alias": manifest.get("operator_alias", "owner_local"),
        "account_alias": manifest.get("account_alias", "MT5_ACCOUNT_REDACTED"),
        "server": manifest.get("server", ""),
        "symbol": manifest.get("symbol", "XAUUSDm"),
        "timeframe": manifest.get("timeframe", "M30"),
        "ea_ex5": manifest.get("ea_ex5", ""),
        "set_snapshot": manifest.get("live_loading_set_snapshot", ""),
        "approval_items": {
            "remove_EMERGENCY_STOP_flag": False,
            "remove_RUNNER_STOP_flag": False,
            "manual_load_EA_on_XAUUSDm_M30": False,
            "confirm_MT5_AutoTrading_can_be_enabled_after_EA_loaded": False,
            "confirm_owner_local_watches_alerts_and_reconciliation": False,
            "confirm_stop_if_unexpected_position_order_or_log_error": False,
        },
        "ready_to_live_trade": False,
        "do_not_include": [
            "full account number",
            "password",
            "investor password",
            "api token",
            "secret key",
        ],
    }

    checklist_rows = [
        {
            "step_no": 1,
            "phase": "approval_before_action",
            "action": "Confirm exact loading package is ready",
            "expected": "exact_live_loading_package_ready_fail_closed",
            "current_status": loading.get("status", ""),
            "operator_required": False,
        },
        {
            "step_no": 2,
            "phase": "approval_before_action",
            "action": "Explicitly approve removing EMERGENCY_STOP.flag",
            "expected": "approval true in signed template",
            "current_status": False,
            "operator_required": True,
        },
        {
            "step_no": 3,
            "phase": "approval_before_action",
            "action": "Explicitly approve removing RUNNER_STOP.flag",
            "expected": "approval true in signed template",
            "current_status": False,
            "operator_required": True,
        },
        {
            "step_no": 4,
            "phase": "manual_mt5_loading",
            "action": "Manually load EA on XAUUSDm/M30 with the approved set snapshot",
            "expected": "separate loading evidence after approval",
            "current_status": "not_started",
            "operator_required": True,
        },
        {
            "step_no": 5,
            "phase": "after_loading",
            "action": "Collect post-load read-only evidence",
            "expected": "EA attached, inputs visible, no unexpected exposure",
            "current_status": "pending",
            "operator_required": True,
        },
    ]

    checks = [
        {
            "check_id": "loading_package_ready",
            "status": "pass" if loading_package_ready else "fail",
            "pass": loading_package_ready,
            "actual": loading.get("status", ""),
            "expected": "exact_live_loading_package_ready_fail_closed",
            "severity": "blocker",
            "note": "",
        },
        {
            "check_id": "stop_flags_present_before_approval",
            "status": "pass" if stop_flags_present else "fail",
            "pass": stop_flags_present,
            "actual": stop_flags_present,
            "expected": True,
            "severity": "blocker",
            "note": "Stop flags must remain until explicit approval is applied.",
        },
        {
            "check_id": "approval_template_unsigned",
            "status": "pass",
            "pass": True,
            "actual": "all loading approval booleans false",
            "expected": "unsigned request only",
            "severity": "blocker",
            "note": "This request package does not authorize action by itself.",
        },
    ]
    blocker_failures = [row for row in checks if row["severity"] == "blocker" and not row["pass"]]
    decision = {
        "decision_time": generated_at,
        "check_id": "stage_state_stop_flag_removal_manual_loading_approval_request",
        "status": (
            "stop_flag_removal_manual_loading_approval_request_ready_waiting_for_explicit_approval"
            if not blocker_failures
            else "stop_flag_removal_manual_loading_approval_request_blocked"
        ),
        "loading_package_ready": loading_package_ready,
        "stop_flags_present": stop_flags_present,
        "approval_items_signed": 0,
        "approval_items_required": len(approval_template["approval_items"]),
        "orders_placed": False,
        "runner_executed": False,
        "ea_loaded": False,
        "stop_flags_removed": False,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "recommended_next_action": "operator_explicitly_approves_stop_flag_removal_and_manual_ea_loading_or_keep_blocked",
    }

    write_json(OUT_DIR / "stop_flag_removal_manual_loading_approval_template.json", approval_template)
    write_csv(
        OUT_DIR / "stop_flag_removal_manual_loading_checklist.csv",
        checklist_rows,
        ["step_no", "phase", "action", "expected", "current_status", "operator_required"],
    )
    write_csv(
        OUT_DIR / "stop_flag_removal_manual_loading_precheck.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(
        OUT_DIR / "stop_flag_removal_manual_loading_approval_request_decision.csv",
        [decision],
        list(decision.keys()),
    )
    write_json(OUT_DIR / "stop_flag_removal_manual_loading_approval_request_decision.json", decision)

    report = f"""# Stop Flag Removal And Manual MT5 EA Loading Approval Request

Generated: {generated_at}

## Current State

- Loading package ready: `{loading_package_ready}`
- Stop flags present: `{stop_flags_present}`
- Account alias/server: `{manifest.get("account_alias")} / {manifest.get("server")}`
- Symbol/timeframe: `{manifest.get("symbol")} / {manifest.get("timeframe")}`
- EA EX5: `{manifest.get("ea_ex5")}`
- Set snapshot: `{manifest.get("live_loading_set_snapshot")}`
- Ready to live trade: `false`

## Important Boundary

This request package does not remove stop flags, load the EA, enable MT5 AutoTrading, start a runner, or place orders.

## Required Explicit Approval Text

To continue, the operator must explicitly approve all six action items with non-secret text. Example:

```text
operator_alias: owner_local
批准移除 EMERGENCY_STOP.flag 和 RUNNER_STOP.flag。
批准手动加载 MT5 EA 到 XAUUSDm / M30。
批准加载后可按策略开启 MT5 AutoTrading。
确认 owner_local 继续监控告警与对账，发现异常立即停止。
```

Without that explicit approval, the system remains fail-closed.
"""
    (OUT_DIR / "stop_flag_removal_manual_loading_approval_request.md").write_text(
        report,
        encoding="utf-8-sig",
    )
    return 0 if not blocker_failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
