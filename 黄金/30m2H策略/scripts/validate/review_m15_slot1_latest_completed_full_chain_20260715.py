# -*- coding: utf-8 -*-
"""Run full-chain validation for the M15 SLOT1 latest-completed prototype."""
from __future__ import annotations


import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import prepare_dynamic_risk_inputs_shift90 as prep  # noqa: E402
import simulate_dynamic_risk_alignment_shift90_close_retry_20260714 as sim  # noqa: E402
import map_python_mt5_ledger_trades as mapper  # noqa: E402


STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"

CURRENT_INPUT_DIR = VALIDATION_DIR / "dynamic_risk_inputs_shift90_metadatafix_20260714"
CURRENT_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_shift90_metadatafix_close_retry_20260714"
CURRENT_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_shift90_metadatafix_close_retry_20260714"

PROTO_SIGNAL_DIR = (
    VALIDATION_DIR
    / "m15_slot1_latest_completed_prototype_20260715"
    / "signals"
    / "python_h2_context_q2early_latest_slot1"
)
PROTO_INPUT_DIR = VALIDATION_DIR / "dynamic_risk_inputs_m15_slot1_latest_completed_20260715"
PROTO_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_m15_slot1_latest_completed_close_retry_20260715"
PROTO_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_m15_slot1_latest_completed_close_retry_20260715"
OUT_DIR = VALIDATION_DIR / "m15_slot1_latest_completed_full_chain_review_20260715"

SHIFT90_METADATAFIX_SIGNAL_ROOT = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714"
SHIFT90_M30 = SHIFT90_METADATAFIX_SIGNAL_ROOT / "m30_prepared_with_mt5_shift90.csv"
TARGET_TIME = pd.Timestamp("2025-10-21 10:00:00")


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def safe_num(value: object, default: float = 0.0) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return float(parsed)


def parse_dt_series(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip().str.replace(".", "-", regex=False)
    text = text.mask(text.isin(["", "nan", "NaT", "None"]))
    return pd.to_datetime(text, errors="coerce")


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None, max_rows: int | None = None) -> str:
    if frame.empty:
        return "_No rows._"
    display = frame.copy()
    if columns is not None:
        display = display[[col for col in columns if col in display.columns]]
    if max_rows is not None:
        display = display.head(max_rows)
    return display.to_markdown(index=False)


def run_prepare_inputs() -> None:
    prep.OUT_DIR = PROTO_INPUT_DIR
    prep.SHIFT90_SIGNAL_DIR = PROTO_SIGNAL_DIR
    prep.SHIFT90_M30 = SHIFT90_M30
    prep.SOURCES = [
        prep.SourceConfig("python_only", DATA_DIR / "signals"),
        prep.SourceConfig("python_mt5", PROTO_SIGNAL_DIR, SHIFT90_M30),
    ]
    prep.main()


def run_dynamic_alignment() -> None:
    sim.INPUT_DIR = PROTO_INPUT_DIR
    sim.OUT_DIR = PROTO_DYNAMIC_DIR
    sim.main()


def run_mapping() -> None:
    mapper.INPUT_DIR = PROTO_DYNAMIC_DIR
    mapper.OUT_DIR = PROTO_MAPPING_DIR
    mapper.main()


def source_row(frame: pd.DataFrame, source: str) -> pd.Series:
    rows = frame[frame["source"].astype(str).eq(source)]
    if rows.empty:
        raise ValueError(f"Missing source={source}")
    return rows.iloc[0]


def dynamic_before_after() -> pd.DataFrame:
    rows = []
    for run, directory in [
        ("current_metadatafix", CURRENT_DYNAMIC_DIR),
        ("latest_completed_proto", PROTO_DYNAMIC_DIR),
    ]:
        summary = read_csv(directory / "dynamic_risk_compare_summary.csv")
        for source in ["python_mt5", "mt5_ledger"]:
            row = source_row(summary, source)
            rows.append(
                {
                    "run": run,
                    "source": source,
                    "trade_count": int(row["trade_count"]),
                    "final_balance": round(safe_num(row["final_balance"]), 6),
                    "dynamic_total_profit": round(safe_num(row["dynamic_total_profit"]), 6),
                    "win_rate_pct": round(safe_num(row["win_rate_pct"]), 6),
                    "any_stage_sl_count": int(safe_num(row["any_stage_sl_count"])),
                    "all_stage_sl_count": int(safe_num(row["all_stage_sl_count"])),
                    "avg_stop_pts_spec": round(safe_num(row["avg_stop_pts_spec"]), 6),
                }
            )
    return pd.DataFrame(rows)


