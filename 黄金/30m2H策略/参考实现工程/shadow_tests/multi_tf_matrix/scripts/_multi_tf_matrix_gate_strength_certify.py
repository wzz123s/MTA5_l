# -*- coding: utf-8 -*-
"""组合门强度严格认证，并输出中文终版指标。"""
import os
import sys
from datetime import datetime

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from shadow_tests.multi_tf_matrix.scripts import _multi_tf_matrix_common as common


SHADOW_ROOT = os.path.join(ROOT, "shadow_tests", "multi_tf_matrix")
VALIDATION_ROOT = os.path.join(SHADOW_ROOT, "data", "validation_20260701")
SUMMARY_CSV = os.path.join(SHADOW_ROOT, "data", "multi_tf_matrix_summary.csv")
FINAL_SUMMARY_CSV = os.path.join(VALIDATION_ROOT, "combo_final_best_summary.csv")
TRADES_CSV = os.path.join(VALIDATION_ROOT, "combo_best_stage12_trades.csv")

GATE_TOP3_CSV = os.path.join(VALIDATION_ROOT, "组合门强度前3名_中文.csv")
FINAL_METRICS_CSV = os.path.join(VALIDATION_ROOT, "组合最终资金指标_中文.csv")
GATE_TOP3_XLSX = os.path.join(VALIDATION_ROOT, "组合门强度前3名_中文.xlsx")
FINAL_METRICS_XLSX = os.path.join(VALIDATION_ROOT, "组合最终资金指标_中文.xlsx")
REPORT_PATH = os.path.join(SHADOW_ROOT, "results", "多周期组合门强度严格认证报告.md")

START_BALANCE = 500.0
UNIT_LOT = 0.02
PT_VALUE_PER_LOT = 10.0


def units_to_tuple(label):
    return tuple(float(x) for x in label.split("/"))


def pick_gate_top3(summary_df):
    picked = []
    for combo, frame in summary_df.groupby("combo"):
        scoped = frame.copy()
        scoped["是否强约束方案"] = scoped["variant"].str.endswith("__stack_core")
        scoped["样本是否达标"] = scoped["n"] >= 50
        if scoped["样本是否达标"].any():
            scoped = scoped[scoped["样本是否达标"]].copy()
        scoped["评分"] = (
            scoped["pf"] * 10
            + scoped["test_pf"].clip(upper=50) * 2
            + scoped["ev"] * 0.02
            - scoped["是否强约束方案"].astype(int) * 100
        )
        picked.append(
            scoped.sort_values(["评分", "test_ev", "n"], ascending=[False, False, False]).head(3)
        )
    return pd.concat(picked, ignore_index=True).reset_index(drop=True)


def compute_weighted_metrics(frame, units_label, years):
    units = units_to_tuple(units_label)
    out = frame.copy().sort_values("date").reset_index(drop=True)
    weighted_points = (
        units[0] * out["stage1_pnl"].astype(float)
        + units[1] * out["stage2_pnl"].astype(float)
        + units[2] * out["stage3_pnl"].astype(float)
    )
    weighted_dollars = weighted_points * UNIT_LOT * PT_VALUE_PER_LOT
    equity = START_BALANCE + weighted_dollars.cumsum()

    r_multiple = weighted_points / out["sd"].astype(float)
    stop_mask = (
        out["stage1_exit"].astype(str).str.contains("SL", regex=False)
        | out["stage2_exit"].astype(str).str.contains("SL", regex=False)
        | out["stage3_exit"].astype(str).str.contains("SL", regex=False)
    )
    out["加权点数"] = weighted_points
    out["加权盈亏美元"] = weighted_dollars
    out["是否止损交易"] = stop_mask
    out["盈亏比R"] = r_multiple
    out["年份"] = pd.to_datetime(out["date"]).dt.year

    result = {
        "总交易次数": int(len(out)),
        "最终资金额": float(equity.iloc[-1]) if len(equity) else START_BALANCE,
        "总盈利": float(weighted_dollars.sum()),
        "止损幅度均值pt": float(out["sd"].mean()) if len(out) else 0.0,
        "止损幅度中位数pt": float(out["sd"].median()) if len(out) else 0.0,
        "最大盈亏比R": float(r_multiple.max()) if len(r_multiple) else 0.0,
        "最小盈亏比R": float(r_multiple.min()) if len(r_multiple) else 0.0,
        "平均盈亏比R": float(r_multiple.mean()) if len(r_multiple) else 0.0,
        "中位数盈亏比R": float(r_multiple.median()) if len(r_multiple) else 0.0,
        "止损次数": int(stop_mask.sum()),
        "止损次数占比": float(stop_mask.mean()) if len(stop_mask) else 0.0,
    }
    for year in years:
        year_frame = out[out["年份"] == year]
        result[f"{year}年交易次数"] = int(len(year_frame))
        result[f"{year}年盈利"] = float(year_frame["加权盈亏美元"].sum()) if len(year_frame) else 0.0
        result[f"{year}年止损次数"] = int(year_frame["是否止损交易"].sum()) if len(year_frame) else 0
    return result


