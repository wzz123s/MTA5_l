# -*- coding: utf-8 -*-
"""Scan Stage 1 / Stage 2 settings on the current M15+H2 combo candidate and render equity curves."""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from processing.prepare import prepare
import _pre_cross_range_test as pct
import _m15_early_entry_test as m15t
import _h2_early_gate_test as h2t
import _m15_h2_combo_test as combo
from _h2_context import load_h2_context


RESULT_ROOT = os.path.join(ROOT, "data", "results", "stage12_combo_20260627")
REPORT_PATH = os.path.join(ROOT, "30m2H策略", "Stage1_Stage2测试结果.md")
DETAIL_PATH = os.path.join(RESULT_ROOT, "stage12_combo_summary.csv")
TRADE_PATH = os.path.join(RESULT_ROOT, "stage12_combo_trade_detail.csv")
CURVE_PATH = os.path.join(RESULT_ROOT, "stage12_combo_equity_curve.png")

STAGE1_VALUES = [1.0, 1.2, 1.5, 2.0]
STAGE2_TRAIL_VALUES = [1.5, 2.0, 2.5]
STAGE2_FORCE_VALUES = [2.5, 3.0, 4.0]
LOTS_PER_STAGE = 0.02
PT_VALUE_PER_LOT = 10.0
STAGE3_VARIANT = "m30_merged_cross"
START_BALANCE = 10000.0
SPLIT_DATE = pd.Timestamp("2023-01-01")


def metric(values):
    vals = np.asarray(values, dtype=float)
    if len(vals) == 0:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "ev": 0.0, "pnl": 0.0, "ml": 0}
    wins = vals > 0
    gross_win = vals[wins].sum()
    gross_loss = abs(vals[~wins].sum())
    pf = gross_win / gross_loss if gross_loss > 0 else 0.0
    cl = 0
    ml = 0
    for w in wins:
        if w:
            cl = 0
        else:
            cl += 1
            ml = max(ml, cl)
    pnl = gross_win - gross_loss
    return {
        "n": len(vals),
        "wr": wins.mean() * 100.0,
        "pf": pf,
        "ev": pnl / len(vals),
        "pnl": pnl,
        "ml": ml,
    }


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def first_opposite_idx(direction, start_i, is_long):
    target = "bad" if is_long else "good"
    for i in range(start_i + 1, len(direction)):
        if direction[i] == target:
            return i
    return len(direction) - 1


def sl_hit_before(df, start_i, end_i, is_long, stop):
    if end_i <= start_i:
        return None
    seg = df.iloc[start_i + 1 : end_i + 1]
    if len(seg) == 0:
        return None
    hits = seg["low"] <= stop if is_long else seg["high"] >= stop
    if hits.any():
        hit_pos = hits.to_numpy().argmax()
        row = seg.iloc[hit_pos]
        return {"price": stop, "time": row["date"], "idx": int(seg.index[hit_pos])}
    return None


def stage1_exit(df, trade, stage1_r):
    i = int(trade["i"])
    is_long = trade["dir"] == "L"
    entry = float(trade["entry"])
    stop = float(trade["stop"])
    r = abs(entry - stop)
    target = entry + stage1_r * r if is_long else entry - stage1_r * r

    for j in range(i + 1, len(df)):
        row = df.iloc[j]
        if is_long and row["low"] <= stop:
            return -r, "SL hit", row["date"]
        if (not is_long) and row["high"] >= stop:
            return -r, "SL hit", row["date"]
        if is_long and row["high"] >= target:
            return stage1_r * r, f"{stage1_r:.1f}R TP", row["date"]
        if (not is_long) and row["low"] <= target:
            return stage1_r * r, f"{stage1_r:.1f}R TP", row["date"]
    return 0.0, "data end", df.iloc[-1]["date"]


