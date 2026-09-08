# -*- coding: utf-8 -*-
"""Export local and reference validation outputs for 1H_M30_4H."""
from __future__ import annotations


from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_workspace_common import (  # noqa: E402
    COMBO,
    FRAMES,
    PERIOD_LABEL,
    SIGNALS_DIR,
    VALIDATION_DIR,
    build_gate_scan,
    build_yearly_performance,
    ensure_dirs,
    export_csv,
    export_reference_validation,
    pick_primary_variant,
)


REFERENCE_FILES = [
    ("combo_best_stage12_trades.csv", "combo_best_stage12_trades.csv"),
    ("combo_candidate_pick.csv", "combo_candidate_pick.csv"),
    ("combo_final_best_summary.csv", "combo_final_best_summary.csv"),
    ("combo_final_capital_metrics.csv", "combo_final_capital_metrics_raw.csv"),
    ("combo_gate_strength_top3.csv", "combo_gate_strength_top3.csv"),
    ("combo_position_sizing.csv", "combo_position_sizing.csv"),
    ("combo_stage12_sweep.csv", "combo_stage12_sweep.csv"),
    ("combo_top3_position.csv", "combo_top3_position.csv"),
    ("combo_top3_stage12.csv", "combo_top3_stage12.csv"),
    ("组合门范围细扫_中文.csv", "combo_gate_range_scan_reference.csv"),
    ("组合止损范围测试_中文.csv", "combo_stop_range_scan_reference.csv"),
    ("组合止损范围推荐_中文.csv", "combo_stop_range_pick_reference.csv"),
    ("组合参数总表_门区间_止损区间_中文.csv", "combo_combined_summary_reference.csv"),
    ("组合最终资金指标_中文_utf8.csv", "combo_final_capital_metrics_reference.csv"),
]


def main() -> None:
    ensure_dirs()
    summary = pd.read_csv(SIGNALS_DIR / "strategy_variant_summary.csv", encoding="utf-8-sig")
    candidates = pd.read_csv(SIGNALS_DIR / "strategy_candidate_trades.csv", encoding="utf-8-sig")
    primary = pick_primary_variant(summary)
    primary_variant = str(primary["variant"])
    primary_trades = candidates.loc[candidates["variant"].astype(str) == primary_variant].copy()

    strategy_summary = pd.DataFrame(
        [
            {
                "combo": COMBO,
                "frames": PERIOD_LABEL,
                "primary_variant": primary_variant,
                "primary_desc": primary["desc"],
                "trades": int(primary["n"]),
                "wr": float(primary["wr"]),
                "pf": float(primary["pf"]),
                "ev": float(primary["ev"]),
                "pnl": float(primary["pnl"]),
                "test_n": int(primary["test_n"]),
                "test_pf": float(primary["test_pf"]),
                "test_ev": float(primary["test_ev"]),
            }
        ]
    )
    export_csv(strategy_summary, VALIDATION_DIR / "strategy_summary.csv")
    export_csv(build_gate_scan(summary, primary_variant), VALIDATION_DIR / "combo_gate_range_scan.csv")
    export_csv(build_yearly_performance(primary_trades), VALIDATION_DIR / "yearly_performance.csv")

    exported_reference = []
    for src_name, dst_name in REFERENCE_FILES:
        if export_reference_validation(src_name, dst_name):
            exported_reference.append(dst_name)

    readme = [
        "# 1H_M30_4H 验证数据",
        "",
        "## 本地验证输出",
        "",
        "- `strategy_summary.csv`",
        "- `combo_gate_range_scan.csv`",
        "- `yearly_performance.csv`",
        "",
        "## 参考验证输出",
        "",
    ]
    if exported_reference:
        readme.extend(f"- `{name}`" for name in exported_reference)
    else:
        readme.append("- 暂无可用参考验证输出。")
    readme.extend(
        [
            "",
            "## 说明",
            "",
            "- 本地验证按 30M / 1H / 4H 上下文门重新计算候选表现。",
            "- 参考验证来自 `黄金/30m2H策略/参考实现工程/shadow_tests/multi_tf_matrix` 的 `H1_M30_H4` 结果，并在本目录中统一改名为 `1H_M30_4H`。",
        ]
    )
    (VALIDATION_DIR / "README.md").write_bytes(("\n".join(readme) + "\n").encode("utf-8-sig"))
    print(f"Exported validation bundle for {COMBO}.")


if __name__ == "__main__":
    main()
