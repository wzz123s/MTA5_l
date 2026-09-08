# -*- coding: utf-8 -*-
"""Combine gate-range recommendations and stop-range recommendations."""
import os
from datetime import datetime

import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SHADOW_ROOT = os.path.join(ROOT, "shadow_tests", "multi_tf_matrix")
VALIDATION_ROOT = os.path.join(SHADOW_ROOT, "data", "validation_20260701")

FINAL_SUMMARY_CSV = os.path.join(VALIDATION_ROOT, "combo_final_best_summary.csv")
GATE_SCAN_CSV = os.path.join(VALIDATION_ROOT, "组合门范围细扫_中文.csv")
STOP_SUMMARY_CSV = os.path.join(VALIDATION_ROOT, "组合止损范围推荐_中文.csv")

COMBINED_CSV = os.path.join(VALIDATION_ROOT, "组合参数总表_门区间_止损区间_中文.csv")
REPORT_PATH = os.path.join(SHADOW_ROOT, "results", "多周期组合参数总表_门区间_止损区间.md")


def normalize_gate_scan_columns(frame):
    expected = [
        "策略组合",
        "当前组合门",
        "聚焦周期",
        "门族",
        "门参数",
        "说明",
        "交易数",
        "胜率",
        "盈亏比PF",
        "期望EV_pt",
        "验证PF",
        "验证EV_pt",
    ]
    if list(frame.columns[: len(expected)]) == expected:
        return frame
    renamed = frame.copy()
    renamed.columns = expected + list(renamed.columns[len(expected):])
    return renamed


def build_gate_range(frame):
    by_family = {}
    for family, fam in frame.groupby("门族"):
        ranked = fam.sort_values(
            ["盈亏比PF", "验证PF", "期望EV_pt", "交易数"],
            ascending=[False, False, False, False],
        ).reset_index(drop=True)
        by_family[family] = ranked

    focus = frame["聚焦周期"].iloc[0]
    notes = []
    if "方向族" in by_family:
        notes.append("方向族：" + " / ".join(by_family["方向族"].head(2)["门参数"].tolist()))
    if "位置族" in by_family:
        notes.append("位置族：" + " / ".join(by_family["位置族"].head(2)["门参数"].tolist()))
    if "强度族" in by_family:
        viable = by_family["强度族"]
        if (viable["交易数"] >= 50).any():
            viable = viable[viable["交易数"] >= 50].copy()
        notes.append("强度族：" + " / ".join(viable.head(2)["门参数"].tolist()))
    return f"聚焦 {focus}；" + "；".join(notes)


def main():
    final_summary = pd.read_csv(FINAL_SUMMARY_CSV, encoding="utf-8-sig")
    gate_scan = normalize_gate_scan_columns(pd.read_csv(GATE_SCAN_CSV, encoding="gbk"))
    stop_summary = pd.read_csv(STOP_SUMMARY_CSV, encoding="utf-8-sig")

    rows = []
    for _, base in final_summary.sort_values("combo").iterrows():
        combo = base["combo"]
        gate_frame = gate_scan[gate_scan["策略组合"] == combo].copy()
        stop_row = stop_summary[stop_summary["策略组合"] == combo].iloc[0]

        rows.append({
            "策略组合": combo,
            "当前组合门": base["picked_variant"],
            "组合门说明": base["picked_desc"],
            "推荐门参数区间": build_gate_range(gate_frame),
            "Stage参数": f"{base['stage1_r']:.1f}/{base['stage2_trail_r']:.1f}/{base['stage2_force_r']:.1f}",
            "仓位单位": base["units"],
            "手数": base["lots"],
            "聚焦周期": stop_row["聚焦周期"],
            "主推荐止损范围": stop_row["主推荐止损范围"],
            "次优止损范围": stop_row["次优止损范围"],
            "可接受止损区间": stop_row["可接受止损区间"],
            "止损扫描下限集": stop_row["止损扫描下限集"],
            "止损扫描上限集": stop_row["止损扫描上限集"],
            "止损范围说明": stop_row["止损范围说明"],
            "止损范围测试PF": float(stop_row["主推荐PF"]),
            "止损范围测试验证PF": float(stop_row["主推荐验证PF"]),
            "止损范围测试EV_pt": float(stop_row["主推荐EV_pt"]),
            "止损范围测试总盈利$": float(stop_row["主推荐总盈利$"]),
        })

    out = pd.DataFrame(rows)
    out.to_csv(COMBINED_CSV, index=False, encoding="utf-8-sig")

    lines = []
    lines.append("# 多周期组合参数总表")
    lines.append("")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 总表")
    lines.append("")
    lines.append(out.to_markdown(index=False))
    lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote {COMBINED_CSV}")
    print(f"Wrote {REPORT_PATH}")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
