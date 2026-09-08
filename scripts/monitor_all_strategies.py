# -*- coding: utf-8 -*-
"""Unified paper monitor + horizontal dashboard for recommended combos.

Strategies / recommended combos (unified A+B+C logic):
  1H_M30_4H : 5-35pt, H4 bias5 same-direction >= 0.6%
  30m2H     : 5-35pt, |H2 bias5| same-sign >= 0.2% (native abs-bias55 pool)
  2H_M30_6H : 5-35pt, no bias5 filter (6H bias5+13+55 signed > 0 pool)
  USOIL2H   : 2H cross_confirm（因果口径, cross_confirm_causal, 无 lookahead）

Read-only: refreshes each strategy's raw data from MT5 (default) and
recomputes the full pipeline on closed bars. No orders are placed.

Usage:
  python scripts/monitor_all_strategies.py
  python scripts/monitor_all_strategies.py --no-refresh
  python scripts/monitor_all_strategies.py --strategies 30m2H,2H_M30_6H
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
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mt5.mt5_history import export_history_bundle  # noqa: E402
from replay_1h_bias55_h1_stop_optimization import load_frames as load_frames_1h  # noqa: E402
from replay_1h_way_momentum_filter_scan import add_h1_way_and_momentum  # noqa: E402
from experiment_1h_m30_4h_combined_20260813 import (  # noqa: E402
    build_combined_trades as build_combined_trades_1h,
)
from combined_abc_30m2h_2h_20260814 import (  # noqa: E402
    STRATS as ABC_STRATS,
    attach_context,
    build_combo,
    build_three_opportunities,
    load_strategy,
    replay_signals,
)
from experiment_1h_m30_4h_variants_20260813 import (  # noqa: E402
    add_m30_state,
    markdown_table,
    replay_three_stage,
)


STAGE_UNITS = {1: 0.5, 2: 1.0, 3: 1.5}
STAGE_UNITS_OIL = {1: 1.0}
USD_PER_POINT_PER_LOT = {"1H_M30_4H": 10.0, "30m2H": 10.0, "2H_M30_6H": 10.0, "USOIL2H": 1.0, "USOIL4H": 1.0, "BiasReversal": 1.0, "Gold_DataEvent": 10.0, "Oil_DataEvent": 1.0, "MCT": 1.0}
UNITS_TOTAL = {"1H_M30_4H": 3.0, "30m2H": 3.0, "2H_M30_6H": 3.0, "USOIL2H": 1.0, "USOIL4H": 1.0, "BiasReversal": 1.0, "Gold_DataEvent": 3.0, "Oil_DataEvent": 1.0, "MCT": 1.0}
START_CAPITAL = 500.0
OUT_ROOT = ROOT / "observation_dashboard"
TERMINAL_DATA = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65")
# Main monitoring terminal install (must match scripts/mt5/mt5_connection.MAIN_TERMINAL_PATH).
MAIN_TERMINAL_PATH = r"F:\Program Files\MetaTrader 5\terminal64.exe"

STRATEGY_CONFIGS = {
    "1H_M30_4H": {
        "dir": ROOT / "黄金" / "1H_M30_4H策略",
        "timeframes": ["M30", "H1", "H4"],
        "source_id": "1h_m30_4h_live",
        "date_from": "2020-01-01",
        "combo": "5_35/bias5>=0.6%",
        "symbol": "XAUUSDm",
        "magics": [312026, 312036],
    },
    "30m2H": {
        "dir": ROOT / "黄金" / "30m2H策略",
        "timeframes": ["M30", "H2", "M15"],
        "source_id": "30m2h_live",
        "date_from": "2018-01-01",
        "combo": "5_35/bias5同向>=0.2%",
        "symbol": "XAUUSDm",
        "magics": [302036, 302037, 302038, 302039, 352036],
    },
    "2H_M30_6H": {
        "dir": ROOT / "黄金" / "2H_M30_6H策略",
        "timeframes": ["M30", "H2", "H6"],
        "source_id": "2h_m30_6h_live",
        "date_from": "2020-01-01",
        "combo": "5_35/6H bias5+55>0",
        "symbol": "XAUUSDm",
        "magics": [342036],
    },
    "USOIL2H": {
        "dir": ROOT / "原油" / "原油2H策略",
        "timeframes": ["M30", "H2"],
        "source_id": "usoil2h_live",
        "date_from": "2020-01-01",
        "combo": "2H cross_confirm（因果口径）",
        "symbol": "USOILm",
        "magics": [362036],
    },
    "USOIL4H": {
        "dir": ROOT / "原油" / "原油4H门策略",
        "timeframes": ["M30", "H2", "H4"],
        "source_id": "usoil_4h_gate_live",
        "date_from": "2020-01-01",
        "combo": "4H门(三条件)+2H cross/pre_cross（72笔/PF1.73）",
        "symbol": "USOILm",
        "magics": [362137],
    },

    "Gold_DataEvent": {
        "dir": ROOT / "原油黄金数据行情策略",
        "timeframes": ["M30", "H2", "H6"],
        "source_id": "gold_dataevent_live",
        "date_from": "2019-01-01",
        "combo": "6H门+M30三机会+V1_T2h事件过滤（PF 1.753）",
        "symbol": "XAUUSDm",
        "magics": [411101],
    },
    "Oil_DataEvent": {
        "dir": ROOT / "原油黄金数据行情策略",
        "timeframes": ["M30", "H2", "H4"],
        "source_id": "oil_dataevent_live",
        "date_from": "2019-01-01",
        "combo": "4H way门+H2 cross/pre_cross+V1_T1h事件过滤（PF 1.488）",
        "symbol": "USOILm",
        "magics": [411102],
    },
    "MCT": {
        "dir": ROOT / "大周期拐点" / "策略开发" / "阶段4_EA对齐",
        "timeframes": ["D1", "H4"],
        "source_id": "mct_live",
        "date_from": "2021-07-01",
        "combo": "D1 13x55 穿越 → H4 待定穿越入场 + hybrid 退出（因果口径，EA 对齐 26/26）",
        "symbol": "USOILm",
        "magics": [411103],
        "no_refresh": True,
    },
    "BiasReversal": {
        "dir": ROOT / "黄金" / "乖离反转策略",
        "timeframes": ["M30", "H1", "H2", "H4", "H6"],
        "source_id": "bias_reversal_live",
        "date_from": "2018-01-01",
        "combo": "做空 H4超涨≥3.5%+2H段反转 / 做多 6H门+H1金叉（v8 PF 2.30/2.19）",
        "symbol": "XAUUSDm",
        "magics": [372036, 372037],
        "ea_inputs": {"InpLongMode": {"0": "0-6H门+H1金叉", "1": "1-超跌镜像"}},
    },
}


def refresh_strategy(name: str) -> dict:
    cfg = STRATEGY_CONFIGS[name]
    if cfg.get("no_refresh"):
        return {"source_id": cfg["source_id"], "no_refresh": True, "files": []}
    return export_history_bundle(
        strategy=name,
        strategy_dir=cfg["dir"],
        symbol=cfg["symbol"],
        timeframes=cfg["timeframes"],
        date_from=cfg["date_from"],
        # date_to = tomorrow midnight UTC so today's intraday bars are included
        # (parse_utc_datetime treats "YYYY-MM-DD" as 00:00 UTC and would cut today).
        date_to=(datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat(),
        source_id=cfg["source_id"],
    )


def read_real_positions() -> dict | None:
    """Read LIVE positions from the running MT5 terminal via MetaTrader5 lib.

    Returns {strategy: [position dicts]} grouped by configured magics,
    or None when the lib/terminal is unavailable (callers fall back to replay data).
    """
    try:
        import MetaTrader5 as mt5
    except Exception:
        return None
    # Lock to the main monitoring terminal install (see mt5_connection.MAIN_TERMINAL_PATH):
    # a secondary debug terminal must never hijack the default-instance connection.
    if not mt5.initialize(path=MAIN_TERMINAL_PATH):
        return None
    try:
        pos = mt5.positions_get()
        out: dict = {}
        if pos:
            for p in pos:
                for strat, cfg in STRATEGY_CONFIGS.items():
                    if p.magic in cfg["magics"]:
                        out.setdefault(strat, []).append({
                            "symbol": p.symbol,
                            "type": "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
                            "volume": float(p.volume),
                            "price": float(p.price_open),
                            "sl": float(p.sl) if p.sl else None,
                            "profit": float(p.profit),
                            "ticket": p.ticket,
                        })
        return out
    finally:
        mt5.shutdown()


def read_ea_input(input_name: str, chart_file: str = "chart10.chr") -> str | None:
    """读运行中终端的图表 EA 输入参数（chart*.chr UTF-16，<inputs> 块）。"""
    try:
        p = TERMINAL_DATA / "MQL5" / "Profiles" / "Charts" / "Default" / chart_file
        txt = p.read_text(encoding="utf-16")
    except Exception:
        return None
    marker = input_name + "="
    i = txt.find(marker)
    if i < 0:
        return None
    j = i + len(marker)
    k = j
    while k < len(txt) and (txt[k].isdigit() or txt[k] in ".-+"):
        k += 1
    return txt[j:k]


def build_strategy_oil():
    """USOIL2H causal cross_confirm (matches EA v5, no lookahead)."""
    from validate_usoil_2h_standalone import load_2h, replay, signals

    tf = load_2h()
    sig = signals(tf, use_pre=False)
    trades = replay(tf, sig, True, causal=True).copy()
    st = trades.rename(columns={"pnl_points": "stage_pnl"}).copy()
    st["stage"] = 1
    st["mode"] = "cross_confirm_causal"
    st["signal_time"] = pd.to_datetime(st["signal_time"])
    st["stage_exit_time"] = pd.to_datetime(st["exit_time"])
    st["stage_exit_price"] = pd.to_numeric(st["exit_price"], errors="coerce")
    st["stage_reason"] = st["reason"]
    # USOILm: 1 price unit = 1000 points; 1 lot x 1 point x $1/pt. Convert to points
    # so the shared point-based equity simulation matches the EA (1% risk on balance).
    st["stage_pnl"] = pd.to_numeric(st["stage_pnl"], errors="coerce") * 1000.0
    st["stop_distance"] = (
        pd.to_numeric(st["entry"], errors="coerce") - pd.to_numeric(st["stop"], errors="coerce")
    ).abs() * 1000.0
    return st, trades, tf


def build_strategy_4h_gate():
    """USOIL4H gate: 4H three-condition gate + 2H cross/pre_cross (matches 72-trade baseline)."""
    from validate_usoil_gate_strategy import (  # noqa: E402
        STRATEGIES as GATE_STRATEGIES,
        build_triggers,
        gate_check,
        load_2h,
        load_gate,
    )

    strategy_dir = ROOT / "原油" / "原油4H门策略"
    cfg = GATE_STRATEGIES["原油4H门策略"]
    tf2 = load_2h(strategy_dir)
    gt = load_gate(strategy_dir, cfg)
    trig = build_triggers(tf2)
    check = gate_check(gt, cfg["n_min"], cfg["thr"], *cfg["amp"])
    keep = [check(t, r["dir"] == "L") for t, r in zip(trig["signal_time"], trig.to_dict("records"))]
    trades = trig.loc[keep].copy().reset_index(drop=True)
    st = trades.rename(columns={"pnl_points": "stage_pnl"}).copy()
    st["stage"] = 1
    st["signal_time"] = pd.to_datetime(st["signal_time"])
    st["stage_exit_time"] = pd.to_datetime(st["exit_time"])
    st["stage_exit_price"] = pd.to_numeric(st["exit"], errors="coerce")
    st["stage_reason"] = st["exit_reason"]
    # USOILm: 1 price unit = 1000 points (same convention as USOIL2H monitor)
    st["stage_pnl"] = pd.to_numeric(st["stage_pnl"], errors="coerce") * 1000.0
    st["stop_distance"] = (
        pd.to_numeric(st["entry"], errors="coerce") - pd.to_numeric(st["stop"], errors="coerce")
    ).abs() * 1000.0
    return st, trades, tf2


def build_strategy_bias_reversal():
    """BiasReversal_Combo: 做空 H4超涨门+2H段反转 / 做多 6H门+H1金叉（与 EA 已部署参数一致）。

    从刷新后的 bundle 读取 H1/H2/H4/H6，用 bias_reversal_replay 复现 EA 逻辑；
    点数口径: 1点=0.01价，0.01手1点=$1（XAUUSDm），与真实账户成交一致。
    """
    from bias_reversal_replay import replay_combo  # noqa: E402

    manifest = json.loads(
        (ROOT / "黄金" / "乖离反转策略" / "data" / "raw" / "raw_source_manifest.json")
        .read_text(encoding="utf-8-sig")
    )
    bundle = Path(manifest["bundle_dir"])
    st, h1 = replay_combo(
        h4_csv=bundle / "XAUUSDm_H4.csv",
        h6_csv=bundle / "XAUUSDm_H6.csv",
        h2_csv=bundle / "XAUUSDm_H2.csv",
        h1_csv=bundle / "XAUUSDm_H1.csv",
    )
    return st, st, h1


def build_strategy(name: str):
    """Return (st, trades) for the strategy's recommended combo."""
    if name == "MCT":
        sys.path.insert(0, str(ROOT / "大周期拐点" / "策略开发" / "阶段4_EA对齐" / "scripts"))
        import monitor_mct_adapter as mcta
        return mcta.build_mct()
    if name == "BiasReversal":
        return build_strategy_bias_reversal()
    if name == "USOIL2H":
        return build_strategy_oil()
    if name == "USOIL4H":
        return build_strategy_4h_gate()

    if name in ("Gold_DataEvent", "Oil_DataEvent"):
        sys.path.insert(0, str(ROOT / "原油黄金数据行情策略" / "scripts"))
        import monitor_data_event_adapter as mdea
        if name == "Gold_DataEvent":
            return mdea.build_gold()
        return mdea.build_oil()
    if name == "1H_M30_4H":
        _, m30, h1, contexts = load_frames_1h()
        h4 = contexts["4H"]
        h1_way = add_h1_way_and_momentum(h1)
        m30_state = add_m30_state(m30)
        trades = build_combined_trades_1h(m30, h1_way, h4, 5.0, 35.0, 0.6)
        trades["entry_bar_idx"] = pd.to_numeric(trades["entry_bar_idx"], errors="coerce").astype(int)
        st = replay_three_stage(m30_state, trades)
        return st, trades, m30

    abc_cfg = ABC_STRATS[name]
    m30, gate_tf = load_strategy(abc_cfg)
    m30_state = add_m30_state(m30)
    spec = (5.0, 35.0)
    sig = build_three_opportunities(m30, spec_lo=spec[0], spec_hi=spec[1])
    replayed = replay_signals(sig, m30)
    prefix = str(abc_cfg["c_tf"]).lower()
    enriched = attach_context(replayed, gate_tf, prefix)
    bias5_thr = 0.2 if name == "30m2H" else 0.0
    trades = build_combo(enriched, abc_cfg, bias5_thr)
    st = replay_three_stage(m30_state, trades)
    return st, trades, m30


