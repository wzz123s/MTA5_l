# -*- coding: utf-8 -*-
"""① 黄金 S2B 段长过滤实验 ② v1.2 模拟盘信号（扩大窗口至2025-01）"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"
SIG = BASE / "data" / "signals"
OUT = BASE / "data"
REP = BASE / "报告"
MIN_STOP = 0.003
COOLDOWN_H = 48

def load(symbol, tf):
    df = pd.read_csv(PROC / f"{symbol}_{tf}_features.csv")
    df["dt"] = pd.to_datetime(df["dt"], utc=True)
    return df

TF_MIN = {"M15": 15, "M30": 30, "H1": 60, "H2": 120, "H4": 240, "H6": 360, "H8": 480, "D1": 1440, "W1": 10080}

def last_closed(df_hi, t, tf_gate, tf_sig):
    # 因果修复(2026-09-04): 门 bar 收盘 <= 信号 bar 收盘
    cutoff = t + pd.Timedelta(minutes=TF_MIN[tf_sig])
    m = (df_hi["dt"] + pd.Timedelta(minutes=TF_MIN[tf_gate])) <= cutoff
    if not m.any(): return None
    return df_hi.loc[m].iloc[-1]

def cooldown(rows, hours=COOLDOWN_H):
    rows = sorted(rows, key=lambda r: r.get('dt', r.get('signal_dt')))
    kept = []; last_dt = {}
    for r in rows:
        d = r['dir']
        rt = r.get('dt', r.get('signal_dt'))
        if d in last_dt and (rt - last_dt[d]) < pd.Timedelta(hours=hours): continue
        last_dt[d] = rt; kept.append(r)
    return kept

def s2b_signals(seg_min=0, seg_max=999, min_stop=MIN_STOP):
    """黄金 S2B（H6趋势门+回调+M30 good），可选段长过滤"""
    df = load("XAUUSDm", "M30")
    h6 = load("XAUUSDm", "H6")
    rows = []
    goods = df[df["dir"] == "good"]
    for _, row in goods.iterrows():
        t = row["dt"]
        g6 = last_closed(h6, t, "H6", "M30")
        if g6 is None: continue
        if not (g6["bias5_pct"] > 0 and g6["bias55_pct"] > 0): continue
        if abs(g6["bias13_pct"]) >= 2.0: continue
        if g6["seg_len"] < seg_min or g6["seg_len"] > seg_max: continue
        stop = row["prev_seg_low_sma13"]
        if pd.isna(stop): continue
        idx = df.index.get_loc(row.name)
        if idx + 1 >= len(df): continue
        nb = df.iloc[idx + 1]
        entry = float(nb["open"])
        sd = abs(entry - float(stop))
        if sd <= 0 or sd / entry < min_stop or sd / entry > 0.008: continue
        rows.append({"dir": "long", "entry_dt": nb["dt"], "entry": entry, "stop": float(stop), "signal_dt": t, "sd_pct": round(sd / entry * 100, 2), "h6_seg_len": int(g6["seg_len"]), "h6_bias13": round(float(g6["bias13_pct"]), 2)})
    return pd.DataFrame(cooldown(rows))

def simulate(df, row, max_bars):
    entry = float(row["entry"]); stop = float(row["stop"]); direction = row["dir"]
    sd = abs(entry - stop)
    if sd <= 0: return None
    m = df["dt"] == row["entry_dt"]
    if not m.any(): return None
    idx = df.index.get_loc(df.index[m][0])
    start = idx + 1
    end = min(start + max_bars, len(df))
    for j in range(start, end):
        bar = df.iloc[j]
        high, low, close = float(bar["high"]), float(bar["low"]), float(bar["close"])
        sma55 = bar["sma55"]
        if direction == "short":
            if high >= stop: return {'R': -1.0, 'reason': 'stop'}
            if not pd.isna(sma55) and close <= sma55: return {'R': (entry - close) / sd, 'reason': 'target1'}
            if bar["dir"] == "good": return {"R": (entry - close) / sd, "reason": "cross"}
        else:
            if low <= stop: return {'R': -1.0, 'reason': 'stop'}
            if not pd.isna(sma55) and close >= sma55: return {'R': (close - entry) / sd, 'reason': 'target1'}
            if bar["dir"] == "bad": return {"R": (close - entry) / sd, "reason": "cross"}
    last = df.iloc[end - 1]
    close = float(last["close"])
    r = (entry - close) / sd if direction == "short" else (close - entry) / sd
    return {"R": r, "reason": "timeout"}

def run(df, cand, max_bars):
    out = []
    for _, row in cand.iterrows():
        res = simulate(df, row, max_bars)
        if res:
            res["signal_dt"] = row["signal_dt"]
            out.append(res)
    return pd.DataFrame(out) if out else pd.DataFrame()

def stats(t):
    if t is None or len(t) == 0: return None
    w = t[t["R"] > 0]; l = t[t["R"] <= 0]
    gw = float(w["R"].sum()) if not w.empty else 0.0
    gl = -float(l["R"].sum()) if not l.empty else 0.0
    return {"n": len(t), "wr": len(w) / len(t), "ev": float(t["R"].mean()), "pf": gw / gl if gl > 0 else float("inf")}

def fmt(r):
    if r is None: return "n=0"
    return f"n={r['n']} wr={r['wr']:.1%} ev={r['ev']:.2f}R pf={r['pf']:.2f}"

def main():
    h1 = load("XAUUSDm", "M30")
    out = []
    out.append("# 黄金 S2B 段长过滤实验 + v1.2 模拟盘信号")
    out.append("")
    out.append("## ① S2B 段长过滤（H6 段长 8~30）")
    out.append("")
    out.append("| 版本 | 全样本 | 2020-2024 | 2025-2026 |")
    out.append("|---|---|---|---|")
    for name, smin, smax in [('S2B原版', 0, 999), ('S2B+段长8-30', 8, 30)]:
        cand = s2b_signals(seg_min=smin, seg_max=smax)
        t = run(h1, cand, 240)
        s_all = stats(t)
        t2 = t.copy(); t2["dt"] = pd.to_datetime(t2["signal_dt"], utc=True)
        s_e = stats(t2[t2['dt'] < '2025-01-01'])
        s_l = stats(t2[t2['dt'] >= '2025-01-01'])
        out.append(f"| {name} | {fmt(s_all)} | {fmt(s_e)} | {fmt(s_l)} |")
    out.append("")
    out.append("## ② v1.2 模拟盘信号（2025-01 起，段长8-30过滤）")
    out.append("")
    # 原油 v1.2
    h2 = load("USOILm", "H2")
    h4 = load("USOILm", "H4")
    oil_rows = []
    crosses = h2[h2["dir"].isin(["bad", "good"])]
    for _, row in crosses.iterrows():
        t = row["dt"]
        g4 = last_closed(h4, t, "H4", "M30")
        if g4 is None or not (8 <= g4['seg_len'] <= 30): continue
        if row["dir"] == "bad":
            if g4["bias55_pct"] < 2.5: continue
            direction, stop = "short", row["prev_seg_high_sma13"]
        else:
            if g4["bias55_pct"] > -2.5: continue
            direction, stop = "long", row["prev_seg_low_sma13"]
        if pd.isna(stop): continue
        idx = h2.index.get_loc(row.name)
        if idx + 1 >= len(h2): continue
        nb = h2.iloc[idx + 1]
        entry = float(nb["open"])
        sd = abs(entry - float(stop))
        if sd <= 0 or sd / entry < MIN_STOP or sd / entry > 0.01: continue
        oil_rows.append({"dir": direction, "entry_dt": nb["dt"], "entry": entry, "stop": float(stop), "signal_dt": t, "sd_pct": round(sd / entry * 100, 2), "gate_seg_len": int(g4["seg_len"]), "gate_bias55": round(float(g4["bias55_pct"]), 2)})
    oil_cand = pd.DataFrame(cooldown(oil_rows))
    oil_recent = oil_cand[oil_cand["signal_dt"] >= "2025-01-01"]
    oil_cand.to_csv(OUT / "sim_signals_USOILm.csv", index=False)
    print(f"[USOILm] v1.2 全量信号 {len(oil_cand)}，2025起 {len(oil_recent)}")
    # 黄金 S2B v1.2（段长8-30）
    gold_cand = s2b_signals(seg_min=8, seg_max=30)
    gold_recent = gold_cand[gold_cand["signal_dt"] >= "2025-01-01"]
    gold_cand.to_csv(OUT / "sim_signals_XAUUSDm.csv", index=False)
    print(f"[XAUUSDm] v1.2 全量信号 {len(gold_cand)}，2025起 {len(gold_recent)}")
    out.append("信号已输出：data/sim_signals_*.csv（v1.2 规则）")
    out.append("")
    REP.mkdir(parents=True, exist_ok=True)
    (REP / "S2B段长实验与v1.2信号_v1.2.md").write_text("\n".join(out), encoding="utf-8")
    print("saved ->", REP / "S2B段长实验与v1.2信号_v1.2.md")
    print("\n".join(out))

if __name__ == "__main__":
    main()