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
OUT_DIR = VALIDATION_DIR / "stage_state_live_risk_guard_implementation_20260722"

EA_MQ5 = AUTO_TRADE / "30m2H_Strategy_EA.mq5"
EA_EX5 = AUTO_TRADE / "30m2H_Strategy_EA.ex5"
COMPILE_LOG = AUTO_TRADE / "compile_live_risk_guard_20260722.log"
POLICY_JSON = (
    VALIDATION_DIR
    / "stage_state_live_numeric_risk_policy_proposal_20260722"
    / "live_risk_policy_proposal.json"
)
NONPROD_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_nonprod_mt5_rehearsal_execution_20260721"
    / "nonprod_mt5_rehearsal_decision.json"
)
NONPROD_METRICS_CSV = (
    VALIDATION_DIR
    / "stage_state_nonprod_mt5_rehearsal_execution_20260721"
    / "nonprod_mt5_rehearsal_lifecycle_metrics.csv"
)


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


def read_text_any(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or b"\x00" in raw[:200]:
        return raw.decode("utf-16", errors="ignore")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig", errors="ignore")
    return raw.decode("utf-8", errors="ignore")


def has_pattern(text: str, pattern: str) -> bool:
    return re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL) is not None


def metric(metrics: List[Dict[str, str]], name: str, default: str = "") -> str:
    for row in metrics:
        if row.get("metric") == name:
            return row.get("value", default)
    return default


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