def simulate_equity(st: pd.DataFrame, risk_pct: float,
                    usd_per_point_per_lot: float = 10.0, units_total: float = 3.0,
                    stage_units: dict | None = None) -> pd.DataFrame:
    stage_units = stage_units or STAGE_UNITS
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
            unit_lot = risk_usd / (units_total * stop_pts * usd_per_point_per_lot)
            unit_lot = float(np.clip(unit_lot, 0.01, 10.0))
            lot = unit_lot * stage_units[int(r["stage"])]
            pnl_usd += lot * float(r["stage_pnl"]) * usd_per_point_per_lot
        balance += pnl_usd
        peak = max(peak, balance)
        max_dd = max(max_dd, peak - balance)
        rows.append(
            {
                "signal_time": pd.Timestamp(signal_time),
                "dir": dir_,
                "pnl_usd": pnl_usd,
                "balance": balance,
                "max_dd_pct": max_dd / peak * 100.0 if peak > 0 else 0.0,
            }
        )
    return pd.DataFrame(rows)


def per_trade_summary(st: pd.DataFrame, tf_frame, stage_units: dict) -> pd.DataFrame:
    latest_bar_close = pd.to_datetime(tf_frame["bar_close_time"]).max()
    st = st.copy()
    st["signal_time"] = pd.to_datetime(st["signal_time"])
    st["stage_exit_time"] = pd.to_datetime(st["stage_exit_time"])
    st["_w"] = st["stage_pnl"].astype(float) * st["stage"].map(stage_units)
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
    return per.sort_values("signal_time").reset_index(drop=True), latest_bar_close