def main():
    summary = pd.read_csv(SUMMARY_CSV, encoding="utf-8-sig")
    final_summary = pd.read_csv(FINAL_SUMMARY_CSV, encoding="utf-8-sig")
    trades = pd.read_csv(TRADES_CSV, encoding="utf-8-sig")
    trades["date"] = pd.to_datetime(trades["date"])

    years = sorted(pd.to_datetime(trades["date"]).dt.year.unique().tolist())

    bundle = common.load_mainline_bundle()
    signals = bundle["signals"][["date", "mode", "dir", "sd", "entry", "stop"]].copy()
    signals["date"] = pd.to_datetime(signals["date"])

    gate_top3 = pick_gate_top3(summary)
    gate_top3_cn_rows = []
    for _, row in gate_top3.iterrows():
        gate_top3_cn_rows.append({
            "策略组合": row["combo"],
            "组合门": row["variant"],
            "组合门说明": row["desc"],
            "交易次数": int(row["n"]),
            "胜率": float(row["wr"]),
            "盈亏比PF": float(row["pf"]),
            "期望EV_pt": float(row["ev"]),
            "验证段盈亏比PF": float(row["test_pf"]),
            "验证段期望EV_pt": float(row["test_ev"]),
            "样本是否达标": bool(row["样本是否达标"]),
            "是否强约束方案": bool(row["是否强约束方案"]),
            "评分": float(row["评分"]),
        })
    gate_top3_cn = pd.DataFrame(gate_top3_cn_rows)
    gate_top3_cn.to_csv(GATE_TOP3_CSV, index=False, encoding="gbk")
    gate_top3_cn.to_excel(GATE_TOP3_XLSX, index=False)

    metric_rows = []
    for _, row in final_summary.iterrows():
        combo = row["combo"]
        trade_frame = trades[
            (trades["combo"] == combo)
            & (trades["picked_stage1_r"] == row["stage1_r"])
            & (trades["picked_stage2_trail_r"] == row["stage2_trail_r"])
            & (trades["picked_stage2_force_r"] == row["stage2_force_r"])
        ].copy()
        trade_frame = trade_frame.merge(signals, on=["date", "mode", "dir"], how="left")
        metrics = compute_weighted_metrics(trade_frame, row["units"], years)
        metric_rows.append({
            "策略组合": combo,
            "最终组合门": row["picked_variant"],
            "组合门说明": row["picked_desc"],
            "阶段参数": f"{row['stage1_r']:.1f}/{row['stage2_trail_r']:.1f}/{row['stage2_force_r']:.1f}",
            "仓位单位": row["units"],
            "仓位手数": row["lots"],
            "起始资金": START_BALANCE,
            **metrics,
        })
    metrics_df = pd.DataFrame(metric_rows).sort_values("策略组合").reset_index(drop=True)
    metrics_df.to_csv(FINAL_METRICS_CSV, index=False, encoding="gbk")
    metrics_df.to_excel(FINAL_METRICS_XLSX, index=False)

    lines = []
    lines.append("# 多周期组合门强度严格认证报告")
    lines.append("")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> 起始资金统一按：`${START_BALANCE:.0f}`")
    lines.append("")
    lines.append("这轮结果已经与之前 `30_2H` 口径对齐：")
    lines.append("- 起始资金统一按 500 美元计算。")
    lines.append("- 输出列名统一为中文。")
    lines.append("- 增加最终资金额、总盈利、每年交易次数、每年盈利、每年止损次数。")
    lines.append("")

    lines.append("## 1. 每组组合门强度前 3 名")
    lines.append("")
    gate_rows = []
    for _, row in gate_top3_cn.iterrows():
        gate_rows.append([
            row["策略组合"],
            row["组合门"],
            row["组合门说明"],
            int(row["交易次数"]),
            f"{row['胜率']:.1f}%",
            f"{row['盈亏比PF']:.2f}",
            f"{row['期望EV_pt']:+.2f}pt",
            f"{row['验证段盈亏比PF']:.2f}",
            f"{row['验证段期望EV_pt']:+.2f}pt",
        ])
    lines.append(common.md_table(
        ["策略组合", "组合门", "说明", "交易次数", "胜率", "PF", "EV", "验证PF", "验证EV"],
        gate_rows,
    ))
    lines.append("")

    lines.append("## 2. 最终资金与盈亏比指标")
    lines.append("")
    metric_rows_md = []
    for _, row in metrics_df.iterrows():
        metric_rows_md.append([
            row["策略组合"],
            row["最终组合门"],
            row["阶段参数"],
            row["仓位单位"],
            row["仓位手数"],
            f"${row['起始资金']:.0f}",
            f"${row['最终资金额']:.2f}",
            f"${row['总盈利']:.2f}",
            f"{row['止损幅度均值pt']:.2f} / {row['止损幅度中位数pt']:.2f}",
            f"{row['最大盈亏比R']:+.2f}",
            f"{row['最小盈亏比R']:+.2f}",
            f"{row['平均盈亏比R']:+.2f}",
            f"{row['中位数盈亏比R']:+.2f}",
            int(row["止损次数"]),
            f"{row['止损次数占比']:.2%}",
        ])
    lines.append(common.md_table(
        ["策略组合", "最终组合门", "阶段参数", "仓位单位", "仓位手数", "起始资金", "最终资金额", "总盈利", "止损幅度(均值/中位)", "最大盈亏比", "最小盈亏比", "平均盈亏比", "中位数盈亏比", "止损次数", "止损占比"],
        metric_rows_md,
    ))
    lines.append("")

    for _, row in metrics_df.iterrows():
        lines.append(f"## {row['策略组合']}")
        lines.append("")
        lines.append("### 最终结果")
        lines.append("")
        lines.append(common.md_table(
            ["项目", "值"],
            [
                ["最终组合门", row["最终组合门"]],
                ["组合门说明", row["组合门说明"]],
                ["阶段参数", row["阶段参数"]],
                ["仓位单位", row["仓位单位"]],
                ["仓位手数", row["仓位手数"]],
                ["起始资金", f"${row['起始资金']:.2f}"],
                ["最终资金额", f"${row['最终资金额']:.2f}"],
                ["总盈利", f"${row['总盈利']:.2f}"],
                ["止损幅度", f"均值 {row['止损幅度均值pt']:.2f}pt / 中位 {row['止损幅度中位数pt']:.2f}pt"],
                ["最大盈亏比", f"{row['最大盈亏比R']:+.4f}R"],
                ["最小盈亏比", f"{row['最小盈亏比R']:+.4f}R"],
                ["平均盈亏比", f"{row['平均盈亏比R']:+.4f}R"],
                ["中位数盈亏比", f"{row['中位数盈亏比R']:+.4f}R"],
                ["止损次数", int(row["止损次数"])],
                ["止损次数与总交易次数比", f"{int(row['止损次数'])} / {int(row['总交易次数'])} = {row['止损次数占比']:.2%}"],
            ],
        ))
        lines.append("")
        lines.append("### 分年结果")
        lines.append("")
        year_rows = []
        for year in years:
            year_rows.append([
                year,
                int(row[f"{year}年交易次数"]),
                f"${row[f'{year}年盈利']:.2f}",
                int(row[f"{year}年止损次数"]),
            ])
        lines.append(common.md_table(
            ["年份", "交易次数", "当年盈利", "当年止损次数"],
            year_rows,
        ))
        lines.append("")

    lines.append("## 文件")
    lines.append("")
    lines.append(f"- `shadow_tests\\multi_tf_matrix\\data\\validation_20260701\\{os.path.basename(GATE_TOP3_CSV)}`")
    lines.append(f"- `shadow_tests\\multi_tf_matrix\\data\\validation_20260701\\{os.path.basename(FINAL_METRICS_CSV)}`")
    lines.append(f"- `shadow_tests\\multi_tf_matrix\\results\\{os.path.basename(REPORT_PATH)}`")
    lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote {GATE_TOP3_CSV}")
    print(f"Wrote {FINAL_METRICS_CSV}")
    print(f"Wrote {GATE_TOP3_XLSX}")
    print(f"Wrote {FINAL_METRICS_XLSX}")
    print(f"Wrote {REPORT_PATH}")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    main()
