# -*- coding: utf-8 -*-
"""测试：EUR/GBP 利率类事件（利率决议/央行讲话/通胀）与黄金、原油的关系。

维度：
  A. 事件样本与频率
  B. 波动放大（±30m/±60m/后4h |收益| vs 基线）
  C. 方向性（净位移/绝对路径 = 方向一致性；事件后4h净位移 vs 基线）
  D. 策略交易交叉（开仓前24h内发生该类事件的交易表现 vs 无事件，置换检验）
"""
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
OUT = RESEARCH / "报告" / "EUR_GBP利率事件与黄金原油测试.md"

ev = pd.read_csv(RESEARCH / "data" / "calendar_export.csv", sep="|", dtype={"event_id": "int64", "time": "int64"})
ev["t"] = pd.to_datetime(ev["time"], unit="s", utc=True)
ev["is_high"] = ev["importance"] >= 3
hi = ev[ev["is_high"]].sort_values("t").reset_index(drop=True)

lines = []
def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    lines.append(s)

# ---- 事件分类 ----
def classify_mp(row):
    name = str(row["event_name"])
    cur = str(row["currency"])
    n = name
    if cur == "EUR":
        if ("利率决议" in n or "存款便利" in n or "再融资利率" in n or "边际贷款利率" in n) and "预期" not in n:
            return "EUR利率决议"
        if ("行长" in n or "主席" in n or "讲话" in n or "Lagarde" in n or "拉加德" in n):
            return "EUR央行讲话"
        if "CPI" in n or "通胀" in n or "调和" in n or "HICP" in n:
            return "EUR通胀"
    if cur == "GBP":
        if ("利率决定" in n or "利率决议" in n or "BoE" in n and "利率" in n):
            return "GBP利率决议"
        if ("行长" in n or "讲话" in n or "Bailey" in n or "贝利" in n):
            return "GBP央行讲话"
        if "CPI" in n or "通胀" in n:
            return "GBP通胀"
    if cur == "USD" and ("利率决议" in n or "FOMC" in n and "利率" in n or "联邦基金" in n):
        return "USD利率决议(FOMC)"
    return None

hi = hi.copy()
hi["mp"] = hi.apply(classify_mp, axis=1)
mp_ev = hi[hi["mp"].notna()].copy()
P("# EUR/GBP 利率类事件 vs 黄金/原油 专项测试\n")

P("## A. 样本（高影响事件，2019-2026）")
for mp, g in mp_ev.groupby("mp"):
    P(f"- {mp}: {len(g)} 条（{g['t'].min().date()} ~ {g['t'].max().date()}）")
P(f"- 对照组 USD利率决议(FOMC): {len(mp_ev[mp_ev['mp']=='USD利率决议(FOMC)'])} 条")
P(f"- 全部高影响事件: {len(hi)} 条")