def warnings_for(per: pd.DataFrame) -> list[str]:
    warns = []
    last12 = per[per["signal_time"] >= per["signal_time"].max() - pd.DateOffset(months=12)]
    if len(last12) and last12["weighted_pts"].sum() < 0:
        warns.append("最近12个月累计加权点数为负")
    months = (
        per.assign(month=per["signal_time"].dt.to_period("M"))
        .groupby("month")["weighted_pts"]
        .sum()
    )
    tail = months.tail(3)
    if len(tail) >= 2 and (tail < 0).all():
        warns.append("连续3个月中最后2个月为负")
    short_ratio = (per["dir"].astype(str).str.upper() == "S").mean()
    if short_ratio > 0.85:
        warns.append(f"空单占比 {short_ratio:.0%} > 85%（2024型态）")
    return warns


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-refresh", action="store_true")
    parser.add_argument("--strategies", default=",".join(STRATEGY_CONFIGS))
    args = parser.parse_args()
    names = [s.strip() for s in args.strategies.split(",") if s.strip() in STRATEGY_CONFIGS]
    if not names:
        raise SystemExit("no valid strategy names")
    full_run = set(names) == set(STRATEGY_CONFIGS)
    real = read_real_positions()
    if real is None:
        print("[positions] MT5 实时持仓不可用（MetaTrader5 库/终端未连接），open 列回退重放口径")
    else:
        print("[positions] MT5 实时持仓读取成功:", {k: len(v) for k, v in real.items()})

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    if not args.no_refresh:
        for name in names:
            manifest = refresh_strategy(name)
            print(f"[{name}] data refreshed: {manifest['source_id']} "
                  f"bars={[f['rows'] for f in manifest['files']]}")

    dashboard_rows = []
    sections = []
    for name in names:
        out_dir = OUT_ROOT / name
        out_dir.mkdir(parents=True, exist_ok=True)
        st, trades, tf_frame = build_strategy(name)
        stage_units = STAGE_UNITS_OIL if name in ("USOIL2H", "USOIL4H", "BiasReversal", "Oil_DataEvent", "MCT") else STAGE_UNITS
        per, latest_bar_close = per_trade_summary(st, tf_frame, stage_units)

        eq05 = simulate_equity(st, 0.5, USD_PER_POINT_PER_LOT[name], UNITS_TOTAL[name], stage_units)
        eq10 = simulate_equity(st, 1.0, USD_PER_POINT_PER_LOT[name], UNITS_TOTAL[name], stage_units)

        state_path = out_dir / "monitor_state.json"
        prev_max_signal = None
        prev_keys = None
        if state_path.exists():
            try:
                prev_state = json.loads(state_path.read_text(encoding="utf-8"))
                prev_max_signal = prev_state.get("last_signal_time")
                pk = prev_state.get("trade_keys")
                if pk:
                    prev_keys = set(pk)
            except Exception:
                pass

        # "新增" strictly counts by signal_time; 回补 = old-signal trades that only
        # appeared now because their exit completed (data-end backfill), e.g. the
        # 2H_M30_6H signals whose opposite/M30-merged cross closed later.
        cur_keys = set()
        if not per.empty:
            cur_keys = set(
                per["signal_time"].map(lambda t: pd.Timestamp(t).strftime("%Y-%m-%d %H:%M:%S"))
                + "|" + per["dir"].astype(str).str.upper()
            )
        appeared = cur_keys if prev_keys is None else cur_keys - prev_keys
        if prev_max_signal is None:
            new_since_last = len(per)
            backfill_since_last = 0
        elif prev_keys is None:
            # old schema without trade_keys: cannot separate backfill; fall back to
            # strict signal_time counting and treat backfill as unknown (0).
            prev_ts = pd.Timestamp(prev_max_signal)
            new_since_last = int((per["signal_time"] > prev_ts).sum())
            backfill_since_last = 0
        else:
            prev_ts = pd.Timestamp(prev_max_signal)
            appeared_times = {k: pd.Timestamp(k[:19]) for k in appeared}
            new_since_last = sum(1 for t in appeared_times.values() if t > prev_ts)
            backfill_since_last = sum(1 for t in appeared_times.values() if t <= prev_ts)

        state = {
            "run_time_utc": datetime.now(timezone.utc).isoformat(),
            "data_last_bar_close": latest_bar_close.isoformat(),
            "total_trades": int(len(per)),
            "last_signal_time": per["signal_time"].max().isoformat() if len(per) else None,
            "open_positions": int(per["open"].sum()),
            "new_since_last_run": int(new_since_last),
            "backfill_since_last_run": int(backfill_since_last),
            "trade_keys": sorted(cur_keys),
            "equity_0_5pct": float(eq05["balance"].iloc[-1]) if len(eq05) else START_CAPITAL,
            "equity_1pct": float(eq10["balance"].iloc[-1]) if len(eq10) else START_CAPITAL,
            "warnings": warnings_for(per),
        }
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        real_pos = (real or {}).get(name, []) if real is not None else None
        real_count = len(real_pos) if real_pos is not None else 0
        real_vol = round(sum(p["volume"] for p in real_pos), 2) if real_pos else 0.0
        real_profit = round(sum(p["profit"] for p in real_pos), 2) if real_pos else 0.0
        per.to_csv(out_dir / "trades_snapshot.csv", index=False, encoding="utf-8-sig")
        eq05.to_csv(out_dir / "equity_0_5pct.csv", index=False, encoding="utf-8-sig")
        eq10.to_csv(out_dir / "equity_1pct.csv", index=False, encoding="utf-8-sig")
        per.loc[per["open"]].to_csv(out_dir / "open_positions.csv", index=False, encoding="utf-8-sig")

        monthly_series = (
            per.assign(month=per["signal_time"].dt.to_period("M"))
            .groupby("month")["weighted_pts"]
            .sum()
            .tail(6)
        )
        monthly_df = monthly_series.reset_index()
        monthly_df.columns = ["month", "weighted_pts"]
        monthly_df.to_csv(out_dir / "monthly_last6.csv", index=False, encoding="utf-8-sig")

        total_pnl = per["weighted_pts"].sum()
        ea_mode = ""
        ea_labels = STRATEGY_CONFIGS[name].get("ea_inputs", {})
        if ea_labels:
            parts = []
            for inp, labelmap in ea_labels.items():
                v = read_ea_input(inp)
                parts.append(labelmap.get(v, f"{inp}={v}") if v is not None else "N/A")
            ea_mode = " / ".join(parts)
        dashboard_rows.append(
            {
                "strategy": name,
                "ea_mode": ea_mode,
                "combo": STRATEGY_CONFIGS[name]["combo"],
                "total_trades": state["total_trades"],
                "new_since_last": state["new_since_last_run"],
                "backfill_since_last": state["backfill_since_last_run"],
                "open": real_count if real is not None else state["open_positions"],
                "real_volume": real_vol if real is not None else 0.0,
                "real_profit": real_profit if real is not None else 0.0,
                "total_weighted_pts": round(total_pnl, 1),
                "equity_0_5pct": round(state["equity_0_5pct"], 0),
                "equity_1pct": round(state["equity_1pct"], 0),
                "data_last_bar": latest_bar_close.strftime("%Y-%m-%d %H:%M"),
                "warnings": "；".join(state["warnings"]) if state["warnings"] else "无",
            }
        )
        if real is not None:
            if real_pos:
                det = "；".join(
                    "%s %s %.2f手 @%.2f(SL %s) 浮盈$%.2f" % (
                        p["symbol"], p["type"], p["volume"], p["price"],
                        ("%.2f" % p["sl"]) if p["sl"] else "-", p["profit"])
                    for p in real_pos
                )
                real_line = f"{real_count} 仓 / {real_vol:.2f} 手，浮盈 ${real_profit:+.2f}：{det}"
            else:
                real_line = "无"
        else:
            real_line = "N/A（库不可用）"
        ea_line = f"\n- EA 模式：{ea_mode}" if ea_mode else ""
        sec = (
            f"## {name}（{STRATEGY_CONFIGS[name]['combo']}）"
            f"\n\n- 累计 {state['total_trades']} 笔，新增 {state['new_since_last_run']} 笔"
            f"（回补 {state['backfill_since_last_run']} 笔），重放未平仓 {state['open_positions']} 笔"
            f"\n- 真实持仓（MT5实时）：{real_line}"
            f"{ea_line}"
            f"\n- 0.5%风险净值 ${state['equity_0_5pct']:,.0f} / 1%风险净值 ${state['equity_1pct']:,.0f}"
            f"\n- 警戒：{'；'.join(state['warnings']) if state['warnings'] else '无'}"
        )
        if len(per):
            sec += (
                f"\n\n### 最近5笔信号"
                f"\n\n{markdown_table(per.tail(5)[['signal_time', 'dir', 'mode', 'entry', 'stop_distance', 'weighted_pts', 'stage3_reason', 'open']], ['signal_time', 'dir', 'mode', 'entry', 'stop_distance', 'weighted_pts', 'stage3_reason', 'open'])}"
                f"\n\n### 最近6个月加权点数"
                f"\n\n{markdown_table(monthly_df, ['month', 'weighted_pts'])}"
            )
        else:
            sec += "\n\n- 尚无已平仓信号（实时模拟盘启动初期，详见下方「模拟盘实时状态」）"
        sections.append(sec)
        if name == "MCT":
            try:
                sys.path.insert(0, str(ROOT / "大周期拐点" / "策略开发" / "阶段4_EA对齐" / "scripts"))
                import monitor_mct_adapter as _mcta
                sections[-1] = sections[-1] + "\n\n### 模拟盘实时状态（MCT EA ledger 口径）\n\n" + _mcta.live_snapshot()
            except Exception as _e:
                sections[-1] = sections[-1] + f"\n\n### 模拟盘实时状态\n\n- 快照生成失败: {_e}"
        if name in ("Gold_DataEvent", "Oil_DataEvent"):
            try:
                import monitor_data_event_adapter as _mdea_live
                sections[-1] = (
                    sections[-1] + "\n\n### 模拟盘实时状态（live ledger 口径）\n\n"
                    + _mdea_live.live_snapshot(name)
                )
            except Exception as _e:
                sections[-1] = sections[-1] + f"\n\n### 模拟盘实时状态\n\n- 快照生成失败: {_e}"

    dash_df = pd.DataFrame(dashboard_rows)
    print("\n" + "=" * 90)
    print(dash_df.to_string(index=False))
    print("=" * 90)

    if full_run:
        dash_df.to_csv(OUT_ROOT / "dashboard.csv", index=False, encoding="utf-8-sig")
        lines = [
            "# 推荐组合横向观察仪表盘（黄金四策略含乖离反转组合 + 原油2H/4H门）",
            "",
            f"> 生成：{datetime.now(timezone.utc).isoformat()}（UTC）",
            "> 口径：黄金三策略 A+B+C 统一逻辑；原油2H 为因果口径 `cross_confirm_causal`（无 lookahead，"
            "与 EA v5 冒烟 53/53 一致）；原油4H门为 4H 三条件门 + 2H cross/pre_cross（72笔基线，"
            "与 Tester 对照 72/72 一致）；Gold/Oil_DataEvent 行 = 实时模拟盘 ledger 口径（EA Files 导出：signals_export + trade_ledger + gate_state，实时不可用回退回测基线）；「真实持仓」列 = MT5 账户实时读数（MetaTrader5 库，按 EA magic 归类），不可用时回退重放口径；0.5%/1% 复利净值按 $500 起、单笔风险、不复利上限外推；只读监控不下单。",
            "",
            "## 总览",
            "",
            markdown_table(
                dash_df.rename(columns={"open": "真实持仓", "real_volume": "真实手数", "real_profit": "浮盈USD", "ea_mode": "EA模式"})
                [["strategy", "combo", "EA模式", "total_trades", "new_since_last", "backfill_since_last", "真实持仓", "真实手数", "浮盈USD",
                  "total_weighted_pts", "equity_0_5pct", "equity_1pct", "data_last_bar", "warnings"]],
                ["strategy", "combo", "EA模式", "total_trades", "new_since_last", "backfill_since_last", "真实持仓", "真实手数", "浮盈USD",
                 "total_weighted_pts", "equity_0_5pct", "equity_1pct", "data_last_bar", "warnings"],
                money_cols={"equity_0_5pct", "equity_1pct", "浮盈USD"},
            ),
            "",
            *sections,
            "",
            "## 使用",
            "",
            "```powershell",
            "python F:\\use_code\\MTA5_l\\scripts\\monitor_all_strategies.py          # 刷新数据+快照",
            "python F:\\use_code\\MTA5_l\\scripts\\monitor_all_strategies.py --no-refresh",
            "```",
        ]
        # 报告用 utf-8-sig（带 BOM）：保证记事本/旧 ANSI 工具按 UTF-8 识别，避免中文乱码
        (OUT_ROOT / "dashboard_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
        print(f"dashboard: {OUT_ROOT / 'dashboard_report.md'}")
    else:
        print(f"[subset] 仅处理 {','.join(names)}，跳过共享 dashboard.csv / dashboard_report.md 写入")
        if sections:
            print("\n" + "\n\n".join(sections))


if __name__ == "__main__":
    main()
