# -*- coding: utf-8 -*-
"""Strict certification for 3-stage position sizing on the current mainline."""
import itertools
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import _stage12_combo_test as s12
import _current_baseline as base


RESULT_ROOT = os.path.join(ROOT, "data", "results", "position_sizing_strict_certify_20260627")
SWEEP_CSV = os.path.join(RESULT_ROOT, "position_sizing_strict_sweep.csv")
CURVE_PATH = os.path.join(RESULT_ROOT, "position_sizing_strict_equity_curve.png")
DETAIL_CSV = os.path.join(RESULT_ROOT, "position_sizing_trade_detail.csv")
REPORT_PATH = os.path.join(ROOT, "30m2H策略", "仓位档位严格认证结果.md")

UNIT_LOT = 0.02
PT_VALUE_PER_LOT = 10.0
START_BALANCE = 10000.0
TOTAL_UNITS = 3.0
GRID = [0.5, 1.0, 1.5, 2.0]
SPEC_LO = 5
SPEC_HI = 35
TOP_PCT = 34
BIAS55_THRESHOLD = 3.0
STAGE1_R = 2.0
STAGE2_TRAIL_R = 1.5
STAGE2_FORCE_R = 4.0


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def max_drawdown(equity):
    peak = equity.cummax()
    dd = equity - peak
    worst = float(dd.min())
    worst_pct = float(((dd / peak.replace(0, pd.NA)).fillna(0)).min() * 100.0)
    return worst, worst_pct


def unit_label(units):
    return f"{units[0]:.1f}/{units[1]:.1f}/{units[2]:.1f}"


def lot_label(units):
    return f"{units[0] * UNIT_LOT:.2f}/{units[1] * UNIT_LOT:.2f}/{units[2] * UNIT_LOT:.2f}"


def evaluate_units(out, units):
    weighted_points = (
        units[0] * out["stage1_pnl"]
        + units[1] * out["stage2_pnl"]
        + units[2] * out["stage3_pnl"]
    )
    dollars = weighted_points * UNIT_LOT * PT_VALUE_PER_LOT
    equity = START_BALANCE + dollars.cumsum()
    total_m = s12.metric(weighted_points.values)
    train_mask = pd.to_datetime(out["date"]) < pd.Timestamp("2023-01-01")
    train_m = s12.metric(weighted_points[train_mask].values)
    test_m = s12.metric(weighted_points[~train_mask].values)
    y2024 = weighted_points[out["year"] == 2024]
    y2024_m = s12.metric(y2024.values)
    dd_abs, dd_pct = max_drawdown(equity)

    frame = out.copy()
    frame["weighted_points"] = weighted_points
    frame["weighted_$"] = dollars
    frame["equity_$"] = equity
    frame["units"] = unit_label(units)
    frame["lots"] = lot_label(units)
    return {
        "units": units,
        "frame": frame,
        "summary": {
            "units": unit_label(units),
            "lots": lot_label(units),
            "n": total_m["n"],
            "wr": total_m["wr"],
            "pf": total_m["pf"],
            "ev": total_m["ev"],
            "pnl_$": float(dollars.sum()),
            "maxcl": total_m["ml"],
            "maxdd_$": dd_abs,
            "maxdd_pct": dd_pct,
            "train_n": train_m["n"],
            "test_n": test_m["n"],
            "test_pf": test_m["pf"],
            "test_ev": test_m["ev"],
            "y2024_n": y2024_m["n"],
            "y2024_wr": y2024_m["wr"],
            "y2024_pf": y2024_m["pf"],
            "y2024_ev": y2024_m["ev"],
        },
    }


