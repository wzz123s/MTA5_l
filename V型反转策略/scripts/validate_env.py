# -*- coding: utf-8 -*-
"""环境过滤器研究：深V过滤 + 时段分段对比

背景：复盘#2 发现全样本（PF 3.31/2.00）与 2026 近期窗口（-16.57R）严重分化，
假设：V反需要'深V'（大幅偏离）才有空间，震荡市浅V反复止损。

实验：
  F0 基线：现有 v1.1 门
  F1 深V：4H 段内 bias55 极值多单<=-4%（空单>=+4%）
  F2 段长：4H 段长 8~30（排除超长衰竭段）
  F3 F1+F2
分段：2020-2024 vs 2025-2026 各自 PF/EV
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

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
    if not m.any(): return None
    return df_hi.loc[m].iloc[-1]

def seg_extreme_bias55(df_hi, t, direction):
    """当前4H段的 bias55 极值（多单看段内最低，空单看段内最高）
    用段内极值价格对应时间段的 bias55 近似：取当前段内 close 与 SMA55 的最大偏离
    """
    g = last_closed(df_hi, t)
    if g is None: return None
    # 简化：段内极值 bias55 用 段极值价格（seg_high/low）相对当前 SMA55 估算
    sma55 = g["sma55"]
    if pd.isna(sma55) or sma55 <= 0: return None
    if direction == "long":
        low_p = g["seg_low_price"]
        if pd.isna(low_p): return None
        return (low_p - sma55) / sma55 * 100
    else:
        high_p = g["seg_high_price"]
        if pd.isna(high_p): return None
        return (high_p - sma55) / sma55 * 100

def build_candidates(symbol, sig_tf, gate_tf, min_stop, max_stop, seg_min):
    df = load(symbol, sig_tf)
    hi = load(symbol, gate_tf)
    rows = []
    crosses = df[df["dir"].isin(["bad", "good"])]
    for _, row in crosses.iterrows():
        t = row["dt"]
        g = last_closed(hi, t)
        if g is None or g['seg_len'] < seg_min: continue
        if row["dir"] == "bad":
            if g["bias55_pct"] < 2.5: continue
            direction, stop = "short", row["prev_seg_high_sma13"]
        else:
            if g["bias55_pct"] > -2.5: continue
            direction, stop = "long", row["prev_seg_low_sma13"]
        if pd.isna(stop): continue
        idx = df.index.get_loc(row.name)
        if idx + 1 >= len(df): continue
        nb = df.iloc[idx + 1]
        entry = float(nb["open"])
        sd = abs(entry - float(stop))
        if sd <= 0 or sd / entry < min_stop or sd / entry > max_stop: continue
        ext = seg_extreme_bias55(hi, t, direction)
        rows.append({"dir": direction, "entry_dt": nb["dt"], "entry": entry, "stop": float(stop), "signal_dt": t, "seg_len": int(g["seg_len"]), "bias55_now": float(g["bias55_pct"]), "bias55_ext": ext})
    return pd.DataFrame(rows)

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

def eval_filters(symbol, sig_tf, gate_tf, min_stop, max_stop, seg_min, max_bars, filters):
    cand = build_candidates(symbol, sig_tf, gate_tf, min_stop, max_stop, seg_min)
    df = load(symbol, sig_tf)
    if cand.empty:
        return None
    # 基线结果
    trades = []
    for _, row in cand.iterrows():
        res = simulate(df, row, max_bars)
        if res:
            res["signal_dt"] = row["signal_dt"]
            res.update({k: row[k] for k in ['dir', 'seg_len', 'bias55_now', 'bias55_ext']})
            trades.append(res)
    t = pd.DataFrame(trades)
    out = {}
    # F0 基线
    out['F0'] = t
    # F1 深V
    m1 = t.apply(lambda r: (r["dir"] == "long" and r["bias55_ext"] <= -4.0) or (r["dir"] == "short" and r["bias55_ext"] >= 4.0), axis=1)
    out['F1'] = t[m1]
    # F2 段长 8~30
    m2 = t["seg_len"].between(8, 30)
    out['F2'] = t[m2]
    # F3 F1+F2
    out['F3'] = t[m1 & m2]
    return out

def stats(t):
    if t is None or len(t) == 0: return None
    w = t[t["R"] > 0]; l = t[t["R"] <= 0]
    gw = float(w["R"].sum()) if not w.empty else 0.0
    gl = -float(l["R"].sum()) if not l.empty else 0.0
    return {"n": len(t), "wr": len(w) / len(t), "ev": float(t["R"].mean()), "pf": gw / gl if gl > 0 else float("inf")}

def fmt(r):
    if r is None: return "n=0"
    return f"n={r['n']} wr={r['wr']:.1%} ev={r['ev']:.2f}R pf={r['pf']:.2f}"

def split_stats(t, cutoff='2025-01-01'):
    t2 = t.copy()
    t2["dt"] = pd.to_datetime(t2["signal_dt"], utc=True)
    early = t2[t2['dt'] < cutoff]
    late = t2[t2['dt'] >= cutoff]
    return stats(early), stats(late)

def main():
    out = []
    out.append("# 环境过滤器研究（深V + 段长 + 时段分段）")
    out.append("")
    out.append("> 目的：解决 2026 震荡市止损密集问题。深V假设：段内 bias55 极值 |ext|>=4% 才有空间（难论：只有深V才诱人）。")
    out.append("")
    for symbol, sig_tf, gate_tf, min_s, max_s, seg_min, max_bars in [
        ("USOILm", "H2", "H4", 0.003, 0.01, 8, 120),
        ("XAUUSDm", "M30", "H4", 0.003, 0.008, 0, 240),
    ]:
        out.append(f"## {symbol}")
        out.append("")
        out.append("| 过滤器 | 全样本 | 2020-2024 | 2025-2026 |")
        out.append("|---|---|---|---|")
        res = eval_filters(symbol, sig_tf, gate_tf, min_s, max_s, seg_min, max_bars, None)
        if res is None:
            out.append(f"| - | 无候选 | | |")
            continue
        for name in ['F0', 'F1', 'F2', 'F3']:
            t = res[name]
            s_all = stats(t)
            s_early, s_late = split_stats(t)
            out.append(f"| {name} | {fmt(s_all)} | {fmt(s_early)} | {fmt(s_late)} |")
        out.append("")
    REP.mkdir(parents=True, exist_ok=True)
    (REP / "环境过滤器研究_v1.1.md").write_text("\n".join(out), encoding="utf-8")
    print("saved ->", REP / "环境过滤器研究_v1.1.md")
    print("\n".join(out))

if __name__ == "__main__":
    main()