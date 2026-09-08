# -*- coding: utf-8 -*-
"""Rebuild Python-with-MT5-data signals using current MT5 export and +90m time semantics.

This script writes versioned outputs only. It does not overwrite the historical
data/signals_mt5 directory because the old script is known to use stale path and
mixed semantics.
"""
from __future__ import annotations


import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from processing.prepare import prepare
import _current_baseline as cb
import _h2_early_gate_test as h2t
import _m15_early_entry_test as m15t
import _m15_h2_combo_test as combo
import _pre_cross_range_test as pct
import _stage12_combo_test as s12
from _h2_context import load_h2_context


DATA_DIR = ROOT / "黄金" / "30m2H策略" / "data"
VALIDATION_DIR = DATA_DIR / "validation"
OUT_ROOT = DATA_DIR / "signals_mt5_shift90_20260712"
MT5_BAR_EXPORT = VALIDATION_DIR / "mt5_only_bar_export_session5_20260712.csv"
MT5_SIGNAL_CSV = (
    VALIDATION_DIR
    / "mt5_log_session_diff_v326_full_20260712_m30postn_strict_veto_initfix_ea_diag"
    / "session_03"
    / "mt5_signals.csv"
)
M30_RAW_CSV = ROOT / "base_data" / "XAUUSDm30.csv"

TIME_SHIFT_MINUTES = 90
SPEC_LO = 5
SPEC_HI = 35
BIAS55_THRESHOLD = 3.0
TOP_PCT = 34
STAGE1_R = 2.0
STAGE2_TRAIL_R = 1.5
STAGE2_FORCE_R = 4.0


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def load_mt5_export() -> pd.DataFrame:
    df = pd.read_csv(MT5_BAR_EXPORT, encoding="utf-8-sig")
    df["bar_time_raw"] = pd.to_datetime(df["bar_time"], format="%Y.%m.%d %H:%M")
    df["date"] = df["bar_time_raw"] + pd.Timedelta(minutes=TIME_SHIFT_MINUTES)
    return df.sort_values("date").reset_index(drop=True)


def build_m30_smma(mt5: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=pd.to_datetime(mt5["date"]))
    out.index.name = "date"
    out["m30_sma5"] = pd.to_numeric(mt5["m30_sma5"], errors="coerce").values
    out["m30_sma13"] = pd.to_numeric(mt5["m30_sma13"], errors="coerce").values
    out["close"] = pd.to_numeric(mt5["close"], errors="coerce").values
    return out[~out.index.duplicated(keep="last")].sort_index()


def build_h2_barlevel(mt5: pd.DataFrame) -> pd.DataFrame:
    h2 = pd.DataFrame()
    h2["date"] = pd.to_datetime(mt5["date"])
    h2["close"] = pd.to_numeric(mt5["h2_close"], errors="coerce")
    h2["SMA_5"] = pd.to_numeric(mt5["h2_sma5"], errors="coerce")
    h2["SMA_13"] = pd.to_numeric(mt5["h2_sma13"], errors="coerce")
    h2["SMA_55"] = pd.to_numeric(mt5["h2_sma55"], errors="coerce")
    h2["source_bar_time"] = pd.to_datetime(mt5["bar_time_raw"])
    h2 = h2.dropna(subset=["date", "close", "SMA_5", "SMA_13", "SMA_55"])
    h2 = h2[h2["SMA_55"] != 0]
    h2 = h2.drop_duplicates(subset=["date"], keep="last").sort_values("date").reset_index(drop=True)
    return h2


def apply_max_pos_3(picked: pd.DataFrame) -> pd.DataFrame:
    if len(picked) == 0:
        return picked.copy()
    picked_sorted = picked.sort_values("date")
    picked_filtered = []
    active = []
    for _, row in picked_sorted.iterrows():
        anchor = pd.Timestamp(row["date"])
        active = [a for a in active if a[0] > anchor]
        if len(active) < 3:
            picked_filtered.append(row)
            active.append((anchor + pd.Timedelta(hours=24), anchor))
    return pd.DataFrame(picked_filtered).reset_index(drop=True)


