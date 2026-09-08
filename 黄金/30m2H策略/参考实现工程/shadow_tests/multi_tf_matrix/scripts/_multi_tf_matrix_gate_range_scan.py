# -*- coding: utf-8 -*-
"""Scan gate-factor families around each combo's current best gate."""
import os
import re
import sys
from datetime import datetime

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from shadow_tests.multi_tf_matrix.scripts import _multi_tf_matrix_common as common


SHADOW_ROOT = os.path.join(ROOT, "shadow_tests", "multi_tf_matrix")
VALIDATION_ROOT = os.path.join(SHADOW_ROOT, "data", "validation_20260701")
SUMMARY_XLSX = os.path.join(VALIDATION_ROOT, "组合门范围细扫_中文.xlsx")
SUMMARY_CSV = os.path.join(VALIDATION_ROOT, "组合门范围细扫_中文.csv")
REPORT_PATH = os.path.join(SHADOW_ROOT, "results", "多周期组合门范围细扫报告.md")
BEST_SUMMARY_CSV = os.path.join(VALIDATION_ROOT, "combo_final_best_summary.csv")

BIAS_TOP_PCTS = [20, 25, 30, 35, 40]


def extract_focus_label(variant_name, combo):
    prefix = f"{combo}__"
    key = variant_name[len(prefix):] if variant_name.startswith(prefix) else variant_name
    if key == "baseline":
        parts = combo.split("_")
        if len(parts) >= 2 and parts[1].upper() == "M30":
            return "30m"
        return parts[0].lower()
    match = re.match(r"([a-z0-9]+)_(.+)", key)
    if match:
        return match.group(1)
    parts = combo.split("_")
    if len(parts) >= 2 and parts[1].upper() == "M30":
        return "30m"
    return parts[0].lower()


def stat_from_frame(combo_name, variant, desc, family, frame):
    item = {"combo": combo_name, "variant": variant, "desc": desc, "frame": frame}
    row = common.summarize_variant_item(item)
    row["family"] = family
    return row


def build_focus_variants(combo, ctx, focus_label):
    sign = common.trade_sign(ctx)
    label = focus_label.lower()
    available = ctx[f"{label}_idx"] >= 0
    variants = []

    dir_align = available & (ctx[f"{label}_dir"].values == sign)
    recent2_any = available & (
        (ctx[f"{label}_dir"].values == sign)
        | (ctx[f"{label}_dir_prev1"].values == sign)
    )
    recent2_all = available & (ctx[f"{label}_dir"].values == sign) & (ctx[f"{label}_dir_prev1"].values == sign)
    close_side = available & (ctx[f"{label}_close_side"].values == sign)
    close_and_dir = close_side & dir_align

    variants.append(stat_from_frame(combo["name"], f"{combo['name']}__baseline_scan", "基线", "基线", ctx.copy()))
    variants.append(stat_from_frame(combo["name"], f"{combo['name']}__{label}_dir_align", f"{focus_label} 当前方向同向", "方向族", ctx[dir_align].copy()))
    variants.append(stat_from_frame(combo["name"], f"{combo['name']}__{label}_recent2_any", f"{focus_label} 最近2根至少1根同向", "方向族", ctx[recent2_any].copy()))
    variants.append(stat_from_frame(combo["name"], f"{combo['name']}__{label}_recent2_all", f"{focus_label} 最近2根都同向", "方向族", ctx[recent2_all].copy()))
    variants.append(stat_from_frame(combo["name"], f"{combo['name']}__{label}_close_side", f"{focus_label} close 位于 SMA13 交易方向一侧", "位置族", ctx[close_side].copy()))
    variants.append(stat_from_frame(combo["name"], f"{combo['name']}__{label}_close_and_dir", f"{focus_label} close 同侧且方向同向", "位置族", ctx[close_and_dir].copy()))

    bias_col = f"{label}_bias5"
    for pct in BIAS_TOP_PCTS:
        if available.any():
            threshold = ctx.loc[available, bias_col].quantile(1 - pct / 100.0)
            mask = available & (ctx[bias_col] >= threshold)
        else:
            mask = available
        variants.append(
            stat_from_frame(
                combo["name"],
                f"{combo['name']}__{label}_bias5_top{pct}",
                f"{focus_label} Bias_5 top{pct}%",
                "强度族",
                ctx[mask].copy(),
            )
        )
    return variants