def load_bars(rel):
    df = pd.read_csv(ROOT / rel, parse_dates=["time"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.sort_values("time").reset_index(drop=True)

def ret(bars, t, bh, ah):
    m = (bars["time"] >= t - pd.Timedelta(hours=bh)) & (bars["time"] <= t + pd.Timedelta(hours=ah))
    sub = bars[m]
    if len(sub) < 2:
        return np.nan
    return float(sub["close"].iloc[-1] / sub["open"].iloc[0] - 1.0)

def path60(bars, t):
    m = (bars["time"] >= t - pd.Timedelta(hours=1)) & (bars["time"] <= t + pd.Timedelta(hours=1))
    sub = bars[m]
    if len(sub) < 3:
        return np.nan, np.nan
    closes = sub["close"].to_numpy(dtype=float)
    path = np.abs(np.diff(closes)).sum()
    disp = abs(closes[-1] - closes[0])
    return path, disp

P("\n## B/C. 波动与方向性（黄金 XAUUSD / 原油 USOIL）")
for sym, rel in [("XAUUSD黄金", "黄金/1H_M30_4H策略/data/raw/mt5_history/1h_m30_4h_live/XAUUSDm_M30.csv"),
                 ("USOIL原油", "原油/原油2H策略/data/raw/mt5_history/usoil2h_live/USOILm_M30.csv")]:
    bars = load_bars(rel)
    t0, t1 = bars["time"].min(), bars["time"].max()
    mask = (bars["time"] >= t0 + pd.Timedelta(hours=1)) & (bars["time"] <= t1 - pd.Timedelta(hours=1))
    closes = bars.loc[mask, "close"].to_numpy(dtype=float)
    base_ret = np.abs(np.diff(closes) / closes[:-1]).mean()
    # 基线方向性：1h窗口 净位移/路径
    bp, bd = [], []
    for i in range(0, len(bars) - 8, 4):
        w = bars.iloc[i:i + 5]["close"].to_numpy(dtype=float)
        if len(w) == 5:
            bp.append(np.abs(np.diff(w)).sum())
            bd.append(abs(w[-1] - w[0]))
    base_ratio = np.mean(bd) / np.mean(bp) if np.mean(bp) > 0 else np.nan
    P(f"\n### {sym}（基线 ±60m|收益|={base_ret:.5f}，方向一致性=净位移/路径={base_ratio:.2f}）")
    P("| 事件类 | n | ±30m | ±60m | 后4h | 方向一致性(±60m) | 后4h净位移倍数 |")
    P("|---|---|---|---|---|---|---|")
    groups = {
        "EUR利率决议": mp_ev[mp_ev["mp"] == "EUR利率决议"],
        "EUR央行讲话": mp_ev[mp_ev["mp"] == "EUR央行讲话"],
        "EUR通胀": mp_ev[mp_ev["mp"] == "EUR通胀"],
        "GBP利率决议": mp_ev[mp_ev["mp"] == "GBP利率决议"],
        "GBP央行讲话": mp_ev[mp_ev["mp"] == "GBP央行讲话"],
        "GBP通胀": mp_ev[mp_ev["mp"] == "GBP通胀"],
        "EUR+GBP利率类合计": mp_ev[mp_ev["mp"].str.startswith(("EUR", "GBP"))],
        "USD-FOMC(对照)": mp_ev[mp_ev["mp"] == "USD利率决议(FOMC)"],
        "全部高影响": hi,
    }
    for label, g in groups.items():
        g = g[(g["t"] >= t0) & (g["t"] <= t1)]
        if len(g) == 0:
            continue
        r30 = [r for r in (ret(bars, t, 0.5, 0.5) for t in g["t"]) if not np.isnan(r)]
        r60 = [r for r in (ret(bars, t, 1, 1) for t in g["t"]) if not np.isnan(r)]
        r4h = [r for r in (ret(bars, t, 0, 4) for t in g["t"]) if not np.isnan(r)]
        ratios = []
        disps = []
        for t in g["t"]:
            pth, disp = path60(bars, t)
            if not np.isnan(pth) and pth > 0:
                ratios.append(disp / pth)
                disps.append(disp)
        m30 = np.mean(np.abs(r30)) / base_ret if r30 else np.nan
        m60 = np.mean(np.abs(r60)) / base_ret if r60 else np.nan
        m4h = np.mean(np.abs(r4h)) / base_ret if r4h else np.nan
        mratio = np.mean(ratios) if ratios else np.nan
        mdisp = np.mean(disps) if disps else np.nan
        mdisp_base = np.mean(bd) if bd else np.nan
        P(f"| {label} | {len(g)} | {m30:.2f}x | {m60:.2f}x | {m4h:.2f}x | {mratio:.2f} | {mdisp/mdisp_base:.2f}x |")

P("\n## D. 策略交易交叉（开仓前24h内发生 EUR/GBP 利率类事件）")
hi_mp = hi[hi["mp"].notna() & hi["mp"].str.startswith(("EUR", "GBP"))]
hits = np.sort(hi_mp["t"].to_numpy(dtype="datetime64[ns]"))
P("| 策略 | 事件前24h内 n | 平均(pts) | 无事件 n | 平均(pts) | 差值 | p值 |")
P("|---|---|---|---|---|---|---|")
from collections import Counter
for strat in ["1H_M30_4H", "30m2H", "2H_M30_6H", "BiasReversal", "USOIL2H", "USOIL4H"]:
    f = ROOT / "observation_dashboard" / strat / "trades_snapshot.csv"
    if not f.exists():
        continue
    df = pd.read_csv(f, parse_dates=["signal_time"])
    df["signal_time"] = pd.to_datetime(df["signal_time"], utc=True)
    st = df["signal_time"].to_numpy(dtype="datetime64[ns]")
    idx = np.searchsorted(hits, st)
    within = np.zeros(len(st), dtype=bool)
    for i in range(len(st)):
        j = idx[i]
        if j > 0 and (st[i] - hits[j - 1]) <= np.timedelta64(24, "h"):
            within[i] = True
    w = df["weighted_pts"].to_numpy(dtype=float)
    if within.sum() < 8:
        P(f"| {strat} | {int(within.sum())}（样本不足） | - | - | - | - | - |")
        continue
    a, b = w[within], w[~within]
    rng = np.random.default_rng(42)
    pooled = np.concatenate([a, b])
    perm = np.array([np.mean(rng.permutation(pooled)[:len(a)]) - np.mean(rng.permutation(pooled)[len(a):]) for _ in range(2000)])
    obs = a.mean() - b.mean()
    pval = (np.abs(perm) >= np.abs(obs)).mean()
    P(f"| {strat} | {len(a)} | {a.mean():+,.1f} | {len(b)} | {b.mean():+,.1f} | {obs:+,.1f} | {pval:.3f} |")

OUT.write_text("\n".join(lines), encoding="utf-8")
P(f"\n[已输出] {OUT}")
