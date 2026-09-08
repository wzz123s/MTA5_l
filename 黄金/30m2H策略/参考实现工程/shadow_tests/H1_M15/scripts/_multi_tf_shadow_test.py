# -*- coding: utf-8 -*-
"""Shadow-test H1/M15 confirmations without changing the live EA logic.

This script keeps the current accepted baseline fixed:
- H2 Layer 1: |Bias_55| > 3.0%
- M30 Layer 2: pre_cross(gap<=0.300%) + cross + post_n(2-6)
- H2 Layer 3: Bias_5 top 30%
- stop spec: [5, 35] pt

It then applies optional H1/M15 filters to the resulting 80 baseline trades.
"""
import os
import sys
import bisect
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from processing.prepare import prepare
from processing.smma import calc_smma
import _pre_cross_range_test as pct

SHADOW_ROOT = os.path.join(ROOT, "shadow_tests", "H1_M15")
REPORT_PATH = os.path.join(SHADOW_ROOT, "results", "H1_M15影子测试结果.md")
CSV_PATH = os.path.join(SHADOW_ROOT, "data", "H1_M15影子测试明细.csv")

BASE_PRE_GAP = 0.003
SPLIT_DATE = pd.Timestamp("2023-01-01")


def load_tf(path, add_hours=2):
    df = pd.read_csv(path, encoding="gbk")
    df.columns = [
        "date", "open", "high", "low", "close", "volume",
        "spread", "real_volume", "symbol", "time_diff",
    ]
    df["date"] = pd.to_datetime(df["date"]) + pd.Timedelta(hours=add_hours)
    df = df.sort_values("date").reset_index(drop=True)
    df["SMA_5"] = calc_smma(df["close"], 5).values
    df["SMA_13"] = calc_smma(df["close"], 13).values
    df["SMA_55"] = calc_smma(df["close"], 55).values
    df["dir"] = np.where(df["SMA_5"] > df["SMA_13"], 1, -1)
    df.loc[df["SMA_5"].isna() | df["SMA_13"].isna(), "dir"] = 0
    df["bias5"] = np.where(
        df["SMA_5"].notna() & (df["SMA_5"] != 0),
        (df["close"] - df["SMA_5"]).abs() / df["SMA_5"] * 100,
        np.nan,
    )
    df["bias55"] = np.where(
        df["SMA_55"].notna() & (df["SMA_55"] != 0),
        (df["close"] - df["SMA_55"]).abs() / df["SMA_55"] * 100,
        np.nan,
    )
    return df


def build_baseline():
    df, _ = prepare("base_data/XAUUSDm30.csv", min_len=8)
    h2 = pd.read_csv("base_data/H2_XAUUSDm_39col.csv", encoding="utf-8-sig")
    h2["date"] = pd.to_datetime(h2["date"])
    pass_set, factor_map = pct.precompute_h2(h2, df["date"].values)
    pre = pct.build_pre_cross(df, BASE_PRE_GAP, pass_set, factor_map)
    cross = pct.build_cross(df, pass_set, factor_map)
    post = pct.build_post_n(df, pass_set, factor_map)
    all_modes = pct.dedupe(pre + cross + post)
    top = pct.layer3_top(all_modes)
    return top.sort_values("date").reset_index(drop=True)


