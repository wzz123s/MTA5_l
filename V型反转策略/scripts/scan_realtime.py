# -*- coding: utf-8 -*-
"""V反策略：实时信号跟踪（黄金 M15×H2 第二观察 + 原油 v1.4 H1×H4 short）

每次数据更新后运行（mt5_history -> data_prepare -> features 之后）：
  1. 重扫两策略信号（validate_periods 引擎逻辑内联，避免依赖中间 CSV）
  2. 输出 2026-08-27（上次跟踪点）之后的新信号
  3. 追加到 data/信号跟踪清单.md
用法：python scan_realtime.py
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"
OUT = BASE / "data"

LAST_TRACK_UTC = "2026-08-28"  # 上次跟踪点（08-27 及之前信号已计入模拟盘批次）

def load(symbol, tf):
    df = pd.read_csv(PROC / f"{symbol}_{tf}_features.csv")
    df["dt"] = pd.to_datetime(df["dt"], utc=True)
    return df

TF_MIN = {"M15": 15, "M30": 30, "H1": 60, "H2": 120, "H4": 240, "H6": 360, "H8": 480, "D1": 1440, "W1": 10080}

def last_closed(gate, t, tf_gate, tf_sig):
    # 因果修复(2026-09-04): 门 bar 必须在信号 bar 收盘时已收盘(避免读未收盘门 bar 终值)
    cutoff = t + pd.Timedelta(minutes=TF_MIN[tf_sig])
    m = (gate["dt"] + pd.Timedelta(minutes=TF_MIN[tf_gate])) <= cutoff
    if not m.any():
        return None
    return gate.loc[m].iloc[-1]

def cooldown(rows, hours=48):
    rows = sorted(rows, key=lambda r: r.get("dt", r.get("signal_dt")))
    kept = []; last_dt = {}
    for r in rows:
        d = r["dir"]
        rt = r.get("dt", r.get("signal_dt"))
        if d in last_dt and (rt - last_dt[d]) < pd.Timedelta(hours=hours):
            continue
        last_dt[d] = rt
        kept.append(r)
    return kept

def s2b(sig, gate, side, sig_tf, gate_tf, seg_min, seg_max, min_stop, max_stop):
    rows = []
    cross = "good" if side == "long" else "bad"
    sig_rows = sig[sig["dir"] == cross]
    for _, row in sig_rows.iterrows():
        t = row["dt"]
        g = last_closed(gate, t, gate_tf, sig_tf)
        if g is None:
            continue
        if side == "long":
            if not (g["bias5_pct"] > 0 and g["bias55_pct"] > 0):
                continue
        else:
            if not (g["bias5_pct"] < 0 and g["bias55_pct"] < 0):
                continue
        if abs(g["bias13_pct"]) >= 2.0:
            continue
        if g["seg_len"] < seg_min or g["seg_len"] > seg_max:
            continue
        stop_col = "prev_seg_low_sma13" if side == "long" else "prev_seg_high_sma13"
        stop = row[stop_col]
        if pd.isna(stop):
            continue
        idx = sig.index.get_loc(row.name)
        if idx + 1 >= len(sig):
            continue
        nb = sig.iloc[idx + 1]
        entry = float(nb["open"])
        sd = abs(entry - float(stop))
        if sd <= 0 or sd / entry < min_stop or sd / entry > max_stop:
            continue
        rows.append({"dir": side, "entry_dt": nb["dt"], "entry": entry, "stop": float(stop),
                     "signal_dt": t, "sd_pct": round(sd / entry * 100, 2),
                     "gate_seg_len": int(g["seg_len"]), "gate_bias13": round(float(g["bias13_pct"]), 2)})
    return pd.DataFrame(cooldown(rows))

def scan(symbol, sig_tf, gate_tf, side, seg_min, seg_max, min_stop, max_stop, label):
    sig = load(symbol, sig_tf)
    gate = load(symbol, gate_tf)
    cand = s2b(sig, gate, side, sig_tf, gate_tf, seg_min, seg_max, min_stop, max_stop)
    if len(cand):
        cand["signal_dt"] = pd.to_datetime(cand["signal_dt"], utc=True)
        new = cand[cand["signal_dt"] > LAST_TRACK_UTC]
        print(f"[{label}] 全量信号 {len(cand)}，{LAST_TRACK_UTC} 之后新信号 {len(new)}")
        if len(new):
            for _, r in new.iterrows():
                print(f"  {r['signal_dt']} {r['dir']} entry={r['entry']:.3f} stop={r['stop']:.3f} ({r['sd_pct']:.2f}%) gate_seg={r['gate_seg_len']} gate_bias13={r['gate_bias13']:.2f}")
        return new
    print(f"[{label}] 无信号")
    return pd.DataFrame()

if __name__ == "__main__":
    print("=== V反实时信号扫描（跟踪点 " + LAST_TRACK_UTC + "） ===")
    g1 = scan("XAUUSDm", "M15", "H2", "long", 8, 30, 0.003, 0.008, "黄金 M15×H2 多")
    o1 = scan("USOILm", "H1", "H4", "short", 8, 30, 0.003, 0.01, "原油 v1.4 H1×H4 空")
    all_new = pd.concat([g1, o1]) if len(g1) and len(o1) else (g1 if len(g1) else o1)
    if len(all_new):
        all_new.to_csv(OUT / "实时信号_最新批次.csv", index=False)
        print("-> data/实时信号_最新批次.csv")
