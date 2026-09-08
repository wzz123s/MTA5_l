# -*- coding: utf-8 -*-
"""诊断：USOIL4H 清单级(filter_sim) vs 信号级(reverify) 的事件门差异来源。"""
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    if str(_p) not in _sys.path:
        _sys.path.insert(0, str(_p))

import numpy as np
import pandas as pd

ROOT = _Path(r"F:\use_code\MTA5_l")
RESEARCH = ROOT / "宏观日历研究"

# 快照口径
snap = pd.read_csv(ROOT / "observation_dashboard" / "USOIL4H" / "trades_snapshot.csv", parse_dates=["signal_time"])
snap["signal_time"] = pd.to_datetime(snap["signal_time"], utc=True)
print("snapshot n =", len(snap))

# 重建口径
from validate_usoil_gate_strategy import STRATEGIES as GATE_STRATEGIES, build_triggers, gate_check, load_2h, load_gate
strategy_dir = ROOT / "原油" / "原油4H门策略"
cfg = GATE_STRATEGIES["原油4H门策略"]
tf2 = load_2h(strategy_dir)
gt = load_gate(strategy_dir, cfg)
trig = build_triggers(tf2)
check = gate_check(gt, cfg["n_min"], cfg["thr"], *cfg["amp"])
keep = [check(t, r["dir"] == "L") for t, r in zip(trig["signal_time"], trig.to_dict("records"))]
trades = trig.loc[keep].copy().reset_index(drop=True)
trades["signal_time"] = pd.to_datetime(trades["signal_time"])
print("rebuilt n =", len(trades))

# 对比 signal_time
s_snap = set(snap["signal_time"].dt.strftime("%Y-%m-%d %H:%M:%S"))
s_reb = set(trades["signal_time"].dt.strftime("%Y-%m-%d %H:%M:%S"))
print("snapshot-only:", len(s_snap - s_reb), "rebuilt-only:", len(s_reb - s_snap))
for t in sorted(s_snap - s_reb)[:5]:
    print("  snap-only:", t)
for t in sorted(s_reb - s_snap)[:5]:
    print("  reb-only:", t)

# 事件
ev = pd.read_csv(RESEARCH / "data" / "calendar_export.csv", sep="|", dtype={"event_id": "int64", "time": "int64"})
hi = np.sort(pd.to_datetime(ev["time"], unit="s", utc=True)[ev["importance"] >= 3].to_numpy(dtype="datetime64[ns]"))

def gap_h(ts_np):
    idx = np.searchsorted(hi, ts_np, side="right")
    out = np.full(len(ts_np), np.nan)
    for i, j in enumerate(idx):
        if j < len(hi):
            out[i] = (hi[j] - ts_np[i]) / np.timedelta64(1, "h")
    return out

# 快照口径的事件门（复现 filter_sim）
st_snap = snap["signal_time"].to_numpy(dtype="datetime64[ns]")
g_snap = gap_h(st_snap)
w_snap = snap["weighted_pts"].to_numpy(dtype=float)
for T in [8]:
    m = g_snap >= T
    print(f"snapshot V1_T{T}h: n={m.sum()} total={w_snap[m].sum():,.0f} avg={w_snap[m].mean():,.1f}")

# 重建口径
st_reb = trades["signal_time"].to_numpy(dtype="datetime64[ns]")
g_reb = gap_h(st_reb)
w_reb = pd.to_numeric(trades["pnl_points"], errors="coerce").to_numpy(dtype=float) * 1000.0
for T in [8]:
    m = g_reb > T
    print(f"rebuilt T{T}h: n={m.sum()} total={w_reb[m].sum():,.0f} avg={w_reb[m].mean():,.1f}")
    # 被过滤的
    mf = ~m
    print(f"  被过滤 {mf.sum()} 笔, 合计 {w_reb[mf].sum():,.0f}")
    for i in np.where(mf)[0]:
        print(f"    {trades['signal_time'].iloc[i]} gap={g_reb[i]:.2f}h pnl={w_reb[i]:,.0f}")

# 对比 gap 差异（同 signal_time 的信号）
common = snap.set_index(snap["signal_time"].dt.strftime("%Y-%m-%d %H:%M:%S")).loc[sorted(s_snap & s_reb)]
print("\\n共同信号 gap 差异(快照-重建):")
diffs = []
for key in s_snap & s_reb:
    gi = gap_h(np.array([snap[snap["signal_time"].dt.strftime('%Y-%m-%d %H:%M:%S') == key]['signal_time'].iloc[0].to_datetime64()]))
    gj = gap_h(np.array([trades[trades['signal_time'].dt.strftime('%Y-%m-%d %H:%M:%S') == key]['signal_time'].iloc[0].to_datetime64()]))
    if not (np.isnan(gi[0]) and np.isnan(gj[0])) and abs((gi[0] if not np.isnan(gi[0]) else 999) - (gj[0] if not np.isnan(gj[0]) else 999)) > 1e-6:
        diffs.append((key, gi[0], gj[0]))
print("gap 不一致数量:", len(diffs))
for d in diffs[:8]:
    print("  ", d)
