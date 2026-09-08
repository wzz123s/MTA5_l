# -*- coding: utf-8 -*-
"""Strict certification for stop-spec lower bound on the current mainline."""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import _stage12_combo_test as s12
import _current_baseline as base


RESULT_ROOT = os.path.join(ROOT, "data", "results", "stop_spec_strict_certify_20260627")
SWEEP_CSV = os.path.join(RESULT_ROOT, "stop_spec_strict_sweep.csv")
YEARLY_CSV = os.path.join(RESULT_ROOT, "stop_spec_strict_yearly.csv")
ADDED_CSV = os.path.join(RESULT_ROOT, "stop_spec_lo4_added_vs_lo5.csv")
REMOVED_CSV = os.path.join(RESULT_ROOT, "stop_spec_lo6_removed_vs_lo5.csv")
CURVE_PATH = os.path.join(RESULT_ROOT, "stop_spec_strict_equity_curve.png")
REPORT_PATH = os.path.join(ROOT, "30m2H策略", "StopSpec严格认证结果.md")

SPEC_HI = 35
TOP_PCT = 34
STAGE1_R = 2.0
STAGE2_TRAIL_R = 1.5
STAGE2_FORCE_R = 4.0
LOWERS = [3, 4, 5, 6, 7, 8]
COMPARE_LOS = [4, 5, 6]


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


def summarize_lower(lo):
    result = base.summarize_strategy(
        spec_lo=lo,
        spec_hi=SPEC_HI,
        top_pct=TOP_PCT,
        stage1_r=STAGE1_R,
        stage2_trail_r=STAGE2_TRAIL_R,
        stage2_force_r=STAGE2_FORCE_R,
    )
    out = result["trades"]
    y2024 = out[out["year"] == 2024]
    y2024_m = s12.metric(y2024["total_points"].values)
    dd_abs, dd_pct = max_drawdown(out)
    return {
        "lo": lo,
        "accepted": result["accepted"],
        "picked": result["picked"],
        "trades": out,
        "summary": {
            "spec_lo": lo,
            "threshold": result["threshold"],
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
            "y2024_pnl_$": float(y2024["total_$"].sum()) if len(y2024) else 0.0,
        },
    }


def frame_keys(frame):
    return set(zip(pd.to_datetime(frame["date"]), frame["dir"], frame["mode"]))


def diff_frames(df, left_picked, right_picked, path, label):
    right_keys = frame_keys(right_picked)
    left_keys = frame_keys(left_picked)
    mask = [
        (pd.Timestamp(d), dr, md) not in right_keys
        for d, dr, md in zip(pd.to_datetime(left_picked["date"]), left_picked["dir"], left_picked["mode"])
    ]
    delta = left_picked[mask].copy().reset_index(drop=True)
    out = s12.summarize_variant(df, delta, STAGE1_R, STAGE2_TRAIL_R, STAGE2_FORCE_R)
    out["year"] = pd.to_datetime(out["date"]).dt.year
    out.to_csv(path, index=False, encoding="utf-8-sig")
    stats = s12.metric(out["total_points"].values)
    year_map = out["year"].value_counts().sort_index().to_dict()
    return {
        "label": label,
        "rows": out,
        "stats": stats,
        "years": year_map,
    }


