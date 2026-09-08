# -*- coding: utf-8 -*-
"""Test combined M15 early-entry and H2 early-gate variants on full strategy results."""
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from processing.prepare import prepare
import _pre_cross_range_test as pct
import _m15_early_entry_test as m15t
import _h2_early_gate_test as h2t
from _h2_context import load_h2_context


RESULT_ROOT = os.path.join(ROOT, "data", "results", "m15_h2_early_trigger_20260626")
REPORT_PATH = os.path.join(ROOT, "30m2H策略", "M15_H2提前触发测试结果.md")
DETAIL_PATH = os.path.join(RESULT_ROOT, "m15_h2_combo_detail.csv")
SPLIT_DATE = pd.Timestamp("2023-01-01")


def stats(tdf):
    out = pct.stats(tdf)
    if len(tdf) == 0:
        out["avg_sd"] = 0.0
        out["median_sd"] = 0.0
        return out
    out["avg_sd"] = float(tdf["sd"].mean())
    out["median_sd"] = float(tdf["sd"].median())
    return out


def stat_cells(s):
    return [
        s["n"],
        f"{s['wr']:.1f}%",
        f"{s['pf']:.2f}",
        f"{s['ev']:+.2f}pt",
        f"${s['pnl']:.0f}",
        s["ml"],
        f"{s['avg_sd']:.2f}",
        f"{s['median_sd']:.2f}",
    ]


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def trade_keys(tdf):
    if len(tdf) == 0:
        return set()
    return set(zip(pd.to_datetime(tdf["date"]), tdf["dir"]))


def subset_by_keys(tdf, keys):
    if len(tdf) == 0 or not keys:
        return tdf.iloc[0:0].copy()
    mask = [(pd.Timestamp(d), dr) in keys for d, dr in zip(pd.to_datetime(tdf["date"]), tdf["dir"])]
    return tdf[np.asarray(mask)].reset_index(drop=True)


def split_stats(tdf):
    train = tdf[pd.to_datetime(tdf["entry_time"]) < SPLIT_DATE]
    test = tdf[pd.to_datetime(tdf["entry_time"]) >= SPLIT_DATE]
    return stats(train), stats(test)


def build_candidate_frames(df, pass_set, factor_map, ea_mode=False):
    raw = (
        m15t.collect_pre_cross_candidates(df, pass_set, factor_map)
        + m15t.collect_cross_candidates(df, pass_set, factor_map, ea_mode=ea_mode)
        + m15t.collect_post_candidates(df, pass_set, factor_map)
    )
    raw_df = pd.DataFrame(raw)
    accepted = m15t.dedupe_anchor([r for r in raw if r["spec_pass"]])
    return raw_df, accepted


def combine_full_sample(pre_cov, cov_frame):
    parts = []
    if len(pre_cov) > 0:
        parts.append(pre_cov.copy())
    if len(cov_frame) > 0:
        parts.append(cov_frame.copy())
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True).sort_values(["date", "dir"]).reset_index(drop=True)


def run_variant(df, m15, pass_set, factor_map, variant_name, mode):
    raw_df, accepted = build_candidate_frames(df, pass_set, factor_map)
    m15_start = pd.Timestamp(m15["date"].min())
    pre_cov = accepted[pd.to_datetime(accepted["date"]) < m15_start].reset_index(drop=True)
    cov = accepted[pd.to_datetime(accepted["date"]) >= m15_start].reset_index(drop=True)

    changed = 0
    rescued_count = 0
    note_parts = []

    if mode == "base":
        final_accepted = accepted
        note_parts.append("no M15 adjustment")
    elif mode == "replace_any":
        cov_mod, changed = m15t.apply_replace_variant(cov, m15, m15t.choose_any, variant_name)
        final_accepted = combine_full_sample(pre_cov, cov_mod)
        note_parts.append(f"replace changed {changed}")
    elif mode == "replace_any_plus_rescue":
        cov_mod, changed = m15t.apply_replace_variant(cov, m15, m15t.choose_any, variant_name)
        rejected_wide = raw_df[
            (~raw_df["spec_pass"])
            & (raw_df["spec_reason"] == "too_wide")
            & m15t.coverage_mask(raw_df, m15_start)
        ].copy()
        rescued, rescued_count = m15t.build_rescued_trades(rejected_wide, m15, m15t.choose_any)
        cov_merged = m15t.dedupe_anchor(cov_mod.to_dict("records") + rescued.to_dict("records"))
        final_accepted = combine_full_sample(pre_cov, cov_merged)
        note_parts.append(f"replace changed {changed}")
        note_parts.append(f"rescued {rescued_count}")
    else:
        raise ValueError(f"Unknown mode: {mode}")

    top = pct.layer3_top(final_accepted).sort_values("date").reset_index(drop=True)
    return {
        "name": variant_name,
        "raw": raw_df,
        "accepted": accepted,
        "top": top,
        "coverage_start": m15_start,
        "changed": changed,
        "rescued_count": rescued_count,
        "note": ", ".join(note_parts),
    }


