from __future__ import annotations


import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
AUTO_TRADE = ROOT / "auto_trade"
OUT_DIR = VALIDATION_DIR / "stage_state_live_risk_guard_leverage_format_probe_20260722"

SOURCE_INI = AUTO_TRADE / "30m2H_Strategy_EA.live_risk_guard_rehearsal_20260601_20260707_20260722.ini"
PROBE_INI = AUTO_TRADE / "30m2H_Strategy_EA.live_risk_guard_rehearsal_20260601_20260707_20260722_levfmt.ini"
PROBE_REPORT = AUTO_TRADE / "live_risk_guard_rehearsal_20260601_20260707_20260722_levfmt_report.xml"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().isoformat(timespec="seconds")
    text = SOURCE_INI.read_text(encoding="utf-8-sig")
    text = text.replace("Leverage=2000", "Leverage=1:2000", 1)
    text = text.replace(str(PROBE_REPORT).replace("_levfmt_report.xml", "_report.xml"), str(PROBE_REPORT))
    if str(PROBE_REPORT) not in text:
        text = text.replace(
            "Report=F:\\use_code\\MTA5_l\\auto_trade\\live_risk_guard_rehearsal_20260601_20260707_20260722_report.xml",
            f"Report={PROBE_REPORT}",
        )
    text = text.replace(
        "; 30m2H guard-enabled non-production MT5 Strategy Tester rehearsal config",
        "; 30m2H guard-enabled leverage-format probe config",
    )
    text = text.replace(
        "; Scope: tester/demo rehearsal only; not real-money live trading.",
        "; Scope: tester/demo leverage-format probe only; not real-money live trading.",
    )
    PROBE_INI.write_text(text, encoding="utf-8-sig")

    decision = {
        "decision_time": generated_at,
        "status": "leverage_format_probe_ini_ready",
        "source_ini": str(SOURCE_INI),
        "probe_ini": str(PROBE_INI),
        "probe_change": "Tester Leverage changed from 2000 to 1:2000",
        "ready_to_live_trade": False,
        "recommended_next_action": "run_terminal64_with_probe_ini_then_collect_effective_leverage",
    }
    write_json(OUT_DIR / "live_risk_guard_leverage_format_probe_package.json", decision)
    (OUT_DIR / "live_risk_guard_leverage_format_probe_package.md").write_text(
        "\n".join(
            [
                "# LIVE-GAP-006 Leverage Format Probe Package",
                "",
                f"Generated: {generated_at}",
                "",
                f"- Source INI: `{SOURCE_INI}`",
                f"- Probe INI: `{PROBE_INI}`",
                "- Change: `Leverage=2000` -> `Leverage=1:2000`",
                "- Boundary: non-production tester probe only; not live trading.",
                "",
            ]
        ),
        encoding="utf-8-sig",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
