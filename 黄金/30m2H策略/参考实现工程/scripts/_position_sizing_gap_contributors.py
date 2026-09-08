# -*- coding: utf-8 -*-
"""Explain which trades widen the gap between two position-sizing variants."""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))


RESULT_ROOT = os.path.join(ROOT, "data", "results", "position_sizing_strict_certify_20260628")
INPUT_CSV = os.path.join(RESULT_ROOT, "position_sizing_deep_dive_trades.csv")
GAP_CSV = os.path.join(RESULT_ROOT, "position_sizing_gap_contributors.csv")
MODE_CSV = os.path.join(RESULT_ROOT, "position_sizing_gap_by_mode.csv")
YEAR_CSV = os.path.join(RESULT_ROOT, "position_sizing_gap_by_year.csv")
REPORT_PATH = os.path.join(ROOT, "30m2H策略", "仓位档位差异交易分析.md")

BALANCED = "平衡推荐"
PEAK = "收益峰值"


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def main():
    df = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
    key_cols = ["date", "mode", "dir"]

    bal = df[df["variant_label"] == BALANCED].copy()
    peak = df[df["variant_label"] == PEAK].copy()

    merge_cols = key_cols + [
        "weighted_$", "weighted_points", "equity_$", "rr_multiple",
        "stage1_exit", "stage2_exit", "stage3_exit", "any_sl", "full_loss_trade", "year"
    ]
    bal = bal[merge_cols].rename(columns={
        "weighted_$": "balanced_$",
        "weighted_points": "balanced_pt",
        "equity_$": "balanced_eq_$",
        "rr_multiple": "balanced_rr",
        "any_sl": "balanced_any_sl",
        "full_loss_trade": "balanced_full_loss",
    })
    peak = peak[merge_cols].rename(columns={
        "weighted_$": "peak_$",
        "weighted_points": "peak_pt",
        "equity_$": "peak_eq_$",
        "rr_multiple": "peak_rr",
        "any_sl": "peak_any_sl",
        "full_loss_trade": "peak_full_loss",
    })

    merged = bal.merge(
        peak[key_cols + ["peak_$", "peak_pt", "peak_eq_$", "peak_rr", "peak_any_sl", "peak_full_loss"]],
        on=key_cols,
        how="inner",
    )
    merged["date"] = pd.to_datetime(merged["date"])
    merged["delta_$"] = merged["peak_$"] - merged["balanced_$"]
    merged["delta_pt"] = merged["peak_pt"] - merged["balanced_pt"]
    merged["cum_gap_$"] = merged["delta_$"].cumsum()
    merged["cum_gap_pt"] = merged["delta_pt"].cumsum()
    merged = merged.sort_values("date").reset_index(drop=True)
    merged.to_csv(GAP_CSV, index=False, encoding="utf-8-sig")

    by_mode = merged.groupby("mode").agg(
        trades=("delta_$", "size"),
        total_delta=("delta_$", "sum"),
        avg_delta=("delta_$", "mean"),
        win_gap_trades=("delta_$", lambda s: int((s > 0).sum())),
    ).reset_index()
    by_mode = by_mode.rename(columns={"total_delta": "total_delta_$", "avg_delta": "avg_delta_$"})
    by_mode = by_mode.sort_values("total_delta_$", ascending=False)
    by_mode.to_csv(MODE_CSV, index=False, encoding="utf-8-sig")

    by_year = merged.groupby("year").agg(
        trades=("delta_$", "size"),
        total_delta=("delta_$", "sum"),
        avg_delta=("delta_$", "mean"),
    ).reset_index()
    by_year = by_year.rename(columns={"total_delta": "total_delta_$", "avg_delta": "avg_delta_$"})
    by_year = by_year[["year", "trades", "total_delta_$", "avg_delta_$"]].sort_values("year")
    by_year.to_csv(YEAR_CSV, index=False, encoding="utf-8-sig")

    top_pos = merged.sort_values("delta_$", ascending=False).head(15)
    top_neg = merged.sort_values("delta_$", ascending=True).head(10)

    lines = []
    lines.append("# 仓位档位差异交易分析")
    lines.append("")
    lines.append("> 对比对象：`平衡推荐 0.5/1.0/1.5` vs `收益峰值 0.5/0.5/2.0`。")
    lines.append("")
    lines.append("## 差异总览")
    lines.append("")
    lines.append(f"- 收益峰值比平衡推荐最终多赚：`${merged['delta_$'].sum():.2f}`")
    lines.append(f"- 两者差距最大的单笔增益：`${merged['delta_$'].max():.2f}`")
    lines.append(f"- 两者差距最大的单笔回吐：`${merged['delta_$'].min():.2f}`")
    lines.append(f"- 正向拉开差距的交易：`{int((merged['delta_$'] > 0).sum())}` 笔")
    lines.append(f"- 反向缩小差距的交易：`{int((merged['delta_$'] < 0).sum())}` 笔")
    lines.append("")

    mode_rows = []
    for _, row in by_mode.iterrows():
        mode_rows.append([
            row["mode"],
            int(row["trades"]),
            f"${row['total_delta_$']:.2f}",
            f"${row['avg_delta_$']:.2f}",
            int(row["win_gap_trades"]),
        ])
    lines.append("## 按 Mode 看差距来源")
    lines.append("")
    lines.append(md_table(["Mode", "Trades", "总差额$", "单笔均值$", "正贡献笔数"], mode_rows))
    lines.append("")

    year_rows = []
    for _, row in by_year.iterrows():
        year_rows.append([
            int(row["year"]),
            int(row["trades"]),
            f"${row['total_delta_$']:.2f}",
            f"${row['avg_delta_$']:.2f}",
        ])
    lines.append("## 按年份看差距来源")
    lines.append("")
    lines.append(md_table(["Year", "Trades", "总差额$", "单笔均值$"], year_rows))
    lines.append("")

    pos_rows = []
    for _, row in top_pos.iterrows():
        pos_rows.append([
            f"{row['date']:%Y-%m-%d %H:%M}",
            row["mode"],
            row["dir"],
            f"${row['balanced_$']:.2f}",
            f"${row['peak_$']:.2f}",
            f"${row['delta_$']:.2f}",
            f"{row['balanced_rr']:+.2f}R",
            f"{row['peak_rr']:+.2f}R",
            row["stage1_exit"],
            row["stage2_exit"],
            row["stage3_exit"],
        ])
    lines.append("## 最能拉开差距的交易")
    lines.append("")
    lines.append(md_table(
        ["Date", "Mode", "Dir", "平衡$", "峰值$", "差额$", "平衡R", "峰值R", "Stage1", "Stage2", "Stage3"],
        pos_rows,
    ))
    lines.append("")

    neg_rows = []
    for _, row in top_neg.iterrows():
        neg_rows.append([
            f"{row['date']:%Y-%m-%d %H:%M}",
            row["mode"],
            row["dir"],
            f"${row['balanced_$']:.2f}",
            f"${row['peak_$']:.2f}",
            f"${row['delta_$']:.2f}",
            f"{row['balanced_rr']:+.2f}R",
            f"{row['peak_rr']:+.2f}R",
            row["stage1_exit"],
            row["stage2_exit"],
            row["stage3_exit"],
        ])
    lines.append("## 会缩小差距的交易")
    lines.append("")
    lines.append(md_table(
        ["Date", "Mode", "Dir", "平衡$", "峰值$", "差额$", "平衡R", "峰值R", "Stage1", "Stage2", "Stage3"],
        neg_rows,
    ))
    lines.append("")

    lines.append("## 当前判断")
    lines.append("")
    lines.append("- 收益峰值方案之所以更强，核心不是止损更少，而是把更多权重压到了 Stage 3 后，尾段大行情的单笔贡献被放大了。")
    lines.append("- 真正把差距拉大的，通常不是普通的小盈利单，而是那些 Stage 3 保留较长、最终吃到长尾利润的交易。")
    lines.append("- 反过来，缩小差距的交易多半是 Stage 3 没有走开，或者回撤后只留下很小尾段利润的单子。")
    lines.append("")
    lines.append("## 文件")
    lines.append("")
    lines.append(f"- `data\\results\\position_sizing_strict_certify_20260628\\{os.path.basename(GAP_CSV)}`")
    lines.append(f"- `data\\results\\position_sizing_strict_certify_20260628\\{os.path.basename(MODE_CSV)}`")
    lines.append(f"- `data\\results\\position_sizing_strict_certify_20260628\\{os.path.basename(YEAR_CSV)}`")
    lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))

    print(f"total_gap=${merged['delta_$'].sum():.2f}")
    print(by_mode.to_string(index=False))
    print(f"Wrote {GAP_CSV}")
    print(f"Wrote {MODE_CSV}")
    print(f"Wrote {YEAR_CSV}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
