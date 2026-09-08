# -*- coding: utf-8 -*-
"""USOIL2H CrossConfirm 正式监控（因果口径）。

读取实盘 EA 输出的 ledger/signals CSV（DAD3B8CC 终端 MQL5\Files），
汇总交易/净值/最近信号，并与因果基线（cross_confirm_causal, 2021+ = 53 笔）对照。
只读，不下单。

用法:
  python monitor_usoil2h_crossconfirm.py
"""
from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path

ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY = ROOT / "原油" / "原油2H策略"
TERMINAL_FILES = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Files"
)
TESTER_FILES = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65"
    r"\Agent-127.0.0.1-3000\MQL5\Files"
)
EXPECTED_CAUSAL = (
    STRATEGY / "auto_trade" / "python_expected_2020_2026"
    / "python_expected_usoil2h_crossconfirm_causal_2021_2026.csv"
)
MONITOR_DIR = STRATEGY / "监控"


def read_csv(path: Path):
    if not path.exists():
        return []
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def norm_time(value: str) -> dt.datetime:
    s = str(value).strip()
    for fmt in ("%Y.%m.%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return dt.datetime.strptime(s[:16], fmt)
        except ValueError:
            continue
    raise ValueError(s)


def main() -> None:
    MONITOR_DIR.mkdir(parents=True, exist_ok=True)
    live_ledger = read_csv(TERMINAL_FILES / "USOIL2H_crossconfirm_trade_ledger.csv")
    live_signals = read_csv(TERMINAL_FILES / "USOIL2H_crossconfirm_signals_export.csv")
    tester_ledger = read_csv(TESTER_FILES / "USOIL2H_crossconfirm_trade_ledger.csv")
    expected = read_csv(EXPECTED_CAUSAL)

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state = {
        "last_update": now,
        "instrument": "USOILm",
        "ea": "USOIL2H_CrossConfirm_EA v5 (SimMode=true)",
        "basis": "cross_confirm_causal (因果口径, 无 lookahead)",
        "live_ledger_path": str(TERMINAL_FILES / "USOIL2H_crossconfirm_trade_ledger.csv"),
        "live_trade_count": len(live_ledger),
        "live_signals": len([r for r in live_signals if r.get("kind") == "signal"]),
        "live_balance": live_ledger[-1].get("virtual_balance") if live_ledger else None,
        "last_live_signal_time": live_ledger[-1].get("signal_time") if live_ledger else None,
        "expected_2021_plus": len(expected),
        "tester_ledger_count": len(tester_ledger),
        "tester_ledger_time": (
            dt.datetime.fromtimestamp(
                (TESTER_FILES / "USOIL2H_crossconfirm_trade_ledger.csv").stat().st_mtime
            ).strftime("%Y-%m-%d %H:%M:%S")
            if (TESTER_FILES / "USOIL2H_crossconfirm_trade_ledger.csv").exists()
            else None
        ),
        "warning": None,
    }

    notes = []
    if len(live_ledger) == 0:
        notes.append("实盘 EA 尚无成交（表头已生成；市场休市/无信号属正常）。")
    if len(expected) != 53:
        notes.append(f"注意：因果基线期望笔数={len(expected)}（应为 53）。")
    if len(tester_ledger) != len(expected):
        notes.append(
            f"Tester 台账 {len(tester_ledger)} 笔 ≠ 因果期望 {len(expected)} 笔，需核对。"
        )

    lines = [
        "# USOIL2H CrossConfirm 正式监控（因果口径）",
        "",
        f"> 更新：{now}",
        "> 口径：`cross_confirm_causal`（确认值截至 i+2 因果计算，无 lookahead）；"
        "lookahead 变体（cross_confirm / cross_pre_confirm）PF 高估，仅参考。",
        "",
        "## 状态",
        "",
        f"- 实盘 EA：{state['ea']}",
        f"- 实盘成交笔数：**{state['live_trade_count']}**（期望基线 2021+ = {state['expected_2021_plus']} 笔）",
        f"- 实盘信号笔数：{state['live_signals']}",
        f"- 虚拟余额：{state['live_balance'] or '—'}",
        f"- 最近成交：{state['last_live_signal_time'] or '—'}",
        f"- Tester 冒烟台账：{state['tester_ledger_count']} 笔（{state['tester_ledger_time'] or '—'}，"
        f"与因果期望 {'一致' if len(tester_ledger) == len(expected) else '不一致'}）",
        "",
        "## 提示",
        "",
    ]
    for n in notes:
        lines.append(f"- {n}")
    if not notes:
        lines.append("- 无异常。")

    state["notes"] = notes
    (MONITOR_DIR / "monitor_state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (MONITOR_DIR / "monitor_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwrote: {MONITOR_DIR / 'monitor_state.json'} / monitor_report.md")


if __name__ == "__main__":
    main()
