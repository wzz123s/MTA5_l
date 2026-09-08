# -*- coding: utf-8 -*-
"""Render a full per-strategy certification pack for multi-timeframe combos."""
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
PICK_CSV = os.path.join(VALIDATION_ROOT, "combo_candidate_pick.csv")
STAGE12_CSV = os.path.join(VALIDATION_ROOT, "combo_stage12_sweep.csv")
POSITION_CSV = os.path.join(VALIDATION_ROOT, "combo_position_sizing.csv")
TRADES_CSV = os.path.join(VALIDATION_ROOT, "combo_best_stage12_trades.csv")

FINAL_SUMMARY_CSV = os.path.join(VALIDATION_ROOT, "combo_final_best_summary.csv")
TOP_STAGE12_CSV = os.path.join(VALIDATION_ROOT, "combo_top3_stage12.csv")
TOP_POSITION_CSV = os.path.join(VALIDATION_ROOT, "combo_top3_position.csv")
REPORT_PATH = os.path.join(SHADOW_ROOT, "results", "multi_tf_matrix_full_certification_report.md")


def pick_stage12_best(frame):
    ranked = frame.sort_values(["score", "test_ev", "pnl"], ascending=[False, False, False]).reset_index(drop=True)
    return ranked.iloc[0], ranked.head(3)


def pick_position_best(frame):
    scoped = frame.copy()
    scoped["balanced_bonus"] = (scoped["units"] == "0.5/1.0/1.5").astype(int)
    scoped["score"] = scoped["pf"] * 10 + scoped["test_pf"] * 2 + scoped["ev"] * 0.02 + scoped["balanced_bonus"] * 0.3
    ranked = scoped.sort_values(["score", "test_ev", "pnl_$"], ascending=[False, False, False]).reset_index(drop=True)
    return ranked.iloc[0], ranked.head(3)


