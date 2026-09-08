# -*- coding: utf-8 -*-
"""V反策略 待办验证轮：参数扰动/成本敏感性/黄金S1高门槛/H5扩样/三段式trail细化"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"
SIG = BASE / "data" / "signals"
REP = BASE / "报告"

def load(symbol, tf):
    df = pd.read_csv(PROC / f"{symbol}_{tf}_features.csv")
    df["dt"] = pd.to_datetime(df["dt"], utc=True)
    return df

def last_closed(df_hi, t):
    m = df_hi["dt"] <= t
    if not m.any():
        return None
    return df_hi.loc[m].iloc[-1]

def gen_cand_threshold(symbol, sig_tf, gate_tf, direction, thr, seg_min=0, stop_lo=0.0, stop_hi=1.0):
    """按单一阈值生成候选（参数扰动用）"""
    df = load(symbol, sig_tf)
    df_hi = load(symbol, gate_tf)
    rows = []
    cross = df[df["dir"].isin(["bad", "good"])]
    for i, row in cross.iterrows():
        t = row["dt"]
        idx = df.index.get_loc(i)
        if idx + 1 >= len(df):
            continue
        nb = df.iloc[idx + 1]
        hi = last_closed(df_hi, t)
        if hi is None: continue
        if direction == "short" and row["dir"] != "bad": continue
        if direction == "long" and row["dir"] != "good": continue
        if seg_min > 0 and hi["seg_len"] < seg_min: continue
        if direction == "short" and hi["bias55_pct"] < thr: continue
        if direction == "long" and hi["bias55_pct"] > -thr: continue
        entry = float(nb["open"])
        stop = float(row["prev_seg_high_sma13"]) if direction == "short" else float(row["prev_seg_low_sma13"])
        if pd.isna(stop) or stop <= 0: continue
        sd = abs(entry - stop)
        if sd <= 0: continue
        if sd / entry < stop_lo or sd / entry > stop_hi: continue
        rows.append({"dir": direction, "entry_dt": nb["dt"], "entry": entry, "stop": stop, "signal_dt": t, "gate_bias55": hi["bias55_pct"], "gate_seg_len": hi["seg_len"], "sd": sd})
    return pd.DataFrame(rows)

def simulate(df, row, max_bars, cost=0.0, trail=False):
    entry = float(row["entry"]); stop = float(row["stop"]); direction = row["dir"]
    sd = abs(entry - stop)
    if sd <= 0: return None
    m = df["dt"] == row["entry_dt"]
    if not m.any(): return None
    idx = df.index.get_loc(df.index[m][0])
    start = idx + 1
    end = min(start + max_bars, len(df))
    trail_active = False
    trail_stop = None
    seg1 = False; seg2 = False; total = 0.0
    for j in range(start, end):
        bar = df.iloc[j]
        high, low, close = float(bar["high"]), float(bar["low"]), float(bar["close"])
        if direction == "short":
            if trail_active and high >= trail_stop:
                return {"R": (entry - trail_stop) / sd - cost, "reason": "trail", "target1": False}
            if high >= stop:
                return {"R": -1.0 - cost, "reason": "stop", "target1": False}
            if trail and not seg1 and low <= entry - 1.5 * sd:
                seg1 = True; trail_active = True; trail_stop = entry - 0.5 * sd
            if seg1 and not seg2 and low <= entry - 4.0 * sd:
                return {"R": (1.5 + 4.0) / 2.0 - cost, "reason": "stage4R", "target1": False}
            if bar["dir"] == "good":
                return {"R": (entry - close) / sd - cost, "reason": "cross", "target1": False}
        else:
            if trail_active and low <= trail_stop:
                return {"R": (trail_stop - entry) / sd - cost, "reason": "trail", "target1": False}
            if low <= stop:
                return {"R": -1.0 - cost, "reason": "stop", "target1": False}
            if trail and not seg1 and high >= entry + 1.5 * sd:
                seg1 = True; trail_active = True; trail_stop = entry + 0.5 * sd
            if seg1 and not seg2 and high >= entry + 4.0 * sd:
                return {"R": (1.5 + 4.0) / 2.0 - cost, "reason": "stage4R", "target1": False}
            if bar["dir"] == "bad":
                return {"R": (close - entry) / sd - cost, "reason": "cross", "target1": False}
    last = df.iloc[end - 1]
    close = float(last["close"])
    r = (entry - close) / sd if direction == "short" else (close - entry) / sd
    return {"R": r - cost, "reason": "timeout", "target1": False}

def run_cand(df, cand, max_bars, cost=0.0, trail=False):
    out = []
    for _, row in cand.iterrows():
        res = simulate(df, row, max_bars, cost, trail)
        if res:
            res["signal_dt"] = row["signal_dt"]
            out.append(res)
    return pd.DataFrame(out) if out else pd.DataFrame()

def pf_ev(t):
    if t is None or len(t) == 0: return None
    w = t[t["R"] > 0]; l = t[t["R"] <= 0]
    gw = float(w["R"].sum()) if not w.empty else 0.0
    gl = -float(l["R"].sum()) if not l.empty else 0.0
    return {"n": len(t), "wr": len(w) / len(t), "ev": float(t["R"].mean()), "pf": gw / gl if gl > 0 else float("inf")}

def fmt(r):
    if r is None: return "n=0"
    return f"n={r['n']} wr={r['wr']:.1%} ev={r['ev']:.2f}R pf={r['pf']:.2f}"

def main():
    out = []
    out.append("# 待办验证轮结果（v0.3）")
    out.append("")

    # ===== 1. 参数扰动：黄金 S1 做空（阈值 2.5~4.5） =====
    out.append("## 1. 参数扰动（黄金 S1 做空，H4 bias55 阈值扫描）")
    out.append("")
    out.append("| 阈值 | 结果 |")
    out.append("|---|---|")
    gold_df = load("XAUUSDm", "M30")
    for thr in [2.5, 3.0, 3.5, 4.0, 4.5]:
        cand = gen_cand_threshold("XAUUSDm", "M30", "H4", "short", thr, seg_min=0, stop_lo=0.0011, stop_hi=0.008)
        t = run_cand(gold_df, cand, 240)
        out.append(f"| {thr}% | {fmt(pf_ev(t))} |")
    out.append("")

    # ===== 2. 参数扰动：原油（阈值 2.0~4.0） =====
    out.append("## 2. 参数扰动（原油，H4 bias55 阈值扫描，多空合并）")
    out.append("")
    out.append("| 阈值 | 结果 |")
    out.append("|---|---|")
    oil_df = load("USOILm", "H2")
    for thr in [2.0, 2.5, 3.0, 3.5, 4.0]:
        cs = gen_cand_threshold("USOILm", "H2", "H4", "short", thr, seg_min=8, stop_lo=0.001, stop_hi=0.01)
        cl = gen_cand_threshold("USOILm", "H2", "H4", "long", thr, seg_min=8, stop_lo=0.001, stop_hi=0.01)
        allc = pd.concat([cs, cl], ignore_index=True) if len(cs) or len(cl) else pd.DataFrame()
        t = run_cand(oil_df, allc, 120)
        out.append(f"| {thr}% | {fmt(pf_ev(t))} |")
    out.append("")

    # ===== 3. 成本敏感性（spread x2） =====
    out.append("## 3. 成本敏感性（spread 放大2倍）")
    out.append("")
    out.append("| 组合 | 无成本 | 含成本 |")
    out.append("|---|---|---|")
    # 原油基础候选（2.0%阈值）
    cs = gen_cand_threshold("USOILm", "H2", "H4", "short", 2.0, seg_min=8, stop_lo=0.001, stop_hi=0.01)
    cl = gen_cand_threshold("USOILm", "H2", "H4", "long", 2.0, seg_min=8, stop_lo=0.001, stop_hi=0.01)
    allc = pd.concat([cs, cl], ignore_index=True) if len(cs) or len(cl) else pd.DataFrame()
    t0 = run_cand(oil_df, allc, 120)
    # 原油成本：spread 4点=0.004 价格单位，x2=0.008；按 sd 比例折算 R 成本
    tc = run_cand(oil_df, allc, 120, cost=0.008 / allc['sd'].mean() if len(allc) else 0.0)
    out.append(f"| 原油 全部 | {fmt(pf_ev(t0))} | {fmt(pf_ev(tc))} |")
    # 黄金 S2B 成本：spread 25点=0.025，x2=0.05
    h1 = load("XAUUSDm", "M30"); h6 = load("XAUUSDm", "H6")
    s2b_rows = []
    goods = h1[h1["dir"] == "good"]
    for _, row in goods.iterrows():
        t = row["dt"]
        g6 = last_closed(h6, t)
        if g6 is None: continue
        if not (g6["bias5_pct"] > 0 and g6["bias55_pct"] > 0): continue
        if abs(g6["bias13_pct"]) >= 2.0: continue
        idx = h1.index.get_loc(row.name)
        if idx + 1 >= len(h1): continue
        nb = h1.iloc[idx + 1]
        stop = row["prev_seg_low_sma13"]
        if pd.isna(stop): continue
        sd = abs(float(nb["open"]) - float(stop))
        if sd <= 0 or sd / float(nb['open']) < 0.0011 or sd / float(nb['open']) > 0.008: continue
        s2b_rows.append({"dir": "long", "entry_dt": nb["dt"], "entry": nb["open"], "stop": stop, "signal_dt": t, "sd": sd})
    s2b = pd.DataFrame(s2b_rows)
    g0 = run_cand(h1, s2b, 240)
    gc = run_cand(h1, s2b, 240, cost=0.05 / s2b['sd'].mean() if len(s2b) else 0.0)
    out.append(f"| 黄金 S2B | {fmt(pf_ev(g0))} | {fmt(pf_ev(gc))} |")
    out.append("")

    # ===== 4. 黄金 S1 高门槛（bias55>=4.5 + 2H rise>=5%） =====
    out.append("## 4. 黄金 S1 高门槛（H4 bias55>=4.5% + H2 rise>=5%）")
    out.append("")
    h2 = load("XAUUSDm", "H2")
    hi_rows = []
    bads = gold_df[gold_df["dir"] == "bad"]
    for _, row in bads.iterrows():
        t = row["dt"]
        g4 = last_closed(load("XAUUSDm", "H4"), t)
        g2 = last_closed(h2, t)
        if g4 is None or g2 is None: continue
        if g4["bias55_pct"] < 4.5: continue
        if pd.isna(g2["rise"]) or g2["rise"] < 0.05: continue
        idx = gold_df.index.get_loc(row.name)
        if idx + 1 >= len(gold_df): continue
        nb = gold_df.iloc[idx + 1]
        stop = row["prev_seg_high_sma13"]
        if pd.isna(stop): continue
        sd = abs(float(nb["open"]) - float(stop))
        if sd <= 0 or sd / float(nb['open']) > 0.008: continue
        hi_rows.append({"dir": "short", "entry_dt": nb["dt"], "entry": nb["open"], "stop": stop, "signal_dt": t, "sd": sd})
    hic = pd.DataFrame(hi_rows)
    ht = run_cand(gold_df, hic, 240)
    out.append(f"| S1高门槛(4.5%+rise5%) | n={len(hic)} {fmt(pf_ev(ht))} |")
    out.append("")

    # ===== 5. H5 前段极值叠加（原油：entry 距 4H 前段极值<1%） =====
    out.append("## 5. H5 前段极值叠加（原油）")
    out.append("")
    h4o = load("USOILm", "H4")
    near = []; far = []
    for _, row in allc.iterrows():
        t = row["signal_dt"]
        g4 = last_closed(h4o, t)
        if g4 is None: continue
        ref = float(g4["prev_seg_high_sma13"]) if row["dir"] == "short" else float(g4["prev_seg_low_sma13"])
        if pd.isna(ref): continue
        d = abs(float(row['entry']) - ref) / float(row['entry'])
        (near if d < 0.01 else far).append(row['signal_dt'])
    tn = run_cand(oil_df, allc[allc['signal_dt'].isin(near)], 120) if near else pd.DataFrame()
    tf_ = run_cand(oil_df, allc[allc['signal_dt'].isin(far)], 120) if far else pd.DataFrame()
    out.append(f"| 前段极值附近(<1%) | {fmt(pf_ev(tn))} |")
    out.append(f"| 远离前段极值 | {fmt(pf_ev(tf_))} |")
    out.append("")

    # ===== 6. 三段式 trail 细化（原油） =====
    out.append("## 6. 三段式 trail 细化（原油：1.5R 启动移损至0.5R + 4R 强制）")
    out.append("")
    tt = run_cand(oil_df, allc, 120, trail=True)
    out.append(f"| trail版 | {fmt(pf_ev(tt))} |")
    out.append(f"| 简单三段式(v0.2) | 见 v0.2 报告 PF 1.89 |")
    out.append("")

    REP.mkdir(parents=True, exist_ok=True)
    (REP / "待办验证结果_v0.3.md").write_text("\n".join(out), encoding="utf-8")
    print("saved ->", REP / "待办验证结果_v0.3.md")
    print("\n".join(out))

if __name__ == "__main__":
    main()