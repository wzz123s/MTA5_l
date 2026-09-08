# -*- coding: utf-8 -*-
"""Scan stop-width bands on the current certified combo samples."""
import math
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
FINAL_SUMMARY_CSV = os.path.join(VALIDATION_ROOT, "combo_final_best_summary.csv")
TRADES_CSV = os.path.join(VALIDATION_ROOT, "combo_best_stage12_trades.csv")
DETAIL_CSV = os.path.join(VALIDATION_ROOT, "组合止损范围测试_中文.csv")
SUMMARY_CSV = os.path.join(VALIDATION_ROOT, "组合止损范围推荐_中文.csv")
REPORT_PATH = os.path.join(SHADOW_ROOT, "results", "多周期组合止损范围测试报告.md")

UNIT_LOT = 0.02
PT_VALUE_PER_LOT = 10.0
MIN_SAMPLE = 50


def units_to_tuple(label):
    return tuple(float(x) for x in str(label).split("/"))


def round_down(value, step):
    return math.floor(float(value) / step) * step


def round_up(value, step):
    return math.ceil(float(value) / step) * step


def choose_step(sd_series):
    median = float(sd_series.median())
    if median <= 30:
        return 2
    if median <= 80:
        return 5
    return 10


def build_stop_band_grid(sd_series):
    sd = pd.Series(sd_series).dropna().astype(float)
    if sd.empty:
        return [], [], []

    step = choose_step(sd)
    lo_qs = [0.10, 0.20, 0.30, 0.40]
    hi_qs = [0.60, 0.70, 0.80, 0.90]

    lo_values = {
        max(step, int(round_down(sd.quantile(q), step)))
        for q in lo_qs
    }
    hi_values = {
        max(step * 2, int(round_up(sd.quantile(q), step)))
        for q in hi_qs
    }

    lo_values.add(max(step, int(round_down(sd.min(), step))))
    hi_values.add(max(step * 2, int(round_up(sd.max(), step))))

    lo_sorted = sorted(lo_values)
    hi_sorted = sorted(hi_values)
    bands = []
    for spec_lo in lo_sorted:
        for spec_hi in hi_sorted:
            if spec_hi <= spec_lo:
                continue
            if spec_hi - spec_lo < step:
                continue
            bands.append((spec_lo, spec_hi))
    return bands, lo_sorted, hi_sorted


def evaluate_band(frame, units):
    weighted_points = (
        units[0] * frame["stage1_pnl"].astype(float)
        + units[1] * frame["stage2_pnl"].astype(float)
        + units[2] * frame["stage3_pnl"].astype(float)
    )
    dollars = weighted_points * UNIT_LOT * PT_VALUE_PER_LOT
    total_m = common.metric(weighted_points.values)
    train_m, test_m = common.split_metrics(weighted_points.values, pd.to_datetime(frame["date"]))
    return {
        "交易数": total_m["n"],
        "胜率": total_m["wr"],
        "盈亏比PF": total_m["pf"],
        "期望EV_pt": total_m["ev"],
        "总盈利$": float(dollars.sum()),
        "验证PF": test_m["pf"],
        "验证EV_pt": test_m["ev"],
        "实际止损均值pt": float(frame["sd"].mean()) if len(frame) else 0.0,
        "实际止损中位数pt": float(frame["sd"].median()) if len(frame) else 0.0,
    }


def add_score(frame):
    scoped = frame.copy()
    scoped["样本达标"] = scoped["交易数"] >= MIN_SAMPLE
    scoped["评分"] = (
        scoped["样本达标"].astype(int) * 1000
        + scoped["盈亏比PF"].clip(upper=200) * 10
        + scoped["验证PF"].clip(upper=50) * 2
        + scoped["期望EV_pt"] * 0.02
    )
    return scoped


def band_label(row):
    return f"{int(row['止损下限pt'])}-{int(row['止损上限pt'])}pt"


def acceptable_range_label(frame):
    acceptable = frame[frame["样本达标"]].copy()
    if acceptable.empty:
        return band_label(frame.iloc[0])
    top_score = float(acceptable["评分"].max())
    scoped = acceptable[acceptable["评分"] >= top_score * 0.95].copy()
    return f"{int(scoped['止损下限pt'].min())}-{int(scoped['止损上限pt'].max())}pt"


