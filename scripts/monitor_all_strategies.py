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


_CHART_PARAMS: dict | None = None


def read_ea_input(input_name: str, ea_name: str) -> str | None:
    """读运行中终端里**指定 EA** 的输入参数（含 bool 型）。

    旧版硬编码 chart_file="chart10.chr" 且只解析数字，实测后果（00_README T18）：
    chart10 是 Gold_DataEvent_EA，而 ea_inputs 只给 BiasReversal 配了 InpLongMode
    → 在别人的图表里找乖离反转参数、恒返回 None → dashboard「EA模式」列从来没有内容；
    且 chart 编号会随图表增删重排（chart05/08/11 已空），硬编号本质不可靠（T20）。
    现按 EA 名扫全部 chart*.chr，委托 live_attribution（该模块亦供台账/血缘归因）。
    """
    global _CHART_PARAMS
    if _CHART_PARAMS is None:
        try:
            import live_attribution as _la
            _CHART_PARAMS = _la.read_chart_params()
        except Exception as e:
            print(f"[ea_input] chart 实参不可用（EA模式列将为 N/A）: {e}")
            _CHART_PARAMS = {}
    rec = _CHART_PARAMS.get(ea_name)
    if not rec:
        return None
    return rec.get("inputs", {}).get(input_name)


