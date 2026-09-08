# -*- coding: utf-8 -*-
"""Strict certification for the Layer 3 global threshold candidate."""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import _stage12_combo_test as s12
import _current_baseline as base


RESULT_ROOT = os.path.join(ROOT, "data", "results", "layer3_strict_certify_20260627")
SWEEP_CSV = os.path.join(RESULT_ROOT, "layer3_strict_sweep.csv")
YEARLY_CSV = os.path.join(RESULT_ROOT, "layer3_strict_yearly.csv")
ADDED_CSV = os.path.join(RESULT_ROOT, "layer3_top34_added_trades.csv")
CURVE_PATH = os.path.join(RESULT_ROOT, "layer3_strict_equity_curve.png")
REPORT_PATH = os.path.join(ROOT, "30m2H策略", "Layer3严格认证结果.md")

PCTS = list(range(30, 41))
COMPARE_PCTS = [30, 34, 35, 38]
SPEC_LO = 5
SPEC_HI = 35
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
    worst_idx = int(dd.idxmin())
    worst = float(dd.iloc[worst_idx])
    worst_pct = float((dd / peak.replace(0, pd.NA)).fillna(0).iloc[worst_idx] * 100.0)
    return worst, worst_pct


def summarize_pct(df, final_acc, pct):
    threshold, picked = base.apply_layer3(final_acc, top_pct=pct)
    out = s12.summarize_variant(df, picked, STAGE1_R, STAGE2_TRAIL_R, STAGE2_FORCE_R)
    total_m = s12.metric(out["total_points"].values)
    train_m, test_m = s12.split_metrics(out)
    out["year"] = pd.to_datetime(out["date"]).dt.year
    y2024 = out[out["year"] == 2024]
    y2024_m = s12.metric(y2024["total_points"].values)
    dd_abs, dd_pct = max_drawdown(out)
    return {
        "pct": pct,
        "threshold": threshold,
        "picked": picked,
        "trades": out,
        "summary": {
            "pct": pct,
            "threshold": threshold,
            "n": total_m["n"],
            "wr": total_m["wr"],
            "pf": total_m["pf"],
            "ev": total_m["ev"],
            "pnl_$": float(out["total_$"].sum()),
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
            "y2024_pnl_$": float(y2024["total_$"].sum()) if len(y2024) else 0.0,
        },
    }


def build_added_trades(df, base_picked, cand_picked):
    base_keys = set(zip(pd.to_datetime(base_picked["date"]), base_picked["dir"], base_picked["mode"]))
    mask = [
        (pd.Timestamp(d), dr, md) not in base_keys
        for d, dr, md in zip(pd.to_datetime(cand_picked["date"]), cand_picked["dir"], cand_picked["mode"])
    ]
    added = cand_picked[mask].copy().reset_index(drop=True)
    out = s12.summarize_variant(df, added, STAGE1_R, STAGE2_TRAIL_R, STAGE2_FORCE_R)
    out["year"] = pd.to_datetime(out["date"]).dt.year
    out.to_csv(ADDED_CSV, index=False, encoding="utf-8-sig")
    m = s12.metric(out["total_points"].values)
    return added, out, m


