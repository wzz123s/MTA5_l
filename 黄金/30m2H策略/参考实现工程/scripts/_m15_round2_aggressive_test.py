# -*- coding: utf-8 -*-
"""Test a more aggressive second-round M15 additive trigger on the current mainline."""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import _current_baseline as base
import _h2_early_gate_test as h2t
import _m15_early_entry_test as m15t
import _m15_h2_combo_test as combo
import _pre_cross_range_test as pct
import _stage12_combo_test as s12


RESULT_ROOT = os.path.join(ROOT, "data", "results", "m15_round2_aggressive_20260628")
SUMMARY_CSV = os.path.join(RESULT_ROOT, "m15_round2_aggressive_summary.csv")
TRADE_CSV = os.path.join(RESULT_ROOT, "m15_round2_aggressive_trades.csv")
ADDED_CSV = os.path.join(RESULT_ROOT, "m15_round2_aggressive_added_only.csv")
CURVE_PATH = os.path.join(RESULT_ROOT, "m15_round2_aggressive_curve.png")
REPORT_PATH = os.path.join(ROOT, "30m2H策略", "M15第二轮激进测试结果.md")

DIR_COL = "方向"
DIR_MERGED_COL = "方向_合并后"
TOP_PCT = 34
STAGE1_R = 2.0
STAGE2_TRAIL_R = 1.5
STAGE2_FORCE_R = 4.0
GAP_VALUES = [0.001, 0.002, 0.003, 0.004, 0.005]


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


def trade_keys(tdf):
    if len(tdf) == 0:
        return set()
    anchor_col = "anchor_i" if "anchor_i" in tdf.columns else "i"
    return set(zip(tdf[anchor_col].astype(int), tdf["dir"]))


def subset_by_keys(tdf, keys):
    if len(tdf) == 0 or not keys:
        return tdf.iloc[0:0].copy()
    anchor_col = "anchor_i" if "anchor_i" in tdf.columns else "i"
    mask = [(int(i), dr) in keys for i, dr in zip(tdf[anchor_col], tdf["dir"])]
    return tdf[np.asarray(mask)].reset_index(drop=True)


def dedupe_added(tdf):
    if len(tdf) == 0:
        return tdf.copy()
    out = tdf.sort_values(["anchor_i", "dir", "entry_time", "sd"]).drop_duplicates(
        subset=["anchor_i", "dir"],
        keep="first",
    )
    return out.reset_index(drop=True)


def build_current_final_acc(df, h2, m15):
    q2_pass_set, q2_factor_map, _, _ = h2t.early_precompute(h2, df, 2, False)
    raw_df, accepted = combo.build_candidate_frames(df, q2_pass_set, q2_factor_map)
    m15_start = pd.Timestamp(m15["date"].min())

    pre_cov = accepted[pd.to_datetime(accepted["date"]) < m15_start].reset_index(drop=True)
    cov = accepted[pd.to_datetime(accepted["date"]) >= m15_start].reset_index(drop=True)
    cov_mod, changed = m15t.apply_replace_variant(cov, m15, m15t.choose_any, "combo_replace_any")

    rejected_wide = raw_df[
        (~raw_df["spec_pass"])
        & (raw_df["spec_reason"] == "too_wide")
        & m15t.coverage_mask(raw_df, m15_start)
    ].copy()
    rescued, rescue_count = m15t.build_rescued_trades(rejected_wide, m15, m15t.choose_any)
    cov_merged = m15t.dedupe_anchor(cov_mod.to_dict("records") + rescued.to_dict("records"))
    final_acc = combo.combine_full_sample(pre_cov, cov_merged).sort_values("date").reset_index(drop=True)
    final_acc["year"] = pd.to_datetime(final_acc["date"]).dt.year
    return {
        "pass_set": q2_pass_set,
        "factor_map": q2_factor_map,
        "raw_df": raw_df,
        "accepted": accepted,
        "final_acc": final_acc,
        "m15_start": m15_start,
        "replace_changed": changed,
        "rescue_count": rescue_count,
    }


