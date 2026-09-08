# -*- coding: utf-8 -*-
"""Evaluate a diagnostic branch that uses slot1_low as the M15 SLOT1 entry-price proxy."""
from __future__ import annotations


import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
ROOT_SCRIPTS_DIR = ROOT / "scripts"

sys.path.insert(0, str(STRATEGY_SCRIPTS_DIR))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT_SCRIPTS_DIR))

from strategy_30m2h_common import export_csv, read_csv_with_fallback, write_text  # noqa: E402
import _current_baseline as cb  # type: ignore  # noqa: E402
import _m15_early_entry_test as m15t  # type: ignore  # noqa: E402
import _pre_cross_range_test as pct  # type: ignore  # noqa: E402
from compare_mt5_log_sessions import build_python_executed_signals  # noqa: E402
from recompare_cached_session_trades import build_diff  # noqa: E402


def choose_slot1_low_by_distance(seg, is_long, stop):
    if len(seg) == 0:
        return None
    row = seg.iloc[0].copy()
    entry = float(row["low"])
    sd = abs(entry - stop)
    if not m15t.m15_same_side(row, is_long):
        return None
    if not (m15t.SPEC_LO <= sd <= m15t.SPEC_HI):
        return None
    row["close"] = entry
    return row


def build_result_slot1_low(
    spec_lo: float,
    spec_hi: float,
    top_pct: float,
    bias55_threshold: float,
    stage1_r: float,
    stage2_trail_r: float,
    stage2_force_r: float,
):
    df, h2, m15 = cb.load_market_context()

    old_pct_lo, old_pct_hi = pct.SPEC_LO, pct.SPEC_HI
    old_bias55 = pct.BIAS_55_THRESHOLD
    old_m15_lo, old_m15_hi = m15t.SPEC_LO, m15t.SPEC_HI
    try:
        pct.SPEC_LO, pct.SPEC_HI = spec_lo, spec_hi
        pct.BIAS_55_THRESHOLD = bias55_threshold
        m15t.SPEC_LO, m15t.SPEC_HI = spec_lo, spec_hi

        q2_pass_set, q2_factor_map, _, _ = cb.h2t.early_precompute(h2, df, 2, False)
        raw_df, accepted = cb.combo.build_candidate_frames(df, q2_pass_set, q2_factor_map)

        m15_start = pd.Timestamp(m15["date"].min())
        pre_cov = accepted[pd.to_datetime(accepted["date"]) < m15_start].reset_index(drop=True)
        cov = accepted[pd.to_datetime(accepted["date"]) >= m15_start].reset_index(drop=True)

        cov_mod, _ = m15t.apply_replace_variant(
            cov,
            m15,
            choose_slot1_low_by_distance,
            "ea_slot1_low_replace",
            require_earlier=True,
            reanchor_stop_by_distance=True,
        )
        rejected_runtime = raw_df[(~raw_df["spec_pass"]) & m15t.coverage_mask(raw_df, m15_start)].copy()
        rescued, _ = m15t.build_rescued_trades(
            rejected_runtime,
            m15,
            choose_slot1_low_by_distance,
            variant_name="ea_slot1_low_runtime_rescue",
            reanchor_stop_by_distance=True,
        )

        cov_merged = m15t.dedupe_anchor(cov_mod.to_dict("records") + rescued.to_dict("records"))
        final_acc = cb.combo.combine_full_sample(pre_cov, cov_merged).sort_values("date").reset_index(drop=True)
        final_acc = cb.apply_m30_close_proxy(final_acc, df)
        final_acc["year"] = pd.to_datetime(final_acc["date"]).dt.year

        threshold, picked = cb.apply_layer3_ea_executable(final_acc, h2, top_pct=top_pct)
        trades = cb.s12.summarize_variant(df, picked, stage1_r, stage2_trail_r, stage2_force_r)
        total_m = cb.s12.metric(trades["total_points"].values)
        train_m, test_m = cb.s12.split_metrics(trades)
        return {
            "df": df,
            "h2": h2,
            "accepted": final_acc,
            "threshold": threshold,
            "picked": picked,
            "trades": trades,
            "total": total_m,
            "train": train_m,
            "test": test_m,
            "ea_executable_diag": True,
            "slot1_proxy": "slot1_low",
        }
    finally:
        pct.SPEC_LO, pct.SPEC_HI = old_pct_lo, old_pct_hi
        pct.BIAS_55_THRESHOLD = old_bias55
        m15t.SPEC_LO, m15t.SPEC_HI = old_m15_lo, old_m15_hi