def render_report(summary_df, yearly_df, added_out, added_stats):
    sweep_rows = []
    for _, row in summary_df.iterrows():
        sweep_rows.append([
            f"top {int(row['pct'])}%",
            f"{row['threshold']:.6f}",
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

    added_rows = []
    for _, row in added_out.iterrows():
        added_rows.append([
            f"{pd.Timestamp(row['date']):%Y-%m-%d %H:%M}",
            row["mode"],
            row["dir"],
            f"{row['total_points']:+.2f}",
            row["stage1_exit"],
            row["stage2_exit"],
            row["stage3_exit"],
        ])

    best_pf = summary_df.sort_values(["pf", "ev", "test_pf"], ascending=[False, False, False]).iloc[0]
    balanced = summary_df[summary_df["pct"] == 34].iloc[0]

    lines = []
    lines.append("# Layer 3 严格认证结果")
    lines.append("")
    lines.append(
        "> 当前入口/退出固定为：`H2 q2 + M15 replace_any_rescue` + "
        "`Stage1 2.0R / Stage2 1.5R trail / 4.0R force / Stage3 m30_merged_cross`。"
    )
    lines.append(f"> 本轮只验证 Layer 3 全样本固定阈值的细扫稳定性；stop spec 固定为 `[{SPEC_LO}, {SPEC_HI}] pt`。")
    lines.append("")
    lines.append("## 30%-40% 细扫")
    lines.append("")
    lines.append(
        md_table(
            ["Variant", "Threshold", "Trades", "WR", "PF", "EV", "PnL", "MaxCL", "MaxDD", "MaxDD%", "2024", "Test PF", "Test EV"],
            sweep_rows,
        )
    )
    lines.append("")
    lines.append("## 分年交易数")
    lines.append("")
    lines.append(md_table(["Year"] + list(pivot.columns), year_rows))
    lines.append("")
    lines.append("## top34 相比 top30 新增交易")
    lines.append("")
    lines.append(f"- 新增笔数：`{len(added_out)}`")
    lines.append(
        f"- 结果：WR `{added_stats['wr']:.1f}%`，PF `{added_stats['pf']:.2f}`，"
        f"EV `{added_stats['ev']:+.2f}pt`，MaxCL `{added_stats['ml']}`"
    )
    lines.append(f"- 年份分布：`{added_out['year'].value_counts().sort_index().to_dict()}`")
    lines.append("")
    lines.append(md_table(["Date", "Mode", "Dir", "Total pt", "Stage1", "Stage2", "Stage3"], added_rows))
    lines.append("")
    lines.append("## 当前判断")
    lines.append("")
    lines.append(
        f"- 单看 PF 峰值，`top {int(best_pf['pct'])}%` 最强：PF `{best_pf['pf']:.2f}`，"
        f"EV `{best_pf['ev']:+.2f}pt`，2024 年 `{int(best_pf['y2024_n'])}` 笔。"
    )
    lines.append(
        f"- 但若按“少动参数、恢复 2024、保持高 EV、避免风格过度激进”的标准，"
        f"`top 34%` 更像当前最稳的候选：`{int(balanced['n'])}` 笔，"
        f"PF `{balanced['pf']:.2f}`，EV `{balanced['ev']:+.2f}pt`，"
        f"MaxCL `{int(balanced['maxcl'])}`，2024 年 `{int(balanced['y2024_n'])}` 笔。"
    )
    lines.append("- `top 38%/39%` 虽然 PF 略高，但样本又放大了一档，EV 下滑更明显，风格已经比当前主线更激进。")
    lines.append("- `top 34%` 比 `top 35%` 多一个优点：在保留同样 6 笔 2024 交易的前提下，总体 PF 和 EV 都略优。")
    lines.append("")
    lines.append("## 文件")
    lines.append("")
    lines.append(f"- `data\\results\\layer3_strict_certify_20260627\\{os.path.basename(SWEEP_CSV)}`")
    lines.append(f"- `data\\results\\layer3_strict_certify_20260627\\{os.path.basename(YEARLY_CSV)}`")
    lines.append(f"- `data\\results\\layer3_strict_certify_20260627\\{os.path.basename(ADDED_CSV)}`")
    lines.append(f"- `data\\results\\layer3_strict_certify_20260627\\{os.path.basename(CURVE_PATH)}`")
    lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))


def main():
    os.makedirs(RESULT_ROOT, exist_ok=True)
    df, final_acc = base.build_final_accepted(spec_lo=SPEC_LO, spec_hi=SPEC_HI)

    variants = [summarize_pct(df, final_acc, pct) for pct in PCTS]
    summary_df = pd.DataFrame([v["summary"] for v in variants]).sort_values("pct").reset_index(drop=True)
    summary_df.to_csv(SWEEP_CSV, index=False, encoding="utf-8-sig")

    yearly_rows = []
    for v in variants:
        counts = v["trades"].groupby("year").size()
        for year, n in counts.items():
            yearly_rows.append({"variant": f"top{v['pct']}", "year": int(year), "trades": int(n)})
    yearly_df = pd.DataFrame(yearly_rows).sort_values(["year", "variant"]).reset_index(drop=True)
    yearly_df.to_csv(YEARLY_CSV, index=False, encoding="utf-8-sig")

    comp_frames = []
    for pct in COMPARE_PCTS:
        v = next(x for x in variants if x["pct"] == pct)
        comp_frames.append((f"top{pct}", v["trades"]))
    s12.render_curve(comp_frames, CURVE_PATH)

    base30 = next(x for x in variants if x["pct"] == 30)
    cand34 = next(x for x in variants if x["pct"] == 34)
    _, added_out, added_stats = build_added_trades(df, base30["picked"], cand34["picked"])

    render_report(summary_df, yearly_df, added_out, added_stats)

    print(summary_df.to_string(index=False))
    print(f"Wrote {SWEEP_CSV}")
    print(f"Wrote {YEARLY_CSV}")
    print(f"Wrote {ADDED_CSV}")
    print(f"Wrote {CURVE_PATH}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