def trade_excerpt(frame, n=12):
    if frame.empty:
        return []
    out = frame.copy().sort_values("date").reset_index(drop=True)
    show = pd.concat([out.head(n // 2), out.tail(n - n // 2)], ignore_index=True)
    rows = []
    for _, row in show.iterrows():
        rows.append([
            f"{pd.Timestamp(row['date']):%Y-%m-%d %H:%M}",
            row["mode"],
            row["dir"],
            f"{row['stage1_pnl']:+.2f}",
            f"{row['stage2_pnl']:+.2f}",
            f"{row['stage3_pnl']:+.2f}",
            f"{row['total_points']:+.2f}",
            row["stage1_exit"],
            row["stage2_exit"],
            row["stage3_exit"],
        ])
    return rows


def main():
    picks = pd.read_csv(PICK_CSV, encoding="utf-8-sig")
    stage12 = pd.read_csv(STAGE12_CSV, encoding="utf-8-sig")
    position = pd.read_csv(POSITION_CSV, encoding="utf-8-sig")
    trades = pd.read_csv(TRADES_CSV, encoding="utf-8-sig")
    trades["date"] = pd.to_datetime(trades["date"])

    final_rows = []
    top_stage_rows = []
    top_position_rows = []
    report_lines = []
    report_lines.append("# 多周期完整认证报告")
    report_lines.append("")
    report_lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    report_lines.append("本报告把每个策略的认证结果完整串起来：候选门选择、Stage1/2 最优参数、仓位最优参数，以及对应的结果表现。")
    report_lines.append("")

    overview_rows = []

    for combo in picks["combo"].tolist():
        pick = picks[picks["combo"] == combo].iloc[0]
        s_frame = stage12[stage12["combo"] == combo].copy()
        z_frame = position[position["combo"] == combo].copy()

        best_stage, top3_stage = pick_stage12_best(s_frame)
        best_position, top3_position = pick_position_best(z_frame)

        for _, row in top3_stage.iterrows():
            top_stage_rows.append(row.to_dict())
        for _, row in top3_position.iterrows():
            top_position_rows.append(row.to_dict())

        final_rows.append({
            "combo": combo,
            "picked_variant": pick["variant"],
            "picked_desc": pick["desc"],
            "picked_n": int(pick["n"]),
            "picked_pf": float(pick["pf"]),
            "picked_ev": float(pick["ev"]),
            "picked_test_pf": float(pick["test_pf"]),
            "picked_test_ev": float(pick["test_ev"]),
            "stage1_r": float(best_stage["stage1_r"]),
            "stage2_trail_r": float(best_stage["stage2_trail_r"]),
            "stage2_force_r": float(best_stage["stage2_force_r"]),
            "stage_pf": float(best_stage["pf"]),
            "stage_ev": float(best_stage["ev"]),
            "stage_test_pf": float(best_stage["test_pf"]),
            "stage_test_ev": float(best_stage["test_ev"]),
            "units": best_position["units"],
            "lots": best_position["lots"],
            "final_pf": float(best_position["pf"]),
            "final_ev": float(best_position["ev"]),
            "final_pnl_$": float(best_position["pnl_$"]),
            "final_test_pf": float(best_position["test_pf"]),
            "final_test_ev": float(best_position["test_ev"]),
        })

        overview_rows.append([
            combo,
            pick["variant"],
            f"{best_stage['stage1_r']:.1f}/{best_stage['stage2_trail_r']:.1f}/{best_stage['stage2_force_r']:.1f}",
            best_position["units"],
            f"{best_position['pf']:.2f}",
            f"{best_position['ev']:+.2f}pt",
            f"${best_position['pnl_$']:.0f}",
            f"{best_position['test_pf']:.2f}",
            f"{best_position['test_ev']:+.2f}pt",
        ])

        report_lines.append(f"## {combo}")
        report_lines.append("")
        report_lines.append("### 最终采用参数")
        report_lines.append("")
        report_lines.append(common.md_table(
            ["项", "值"],
            [
                ["候选门", pick["variant"]],
                ["候选门说明", pick["desc"]],
                ["候选门样本", int(pick["n"])],
                ["Stage 参数", f"Stage1={best_stage['stage1_r']:.1f}R, Trail={best_stage['stage2_trail_r']:.1f}R, Force={best_stage['stage2_force_r']:.1f}R"],
                ["仓位参数", f"units={best_position['units']} / lots={best_position['lots']}"],
                ["最终 PF / EV", f"{best_position['pf']:.2f} / {best_position['ev']:+.2f}pt"],
                ["最终验证段 PF / EV", f"{best_position['test_pf']:.2f} / {best_position['test_ev']:+.2f}pt"],
                ["最终 PnL", f"${best_position['pnl_$']:.0f}"],
            ],
        ))
        report_lines.append("")

        report_lines.append("### 候选门结果")
        report_lines.append("")
        report_lines.append(common.md_table(
            ["笔数", "WR", "PF", "EV", "验证PF", "验证EV"],
            [[int(pick["n"]), f"{pick['wr']:.1f}%", f"{pick['pf']:.2f}", f"{pick['ev']:+.2f}pt", f"{pick['test_pf']:.2f}", f"{pick['test_ev']:+.2f}pt"]],
        ))
        report_lines.append("")

        report_lines.append("### Stage1/2 前 3 名")
        report_lines.append("")
        report_lines.append(common.md_table(
            ["Stage1R", "TrailR", "ForceR", "笔数", "WR", "PF", "EV", "验证PF", "验证EV"],
            [
                [
                    f"{row['stage1_r']:.1f}",
                    f"{row['stage2_trail_r']:.1f}",
                    f"{row['stage2_force_r']:.1f}",
                    int(row["n"]),
                    f"{row['wr']:.1f}%",
                    f"{row['pf']:.2f}",
                    f"{row['ev']:+.2f}pt",
                    f"{row['test_pf']:.2f}",
                    f"{row['test_ev']:+.2f}pt",
                ]
                for _, row in top3_stage.iterrows()
            ],
        ))
        report_lines.append("")

        report_lines.append("### 仓位前 3 名")
        report_lines.append("")
        report_lines.append(common.md_table(
            ["Units", "Lots", "笔数", "WR", "PF", "EV", "PnL", "验证PF", "验证EV"],
            [
                [
                    row["units"],
                    row["lots"],
                    int(row["n"]),
                    f"{row['wr']:.1f}%",
                    f"{row['pf']:.2f}",
                    f"{row['ev']:+.2f}pt",
                    f"${row['pnl_$']:.0f}",
                    f"{row['test_pf']:.2f}",
                    f"{row['test_ev']:+.2f}pt",
                ]
                for _, row in top3_position.iterrows()
            ],
        ))
        report_lines.append("")

        trade_frame = trades[
            (trades["combo"] == combo)
            & (trades["picked_stage1_r"] == best_stage["stage1_r"])
            & (trades["picked_stage2_trail_r"] == best_stage["stage2_trail_r"])
            & (trades["picked_stage2_force_r"] == best_stage["stage2_force_r"])
        ].copy()
        excerpt = trade_excerpt(trade_frame)
        report_lines.append("### 最优 Stage 交易摘录")
        report_lines.append("")
        report_lines.append(common.md_table(
            ["Date", "Mode", "Dir", "S1", "S2", "S3", "Total", "Stage1 Exit", "Stage2 Exit", "Stage3 Exit"],
            excerpt,
        ))
        report_lines.append("")

    final_df = pd.DataFrame(final_rows).sort_values("combo").reset_index(drop=True)
    top_stage_df = pd.DataFrame(top_stage_rows).sort_values(["combo", "score", "test_ev"], ascending=[True, False, False]).reset_index(drop=True)
    top_position_df = pd.DataFrame(top_position_rows).sort_values(["combo", "pf", "test_pf", "ev"], ascending=[True, False, False, False]).reset_index(drop=True)

    final_df.to_csv(FINAL_SUMMARY_CSV, index=False, encoding="utf-8-sig")
    top_stage_df.to_csv(TOP_STAGE12_CSV, index=False, encoding="utf-8-sig")
    top_position_df.to_csv(TOP_POSITION_CSV, index=False, encoding="utf-8-sig")

    report_lines.insert(5, "## 总览")
    report_lines.insert(6, "")
    report_lines.insert(7, common.md_table(
        ["组合", "候选门", "Stage参数(S1/Trail/Force)", "仓位", "最终PF", "最终EV", "最终PnL", "验证PF", "验证EV"],
        overview_rows,
    ))
    report_lines.insert(8, "")

    report_lines.append("## 文件")
    report_lines.append("")
    report_lines.append(f"- `shadow_tests\\multi_tf_matrix\\data\\validation_20260701\\{os.path.basename(FINAL_SUMMARY_CSV)}`")
    report_lines.append(f"- `shadow_tests\\multi_tf_matrix\\data\\validation_20260701\\{os.path.basename(TOP_STAGE12_CSV)}`")
    report_lines.append(f"- `shadow_tests\\multi_tf_matrix\\data\\validation_20260701\\{os.path.basename(TOP_POSITION_CSV)}`")
    report_lines.append(f"- `shadow_tests\\multi_tf_matrix\\results\\{os.path.basename(REPORT_PATH)}`")
    report_lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"Wrote {FINAL_SUMMARY_CSV}")
    print(f"Wrote {TOP_STAGE12_CSV}")
    print(f"Wrote {TOP_POSITION_CSV}")
    print(f"Wrote {REPORT_PATH}")
    print(final_df.to_string(index=False))


if __name__ == "__main__":
    main()