def main():
    final_summary = pd.read_csv(FINAL_SUMMARY_CSV, encoding="utf-8-sig")
    trades = pd.read_csv(TRADES_CSV, encoding="utf-8-sig")
    trades["date"] = pd.to_datetime(trades["date"])

    bundle = common.load_mainline_bundle()
    base_signals = bundle["signals"].copy()
    all_frames = sorted(
        {frame for combo in common.TIMEFRAME_MATRIX for frame in combo["frames"]},
        key=common.tf_label_to_hours,
    )
    ctx_signals = common.attach_all_context(base_signals, all_frames)

    detail_rows = []
    summary_rows = []

    for _, final_row in final_summary.sort_values("combo").iterrows():
        combo = final_row["combo"]
        units = units_to_tuple(final_row["units"])
        focus_label = common.extract_focus_label(final_row["picked_variant"], combo)
        combo_signal_frame = common.recompute_focus_sd(ctx_signals.copy(), focus_label)

        combo_frame = trades[
            (trades["combo"] == combo)
            & (trades["variant"] == final_row["picked_variant"])
            & (trades["picked_stage1_r"] == final_row["stage1_r"])
            & (trades["picked_stage2_trail_r"] == final_row["stage2_trail_r"])
            & (trades["picked_stage2_force_r"] == final_row["stage2_force_r"])
        ].copy()
        combo_frame = combo_frame.merge(
            combo_signal_frame[["date", "mode", "dir", "focus_stop", "focus_sd"]],
            on=["date", "mode", "dir"],
            how="left",
        )
        combo_frame["sd"] = combo_frame["focus_sd"]
        combo_frame = combo_frame.dropna(subset=["sd"]).reset_index(drop=True)

        bands, lo_grid, hi_grid = build_stop_band_grid(combo_frame["sd"])
        combo_rows = []
        for spec_lo, spec_hi in bands:
            scoped = combo_frame[combo_frame["sd"].between(spec_lo, spec_hi, inclusive="both")].copy()
            metrics = evaluate_band(scoped, units)
            combo_rows.append({
                "策略组合": combo,
                "当前组合门": final_row["picked_variant"],
                "聚焦周期": focus_label.upper(),
                "止损范围": f"{spec_lo}-{spec_hi}pt",
                "止损下限pt": spec_lo,
                "止损上限pt": spec_hi,
                "扫描下限集": "/".join(str(x) for x in lo_grid),
                "扫描上限集": "/".join(str(x) for x in hi_grid),
                **metrics,
            })

        combo_df = add_score(pd.DataFrame(combo_rows)).sort_values(
            ["评分", "验证EV_pt", "总盈利$", "交易数"],
            ascending=[False, False, False, False],
        ).reset_index(drop=True)
        detail_rows.extend(combo_df.to_dict("records"))

        viable = combo_df[combo_df["交易数"] >= MIN_SAMPLE].copy()
        ranked = viable if len(viable) else combo_df
        primary = ranked.iloc[0]
        secondary = ranked.iloc[1] if len(ranked) >= 2 else primary
        acceptable_range = acceptable_range_label(ranked)

        summary_rows.append({
            "策略组合": combo,
            "当前组合门": final_row["picked_variant"],
            "聚焦周期": focus_label.upper(),
            "当前阶段参数": f"{final_row['stage1_r']:.1f}/{final_row['stage2_trail_r']:.1f}/{final_row['stage2_force_r']:.1f}",
            "当前仓位单位": final_row["units"],
            "止损扫描下限集": "/".join(str(x) for x in lo_grid),
            "止损扫描上限集": "/".join(str(x) for x in hi_grid),
            "主推荐止损范围": band_label(primary),
            "次优止损范围": band_label(secondary),
            "可接受止损区间": acceptable_range,
            "止损范围说明": (
                f"聚焦 {focus_label.upper()}，按本策略 sd 分布单独扫描；"
                f"主推荐 {band_label(primary)}，次优 {band_label(secondary)}，可接受区间 {acceptable_range}"
            ),
            "主推荐交易数": int(primary["交易数"]),
            "主推荐PF": float(primary["盈亏比PF"]),
            "主推荐验证PF": float(primary["验证PF"]),
            "主推荐EV_pt": float(primary["期望EV_pt"]),
            "主推荐总盈利$": float(primary["总盈利$"]),
        })

    detail_df = pd.DataFrame(detail_rows).sort_values(
        ["策略组合", "评分", "验证EV_pt", "总盈利$"],
        ascending=[True, False, False, False],
    ).reset_index(drop=True)
    summary_df = pd.DataFrame(summary_rows).sort_values("策略组合").reset_index(drop=True)

    detail_df.to_csv(DETAIL_CSV, index=False, encoding="utf-8-sig")
    summary_df.to_csv(SUMMARY_CSV, index=False, encoding="utf-8-sig")

    lines = []
    lines.append("# 多周期组合止损范围测试报告")
    lines.append("")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("本轮在每个策略当前已认证的组合门、Stage 参数、仓位参数上，按各自聚焦周期重算 `sd`，并按各自 `sd` 分布单独扫描止损区间。")
    lines.append("")
    lines.append("## 推荐区间")
    lines.append("")
    lines.append(common.md_table(
        ["策略组合", "聚焦周期", "主推荐", "次优", "可接受区间", "交易数", "PF", "验证PF", "EV"],
        [
            [
                row["策略组合"],
                row["聚焦周期"],
                row["主推荐止损范围"],
                row["次优止损范围"],
                row["可接受止损区间"],
                int(row["主推荐交易数"]),
                f"{row['主推荐PF']:.2f}",
                f"{row['主推荐验证PF']:.2f}",
                f"{row['主推荐EV_pt']:+.2f}pt",
            ]
            for _, row in summary_df.iterrows()
        ],
    ))
    lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote {DETAIL_CSV}")
    print(f"Wrote {SUMMARY_CSV}")
    print(f"Wrote {REPORT_PATH}")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
