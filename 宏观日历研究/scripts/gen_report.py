# -*- coding: utf-8 -*-
"""把三个分析CSV汇总为Markdown报告。"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

import pandas as pd

REPORT_DIR = Path(r"F:\use_code\MTA5_l\宏观日历研究\报告")


def load(name: str) -> pd.DataFrame:
    p = REPORT_DIR / name
    if not p.exists():
        print(f"警告: 缺少 {p}")
        return pd.DataFrame()
    return pd.read_csv(p)


def num(v, nd=2):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "-"
    if pd.isna(f):
        return "-"
    if abs(f) >= 1000:
        return f"{f:,.0f}"
    return f"{f:.{nd}f}"


def main():
    proximity = load("事件邻近_汇总.csv")
    volatility = load("波动率验证_汇总.csv")
    variants = load("过滤变体_汇总.csv")

    lines = []
    lines.append("# 宏观日历 × 策略影响分析报告")
    lines.append("")
    lines.append(f"> 生成时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append("## 1. 事件邻近度分析（阶段2）")
    lines.append("")
    lines.append("高影响事件（impact=HIGH）窗口内开仓 vs 窗口外开仓的交易表现对比。"
                 "diff 为均值差（窗口内 − 窗口外），bootstrap 95% CI 与置换检验 p 值。")
    lines.append("")
    if not proximity.empty:
        base = proximity[proximity["bucket"].isna()].copy() if "bucket" in proximity.columns else proximity[proximity["variant"].isna()].copy()
        lines.append("### 基线")
        lines.append("")
        lines.append("| 策略 | 交易数 | 胜率 | 平均盈亏(pts) |")
        lines.append("|---|---|---|---|")
        if "bucket" in proximity.columns:
            for _, r in proximity[proximity["bucket"].isna()].iterrows():
                lines.append(f"| {r['strategy']} | {int(r['n'])} | {r['win_rate']:.1%} | {num(r['avg_pts'])} |")
            buckets = proximity[~proximity["bucket"].isna()].copy()
            for w in [1, 2, 4, 8, 12, 24]:
                wrows = buckets[buckets["bucket"] == f"±{w}h内"].copy()
                if wrows.empty:
                    continue
                lines.append(f"### ±{w}h 窗口")
                lines.append("")
                lines.append("| 策略 | 窗口内n | 窗口内胜率 | 窗口内平均 | 窗口外n | 窗口外平均 | p值 |")
                lines.append("|---|---|---|---|---|---|---|")
                for _, r in wrows.iterrows():
                    outside = buckets[(buckets["strategy"] == r["strategy"]) & (buckets["bucket"] == f"±{w}h外")]
                    o = outside.iloc[0] if len(outside) else None
                    p = num(r.get("p"), 3) if "p" in r.index else "-"
                    lines.append(f"| {r['strategy']} | {int(r['n'])} | {r['win_rate']:.1%} | {num(r['avg_pts'])} | "
                                 f"{int(o['n']) if o is not None else '-'} | {num(o['avg_pts']) if o is not None else '-'} | {p} |")
    lines.append("")

    lines.append("## 2. 波动率验证（阶段3）")
    lines.append("")
    lines.append("高影响事件窗口内平均 |收益率| 与全样本基线的倍数。倍数 > 1 表示事件确实放大波动。")
    lines.append("")
    if not volatility.empty:
        v = volatility[~volatility["window"].str.contains("bycat", na=False)]
        for _, r in v.iterrows():
            lines.append(f"- {r['symbol']} {r['window']}: 事件窗口平均 {r['event_mean_abs_ret']:.5f} vs 基线 {r['baseline_mean_abs_ret']:.5f} → **{r['ratio']:.2f}x**")
        lines.append("")
        lines.append("### 按事件类别（±60m）")
        lines.append("")
        lines.append("| 品种 | 类别 | n | 倍数 |")
        lines.append("|---|---|---|---|")
        for _, r in volatility[volatility["window"].str.contains("bycat", na=False)].iterrows():
            lines.append(f"| {r['symbol']} | {r['category']} | {int(r.get('event_n', 0)) if 'event_n' in r.index else '-'} | {r['ratio']:.2f}x |")

    lines.append("")
    lines.append("## 3. 改进变体模拟（阶段4）")
    lines.append("")
    lines.append("| 策略 | 变体 | n | 胜率 | 平均(pts) | 合计(pts) | PF | MaxDD(pts) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    if not variants.empty:
        for _, r in variants.iterrows():
            pf = "inf" if pd.isna(r.get("profit_factor")) or r["profit_factor"] == float("inf") else num(r["profit_factor"])
            lines.append(f"| {r['strategy']} | {r['variant']} | {int(r['n'])} | {r['win_rate']:.1%} | {num(r['avg_pts'])} | "
                         f"{num(r['total_pts'])} | {pf} | {num(r['max_dd_pts'])} |")

    lines.append("")
    lines.append("## 4. 结论与建议")
    lines.append("")
    lines.append("（待分析完成后由研究员填写：事件过滤/避险是否采纳、参数建议、EA 接入方案）")
    lines.append("")

    out = REPORT_DIR / "宏观日历影响分析报告.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("written:", out)


if __name__ == "__main__":
    main()