def choose_range_notes(frame):
    if frame.empty:
        return "无结果"
    ranked = frame.sort_values(["pf", "test_pf", "ev"], ascending=[False, False, False])
    fam_best = ranked.groupby("family").head(1)
    notes = []
    for _, row in fam_best.iterrows():
        notes.append(
            f"{row['family']}优先看 {row['desc']}（{int(row['n'])}笔, PF {row['pf']:.2f}, 验证PF {row['test_pf']:.2f}）"
        )
    return "；".join(notes)


def main():
    best_df = pd.read_csv(BEST_SUMMARY_CSV, encoding="utf-8-sig")
    bundle = common.load_mainline_bundle()
    baseline = bundle["signals"]
    all_frames = sorted(
        {frame for combo in common.TIMEFRAME_MATRIX for frame in combo["frames"]},
        key=common.tf_label_to_hours,
    )
    ctx = common.attach_all_context(baseline, all_frames)

    all_rows = []
    summary_rows = []
    for combo in common.TIMEFRAME_MATRIX:
        picked = best_df[best_df["combo"] == combo["name"]].iloc[0]
        focus_label = extract_focus_label(picked["picked_variant"], combo["name"])
        scoped = build_focus_variants(combo, ctx, focus_label)
        frame = pd.DataFrame(scoped).sort_values(
            ["pf", "test_pf", "ev", "n"], ascending=[False, False, False, False]
        ).reset_index(drop=True)
        frame["聚焦周期"] = focus_label
        frame["当前采用门"] = picked["picked_variant"]
        all_rows.append(frame)
        summary_rows.append(
            {
                "策略组合": combo["name"],
                "当前采用门": picked["picked_variant"],
                "聚焦周期": focus_label,
                "建议范围说明": choose_range_notes(frame),
            }
        )

    result = pd.concat(all_rows, ignore_index=True)
    out = result[
        ["combo", "当前采用门", "聚焦周期", "family", "variant", "desc", "n", "wr", "pf", "ev", "test_pf", "test_ev"]
    ].copy()
    out.columns = [
        "策略组合",
        "当前采用门",
        "聚焦周期",
        "门族",
        "门参数",
        "说明",
        "交易次数",
        "胜率",
        "盈亏比PF",
        "期望EV_pt",
        "验证段盈亏比PF",
        "验证段期望EV_pt",
    ]

    out.to_csv(SUMMARY_CSV, index=False, encoding="utf-8-sig")
    out.to_excel(SUMMARY_XLSX, index=False)

    summary_df = pd.DataFrame(summary_rows)

    lines = []
    lines.append("# 多周期组合门范围细扫报告")
    lines.append("")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("这一轮不是重新盲比离散门名字，而是围绕每个组合当前最优门，按主线做门测试的思路，把可比较的门族范围再扫一轮。")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(common.md_table(["策略组合", "当前采用门", "聚焦周期", "建议范围说明"], summary_df.values.tolist()))
    lines.append("")

    for combo_name in summary_df["策略组合"]:
        frame = out[out["策略组合"] == combo_name].copy()
        lines.append(f"## {combo_name}")
        lines.append("")
        top_rows = []
        for _, row in frame.head(8).iterrows():
            top_rows.append(
                [
                    row["门族"],
                    row["门参数"],
                    row["说明"],
                    int(row["交易次数"]),
                    f"{row['胜率']:.1f}%",
                    f"{row['盈亏比PF']:.2f}",
                    f"{row['期望EV_pt']:+.2f}pt",
                    f"{row['验证段盈亏比PF']:.2f}",
                    f"{row['验证段期望EV_pt']:+.2f}pt",
                ]
            )
        lines.append(
            common.md_table(
                ["门族", "门参数", "说明", "交易次数", "胜率", "PF", "EV", "验证PF", "验证EV"],
                top_rows,
            )
        )
        lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote {SUMMARY_CSV}")
    print(f"Wrote {SUMMARY_XLSX}")
    print(f"Wrote {REPORT_PATH}")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