def compile_passed(log_text: str) -> bool:
    return "Result: 0 errors, 0 warnings" in log_text


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reviewed_at = datetime.now().isoformat(timespec="seconds")

    ea_text = EA_MQ5.read_text(encoding="utf-8-sig", errors="ignore")
    compile_text = read_text_any(COMPILE_LOG) if COMPILE_LOG.exists() else ""
    policy = read_json(POLICY_JSON) if POLICY_JSON.exists() else {}
    nonprod = read_json(NONPROD_DECISION_JSON) if NONPROD_DECISION_JSON.exists() else {}
    metrics = read_rows(NONPROD_METRICS_CSV) if NONPROD_METRICS_CSV.exists() else []

    source_checks = [
        check(
            "LIVE-RISK-SRC-001",
            has_pattern(ea_text, r"input\s+bool\s+InpEnableLiveRiskGuards\s*=\s*false"),
            "InpEnableLiveRiskGuards=false found",
            "guard defaults disabled until explicitly enabled",
            note="Prevents silent live/trade behavior change in old set files.",
        ),
        check(
            "LIVE-RISK-SRC-002",
            all(name in ea_text for name in [
                "InpLiveBalanceCap",
                "InpMaxDailyLossUSD",
                "InpMaxDrawdownUSD",
                "InpMaxNewPositionsPerDay",
                "InpMaxSpreadPoints",
                "InpMarginGuardPct",
                "InpLiveMaxLotCap",
                "InpLeverageOverride",
            ]),
            "live risk input set present",
            "all proposed numeric risk knobs represented in EA inputs",
        ),
        check(
            "LIVE-RISK-SRC-003",
            "LiveRiskAccountGuardPass(trigger_tag, signal_src, signal_dir, anchor_time)" in ea_text,
            "account guard called before stage execution",
            "pre-trade account/spread/history guard is on ExecuteSignal path",
        ),
        check(
            "LIVE-RISK-SRC-004",
            all(token in ea_text for token in [
                "CurrentSpreadPoints()",
                "InpMaxSpreadPoints",
                "spread_points > InpMaxSpreadPoints",
            ]),
            "spread guard code present",
            "block new entries above configured spread",
        ),
        check(
            "LIVE-RISK-SRC-005",
            all(token in ea_text for token in [
                "LiveRiskHistoryStats",
                "daily_net <= -InpMaxDailyLossUSD",
                "new_entries_today + InpStageCount > InpMaxNewPositionsPerDay",
            ]),
            "daily loss and daily entry counters present",
            "block new entries after daily risk limit breach",
        ),
        check(
            "LIVE-RISK-SRC-006",
            "InpLiveBalanceCap - equity >= InpMaxDrawdownUSD" in ea_text,
            "drawdown-from-cap guard present",
            "block new entries when equity drawdown reaches configured cap",
        ),
        check(
            "LIVE-RISK-SRC-007",
            all(token in ea_text for token in [
                "InpLiveMaxLotCap",
                "stage_lots_arr[stage] > InpLiveMaxLotCap",
                "live max lot cap",
            ]),
            "per-stage lot cap guard present",
            "block stage lot above configured live cap",
        ),
        check(
            "LIVE-RISK-SRC-008",
            all(token in ea_text for token in [
                "OrderCalcMargin",
                "FallbackMarginEstimate",
                "estimated margin level after signal",
                "est_margin_level_after < InpMarginGuardPct",
            ]),
            "post-signal margin estimate guard present",
            "use broker margin calculation and fail closed when guard is enabled",
        ),
        check(
            "LIVE-RISK-SRC-009",
            "result=LIVE_RISK_BLOCK" in ea_text,
            "diagnostic block log present",
            "blocked entries are visible in EA diagnostics",
        ),
        check(
            "LIVE-RISK-COMPILE-001",
            compile_passed(compile_text),
            "Result: 0 errors, 0 warnings" if compile_passed(compile_text) else "compile pass marker missing",
            "MetaEditor compile log contains 0 errors and 0 warnings",
        ),
        check(
            "LIVE-RISK-COMPILE-002",
            EA_EX5.exists() and EA_EX5.stat().st_size > 0,
            f"exists={EA_EX5.exists()} size={EA_EX5.stat().st_size if EA_EX5.exists() else 0}",
            "compiled EX5 artifact exists",
        ),
    ]

    blockers = [row for row in source_checks if row["severity"] == "blocker" and not row["pass"]]
    compile_ok = compile_passed(compile_text)

    observed_max_lot = float(str(nonprod.get("max_lot", "0") or 0))
    proposed_live_max_lot = float(str(policy.get("max_lot", "0.10") or 0.10))
    nonprod_review = [
        {
            "review_item": "prior_nonprod_rehearsal_status",
            "value": nonprod.get("status", ""),
            "interpretation": "baseline non-production MT5 order lifecycle passed, but it did not enable the new live risk guard inputs",
        },
        {
            "review_item": "prior_nonprod_initial_deposit",
            "value": nonprod.get("initial_deposit", ""),
            "interpretation": "matches the requested 2000 demo balance cap for rehearsal context",
        },
        {
            "review_item": "prior_nonprod_final_balance",
            "value": nonprod.get("final_balance", ""),
            "interpretation": "baseline rehearsal profit/loss reference only; not a guard-enabled result",
        },
        {
            "review_item": "prior_nonprod_trade_ledger_rows",
            "value": nonprod.get("trade_ledger_rows", ""),
            "interpretation": "ledger exists for lifecycle review and future guard-enabled comparison",
        },
        {
            "review_item": "prior_nonprod_sl_rows",
            "value": metric(metrics, "sl_rows"),
            "interpretation": "stop-loss outcomes are present for post-guard comparison",
        },
        {
            "review_item": "observed_lot_vs_proposed_cap",
            "value": f"observed_max_lot={observed_max_lot:.2f}; proposed_live_cap={proposed_live_max_lot:.2f}",
            "interpretation": "prior run stayed below the proposed cap, but this must be rehearsed with InpEnableLiveRiskGuards=true",
        },
    ]

    decision = {
        "decision_time": reviewed_at,
        "check_id": "stage_state_live_risk_guard_implementation",
        "status": (
            "live_risk_guard_implemented_compile_passed_guard_rehearsal_pending"
            if compile_ok and not blockers
            else "live_risk_guard_implementation_blocked"
        ),
        "source_check_count": len(source_checks),
        "source_check_fail_count": len(blockers),
        "compile_passed": compile_ok,
        "mq5_path": str(EA_MQ5),
        "ex5_path": str(EA_EX5),
        "compile_log_path": str(COMPILE_LOG),
        "metaeditor_process_exit_code_note": "tool output showed ExitCode=1, but compile log is the controlling evidence and reports 0 errors, 0 warnings",
        "live_gap_006_code_implemented": compile_ok and not blockers,
        "live_gap_006_closed": False,
        "ready_to_live_trade": False,
        "why_not_closed": [
            "numeric risk policy still needs explicit final confirmation after code implementation",
            "new guard inputs have not yet been exercised in a guard-enabled non-production MT5 rehearsal",
            "live alert and emergency stop handling remain outside this code-only check",
        ],
        "recommended_next_action": "prepare_and_run_guard_enabled_nonprod_mt5_rehearsal_then_update_live_gate",
    }

    write_csv(
        OUT_DIR / "live_risk_guard_implementation_checks.csv",
        source_checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(
        OUT_DIR / "live_risk_guard_prior_nonprod_coverage_review.csv",
        nonprod_review,
        ["review_item", "value", "interpretation"],
    )
    write_csv(
        OUT_DIR / "live_risk_guard_implementation_decision.csv",
        [decision],
        [
            "decision_time",
            "check_id",
            "status",
            "source_check_count",
            "source_check_fail_count",
            "compile_passed",
            "live_gap_006_code_implemented",
            "live_gap_006_closed",
            "ready_to_live_trade",
            "recommended_next_action",
        ],
    )
    write_json(OUT_DIR / "live_risk_guard_implementation_decision.json", decision)

    report = f"""# LIVE-GAP-006 EA Live Risk Guard Implementation Review

Generated: {reviewed_at}

## Decision

- Status: `{decision["status"]}`
- Compile: `{"PASS" if compile_ok else "FAIL"}`
- LIVE-GAP-006 code implemented: `{decision["live_gap_006_code_implemented"]}`
- LIVE-GAP-006 closed: `false`
- Ready to live trade: `false`

## What changed

- Added explicit live/pre-live guard switch with default `InpEnableLiveRiskGuards=false`.
- Added numeric guard inputs for balance cap, daily loss, drawdown, daily entries, spread, margin level, per-stage lot cap, and leverage override.
- Connected guard checks to the `ExecuteSignal` path before the split-stage orders are sent.
- Replaced the old hardcoded 1:500 margin estimate with `OrderCalcMargin`, while retaining a fallback estimate for diagnostics.
- Guard-enabled mode blocks new entries fail-closed and writes `LIVE_RISK_BLOCK` diagnostics.

## Current Evidence

- MQ5: `{EA_MQ5}`
- EX5: `{EA_EX5}`
- Compile log: `{COMPILE_LOG}`
- Compile log result: `{"0 errors, 0 warnings" if compile_ok else "pass marker missing"}`
- Prior non-production rehearsal: `{nonprod.get("status", "")}`
- Prior rehearsal max lot: `{observed_max_lot:.2f}`
- Proposed live max lot cap: `{proposed_live_max_lot:.2f}`

## Why LIVE-GAP-006 Is Not Closed Yet

1. The code now supports the numeric risk policy, but the final policy values still need explicit confirmation after implementation.
2. The prior MT5 rehearsal did not run with `InpEnableLiveRiskGuards=true`, so it proves baseline order lifecycle, not guard behavior.
3. The broader live gate still requires alert evidence and emergency stop handling evidence.

## Next Action

Prepare and run a non-production MT5 Strategy Tester rehearsal using the compiled EX5 with `InpEnableLiveRiskGuards=true`, then update the live gate from that evidence.
"""
    (OUT_DIR / "live_risk_guard_implementation_review.md").write_text(report, encoding="utf-8-sig")
    return 0 if compile_ok and not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
