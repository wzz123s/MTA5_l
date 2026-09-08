# -*- coding: utf-8 -*-
"""Run configurable multi-timeframe shadow tests on the current mainline trades."""
import os
import sys
from datetime import datetime

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from shadow_tests.multi_tf_matrix.scripts import _multi_tf_matrix_common as common


SHADOW_ROOT = os.path.join(ROOT, "shadow_tests", "multi_tf_matrix")
REPORT_PATH = os.path.join(SHADOW_ROOT, "results", "multi_tf_matrix_test_results.md")
DETAIL_PATH = os.path.join(SHADOW_ROOT, "data", "multi_tf_matrix_trade_context.csv")
SUMMARY_CSV_PATH = os.path.join(SHADOW_ROOT, "data", "multi_tf_matrix_summary.csv")
TIMEFRAME_MATRIX = common.TIMEFRAME_MATRIX


def main():
    baseline = common.load_mainline_trades()
    all_frames = sorted({frame for combo in TIMEFRAME_MATRIX for frame in combo["frames"]}, key=common.tf_label_to_hours)
    ctx = common.attach_all_context(baseline, all_frames)

    all_rows = []
    summary_frames = []
    for combo in TIMEFRAME_MATRIX:
        variants = common.build_combo_variant_frames(combo, ctx)
        combo_rows = []
        combo_summaries = []
        for item in variants:
            s = common.summarize_variant_item(item)
            combo_rows.append([
                s["variant"], s["desc"], s["n"], f"{s['wr']:.1f}%", f"{s['pf']:.2f}",
                f"{s['ev']:+.2f}pt", f"${s['pnl']:.0f}", s["max_loss_streak"],
                s["train_n"], s["test_n"], f"{s['test_pf']:.2f}", f"{s['test_ev']:+.2f}pt",
            ])
            combo_summaries.append(s)
        all_rows.extend((combo["name"], row) for row in combo_rows)
        summary_df = pd.DataFrame(combo_summaries)
        summary_frames.append(summary_df)

    summary = pd.concat(summary_frames, ignore_index=True)
    focus = common.choose_primary_candidates(summary)

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(DETAIL_PATH), exist_ok=True)
    ctx.to_csv(DETAIL_PATH, index=False, encoding="utf-8-sig")
    summary.to_csv(SUMMARY_CSV_PATH, index=False, encoding="utf-8-sig")

    lines = []
    lines.append("# 多周期影子测试结果")
    lines.append("")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("本测试固定当前 30m x 2H 主线执行结果，不改 EA、不改主策略，只给最终 102 笔交易挂上额外周期上下文，验证附加过滤是否值得继续研究。")
    lines.append("")
    lines.append("## 固定基线")
    lines.append("")
    lines.append(common.md_table(
        ["项目", "值"],
        [
            ["主线", "当前 30m x 2H + M15/H2 提前触发增强"],
            ["执行层样本", "102 笔"],
            ["基线结果", "WR 80.4%，PF 10.37，EV +93.75pt，PnL $9562，MaxCL 4"],
            ["测试矩阵", "1H/30M-4H，2H-6H/8H，3H-10H/12H，4H-16H，5H-20H，6H-24H"],
        ],
    ))
    lines.append("")
    lines.append("## 聚焦组合")
    lines.append("")
    if len(focus):
        focus_rows = []
        for _, row in focus.iterrows():
            focus_rows.append([
                row["combo"], row["variant"], row["desc"], int(row["n"]),
                f"{row['wr']:.1f}%", f"{row['pf']:.2f}", f"{row['ev']:+.2f}pt",
                f"${row['pnl']:.0f}", int(row["max_loss_streak"]),
                f"{row['test_pf']:.2f}", f"{row['test_ev']:+.2f}pt",
            ])
        lines.append(common.md_table(
            ["组合", "方案", "说明", "笔数", "WR", "PF", "EV", "PnL", "MaxCL", "验证PF", "验证EV"],
            focus_rows,
        ))
    else:
        lines.append("暂无聚焦组合。")
    lines.append("")

    current_combo = None
    for combo_name, row in all_rows:
        if current_combo != combo_name:
            current_combo = combo_name
            lines.append(f"## {combo_name}")
            lines.append("")
            lines.append(common.md_table(
                ["方案", "说明", "笔数", "WR", "PF", "EV", "PnL", "MaxCL", "训练笔数(<2023)", "验证笔数(>=2023)", "验证PF", "验证EV"],
                [r for c, r in all_rows if c == combo_name],
            ))
            lines.append("")

    lines.append("## 明细文件")
    lines.append("")
    lines.append(f"- `{os.path.relpath(DETAIL_PATH, ROOT)}`")
    lines.append(f"- `{os.path.relpath(SUMMARY_CSV_PATH, ROOT)}`")
    lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"report={os.path.relpath(REPORT_PATH, ROOT)}")
    print(f"detail={os.path.relpath(DETAIL_PATH, ROOT)}")
    print(f"summary={os.path.relpath(SUMMARY_CSV_PATH, ROOT)}")
    print(focus.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
