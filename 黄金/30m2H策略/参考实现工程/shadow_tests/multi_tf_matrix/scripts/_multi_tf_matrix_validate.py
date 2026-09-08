# -*- coding: utf-8 -*-
"""Validate each multi-timeframe combo with a 30m2H-like parameter workflow."""
import itertools
import os
import sys
from datetime import datetime

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import _stage12_combo_test as s12
from shadow_tests.multi_tf_matrix.scripts import _multi_tf_matrix_common as common


SHADOW_ROOT = os.path.join(ROOT, "shadow_tests", "multi_tf_matrix")
RESULT_ROOT = os.path.join(SHADOW_ROOT, "data", "validation_20260701")
REPORT_PATH = os.path.join(SHADOW_ROOT, "results", "multi_tf_matrix_validation_report.md")
PICK_CSV = os.path.join(RESULT_ROOT, "combo_candidate_pick.csv")
STAGE12_CSV = os.path.join(RESULT_ROOT, "combo_stage12_sweep.csv")
POSITION_CSV = os.path.join(RESULT_ROOT, "combo_position_sizing.csv")
BEST_STAGE_TRADES_CSV = os.path.join(RESULT_ROOT, "combo_best_stage12_trades.csv")

STAGE1_VALUES = [1.0, 1.2, 1.5, 2.0]
STAGE2_TRAIL_VALUES = [1.5, 2.0, 2.5]
STAGE2_FORCE_VALUES = [2.5, 3.0, 4.0]
POSITION_GRID = [0.5, 1.0, 1.5, 2.0]
TOTAL_UNITS = 3.0
UNIT_LOT = 0.02
PT_VALUE_PER_LOT = 10.0


def score_stage12(frame):
    frame = frame.copy()
    frame["sample_ok"] = frame["n"] >= 50
    frame["score"] = (
        frame["sample_ok"].astype(int) * 1000
        + frame["pf"] * 10
        + frame["test_pf"] * 2
        + frame["ev"] * 0.02
    )
    return frame


def evaluate_position_sizing(out, units):
    weighted_points = (
        units[0] * out["stage1_pnl"]
        + units[1] * out["stage2_pnl"]
        + units[2] * out["stage3_pnl"]
    )
    dollars = weighted_points * UNIT_LOT * PT_VALUE_PER_LOT
    total_m = common.metric(weighted_points.values)
    train_m, test_m = common.split_metrics(weighted_points.values, pd.to_datetime(out["date"]))
    return {
        "units": f"{units[0]:.1f}/{units[1]:.1f}/{units[2]:.1f}",
        "lots": f"{units[0] * UNIT_LOT:.2f}/{units[1] * UNIT_LOT:.2f}/{units[2] * UNIT_LOT:.2f}",
        "n": total_m["n"],
        "wr": total_m["wr"],
        "pf": total_m["pf"],
        "ev": total_m["ev"],
        "pnl_$": float(dollars.sum()),
        "maxcl": total_m["ml"],
        "test_pf": test_m["pf"],
        "test_ev": test_m["ev"],
    }


def choose_position(summary_df):
    scored = summary_df.copy()
    scored["balanced_bonus"] = (scored["units"] == "0.5/1.0/1.5").astype(int)
    scored["score"] = scored["pf"] * 10 + scored["test_pf"] * 2 + scored["ev"] * 0.02 + scored["balanced_bonus"] * 0.3
    return scored.sort_values(["score", "test_ev", "pnl_$"], ascending=[False, False, False]).iloc[0]