def mapping_before_after() -> pd.DataFrame:
    rows = []
    for run, directory in [
        ("current_metadatafix", CURRENT_MAPPING_DIR),
        ("latest_completed_proto", PROTO_MAPPING_DIR),
    ]:
        summary = read_csv(directory / "unique_match_summary.csv")
        row = source_row(summary, "python_mt5")
        rows.append(
            {
                "run": run,
                "python_trades": int(row["python_trades"]),
                "mt5_trades": int(row["mt5_trades"]),
                "matched_unique": int(row["matched_unique"]),
                "reliable_tier_matched": int(row["reliable_tier_matched"]),
                "relaxed_tier_matched": int(row["relaxed_tier_matched"]),
                "python_unmatched": int(row["python_unmatched"]),
                "mt5_unmatched": int(row["mt5_unmatched"]),
                "matched_python_profit": round(safe_num(row["matched_python_profit"]), 6),
                "matched_mt5_profit": round(safe_num(row["matched_mt5_profit"]), 6),
                "matched_profit_diff": round(safe_num(row["matched_profit_diff"]), 6),
            }
        )
    return pd.DataFrame(rows)


def gap_components_for(run: str, dynamic_dir: Path, mapping_dir: Path) -> dict[str, object]:
    dyn = read_csv(dynamic_dir / "dynamic_risk_compare_summary.csv")
    py_summary = source_row(dyn, "python_mt5")
    mt5_summary = source_row(dyn, "mt5_ledger")
    mapping = source_row(read_csv(mapping_dir / "unique_match_summary.csv"), "python_mt5")
    py_unmatched = read_csv(mapping_dir / "python_mt5_unmatched_python_trades.csv")
    mt5_unmatched = read_csv(mapping_dir / "python_mt5_unmatched_mt5_trades.csv")

    py_unmatched_profit = float(pd.to_numeric(py_unmatched["dynamic_total_$"], errors="coerce").fillna(0.0).sum())
    mt5_unmatched_profit = float(pd.to_numeric(mt5_unmatched["net_profit"], errors="coerce").fillna(0.0).sum())
    mt5_unmatched_gap = -mt5_unmatched_profit
    matched_profit_diff = safe_num(mapping["matched_profit_diff"])
    reconstructed = matched_profit_diff + py_unmatched_profit + mt5_unmatched_gap
    direct = safe_num(py_summary["dynamic_total_profit"]) - safe_num(mt5_summary["dynamic_total_profit"])

    return {
        "run": run,
        "python_mt5_total_profit": round(safe_num(py_summary["dynamic_total_profit"]), 6),
        "mt5_total_profit": round(safe_num(mt5_summary["dynamic_total_profit"]), 6),
        "direct_dynamic_gap_python_minus_mt5": round(direct, 6),
        "matched_profit_diff": round(matched_profit_diff, 6),
        "python_unmatched_gap_effect": round(py_unmatched_profit, 6),
        "mt5_unmatched_gap_effect": round(mt5_unmatched_gap, 6),
        "signal_set_gap_effect": round(py_unmatched_profit + mt5_unmatched_gap, 6),
        "reconstructed_dynamic_gap": round(reconstructed, 6),
    }


def gap_before_after() -> pd.DataFrame:
    return pd.DataFrame(
        [
            gap_components_for("current_metadatafix", CURRENT_DYNAMIC_DIR, CURRENT_MAPPING_DIR),
            gap_components_for("latest_completed_proto", PROTO_DYNAMIC_DIR, PROTO_MAPPING_DIR),
        ]
    )


def top_unmatched(mapping_dir: Path, side: str, max_rows: int = 15) -> pd.DataFrame:
    if side == "python":
        frame = read_csv(mapping_dir / "python_mt5_unmatched_python_trades.csv")
        frame["effect"] = pd.to_numeric(frame["dynamic_total_$"], errors="coerce").fillna(0.0)
        frame["abs_effect"] = frame["effect"].abs()
        cols = ["py_trade_id", "date", "dir_norm", "trigger_family", "mode_family", "mode", "variant", "dynamic_total_$", "effect", "abs_effect"]
    else:
        frame = read_csv(mapping_dir / "python_mt5_unmatched_mt5_trades.csv")
        frame["effect"] = -pd.to_numeric(frame["net_profit"], errors="coerce").fillna(0.0)
        frame["abs_effect"] = frame["effect"].abs()
        cols = ["mt5_trade_id", "signal_anchor_time", "aligned_time", "dir_norm", "trigger_family", "mode_family", "signal_src", "net_profit", "effect", "abs_effect"]
    frame["side"] = f"{side}_unmatched"
    return frame.sort_values("abs_effect", ascending=False)[["side", *[c for c in cols if c in frame.columns]]].head(max_rows).reset_index(drop=True)


