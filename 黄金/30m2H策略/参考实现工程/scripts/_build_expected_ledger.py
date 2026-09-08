# -*- coding: utf-8 -*-
"""Build 30m2H Python expected trade ledger (3-stage split) from frozen 121-trade baseline.

Each frozen strategy trade is executed as 3 independent sub-positions (stage 1/2/3),
matching the 30m2H EA v3.26 split-stage structure. This script reproduces the exact
stage execution logic of _stage12_combo_test.stage1_exit/stage2_exit/stage3_exit
but additionally captures each stage's exit price/time so the expected ledger can be
aligned against the EA's exported 30m2H_strategy_trade_ledger.csv.

Reference parameters (frozen 2026-08-10, 121-trade baseline):
  - Layer1 |H2 Bias_55| > 3.0%
  - Layer2 pre_cross + cross + post_n(2-6)
  - Layer3 Bias_5 top 34%  (threshold 0.374868)
  - M15  replace_any + rescue
  - H2   Layer1 q2 early-gate
  - Stage1 2.0R, Stage2 1.5R trail / 4.0R force, Stage3 M30 merged cross
  - stop spec [5, 35] pt
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import _current_baseline as base
import _stage12_combo_test as s12

SPEC_LO = 5
SPEC_HI = 35
TOP_PCT = 34
STAGE1_R = 2.0
STAGE2_TRAIL_R = 1.5
STAGE2_FORCE_R = 4.0

OUT_DIR = os.path.join(
    ROOT, "..", "data", "validation", "final_ea_alignment_20260811"
)
LEDGER_PATH = os.path.join(OUT_DIR, "python_expected_trade_ledger.csv")
SUMMARY_PATH = os.path.join(OUT_DIR, "python_expected_ledger_summary.md")


# --- stage executions, returning (pnl_points, reason, time, exit_price) ---

def stage1_exec(df, trade, stage1_r):
    """Stage 1: 2.0R TP or SL hit (single unit). Returns exit price."""
    i = int(trade["i"])
    is_long = trade["dir"] == "L"
    entry = float(trade["entry"])
    stop = float(trade["stop"])
    r = abs(entry - stop)
    target = entry + stage1_r * r if is_long else entry - stage1_r * r
    for j in range(i + 1, len(df)):
        row = df.iloc[j]
        if is_long and row["low"] <= stop:
            return -r, "SL hit", row["date"], stop
        if (not is_long) and row["high"] >= stop:
            return -r, "SL hit", row["date"], stop
        if is_long and row["high"] >= target:
            return stage1_r * r, f"{stage1_r:.1f}R TP", row["date"], target
        if (not is_long) and row["low"] <= target:
            return stage1_r * r, f"{stage1_r:.1f}R TP", row["date"], target
    return 0.0, "data end", df.iloc[-1]["date"], df.iloc[-1]["close"]


def stage2_exec(df, trade, trail_r, force_r):
    """Stage 2: trail 1.5R / force 4R / M30 merged cross. Returns exit price."""
    i = int(trade["i"])
    is_long = trade["dir"] == "L"
    entry = float(trade["entry"])
    stop = float(trade["stop"])
    r = abs(entry - stop)
    trail_start = entry + trail_r * r if is_long else entry - trail_r * r
    force = entry + force_r * r if is_long else entry - force_r * r
    trail_sl = stop
    m30_end = s12.first_opposite_idx(df["方向_合并后"].values, i, is_long)
    for j in range(i + 1, m30_end + 1):
        row = df.iloc[j]
        if is_long and row["high"] >= force:
            return force_r * r, f"{force_r:.1f}R forced", row["date"], force
        if (not is_long) and row["low"] <= force:
            return force_r * r, f"{force_r:.1f}R forced", row["date"], force
        if is_long and row["low"] <= trail_sl:
            return trail_sl - entry, "trail/SL hit", row["date"], trail_sl
        if (not is_long) and row["high"] >= trail_sl:
            return entry - trail_sl, "trail/SL hit", row["date"], trail_sl
        if is_long and row["high"] >= trail_start and row["SMA_13"] > trail_sl:
            trail_sl = row["SMA_13"]
        if (not is_long) and row["low"] <= trail_start and (row["SMA_13"] < trail_sl or trail_sl == stop):
            trail_sl = row["SMA_13"]
    exit_price = df.iloc[m30_end]["close"]
    pnl = exit_price - entry if is_long else entry - exit_price
    return pnl, "M30 merged cross", df.iloc[m30_end]["date"], exit_price


def stage3_exec(df, trade):
    """Stage 3: final SL or M30 merged cross. Returns exit price."""
    i = int(trade["i"])
    is_long = trade["dir"] == "L"
    entry = float(trade["entry"])
    stop = float(trade["stop"])
    end_i = s12.first_opposite_idx(df["方向_合并后"].values, i, is_long)
    sl = s12.sl_hit_before(df, i, end_i, is_long, stop)
    if sl is not None:
        return -abs(entry - stop), "SL hit", sl["time"], stop
    exit_price = df.iloc[end_i]["close"]
    pnl = exit_price - entry if is_long else entry - exit_price
    return pnl, "M30 merged cross", df.iloc[end_i]["date"], exit_price


def apply_maxpos_filter(picked, df, max_pos=3):
    """模拟 EA InpMaxPos 持仓限制: 信号入场时若已有持仓 stage 数 >= max_pos → 拒绝。

    EA 语义 (OurStageCount): 每 tick 数实际持仓 (magic InpMagic+1..3) 的 stage 数,
    信号判定 (new bar 收盘) 时 >= max_pos → 信号丢弃 (不重试)。
    Python 近似: 用 stage 的 bar 级 exit_time 判断未平仓状态。
    """
    rows = []
    for _, tr in picked.iterrows():
        is_long = tr["dir"] == "L"
        entry_time = pd.to_datetime(tr["entry_time"])
        stages = [
            (1, stage1_exec(df, tr, STAGE1_R)),
            (2, stage2_exec(df, tr, STAGE2_TRAIL_R, STAGE2_FORCE_R)),
            (3, stage3_exec(df, tr)),
        ]
        exit_times = [pd.to_datetime(et) for _, (_, _, et, _) in stages]
        # v3.36: MAXPOS 检查时刻 = 信号判定时刻 (bar close = entry_time + 30min),
        # 与 EA 一致 (EA 在 new_m30_bar tick 检查 OurStageCount)。
        # 旧版用 entry_time (= 信号 bar open) → 检查早 30min → 多拒信号。
        check_time = entry_time + pd.Timedelta(minutes=30)
        held = 0
        for acc in rows:
            for et in acc["_exit_times"]:
                if et > check_time:
                    held += 1
        if held >= max_pos:
            continue
        rows.append({"_seq": None, "_exit_times": exit_times, "_tr": tr, "_stages": stages})
    return rows


def build_ledger(ea_executable=False, rolling_merged=False, max_pos_sim=0):
    if ea_executable:
        # EA 可执行口径: 滚动 Layer3 分位 + M30 close proxy + M15 require_earlier
        df, final_acc = base.build_final_accepted(
            spec_lo=SPEC_LO, spec_hi=SPEC_HI, ea_executable_diag=True,
            rolling_merged=rolling_merged,
        )
        h2 = base.load_h2_context()
        threshold, picked = base.apply_layer3_ea_executable(final_acc, h2, top_pct=TOP_PCT)
    else:
        df, final_acc = base.build_final_accepted(
            spec_lo=SPEC_LO, spec_hi=SPEC_HI, rolling_merged=rolling_merged,
        )
        threshold, picked = base.apply_layer3(final_acc, top_pct=TOP_PCT)

    if max_pos_sim > 0:
        sim_rows = apply_maxpos_filter(picked, df, max_pos=max_pos_sim)
        print(f"MAXPOS 模拟: picked={len(picked)} → 接受 {len(sim_rows)} (max_pos={max_pos_sim})")
        # sim_rows 顺序 = picked 顺序 (含被拒标记) → 重建完整 picked 列表
        picked_list = list(picked.iterrows())
        accepted_idx = 0
    else:
        sim_rows = None
        picked_list = None

    rows = []
    seq = 0
    for _, tr in picked.iterrows():
        entry_time = pd.to_datetime(tr["entry_time"])
        entry = float(tr["entry"])
        stop = float(tr["stop"])
        stop_pts = abs(entry - stop)
        dir_str = "BUY" if tr["dir"] == "L" else "SELL"
        trigger_tag = "[M30 CLOSE]" if entry_time == pd.to_datetime(tr["date"]) else "[M15 SLOT1]"

        if sim_rows is not None:
            # MAXPOS: 跳过被拒笔 (sim_rows 是接受的子集, 顺序与 picked 一致)
            if accepted_idx >= len(sim_rows):
                break
            sim = sim_rows[accepted_idx]
            if sim["_tr"].name != tr.name:
                continue  # 被拒笔 → 跳过 (不占 seq)
            stages = sim["_stages"]
            accepted_idx += 1
        else:
            stages = [
                (1, stage1_exec(df, tr, STAGE1_R)),
                (2, stage2_exec(df, tr, STAGE2_TRAIL_R, STAGE2_FORCE_R)),
                (3, stage3_exec(df, tr)),
            ]

        seq += 1
        for stage, (pnl, reason, exit_time, exit_price) in stages:
            rows.append({
                "trade_seq": seq,
                "signal_anchor_time": pd.to_datetime(tr["date"]),
                "trigger_tag": trigger_tag,
                "signal_src": tr["mode"],
                "dir": dir_str,
                "stage": stage,
                "open_time": entry_time,
                "signal_entry": entry,
                "signal_stop": stop,
                "stop_pts": round(stop_pts, 2),
                "exit_time": exit_time,
                "exit_price": exit_price,
                "local_exit_reason": reason,
                "pnl_points": pnl,
                "trade_key": f"{entry_time.strftime('%Y.%m.%d %H:%M:%S')}|{dir_str}|S{stage}",
            })

    out = pd.DataFrame(rows).sort_values(["trade_seq", "stage"]).reset_index(drop=True)
    out.to_csv(LEDGER_PATH, index=False, encoding="utf-8-sig")

    # Summary
    trades = picked.shape[0]
    stage_counts = out["stage"].value_counts().sort_index()
    lines = [
        "# 30m2H Python Expected Ledger 构建记录",
        "",
        f"> 生成时间：2026-08-11",
        f"> 基线：{trades} 笔冻结口径（Layer3 threshold {threshold:.6f}）",
        f"> 每笔拆 3 个 stage 子头寸 → 共 {len(out)} 行",
        "",
        "| 指标 | 值 |",
        "| --- | ---: |",
        f"| 交易数 | {trades} |",
        "| Ledger 行数 | " + str(len(out)) + " |",
        "| stage1 行数 | " + str(int(stage_counts.get(1, 0))) + " |",
        "| stage2 行数 | " + str(int(stage_counts.get(2, 0))) + " |",
        "| stage3 行数 | " + str(int(stage_counts.get(3, 0))) + " |",
        "| exit 原因 | SL hit / 2.0R TP / trail/SL hit / 4.0R forced / M30 merged cross |",
        "",
        "## 参数",
        "",
        "- Layer1: `|H2 Bias_55| > 3.0%`",
        "- Layer2: `pre_cross + cross + post_n(2-6)`",
        "- Layer3: `Bias_5 top 34%`",
        "- M15: `replace_any + rescue`",
        "- H2: `Layer1 q2 early-gate`",
        "- Stage1: `2.0R` / Stage2: `1.5R trail / 4.0R force` / Stage3: `M30 merged cross`",
        f"- stop spec: `[{SPEC_LO}, {SPEC_HI}] pt`",
        "",
        "## 文件",
        "",
        f"- `{os.path.relpath(LEDGER_PATH, ROOT)}`",
    ]
    with open(SUMMARY_PATH, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))

    print("\n".join(lines))
    print(f"\nWrote {LEDGER_PATH}")
    print(f"Wrote {SUMMARY_PATH}")
    return out


if __name__ == "__main__":
    import sys as _s
    args = _s.argv[1:]
    mp = 0
    if "--maxpos" in args:
        i = args.index("--maxpos")
        if i + 1 < len(args):
            mp = int(args[i + 1])
    build_ledger(
        ea_executable=("--ea" in args),
        rolling_merged=("--rolling" in args),
        max_pos_sim=mp,
    )
