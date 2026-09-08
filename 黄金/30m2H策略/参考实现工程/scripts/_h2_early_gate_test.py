# -*- coding: utf-8 -*-
"""Test H2 early-gate variants on full strategy results."""
import os
import sys
import bisect
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from processing.prepare import prepare
import _pre_cross_range_test as pct
from _h2_context import load_h2_context


RESULT_ROOT = os.path.join(ROOT, "data", "results", "m15_h2_early_trigger_20260626")
REPORT_PATH = os.path.join(ROOT, "30m2H策略", "M15_H2提前触发测试结果.md")
DETAIL_PATH = os.path.join(RESULT_ROOT, "h2_early_gate_detail.csv")
SPLIT_DATE = pd.Timestamp("2023-01-01")


def stats(tdf):
    return pct.stats(tdf)


def stat_cells(s):
    return [s["n"], f"{s['wr']:.1f}%", f"{s['pf']:.2f}", f"{s['ev']:+.2f}pt", f"${s['pnl']:.0f}", s["ml"]]


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def smma_step(prev_smma, close, period):
    if pd.isna(prev_smma) or period <= 0:
        return np.nan
    return (prev_smma * (period - 1) + close) / period


def build_strategy(df, pass_set, factor_map):
    pre = pct.build_pre_cross(df, 0.003, pass_set, factor_map)
    cross = pct.build_cross(df, pass_set, factor_map)
    post = pct.build_post_n(df, pass_set, factor_map)
    all_modes = pct.dedupe(pre + cross + post)
    top = pct.layer3_top(all_modes).sort_values("date").reset_index(drop=True)
    return all_modes, top


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
    train = tdf[pd.to_datetime(tdf["date"]) < SPLIT_DATE]
    test = tdf[pd.to_datetime(tdf["date"]) >= SPLIT_DATE]
    return stats(train), stats(test)


def early_precompute(h2, df, q_min, use_early_factor):
    baseline_pass_set, baseline_factor_map = pct.precompute_h2(h2, df["date"].values)
    pass_set = set(baseline_pass_set)
    factor_map = {k: dict(v) for k, v in baseline_factor_map.items()}

    h2_times = pd.to_datetime(h2["date"]).values.astype("datetime64[ns]")
    close_m30 = df["close"].values
    h2_sma5 = h2["SMA_5"].values
    h2_sma13 = h2["SMA_13"].values
    h2_sma55 = h2["SMA_55"].values

    early_bar_count = 0
    for i, t in enumerate(pd.to_datetime(df["date"]).values.astype("datetime64[ns]")):
        prev_idx = bisect.bisect_right(h2_times, t) - 1
        next_idx = bisect.bisect_left(h2_times, t)
        if prev_idx < 0 or next_idx >= len(h2_times):
            continue
        if h2_times[next_idx] == t:
            continue

        # v3.36: elapsed_q 与 EA CalcBias55EarlyQ 对齐 — 距上一根 H2 的 OPEN 时间
        # (EA: elapsed_q = (last_m30_open - prev_h2_open)/1800; H2 数据 date=bar close,
        #  旧版用 close 时间差 2 根)
        prev_time = pd.Timestamp(h2_times[prev_idx]) - pd.Timedelta(hours=2)
        now_time = pd.Timestamp(t)
        elapsed_q = int((now_time - prev_time) / pd.Timedelta(minutes=30))
        if elapsed_q < q_min:
            continue

        partial_close = float(close_m30[i])
        est_sma5 = smma_step(h2_sma5[prev_idx], partial_close, 5)
        est_sma13 = smma_step(h2_sma13[prev_idx], partial_close, 13)
        est_sma55 = smma_step(h2_sma55[prev_idx], partial_close, 55)
        if any(pd.isna(x) or x == 0 for x in (est_sma5, est_sma13, est_sma55)):
            continue

        est_bias55 = abs((partial_close - est_sma55) / est_sma55 * 100.0)
        est_bias5 = abs((partial_close - est_sma5) / est_sma5 * 100.0)
        est_bias13 = abs((partial_close - est_sma13) / est_sma13 * 100.0)

        if use_early_factor:
            factor_map[i] = {
                "Bias_5": est_bias5,
                "Bias_13": est_bias13,
                "Bias_55": est_bias55,
            }

        if est_bias55 > pct.BIAS_55_THRESHOLD:
            if i not in pass_set:
                early_bar_count += 1
            pass_set.add(i)

    return pass_set, factor_map, len(pass_set), early_bar_count


def variant_result(name, note, pass_set, factor_map, base_top, pass_bars, early_bar_count):
    _, top = build_strategy(df_global, pass_set, factor_map)
    s = stats(top)
    train_s, test_s = split_stats(top)

    base_keys = trade_keys(base_top)
    top_keys = trade_keys(top)
    added_keys = top_keys - base_keys
    removed_keys = base_keys - top_keys
    added_df = subset_by_keys(top, added_keys)
    removed_df = subset_by_keys(base_top, removed_keys)

    added_modes = "-"
    if len(added_df) > 0:
        counts = added_df["mode"].value_counts().to_dict()
        added_modes = ", ".join(f"{k}:{v}" for k, v in counts.items())

    row = [
        name,
        pass_bars,
        early_bar_count,
        len(added_df),
        len(removed_df),
        *stat_cells(s),
        train_s["n"],
        test_s["n"],
        f"{test_s['pf']:.2f}",
        f"{test_s['ev']:+.2f}pt",
        note,
    ]

    return {
        "name": name,
        "row": row,
        "top": top,
        "added": added_df,
        "removed": removed_df,
        "added_modes": added_modes,
    }


