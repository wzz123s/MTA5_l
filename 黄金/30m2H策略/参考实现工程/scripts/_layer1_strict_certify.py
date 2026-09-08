# -*- coding: utf-8 -*-
"""Strict certification for Layer 1 Bias_55 threshold on the current mainline."""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import _stage12_combo_test as s12
import _current_baseline as base


RESULT_ROOT = os.path.join(ROOT, "data", "results", "layer1_strict_certify_20260628")
SWEEP_CSV = os.path.join(RESULT_ROOT, "layer1_strict_sweep.csv")
YEARLY_CSV = os.path.join(RESULT_ROOT, "layer1_strict_yearly.csv")
REMOVED_CSV = os.path.join(RESULT_ROOT, "layer1_3p4_removed_vs_3p0.csv")
CURVE_PATH = os.path.join(RESULT_ROOT, "layer1_strict_equity_curve.png")
REPORT_PATH = os.path.join(ROOT, "30m2H策略", "Layer1严格认证结果.md")

THRESHOLDS = [2.0, 2.5, 3.0, 3.2, 3.4, 3.6, 4.0, 5.0]
COMPARE_THRESHOLDS = [2.5, 3.0, 3.4, 3.6]
SPEC_LO = 5
SPEC_HI = 35
TOP_PCT = 34
STAGE1_R = 2.0
STAGE2_TRAIL_R = 1.5
STAGE2_FORCE_R = 4.0


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def max_drawdown(frame):
    equity = frame["equity_$"].astype(float)
    peak = equity.cummax()
    dd = equity - peak
    worst = float(dd.min())
    worst_pct = float(((dd / peak.replace(0, pd.NA)).fillna(0)).min() * 100.0)
    return worst, worst_pct


def summarize_threshold(threshold):
    result = base.summarize_strategy(
        spec_lo=SPEC_LO,
        spec_hi=SPEC_HI,
        top_pct=TOP_PCT,
        bias55_threshold=threshold,
        stage1_r=STAGE1_R,
        stage2_trail_r=STAGE2_TRAIL_R,
        stage2_force_r=STAGE2_FORCE_R,
    )
    out = result["trades"]
    y2024 = out[out["year"] == 2024]
    y2024_m = s12.metric(y2024["total_points"].values)
    dd_abs, dd_pct = max_drawdown(out)
    return {
        "threshold": threshold,
        "df": result["df"],
        "accepted": result["accepted"],
        "picked": result["picked"],
        "trades": out,
        "summary": {
            "threshold": threshold,
            "accepted_n": len(result["accepted"]),
            "n": result["total"]["n"],
            "wr": result["total"]["wr"],
            "pf": result["total"]["pf"],
            "ev": result["total"]["ev"],
            "pnl_$": float(out["total_$"].sum()),
            "maxcl": result["total"]["ml"],
            "maxdd_$": dd_abs,
            "maxdd_pct": dd_pct,
            "train_n": result["train"]["n"],
            "test_n": result["test"]["n"],
            "test_pf": result["test"]["pf"],
            "test_ev": result["test"]["ev"],
            "y2024_n": y2024_m["n"],
            "y2024_wr": y2024_m["wr"],
            "y2024_pf": y2024_m["pf"],
            "y2024_ev": y2024_m["ev"],
        },
    }


def diff_removed(df, loose_picked, tight_picked):
    tight_keys = set(zip(pd.to_datetime(tight_picked["date"]), tight_picked["dir"], tight_picked["mode"]))
    mask = [
        (pd.Timestamp(d), dr, md) not in tight_keys
        for d, dr, md in zip(pd.to_datetime(loose_picked["date"]), loose_picked["dir"], loose_picked["mode"])
    ]
    removed = loose_picked[mask].copy().reset_index(drop=True)
    out = s12.summarize_variant(df, removed, STAGE1_R, STAGE2_TRAIL_R, STAGE2_FORCE_R)
    out["year"] = pd.to_datetime(out["date"]).dt.year
    out.to_csv(REMOVED_CSV, index=False, encoding="utf-8-sig")
    stats = s12.metric(out["total_points"].values)
    return out, stats