def render_summary(
    baseline_outputs: dict[str, pd.DataFrame],
    low_outputs: dict[str, pd.DataFrame],
    baseline_m15: pd.DataFrame,
    low_m15: pd.DataFrame,
    output_dir: Path,
) -> str:
    lines = [
        "# M15 SLOT1 = slot1_low 诊断分支",
        "",
        f"- 输出目录：`{output_dir}`",
        "",
        "## 总量对比",
        "",
        "| 口径 | Python执行信号数 | 共同信号数 | 共同但字段不一致 | MT5独有 | Python独有 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        f"| 当前EA可执行诊断 | {len(baseline_outputs['python'])} | {len(baseline_outputs['shared'])} | {len(baseline_outputs['shared_mismatch'])} | {len(baseline_outputs['mt5_only'])} | {len(baseline_outputs['python_only'])} |",
        f"| slot1_low 诊断分支 | {len(low_outputs['python'])} | {len(low_outputs['shared'])} | {len(low_outputs['shared_mismatch'])} | {len(low_outputs['mt5_only'])} | {len(low_outputs['python_only'])} |",
        "",
        "## M15 SLOT1 共享残差对比",
        "",
        "| 口径 | 笔数 | 平均绝对误差 | 中位数绝对误差 | 最大绝对误差 |",
        "| --- | ---: | ---: | ---: | ---: |",
        f"| 当前EA可执行诊断 | {len(baseline_m15)} | {baseline_m15['abs_diff'].mean():.6f} | {baseline_m15['abs_diff'].median():.6f} | {baseline_m15['abs_diff'].max():.6f} |",
        f"| slot1_low 诊断分支 | {len(low_m15)} | {low_m15['abs_diff'].mean():.6f} | {low_m15['abs_diff'].median():.6f} | {low_m15['abs_diff'].max():.6f} |",
        "",
    ]

    if not low_m15.empty:
        lines.extend(
            [
                "## slot1_low 分支逐笔结果",
                "",
                low_m15[
                    [
                        "anchor_time_mt5",
                        "dir_mt5",
                        "trigger_mt5",
                        "mt5_stop_dist",
                        "python_stop_dist_1dp",
                        "abs_diff",
                        "variant",
                    ]
                ].to_markdown(index=False),
                "",
            ]
        )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate slot1_low diagnostic branch against cached session diff.")
    parser.add_argument("--session-dir", type=Path, required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--spec-lo", type=float, required=True)
    parser.add_argument("--spec-hi", type=float, required=True)
    parser.add_argument("--top-pct", type=float, required=True)
    parser.add_argument("--bias55-threshold", type=float, required=True)
    parser.add_argument("--stage1-r", type=float, required=True)
    parser.add_argument("--stage2-trail-r", type=float, required=True)
    parser.add_argument("--stage2-force-r", type=float, required=True)
    args = parser.parse_args()

    output_dir = args.session_dir
    mt5 = read_csv_with_fallback(output_dir / "mt5_signals.csv")
    for col in ["anchor_time", "mt5_raw_anchor_time", "log_time"]:
        if col in mt5.columns:
            mt5[col] = pd.to_datetime(mt5[col])

    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end)

    baseline_result = cb.summarize_strategy(
        spec_lo=args.spec_lo,
        spec_hi=args.spec_hi,
        top_pct=args.top_pct,
        bias55_threshold=args.bias55_threshold,
        stage1_r=args.stage1_r,
        stage2_trail_r=args.stage2_trail_r,
        stage2_force_r=args.stage2_force_r,
        ea_executable_diag=True,
    )
    baseline_py = build_python_executed_signals(baseline_result, start, end)
    baseline_py["key"] = baseline_py["anchor_time"].dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + baseline_py["dir"]
    baseline_py["python_stop_dist_1dp"] = baseline_py["sd"].round(1)
    baseline_outputs = build_diff(mt5, baseline_py)

    low_result = build_result_slot1_low(
        spec_lo=args.spec_lo,
        spec_hi=args.spec_hi,
        top_pct=args.top_pct,
        bias55_threshold=args.bias55_threshold,
        stage1_r=args.stage1_r,
        stage2_trail_r=args.stage2_trail_r,
        stage2_force_r=args.stage2_force_r,
    )
    low_py = build_python_executed_signals(low_result, start, end)
    low_py["key"] = low_py["anchor_time"].dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + low_py["dir"]
    low_py["python_stop_dist_1dp"] = low_py["sd"].round(1)
    low_outputs = build_diff(mt5, low_py)

    baseline_m15 = baseline_outputs["shared_mismatch"].copy()
    low_m15 = low_outputs["shared_mismatch"].copy()
    baseline_m15 = baseline_m15[baseline_m15["trigger_mt5"] == "M15 SLOT1"].copy()
    low_m15 = low_m15[low_m15["trigger_mt5"] == "M15 SLOT1"].copy()
    for frame in (baseline_m15, low_m15):
        if not frame.empty:
            frame["abs_diff"] = (frame["mt5_stop_dist"] - frame["python_stop_dist_1dp"]).abs()

    export_csv(low_outputs["python"].drop(columns=["key"], errors="ignore"), output_dir / "python_executed_signals_slot1_low.csv")
    export_csv(low_outputs["shared"].drop(columns=["key"], errors="ignore"), output_dir / "shared_signals_slot1_low.csv")
    export_csv(low_outputs["shared_mismatch"].drop(columns=["key"], errors="ignore"), output_dir / "shared_mismatch_slot1_low.csv")
    export_csv(low_outputs["mt5_only"].drop(columns=["key"], errors="ignore"), output_dir / "mt5_only_signals_slot1_low.csv")
    export_csv(low_outputs["python_only"].drop(columns=["key"], errors="ignore"), output_dir / "python_only_signals_slot1_low.csv")
    export_csv(baseline_m15, output_dir / "shared_m15_mismatch_baseline.csv")
    export_csv(low_m15, output_dir / "shared_m15_mismatch_slot1_low.csv")

    summary_text = render_summary(baseline_outputs, low_outputs, baseline_m15, low_m15, output_dir)
    write_text(output_dir / "slot1_low_branch_eval_20260708.md", summary_text)
    print(f"Wrote {output_dir / 'slot1_low_branch_eval_20260708.md'}")


if __name__ == "__main__":
    main()