def stage2_exit(df, trade, trail_r, force_r):
    i = int(trade["i"])
    is_long = trade["dir"] == "L"
    entry = float(trade["entry"])
    stop = float(trade["stop"])
    r = abs(entry - stop)
    trail_start = entry + trail_r * r if is_long else entry - trail_r * r
    force = entry + force_r * r if is_long else entry - force_r * r
    trail_sl = stop
    m30_end = first_opposite_idx(df["方向_合并后"].values, i, is_long)

    for j in range(i + 1, m30_end + 1):
        row = df.iloc[j]
        if is_long and row["high"] >= force:
            return force_r * r, f"{force_r:.1f}R forced", row["date"]
        if (not is_long) and row["low"] <= force:
            return force_r * r, f"{force_r:.1f}R forced", row["date"]
        if is_long and row["low"] <= trail_sl:
            return trail_sl - entry, "trail/SL hit", row["date"]
        if (not is_long) and row["high"] >= trail_sl:
            return entry - trail_sl, "trail/SL hit", row["date"]
        if is_long and row["high"] >= trail_start and row["SMA_13"] > trail_sl:
            trail_sl = row["SMA_13"]
        if (not is_long) and row["low"] <= trail_start and (row["SMA_13"] < trail_sl or trail_sl == stop):
            trail_sl = row["SMA_13"]

    exit_price = df.iloc[m30_end]["close"]
    pnl = exit_price - entry if is_long else entry - exit_price
    return pnl, "M30 merged cross", df.iloc[m30_end]["date"]


def stage3_exit(df, trade):
    i = int(trade["i"])
    is_long = trade["dir"] == "L"
    entry = float(trade["entry"])
    stop = float(trade["stop"])
    end_i = first_opposite_idx(df["方向_合并后"].values, i, is_long)
    sl = sl_hit_before(df, i, end_i, is_long, stop)
    if sl is not None:
        return -abs(entry - stop), "SL hit", sl["time"]
    exit_price = df.iloc[end_i]["close"]
    return (exit_price - entry if is_long else entry - exit_price), "M30 merged cross", df.iloc[end_i]["date"]


def build_combo_signals():
    df, _ = prepare("base_data/XAUUSDm30.csv", min_len=8)
    h2 = load_h2_context()
    m15 = m15t.load_m15()

    m15t.df_global = df
    h2t.df_global = df

    q2_pass_set, q2_factor_map, _, _ = h2t.early_precompute(h2, df, 2, False)
    item = combo.run_variant(
        df,
        m15,
        q2_pass_set,
        q2_factor_map,
        "combo_h2_q2_plus_replace_any_rescue",
        "replace_any_plus_rescue",
    )
    top = item["top"].copy().sort_values("date").reset_index(drop=True)
    return df, top


def summarize_variant(df, signals, stage1_r, trail_r, force_r):
    rows = []
    for _, tr in signals.iterrows():
        s1_pnl, s1_exit, _ = stage1_exit(df, tr, stage1_r)
        s2_pnl, s2_exit, _ = stage2_exit(df, tr, trail_r, force_r)
        s3_pnl, s3_exit, s3_time = stage3_exit(df, tr)
        total_points = s1_pnl + s2_pnl + s3_pnl
        rows.append({
            "date": tr["date"],
            "mode": tr["mode"],
            "dir": tr["dir"],
            "stage1_r": stage1_r,
            "stage2_trail_r": trail_r,
            "stage2_force_r": force_r,
            "stage1_pnl": s1_pnl,
            "stage2_pnl": s2_pnl,
            "stage3_pnl": s3_pnl,
            "total_points": total_points,
            "total_$": total_points * LOTS_PER_STAGE * PT_VALUE_PER_LOT,
            "stage1_exit": s1_exit,
            "stage2_exit": s2_exit,
            "stage3_exit": s3_exit,
            "stage3_time": s3_time,
        })
    out = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    out["equity_$"] = START_BALANCE + out["total_$"].cumsum()
    return out


