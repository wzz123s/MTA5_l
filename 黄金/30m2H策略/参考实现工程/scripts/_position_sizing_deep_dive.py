# -*- coding: utf-8 -*-
"""Deep-dive comparison for selected position sizing variants."""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import _current_baseline as base
import _position_sizing_strict_certify as ps


RESULT_ROOT = os.path.join(ROOT, "data", "results", "position_sizing_strict_certify_20260628")
SUMMARY_CSV = os.path.join(RESULT_ROOT, "position_sizing_deep_dive_summary.csv")
DETAIL_CSV = os.path.join(RESULT_ROOT, "position_sizing_deep_dive_trades.csv")
REPORT_PATH = os.path.join(ROOT, "30m2H策略", "仓位档位详细分析.md")

TARGETS = [
    ((0.5, 1.0, 1.5), "平衡推荐"),
    ((0.5, 0.5, 2.0), "收益峰值"),
]


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def risk_points_per_trade(row):
    exit_name = str(row["stage1_exit"])
    pnl = float(row["stage1_pnl"])
    if exit_name.endswith("R TP"):
        return abs(pnl) / 2.0
    if exit_name == "SL hit":
        return abs(pnl)
    return pd.NA


def analyze_variant(frame, label):
    frame = frame.copy().reset_index(drop=True)
    total_units = sum(float(x) for x in str(frame.loc[0, "units"]).split("/"))

    frame["risk_points"] = frame.apply(risk_points_per_trade, axis=1)
    frame["risk_$"] = frame["risk_points"].astype(float) * total_units * ps.UNIT_LOT * ps.PT_VALUE_PER_LOT
    frame["rr_multiple"] = frame["weighted_points"] / (frame["risk_points"].astype(float) * total_units)

    frame["stage1_sl"] = frame["stage1_exit"].eq("SL hit")
    frame["stage2_sl"] = frame["stage2_exit"].astype(str).str.contains("SL", na=False)
    frame["stage3_sl"] = frame["stage3_exit"].eq("SL hit")
    frame["any_sl"] = frame[["stage1_sl", "stage2_sl", "stage3_sl"]].any(axis=1)
    frame["full_loss_trade"] = frame["weighted_points"] < 0
    frame["return_pct"] = frame["weighted_$"] / ps.START_BALANCE * 100.0

    summary = {
        "label": label,
        "units": frame.loc[0, "units"],
        "lots": frame.loc[0, "lots"],
        "trades": int(len(frame)),
        "final_amount": float(frame["equity_$"].iloc[-1]),
        "total_pnl_$": float(frame["weighted_$"].sum()),
        "return_pct": float(frame["weighted_$"].sum() / ps.START_BALANCE * 100.0),
        "wr": float((frame["weighted_points"] > 0).mean() * 100.0),
        "avg_rr": float(frame["rr_multiple"].mean()),
        "median_rr": float(frame["rr_multiple"].median()),
        "best_rr": float(frame["rr_multiple"].max()),
        "worst_rr": float(frame["rr_multiple"].min()),
        "maxdd_$": float((frame["equity_$"] - frame["equity_$"].cummax()).min()),
        "maxdd_pct": float((((frame["equity_$"] - frame["equity_$"].cummax()) / frame["equity_$"].cummax().replace(0, pd.NA)).fillna(0)).min() * 100.0),
        "any_sl_count": int(frame["any_sl"].sum()),
        "full_loss_count": int(frame["full_loss_trade"].sum()),
        "stage1_sl_count": int(frame["stage1_sl"].sum()),
        "stage2_sl_count": int(frame["stage2_sl"].sum()),
        "stage3_sl_count": int(frame["stage3_sl"].sum()),
        "avg_win_$": float(frame.loc[frame["weighted_$"] > 0, "weighted_$"].mean()),
        "avg_loss_$": float(frame.loc[frame["weighted_$"] < 0, "weighted_$"].mean()),
    }
    return summary, frame


