# -*- coding: utf-8 -*-
"""M4.4b 生成 expected trade ledger（405 笔口径，与 EA CSV 账本同格式）。
黄金（Gold_DataEvent_EA）：V1_T2h 全事件过滤 + StopSpec 5-35 美元 → 逐段行 stage=1/2/3，
      pnl_points=价格单位盈亏（EA RecordStageExit 口径；0.01 手下 pnl_usd≈pnl_points）。
      列：signal_time/entry_time/dir/mode/stage/open_time/entry/stop/exit_time/exit_price/
          reason/pnl_points/pnl_usd/virtual_balance
原油（Oil_DataEvent_EA）：way门+pre_cross + V1_T1h 全事件过滤 + 止损 0.1-1.0% → 单行/笔，
      列：signal_time/entry_time/dir/entry/stop/stop_pct/exit_time/exit_price/reason/
          pnl_points/pnl_usd/virtual_balance（pnl_points=价格单位盈亏，EA RecordExit 口径）
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "validate"))
from backtest_baseline import gen_signals_gold_ea  # noqa: E402
from variants import simulate_with_variant, load_blackout_events  # noqa: E402

BALANCE = 500.0
# EA 运行时过滤（M4 对齐 v1：并发3 + 损失冷却 + 同向冷却，与 EA 默认一致）
EA_FILTERS = dict(max_open=3, loss_cd_loss=2, loss_cd_hours=120, same_dir_cd_bars=3)


def fmt_time(t) -> str:
    return pd.Timestamp(t).isoformat(sep=" ")


def make_gold_ledger() -> pd.DataFrame:
    ctx = pd.read_csv(ROOT / "data" / "processed" / "gold_context.csv", parse_dates=["time"])
    ctx["time"] = pd.to_datetime(ctx["time"], utc=True)
    # M4 对齐 v1：EA 同口径信号（merged 方向 + pre_cross 修正 + post_n 止损）
    df = gen_signals_gold_ea(ctx)
    et = load_blackout_events()
    # 405 笔口径：StopSpec 5-35 美元 + V1_T2h 事件过滤 + EA 运行时过滤，逐段明细
    trades = simulate_with_variant(df, "sig", et, "v1", v1_hours=2, trade_unit="R",
                                   stop_spec=(5.0, 35.0), with_detail=True, **EA_FILTERS)
    rows = []
    bal = BALANCE
    for t in trades:
        for st in t["stages"]:
            pnl_pts = st["pnl_price"]
            bal += pnl_pts  # 0.01 手下 XAUUSD pnl_usd≈pnl_pts（contract=100）
            rows.append({
                "signal_time": fmt_time(t["signal_time"]),
                "entry_time": fmt_time(t["entry_time"]),
                "dir": "BUY" if t["dir"] == "L" else "SELL",
                "mode": t["mode"],
                "stage": st["stage"],
                "open_time": fmt_time(t["entry_time"]),
                "entry": round(t["entry"], 5),
                "stop": round(t["stop"], 5),
                "exit_time": fmt_time(st["exit_time"]),
                "exit_price": round(st["exit_price"], 5),
                "reason": st["ea_reason"],
                "pnl_points": round(pnl_pts, 5),
                "pnl_usd": round(pnl_pts, 5),
                "virtual_balance": round(bal, 5),
            })
    return pd.DataFrame(rows)


def make_oil_ledger() -> pd.DataFrame:
    # 复用 canonical way门管线（backtest_oil_gate.py，--variant v1 --hours 1 = EA 事件门 T=1h）
    # 注：沙箱禁止子进程管道捕获，使用继承 stdio
    subprocess.run([sys.executable, str(ROOT / "scripts" / "validate" / "backtest_oil_gate.py"),
                    "--variant", "v1", "--hours", "1"], check=True,
                   cwd=str(ROOT))
    tdf = pd.read_csv(ROOT / "data" / "validation" / "baseline_oil_trades_v1_1.0h.csv",
                      parse_dates=["signal_time", "entry_time", "exit_time"])
    rows = []
    bal = BALANCE
    for _, t in tdf.iterrows():
        is_long = t["dir"] == "L"
        pnl_pts = (t["exit_price"] - t["entry"]) if is_long else (t["entry"] - t["exit_price"])
        bal += pnl_pts  # 0.01 手下 USOIL pnl_usd≈pnl_pts（contract=1000）
        reason = {"sl": "SL hit", "rev": "opposite cross", "eod": "end of data"}.get(t["exit_reason"], t["exit_reason"])
        rows.append({
            "signal_time": fmt_time(t["signal_time"]),
            "entry_time": fmt_time(t["entry_time"]),
            "dir": "BUY" if is_long else "SELL",
            "entry": round(t["entry"], 5),
            "stop": round(t["stop"], 5),
            "stop_pct": round(t["stop_pct"], 3),
            "exit_time": fmt_time(t["exit_time"]),
            "exit_price": round(t["exit_price"], 5),
            "reason": reason,
            "pnl_points": round(pnl_pts, 5),
            "pnl_usd": round(pnl_pts, 5),
            "virtual_balance": round(bal, 5),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    gold = make_gold_ledger()
    gold.to_csv(ROOT / "data" / "validation" / "expected_ledger_gold.csv", index=False, encoding="utf-8-sig")
    print(f"[gold expected] {len(gold)} rows (signals={gold['entry_time'].nunique()})")
    oil = make_oil_ledger()
    oil.to_csv(ROOT / "data" / "validation" / "expected_ledger_oil.csv", index=False, encoding="utf-8-sig")
    print(f"[oil expected] {len(oil)} rows")
