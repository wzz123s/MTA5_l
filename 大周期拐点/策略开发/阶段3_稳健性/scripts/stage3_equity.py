# -*- coding: utf-8 -*-
"""
stage3_equity.py —— 复利资金曲线 + 最大回撤 + 滚动12月年正口径 + 组合

资金：1% 固定分数复利（equity *= (1 + 0.01 * pnl_R)），逐笔按时间序
输出：V3_资金曲线指标.csv（单品种+组合） + V3_滚动12月年正.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "阶段1_机会层统计" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "阶段2_全链路回测" / "scripts"))
import stage1_common as C
import stage2_backtest as B2

PROC = Path(__file__).resolve().parent / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

CONFIGS = {
    "XAUUSDm": dict(long_only=True, spec=("pct", 0.003, 0.02), exit_mode="break",
                    eff="2017-03-01", spread=0.10, swap=0.002),
    "USOILm": dict(long_only=False, spec=("pct", 0.008, 0.025), exit_mode="hybrid",
                   eff="2021-07-01", spread=0.03, swap=0.0005),
}


def get_trades(sym, cfg):
    d1 = C.analyze_tf(sym, "D1")
    h4 = C.analyze_tf(sym, "H4")
    cr = C.find_cross13_55(d1)
    cr = cr[pd.to_datetime(cr["time"]) >= cfg["eff"]].reset_index(drop=True)
    return B2.fullchain_backtest(d1, h4, cr, sym, "D1", "H4",
                                 glue_thresh=0.003, bias_floor=0.0,
                                 stop_mode="sub_struct", stop_spec=cfg["spec"],
                                 exit_mode=cfg["exit_mode"], time_exit_bars=120,
                                 long_only=cfg["long_only"],
                                 spread_price=cfg["spread"], swap_per_bar=cfg["swap"],
                                 start=cfg["eff"])


def equity_curve(trades, risk=0.01):
    df = trades.sort_values("time").reset_index(drop=True)
    eq = 100.0
    curve = [{"time": pd.to_datetime(df["time"].iloc[0]), "equity": eq}]
    for _, r in df.iterrows():
        eq = eq * (1 + risk * r["pnl_R"])
        curve.append({"time": pd.to_datetime(r["time"]), "equity": eq,
                      "pnl_R": r["pnl_R"]})
    return pd.DataFrame(curve)


def max_drawdown(eq):
    peak = eq["equity"].cummax()
    dd = eq["equity"] / peak - 1
    return dd.min(), dd.idxmin()


def rolling12m_winrate(trades, eff):
    """滚动 12 个月窗口（月步长）内 sum_R 为正的比例。"""
    df = trades.copy()
    df["t"] = pd.to_datetime(df["time"])
    months = pd.period_range(eff, "2026-08", freq="M")
    pos = 0
    tot = 0
    for i in range(len(months) - 12):
        s = months[i].start_time
        e = months[i + 11].end_time
        sub = df[(df["t"] >= s) & (df["t"] <= e)]
        tot += 1
        if sub["pnl_R"].sum() > 0:
            pos += 1
    return pos / tot * 100 if tot else None, tot


def main():
    trades = {}
    curves = {}
    rows = []
    print("== 复利资金曲线（1% 固定分数）==")
    for sym, cfg in CONFIGS.items():
        tr = get_trades(sym, cfg)
        trades[sym] = tr
        cu = equity_curve(tr)
        curves[sym] = cu
        mdd, mdd_i = max_drawdown(cu)
        final = cu["equity"].iloc[-1]
        years = (cu["time"].iloc[-1] - cu["time"].iloc[0]).days / 365.25
        cagr = (final / 100) ** (1 / years) - 1 if years > 0 else 0
        rows.append({"symbol": sym, "n": len(tr), "final_equity": round(final, 1),
                     "total_return_pct": round(final - 100, 1),
                     "max_dd_pct": round(mdd * 100, 1),
                     "cagr_pct": round(cagr * 100, 2),
                     "years": round(years, 1)})
        print(f"  {sym}: n={len(tr)} 终值={final:.1f}（+{final-100:.1f}%） "
              f"最大回撤={mdd*100:.1f}% CAGR={cagr*100:.2f}%")

    # 组合（合并按时间排序，1% 风险/笔，总风险≤2%）
    comb = pd.concat([trades["XAUUSDm"].assign(sym="G"),
                      trades["USOILm"].assign(sym="O")]).sort_values("time").reset_index(drop=True)
    eq = 100.0
    peak = eq
    mdd_c = 0.0
    for _, r in comb.iterrows():
        eq = eq * (1 + 0.01 * r["pnl_R"])
        peak = max(peak, eq)
        mdd_c = min(mdd_c, eq / peak - 1)
    years_c = (pd.to_datetime(comb["time"].iloc[-1]) - pd.to_datetime(comb["time"].iloc[0])).days / 365.25
    cagr_c = (eq / 100) ** (1 / years_c) - 1 if years_c > 0 else 0
    rows.append({"symbol": "组合(G+O)", "n": len(comb), "final_equity": round(eq, 1),
                 "total_return_pct": round(eq - 100, 1), "max_dd_pct": round(mdd_c * 100, 1),
                 "cagr_pct": round(cagr_c * 100, 2), "years": round(years_c, 1)})
    print(f"  组合(G+O): n={len(comb)} 终值={eq:.1f}（+{eq-100:.1f}%）最大回撤={mdd_c*100:.1f}% CAGR={cagr_c*100:.2f}%")

    print()
    print("== 滚动 12 个月年正收益（修订口径）==")
    for sym in ["XAUUSDm", "USOILm"]:
        wr, tot = rolling12m_winrate(trades[sym], CONFIGS[sym]["eff"])
        print(f"  {sym}: 滚动12月窗口 {tot} 个，正收益占比 {wr:.1f}% "
              f"({'✅ ≥80%' if wr >= 80 else '❌ <80%'})")

    pd.DataFrame(rows).to_csv(PROC / "V3_资金曲线指标.csv", index=False, encoding="utf-8-sig")

    lines = ["# 复利资金曲线与滚动12月口径（阶段3）", "",
             "| 组合 | n | 终值 | 总收益 | 最大回撤 | CAGR | 年数 |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['symbol']} | {r['n']} | {r['final_equity']} | {r['total_return_pct']}% "
                     f"| {r['max_dd_pct']}% | {r['cagr_pct']}% | {r['years']} |")
    lines += ["", "## 滚动 12 个月年正收益（修订口径，替代年度口径）"]
    for sym in ["XAUUSDm", "USOILm"]:
        wr, tot = rolling12m_winrate(trades[sym], CONFIGS[sym]["eff"])
        lines.append(f"- {sym}：{tot} 个滚动12月窗口，正收益占比 {wr:.1f}%")
    (PROC / "V3_资金曲线汇总.md").write_text("\n".join(lines), encoding="utf-8")
    print("  已保存 V3_资金曲线指标.csv / V3_资金曲线汇总.md")


if __name__ == "__main__":
    main()