def choose_pre_cross(window, m15, gap_thr):
    for idx, row in window.iterrows():
        if idx <= 0:
            continue
        prev = m15.iloc[idx - 1]
        if any(pd.isna(x) for x in (prev["close"], prev["SMA_13"], row["close"], row["SMA_5"], row["SMA_13"])):
            continue
        if row["SMA_13"] == 0:
            continue
        gap = abs(row["SMA_5"] - row["SMA_13"]) / row["SMA_13"]
        if gap > gap_thr:
            continue
        long_setup = prev["close"] <= prev["SMA_13"] and row["close"] > row["SMA_13"] and row["SMA_5"] < row["SMA_13"]
        short_setup = prev["close"] >= prev["SMA_13"] and row["close"] < row["SMA_13"] and row["SMA_5"] > row["SMA_13"]
        if long_setup:
            return row, True, {"m15_gap": gap}
        if short_setup:
            return row, False, {"m15_gap": gap}
    return None


def choose_close_side(window):
    for _, row in window.iterrows():
        if pd.isna(row["SMA_13"]):
            continue
        if row["close"] > row["SMA_13"]:
            return row, True, {"m15_gap": np.nan}
        if row["close"] < row["SMA_13"]:
            return row, False, {"m15_gap": np.nan}
    return None


def build_added_candidates(df, m15, pass_set, factor_map, raw_keys, variant, gap_thr=None):
    direction = df[DIR_COL].values
    direction_merged = df[DIR_MERGED_COL].values
    sma13 = df["SMA_13"].values
    rows = []
    m15_start = pd.Timestamp(m15["date"].min())

    for i in range(1, len(df) - 1):
        anchor_time = pd.Timestamp(df.iloc[i]["date"])
        if i not in pass_set or anchor_time < m15_start:
            continue

        start = anchor_time - pd.Timedelta(minutes=30)
        window = m15[(m15["date"] > start) & (m15["date"] <= anchor_time)].sort_values("date")
        if len(window) == 0:
            continue

        if variant == "m15_add_pre_cross":
            chosen = choose_pre_cross(window, m15, gap_thr)
        elif variant == "m15_add_close_side":
            chosen = choose_close_side(window)
        else:
            raise ValueError(f"Unknown variant: {variant}")

        if chosen is None:
            continue

        row, is_long, extra = chosen
        dir_char = "L" if is_long else "S"
        if (i, dir_char) in raw_keys:
            continue

        stop = pct.prior_segment_stop(i, is_long, direction, sma13)
        if pd.isna(stop):
            continue

        entry = float(row["close"])
        if is_long and stop >= entry:
            continue
        if (not is_long) and stop <= entry:
            continue

        sd = abs(entry - stop)
        if sd < pct.SPEC_LO or sd > pct.SPEC_HI:
            continue

        opp = "bad" if is_long else "good"
        j = i + 1
        while j < len(df) and direction_merged[j] != opp:
            j += 1
        if j >= len(df):
            continue

        trade = {
            "anchor_i": i,
            "i": i,
            "date": anchor_time,
            "entry_time": pd.Timestamp(row["date"]),
            "mode": variant,
            "dir": dir_char,
            "entry": entry,
            "stop": float(stop),
            "sd": sd,
            "exit_i": j,
            "won": False,
            "pnl": np.nan,
            "variant": variant,
            "lead_min": (anchor_time - pd.Timestamp(row["date"])).total_seconds() / 60.0,
        }
        if i in factor_map:
            trade.update(factor_map[i])
        trade.update(extra)
        trade = m15t.finalize_trade(df, trade, m15)
        rows.append(trade)

    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out["year"] = pd.to_datetime(out["date"]).dt.year
    return dedupe_added(out)


