# -*- coding: utf-8 -*-
"""三个警戒策略深度分析：1H_M30_4H / USOIL4H / BiasReversal。

维度：年度/月度、退出原因、信号模式、多空、连亏与冷却、高影响事件邻近。
输出: 报告/警戒策略深度分析.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
RESEARCH = ROOT / "宏观日历研究"
sys.path.insert(0, str(RESEARCH / "scripts"))
from classify_events import classify  # noqa: E402

REPORT_DIR = RESEARCH / "报告"
EVENTS_CSV = RESEARCH / "data" / "calendar_export.csv"
STRATS = ["1H_M30_4H", "USOIL4H", "BiasReversal"]


def load_trades(strat: str) -> pd.DataFrame:
    path = ROOT / "observation_dashboard" / strat / "trades_snapshot.csv"
    df = pd.read_csv(path, parse_dates=["signal_time", "stage3_exit_time"])
    df["signal_time"] = pd.to_datetime(df["signal_time"], utc=True)
    df["stage3_exit_time"] = pd.to_datetime(df["stage3_exit_time"], utc=True)
    df["dir"] = df["dir"].astype(str).str.upper()
    df["mode"] = df["mode"].astype(str)
    df["reason"] = df["stage3_reason"].astype(str)
    return df.sort_values("signal_time").reset_index(drop=True)


def load_events():
    df = pd.read_csv(EVENTS_CSV, sep="|", dtype={"event_id": "int64", "time": "int64"})
    df["time_utc"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df["is_high"] = df["importance"] >= 3
    df["category"] = df["event_name"].map(classify)
    return df


def fmt(v):
    return f"{v:+.0f}"


def section(lines, title):
    lines.append("")
    lines.append(f"## {title}")
    lines.append("")


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events()
    high = events[events["is_high"]].sort_values("time_utc").reset_index(drop=True)
    eh = high["time_utc"].to_numpy(dtype="datetime64[ns]")

    lines = ["# 三个警戒策略深度分析（2026-08-27）", ""]
    lines.append("> 数据：observation_dashboard/trades_snapshot.csv（监控重放口径）+ MT5 日历高影响事件（importance>=3）。")
    lines.append("> 说明：加权盈亏为策略自身点数口径（各策略换算系数不同，横向不可直接比）。")

    for strat in STRATS:
        df = load_trades(strat)
        w = df["weighted_pts"].to_numpy(float)
        section(lines, f"{strat}（n={len(df)}，累计 {w.sum():+,.0f} pts）")

        # 1) 年度
        lines.append("### 年度")
        lines.append("| 年 | n | 胜率 | 合计 | PF(按信号) |")
        lines.append("|---|---|---|---|---|")
        y = df.assign(y=df["signal_time"].dt.year)
        for yr, g in y.groupby("y"):
            gp = g["weighted_pts"]
            wins, losses = gp[gp > 0].sum(), -gp[gp < 0].sum()
            pf = wins / losses if losses > 0 else float("inf")
            lines.append(f"| {yr} | {len(g)} | {(gp > 0).mean():.0%} | {gp.sum():+,.0f} | {pf:.2f} |")

        # 2) 最近14个月逐月
        lines.append("")
        lines.append("### 最近14个月")
        lines.append("| 月 | n | 合计 | 平均 |")
        lines.append("|---|---|---|---|")
        m = df.assign(month=df["signal_time"].dt.to_period("M")).groupby("month")["weighted_pts"]
        tail = m.agg(["count", "sum", "mean"]).tail(14)
        for month, row in tail.iterrows():
            lines.append(f"| {month} | {int(row['count'])} | {row['sum']:+,.0f} | {row['mean']:+,.1f} |")

        # 3) 退出原因分解
        lines.append("")
        lines.append("### 退出原因（加权盈亏）")
        lines.append("| 原因 | n | 合计 | 平均 | 胜率 |")
        lines.append("|---|---|---|---|---|")
        for reason, g in df.groupby("reason"):
            gp = g["weighted_pts"]
            lines.append(f"| {reason} | {len(g)} | {gp.sum():+,.0f} | {gp.mean():+,.1f} | {(gp > 0).mean():.0%} |")

        # 4) 模式分解
        lines.append("")
        lines.append("### 信号模式")
        lines.append("| 模式 | n | 合计 | 平均 | 胜率 |")
        lines.append("|---|---|---|---|---|")
        for mode, g in df.groupby("mode"):
            gp = g["weighted_pts"]
            lines.append(f"| {mode} | {len(g)} | {gp.sum():+,.0f} | {gp.mean():+,.1f} | {(gp > 0).mean():.0%} |")

        # 5) 多空
        lines.append("")
        lines.append("### 多/空")
        for d, g in df.groupby("dir"):
            gp = g["weighted_pts"]
            lines.append(f"- {d}: n={len(g)} 合计={gp.sum():+,.0f} 平均={gp.mean():+,.1f} 胜率={(gp > 0).mean():.0%}")

        # 6) 连亏统计（信号序）
        lines.append("")
        lines.append("### 连亏与冷却模拟")
        streak = 0
        max_streak = 0
        n_streaks = 0
        prev_win = None
        for v in w:
            if v < 0:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                if streak >= 2:
                    n_streaks += 1
                streak = 0
        if streak >= 2:
            n_streaks += 1
        lines.append(f"- 最大连亏: {max_streak} 笔；≥2连亏段: {n_streaks} 段（损失冷却会在这之后暂停120h）")
        # 2连亏后的下一笔表现
        nxt = []
        for i in range(1, len(w)):
            if w[i - 1] < 0 and w[i] < 0:
                if i + 1 < len(w):
                    nxt.append(w[i + 1])
        if nxt:
            lines.append(f"- 2连亏后立即再开的那笔: n={len(nxt)} 合计={sum(nxt):+,.0f} 平均={np.mean(nxt):+,.1f} 胜率={(np.array(nxt) > 0).mean():.0%}")

        # 7) 高影响事件邻近
        st = df["signal_time"].to_numpy(dtype="datetime64[ns]")
        idx = np.searchsorted(eh, st)
        gap_after = np.array([float((eh[j] - st[i]) / np.timedelta64(1, "h")) if j < len(eh) else np.nan
                              for i, j in enumerate(idx)])
        lines.append("")
        lines.append("### 高影响事件邻近（开仓距下一事件）")
        lines.append("| 窗口 | n | 合计 | 平均 | 胜率 |")
        lines.append("|---|---|---|---|---|")
        for T in [1, 2, 4, 8, 24]:
            m_ = gap_after <= T
            gp = df.loc[m_, "weighted_pts"]
            if len(gp):
                lines.append(f"| 事件前{T}h内 | {len(gp)} | {gp.sum():+,.0f} | {gp.mean():+,.1f} | {(gp > 0).mean():.0%} |")
        gp = df.loc[~(gap_after <= 24), "weighted_pts"]
        if len(gp):
            lines.append(f"| 24h外 | {len(gp)} | {gp.sum():+,.0f} | {gp.mean():+,.1f} | {(gp > 0).mean():.0%} |")

        # 8) 事件类别（前24h）
        lines.append("")
        lines.append("### 事件类别（开仓前24h内发生）")
        lines.append("| 类别 | n | 合计 | 平均 |")
        lines.append("|---|---|---|---|")
        for cat in high["category"].value_counts().index[:12]:
            evs = high[high["category"] == cat]["time_utc"].to_numpy(dtype="datetime64[ns]")
            within = np.zeros(len(st), dtype=bool)
            for i in range(len(st)):
                j = np.searchsorted(evs, st[i])
                if j > 0 and (st[i] - evs[j - 1]) <= np.timedelta64(24, "h"):
                    within[i] = True
            if within.sum() >= 5:
                gp = df.loc[within, "weighted_pts"]
                lines.append(f"| {cat} | {int(within.sum())} | {gp.sum():+,.0f} | {gp.mean():+,.1f} |")

    lines.append("")
    lines.append("---")
    lines.append("*生成：宏观日历研究/scripts/deep_analyze_warnings.py*")
    out = REPORT_DIR / "警戒策略深度分析.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("written:", out)


if __name__ == "__main__":
    main()
