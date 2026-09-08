# -*- coding: utf-8 -*-
"""30m2H Python expected vs EA actual 逐笔对齐 (128 笔基线 × 3 stage)

匹配键: (signal_anchor_time, dir, stage)
对比字段: signal_entry / signal_stop / exit_time / exit_price / local_exit_reason / pnl_points
输出: python_vs_ea_alignment_summary.csv / detail.csv / alignment_report.md
"""
from __future__ import annotations


from pathlib import Path
import pandas as pd

BASE = Path(r"F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\final_ea_alignment_20260811")
EXPECTED = BASE / "python_expected_trade_ledger.csv"
ACTUAL = BASE / "30m2H_strategy_trade_ledger_v335.csv"
SUMMARY = BASE / "python_vs_ea_alignment_summary.csv"
DETAIL = BASE / "python_vs_ea_alignment_detail.csv"
REPORT = BASE / "alignment_report.md"

TOLERANCE = 1e-6
BAR_MINUTES = 30  # M30 bar 容差

# reason 语义映射（EA 名称 → Python 名称）
REASON_MAP = {
    "stage1_tp": "2.0R TP",
    "stage2_forced": "4.0R forced",
    "stage3_cross_exit": "M30 merged cross",
    "stage2_merged_cross": "M30 merged cross",
    "deal_exit": "SL hit",   # 平仓 deal（SL/trail 等）→ 归为 SL hit 类
}


def norm_time(s):
    """归一化时间到 '%Y-%m-%d %H:%M:%S'（Series 或标量）。"""
    return pd.to_datetime(s).dt.strftime("%Y-%m-%d %H:%M:%S")


def load_expected():
    df = pd.read_csv(EXPECTED, encoding="utf-8-sig")
    df["signal_anchor_time"] = pd.to_datetime(df["signal_anchor_time"])
    return df


def load_actual():
    df = pd.read_csv(ACTUAL, encoding="utf-8-sig")
    df["signal_anchor_time"] = pd.to_datetime(df["signal_anchor_time"])
    return df


def main() -> None:
    exp = load_expected()
    act = load_actual()
    print(f"expected rows: {len(exp)} (trades {exp['trade_seq'].nunique()})")
    print(f"actual rows:   {len(act)}")
    print(f"actual columns: {list(act.columns)[:20]}")

    exp["match_key"] = (
        exp["signal_anchor_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
        + "|" + exp["dir"] + "|S" + exp["stage"].astype(str)
    )
    act["match_key"] = (
        act["signal_anchor_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
        + "|" + act["dir"] + "|S" + act["stage"].astype(str)
    )

    exp_keys = set(exp["match_key"])
    act_keys = set(act["match_key"])
    matched = exp_keys & act_keys
    missing = exp_keys - act_keys
    extra = act_keys - exp_keys

    # --- 容差匹配（时间 ±30min 同 M30 bar + dir + stage）---
    exp_tm = pd.to_datetime(exp["signal_anchor_time"])
    act_tm = pd.to_datetime(act["signal_anchor_time"])
    tol_matched_keys = []
    for _, row in act.iterrows():
        same_dir_stage = exp[
            (exp["dir"] == row["dir"]) & (exp["stage"] == row["stage"])
        ]
        if len(same_dir_stage) == 0:
            continue
        d = (same_dir_stage["signal_anchor_time"] - row["signal_anchor_time"]).abs()
        if d.min() <= pd.Timedelta(minutes=BAR_MINUTES):
            tol_matched_keys.append(row["match_key"])
    tol_matched = len(set(tol_matched_keys))

    detail = exp[exp["match_key"].isin(matched)].merge(
        act[["match_key", "signal_entry", "signal_stop", "exit_time", "exit_price",
             "local_exit_reason", "stop_pts", "profit", "net_profit"]],
        on="match_key", suffixes=("_exp", "_ea"),
    )
    detail["entry_diff"] = (detail["signal_entry_exp"] - detail["signal_entry_ea"]).abs()
    detail["stop_diff"] = (detail["signal_stop_exp"] - detail["signal_stop_ea"]).abs()
    detail["exit_price_diff"] = (detail["exit_price_exp"] - detail["exit_price_ea"]).abs()
    # exit_time 匹配: 同 M30 bar（±30 分钟容差，EA 为 tick 精度）
    et_exp = pd.to_datetime(detail["exit_time_exp"])
    et_ea = pd.to_datetime(detail["exit_time_ea"])
    detail["exit_time_match"] = (et_exp - et_ea).abs().dt.total_seconds() <= BAR_MINUTES * 60
    # reason 匹配: 语义映射
    detail["reason_match"] = detail.apply(
        lambda r: REASON_MAP.get(str(r["local_exit_reason_ea"]).strip(), str(r["local_exit_reason_ea"]).strip())
        == str(r["local_exit_reason_exp"]).strip(), axis=1)
    detail["pnl_diff"] = (detail["pnl_points"] - detail["profit"]).abs()
    # pnl 符号一致率
    detail["pnl_sign_match"] = (detail["pnl_points"] * detail["profit"]) >= 0

    rows = {
        "expected_rows": len(exp),
        "actual_rows": len(act),
        "matched_rows": len(matched),
        "tolerance_matched_rows": tol_matched,
        "missing_in_actual": len(missing),
        "extra_in_actual": len(extra),
        "max_abs_entry_diff": detail["entry_diff"].max() if len(detail) else None,
        "max_abs_stop_diff": detail["stop_diff"].max() if len(detail) else None,
        "max_abs_exit_diff": detail["exit_price_diff"].max() if len(detail) else None,
        "exit_time_match_count": int(detail["exit_time_match"].sum()) if len(detail) else 0,
        "reason_match_count": int(detail["reason_match"].sum()) if len(detail) else 0,
        "pnl_sign_match_count": int(detail["pnl_sign_match"].sum()) if len(detail) else 0,
        "max_abs_pnl_points_diff": detail["pnl_diff"].max() if len(detail) else None,
    }
    pd.DataFrame([rows]).to_csv(SUMMARY, index=False, encoding="utf-8-sig")
    detail.to_csv(DETAIL, index=False, encoding="utf-8-sig")

    print("\n=== 对齐结果 ===")
    for k, v in rows.items():
        print(f"  {k}: {v}")

    # 报告
    lines = [
        "# 30m2H Python vs EA 逐笔对齐报告",
        "",
        f"> 生成时间：2026-08-11",
        f"> 基线：128 笔 UTC 同源口径",
        "",
        "| 指标 | 数值 |",
        "| --- | ---: |",
    ]
    for k, v in rows.items():
        lines.append(f"| {k} | {v} |")
    lines += [
        "",
        "## 判定",
        "",
        f"status = {'pass' if len(missing) == 0 and len(extra) == 0 else 'fail'}",
    ]
    (REPORT).write_text("\n".join(lines), encoding="utf-8-sig")
    print(f"\n已输出: {SUMMARY.name} / {DETAIL.name} / {REPORT.name}")


if __name__ == "__main__":
    main()