def stage_stop_metrics(trades: pd.DataFrame) -> dict[str, object]:
    out: dict[str, object] = {
        "trade_rows": int(len(trades)),
        "unique_signal_rows": int(
            trades.drop_duplicates(subset=["date", "mode", "dir"]).shape[0]
            if {"date", "mode", "dir"}.issubset(trades.columns)
            else len(trades)
        ),
    }
    if "total_points" in trades.columns:
        points = pd.to_numeric(trades["total_points"], errors="coerce")
        out["wins"] = int((points > 0).sum())
        out["losses"] = int((points <= 0).sum())
        out["win_rate_pct"] = float((points > 0).mean() * 100.0) if len(points) else 0.0
    if "total_$" in trades.columns:
        total = pd.to_numeric(trades["total_$"], errors="coerce").sum()
        out["total_dollars"] = float(total)
        out["final_balance_python_multiplier5"] = float(500.0 + total * 5.0)
    for col in ["stage1_exit", "stage2_exit", "stage3_exit"]:
        if col in trades.columns:
            out[f"{col}_sl_count"] = int(trades[col].astype(str).str.contains("SL", regex=False).sum())
    if {"stage1_exit", "stage2_exit", "stage3_exit"}.issubset(trades.columns):
        s1 = trades["stage1_exit"].astype(str).str.contains("SL", regex=False)
        s2 = trades["stage2_exit"].astype(str).str.contains("SL", regex=False)
        s3 = trades["stage3_exit"].astype(str).str.contains("SL", regex=False)
        out["any_stage_sl_count"] = int((s1 | s2 | s3).sum())
        out["all_stage_sl_count"] = int((s1 & s2 & s3).sum())
    if "mode" in trades.columns:
        out["mode_counts"] = "; ".join(f"{k}:{v}" for k, v in trades["mode"].value_counts().sort_index().items())
    return out


def normalize_mode(value: object) -> str:
    text = str(value)
    if "post_n" in text:
        return "post_n"
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    return text


def compare_variants_to_mt5(metrics: pd.DataFrame) -> pd.DataFrame:
    if not MT5_SIGNAL_CSV.exists():
        return pd.DataFrame()
    mt5 = pd.read_csv(MT5_SIGNAL_CSV, encoding="utf-8-sig")
    mt5["anchor_time"] = pd.to_datetime(mt5["anchor_time"])
    mt5["mode_norm_cmp"] = mt5["mode_norm"].map(normalize_mode)
    mt5_keys = set(zip(mt5["anchor_time"].astype(str), mt5["dir"], mt5["mode_norm_cmp"]))
    mt5_td = set(zip(mt5["anchor_time"].astype(str), mt5["dir"]))

    rows: list[dict[str, object]] = []
    for _, metric_row in metrics.iterrows():
        variant = str(metric_row["variant"])
        trade_path = OUT_ROOT / variant / "执行交易_Stage结果.csv"
        if not trade_path.exists():
            continue
        py = pd.read_csv(trade_path, encoding="utf-8-sig")
        py["date"] = pd.to_datetime(py["date"])
        py["mode_norm_cmp"] = py["mode"].map(normalize_mode)
        py = py.drop_duplicates(["date", "dir", "mode_norm_cmp"])
        py_keys = set(zip(py["date"].astype(str), py["dir"], py["mode_norm_cmp"]))
        py_td = set(zip(py["date"].astype(str), py["dir"]))
        best_strict = -1
        best_date_dir = -1
        best_offset = 0
        for offset in [-240, -180, -150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150, 180, 240]:
            shifted = py.copy()
            shifted["date_shifted"] = shifted["date"] + pd.Timedelta(minutes=offset)
            shifted_keys = set(zip(shifted["date_shifted"].astype(str), shifted["dir"], shifted["mode_norm_cmp"]))
            shifted_td = set(zip(shifted["date_shifted"].astype(str), shifted["dir"]))
            strict_shared = len(shifted_keys & mt5_keys)
            date_dir_shared = len(shifted_td & mt5_td)
            if (strict_shared, date_dir_shared) > (best_strict, best_date_dir):
                best_strict = strict_shared
                best_date_dir = date_dir_shared
                best_offset = offset
        rows.append(
            {
                "variant": variant,
                "python_signals": int(len(py_keys)),
                "mt5_signals": int(len(mt5_keys)),
                "strict_shared_offset0": int(len(py_keys & mt5_keys)),
                "date_dir_shared_offset0": int(len(py_td & mt5_td)),
                "best_strict_shared": int(best_strict),
                "best_date_dir_shared": int(best_date_dir),
                "best_python_offset_min": int(best_offset),
                "python_only_offset0": int(len(py_keys - mt5_keys)),
                "mt5_only_offset0": int(len(mt5_keys - py_keys)),
            }
        )
    return pd.DataFrame(rows)