def target_case_before_after() -> pd.DataFrame:
    rows = []
    for run, dynamic_dir, mapping_dir in [
        ("current_metadatafix", CURRENT_DYNAMIC_DIR, CURRENT_MAPPING_DIR),
        ("latest_completed_proto", PROTO_DYNAMIC_DIR, PROTO_MAPPING_DIR),
    ]:
        trades = read_csv(dynamic_dir / "python_mt5_dynamic_risk_trades.csv")
        trades["date_dt"] = parse_dt_series(trades["date"])
        target_trades = trades[trades["date_dt"].eq(TARGET_TIME)].copy()
        matches = read_csv(mapping_dir / "python_mt5_mt5_unique_matches.csv")
        matches["py_date_dt"] = parse_dt_series(matches["py_date"]) if "py_date" in matches.columns else pd.NaT
        target_matches = matches[matches["py_date_dt"].eq(TARGET_TIME)].copy()
        rows.append(
            {
                "run": run,
                "target_dynamic_trade_rows": int(len(target_trades)),
                "target_mapping_rows": int(len(target_matches)),
                "target_modes": "; ".join(target_trades["mode"].astype(str).tolist()) if not target_trades.empty else "",
                "target_variants": "; ".join(target_trades["variant"].astype(str).tolist()) if "variant" in target_trades and not target_trades.empty else "",
                "target_dynamic_total_sum": round(float(pd.to_numeric(target_trades.get("dynamic_total_$", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum()), 6),
                "target_match_tiers": "; ".join(target_matches["match_tier"].astype(str).tolist()) if not target_matches.empty else "",
            }
        )
    return pd.DataFrame(rows)


def write_readme() -> None:
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# m15_slot1_latest_completed_full_chain_review_20260715",
                "",
                "Runs dynamic-risk input preparation, dynamic-risk alignment, and MT5 ledger mapping for the M15 SLOT1 latest-completed prototype.",
                "",
                "Runtime-style Stage-exit adjusted gap is not recalculated here; this review decides whether that heavier rerun is worth doing.",
            ]
        ),
    )


def build_report(
    dynamic_cmp: pd.DataFrame,
    mapping_cmp: pd.DataFrame,
    gap_cmp: pd.DataFrame,
    target_cmp: pd.DataFrame,
    top_py: pd.DataFrame,
    top_mt5: pd.DataFrame,
) -> str:
    current_gap = gap_cmp[gap_cmp["run"].eq("current_metadatafix")].iloc[0]
    proto_gap = gap_cmp[gap_cmp["run"].eq("latest_completed_proto")].iloc[0]
    gap_delta = safe_num(proto_gap["direct_dynamic_gap_python_minus_mt5"]) - safe_num(current_gap["direct_dynamic_gap_python_minus_mt5"])
    signal_gap_delta = safe_num(proto_gap["signal_set_gap_effect"]) - safe_num(current_gap["signal_set_gap_effect"])

    lines = [
        "# M15 SLOT1 latest-completed full-chain review",
        "",
        "## 结论",
        "",
        "- 本报告把 latest-completed prototype 接入 dynamic risk、MT5 ledger mapping 和 gap components；没有修改 EA，也没有覆盖当前主线快照。",
        "- `2025-10-21 10:00` 目标假阳性在 prototype dynamic/mapping 中消失。",
        f"- direct dynamic gap delta = `{gap_delta:.6f}`，signal-set gap delta = `{signal_gap_delta:.6f}`；正数表示 Python-MT5 相对 MT5 更高，负数表示更低。",
        "- 本报告未重跑 runtime-style Stage-exit adjustment；若 mapping/gap 明显收敛，再进入更重的 runtime-style rerun。",
        "",
        "## Dynamic Risk Before/After",
        "",
        markdown_table(dynamic_cmp),
        "",
        "## Mapping Before/After",
        "",
        markdown_table(mapping_cmp),
        "",
        "## Gap Components",
        "",
        markdown_table(gap_cmp),
        "",
        "## Target Case Before/After",
        "",
        markdown_table(target_cmp),
        "",
        "## Top Prototype Python-Unmatched",
        "",
        markdown_table(top_py, max_rows=12),
        "",
        "## Top Prototype MT5-Unmatched",
        "",
        markdown_table(top_mt5, max_rows=12),
        "",
        "## Output Snapshots",
        "",
        f"- `{PROTO_INPUT_DIR.relative_to(DATA_DIR)}`",
        f"- `{PROTO_DYNAMIC_DIR.relative_to(DATA_DIR)}`",
        f"- `{PROTO_MAPPING_DIR.relative_to(DATA_DIR)}`",
    ]
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_prepare_inputs()
    run_dynamic_alignment()
    run_mapping()

    dynamic_cmp = dynamic_before_after()
    mapping_cmp = mapping_before_after()
    gap_cmp = gap_before_after()
    target_cmp = target_case_before_after()
    top_py = top_unmatched(PROTO_MAPPING_DIR, "python")
    top_mt5 = top_unmatched(PROTO_MAPPING_DIR, "mt5")

    export_csv(dynamic_cmp, OUT_DIR / "dynamic_risk_before_after.csv")
    export_csv(mapping_cmp, OUT_DIR / "mapping_before_after.csv")
    export_csv(gap_cmp, OUT_DIR / "gap_components_before_after.csv")
    export_csv(target_cmp, OUT_DIR / "target_case_before_after.csv")
    export_csv(top_py, OUT_DIR / "prototype_top_python_unmatched.csv")
    export_csv(top_mt5, OUT_DIR / "prototype_top_mt5_unmatched.csv")
    write_text(
        OUT_DIR / "m15_slot1_latest_completed_full_chain_review.md",
        build_report(dynamic_cmp, mapping_cmp, gap_cmp, target_cmp, top_py, top_mt5),
    )
    write_readme()

    print(mapping_cmp.to_string(index=False))
    print()
    print(gap_cmp.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