def h2_section(rows, added_rows):
    lines = []
    lines.append("## 第二轮：H2 early-gate")
    lines.append("")
    lines.append("这一轮不是单看 H2 gate 通过了多少，而是把 H2 提前确认直接放回整套策略里，重新看最终交易笔数、PF、EV、MaxCL。")
    lines.append("")
    lines.append(md_table(
        ["方案", "pass_bars", "early_add_bars", "added_trades", "removed_trades", "笔数", "WR", "PF", "EV", "PnL", "MaxCL", "训练笔数", "验证笔数", "验证PF", "验证EV", "备注"],
        rows,
    ))
    lines.append("")
    lines.append("## H2 新增交易分析")
    lines.append("")
    lines.append(md_table(
        ["方案", "新增笔数", "新增WR", "新增PF", "新增EV", "新增PnL", "新增MaxCL", "mode split"],
        added_rows,
    ))
    lines.append("")
    lines.append("## 当前判断")
    lines.append("")
    lines.append("- 先看 `added_trades` 和 `removed_trades`，判断 H2 提前确认是在扩容还是只是在换仓。")
    lines.append("- 如果 `L1 only` 已经能增加笔数，就说明等待完整 H2 收完确实太慢。")
    lines.append("- 如果 `L1 + L3` 一起提前后 PF / EV 更稳，说明 H2 的质量筛选也存在时间滞后。")
    lines.append("- 下一步再决定是先和当前最优的 M15 `replace_any + rescue` 组合，还是先扩展更激进的 M15 新增触发。")
    lines.append("")
    lines.append("## 结果文件")
    lines.append("")
    lines.append(f"- `data\\results\\m15_h2_early_trigger_20260626\\{os.path.basename(DETAIL_PATH)}`")
    lines.append("")
    return "\n".join(lines)


def main():
    global df_global
    df_global, _ = prepare("base_data/XAUUSDm30.csv", min_len=8)
    h2 = load_h2_context()

    base_pass_set, base_factor_map = pct.precompute_h2(h2, df_global["date"].values)
    _, base_top = build_strategy(df_global, base_pass_set, base_factor_map)

    variants = []
    variants.append(variant_result(
        "baseline_full_h2",
        "completed H2 only",
        base_pass_set,
        base_factor_map,
        base_top,
        len(base_pass_set),
        0,
    ))

    for q_min, use_early_factor, name, note in [
        (2, False, "h2_l1_q2", "q2 start, Layer1 early only"),
        (3, False, "h2_l1_q3", "q3 start, Layer1 early only"),
        (2, True, "h2_l1l3_q2", "q2 start, Layer1 + Layer3 early"),
        (3, True, "h2_l1l3_q3", "q3 start, Layer1 + Layer3 early"),
    ]:
        pass_set, factor_map, pass_bars, early_bar_count = early_precompute(h2, df_global, q_min, use_early_factor)
        variants.append(variant_result(name, note, pass_set, factor_map, base_top, pass_bars, early_bar_count))

    os.makedirs(RESULT_ROOT, exist_ok=True)
    detail_frames = []
    rows = []
    added_rows = []
    for item in variants:
        rows.append(item["row"])
        top = item["top"].copy()
        top["report_variant"] = item["name"]
        detail_frames.append(top)

        added_s = stats(item["added"])
        added_rows.append([
            item["name"],
            added_s["n"],
            f"{added_s['wr']:.1f}%",
            f"{added_s['pf']:.2f}",
            f"{added_s['ev']:+.2f}pt",
            f"${added_s['pnl']:.0f}",
            added_s["ml"],
            item["added_modes"],
        ])

    pd.concat(detail_frames, ignore_index=True).to_csv(DETAIL_PATH, index=False, encoding="utf-8-sig")

    section = h2_section(rows, added_rows)
    if os.path.exists(REPORT_PATH):
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            existing = f.read().rstrip()
        marker = "\n## 第二轮：H2 early-gate"
        if marker in existing:
            existing = existing.split(marker)[0].rstrip()
        content = existing + "\n\n" + section + "\n"
    else:
        content = "# M15 / H2 提前触发测试结果\n\n" + section + "\n"

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(md_table(
        ["方案", "pass_bars", "early_add_bars", "added_trades", "removed_trades", "笔数", "WR", "PF", "EV", "PnL", "MaxCL", "训练笔数", "验证笔数", "验证PF", "验证EV", "备注"],
        rows,
    ))
    print()
    print(md_table(
        ["方案", "新增笔数", "新增WR", "新增PF", "新增EV", "新增PnL", "新增MaxCL", "mode split"],
        added_rows,
    ))
    print()
    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {DETAIL_PATH}")


if __name__ == "__main__":
    main()
