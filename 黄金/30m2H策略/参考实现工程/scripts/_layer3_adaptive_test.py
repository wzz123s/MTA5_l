# -*- coding: utf-8 -*-
"""Compare Layer 3 global threshold vs prior-year adaptive threshold."""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from processing.prepare import prepare
import _stage12_combo_test as s12
import _m15_h2_combo_test as combo
import _m15_early_entry_test as m15t
import _h2_early_gate_test as h2t
from _h2_context import load_h2_context


RESULT_ROOT = os.path.join(ROOT, "data", "results", "layer3_adaptive_20260627")
SUMMARY_CSV = os.path.join(RESULT_ROOT, "layer3_adaptive_summary.csv")
YEARLY_CSV = os.path.join(RESULT_ROOT, "layer3_adaptive_yearly_counts.csv")
THRESHOLD_CSV = os.path.join(RESULT_ROOT, "layer3_adaptive_thresholds.csv")
CURVE_PATH = os.path.join(RESULT_ROOT, "layer3_adaptive_equity_curve.png")
REPORT_PATH = os.path.join(ROOT, "30m2H策略", "Layer3动态阈值测试结果.md")

TOP_PCTS = [30, 35, 40]


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def build_final_accepted():
    df, _ = prepare("base_data/XAUUSDm30.csv", min_len=8)
    h2 = load_h2_context()
    m15 = m15t.load_m15()

    m15t.df_global = df
    h2t.df_global = df

    q2_pass_set, q2_factor_map, _, _ = h2t.early_precompute(h2, df, 2, False)
    raw_df, accepted = combo.build_candidate_frames(df, q2_pass_set, q2_factor_map)

    m15_start = pd.Timestamp(m15["date"].min())
    pre_cov = accepted[pd.to_datetime(accepted["date"]) < m15_start].reset_index(drop=True)
    cov = accepted[pd.to_datetime(accepted["date"]) >= m15_start].reset_index(drop=True)
    cov_mod, _ = m15t.apply_replace_variant(cov, m15, m15t.choose_any, "combo")
    rejected_wide = raw_df[
        (~raw_df["spec_pass"])
        & (raw_df["spec_reason"] == "too_wide")
        & m15t.coverage_mask(raw_df, m15_start)
    ].copy()
    rescued, _ = m15t.build_rescued_trades(rejected_wide, m15, m15t.choose_any)
    cov_merged = m15t.dedupe_anchor(cov_mod.to_dict("records") + rescued.to_dict("records"))
    final_acc = combo.combine_full_sample(pre_cov, cov_merged).sort_values("date").reset_index(drop=True)
    final_acc["year"] = pd.to_datetime(final_acc["date"]).dt.year
    return df, final_acc


def apply_global_top(final_acc, top_pct):
    threshold = float(final_acc["Bias_5"].quantile(1 - top_pct / 100.0))
    picked = final_acc[final_acc["Bias_5"] >= threshold].reset_index(drop=True)
    threshold_rows = [{
        "variant": f"global_top{top_pct}",
        "year": int(year),
        "threshold": threshold,
        "source": "global",
        "source_year": None,
        "source_n": len(final_acc),
    } for year in sorted(final_acc["year"].unique())]
    return picked, threshold_rows


def apply_prior_year_top(final_acc, top_pct):
    years = sorted(final_acc["year"].unique())
    global_threshold = float(final_acc["Bias_5"].quantile(1 - top_pct / 100.0))
    picked_parts = []
    threshold_rows = []

    for year in years:
        cur = final_acc[final_acc["year"] == year].copy()
        prev = final_acc[final_acc["year"] == year - 1].copy()
        if len(prev) > 0:
            threshold = float(prev["Bias_5"].quantile(1 - top_pct / 100.0))
            source = "prior_year"
            source_year = year - 1
            source_n = len(prev)
        else:
            threshold = global_threshold
            source = "global_fallback"
            source_year = None
            source_n = len(final_acc)

        keep = cur[cur["Bias_5"] >= threshold].copy()
        picked_parts.append(keep)
        threshold_rows.append({
            "variant": f"prior_year_top{top_pct}",
            "year": year,
            "threshold": threshold,
            "source": source,
            "source_year": source_year,
            "source_n": source_n,
        })

    picked = pd.concat(picked_parts, ignore_index=True).sort_values("date").reset_index(drop=True)
    return picked, threshold_rows