def add_context(trades, tf, prefix):
    out = trades.copy()
    times = pd.to_datetime(tf["date"]).values.astype("datetime64[ns]")
    trade_times = pd.to_datetime(out["date"]).values.astype("datetime64[ns]")

    cols = {
        f"{prefix}_idx": [],
        f"{prefix}_date": [],
        f"{prefix}_dir": [],
        f"{prefix}_close": [],
        f"{prefix}_sma13": [],
        f"{prefix}_bias5": [],
        f"{prefix}_bias55": [],
        f"{prefix}_dir_prev1": [],
        f"{prefix}_dir_prev2": [],
    }
    for t in trade_times:
        idx = bisect.bisect_right(times, t) - 1
        cols[f"{prefix}_idx"].append(idx)
        if idx < 0:
            cols[f"{prefix}_date"].append(pd.NaT)
            cols[f"{prefix}_dir"].append(0)
            cols[f"{prefix}_close"].append(np.nan)
            cols[f"{prefix}_sma13"].append(np.nan)
            cols[f"{prefix}_bias5"].append(np.nan)
            cols[f"{prefix}_bias55"].append(np.nan)
            cols[f"{prefix}_dir_prev1"].append(0)
            cols[f"{prefix}_dir_prev2"].append(0)
            continue
        row = tf.iloc[idx]
        cols[f"{prefix}_date"].append(row["date"])
        cols[f"{prefix}_dir"].append(int(row["dir"]))
        cols[f"{prefix}_close"].append(float(row["close"]))
        cols[f"{prefix}_sma13"].append(float(row["SMA_13"]) if not pd.isna(row["SMA_13"]) else np.nan)
        cols[f"{prefix}_bias5"].append(float(row["bias5"]) if not pd.isna(row["bias5"]) else np.nan)
        cols[f"{prefix}_bias55"].append(float(row["bias55"]) if not pd.isna(row["bias55"]) else np.nan)
        cols[f"{prefix}_dir_prev1"].append(int(tf.iloc[idx - 1]["dir"]) if idx - 1 >= 0 else 0)
        cols[f"{prefix}_dir_prev2"].append(int(tf.iloc[idx - 2]["dir"]) if idx - 2 >= 0 else 0)

    for key, val in cols.items():
        out[key] = val
    return out


def trade_sign(tdf):
    return np.where(tdf["dir"] == "L", 1, -1)


def metric(tdf):
    return pct.stats(tdf)


def stat_cells(tdf):
    s = metric(tdf)
    return [s["n"], f"{s['wr']:.1f}%", f"{s['pf']:.2f}", f"{s['ev']:+.2f}pt", f"${s['pnl']:.0f}", s["ml"]]


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def split_stats(tdf):
    train = tdf[pd.to_datetime(tdf["date"]) < SPLIT_DATE]
    test = tdf[pd.to_datetime(tdf["date"]) >= SPLIT_DATE]
    return stat_cells(train), stat_cells(test)


def evaluate_variants(ctx):
    sign = trade_sign(ctx)
    variants = []

    h1_available = ctx["h1_idx"] >= 0
    m15_available = ctx["m15_idx"] >= 0

    # Baselines for fair comparison.
    variants.append(("baseline_all", ctx, "当前 80 笔基线"))
    variants.append(("baseline_h1_available", ctx[h1_available], "H1 覆盖期基线"))
    variants.append(("baseline_m15_available", ctx[m15_available], "M15 覆盖期基线，仅用于比较 M15 过滤"))

    h1_align = h1_available & (ctx["h1_dir"].values == sign)
    h1_any2 = h1_available & ((ctx["h1_dir"].values == sign) | (ctx["h1_dir_prev1"].values == sign))
    h1_all2 = h1_available & (ctx["h1_dir"].values == sign) & (ctx["h1_dir_prev1"].values == sign)
    h1_bias5_thr = ctx.loc[h1_available, "h1_bias5"].quantile(0.70)
    h1_bias5_top30 = h1_available & (ctx["h1_bias5"] >= h1_bias5_thr)

    variants.extend([
        ("h1_dir_align", ctx[h1_align], "H1 SMMA5/13 方向与交易方向一致"),
        ("h1_recent2_any", ctx[h1_any2], "最近 2 根 H1 至少 1 根同向"),
        ("h1_recent2_all", ctx[h1_all2], "最近 2 根 H1 都同向"),
        ("h1_bias5_top30", ctx[h1_bias5_top30], "H1 Bias_5 位于基线候选 top30%"),
    ])

    m15_dir_align = m15_available & (ctx["m15_dir"].values == sign)
    m15_close_side = m15_available & (
        ((sign == 1) & (ctx["m15_close"] > ctx["m15_sma13"])) |
        ((sign == -1) & (ctx["m15_close"] < ctx["m15_sma13"]))
    )
    m15_both = m15_dir_align & m15_close_side
    m15_recent2_all = m15_available & (ctx["m15_dir"].values == sign) & (ctx["m15_dir_prev1"].values == sign)

    variants.extend([
        ("m15_dir_align", ctx[m15_dir_align], "M15 SMMA5/13 方向同向"),
        ("m15_close_side", ctx[m15_close_side], "M15 close 在 SMA13 交易方向一侧"),
        ("m15_dir_and_close", ctx[m15_both], "M15 方向同向且 close 在 SMA13 同侧"),
        ("m15_recent2_all", ctx[m15_recent2_all], "最近 2 根 M15 都同向"),
    ])

    combos = [
        ("h1_align__m15_dir", h1_align & m15_dir_align, "H1 同向 + M15 方向同向"),
        ("h1_align__m15_close", h1_align & m15_close_side, "H1 同向 + M15 close 同侧"),
        ("h1_any2__m15_dir", h1_any2 & m15_dir_align, "H1 近 2 根任一同向 + M15 同向"),
        ("h1_any2__m15_close", h1_any2 & m15_close_side, "H1 近 2 根任一同向 + M15 close 同侧"),
    ]
    variants.extend((name, ctx[mask], desc) for name, mask, desc in combos)

    rows = []
    detail = []
    for name, tdf, desc in variants:
        train_cells, test_cells = split_stats(tdf)
        rows.append([name, desc, *stat_cells(tdf), train_cells[0], test_cells[0], test_cells[2], test_cells[3]])
        detail.append((name, desc, tdf.copy()))
    return rows, detail