def render_report(summary_df, yearly_df, lo4_added, lo6_removed):
    sweep_rows = []
    for _, row in summary_df.iterrows():
        sweep_rows.append([
            f"[{int(row['spec_lo'])}, {SPEC_HI}]",
            int(row["accepted_n"]),
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

    def detail_lines(title, info):
        rows = []
        for _, row in info["rows"].iterrows():
            rows.append([
                f"{pd.Timestamp(row['date']):%Y-%m-%d %H:%M}",
                row["mode"],
                row["dir"],
                f"{row['total_points']:+.2f}",
                row["stage1_exit"],
                row["stage2_exit"],
                row["stage3_exit"],
            ])
        lines = []
        lines.append(f"## {title}")
        lines.append("")
        lines.append(
            f"- 数量：`{len(info['rows'])}`，WR `{info['stats']['wr']:.1f}%`，PF `{info['stats']['pf']:.2f}`，"
            f"EV `{info['stats']['ev']:+.2f}pt`，MaxCL `{info['stats']['ml']}`"
        )
        lines.append(f"- 年份分布：`{info['years']}`")
        lines.append("")
        lines.append(md_table(["Date", "Mode", "Dir", "Total pt", "Stage1", "Stage2", "Stage3"], rows))
        lines.append("")
        return lines

    best_pf = summary_df.sort_values(["pf", "ev", "test_pf"], ascending=[False, False, False]).iloc[0]
    baseline = summary_df[summary_df["spec_lo"] == 5].iloc[0]
    lo6 = summary_df[summary_df["spec_lo"] == 6].iloc[0]
    lo4 = summary_df[summary_df["spec_lo"] == 4].iloc[0]

    lines = []
    lines.append("# Stop Spec 严格认证结果")
    lines.append("")
    lines.append(
        "> 当前基线固定为：`Layer1 3.0%` + `pre_cross + cross + post_n(2-6)` + "
        "`M15 replace_any + rescue` + `H2 q2 early-gate` + `Layer3 top34%`。"
    )
    lines.append("> 本轮只验证 stop spec 下限，`spec_hi` 固定为 `35pt`，退出固定为当前主线三段退出。")
    lines.append("")
    lines.append("## [3,35] - [8,35] 细扫")
    lines.append("")
    lines.append(
        md_table(
            ["Spec", "Accepted", "L3 threshold", "Trades", "WR", "PF", "EV", "PnL", "MaxCL", "MaxDD", "MaxDD%", "2024", "Test PF", "Test EV"],
            sweep_rows,
        )
    )
    lines.append("")
    lines.append("## 分年交易数")
    lines.append("")
    lines.append(md_table(["Year"] + list(pivot.columns), year_rows))
    lines.append("")
    lines.extend(detail_lines("[4,35] 相比 [5,35] 新增交易", lo4_added))
    lines.extend(detail_lines("[5,35] 相比 [6,35] 被保留下来的交易", lo6_removed))
    lines.append("## 当前判断")
    lines.append("")
    lines.append(
        f"- 单看 PF 峰值，`[{int(best_pf['spec_lo'])}, {SPEC_HI}]` 最强：PF `{best_pf['pf']:.2f}`，"
        f"EV `{best_pf['ev']:+.2f}pt`，2024 年 `{int(best_pf['y2024_n'])}` 笔。"
    )
    lines.append(
        f"- 若按“恢复 2024 + 不显著牺牲 EV/PF + 不把样本拉得过松”的标准，`[5,35]` 仍是最平衡主线："
        f"`{int(baseline['n'])}` 笔，PF `{baseline['pf']:.2f}`，EV `{baseline['ev']:+.2f}pt`，"
        f"2024 年 `{int(baseline['y2024_n'])}` 笔。"
    )
    lines.append(
        f"- `[4,35]` 会把 2024 交易从 `{int(baseline['y2024_n'])}` 提到 `{int(lo4['y2024_n'])}`，"
        f"但总体 PF 从 `{baseline['pf']:.2f}` 降到 `{lo4['pf']:.2f}`，EV 从 `{baseline['ev']:+.2f}pt` 降到 "
        f"`{lo4['ev']:+.2f}pt`。"
    )
    lines.append(
        f"- `[6,35]` 虽然 EV 升到 `{lo6['ev']:+.2f}pt`，但交易数从 `{int(baseline['n'])}` 掉到 "
        f"`{int(lo6['n'])}`，而且 2024 仍只有 `{int(lo6['y2024_n'])}` 笔；这更像偏保守的备选，不像主线。"
    )
    lines.append("- 结论：当前不建议把 stop 下限从 `5pt` 放宽到 `3pt/4pt`，也不建议收紧到 `6pt+` 作为主线。")
    lines.append("")
    lines.append("## 文件")
    lines.append("")
    lines.append(f"- `data\\results\\stop_spec_strict_certify_20260627\\{os.path.basename(SWEEP_CSV)}`")
    lines.append(f"- `data\\results\\stop_spec_strict_certify_20260627\\{os.path.basename(YEARLY_CSV)}`")
    lines.append(f"- `data\\results\\stop_spec_strict_certify_20260627\\{os.path.basename(ADDED_CSV)}`")
    lines.append(f"- `data\\results\\stop_spec_strict_certify_20260627\\{os.path.basename(REMOVED_CSV)}`")
    lines.append(f"- `data\\results\\stop_spec_strict_certify_20260627\\{os.path.basename(CURVE_PATH)}`")
    lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))


def main():
    os.makedirs(RESULT_ROOT, exist_ok=True)
    variants = [summarize_lower(lo) for lo in LOWERS]
    summary_df = pd.DataFrame([v["summary"] for v in variants]).sort_values("spec_lo").reset_index(drop=True)
    summary_df.to_csv(SWEEP_CSV, index=False, encoding="utf-8-sig")

    yearly_rows = []
    for v in variants:
        counts = v["trades"].groupby("year").size()
        for year, n in counts.items():
            yearly_rows.append({"variant": f"lo{v['lo']}", "year": int(year), "trades": int(n)})
    yearly_df = pd.DataFrame(yearly_rows).sort_values(["year", "variant"]).reset_index(drop=True)
    yearly_df.to_csv(YEARLY_CSV, index=False, encoding="utf-8-sig")

    frames = []
    for lo in COMPARE_LOS:
        v = next(x for x in variants if x["lo"] == lo)
        frames.append((f"lo{lo}", v["trades"]))
    s12.render_curve(frames, CURVE_PATH)

    lo4 = next(x for x in variants if x["lo"] == 4)
    lo5 = next(x for x in variants if x["lo"] == 5)
    lo6 = next(x for x in variants if x["lo"] == 6)
    base_df, _ = base.build_final_accepted(spec_lo=5, spec_hi=SPEC_HI)
    lo4_added = diff_frames(base_df, lo4["picked"], lo5["picked"], ADDED_CSV, "lo4_added")
    lo6_removed = diff_frames(base_df, lo5["picked"], lo6["picked"], REMOVED_CSV, "lo6_removed")

    render_report(summary_df, yearly_df, lo4_added, lo6_removed)

    print(summary_df.to_string(index=False))
    print(f"Wrote {SWEEP_CSV}")
    print(f"Wrote {YEARLY_CSV}")
    print(f"Wrote {ADDED_CSV}")
    print(f"Wrote {REMOVED_CSV}")
    print(f"Wrote {CURVE_PATH}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