def summarize_variant(df, picked, variant_name):
    out = s12.summarize_variant(df, picked, 2.0, 1.5, 4.0)
    total_m = s12.metric(out["total_points"].values)
    train_m, test_m = s12.split_metrics(out)
    out["year"] = pd.to_datetime(out["date"]).dt.year
    y2024 = out[out["year"] == 2024]
    y2024_m = s12.metric(y2024["total_points"].values)
    return {
        "name": variant_name,
        "trades": out,
        "summary": {
            "variant": variant_name,
            "n": total_m["n"],
            "wr": total_m["wr"],
            "pf": total_m["pf"],
            "ev": total_m["ev"],
            "pnl_$": float(out["total_$"].sum()),
            "maxcl": total_m["ml"],
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


def render_report(summary_df, yearly_df, threshold_df):
    top_rows = []
    for _, row in summary_df.iterrows():
        top_rows.append([
            row["variant"],
            int(row["n"]),
            f"{row['wr']:.1f}%",
            f"{row['pf']:.2f}",
            f"{row['ev']:+.2f}pt",
            f"${row['pnl_$']:.0f}",
            int(row["maxcl"]),
            int(row["y2024_n"]),
            f"{row['y2024_wr']:.1f}%" if row["y2024_n"] > 0 else "-",
            f"{row['y2024_pf']:.2f}" if row["y2024_n"] > 0 else "-",
            f"{row['y2024_ev']:+.2f}pt" if row["y2024_n"] > 0 else "-",
            f"{row['test_pf']:.2f}",
            f"{row['test_ev']:+.2f}pt",
        ])

    year_rows = []
    pivot = yearly_df.pivot(index="year", columns="variant", values="trades").fillna(0).astype(int)
    for year, row in pivot.iterrows():
        year_rows.append([int(year)] + [int(row[col]) for col in pivot.columns])

    th_rows = []
    th_2024 = threshold_df[threshold_df["year"] == 2024].copy()
    for _, row in th_2024.iterrows():
        src = str(int(row["source_year"])) if pd.notna(row["source_year"]) else "global"
        th_rows.append([
            row["variant"],
            f"{row['threshold']:.6f}",
            row["source"],
            src,
            int(row["source_n"]),
        ])

    lines = []
    lines.append("# Layer 3 动态阈值测试结果")
    lines.append("")
    lines.append("> 当前入口/退出固定为主线版本：`H2 q2 + M15 replace_any_rescue` + `Stage1 2.0R / Stage2 1.5R trail / 4.0R force / Stage3 m30_merged_cross`。")
    lines.append("> 这一轮只比较 Layer 3：全样本固定阈值 vs 前一年分位阈值。")
    lines.append("")
    lines.append("## 对照结果")
    lines.append("")
    lines.append(md_table(
        ["Variant", "Trades", "WR", "PF", "EV", "PnL", "MaxCL", "2024", "2024 WR", "2024 PF", "2024 EV", "Test PF", "Test EV"],
        top_rows,
    ))
    lines.append("")
    lines.append("## 分年交易数")
    lines.append("")
    lines.append(md_table(["Year"] + list(pivot.columns), year_rows))
    lines.append("")
    lines.append("## 2024 年阈值来源")
    lines.append("")
    lines.append(md_table(["Variant", "Threshold", "Source", "Source Year", "Source N"], th_rows))
    lines.append("")

    best_pf = summary_df.iloc[0]
    lines.append("## 当前判断")
    lines.append("")
    lines.append(f"- 当前扫描里，PF 最高的是 `{best_pf['variant']}`：{int(best_pf['n'])} 笔，PF {best_pf['pf']:.2f}，EV {best_pf['ev']:+.2f}pt，2024 年 {int(best_pf['y2024_n'])} 笔。")
    lines.append("- `global_top35` 的特点是简单、稳定，而且已经能把 2024 年带回 6 笔。")
    lines.append("- `prior_year_top30/35/40` 的特点是会顺着年度分布自适应；如果前一年 `Bias_5` 偏弱，下一年门槛会自动放松。")
    lines.append("- 需要额外注意：前一年法对样本很少的早期年份更敏感，后续若采用，最好再加 `source_n` 下限或 warm-up 规则。")
    lines.append("")
    lines.append("## 文件")
    lines.append("")
    lines.append(f"- `data\\results\\layer3_adaptive_20260627\\{os.path.basename(SUMMARY_CSV)}`")
    lines.append(f"- `data\\results\\layer3_adaptive_20260627\\{os.path.basename(YEARLY_CSV)}`")
    lines.append(f"- `data\\results\\layer3_adaptive_20260627\\{os.path.basename(THRESHOLD_CSV)}`")
    lines.append(f"- `data\\results\\layer3_adaptive_20260627\\{os.path.basename(CURVE_PATH)}`")
    lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    os.makedirs(RESULT_ROOT, exist_ok=True)
    df, final_acc = build_final_accepted()

    variants = []
    threshold_rows = []

    for top_pct in TOP_PCTS:
        picked, rows = apply_global_top(final_acc, top_pct)
        variants.append(summarize_variant(df, picked, f"global_top{top_pct}"))
        threshold_rows.extend(rows)

    for top_pct in TOP_PCTS:
        picked, rows = apply_prior_year_top(final_acc, top_pct)
        variants.append(summarize_variant(df, picked, f"prior_year_top{top_pct}"))
        threshold_rows.extend(rows)

    summary_df = pd.DataFrame([v["summary"] for v in variants]).sort_values(
        ["pf", "ev", "pnl_$", "y2024_n"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    summary_df.to_csv(SUMMARY_CSV, index=False, encoding="utf-8-sig")

    yearly_rows = []
    for v in variants:
        frame = v["trades"].copy()
        counts = frame.groupby("year").size()
        for year, n in counts.items():
            yearly_rows.append({"variant": v["summary"]["variant"], "year": int(year), "trades": int(n)})
    yearly_df = pd.DataFrame(yearly_rows).sort_values(["year", "variant"]).reset_index(drop=True)
    yearly_df.to_csv(YEARLY_CSV, index=False, encoding="utf-8-sig")

    threshold_df = pd.DataFrame(threshold_rows).sort_values(["variant", "year"]).reset_index(drop=True)
    threshold_df.to_csv(THRESHOLD_CSV, index=False, encoding="utf-8-sig")

    # Compare baseline with the strongest global and adaptive variants.
    best_global = summary_df[summary_df["variant"].str.startswith("global_")].iloc[0]["variant"]
    best_adapt = summary_df[summary_df["variant"].str.startswith("prior_year_")].iloc[0]["variant"]
    curve_frames = []
    for name in ["global_top30", best_global, best_adapt]:
        frame = next(v["trades"] for v in variants if v["summary"]["variant"] == name)
        label = name
        curve_frames.append((label, frame))
    s12.render_curve(curve_frames, CURVE_PATH)

    render_report(summary_df, yearly_df, threshold_df)

    print(summary_df.to_string(index=False))
    print(f"Wrote {SUMMARY_CSV}")
    print(f"Wrote {YEARLY_CSV}")
    print(f"Wrote {THRESHOLD_CSV}")
    print(f"Wrote {CURVE_PATH}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
