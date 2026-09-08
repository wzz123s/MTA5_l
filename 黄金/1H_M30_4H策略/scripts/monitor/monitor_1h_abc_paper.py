# -*- coding: utf-8 -*-

"""Read-only paper monitor for the 1H_M30_4H A+B+C candidate (5-35pt, bias5>=0.6%).

No orders are placed. Each run:
  1. (default) refreshes the strategy raw data from the local MT5 terminal
     (chunked copy_rates_range; source_id = 1h_m30_4h_live).
  2. recomputes the full A+B+C pipeline on all closed bars,
  3. rewrites a snapshot: trade ledger, equity curves (0.5% / 1% risk),
     open positions, and a human-readable report,
  4. reports trades that appeared since the previous run.

Usage:
  python "黄金/1H_M30_4H策略/scripts/monitor/monitor_1h_abc_paper.py"            # refresh + snapshot
  python "黄金/1H_M30_4H策略/scripts/monitor/monitor_1h_abc_paper.py" --no-refresh  # use existing data
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)


import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mt5.mt5_history import export_history_bundle  # noqa: E402
from experiment_1h_m30_4h_variants_20260813 import (  # noqa: E402
    SPEC_5_35,
    add_m30_state,
    attach_side_extreme,
    build_three_opportunities,
    markdown_table,
    metric,
    pool_mask,
    replay_three_stage,
    replay_signals,
    third_filter_mask,
)
from replay_1h_bias55_h1_stop_optimization import load_frames  # noqa: E402
from replay_1h_way_momentum_filter_scan import add_h1_way_and_momentum  # noqa: E402


STRATEGY = "1H_M30_4H"
STRATEGY_DIR = ROOT / "黄金" / f"{STRATEGY}策略"
LIVE_SOURCE_ID = "1h_m30_4h_live"
BIAS5_THRESHOLD = 0.6
OUT_DIR = (
    STRATEGY_DIR
    / "data"
    / "validation"
    / "experiments_20260813"
    / "candidate_5_35_bias5_0p6_20260814"
    / "monitor"
)
STAGE_UNITS = {1: 0.5, 2: 1.0, 3: 1.5}
START_CAPITAL = 500.0
RISK_LEVELS = [0.5, 1.0]


def refresh_data() -> dict:
    today = datetime.now(timezone.utc).date().isoformat()
    return export_history_bundle(
        strategy=STRATEGY,
        strategy_dir=STRATEGY_DIR,
        symbol="XAUUSDm",
        timeframes=["M30", "H1", "H4"],
        date_from="2020-01-01",
        date_to=today,
        source_id=LIVE_SOURCE_ID,
    )


def build_pipeline(m30, h1_way, h4, m30_state):
    sig = build_three_opportunities(m30, spec_lo=SPEC_5_35[0], spec_hi=SPEC_5_35[1])
    replayed = replay_signals(sig, m30)
    enriched = attach_side_extreme(replayed, h1_way, h4)
    enriched["entry_bar_idx"] = pd.to_numeric(enriched["entry_bar_idx"], errors="coerce").astype(int)
    mask = pool_mask(enriched) & third_filter_mask(enriched)
    bias5 = pd.to_numeric(enriched["side_extreme_bias5_h4sma_pct"], errors="coerce")
    side = enriched["dir"].astype(str).str.upper()
    mask &= (side.eq("S") & bias5.ge(BIAS5_THRESHOLD)) | (side.eq("L") & bias5.le(-BIAS5_THRESHOLD))
    trades = enriched.loc[mask].copy().reset_index(drop=True)
    trades["entry_bar_idx"] = pd.to_numeric(trades["entry_bar_idx"], errors="coerce").astype(int)
    st = replay_three_stage(m30_state, trades)
    return trades, st, enriched


def simulate_equity(st: pd.DataFrame, risk_pct: float) -> pd.DataFrame:
    rows = []
    balance = START_CAPITAL
    peak = START_CAPITAL
    max_dd = 0.0
    for (signal_time, dir_), group in st.groupby(["signal_time", "dir"], sort=True):
        risk_usd = balance * risk_pct / 100.0
        pnl_usd = 0.0
        for _, r in group.iterrows():
            stop_pts = float(r["stop_distance"])
            if stop_pts <= 0 or not np.isfinite(stop_pts):
                continue
            unit_lot = risk_usd / (3.0 * stop_pts * 10.0)
            unit_lot = float(np.clip(unit_lot, 0.01, 10.0))
            lot = unit_lot * STAGE_UNITS[int(r["stage"])]
            pnl_usd += lot * float(r["stage_pnl"]) * 10.0
        balance += pnl_usd
        peak = max(peak, balance)
        max_dd = max(max_dd, peak - balance)
        rows.append(
            {
                "signal_time": pd.Timestamp(signal_time),
                "dir": dir_,
                "pnl_usd": pnl_usd,
                "balance": balance,
                "peak": peak,
                "max_dd_usd": max_dd,
                "max_dd_pct": max_dd / peak * 100.0 if peak > 0 else 0.0,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-refresh", action="store_true", help="Skip MT5 data refresh.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not args.no_refresh:
        manifest = refresh_data()
        print("data refreshed:", manifest["source_id"], "bars:", [f["rows"] for f in manifest["files"]])

    _, m30, h1, contexts = load_frames()
    h4 = contexts["4H"]
    h1_way = add_h1_way_and_momentum(h1)
    m30_state = add_m30_state(m30)
    trades, st, enriched = build_pipeline(m30, h1_way, h4, m30_state)

    latest_bar_close = pd.to_datetime(m30["bar_close_time"]).max()
    st = st.copy()
    st["signal_time"] = pd.to_datetime(st["signal_time"])
    st["stage_exit_time"] = pd.to_datetime(st["stage_exit_time"])
    st["_w"] = st["stage_pnl"].astype(float) * st["stage"].map(STAGE_UNITS)
    per = st.groupby(["signal_time", "dir"], sort=True).agg(
        entry=("entry", "first"),
        stop=("stop", "first"),
        stop_distance=("stop_distance", "first"),
        mode=("mode", "first"),
        weighted_pts=("_w", "sum"),
        stage3_exit_time=("stage_exit_time", lambda x: x.iloc[-1]),
        stage3_exit_price=("stage_exit_price", lambda x: x.iloc[-1]),
        stage3_reason=("stage_reason", lambda x: x.iloc[-1]),
    ).reset_index()
    per["year"] = per["signal_time"].dt.year
    per["open"] = per["stage3_exit_time"] > latest_bar_close
    per = per.sort_values("signal_time").reset_index(drop=True)

    eq05 = simulate_equity(st, 0.5)
    eq10 = simulate_equity(st, 1.0)

    state_path = OUT_DIR / "monitor_state.json"
    prev_max_signal = None
    prev_total = 0
    if state_path.exists():
        try:
            prev = json.loads(state_path.read_text(encoding="utf-8"))
            prev_max_signal = prev.get("last_signal_time")
            prev_total = int(prev.get("total_trades", 0))
        except Exception:
            pass

    new_trades = per
    if prev_max_signal:
        new_trades = per[per["signal_time"] > pd.Timestamp(prev_max_signal)]

    m = metric(per["weighted_pts"])
    state = {
        "run_time_utc": datetime.now(timezone.utc).isoformat(),
        "data_last_bar_close": latest_bar_close.isoformat(),
        "total_trades": int(len(per)),
        "last_signal_time": per["signal_time"].max().isoformat() if len(per) else None,
        "open_positions": int(per["open"].sum()),
        "new_trades_since_last_run": int(len(new_trades)),
        "overall_pf": float(m["pf"]),
        "equity_0_5pct": float(eq05["balance"].iloc[-1]) if len(eq05) else START_CAPITAL,
        "equity_1pct": float(eq10["balance"].iloc[-1]) if len(eq10) else START_CAPITAL,
    }
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    per.to_csv(OUT_DIR / "trades_snapshot.csv", index=False, encoding="utf-8-sig")
    eq05.to_csv(OUT_DIR / "equity_0_5pct.csv", index=False, encoding="utf-8-sig")
    eq10.to_csv(OUT_DIR / "equity_1pct.csv", index=False, encoding="utf-8-sig")
    open_df = per.loc[per["open"]].copy()
    open_df.to_csv(OUT_DIR / "open_positions.csv", index=False, encoding="utf-8-sig")

    lines = [
        "# 1H_M30_4H A+B+C 纸面监控快照",
        "",
        f"- 运行时间(UTC)：{state['run_time_utc']}",
        f"- 数据最后收盘 bar：{state['data_last_bar_close']}",
        f"- 累计信号：{state['total_trades']} 笔（自数据起点 2020-01-02 起重算）",
        f"- 自上次运行新增：{state['new_trades_since_last_run']} 笔",
        f"- 当前未平仓（stage3 未退出）：{state['open_positions']} 笔",
        f"- 累计加权点数 PF：{state['overall_pf']:.3f}",
        f"- 复利净值（$500起）：0.5% → ${state['equity_0_5pct']:,.0f}；1% → ${state['equity_1pct']:,.0f}",
        "",
        "## 最近 10 笔信号",
        "",
        markdown_table(
            per.tail(10)[
                ["signal_time", "dir", "mode", "entry", "stop_distance", "weighted_pts",
                 "stage3_exit_time", "stage3_reason", "open"]
            ],
            ["signal_time", "dir", "mode", "entry", "stop_distance", "weighted_pts",
             "stage3_exit_time", "stage3_reason", "open"],
        ),
        "",
        "## 未平仓持仓",
        "",
        markdown_table(
            open_df[["signal_time", "dir", "mode", "entry", "stop_distance", "stage3_exit_price", "stage3_reason"]],
            ["signal_time", "dir", "mode", "entry", "stop_distance", "stage3_exit_price", "stage3_reason"],
        ) if len(open_df) else "（无）",
        "",
        "## 监控说明",
        "",
        "- 只读监控，不产生任何订单；每次运行从 MT5 拉取最新历史并全量重算。",
        "- 建议每个交易日收盘后运行一次（Windows 任务计划程序或手动）。",
        "- 硬警戒：出现连续 2 个负月份、或空单占比 >85%、或最近 12 个月累计为负时，暂停观察。",
    ]
    (OUT_DIR / "monitor_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"snapshot: trades={state['total_trades']} new={state['new_trades_since_last_run']} "
        f"open={state['open_positions']} equity_0.5pct=${state['equity_0_5pct']:,.0f} "
        f"equity_1pct=${state['equity_1pct']:,.0f}"
    )
    print(f"report: {OUT_DIR / 'monitor_report.md'}")


if __name__ == "__main__":
    main()