def render_report(summary_rows, detail_df):
    summary_table = []
    for row in summary_rows:
        summary_table.append([
            row["label"],
            row["units"],
            row["lots"],
            row["trades"],
            f"${row['final_amount']:.2f}",
            f"${row['total_pnl_$']:.2f}",
            f"{row['return_pct']:+.2f}%",
            f"{row['wr']:.1f}%",
            f"${row['maxdd_$']:.2f}",
            f"{row['maxdd_pct']:+.2f}%",
            row["any_sl_count"],
            row["full_loss_count"],
            f"{row['avg_rr']:+.2f}R",
            f"{row['median_rr']:+.2f}R",
        ])

    lines = []
    lines.append("# 仓位档位详细分析")
    lines.append("")
    lines.append("> 对比对象：`平衡推荐 0.5/1.0/1.5` 与 `收益峰值 0.5/0.5/2.0`。")
    lines.append("> 起始资金固定为 `$10,000`。")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(md_table(
        ["方案", "Units", "Lots", "Trades", "最终金额", "总盈亏", "总收益率", "胜率", "最大回撤$", "最大回撤%", "有止损交易", "整单亏损", "平均R", "中位R"],
        summary_table,
    ))
    lines.append("")

    for row in summary_rows:
        lines.append(f"## {row['label']}")
        lines.append("")
        lines.append(f"- 仓位分配：`{row['units']}`，即 `{row['lots']} lot`")
        lines.append(f"- 最终金额：`${row['final_amount']:.2f}`")
        lines.append(f"- 总盈亏：`${row['total_pnl_$']:.2f}`")
        lines.append(f"- 总收益率：`{row['return_pct']:+.2f}%`")
        lines.append(f"- 最大回撤：`${row['maxdd_$']:.2f}` / `{row['maxdd_pct']:+.2f}%`")
        lines.append(f"- 有止损交易：`{row['any_sl_count']}` 笔")
        lines.append(f"- 整单亏损：`{row['full_loss_count']}` 笔")
        lines.append(
            f"- 止损分布：Stage1 ` {row['stage1_sl_count']} ` / Stage2 ` {row['stage2_sl_count']} ` / Stage3 ` {row['stage3_sl_count']} `"
        )
        lines.append(
            f"- 逐笔盈亏比：平均 `{row['avg_rr']:+.2f}R`，中位 `{row['median_rr']:+.2f}R`，"
            f"最好 `{row['best_rr']:+.2f}R`，最差 `{row['worst_rr']:+.2f}R`"
        )
        lines.append("")

    sample = detail_df[
        ["variant_label", "date", "mode", "dir", "weighted_$", "equity_$", "rr_multiple", "any_sl", "stage1_exit", "stage2_exit", "stage3_exit"]
    ].copy()
    sample["date"] = pd.to_datetime(sample["date"]).dt.strftime("%Y-%m-%d %H:%M")
    sample_rows = []
    for _, row in sample.head(24).iterrows():
        sample_rows.append([
            row["variant_label"],
            row["date"],
            row["mode"],
            row["dir"],
            f"${row['weighted_$']:.2f}",
            f"${row['equity_$']:.2f}",
            f"{row['rr_multiple']:+.2f}R",
            "Y" if row["any_sl"] else "N",
            row["stage1_exit"],
            row["stage2_exit"],
            row["stage3_exit"],
        ])

    lines.append("## 逐笔样例")
    lines.append("")
    lines.append("完整逐笔明细请看 CSV；这里先展示前 24 行。")
    lines.append("")
    lines.append(md_table(
        ["方案", "时间", "Mode", "方向", "单笔盈亏$", "累计资金", "盈亏比", "有止损", "Stage1", "Stage2", "Stage3"],
        sample_rows,
    ))
    lines.append("")
    lines.append("## 文件")
    lines.append("")
    lines.append(f"- `data\\results\\position_sizing_strict_certify_20260628\\{os.path.basename(SUMMARY_CSV)}`")
    lines.append(f"- `data\\results\\position_sizing_strict_certify_20260628\\{os.path.basename(DETAIL_CSV)}`")
    lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))


def main():
    os.makedirs(RESULT_ROOT, exist_ok=True)
    result = base.summarize_strategy()
    out = result["trades"]

    summary_rows = []
    frames = []
    for units, label in TARGETS:
        item = ps.evaluate_units(out, units)
        summary, frame = analyze_variant(item["frame"], label)
        frame["variant_label"] = label
        summary_rows.append(summary)
        frames.append(frame)

    summary_df = pd.DataFrame(summary_rows)
    detail_df = pd.concat(frames, ignore_index=True)
    summary_df.to_csv(SUMMARY_CSV, index=False, encoding="utf-8-sig")
    detail_df.to_csv(DETAIL_CSV, index=False, encoding="utf-8-sig")
    render_report(summary_rows, detail_df)

    print(summary_df.to_string(index=False))
    print(f"Wrote {SUMMARY_CSV}")
    print(f"Wrote {DETAIL_CSV}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
