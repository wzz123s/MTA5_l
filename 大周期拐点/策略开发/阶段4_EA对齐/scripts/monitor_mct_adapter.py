# -*- coding: utf-8 -*-
"""monitor_mct_adapter.py —— MCT 大周期拐点策略监控适配（阶段5 模拟盘）。

数据源优先级：
  1. 实时模拟盘 ledger（EA Files 导出 MCT_trade_ledger.csv，SimMode 虚拟盘）
  2. 回测基线兜底（阶段4 因果化 expected ledger 26 笔，历史已平仓）
标准列（monitor_all_strategies.per_trade_summary 所需）：
  signal_time / dir / stage / mode / entry / stop / stop_distance /
  stage_pnl / stage_exit_time / stage_exit_price / stage_reason
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]   # 阶段4_EA对齐/
TERMINAL_FILES = Path(os.environ.get(
    "MCT_LIVE_DIR",
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Files",
))

ST_COLS = ["signal_time", "dir", "stage", "mode", "entry", "stop", "stop_distance",
           "stage_pnl", "stage_exit_time", "stage_exit_price", "stage_reason"]
PTS_PER_PRICE = 1000.0   # USOILm 1 价格单位 = 1000 点


def _read_live_ledger():
    f = TERMINAL_FILES / "MCT_trade_ledger.csv"
    if not f.exists():
        return None
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            df = pd.read_csv(f, encoding=enc, on_bad_lines="skip")
            return df if len(df) else None
        except Exception:
            continue
    return None


def _st_from_ledger(led):
    if led is None or led.empty:
        return pd.DataFrame(columns=ST_COLS)
    st = led.copy()
    st["signal_time"] = pd.to_datetime(st["signal_time"], errors="coerce")
    st["stage_exit_time"] = pd.to_datetime(st["exit_time"], errors="coerce")
    st["dir"] = st["dir"].astype(str).str.upper().map({"BUY": "L", "SELL": "S"})
    st["entry"] = pd.to_numeric(st["entry"], errors="coerce")
    st["stop"] = pd.to_numeric(st["stop"], errors="coerce")
    st["stop_distance"] = (st["entry"] - st["stop"]).abs() * PTS_PER_PRICE
    st["stage_pnl"] = pd.to_numeric(st["pnl_points"], errors="coerce") * PTS_PER_PRICE
    st["stage_exit_price"] = pd.to_numeric(st["exit_price"], errors="coerce")
    st["stage_reason"] = st["reason"].astype(str)
    st["stage"] = 1
    st["mode"] = "mct_hybrid"
    return st[ST_COLS].dropna(subset=["signal_time", "dir"])


def build_mct():
    """实时 ledger 优先，回退阶段4 因果 expected ledger（历史 26 笔）。"""
    live = _read_live_ledger()
    if live is not None and len(live) > 0:
        st = _st_from_ledger(live)
        if len(st) > 0:
            return st, st, pd.DataFrame({"bar_close_time": st["stage_exit_time"]})
    exp = ROOT / "data" / "validation" / "expected_ledger_mct_oil.csv"
    if exp.exists():
        led = pd.read_csv(exp)
        st = _st_from_ledger(led)
        return st, st, pd.DataFrame({"bar_close_time": pd.to_datetime(["2026-09-01"])})
    empty = pd.DataFrame(columns=ST_COLS)
    return empty, empty, pd.DataFrame({"bar_close_time": pd.to_datetime([pd.Timestamp.now().normalize()])})


def live_snapshot():
    """实时模拟盘快照 markdown（EA ledger 口径）。"""
    led = _read_live_ledger()
    led_f = TERMINAL_FILES / "MCT_trade_ledger.csv"
    lines = []
    if led is None or len(led) == 0:
        if led_f.exists():
            lines.append("- 口径: **回测基线兜底（实时 ledger 已生成文件但尚无已平仓记录——EA 已挂载，等待首笔虚拟平仓）**")
            lines.append("- 实时账本文件: 已生成（仅表头，等待首笔平仓写入 MCT_trade_ledger.csv）")
        else:
            lines.append("- 口径: **回测基线兜底（实时 ledger 暂无数据行——EA 需挂载到 USOILm 图表后随行情写入）**")
            lines.append("- 实时账本文件: 尚未生成（终端 MQL5\\Files\\MCT_trade_ledger.csv）")
        return chr(10).join(lines)
    st = _st_from_ledger(led)
    bal = float(led["virtual_balance"].iloc[-1]) if "virtual_balance" in led else 0.0
    lines.append("- 口径: **实时模拟盘 ledger（EA Files 导出）**｜账本 " + str(len(st)) + " 笔｜虚拟余额 $" + f"{bal:,.2f}")
    last = st.tail(3)
    for _, r in last.iterrows():
        lines.append("  - " + r["signal_time"].strftime("%Y-%m-%d %H:%M") + " " + r["dir"] +
                     " 入" + f"{r['entry']:.2f}" + " 停" + f"{r['stop']:.2f}" +
                     " 出" + f"{r['stage_exit_price']:.2f}" + " (" + str(r["stage_reason"]) + ") 点数" + f"{r['stage_pnl']:+.0f}")
    return chr(10).join(lines)


if __name__ == "__main__":
    st, _, tf = build_mct()
    print("MCT st rows:", len(st))
    print(live_snapshot())