def summarize_variant(df, final_acc, base_picked, base_keys_after_l3, name, added_only):
    threshold = float(final_acc["Bias_5"].quantile(1 - TOP_PCT / 100.0))
    picked = final_acc[final_acc["Bias_5"] >= threshold].sort_values("date").reset_index(drop=True)
    out = s12.summarize_variant(df, picked, STAGE1_R, STAGE2_TRAIL_R, STAGE2_FORCE_R)
    total_m = s12.metric(out["total_points"].values)
    train_m, test_m = s12.split_metrics(out)
    dd_abs, dd_pct = max_drawdown(out["equity_$"])

    picked_keys = trade_keys(picked)
    source_keys = trade_keys(added_only)
    source_picked = subset_by_keys(added_only, picked_keys & source_keys)
    source_picked_stats = pct.stats(source_picked) if len(source_picked) else pct.stats(added_only.iloc[0:0].copy())
    final_increment = subset_by_keys(picked, picked_keys - base_keys_after_l3)
    final_increment_stats = pct.stats(final_increment) if len(final_increment) else pct.stats(picked.iloc[0:0].copy())

    added_only = added_only.sort_values("date").reset_index(drop=True)
    added_only_stats = pct.stats(added_only) if len(added_only) else pct.stats(added_only)
    modes = "-"
    if len(source_picked) > 0:
        mode_counts = source_picked["mode"].value_counts().to_dict()
        modes = ", ".join(f"{k}:{v}" for k, v in mode_counts.items())

    return {
        "name": name,
        "threshold": threshold,
        "picked": picked,
        "trades": out,
        "total": total_m,
        "train": train_m,
        "test": test_m,
        "maxdd_$": dd_abs,
        "maxdd_pct": dd_pct,
        "accepted_n": len(final_acc),
        "picked_n": len(picked),
        "added_accept_n": len(added_only),
        "added_source_pick_n": len(source_picked),
        "final_increment_n": len(final_increment),
        "added_accept_stats": added_only_stats,
        "added_source_pick_stats": source_picked_stats,
        "final_increment_stats": final_increment_stats,
        "added_pick_modes": modes,
    }


