# -*- coding: utf-8 -*-
"""Snapshot the current main strategy with fixed entry and exit settings."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import _stage12_combo_test as s12
import _current_baseline as base


RESULT_ROOT = os.path.join(ROOT, "data", "results", "current_strategy_20260627")
SUMMARY_PATH = os.path.join(RESULT_ROOT, "current_strategy_summary.md")
DETAIL_PATH = os.path.join(RESULT_ROOT, "current_strategy_trades.csv")
CURVE_PATH = os.path.join(RESULT_ROOT, "current_strategy_equity_curve.png")

STAGE1_R = 2.0
STAGE2_TRAIL_R = 1.5
STAGE2_FORCE_R = 4.0
TOP_PCT = 34
SPEC_LO = 5
SPEC_HI = 35


def main():
    result = base.summarize_strategy(
        spec_lo=SPEC_LO,
        spec_hi=SPEC_HI,
        top_pct=TOP_PCT,
        stage1_r=STAGE1_R,
        stage2_trail_r=STAGE2_TRAIL_R,
        stage2_force_r=STAGE2_FORCE_R,
    )
    out = result["trades"]
    total_m = result["total"]
    test_m = result["test"]

    os.makedirs(RESULT_ROOT, exist_ok=True)
    out.to_csv(DETAIL_PATH, index=False, encoding="utf-8-sig")
    s12.render_curve([("Current main strategy", out)], CURVE_PATH)

    lines = []
    lines.append("# 当前主线策略快照")
    lines.append("")
    lines.append("## 固定参数")
    lines.append("")
    lines.append("- Layer 1: `|H2 Bias_55| > 3.0%`")
    lines.append("- Layer 2: `pre_cross + cross + post_n(2-6)`")
    lines.append(f"- Layer 3: `Bias_5 top {TOP_PCT}%`")
    lines.append("- M15: `replace_any + rescue`")
    lines.append("- H2: `Layer1 q2 early-gate`")
    lines.append("- Stage 1: `2.0R`")
    lines.append("- Stage 2: `1.5R trail / 4.0R force`")
    lines.append("- Stage 3: `m30_merged_cross`")
    lines.append(f"- stop spec: `[{SPEC_LO}, {SPEC_HI}] pt`")
    lines.append(f"- Layer 3 threshold: `{result['threshold']:.6f}`")
    lines.append("")
    lines.append("## 当前结果")
    lines.append("")
    lines.append(f"- 交易数: `{total_m['n']}`")
    lines.append(f"- 胜率: `{total_m['wr']:.1f}%`")
    lines.append(f"- PF: `{total_m['pf']:.2f}`")
    lines.append(f"- EV: `{total_m['ev']:+.2f}pt`")
    lines.append(f"- PnL: `${out['total_$'].sum():.0f}`")
    lines.append(f"- MaxCL: `{total_m['ml']}`")
    lines.append(f"- 验证集 PF: `{test_m['pf']:.2f}`")
    lines.append(f"- 验证集 EV: `{test_m['ev']:+.2f}pt`")
    lines.append("")
    lines.append("## 文件")
    lines.append("")
    lines.append(f"- `data\\results\\current_strategy_20260627\\{os.path.basename(DETAIL_PATH)}`")
    lines.append(f"- `data\\results\\current_strategy_20260627\\{os.path.basename(CURVE_PATH)}`")
    lines.append("")

    with open(SUMMARY_PATH, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))

    print("\n".join(lines))
    print(f"Wrote {DETAIL_PATH}")
    print(f"Wrote {CURVE_PATH}")


if __name__ == "__main__":
    main()