def render_report(picks_df, stage12_df, position_df):
    pick_rows = []
    for _, row in picks_df.iterrows():
        pick_rows.append([
            row["combo"], row["variant"], row["desc"], int(row["n"]),
            f"{row['wr']:.1f}%", f"{row['pf']:.2f}", f"{row['ev']:+.2f}pt",
            f"{row['test_pf']:.2f}", f"{row['test_ev']:+.2f}pt",
        ])

    best_stage_rows = []
    for _, row in stage12_df.sort_values("combo").groupby("combo").head(1).iterrows():
        best_stage_rows.append([
            row["combo"], row["variant"],
            f"{row['stage1_r']:.1f}", f"{row['stage2_trail_r']:.1f}", f"{row['stage2_force_r']:.1f}",
            int(row["n"]), f"{row['wr']:.1f}%", f"{row['pf']:.2f}", f"{row['ev']:+.2f}pt",
            f"{row['test_pf']:.2f}", f"{row['test_ev']:+.2f}pt",
        ])

    best_position_rows = []
    for _, row in position_df.sort_values("combo").groupby("combo").head(1).iterrows():
        best_position_rows.append([
            row["combo"], row["variant"], row["units"], row["lots"], int(row["n"]),
            f"{row['wr']:.1f}%", f"{row['pf']:.2f}", f"{row['ev']:+.2f}pt",
            f"${row['pnl_$']:.0f}", f"{row['test_pf']:.2f}", f"{row['test_ev']:+.2f}pt",
        ])

    lines = []
    lines.append("# 多周期参数调整与验证报告")
    lines.append("")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("这轮按 `30M_2H` 主线的验证思路，对每个多周期组合依次做了：候选门选择 -> Stage1/Stage2 扫描 -> 仓位严格认证。")
    lines.append("")
    lines.append("## 1. 组合候选门选择")
    lines.append("")
    lines.append(common.md_table(
        ["组合", "候选门", "说明", "笔数", "WR", "PF", "EV", "验证PF", "验证EV"],
        pick_rows,
    ))
    lines.append("")
    lines.append("## 2. 每组最优 Stage1/2")
    lines.append("")
    lines.append(common.md_table(
        ["组合", "候选门", "Stage1R", "TrailR", "ForceR", "笔数", "WR", "PF", "EV", "验证PF", "验证EV"],
        best_stage_rows,
    ))
    lines.append("")
    lines.append("## 3. 每组最优仓位")
    lines.append("")
    lines.append(common.md_table(
        ["组合", "候选门", "Units", "Lots", "笔数", "WR", "PF", "EV", "PnL", "验证PF", "验证EV"],
        best_position_rows,
    ))
    lines.append("")
    lines.append("## 4. 当前结论")
    lines.append("")
    lines.append("- 多周期组合可以沿用主线的验证节奏，但它们当前更像附加门，不像完整替代主线。")
    lines.append("- 第一优先应该先看样本是否还能守住 `>= 50`，再看 PF / EV；否则很容易挑到漂亮但过窄的门。")
    lines.append("- 这轮暂时只把 Stage1/2 和仓位这一段通用化；如果你要继续收口，我们下一步就补“组合门强度细扫”，作为多周期版的严格认证层。")
    lines.append("")
    lines.append("## 文件")
    lines.append("")
    lines.append(f"- `shadow_tests\\multi_tf_matrix\\data\\validation_20260701\\{os.path.basename(PICK_CSV)}`")
    lines.append(f"- `shadow_tests\\multi_tf_matrix\\data\\validation_20260701\\{os.path.basename(STAGE12_CSV)}`")
    lines.append(f"- `shadow_tests\\multi_tf_matrix\\data\\validation_20260701\\{os.path.basename(POSITION_CSV)}`")
    lines.append(f"- `shadow_tests\\multi_tf_matrix\\data\\validation_20260701\\{os.path.basename(BEST_STAGE_TRADES_CSV)}`")
    lines.append("")
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    os.makedirs(RESULT_ROOT, exist_ok=True)

    bundle = common.load_mainline_bundle()
    baseline = bundle["signals"]
    all_frames = sorted({frame for combo in common.TIMEFRAME_MATRIX for frame in combo["frames"]}, key=common.tf_label_to_hours)
    ctx = common.attach_all_context(baseline, all_frames)

    variant_items = []
    summary_rows = []
    for combo in common.TIMEFRAME_MATRIX:
        for item in common.build_combo_variant_frames(combo, ctx):
            variant_items.append(item)
            summary_rows.append(common.summarize_variant_item(item))
    summary_df = pd.DataFrame(summary_rows)
    picks_df = common.choose_primary_candidates(summary_df).sort_values("combo").reset_index(drop=True)
    picks_df.to_csv(PICK_CSV, index=False, encoding="utf-8-sig")

    m30_df = bundle["df"]
    stage12_rows = []
    best_trade_frames = []
    position_rows = []

    for _, pick in picks_df.iterrows():
        item = next(x for x in variant_items if x["variant"] == pick["variant"])
        signals = item["frame"].copy().sort_values("date").reset_index(drop=True)

        combo_stage_rows = []
        best_out = None
        best_score = None
        for stage1_r in STAGE1_VALUES:
            for trail_r in STAGE2_TRAIL_VALUES:
                for force_r in STAGE2_FORCE_VALUES:
                    if force_r <= trail_r:
                        continue
                    out = s12.summarize_variant(m30_df, signals, stage1_r, trail_r, force_r)
                    total_m = s12.metric(out["total_points"].values)
                    train_m, test_m = s12.split_metrics(out)
                    row = {
                        "combo": pick["combo"],
                        "variant": pick["variant"],
                        "stage1_r": stage1_r,
                        "stage2_trail_r": trail_r,
                        "stage2_force_r": force_r,
                        "n": total_m["n"],
                        "wr": total_m["wr"],
                        "pf": total_m["pf"],
                        "ev": total_m["ev"],
                        "pnl": total_m["pnl"],
                        "maxcl": total_m["ml"],
                        "test_pf": test_m["pf"],
                        "test_ev": test_m["ev"],
                    }
                    combo_stage_rows.append(row)
                    score = (total_m["n"] >= 50, total_m["pf"], test_m["pf"], total_m["ev"], test_m["ev"])
                    if best_score is None or score > best_score:
                        best_score = score
                        best_out = out.copy()
        combo_stage_df = score_stage12(pd.DataFrame(combo_stage_rows))
        combo_best = combo_stage_df.sort_values(["score", "test_ev", "pnl"], ascending=[False, False, False]).iloc[0]
        stage12_rows.extend(combo_stage_rows)

        tagged_best_out = best_out.copy()
        tagged_best_out["combo"] = pick["combo"]
        tagged_best_out["variant"] = pick["variant"]
        tagged_best_out["picked_stage1_r"] = combo_best["stage1_r"]
        tagged_best_out["picked_stage2_trail_r"] = combo_best["stage2_trail_r"]
        tagged_best_out["picked_stage2_force_r"] = combo_best["stage2_force_r"]
        best_trade_frames.append(tagged_best_out)

        for units in itertools.product(POSITION_GRID, repeat=3):
            if abs(sum(units) - TOTAL_UNITS) > 1e-9:
                continue
            p = evaluate_position_sizing(best_out, units)
            p["combo"] = pick["combo"]
            p["variant"] = pick["variant"]
            p["stage1_r"] = combo_best["stage1_r"]
            p["stage2_trail_r"] = combo_best["stage2_trail_r"]
            p["stage2_force_r"] = combo_best["stage2_force_r"]
            position_rows.append(p)

    stage12_df = score_stage12(pd.DataFrame(stage12_rows)).sort_values(
        ["combo", "score", "test_ev", "pnl"], ascending=[True, False, False, False]
    ).reset_index(drop=True)
    stage12_df.to_csv(STAGE12_CSV, index=False, encoding="utf-8-sig")

    best_trades_df = pd.concat(best_trade_frames, ignore_index=True)
    best_trades_df.to_csv(BEST_STAGE_TRADES_CSV, index=False, encoding="utf-8-sig")

    position_df = pd.DataFrame(position_rows)
    best_positions = []
    for combo, frame in position_df.groupby("combo"):
        best_positions.append(choose_position(frame))
    position_best_df = pd.DataFrame(best_positions).sort_values("combo").reset_index(drop=True)
    position_df = position_df.sort_values(["combo", "pf", "test_pf", "ev"], ascending=[True, False, False, False]).reset_index(drop=True)
    position_df.to_csv(POSITION_CSV, index=False, encoding="utf-8-sig")

    render_report(picks_df, stage12_df, position_best_df)

    print(f"Wrote {PICK_CSV}")
    print(f"Wrote {STAGE12_CSV}")
    print(f"Wrote {POSITION_CSV}")
    print(f"Wrote {BEST_STAGE_TRADES_CSV}")
    print(f"Wrote {REPORT_PATH}")
    print(position_best_df[["combo", "variant", "units", "pf", "ev", "test_pf", "test_ev"]].to_string(index=False))


if __name__ == "__main__":
    main()