def render_report(rows):
    headers = [
        "方案",
        "accepted",
        "picked",
        "added_accept",
        "source_pick",
        "final_plus",
        "WR",
        "PF",
        "EV",
        "PnL",
        "MaxCL",
        "MaxDD",
        "MaxDD%",
        "Test PF",
        "Test EV",
    ]
    table_rows = []
    delta_rows = []
    for item in rows:
        total = item["total"]
        table_rows.append([
            item["name"],
            item["accepted_n"],
            item["picked_n"],
            item["added_accept_n"],
            item["added_source_pick_n"],
            item["final_increment_n"],
            f"{total['wr']:.1f}%",
            f"{total['pf']:.2f}",
            f"{total['ev']:+.2f}pt",
            f"${item['trades']['total_$'].sum():.0f}",
            total["ml"],
            f"${item['maxdd_$']:.0f}",
            f"{item['maxdd_pct']:+.2f}%",
            f"{item['test']['pf']:.2f}",
            f"{item['test']['ev']:+.2f}pt",
        ])

        add_s = item["added_source_pick_stats"]
        delta_rows.append([
            item["name"],
            item["added_source_pick_n"],
            f"{add_s['wr']:.1f}%",
            f"{add_s['pf']:.2f}",
            f"{add_s['ev']:+.2f}pt",
            f"${add_s['pnl']:.0f}",
            add_s["ml"],
            item["added_pick_modes"],
        ])

    lines = []
    lines.append("# M15 第二轮激进测试结果")
    lines.append("")
    lines.append("> 固定主线不变：`Layer1 3.0%` + `H2 Layer1 q2 early-gate` + `Layer3 top34%` + "
                 "`M15 replace_any + rescue` + `Stage1 2.0R / Stage2 1.5R trail / 4.0R force / Stage3 m30_merged_cross`。")
    lines.append("> 本轮只测试：在当前主线之上，是否把 M15 作为“新增触发层”继续往前提。")
    lines.append("")
    lines.append("## 结果总览")
    lines.append("")
    lines.append(md_table(headers, table_rows))
    lines.append("")
    lines.append("## 新增交易质量")
    lines.append("")
    lines.append(md_table(
        ["方案", "source_pick", "新增WR", "新增PF", "新增EV", "新增PnL", "新增MaxCL", "mode split"],
        delta_rows,
    ))
    lines.append("")

    best_pf = max(rows, key=lambda x: (x["total"]["pf"], x["total"]["ev"], x["picked_n"]))
    best_trade_gain = max(rows[1:], key=lambda x: (x["picked_n"] - rows[0]["picked_n"], x["total"]["pf"], x["total"]["ev"]))
    lines.append("## 当前判断")
    lines.append("")
    lines.append(
        f"- 基线仍然是 `{rows[0]['name']}`：`{rows[0]['picked_n']}` 笔，PF `{rows[0]['total']['pf']:.2f}`，"
        f"EV `{rows[0]['total']['ev']:+.2f}pt`，PnL `${rows[0]['trades']['total_$'].sum():.0f}`。"
    )
    lines.append(
        f"- 单看整体 PF / EV，当前最强是 `{best_pf['name']}`：`{best_pf['picked_n']}` 笔，"
        f"PF `{best_pf['total']['pf']:.2f}`，EV `{best_pf['total']['ev']:+.2f}pt`。"
    )
    lines.append(
        f"- 单看“尽量多拿新增交易”，增量最多的是 `{best_trade_gain['name']}`："
        f"比基线多 `{best_trade_gain['picked_n'] - rows[0]['picked_n']}` 笔最终交易，"
        f"同时 PF `{best_trade_gain['total']['pf']:.2f}`，EV `{best_trade_gain['total']['ev']:+.2f}pt`。"
    )
    lines.append("- 如果新增交易的 PF/EV 明显低于基线，就说明这轮 M15 前提过头了；这时更适合保留为研究备选，不直接并入主线。")
    lines.append("")

    lines.append("## 方案说明")
    lines.append("")
    lines.append("- `baseline_current_combo`：当前主线，不新增 M15 第二轮触发。")
    lines.append("- `m15_add_pre_cross_xxx`：只在当前 M30 没有原始 Layer2 候选时，额外尝试用 M15 `pre_cross` 直接补一笔。")
    lines.append("- `m15_add_close_side`：更激进的上界版，只要当前 M30 没有原始候选，就尝试用最早满足方向侧的 M15 close 直接补一笔。")
    lines.append("- `added_accept` 是 Layer3 之前新增进去的 M15 源候选数。")
    lines.append("- `source_pick` 是这些 M15 源候选里，经过 `Bias_5 top34%` 后仍留在最终交易里的数量。")
    lines.append("- `final_plus` 是整套策略相对基线最终多出来的交易数；它会同时包含 M15 新源交易，以及阈值变化后被一起带进来的旧源交易。")
    lines.append("")

    lines.append("## 文件")
    lines.append("")
    lines.append(f"- `data\\results\\m15_round2_aggressive_20260628\\{os.path.basename(SUMMARY_CSV)}`")
    lines.append(f"- `data\\results\\m15_round2_aggressive_20260628\\{os.path.basename(TRADE_CSV)}`")
    lines.append(f"- `data\\results\\m15_round2_aggressive_20260628\\{os.path.basename(ADDED_CSV)}`")
    lines.append(f"- `data\\results\\m15_round2_aggressive_20260628\\{os.path.basename(CURVE_PATH)}`")
    lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))