def main():
    baseline = build_baseline()
    h1 = load_tf("base_data/XAUUSDm16385.csv")
    m15 = load_tf("base_data/XAUUSDm15.csv")

    ctx = add_context(baseline, h1, "h1")
    ctx = add_context(ctx, m15, "m15")

    rows, detail = evaluate_variants(ctx)

    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    ctx.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    lines = []
    lines.append("# H1/M15 小周期影子测试结果")
    lines.append("")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("本测试不改 EA、不改现有策略代码，只在 Python 侧对当前 80 笔基线候选做附加过滤验证。")
    lines.append("")
    lines.append("## 固定基线")
    lines.append("")
    lines.append(md_table(
        ["项目", "值"],
        [
            ["Layer 1", "H2 `|Bias_55| > 3.0%`"],
            ["Layer 2", "`pre_cross(gap<=0.300%) + cross + post_n(2-6)`"],
            ["Layer 3", "H2 `Bias_5 top30`"],
            ["stop spec", "`[5, 35] pt`"],
            ["基线结果", "80 笔，WR 65.0%，PF 8.06，EV +33.27pt，PnL $2662，MaxCL 5"],
        ],
    ))
    lines.append("")
    lines.append("## 结果总览")
    lines.append("")
    lines.append(md_table(
        ["方案", "说明", "笔数", "WR", "PF", "EV", "PnL", "MaxCL", "训练笔数(<2023)", "验证笔数(>=2023)", "验证PF", "验证EV"],
        rows,
    ))
    lines.append("")
    lines.append("## 初步结论")
    lines.append("")
    lines.append("- H1/M15 过滤必须优先看样本数和验证段表现，不能只看总 PF。")
    lines.append("- M15 数据从 2022-03-30 附近才开始，所有 M15 方案必须和 `baseline_m15_available` 比较，不能直接和 8.5 年 80 笔基线比较。")
    lines.append("- 若某方案样本数低于 50，即使 PF 很高，也只作为观察，不进入 EA。")
    lines.append("- 只有满足样本数、PF/EV、MaxCL、训练/验证稳定性后，才考虑归档旧代码并进入 EA。")
    lines.append("")
    lines.append("## 明细文件")
    lines.append("")
    lines.append(f"- `{os.path.relpath(CSV_PATH, ROOT)}`")
    lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(md_table(
        ["方案", "说明", "笔数", "WR", "PF", "EV", "PnL", "MaxCL", "训练笔数", "验证笔数", "验证PF", "验证EV"],
        rows,
    ))
    print(f"\nWrote {REPORT_PATH}")
    print(f"Wrote {CSV_PATH}")


if __name__ == "__main__":
    main()