def make_variant_rows(items, baseline_top):
    rows = []
    delta_rows = []
    base_keys = trade_keys(baseline_top)
    for item in items:
        top = item["top"]
        s = stats(top)
        train_s, test_s = split_stats(top)
        top_keys = trade_keys(top)
        added = subset_by_keys(top, top_keys - base_keys)
        removed = subset_by_keys(baseline_top, base_keys - top_keys)
        added_modes = "-"
        if len(added) > 0:
            counts = added["mode"].value_counts().to_dict()
            added_modes = ", ".join(f"{k}:{v}" for k, v in counts.items())

        rows.append([
            item["name"],
            len(added),
            len(removed),
            *stat_cells(s),
            train_s["n"],
            test_s["n"],
            f"{test_s['pf']:.2f}",
            f"{test_s['ev']:+.2f}pt",
            item["note"],
        ])

        add_s = stats(added)
        delta_rows.append([
            item["name"],
            add_s["n"],
            f"{add_s['wr']:.1f}%",
            f"{add_s['pf']:.2f}",
            f"{add_s['ev']:+.2f}pt",
            f"${add_s['pnl']:.0f}",
            add_s["ml"],
            added_modes,
        ])
    return rows, delta_rows


def combo_section(rows, delta_rows, coverage_start):
    lines = []
    lines.append("## 第三轮：M15 + H2 组合测试")
    lines.append("")
    lines.append(f"> 组合测试中的 M15 部分从 `{coverage_start:%Y-%m-%d %H:%M}` 开始生效；更早时段保持原主策略口径。")
    lines.append("")
    lines.append("这一轮把 M15 early-entry 和 H2 early-gate 放回同一套策略里一起看，重点判断两者叠加后，是继续增益，还是互相稀释。")
    lines.append("")
    lines.append(md_table(
        ["方案", "added_trades", "removed_trades", "笔数", "WR", "PF", "EV", "PnL", "MaxCL", "avg_sd", "median_sd", "训练笔数", "验证笔数", "验证PF", "验证EV", "备注"],
        rows,
    ))
    lines.append("")
    lines.append("## 组合新增交易分析")
    lines.append("")
    lines.append(md_table(
        ["方案", "新增笔数", "新增WR", "新增PF", "新增EV", "新增PnL", "新增MaxCL", "mode split"],
        delta_rows,
    ))
    lines.append("")
    lines.append("## 当前判断")
    lines.append("")
    lines.append("- 先看 `H2 only` 是否带来稳定增量，再看 `M15 only` 是否继续改善 stop distance 与最终收益。")
    lines.append("- 如果组合版比单独 `H2 only` 与单独 `M15 only` 都更强，说明两条提前触发思路是互补的。")
    lines.append("- 如果组合版笔数变多但 PF/EV 明显掉，说明新增信号质量不足，后面就要回到更严格的 rescue 或 mode 限制。")
    lines.append("")
    lines.append("## 结果文件")
    lines.append("")
    lines.append(f"- `data\\results\\m15_h2_early_trigger_20260626\\{os.path.basename(DETAIL_PATH)}`")
    lines.append("")
    return "\n".join(lines)


def main():
    df, _ = prepare("base_data/XAUUSDm30.csv", min_len=8)
    h2 = load_h2_context()
    m15 = m15t.load_m15()

    m15t.df_global = df
    h2t.df_global = df

    base_pass_set, base_factor_map = pct.precompute_h2(h2, df["date"].values)
    q2_pass_set, q2_factor_map, _, _ = h2t.early_precompute(h2, df, 2, False)

    variants = [
        run_variant(df, m15, base_pass_set, base_factor_map, "baseline_full", "base"),
        run_variant(df, m15, q2_pass_set, q2_factor_map, "h2_l1_q2_only", "base"),
        run_variant(df, m15, base_pass_set, base_factor_map, "m15_replace_any_only", "replace_any"),
        run_variant(df, m15, base_pass_set, base_factor_map, "m15_replace_any_plus_rescue_only", "replace_any_plus_rescue"),
        run_variant(df, m15, q2_pass_set, q2_factor_map, "combo_h2_q2_plus_replace_any", "replace_any"),
        run_variant(df, m15, q2_pass_set, q2_factor_map, "combo_h2_q2_plus_replace_any_rescue", "replace_any_plus_rescue"),
    ]

    os.makedirs(RESULT_ROOT, exist_ok=True)
    detail_frames = []
    for item in variants:
        if len(item["top"]) == 0:
            continue
        tmp = item["top"].copy()
        tmp["report_variant"] = item["name"]
        detail_frames.append(tmp)
    if detail_frames:
        pd.concat(detail_frames, ignore_index=True).to_csv(DETAIL_PATH, index=False, encoding="utf-8-sig")

    rows, delta_rows = make_variant_rows(variants, variants[0]["top"])
    section = combo_section(rows, delta_rows, variants[0]["coverage_start"])

    if os.path.exists(REPORT_PATH):
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            existing = f.read().rstrip()
        marker = "\n## 第三轮：M15 + H2 组合测试"
        if marker in existing:
            existing = existing.split(marker)[0].rstrip()
        content = existing + "\n\n" + section + "\n"
    else:
        content = "# M15 / H2 提前触发测试结果\n\n" + section + "\n"

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(md_table(
        ["方案", "added_trades", "removed_trades", "笔数", "WR", "PF", "EV", "PnL", "MaxCL", "avg_sd", "median_sd", "训练笔数", "验证笔数", "验证PF", "验证EV", "备注"],
        rows,
    ))
    print()
    print(md_table(
        ["方案", "新增笔数", "新增WR", "新增PF", "新增EV", "新增PnL", "新增MaxCL", "mode split"],
        delta_rows,
    ))
    print()
    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {DETAIL_PATH}")


if __name__ == "__main__":
    main()