def main():
    os.makedirs(RESULT_ROOT, exist_ok=True)
    df, h2, m15 = base.load_market_context()
    context = build_current_final_acc(df, h2, m15)

    current_final_acc = context["final_acc"]
    base_threshold = float(current_final_acc["Bias_5"].quantile(1 - TOP_PCT / 100.0))
    base_picked = current_final_acc[current_final_acc["Bias_5"] >= base_threshold].sort_values("date").reset_index(drop=True)
    base_keys_after_l3 = trade_keys(base_picked)

    raw_keys = trade_keys(context["raw_df"])

    variants = []
    baseline_item = summarize_variant(
        df,
        current_final_acc,
        base_picked,
        base_keys_after_l3,
        "baseline_current_combo",
        current_final_acc.iloc[0:0].copy(),
    )
    variants.append(baseline_item)

    detail_frames = []
    added_frames = []

    for gap_thr in GAP_VALUES:
        added = build_added_candidates(
            df,
            m15,
            context["pass_set"],
            context["factor_map"],
            raw_keys,
            "m15_add_pre_cross",
            gap_thr=gap_thr,
        )
        merged = m15t.dedupe_anchor(current_final_acc.to_dict("records") + added.to_dict("records"))
        merged["year"] = pd.to_datetime(merged["date"]).dt.year
        name = f"m15_add_pre_cross_{gap_thr * 100:.1f}pct"
        item = summarize_variant(df, merged, base_picked, base_keys_after_l3, name, added)
        variants.append(item)
        if len(added) > 0:
            tmp = added.copy()
            tmp["report_variant"] = name
            added_frames.append(tmp)

    added_close = build_added_candidates(
        df,
        m15,
        context["pass_set"],
        context["factor_map"],
        raw_keys,
        "m15_add_close_side",
    )
    merged_close = m15t.dedupe_anchor(current_final_acc.to_dict("records") + added_close.to_dict("records"))
    merged_close["year"] = pd.to_datetime(merged_close["date"]).dt.year
    close_item = summarize_variant(df, merged_close, base_picked, base_keys_after_l3, "m15_add_close_side", added_close)
    variants.append(close_item)
    if len(added_close) > 0:
        tmp = added_close.copy()
        tmp["report_variant"] = "m15_add_close_side"
        added_frames.append(tmp)

    summary_rows = []
    curve_frames = []
    trade_frames = []
    for item in variants:
        total = item["total"]
        summary_rows.append({
            "variant": item["name"],
            "accepted_n": item["accepted_n"],
            "picked_n": item["picked_n"],
            "added_accept_n": item["added_accept_n"],
            "added_source_pick_n": item["added_source_pick_n"],
            "final_increment_n": item["final_increment_n"],
            "wr": total["wr"],
            "pf": total["pf"],
            "ev": total["ev"],
            "pnl_$": float(item["trades"]["total_$"].sum()),
            "maxcl": total["ml"],
            "maxdd_$": item["maxdd_$"],
            "maxdd_pct": item["maxdd_pct"],
            "test_pf": item["test"]["pf"],
            "test_ev": item["test"]["ev"],
            "threshold": item["threshold"],
        })
        curve_frames.append((item["name"], item["trades"][["date", "equity_$"]].copy()))
        tmp = item["trades"].copy()
        tmp["report_variant"] = item["name"]
        trade_frames.append(tmp)

    summary_df = pd.DataFrame(summary_rows).sort_values(
        ["pf", "ev", "picked_n", "pnl_$"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    summary_df.to_csv(SUMMARY_CSV, index=False, encoding="utf-8-sig")

    if trade_frames:
        pd.concat(trade_frames, ignore_index=True).to_csv(TRADE_CSV, index=False, encoding="utf-8-sig")
    if added_frames:
        pd.concat(added_frames, ignore_index=True).to_csv(ADDED_CSV, index=False, encoding="utf-8-sig")

    baseline_variant = next(x for x in variants if x["name"] == "baseline_current_combo")
    best_nonbaseline = max(
        [x for x in variants if x["name"] != "baseline_current_combo" and x["name"] != "m15_add_close_side"],
        key=lambda x: (x["total"]["pf"], x["total"]["ev"], x["picked_n"]),
    )
    close_variant = next(x for x in variants if x["name"] == "m15_add_close_side")
    s12.render_curve(
        [
            ("baseline_current_combo", baseline_variant["trades"][["date", "equity_$"]].copy()),
            (best_nonbaseline["name"], best_nonbaseline["trades"][["date", "equity_$"]].copy()),
            ("m15_add_close_side", close_variant["trades"][["date", "equity_$"]].copy()),
        ],
        CURVE_PATH,
    )

    render_report(variants)

    print(summary_df.to_string(index=False))
    print(f"Wrote {SUMMARY_CSV}")
    print(f"Wrote {TRADE_CSV}")
    print(f"Wrote {ADDED_CSV}")
    print(f"Wrote {CURVE_PATH}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