def run_variant(df: pd.DataFrame, h2: pd.DataFrame, m15: pd.DataFrame, name: str, use_q2_early: bool) -> dict[str, object]:
    old_pct_lo, old_pct_hi = pct.SPEC_LO, pct.SPEC_HI
    old_bias55 = pct.BIAS_55_THRESHOLD
    old_m15_lo, old_m15_hi = m15t.SPEC_LO, m15t.SPEC_HI
    try:
        pct.SPEC_LO, pct.SPEC_HI = SPEC_LO, SPEC_HI
        pct.BIAS_55_THRESHOLD = BIAS55_THRESHOLD
        m15t.SPEC_LO, m15t.SPEC_HI = SPEC_LO, SPEC_HI
        m15t.df_global = df
        h2t.df_global = df

        if use_q2_early:
            pass_set, factor_map, pass_bars, early_bar_count = h2t.early_precompute(h2, df, 2, False)
        else:
            pass_set, factor_map = pct.precompute_h2(h2, df["date"].values)
            pass_bars = len(pass_set)
            early_bar_count = 0

        raw_df, accepted = combo.build_candidate_frames(df, pass_set, factor_map)
        m15_start = pd.Timestamp(m15["date"].min())
        pre_cov = accepted[pd.to_datetime(accepted["date"]) < m15_start].reset_index(drop=True)
        cov = accepted[pd.to_datetime(accepted["date"]) >= m15_start].reset_index(drop=True)

        cov_mod, changed = m15t.apply_replace_variant(
            cov,
            m15,
            m15t.choose_slot1_by_distance,
            "ea_slot1_replace",
            require_earlier=True,
            reanchor_stop_by_distance=True,
        )
        rejected_runtime = raw_df[
            (~raw_df["spec_pass"])
            & m15t.coverage_mask(raw_df, m15_start)
        ].copy()
        rescued, rescued_count = m15t.build_rescued_trades(
            rejected_runtime,
            m15,
            m15t.choose_slot1_by_distance,
            variant_name="ea_slot1_runtime_rescue",
            reanchor_stop_by_distance=True,
        )
        cov_merged = m15t.dedupe_anchor(cov_mod.to_dict("records") + rescued.to_dict("records"))
        final_acc = combo.combine_full_sample(pre_cov, cov_merged).sort_values("date").reset_index(drop=True)
        final_acc = cb.apply_m30_close_proxy(final_acc, df)
        threshold, picked = cb.apply_layer3_ea_executable(final_acc, h2, top_pct=TOP_PCT)
        picked_limited = apply_max_pos_3(picked)
        trades = s12.summarize_variant(df, picked_limited, STAGE1_R, STAGE2_TRAIL_R, STAGE2_FORCE_R)

        variant_dir = OUT_ROOT / name
        export_csv(raw_df, variant_dir / "raw_candidates.csv")
        export_csv(final_acc, variant_dir / "候选信号_Layer1_Layer2通过.csv")
        export_csv(picked_limited, variant_dir / "最终信号_Layer3入选.csv")
        export_csv(trades, variant_dir / "执行交易_Stage结果.csv")

        metrics: dict[str, object] = {
            "variant": name,
            "use_q2_early": use_q2_early,
            "mt5_time_shift_minutes": TIME_SHIFT_MINUTES,
            "m30_rows": int(len(df)),
            "h2_rows": int(len(h2)),
            "m15_rows": int(len(m15)),
            "layer1_pass_bars": int(pass_bars),
            "early_bar_count": int(early_bar_count),
            "raw_candidates": int(len(raw_df)),
            "accepted": int(len(final_acc)),
            "layer3_threshold": float(threshold) if not pd.isna(threshold) else "",
            "picked_before_maxpos": int(len(picked)),
            "picked_after_maxpos": int(len(picked_limited)),
            "m15_replace_changed": int(changed),
            "m15_rescued_count": int(rescued_count),
            "output_dir": str(variant_dir),
        }
        metrics.update(stage_stop_metrics(trades))
        return metrics
    finally:
        pct.SPEC_LO, pct.SPEC_HI = old_pct_lo, old_pct_hi
        pct.BIAS_55_THRESHOLD = old_bias55
        m15t.SPEC_LO, m15t.SPEC_HI = old_m15_lo, old_m15_hi