def render_report(summary_df, yearly_df, removed_out, removed_stats):
    rows = []
    for _, row in summary_df.iterrows():
        rows.append([
            f"{row['threshold']:.1f}%",
            int(row["accepted_n"]),
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

    pivot = yearly_df.pivot(index="year", columns="variant", values="trades").fillna(0).astype(int)
    year_rows = []
    for year, row in pivot.iterrows():
        year_rows.append([int(year)] + [int(row[col]) for col in pivot.columns])

    removed_rows = []
    for _, row in removed_out.iterrows():
        removed_rows.append([
            f"{pd.Timestamp(row['date']):%Y-%m-%d %H:%M}",
            row["mode"],
            row["dir"],
            f"{row['total_points']:+.2f}",
            row["stage1_exit"],
            row["stage2_exit"],
            row["stage3_exit"],
        ])

    best_pf = summary_df.sort_values(["pf", "ev", "test_pf"], ascending=[False, False, False]).iloc[0]
    baseline = summary_df[summary_df["threshold"] == 3.0].iloc[0]
    strict34 = summary_df[summary_df["threshold"] == 3.4].iloc[0]

    lines = []
    lines.append("# Layer 1 严格认证结果")
    lines.append("")
    lines.append(
        "> 当前固定主线为：`pre_cross + cross + post_n(2-6)` + `M15 replace_any + rescue` + "
        "`H2 q2 early-gate` + `Layer3 top34%` + `stop spec [5,35] pt`。"
    )
    lines.append("> 本轮只验证 Layer 1 `|Bias_55|` threshold，不再混入 stop / Layer 3 / 退出参数改动。")
    lines.append("")
    lines.append("## 2.0% - 5.0% 细扫")
    lines.append("")
    lines.append(
        md_table(
            ["Threshold", "Accepted", "Trades", "WR", "PF", "EV", "PnL", "MaxCL", "MaxDD", "MaxDD%", "2024", "Test PF", "Test EV"],
            rows,
        )
    )
    lines.append("")
    lines.append("## 分年交易数")
    lines.append("")
    lines.append(md_table(["Year"] + list(pivot.columns), year_rows))
    lines.append("")
    lines.append("## 3.4% 相比 3.0% 被删掉的交易")
    lines.append("")
    lines.append(
        f"- 数量：`{len(removed_out)}`，WR `{removed_stats['wr']:.1f}%`，PF `{removed_stats['pf']:.2f}`，"
        f"EV `{removed_stats['ev']:+.2f}pt`，MaxCL `{removed_stats['ml']}`"
    )
    lines.append(f"- 年份分布：`{removed_out['year'].value_counts().sort_index().to_dict()}`")
    lines.append("")
    lines.append(md_table(["Date", "Mode", "Dir", "Total pt", "Stage1", "Stage2", "Stage3"], removed_rows))
    lines.append("")
    lines.append("## 当前判断")
    lines.append("")
    lines.append(
        f"- 单看 PF / EV 峰值，更严格阈值会继续上升；本轮最高是 `{best_pf['threshold']:.1f}%`，"
        f"PF `{best_pf['pf']:.2f}`，EV `{best_pf['ev']:+.2f}pt`。"
    )
    lines.append(
        f"- 但如果把“保留有效样本 + 保留 2024 恢复能力 + 不让主线风格过窄”一起考虑，`3.0%` 仍是最平衡主线："
        f"`{int(baseline['n'])}` 笔，PF `{baseline['pf']:.2f}`，EV `{baseline['ev']:+.2f}pt`，2024 年 `{int(baseline['y2024_n'])}` 笔。"
    )
    lines.append(
        f"- `3.4%` 虽然把 EV 提到 `{strict34['ev']:+.2f}pt`，PF 提到 `{strict34['pf']:.2f}`，"
        f"但交易数会从 `{int(baseline['n'])}` 缩到 `{int(strict34['n'])}`，而且 2024 会再次变成 `0`。"
    )
    lines.append("- 结论：`Bias_55 threshold` 不是越大越好；当前不建议把主线从 `3.0%` 收紧到 `3.4%`。")
    lines.append("")
    lines.append("## 文件")
    lines.append("")
    lines.append(f"- `data\\results\\layer1_strict_certify_20260628\\{os.path.basename(SWEEP_CSV)}`")
    lines.append(f"- `data\\results\\layer1_strict_certify_20260628\\{os.path.basename(YEARLY_CSV)}`")
    lines.append(f"- `data\\results\\layer1_strict_certify_20260628\\{os.path.basename(REMOVED_CSV)}`")
    lines.append(f"- `data\\results\\layer1_strict_certify_20260628\\{os.path.basename(CURVE_PATH)}`")
    lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))


def main():
    os.makedirs(RESULT_ROOT, exist_ok=True)
    variants = [summarize_threshold(x) for x in THRESHOLDS]
    summary_df = pd.DataFrame([v["summary"] for v in variants]).sort_values("threshold").reset_index(drop=True)
    summary_df.to_csv(SWEEP_CSV, index=False, encoding="utf-8-sig")

    yearly_rows = []
    for v in variants:
        counts = v["trades"].groupby("year").size()
        for year, n in counts.items():
            yearly_rows.append({"variant": f"thr{v['threshold']:.1f}", "year": int(year), "trades": int(n)})
    yearly_df = pd.DataFrame(yearly_rows).sort_values(["year", "variant"]).reset_index(drop=True)
    yearly_df.to_csv(YEARLY_CSV, index=False, encoding="utf-8-sig")

    curve_frames = []
    for threshold in COMPARE_THRESHOLDS:
        item = next(x for x in variants if x["threshold"] == threshold)
        curve_frames.append((f"{threshold:.1f}%", item["trades"]))
    s12.render_curve(curve_frames, CURVE_PATH)

    thr30 = next(x for x in variants if x["threshold"] == 3.0)
    thr34 = next(x for x in variants if x["threshold"] == 3.4)
    removed_out, removed_stats = diff_removed(thr30["df"], thr30["picked"], thr34["picked"])

    render_report(summary_df, yearly_df, removed_out, removed_stats)

    print(summary_df.to_string(index=False))
    print(f"Wrote {SWEEP_CSV}")
    print(f"Wrote {YEARLY_CSV}")
    print(f"Wrote {REMOVED_CSV}")
    print(f"Wrote {CURVE_PATH}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
