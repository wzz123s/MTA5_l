# -*- coding: utf-8 -*-
"""模拟盘批次生成：黄金M15xH2 + 原油H1xH4（2025起）"""
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(r"F:\use_code\MTA5_l\V型反转策略")
DATA = BASE / "data"
CAL = Path(r"F:\use_code\MTA5_l\宏观日历研究\data\calendar_export.csv")

KEYWORDS = ["CPI", "FOMC", "EIA", "非农", "GDP", "PCE", "PPI", "失业率", "利率决议", "原油库存"]

def load_events():
    df = pd.read_csv(CAL, sep="|", usecols=["event_name", "importance", "time"])
    hi = df[df["importance"] >= 3]
    names = hi["event_name"].astype(str)
    mask = np.zeros(len(hi), dtype=bool)
    for kw in KEYWORDS:
        mask |= names.str.contains(kw, na=False)
    times = pd.to_datetime(hi.loc[mask, "time"], unit="s", utc=True)
    return sorted(times.tolist())

def before_event(t, events, hours):
    """t 之后 hours 小时内是否有高影响事件（红线3：事件前2h不开新仓）"""
    from bisect import bisect_left
    i = bisect_left(events, t)
    return i < len(events) and events[i] <= t + pd.Timedelta(hours=hours)

def max_consec_losses(rs):
    best = cur = 0
    for r in rs:
        if r <= 0: cur += 1; best = max(best, cur)
        else: cur = 0
    return best

def payoff_ratio(rs):
    w = rs[rs > 0]; l = rs[rs <= 0]
    aw = w.mean() if len(w) else 0.0
    al = -l.mean() if len(l) else 0.0
    return aw / al if al > 0 else float("inf")

def build_batch(tag, symbol, out_file):
    cand = pd.read_csv(DATA / ("period_cand_" + tag + ".csv"))
    trades = pd.read_csv(DATA / ("period_trades_" + tag + ".csv"))
    cand["signal_dt"] = pd.to_datetime(cand["signal_dt"], utc=True)
    trades["signal_dt"] = pd.to_datetime(trades["signal_dt"], utc=True)
    m = cand["signal_dt"] >= "2025-01-01"
    cand = cand[m].copy()
    tr = trades[trades["signal_dt"].isin(cand["signal_dt"])].copy()
    events = load_events()
    tr["pre_event"] = [before_event(t, events, 2) for t in tr["signal_dt"]]
    tr["discipline"] = ["合规" if not w else "违规-事件前2h" for w in tr["pre_event"]]
    rs = tr["R"].values
    n = len(tr)
    wins = int((rs > 0).sum())
    wsum = float(tr[tr.R > 0].R.sum()) if wins else 0.0
    lsum = -float(tr[tr.R <= 0].R.sum()) if (tr[tr.R <= 0].R.sum() < 0) else 0.0
    pf = wsum / lsum if lsum > 0 else float("inf")
    comply = int((tr["discipline"] == "合规").sum())
    stats = {"n": n, "wr": wins/n if n else 0, "payoff": payoff_ratio(rs),
             "max_loss": max_consec_losses(rs), "sumR": float(rs.sum()),
             "ev": float(rs.mean()) if n else 0.0, "comply": comply, "pf": pf}
    lines = ["# 模拟盘逐笔记录：" + symbol + "（" + out_file + "）", "",
             "> 批次：2025-01 起（最新数据至 2026-09-01）｜ 规则：S2B 顺势回归 + 段长8~30 + 48h冷却 + 结构止损 + 三段式退出",
             "> 信号源：scripts/validate_periods.py（period_cand/period_trades）",
             "> 合规口径：红线3=高影响事件前2h不开新仓（事件后信号允许，属优先做场景）", "",
             "| # | 信号时间(UTC) | 方向 | 入场 | 止损/距离 | 退出 | 结果R | 事件前2h | 纪律 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for i, r in tr.iterrows():
        cs = cand[cand["signal_dt"] == r["signal_dt"]]
        stop = float(cs["stop"].iloc[0]) if len(cs) else float("nan")
        sd = float(cs["sd_pct"].iloc[0]) if len(cs) else float("nan")
        ev = "是" if r["pre_event"] else "否"
        line = "| " + str(i+1) + " | " + str(r["signal_dt"]) + " | " + str(r["dir"]) + " | " + ("%.3f" % r["entry"]) + " | " + ("%.3f/%.2f%%" % (stop, sd)) + " | " + str(r["reason"]) + " | " + ("%+.2f" % r["R"]) + " | " + ev + " | " + r["discipline"] + " |"
        lines.append(line)
    lines += ["", "## 批次汇总", "",
              "- 笔数：" + str(stats["n"]) + " ｜ 合规：" + str(stats["comply"]) + "/" + str(stats["n"]),
              "- 胜率：" + ("%.1f%%" % (stats["wr"]*100)) + " ｜ 盈亏比：" + ("%.2f" % stats["payoff"]) + " ｜ 最大连亏：" + str(stats["max_loss"]),
              "- 总R：" + ("%+.2f" % stats["sumR"]) + " ｜ 平均R：" + ("%+.2f" % stats["ev"]) + " ｜ PF：" + ("%.2f" % stats["pf"]), "",
              "> 对照《04_阶段3模拟盘手册》20笔标准：合规≥90% / 盈亏比>1.5 / 最大连亏≤4 / 单笔风险≤1%（本批次为历史回放，风险按1%口径）", ""]
    (DATA / out_file).write_text("\n".join(lines), encoding="utf-8")
    print("===== " + symbol + " (" + tag + ") =====")
    print("  笔数=" + str(stats["n"]) + " 合规=" + str(stats["comply"]) + "/" + str(stats["n"]) + " 胜率=" + ("%.1f%%" % (stats["wr"]*100)) + " 盈亏比=" + ("%.2f" % stats["payoff"]) + " 最大连亏=" + str(stats["max_loss"]) + " 总R=" + ("%+.2f" % stats["sumR"]) + " PF=" + ("%.2f" % stats["pf"]))
    print("  -> " + out_file)
    print("  violations:", tr[tr["discipline"] != "合规"]["signal_dt"].tolist())
    return stats

s1 = build_batch("XAUUSDm_M15xH2_s2b_long_2.5", "XAUUSDm M15xH2 多", "模拟盘_黄金M15xH2.md")
s2 = build_batch("USOILm_H1xH4_s2b_short_2.5", "USOILm H1xH4 空", "模拟盘_原油H1xH4.md")