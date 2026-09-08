# -*- coding: utf-8 -*-
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
OUT = RESEARCH / "报告" / "事件币种影响分析.md"

ev = pd.read_csv(RESEARCH / "data" / "calendar_export.csv", sep="|", dtype={"event_id": "int64", "time": "int64"})
ev["t"] = pd.to_datetime(ev["time"], unit="s", utc=True)
ev["is_high"] = ev["importance"] >= 3
hi = ev[ev["is_high"]].sort_values("t").reset_index(drop=True)

lines = []
def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    lines.append(s)

P("# 事件币种影响分析（东京CPI 等非USD事件 vs USD）\n")
P("## 高影响事件按币种分布（importance>=3, 共", len(hi), "）")
for cur, n in hi["currency"].value_counts().head(12).items():
    P(f"- {cur}: {n}")

tokyo = hi[hi["event_name"].str.contains("东京", na=False)]
P("\n## 东京CPI（高影响样本）:", len(tokyo), "条")
for _, r in tokyo.head(8).iterrows():
    P(f"- {r['t']}  {r['event_name']}  {r['currency']}")

def load_bars(rel):
    df = pd.read_csv(ROOT / rel, parse_dates=["time"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.sort_values("time").reset_index(drop=True)

def ret60(bars, t):
    m = (bars["time"] >= t - pd.Timedelta(hours=1)) & (bars["time"] <= t + pd.Timedelta(hours=1))
    sub = bars[m]
    if len(sub) < 2:
        return np.nan
    return abs(float(sub["close"].iloc[-1] / sub["open"].iloc[0] - 1.0))

P("\n## 事件前后 ±60m 波动倍数（基线=全样本平均|收益|）")
for sym, rel in [("XAUUSD(黄金)", "黄金/1H_M30_4H策略/data/raw/mt5_history/1h_m30_4h_live/XAUUSDm_M30.csv"),
                 ("USOIL(原油)", "原油/原油2H策略/data/raw/mt5_history/usoil2h_live/USOILm_M30.csv")]:
    bars = load_bars(rel)
    t0, t1 = bars["time"].min(), bars["time"].max()
    mask = (bars["time"] >= t0 + pd.Timedelta(hours=1)) & (bars["time"] <= t1 - pd.Timedelta(hours=1))
    base = np.abs(bars.loc[mask, "close"].values[1:] / bars.loc[mask, "close"].values[:-1] - 1.0).mean()
    evs = hi[(hi["t"] >= t0) & (hi["t"] <= t1)]
    P(f"\n### {sym}（基线 {base:.5f}）")
    for label, g in [("全部高影响", evs), ("USD事件", evs[evs["currency"] == "USD"]),
                     ("非USD事件", evs[evs["currency"] != "USD"]),
                     ("JPY事件", evs[evs["currency"] == "JPY"]),
                     ("东京CPI", evs[evs["event_name"].str.contains("东京", na=False)])]:
        rs = [r for r in (ret60(bars, t) for t in g["t"]) if not np.isnan(r)]
        if rs:
            P(f"- {label}: n={len(g):>4} 事件窗口均值={np.mean(rs):.5f} 倍数={np.mean(rs)/base:.2f}x")

P("\n## USOIL4H 事件门(T=4h) 拦截信号的触发事件归属")
from validate_usoil_gate_strategy import STRATEGIES as GATE_STRATEGIES, build_triggers, gate_check, load_2h, load_gate
strategy_dir = ROOT / "原油" / "原油4H门策略"
cfg = GATE_STRATEGIES["原油4H门策略"]
tf2 = load_2h(strategy_dir)
gt = load_gate(strategy_dir, cfg)
trig = build_triggers(tf2)
check = gate_check(gt, cfg["n_min"], cfg["thr"], *cfg["amp"])
keep = [check(t, r["dir"] == "L") for t, r in zip(trig["signal_time"], trig.to_dict("records"))]
trades = trig.loc[keep].copy().reset_index(drop=True)
st = pd.to_datetime(trades["signal_time"]).to_numpy(dtype="datetime64[ns]")
hits = hi["t"].to_numpy(dtype="datetime64[ns]")
idx = np.searchsorted(hits, st)
gap = np.array([(hits[j] - st[i]) / np.timedelta64(1, "h") if j < len(hits) else np.nan for i, j in enumerate(idx)])
blocked = gap <= 4
P(f"拦截 {int(blocked.sum())} 笔（共 {len(trades)} 笔）:")
from collections import Counter
cnt = Counter()
for i in np.where(blocked)[0]:
    j = idx[i]
    er = hi.iloc[j]
    cnt[(er["currency"], er["event_name"])] += 1
    w = float(pd.to_numeric(trades["pnl_points"].iloc[i], errors="coerce")) * 1000.0
    P(f"  {trades['signal_time'].iloc[i]} gap={gap[i]:.2f}h {er['currency']} {er['event_name']} | 该笔盈亏={w:+,.0f}pts")
P("\n按币种汇总被拦信号:")
for (cur, name), n in cnt.most_common(15):
    P(f"- {cur} [{name}]: {n} 笔")

OUT.write_text("\n".join(lines), encoding="utf-8")
P(f"\n[已输出] {OUT}")