def build_report(metrics: pd.DataFrame, compare_df: pd.DataFrame) -> str:
    lines = [
        "# Python-MT5 shift90 重建报告（2026-07-12）",
        "",
        "## 口径说明",
        f"- MT5 bar export 来源：`{MT5_BAR_EXPORT}`",
        f"- M30 时间语义：`bar_time + {TIME_SHIFT_MINUTES}min`。",
        "- 输出目录为版本化目录 `黄金/30m2H策略/data/signals_mt5_shift90_20260712`，未覆盖旧 `signals_mt5`。",
        "- 本轮是诊断重建：同时测试 MT5 bar-level H2 与当前 Python decision H2，避免把 H2 时间语义误当成 M30 数据问题。",
        "",
        "## 指标摘要",
        "| variant | accepted | picked | trades | final_python_x5 | any_sl | all_sl | win_rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in metrics.iterrows():
        lines.append(
            f"| {row['variant']} | {int(row['accepted'])} | {int(row['picked_after_maxpos'])} | "
            f"{int(row['trade_rows'])} | {float(row.get('final_balance_python_multiplier5', 0.0)):.2f} | "
            f"{int(row.get('any_stage_sl_count', 0))} | {int(row.get('all_stage_sl_count', 0))} | "
            f"{float(row.get('win_rate_pct', 0.0)):.2f}% |"
        )
    if not compare_df.empty:
        lines.extend(
            [
                "",
                "## 与 MT5 EA 信号集合对比",
                "| variant | Python signals | MT5 signals | shared | Python-only | MT5-only | best offset |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for _, row in compare_df.iterrows():
            lines.append(
                f"| {row['variant']} | {int(row['python_signals'])} | {int(row['mt5_signals'])} | "
                f"{int(row['strict_shared_offset0'])} | {int(row['python_only_offset0'])} | "
                f"{int(row['mt5_only_offset0'])} | {int(row['best_python_offset_min'])}min |"
            )
    lines.extend(
        [
            "",
            "## 判断",
            "- `mt5_h2_barlevel_*` 总笔数接近 MT5 EA，但 shared 很低，不能作为对齐成功版本。",
            "- `python_h2_context_q2early` 的 shared 更高，说明 H2 decision context 仍比 bar-level H2 export 更接近当前 EA/Python 对齐口径。",
            "- 本报告只用于第 2 步重建诊断，不代表最终 MT5 EA ledger 对齐完成。",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    mt5 = load_mt5_export()
    mt5_m30 = build_m30_smma(mt5)
    h2 = build_h2_barlevel(mt5)
    df, _ = prepare(str(M30_RAW_CSV), min_len=8, mt5_smma=mt5_m30)
    m15 = m15t.load_m15()

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    export_csv(mt5_m30.reset_index(), OUT_ROOT / "m30_mt5_shift90_smma.csv")
    export_csv(h2, OUT_ROOT / "h2_mt5_barlevel_shift90_context.csv")
    export_csv(df, OUT_ROOT / "m30_prepared_with_mt5_shift90.csv")

    metrics = pd.DataFrame(
        [
            run_variant(df, h2, m15, "mt5_h2_barlevel_direct", use_q2_early=False),
            run_variant(df, h2, m15, "mt5_h2_barlevel_q2early", use_q2_early=True),
            run_variant(df, load_h2_context(), m15, "python_h2_context_q2early", use_q2_early=True),
        ]
    )
    export_csv(metrics, VALIDATION_DIR / "python_mt5_shift90_metrics_20260712.csv")
    compare_df = compare_variants_to_mt5(metrics)
    if not compare_df.empty:
        export_csv(compare_df, VALIDATION_DIR / "python_mt5_shift90_variants_vs_mt5_ea_summary_20260712.csv")
    report = build_report(metrics, compare_df)
    write_text(VALIDATION_DIR / "python_mt5_shift90_rebuild_report_20260712.md", report)
    print(report)


if __name__ == "__main__":
    main()
