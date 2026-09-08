from __future__ import annotations


from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_DIR = ROOT / "黄金" / "30m2H策略"
INPUT_DIR = STRATEGY_DIR / "data" / "validation" / "dynamic_risk_inputs_20260712"
LEDGER_DIR = STRATEGY_DIR / "data" / "validation" / "mt5_ledger_deinitfix_full_20260713_v1"
OUT_DIR = STRATEGY_DIR / "data" / "validation" / "dynamic_risk_alignment_magic0fix_20260713"

START_CAPITAL = 500.0
RISK_PCT = 3.0
MIN_LOT = 0.01
MAX_LOT = 10.0
LOT_STEP = 0.01
VALUE_PER_SPEC_PT_PER_LOT = 10.0


@dataclass(frozen=True)
class DynamicSource:
    name: str
    path: Path


DYNAMIC_SOURCES = [
    DynamicSource("python_only", INPUT_DIR / "python_only_dynamic_risk_inputs.csv"),
    DynamicSource("python_mt5", INPUT_DIR / "python_mt5_dynamic_risk_inputs.csv"),
]


def normalize_lots(lot: float) -> float:
    lot = max(MIN_LOT, min(MAX_LOT, lot))
    lot = (lot // LOT_STEP) * LOT_STEP
    if lot < MIN_LOT:
        lot = MIN_LOT
    return round(lot, 2)


def calc_total_lot(balance: float, stop_pts_mql5: float) -> float:
    if stop_pts_mql5 <= 0:
        return MIN_LOT
    risk = balance * RISK_PCT / 100.0
    pts_value = VALUE_PER_SPEC_PT_PER_LOT * (stop_pts_mql5 / 1000.0)
    if pts_value <= 0:
        return MIN_LOT
    return normalize_lots(risk / pts_value)


def calc_stage_lots(balance: float, stop_pts_mql5: float) -> tuple[float, float, float, float]:
    total_lot = calc_total_lot(balance, stop_pts_mql5)
    base_lot = total_lot / 3.0
    if base_lot < MIN_LOT:
        base_lot = MIN_LOT
    stage1 = normalize_lots(base_lot * 0.5)
    stage2 = normalize_lots(base_lot * 1.0)
    stage3 = normalize_lots(base_lot * 1.5)
    return total_lot, stage1, stage2, stage3


def mode_family(value: str) -> str:
    text = str(value)
    if "post_n" in text:
        return "post_n"
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    return text


def trigger_family_from_variant(value: str) -> str:
    text = str(value)
    if any(tag in text for tag in ["slot1", "replace", "rescue"]):
        return "M15 SLOT1"
    return "M30 CLOSE"


def trigger_family_from_tag(value: str) -> str:
    text = str(value).replace("[", "").replace("]", "").strip()
    if text.startswith("M15"):
        return "M15 SLOT1"
    if text.startswith("M30"):
        return "M30 CLOSE"
    return text


def simulate_dynamic_source(cfg: DynamicSource) -> tuple[pd.DataFrame, dict[str, object]]:
    df = pd.read_csv(cfg.path, encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    details: list[dict[str, object]] = []
    balance = START_CAPITAL

    for _, row in df.iterrows():
        total_lot, stage1_lot, stage2_lot, stage3_lot = calc_stage_lots(balance, float(row["stop_pts_mql5"]))
        stage1_dynamic = float(row["stage1_pnl"]) * stage1_lot * VALUE_PER_SPEC_PT_PER_LOT
        stage2_dynamic = float(row["stage2_pnl"]) * stage2_lot * VALUE_PER_SPEC_PT_PER_LOT
        stage3_dynamic = float(row["stage3_pnl"]) * stage3_lot * VALUE_PER_SPEC_PT_PER_LOT
        dynamic_total = stage1_dynamic + stage2_dynamic + stage3_dynamic
        balance_after = balance + dynamic_total

        details.append(
            {
                "source": cfg.name,
                "date": row["date"],
                "dir": row["dir"],
                "mode": row["mode"],
                "mode_family": mode_family(row["mode"]),
                "variant": row.get("variant", ""),
                "trigger_family": trigger_family_from_variant(row.get("variant", "")),
                "entry": row["entry"],
                "stop": row["stop"],
                "stop_pts_spec": row["stop_pts_spec"],
                "stop_pts_mql5": row["stop_pts_mql5"],
                "balance_before": round(balance, 6),
                "dynamic_total_lot": total_lot,
                "stage1_lot": stage1_lot,
                "stage2_lot": stage2_lot,
                "stage3_lot": stage3_lot,
                "stage1_dynamic_$": round(stage1_dynamic, 6),
                "stage2_dynamic_$": round(stage2_dynamic, 6),
                "stage3_dynamic_$": round(stage3_dynamic, 6),
                "dynamic_total_$": round(dynamic_total, 6),
                "balance_after": round(balance_after, 6),
                "fixed_total_$": row["total_$"],
                "fixed_equity_$": row["equity_$"],
                "stage1_exit": row["stage1_exit"],
                "stage2_exit": row["stage2_exit"],
                "stage3_exit": row["stage3_exit"],
            }
        )
        balance = balance_after

    out = pd.DataFrame(details)
    total_profit = float(out["dynamic_total_$"].sum()) if not out.empty else 0.0
    win_count = int((out["dynamic_total_$"] > 0).sum()) if not out.empty else 0
    any_sl_mask = (
        (out["stage1_exit"] == "SL hit")
        | out["stage2_exit"].astype(str).str.contains("SL", regex=False)
        | out["stage3_exit"].astype(str).str.contains("SL", regex=False)
    ) if not out.empty else pd.Series(dtype=bool)
    full_sl_mask = (
        (out["stage1_exit"] == "SL hit")
        & out["stage2_exit"].astype(str).str.contains("SL", regex=False)
        & out["stage3_exit"].astype(str).str.contains("SL", regex=False)
    ) if not out.empty else pd.Series(dtype=bool)

    summary = {
        "source": cfg.name,
        "trade_count": int(len(out)),
        "final_balance": round(START_CAPITAL + total_profit, 6),
        "dynamic_total_profit": round(total_profit, 6),
        "win_count": win_count,
        "win_rate_pct": round((win_count / len(out) * 100.0) if len(out) else 0.0, 4),
        "any_stage_sl_count": int(any_sl_mask.sum()) if not out.empty else 0,
        "all_stage_sl_count": int(full_sl_mask.sum()) if not out.empty else 0,
        "avg_stop_pts_spec": round(float(out["stop_pts_spec"].mean()), 6) if not out.empty else 0.0,
        "avg_total_lot": round(float(out["dynamic_total_lot"].mean()), 6) if not out.empty else 0.0,
    }
    return out, summary


def build_mt5_ledger_summary() -> tuple[pd.DataFrame, dict[str, object]]:
    ledger = pd.read_csv(LEDGER_DIR / "30m2H_strategy_trade_ledger.csv", encoding="utf-8-sig")
    ledger["signal_anchor_time"] = pd.to_datetime(ledger["signal_anchor_time"])
    ledger["open_time"] = pd.to_datetime(ledger["open_time"])
    ledger["exit_time"] = pd.to_datetime(ledger["exit_time"])
    for col in ["fill_price", "actual_stop", "lots", "stop_pts", "net_profit"]:
        ledger[col] = pd.to_numeric(ledger[col], errors="coerce")

    ledger["mode_family"] = ledger["signal_src"].map(mode_family)
    ledger["trigger_family"] = ledger["trigger_tag"].map(trigger_family_from_tag)

    key_cols = ["signal_anchor_time", "trigger_family", "mode_family", "dir"]
    rows: list[dict[str, object]] = []
    balance = START_CAPITAL

    for _, grp in ledger.sort_values(["signal_anchor_time", "stage"]).groupby(key_cols, sort=False):
        grp = grp.sort_values("stage")
        total_profit = float(grp["net_profit"].sum())
        balance_after = balance + total_profit
        stop_spec = float(grp["stop_pts"].iloc[0]) / 1000.0 if pd.notna(grp["stop_pts"].iloc[0]) else None
        rows.append(
            {
                "signal_anchor_time": grp["signal_anchor_time"].iloc[0],
                "trigger_family": grp["trigger_family"].iloc[0],
                "mode_family": grp["mode_family"].iloc[0],
                "dir": grp["dir"].iloc[0],
                "signal_src": grp["signal_src"].iloc[0],
                "stage_rows": int(len(grp)),
                "stage_list": ",".join(str(int(v)) for v in grp["stage"].tolist()),
                "lots_list": ",".join(f"{float(v):.2f}" for v in grp["lots"].tolist()),
                "stop_pts_spec": stop_spec,
                "net_profit": round(total_profit, 6),
                "balance_before": round(balance, 6),
                "balance_after": round(balance_after, 6),
                "any_sl": bool((grp["deal_reason"] == "SL").any()),
                "all_sl": bool((grp["deal_reason"] == "SL").all()),
                "local_exit_reasons": ";".join(sorted(set(grp["local_exit_reason"].astype(str)))),
                "deal_reasons": ";".join(sorted(set(grp["deal_reason"].astype(str)))),
            }
        )
        balance = balance_after

    out = pd.DataFrame(rows)
    total_profit = float(out["net_profit"].sum()) if not out.empty else 0.0
    win_count = int((out["net_profit"] > 0).sum()) if not out.empty else 0
    summary = {
        "source": "mt5_ledger",
        "trade_count": int(len(out)),
        "final_balance": round(START_CAPITAL + total_profit, 6),
        "dynamic_total_profit": round(total_profit, 6),
        "win_count": win_count,
        "win_rate_pct": round((win_count / len(out) * 100.0) if len(out) else 0.0, 4),
        "any_stage_sl_count": int(out["any_sl"].sum()) if not out.empty else 0,
        "all_stage_sl_count": int(out["all_sl"].sum()) if not out.empty else 0,
        "avg_stop_pts_spec": round(float(out["stop_pts_spec"].dropna().mean()), 6) if out["stop_pts_spec"].notna().any() else 0.0,
        "avg_total_lot": "",
    }
    return out, summary


def compare_key_overlap(py_df: pd.DataFrame, mt5_df: pd.DataFrame, source: str) -> pd.DataFrame:
    py_keys = py_df[["date", "trigger_family", "mode_family", "dir"]].copy()
    py_keys["key_status"] = "python"
    mt5_keys = mt5_df[["signal_anchor_time", "trigger_family", "mode_family", "dir"]].copy()
    mt5_keys = mt5_keys.rename(columns={"signal_anchor_time": "date"})
    mt5_keys["key_status"] = "mt5"

    merged = py_keys.merge(
        mt5_keys,
        on=["date", "trigger_family", "mode_family", "dir"],
        how="outer",
        indicator=True,
        suffixes=("_py", "_mt5"),
    )
    merged["source"] = source
    merged["match_status"] = merged["_merge"].map(
        {"both": "shared", "left_only": "python_only", "right_only": "mt5_only"}
    )
    return merged.drop(columns=["_merge"])


def write_script_and_data_indexes() -> None:
    script_index_lines = [
        "# Validate Scripts Index",
        "",
        "## Current Active Scripts",
        "- `prepare_dynamic_risk_inputs.py`: 把 Python `Layer3入选` 与 `Stage结果` 合并成动态风险输入底座。",
        "- `simulate_dynamic_risk_alignment.py`: 按 EA `CalcLot()/StageLots()` 近似公式重算 Python 动态风险资金曲线，并与 MT5 ledger 做主键层汇总对比。",
        "- `compare_python_vs_python_mt5_detail.py`: Python-only vs Python-MT5 原始数据、信号层、交易层详细 diff。",
        "- `diagnose_time_semantics.py`: 时间语义、原始数据同步、M15/M30/H2 映射诊断。",
        "- `compare_three_sources_layers.py`: Python-only / Python-MT5 / MT5-only 三来源分层总对比。",
        "",
        "## Current Active Output Dirs",
        "- `data/validation/dynamic_risk_inputs_20260712`",
        "- `data/validation/dynamic_risk_alignment_20260712`",
        "- `data/validation/mt5_trade_ledger_full_20260712`",
        "- `data/validation/python_only_vs_python_mt5_detail_20260712`",
        "- `data/validation/three_sources_layer_compare_20260712`",
    ]
    (STRATEGY_DIR / "scripts" / "validate" / "README.md").write_text(
        "\n".join(script_index_lines) + "\n",
        encoding="utf-8-sig",
    )

    data_index_lines = [
        "# Validation Data Index",
        "",
        "## Current Focus Snapshots",
        "- `mt5_trade_ledger_full_20260712`: 已验证的 MT5 full-run ledger 快照。",
        "- `dynamic_risk_inputs_20260712`: Python 动态风险输入底座。",
        "- `dynamic_risk_alignment_20260712`: Python 动态风险结果、MT5 ledger 汇总、key overlap 对比。",
        "- `python_only_vs_python_mt5_detail_20260712`: Python-only vs Python-MT5 逐层 diff。",
        "- `three_sources_layer_compare_20260712`: 三来源总对比。",
        "",
        "## Notes",
        "- 这些目录都是版本化快照，不覆盖旧实验目录。",
        "- 当前主线比较顺序固定为：数据 -> 信号 -> ledger -> 资金曲线。",
    ]
    (STRATEGY_DIR / "data" / "validation" / "README_20260712.md").write_text(
        "\n".join(data_index_lines) + "\n",
        encoding="utf-8-sig",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    dynamic_summaries: list[dict[str, object]] = []
    detail_frames: dict[str, pd.DataFrame] = {}
    overlap_frames: list[pd.DataFrame] = []

    mt5_df, mt5_summary = build_mt5_ledger_summary()
    mt5_df.to_csv(OUT_DIR / "mt5_ledger_unique_signals.csv", index=False, encoding="utf-8-sig")

    for cfg in DYNAMIC_SOURCES:
        detail_df, summary = simulate_dynamic_source(cfg)
        detail_frames[cfg.name] = detail_df
        dynamic_summaries.append(summary)
        detail_df.to_csv(OUT_DIR / f"{cfg.name}_dynamic_risk_trades.csv", index=False, encoding="utf-8-sig")
        overlap = compare_key_overlap(detail_df, mt5_df, cfg.name)
        overlap_frames.append(overlap)
        overlap.to_csv(OUT_DIR / f"{cfg.name}_vs_mt5_ledger_key_overlap.csv", index=False, encoding="utf-8-sig")

    summary_df = pd.DataFrame(dynamic_summaries + [mt5_summary])
    summary_df.to_csv(OUT_DIR / "dynamic_risk_compare_summary.csv", index=False, encoding="utf-8-sig")

    overlap_summary_rows: list[dict[str, object]] = []
    for overlap in overlap_frames:
        source = overlap["source"].iloc[0] if not overlap.empty else ""
        counts = overlap["match_status"].value_counts()
        overlap_summary_rows.append(
            {
                "source": source,
                "shared": int(counts.get("shared", 0)),
                "python_only": int(counts.get("python_only", 0)),
                "mt5_only": int(counts.get("mt5_only", 0)),
            }
        )
    overlap_summary_df = pd.DataFrame(overlap_summary_rows)
    overlap_summary_df.to_csv(OUT_DIR / "dynamic_risk_key_overlap_summary.csv", index=False, encoding="utf-8-sig")

    report_lines = [
        "# Dynamic Risk Alignment",
        "",
        "## Summary",
        summary_df.to_markdown(index=False),
        "",
        "## Key Overlap",
        overlap_summary_df.to_markdown(index=False) if not overlap_summary_df.empty else "No overlap rows.",
        "",
        "## Interpretation",
        "- `python_only` / `python_mt5` 动态风险版目前仍沿用 Python 信号集合，只是把固定 `total_$ * 5` 改成了按 EA 风格的动态手数近似。",
        "- `mt5_ledger` 侧统计的是已成交并完成 close 的唯一信号，不等于 EA 日志里的全部信号触发。",
        "- 因此这里的主键 overlap 更适合作为“可比成交集合”的第一轮诊断，而不是最终对齐结论。",
        "",
        "## Output Files",
        "- `python_only_dynamic_risk_trades.csv`",
        "- `python_mt5_dynamic_risk_trades.csv`",
        "- `mt5_ledger_unique_signals.csv`",
        "- `dynamic_risk_compare_summary.csv`",
        "- `dynamic_risk_key_overlap_summary.csv`",
    ]
    (OUT_DIR / "dynamic_risk_alignment_report.md").write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8-sig",
    )

    write_script_and_data_indexes()


if __name__ == "__main__":
    main()