def ea_names_for(name: str) -> list[str]:
    """策略行 -> 其挂载的 EA 名列表（用 STRATEGY_CONFIGS.magics 反查权威映射表）。

    一个策略行可能对应多个 EA（如 30m2H = 主线 Strategy_EA + ABC_EA），
    映射表见 live_attribution.EA_MAGIC_MAP（依据 问题记录 §二十三②）。
    """
    try:
        import live_attribution as _la
    except Exception:
        return []
    out: list[str] = []
    for m in STRATEGY_CONFIGS[name].get("magics", []):
        hit = _la.EA_MAGIC_MAP.get(m)
        if hit and hit[0] not in out:
            out.append(hit[0])
    return out


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

    # 真实成交血缘归因（00_README T11/T17/T19）：已实现盈亏只能按 position_id 血缘算——
    # 不能按平仓侧 deal.magic（15/59 持仓开平错配，EA 主动平仓曾落 magic=0），
    # 也不能按 deal.reason（实测不可靠：comment='[sl …]' 被记 TP、人工平仓被记 SL）。
    try:
        import live_attribution as la
        live_attr = la.snapshot()
        live_attr["ledger_files"] = la.LEDGER_FILES
    except Exception as e:
        la = None
        live_attr = {"error": f"live_attribution 不可用: {e}", "per_ea": {}, "per_magic": {},
                     "totals": {}, "gates": [], "ledgers": {}, "charts": {}, "ledger_files": {}}
    if live_attr.get("error"):
        print("[attribution] 降级（已实现盈亏/下单闸/台账列将为 N/A）:", live_attr["error"])
    else:
        _t = live_attr["totals"]
        _live = [g for g in live_attr["gates"] if g["live_trading"]]
        print(f"[attribution] 成交 {_t['deals']} 笔 / 持仓 {_t['positions']} 个 ｜ 已实现 "
              f"${_t['realized']:+,.2f}（另入金等账务 ${_t['deposits']:+,.2f}）｜ 开平 magic 错配 "
              f"{_t['mismatched_positions']} 个持仓 ｜ 终端 {len(live_attr['gates'])} 个实例中 "
              f"{len(_live)} 个双闸放开在真下单")

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
        ea_names = ea_names_for(name)
        ea_mode = ""
        ea_labels = STRATEGY_CONFIGS[name].get("ea_inputs", {})
        if ea_labels:
            parts = []
            for inp, labelmap in ea_labels.items():
                v = None
                for e in ea_names:                      # 按 EA 名找对图表（旧版恒读 chart10）
                    v = read_ea_input(inp, e)
                    if v is not None:
                        break
                parts.append(labelmap.get(v, f"{inp}={v}") if v is not None else "N/A")
            ea_mode = " / ".join(parts)

        # --- 真实成交（血缘口径）与终端下单闸，依据 问题记录 §二十三 ---
        m_rows = [m for m in live_attr.get("per_magic", {}).values() if m["strategy"] == name]
        realized = round(sum(m["realized"] for m in m_rows), 2)
        mismatch = sum(m["mismatched"] for m in m_rows)
        live_positions = sum(m["positions"] for m in m_rows)
        g_rows = [g for g in live_attr.get("gates", []) if g["ea"] in ea_names]
        live_n = sum(1 for g in g_rows if g["live_trading"])
        if not g_rows:
            gate_txt = "无挂载"
        elif live_n:
            gate_txt = f"{live_n}/{len(g_rows)} 实例真下单"
        else:
            gate_txt = f"0/{len(g_rows)} 实例(SimMode)"
        if any(g["duplicate"] for g in g_rows):
            gate_txt += "；双挂"
        led_bad = [f"{fn}={live_attr.get('ledgers', {}).get(fn, 'missing')}"
                   for fn, eaname in live_attr.get("ledger_files", {}).items()
                   if eaname in ea_names
                   and not str(live_attr.get("ledgers", {}).get(fn, "")).startswith("ok")]

        warns = list(state["warnings"])
        if live_attr.get("error"):
            warns.append("血缘归因不可用：" + str(live_attr["error"]))
        else:
            if led_bad:
                warns.append("成交台账不可读→真实成交在报表不可见：" + "；".join(led_bad))
            if live_n and not m_rows:
                warns.append("下单闸已放开但窗口内无成交（一旦出信号即真下单，非只读监控）")
            if mismatch:
                warns.append(f"开平 magic 错配 {mismatch} 笔（本表已实现盈亏按血缘归因，勿按 deal.magic 统计）")
            if any(g["duplicate"] for g in g_rows):
                warns.append("同一 EA 双挂且 magic 相同→台账/信号文件互相覆盖")

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
                "realized_pnl_usd": realized if not live_attr.get("error") else "N/A",
                "live_positions": live_positions if not live_attr.get("error") else "N/A",
                "magic_mismatch": mismatch if not live_attr.get("error") else "N/A",
                "ea_gate": gate_txt,
                "ledger_state": "；".join(led_bad) if led_bad else ("ok" if ea_names else "-"),
                "total_weighted_pts": round(total_pnl, 1),
                "equity_0_5pct": round(state["equity_0_5pct"], 0),
                "equity_1pct": round(state["equity_1pct"], 0),
                "data_last_bar": latest_bar_close.strftime("%Y-%m-%d %H:%M"),
                "warnings": "；".join(warns) if warns else "无",
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

    if la is not None and not live_attr.get("error"):
        sections.append(la.markdown_section(live_attr, live_attr["gates"], live_attr["ledgers"]))

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
            "与 Tester 对照 72/72 一致）；Gold/Oil_DataEvent 行 = 实时模拟盘 ledger 口径（EA Files 导出：signals_export + trade_ledger + gate_state，实时不可用回退回测基线）；「真实持仓」列 = MT5 账户实时读数（MetaTrader5 库，按 EA magic 归类），不可用时回退重放口径；「已实现USD」列 = MT5 账户历史成交按 **position_id 血缘**归因（记到开仓方 magic；不用平仓侧 deal.magic——15/59 持仓开平错配，也不用 deal.reason——实测不可靠，见 问题记录 §二十三）；「下单闸」列 = `chart*.chr` 实参双闸（SimMode=false 且 AllowRealTrading=true 即在 DEMO 真实下单）；0.5%/1% 复利净值按 $500 起、单笔风险、不复利上限外推。**本账户为 DEMO 且 9 个挂载实例中 6 个双闸放开＝真实下单，不是只读监控**（2026-09-09 实测纠偏，原脚注「只读监控不下单」有误，详见 00_README §1）。",
            "",
            "## 总览",
            "",
            markdown_table(
                dash_df.rename(columns={"open": "真实持仓", "real_volume": "真实手数", "real_profit": "浮盈USD",
                                        "ea_mode": "EA模式", "realized_pnl_usd": "已实现USD",
                                        "ea_gate": "下单闸", "magic_mismatch": "magic错配"})
                [["strategy", "combo", "EA模式", "下单闸", "total_trades", "new_since_last", "backfill_since_last",
                  "真实持仓", "真实手数", "浮盈USD", "已实现USD", "magic错配",
                  "total_weighted_pts", "equity_0_5pct", "equity_1pct", "data_last_bar", "warnings"]],
                ["strategy", "combo", "EA模式", "下单闸", "total_trades", "new_since_last", "backfill_since_last",
                 "真实持仓", "真实手数", "浮盈USD", "已实现USD", "magic错配",
                 "total_weighted_pts", "equity_0_5pct", "equity_1pct", "data_last_bar", "warnings"],
                money_cols={"equity_0_5pct", "equity_1pct", "浮盈USD", "已实现USD"},
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