def split_metrics(out):
    train = out[pd.to_datetime(out["date"]) < SPLIT_DATE]
    test = out[pd.to_datetime(out["date"]) >= SPLIT_DATE]
    return metric(train["total_points"].values), metric(test["total_points"].values)


def render_curve(frames, curve_path):
    import matplotlib.pyplot as plt

    plt.figure(figsize=(12, 6))
    for label, frame in frames:
        plt.plot(pd.to_datetime(frame["date"]), frame["equity_$"], label=label, linewidth=2)
    plt.title("Stage1/Stage2 Equity Curves on Current Combo Candidate")
    plt.xlabel("Trade Date")
    plt.ylabel("Equity ($)")
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(curve_path, dpi=160)
    plt.close()


def main():
    df, signals = build_combo_signals()
    os.makedirs(RESULT_ROOT, exist_ok=True)

    all_rows = []
    best_pf_key = None
    best_pf_rank = None
    baseline_key = (1.2, 2.0, 3.0)
    trades_by_key = {}

    for stage1_r in STAGE1_VALUES:
        for trail_r in STAGE2_TRAIL_VALUES:
            for force_r in STAGE2_FORCE_VALUES:
                if force_r <= trail_r:
                    continue
                out = summarize_variant(df, signals, stage1_r, trail_r, force_r)
                trades_by_key[(stage1_r, trail_r, force_r)] = out
                total_m = metric(out["total_points"].values)
                train_m, test_m = split_metrics(out)
                all_rows.append({
                    "stage1_r": stage1_r,
                    "stage2_trail_r": trail_r,
                    "stage2_force_r": force_r,
                    "n": total_m["n"],
                    "wr": total_m["wr"],
                    "pf": total_m["pf"],
                    "ev": total_m["ev"],
                    "pnl": total_m["pnl"],
                    "maxcl": total_m["ml"],
                    "dollar_pnl": float(out["total_$"].sum()),
                    "final_equity": float(out["equity_$"].iloc[-1]),
                    "train_n": train_m["n"],
                    "test_n": test_m["n"],
                    "test_pf": test_m["pf"],
                    "test_ev": test_m["ev"],
                })
                rank = (total_m["pf"], total_m["ev"], total_m["pnl"], test_m["pf"], -abs(stage1_r - 1.2))
                if best_pf_rank is None or rank > best_pf_rank:
                    best_pf_rank = rank
                    best_pf_key = (stage1_r, trail_r, force_r)

    summary = pd.DataFrame(all_rows).sort_values(
        ["pf", "ev", "dollar_pnl", "test_pf"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    summary.to_csv(DETAIL_PATH, index=False, encoding="utf-8-sig")

    best_frame = trades_by_key[best_pf_key].copy()
    best_frame["variant"] = f"s1_{best_pf_key[0]:.1f}_s2_{best_pf_key[1]:.1f}_{best_pf_key[2]:.1f}"
    baseline_frame = trades_by_key[baseline_key].copy()
    baseline_frame["variant"] = "baseline_1.2_2.0_3.0"
    trade_detail = pd.concat([baseline_frame, best_frame], ignore_index=True)
    trade_detail.to_csv(TRADE_PATH, index=False, encoding="utf-8-sig")

    render_curve([
        ("Current baseline 1.2R / 2R / 3R", baseline_frame),
        (f"Best {best_pf_key[0]:.1f}R / {best_pf_key[1]:.1f}R / {best_pf_key[2]:.1f}R", best_frame),
    ], CURVE_PATH)

    top_rows = []
    for _, row in summary.head(8).iterrows():
        top_rows.append([
            f"{row['stage1_r']:.1f}R",
            f"{row['stage2_trail_r']:.1f}R",
            f"{row['stage2_force_r']:.1f}R",
            int(row["n"]),
            f"{row['wr']:.1f}%",
            f"{row['pf']:.2f}",
            f"{row['ev']:+.2f}pt",
            f"${row['dollar_pnl']:.0f}",
            int(row["maxcl"]),
            f"{row['test_pf']:.2f}",
            f"{row['test_ev']:+.2f}pt",
        ])

    baseline_row = summary[
        (summary["stage1_r"] == baseline_key[0])
        & (summary["stage2_trail_r"] == baseline_key[1])
        & (summary["stage2_force_r"] == baseline_key[2])
    ].iloc[0]
    best_row = summary.iloc[0]

    lines = []
    lines.append("# Stage 1 / Stage 2 测试结果")
    lines.append("")
    lines.append("> 基于当前主线组合候选：`combo_h2_q2_plus_replace_any_rescue`。")
    lines.append("> Stage 3 固定为当前推荐：`m30_merged_cross`。")
    lines.append("")
    lines.append("## 测试范围")
    lines.append("")
    lines.append("- Stage 1 R: `1.0 / 1.2 / 1.5 / 2.0`")
    lines.append("- Stage 2 trail start: `1.5R / 2.0R / 2.5R`")
    lines.append("- Stage 2 force close: `2.5R / 3.0R / 4.0R`")
    lines.append("- Stage 3: 固定 `m30_merged_cross`")
    lines.append("")
    lines.append("## 最优结果")
    lines.append("")
    lines.append(f"- 当前扫描最优：Stage 1 `{best_row['stage1_r']:.1f}R`，Stage 2 `{best_row['stage2_trail_r']:.1f}R trail / {best_row['stage2_force_r']:.1f}R force`。")
    lines.append(f"- 结果：{int(best_row['n'])} 笔，WR {best_row['wr']:.1f}%，PF {best_row['pf']:.2f}，EV {best_row['ev']:+.2f}pt，PnL ${best_row['dollar_pnl']:.0f}，MaxCL {int(best_row['maxcl'])}。")
    lines.append("")
    lines.append("## 与当前基线对比")
    lines.append("")
    lines.append(f"- 当前基线：Stage 1 `1.2R`，Stage 2 `2.0R trail / 3.0R force`。")
    lines.append(f"  - PF {baseline_row['pf']:.2f}，EV {baseline_row['ev']:+.2f}pt，PnL ${baseline_row['dollar_pnl']:.0f}。")
    lines.append(f"- 扫描最优：Stage 1 `{best_row['stage1_r']:.1f}R`，Stage 2 `{best_row['stage2_trail_r']:.1f}R trail / {best_row['stage2_force_r']:.1f}R force`。")
    lines.append(f"  - PF {best_row['pf']:.2f}，EV {best_row['ev']:+.2f}pt，PnL ${best_row['dollar_pnl']:.0f}。")
    lines.append("")
    lines.append("## Top 8")
    lines.append("")
    lines.append(md_table(
        ["Stage 1", "Trail", "Force", "笔数", "WR", "PF", "EV", "PnL", "MaxCL", "验证PF", "验证EV"],
        top_rows,
    ))
    lines.append("")
    lines.append("## 结果文件")
    lines.append("")
    lines.append(f"- `data\\results\\stage12_combo_20260627\\{os.path.basename(DETAIL_PATH)}`")
    lines.append(f"- `data\\results\\stage12_combo_20260627\\{os.path.basename(TRADE_PATH)}`")
    lines.append(f"- `data\\results\\stage12_combo_20260627\\{os.path.basename(CURVE_PATH)}`")
    lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(md_table(
        ["Stage 1", "Trail", "Force", "笔数", "WR", "PF", "EV", "PnL", "MaxCL", "验证PF", "验证EV"],
        top_rows,
    ))
    print()
    print(f"Best = Stage1 {best_pf_key[0]:.1f}R, Stage2 {best_pf_key[1]:.1f}R trail / {best_pf_key[2]:.1f}R force")
    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {DETAIL_PATH}")
    print(f"Wrote {TRADE_PATH}")
    print(f"Wrote {CURVE_PATH}")


if __name__ == "__main__":
    main()