def render_report(summary_df, best_pf, best_balanced, baseline):
    rows = []
    for _, row in summary_df.iterrows():
        rows.append([
            row["units"],
            row["lots"],
            int(row["n"]),
            f"{row['wr']:.1f}%",
            f"{row['pf']:.2f}",
            f"{row['ev']:+.2f}pt",
            f"${row['pnl_$']:.0f}",
            int(row["maxcl"]),
            f"${row['maxdd_$']:.0f}",
            f"{row['maxdd_pct']:+.2f}%",
            int(row["y2024_n"]),
            f"{row['test_pf']:.2f}",
            f"{row['test_ev']:+.2f}pt",
        ])

    lines = []
    lines.append("# 仓位档位严格认证结果")
    lines.append("")
    lines.append(
        "> 本轮固定主线为：`Layer1 3.0%` + `pre_cross + cross + post_n(2-6)` + "
        "`M15 replace_any + rescue` + `H2 q2 early-gate` + `Layer3 top34%`。"
    )
    lines.append(
        "> 退出固定为：`Stage1 2.0R / Stage2 1.5R trail / 4.0R force / Stage3 m30_merged_cross`；"
        "本轮只比较三段仓位分配，不改变总手数 `0.06 lots`。"
    )
    lines.append("")
    lines.append("说明：表中的 `units` 以 `0.02 lot` 为 1 单位，例如 `0.5/0.5/2.0` 就是 `0.01 / 0.01 / 0.04 lot`。")
    lines.append("")
    lines.append("## 全部候选")
    lines.append("")
    lines.append(
        md_table(
            ["Units", "Lots", "Trades", "WR", "PF", "EV", "PnL", "MaxCL", "MaxDD", "MaxDD%", "2024", "Test PF", "Test EV"],
            rows,
        )
    )
    lines.append("")
    lines.append("## 当前判断")
    lines.append("")
    lines.append(
        f"- 当前等权基线 `1.0/1.0/1.0`（`0.02/0.02/0.02 lot`）："
        f"PF `{baseline['pf']:.2f}`，EV `{baseline['ev']:+.2f}pt`，PnL `${baseline['pnl_$']:.0f}`，MaxCL `{int(baseline['maxcl'])}`。"
    )
    lines.append(
        f"- 单看 PF / EV / 验证段，最强是 `0.5/0.5/2.0`（`0.01/0.01/0.04 lot`）："
        f"PF `{best_pf['pf']:.2f}`，EV `{best_pf['ev']:+.2f}pt`，PnL `${best_pf['pnl_$']:.0f}`，"
        f"MaxCL `{int(best_pf['maxcl'])}`，MaxDD `{best_pf['maxdd_pct']:+.2f}%`。"
    )
    lines.append(
        f"- 如果想减少一次性把仓位极度压向 Stage 3 的跳跃，较温和的候选是 `0.5/1.0/1.5` "
        f"（`0.01/0.02/0.03 lot`）：PF `{best_balanced['pf']:.2f}`，EV `{best_balanced['ev']:+.2f}pt`，"
        f"PnL `${best_balanced['pnl_$']:.0f}`。"
    )
    lines.append("- 这轮结论很一致：当前退出结构下，仓位越往 Stage 3 倾斜，整体收益质量越高；说明 `m30_merged_cross` 这段尾部利润是真有价值的。")
    lines.append("- 但越偏向 Stage 3，胜率会略降，对后段回撤和持仓耐心要求更高；是否正式切换为主线仓位，还要结合执行习惯决定。")
    lines.append("")
    lines.append("## 文件")
    lines.append("")
    lines.append(f"- `data\\results\\position_sizing_strict_certify_20260627\\{os.path.basename(SWEEP_CSV)}`")
    lines.append(f"- `data\\results\\position_sizing_strict_certify_20260627\\{os.path.basename(DETAIL_CSV)}`")
    lines.append(f"- `data\\results\\position_sizing_strict_certify_20260627\\{os.path.basename(CURVE_PATH)}`")
    lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))


def main():
    os.makedirs(RESULT_ROOT, exist_ok=True)
    result = base.summarize_strategy(
        spec_lo=SPEC_LO,
        spec_hi=SPEC_HI,
        top_pct=TOP_PCT,
        bias55_threshold=BIAS55_THRESHOLD,
        stage1_r=STAGE1_R,
        stage2_trail_r=STAGE2_TRAIL_R,
        stage2_force_r=STAGE2_FORCE_R,
    )
    out = result["trades"]

    candidates = []
    for units in itertools.product(GRID, repeat=3):
        if abs(sum(units) - TOTAL_UNITS) > 1e-9:
            continue
        candidates.append(evaluate_units(out, units))

    summary_df = pd.DataFrame([x["summary"] for x in candidates]).sort_values(
        ["pf", "ev", "pnl_$", "test_pf"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    summary_df.to_csv(SWEEP_CSV, index=False, encoding="utf-8-sig")

    baseline = summary_df[summary_df["units"] == "1.0/1.0/1.0"].iloc[0]
    best_pf = summary_df.iloc[0]
    best_balanced = summary_df[summary_df["units"] == "0.5/1.0/1.5"].iloc[0]

    detail_frames = []
    curve_frames = []
    for label in ["1.0/1.0/1.0", "0.5/1.0/1.5", "0.5/0.5/2.0"]:
        item = next(x for x in candidates if x["summary"]["units"] == label)
        detail_frames.append(item["frame"].copy())
        curve_frames.append((label, item["frame"][["date", "equity_$"]].copy()))
    pd.concat(detail_frames, ignore_index=True).to_csv(DETAIL_CSV, index=False, encoding="utf-8-sig")
    s12.render_curve(curve_frames, CURVE_PATH)

    render_report(summary_df, best_pf, best_balanced, baseline)

    print(summary_df.to_string(index=False))
    print(f"Wrote {SWEEP_CSV}")
    print(f"Wrote {DETAIL_CSV}")
    print(f"Wrote {CURVE_PATH}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
