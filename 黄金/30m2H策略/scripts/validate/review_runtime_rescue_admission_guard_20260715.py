# -*- coding: utf-8 -*-
"""Prototype admission guards for Python-MT5 ea_slot1_runtime_rescue.

The goal is to test Python-side fixes for far-candidate runtime_rescue false
positives without changing EA behavior or overwriting the current metadatafix
signal snapshot.
"""
from __future__ import annotations


import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(SCRIPT_DIR))

import prepare_dynamic_risk_inputs_shift90 as prep  # noqa: E402
import simulate_dynamic_risk_alignment_shift90_close_retry_20260714 as sim  # noqa: E402
import map_python_mt5_ledger_trades as mapper  # noqa: E402


STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"

CURRENT_SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "python_h2_context_q2early"
CURRENT_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_shift90_metadatafix_close_retry_20260714"
CURRENT_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_shift90_metadatafix_close_retry_20260714"

OUT_DIR = VALIDATION_DIR / "runtime_rescue_admission_guard_full_chain_review_20260715"
PROTO_SIGNAL_ROOT = OUT_DIR / "signals"
PROTO_INPUT_ROOT = VALIDATION_DIR / "dynamic_risk_inputs_runtime_rescue_admission_guard_20260715"
PROTO_DYNAMIC_ROOT = VALIDATION_DIR / "dynamic_risk_alignment_runtime_rescue_admission_guard_20260715"
PROTO_MAPPING_ROOT = VALIDATION_DIR / "mapped_trade_alignment_runtime_rescue_admission_guard_20260715"
SHIFT90_M30 = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "m30_prepared_with_mt5_shift90.csv"

TARGET_20251017 = pd.Timestamp("2025-10-17 11:00:00")
TARGET_20251021 = pd.Timestamp("2025-10-21 10:00:00")
SPEC_LO = 5.0
SPEC_HI = 35.0
PRE_GAP_PCT = 0.300


@dataclass(frozen=True)
class GuardConfig:
    name: str
    wide_only: bool = False
    stop_side_valid: bool = False
    require_m15_mode: bool = False


GUARDS = [
    GuardConfig("python_h2_context_q2early_runtime_rescue_wide_only", wide_only=True),
    GuardConfig("python_h2_context_q2early_no_stop_side_mirror", stop_side_valid=True),
    GuardConfig("python_h2_context_q2early_require_selected_m15_mode", require_m15_mode=True),
    GuardConfig(
        "python_h2_context_q2early_combined_runtime_guard",
        wide_only=True,
        stop_side_valid=True,
        require_m15_mode=True,
    ),
]


def load_module_from_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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


def build_m15_mode_map(m15: pd.DataFrame) -> dict[pd.Timestamp, dict[str, int]]:
    df = m15.copy().sort_values("date").reset_index(drop=True)
    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    df["prev_close"] = df["close"].shift(1)
    df["prev_sma5"] = df["SMA_5"].shift(1)
    df["prev_sma13"] = df["SMA_13"].shift(1)
    df["gap_pct"] = (df["SMA_5"] - df["SMA_13"]).abs() / df["SMA_13"] * 100.0
    df["sma5_prev_above"] = df["prev_sma5"] > df["prev_sma13"]
    df["sma5_curr_above"] = df["SMA_5"] > df["SMA_13"]
    df["sma5_crosses"] = df["sma5_prev_above"] != df["sma5_curr_above"]
    long_pre = (
        (df["gap_pct"] <= PRE_GAP_PCT)
        & (~df["sma5_crosses"])
        & (df["prev_close"] <= df["prev_sma13"])
        & (df["close"] > df["SMA_13"])
        & (df["SMA_5"] < df["SMA_13"])
    )
    short_pre = (
        (df["gap_pct"] <= PRE_GAP_PCT)
        & (~df["sma5_crosses"])
        & (df["prev_close"] >= df["prev_sma13"])
        & (df["close"] < df["SMA_13"])
        & (df["SMA_5"] > df["SMA_13"])
    )
    df["pre_cross_dir"] = 0
    df.loc[long_pre, "pre_cross_dir"] = 1
    df.loc[short_pre, "pre_cross_dir"] = -1
    df["cross_dir"] = 0
    df.loc[df["sma5_crosses"] & df["sma5_curr_above"], "cross_dir"] = 1
    df.loc[df["sma5_crosses"] & (~df["sma5_curr_above"]), "cross_dir"] = -1

    out: dict[pd.Timestamp, dict[str, int]] = {}
    for _, row in df.iterrows():
        if pd.isna(row["date_dt"]):
            continue
        out[pd.Timestamp(row["date_dt"])] = {
            "pre_cross_dir": int(row["pre_cross_dir"]),
            "cross_dir": int(row["cross_dir"]),
        }
    return out


def stop_side_is_valid(is_long: bool, entry: float, stop: float) -> bool:
    if is_long:
        return stop < entry
    return stop > entry


def choose_slot1_stopside_by_distance(m15t, seg: pd.DataFrame, is_long: bool, stop: float):
    if len(seg) == 0:
        return None
    row = seg.iloc[0]
    entry = float(row["close"])
    sd = abs(entry - stop)
    if not stop_side_is_valid(is_long, entry, stop):
        return None
    if not m15t.m15_same_side(row, is_long):
        return None
    if not (m15t.SPEC_LO <= sd <= m15t.SPEC_HI):
        return None
    return row


def selected_m15_mode_ok(trade: pd.Series, chosen: pd.Series, mode_map: dict[pd.Timestamp, dict[str, int]]) -> bool:
    mode = str(trade.get("mode", ""))
    direction = 1 if str(trade.get("dir", "")).upper().startswith("L") else -1
    chosen_time = pd.Timestamp(chosen["date"])
    modes = mode_map.get(chosen_time, {"pre_cross_dir": 0, "cross_dir": 0})
    if mode == "pre_cross":
        return modes["pre_cross_dir"] == direction
    if mode == "cross":
        return modes["cross_dir"] == direction
    # EA M15 post_n uses the global merged post_n counter; this prototype does
    # not reconstruct that lifecycle here, so post_n rows are left to other guards.
    return True


def make_guarded_build_rescued(original_build, m15t, config: GuardConfig, mode_map):
    def guarded_build_rescued(
        rejected: pd.DataFrame,
        m15: pd.DataFrame,
        chooser,
        variant_name: str = "m15_rescue_stop",
        reanchor_stop_by_distance: bool = False,
    ):
        if config.wide_only and "spec_reason" in rejected.columns:
            rejected_work = rejected[rejected["spec_reason"].astype(str).eq("too_wide")].copy()
        else:
            rejected_work = rejected.copy()

        rows = []
        rescue_count = 0
        for _, trade in rejected_work.iterrows():
            is_long = str(trade.get("dir", "")).upper().startswith("L")
            stop = float(trade["stop"])
            seg = m15t.m15_window(m15, trade["date"])
            if config.stop_side_valid:
                chosen = choose_slot1_stopside_by_distance(m15t, seg, is_long, stop)
            else:
                chosen = chooser(seg, is_long, stop)
            if chosen is None:
                continue
            if config.require_m15_mode and not selected_m15_mode_ok(trade, chosen, mode_map):
                continue
            row = trade.to_dict()
            row = m15t.recalc_trade(
                row,
                pd.Timestamp(chosen["date"]),
                float(chosen["close"]),
                variant_name,
                m15,
                reanchor_stop_by_distance=reanchor_stop_by_distance,
            )
            row = m15t.finalize_trade(m15t.df_global, row, m15) if pd.isna(row["pnl"]) else row
            rows.append(row)
            rescue_count += 1
        out = pd.DataFrame(rows)
        return out, rescue_count

    return guarded_build_rescued


def generate_guarded_signals() -> pd.DataFrame:
    rebuild = load_module_from_path(
        "rebuild_python_mt5_shift90_runtime_rescue_guard",
        STRATEGY_DIR / "scripts" / "signals" / "rebuild_python_mt5_shift90.py",
    )
    m15t = rebuild.m15t
    old_out_root = rebuild.OUT_ROOT
    old_build_rescued = m15t.build_rescued_trades

    try:
        rebuild.OUT_ROOT = PROTO_SIGNAL_ROOT
        mt5 = rebuild.load_mt5_export()
        mt5_m30 = rebuild.build_m30_smma(mt5)
        df, _ = rebuild.prepare(str(rebuild.M30_RAW_CSV), min_len=8, mt5_smma=mt5_m30)
        m15 = m15t.load_m15()
        h2 = rebuild.load_h2_context()
        mode_map = build_m15_mode_map(m15)
        PROTO_SIGNAL_ROOT.mkdir(parents=True, exist_ok=True)
        metrics = []
        for config in GUARDS:
            m15t.build_rescued_trades = make_guarded_build_rescued(old_build_rescued, m15t, config, mode_map)
            metrics.append(
                rebuild.run_variant(
                    df,
                    h2,
                    m15,
                    config.name,
                    use_q2_early=True,
                )
            )
    finally:
        rebuild.OUT_ROOT = old_out_root
        m15t.build_rescued_trades = old_build_rescued
    return pd.DataFrame(metrics)


def run_prepare_inputs(variant: str) -> Path:
    input_dir = PROTO_INPUT_ROOT / variant
    signal_dir = PROTO_SIGNAL_ROOT / variant
    prep.OUT_DIR = input_dir
    prep.SHIFT90_SIGNAL_DIR = signal_dir
    prep.SHIFT90_M30 = SHIFT90_M30
    prep.SOURCES = [
        prep.SourceConfig("python_only", DATA_DIR / "signals"),
        prep.SourceConfig("python_mt5", signal_dir, SHIFT90_M30),
    ]
    prep.main()
    return input_dir


def run_dynamic_alignment(variant: str, input_dir: Path) -> Path:
    dynamic_dir = PROTO_DYNAMIC_ROOT / variant
    sim.INPUT_DIR = input_dir
    sim.OUT_DIR = dynamic_dir
    sim.main()
    return dynamic_dir


def run_mapping(variant: str, dynamic_dir: Path) -> Path:
    mapping_dir = PROTO_MAPPING_ROOT / variant
    mapper.INPUT_DIR = dynamic_dir
    mapper.OUT_DIR = mapping_dir
    mapper.main()
    return mapping_dir


def source_row(frame: pd.DataFrame, source: str) -> pd.Series:
    rows = frame[frame["source"].astype(str).eq(source)]
    if rows.empty:
        raise ValueError(f"Missing source={source}")
    return rows.iloc[0]


def dynamic_summary_for(run: str, dynamic_dir: Path) -> list[dict[str, object]]:
    summary = read_csv(dynamic_dir / "dynamic_risk_compare_summary.csv")
    rows = []
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
    return rows


def mapping_summary_for(run: str, mapping_dir: Path) -> dict[str, object]:
    row = source_row(read_csv(mapping_dir / "unique_match_summary.csv"), "python_mt5")
    return {
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
    direct = safe_num(py_summary["dynamic_total_profit"]) - safe_num(mt5_summary["dynamic_total_profit"])
    reconstructed = matched_profit_diff + py_unmatched_profit + mt5_unmatched_gap
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


def invalid_spec_counts_for(run: str, signal_dir: Path, dynamic_dir: Path) -> dict[str, object]:
    def count_invalid(frame: pd.DataFrame) -> int:
        if not {"entry", "stop"}.issubset(frame.columns):
            return 0
        entry = pd.to_numeric(frame["entry"], errors="coerce")
        stop = pd.to_numeric(frame["stop"], errors="coerce")
        sd = (entry - stop).abs()
        return int((sd.notna() & ~sd.between(SPEC_LO, SPEC_HI, inclusive="both")).sum())

    accepted = read_csv(signal_dir / "候选信号_Layer1_Layer2通过.csv")
    picked = read_csv(signal_dir / "最终信号_Layer3入选.csv")
    dynamic = read_csv(dynamic_dir / "python_mt5_dynamic_risk_trades.csv")
    return {
        "run": run,
        "accepted_invalid_spec_rows": count_invalid(accepted),
        "picked_invalid_spec_rows": count_invalid(picked),
        "dynamic_invalid_spec_rows": count_invalid(dynamic),
    }


def target_cases_for(run: str, dynamic_dir: Path, mapping_dir: Path) -> list[dict[str, object]]:
    trades = read_csv(dynamic_dir / "python_mt5_dynamic_risk_trades.csv")
    trades["date_dt"] = parse_dt_series(trades["date"])
    matches = read_csv(mapping_dir / "python_mt5_mt5_unique_matches.csv")
    if "py_date" in matches.columns:
        matches["py_date_dt"] = parse_dt_series(matches["py_date"])
    else:
        matches["py_date_dt"] = pd.NaT

    rows = []
    for label, target in [("target_20251017_no_signal_dir", TARGET_20251017), ("target_20251021_spec_fail", TARGET_20251021)]:
        target_trades = trades[trades["date_dt"].eq(target)].copy()
        target_matches = matches[matches["py_date_dt"].eq(target)].copy()
        rows.append(
            {
                "run": run,
                "target": label,
                "target_time": target.strftime("%Y-%m-%d %H:%M:%S"),
                "dynamic_trade_rows": int(len(target_trades)),
                "mapping_rows": int(len(target_matches)),
                "modes": "; ".join(target_trades["mode"].astype(str).tolist()) if not target_trades.empty else "",
                "variants": "; ".join(target_trades["variant"].astype(str).tolist()) if "variant" in target_trades.columns and not target_trades.empty else "",
                "dynamic_total_sum": round(float(pd.to_numeric(target_trades.get("dynamic_total_$", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum()), 6),
                "match_tiers": "; ".join(target_matches["match_tier"].astype(str).tolist()) if not target_matches.empty else "",
            }
        )
    return rows


def build_decision_matrix(dynamic_cmp: pd.DataFrame, mapping_cmp: pd.DataFrame, gap_cmp: pd.DataFrame, target_cmp: pd.DataFrame, invalid_cmp: pd.DataFrame) -> pd.DataFrame:
    current_dyn = dynamic_cmp[(dynamic_cmp["run"].eq("current_metadatafix")) & (dynamic_cmp["source"].eq("python_mt5"))].iloc[0]
    current_map = mapping_cmp[mapping_cmp["run"].eq("current_metadatafix")].iloc[0]
    current_gap = gap_cmp[gap_cmp["run"].eq("current_metadatafix")].iloc[0]
    current_invalid = invalid_cmp[invalid_cmp["run"].eq("current_metadatafix")].iloc[0]

    rows = []
    for run in [g.name for g in GUARDS]:
        dyn = dynamic_cmp[(dynamic_cmp["run"].eq(run)) & (dynamic_cmp["source"].eq("python_mt5"))].iloc[0]
        mp = mapping_cmp[mapping_cmp["run"].eq(run)].iloc[0]
        gap = gap_cmp[gap_cmp["run"].eq(run)].iloc[0]
        invalid = invalid_cmp[invalid_cmp["run"].eq(run)].iloc[0]
        target17 = target_cmp[(target_cmp["run"].eq(run)) & (target_cmp["target"].eq("target_20251017_no_signal_dir"))].iloc[0]
        target21 = target_cmp[(target_cmp["run"].eq(run)) & (target_cmp["target"].eq("target_20251021_spec_fail"))].iloc[0]
        rows.append(
            {
                "run": run,
                "target_20251017_removed": int(target17["dynamic_trade_rows"]) == 0,
                "target_20251021_removed": int(target21["dynamic_trade_rows"]) == 0,
                "trade_count_delta": int(dyn["trade_count"]) - int(current_dyn["trade_count"]),
                "final_balance_delta": round(safe_num(dyn["final_balance"]) - safe_num(current_dyn["final_balance"]), 6),
                "matched_unique_delta": int(mp["matched_unique"]) - int(current_map["matched_unique"]),
                "python_unmatched_delta": int(mp["python_unmatched"]) - int(current_map["python_unmatched"]),
                "mt5_unmatched_delta": int(mp["mt5_unmatched"]) - int(current_map["mt5_unmatched"]),
                "direct_gap_delta": round(safe_num(gap["direct_dynamic_gap_python_minus_mt5"]) - safe_num(current_gap["direct_dynamic_gap_python_minus_mt5"]), 6),
                "matched_profit_diff_delta": round(safe_num(mp["matched_profit_diff"]) - safe_num(current_map["matched_profit_diff"]), 6),
                "dynamic_invalid_spec_delta": int(invalid["dynamic_invalid_spec_rows"]) - int(current_invalid["dynamic_invalid_spec_rows"]),
            }
        )
    return pd.DataFrame(rows)


def top_unmatched(mapping_dir: Path, side: str, max_rows: int = 15) -> pd.DataFrame:
    if side == "python":
        frame = read_csv(mapping_dir / "python_mt5_unmatched_python_trades.csv")
        frame["effect"] = pd.to_numeric(frame["dynamic_total_$"], errors="coerce").fillna(0.0)
        cols = ["py_trade_id", "date", "dir_norm", "trigger_family", "mode_family", "mode", "variant", "dynamic_total_$", "effect"]
    else:
        frame = read_csv(mapping_dir / "python_mt5_unmatched_mt5_trades.csv")
        frame["effect"] = -pd.to_numeric(frame["net_profit"], errors="coerce").fillna(0.0)
        cols = ["mt5_trade_id", "signal_anchor_time", "aligned_time", "dir_norm", "trigger_family", "mode_family", "signal_src", "net_profit", "effect"]
    frame["abs_effect"] = frame["effect"].abs()
    frame["side"] = f"{side}_unmatched"
    return frame.sort_values("abs_effect", ascending=False)[["side", *[c for c in cols if c in frame.columns], "abs_effect"]].head(max_rows).reset_index(drop=True)


def build_report(signal_metrics: pd.DataFrame, dynamic_cmp: pd.DataFrame, mapping_cmp: pd.DataFrame, gap_cmp: pd.DataFrame, target_cmp: pd.DataFrame, invalid_cmp: pd.DataFrame, decision: pd.DataFrame) -> str:
    local_best_rows = decision[
        decision["target_20251017_removed"]
        & (decision["dynamic_invalid_spec_delta"] <= 0)
        & (decision["matched_unique_delta"] >= 0)
    ].copy()
    merge_ready = decision[
        decision["target_20251017_removed"]
        & decision["target_20251021_removed"]
        & (decision["dynamic_invalid_spec_delta"] <= 0)
        & (decision["matched_unique_delta"] >= 0)
        & (decision["direct_gap_delta"] >= -50.0)
        & (decision["matched_profit_diff_delta"] >= -50.0)
    ].copy()
    if not merge_ready.empty:
        merge_ready["_score"] = merge_ready["direct_gap_delta"].abs() + merge_ready["matched_profit_diff_delta"].abs()
        best = merge_ready.sort_values(["_score", "python_unmatched_delta"]).iloc[0]
        best_note = f"Merge candidate by strict gate: `{best['run']}`."
    elif not local_best_rows.empty:
        local_best_rows["_score"] = local_best_rows["direct_gap_delta"].abs() + local_best_rows["matched_profit_diff_delta"].abs()
        best = local_best_rows.sort_values(["_score", "python_unmatched_delta"]).iloc[0]
        best_note = f"No variant passes the merge gate. Best local diagnostic candidate: `{best['run']}`."
    else:
        best_note = "No variant passes the merge gate or the local diagnostic gate."

    lines = [
        "# Runtime Rescue Admission Guard Prototype",
        "",
        "## Decision",
        "",
        f"- {best_note}",
        "- Merge gate used here requires both target false positives removed, no new invalid spec rows, matched_unique not lower, direct gap delta >= -50, and matched_profit_diff delta >= -50.",
        "- This review changes only Python-MT5 signal generation prototypes; EA behavior and current metadatafix snapshots are not overwritten.",
        "- A candidate still needs manual review before merging into the mainline because runtime_rescue also affects Layer3 ranking and max-pos.",
        "",
        "## Decision Matrix",
        "",
        markdown_table(decision),
        "",
        "## Signal Metrics",
        "",
        markdown_table(signal_metrics),
        "",
        "## Dynamic Risk",
        "",
        markdown_table(dynamic_cmp),
        "",
        "## Mapping",
        "",
        markdown_table(mapping_cmp),
        "",
        "## Gap Components",
        "",
        markdown_table(gap_cmp),
        "",
        "## Target Cases",
        "",
        markdown_table(target_cmp),
        "",
        "## Invalid Spec Counts",
        "",
        markdown_table(invalid_cmp),
        "",
        "## Interpretation",
        "",
        "- `runtime_rescue_wide_only` tests whether rejecting original `too_tight` rescues is enough to remove the `2025-10-17` false positive.",
        "- `no_stop_side_mirror` tests whether rejecting selected M15 entries that put the old stop on the wrong side is enough.",
        "- `require_selected_m15_mode` tests whether M15 pre_cross/cross rows must be true M15 signal rows instead of inheriting M30 mode.",
        "- `combined_runtime_guard` applies all three guards and is expected to be conservative.",
    ]
    return "\n".join(lines)


def write_readme() -> None:
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# runtime_rescue_admission_guard_full_chain_review_20260715",
                "",
                "Prototype review for Python-MT5 ea_slot1_runtime_rescue admission guards.",
                "",
                "Primary report: `runtime_rescue_admission_guard_full_chain_review.md`.",
            ]
        ),
    )


def main() -> None:
    signal_metrics = generate_guarded_signals()
    export_csv(signal_metrics, OUT_DIR / "guard_signal_metrics.csv")

    dynamic_rows = []
    mapping_rows = []
    gap_rows = []
    invalid_rows = []
    target_rows = []
    run_dirs: dict[str, tuple[Path, Path, Path]] = {}

    # Include current metadatafix as the baseline.
    dynamic_rows.extend(dynamic_summary_for("current_metadatafix", CURRENT_DYNAMIC_DIR))
    mapping_rows.append(mapping_summary_for("current_metadatafix", CURRENT_MAPPING_DIR))
    gap_rows.append(gap_components_for("current_metadatafix", CURRENT_DYNAMIC_DIR, CURRENT_MAPPING_DIR))
    invalid_rows.append(invalid_spec_counts_for("current_metadatafix", CURRENT_SIGNAL_DIR, CURRENT_DYNAMIC_DIR))
    target_rows.extend(target_cases_for("current_metadatafix", CURRENT_DYNAMIC_DIR, CURRENT_MAPPING_DIR))

    for config in GUARDS:
        input_dir = run_prepare_inputs(config.name)
        dynamic_dir = run_dynamic_alignment(config.name, input_dir)
        mapping_dir = run_mapping(config.name, dynamic_dir)
        run_dirs[config.name] = (input_dir, dynamic_dir, mapping_dir)

        dynamic_rows.extend(dynamic_summary_for(config.name, dynamic_dir))
        mapping_rows.append(mapping_summary_for(config.name, mapping_dir))
        gap_rows.append(gap_components_for(config.name, dynamic_dir, mapping_dir))
        invalid_rows.append(invalid_spec_counts_for(config.name, PROTO_SIGNAL_ROOT / config.name, dynamic_dir))
        target_rows.extend(target_cases_for(config.name, dynamic_dir, mapping_dir))

    dynamic_cmp = pd.DataFrame(dynamic_rows)
    mapping_cmp = pd.DataFrame(mapping_rows)
    gap_cmp = pd.DataFrame(gap_rows)
    invalid_cmp = pd.DataFrame(invalid_rows)
    target_cmp = pd.DataFrame(target_rows)
    decision = build_decision_matrix(dynamic_cmp, mapping_cmp, gap_cmp, target_cmp, invalid_cmp)

    export_csv(dynamic_cmp, OUT_DIR / "dynamic_risk_summary.csv")
    export_csv(mapping_cmp, OUT_DIR / "mapping_summary.csv")
    export_csv(gap_cmp, OUT_DIR / "gap_components.csv")
    export_csv(invalid_cmp, OUT_DIR / "invalid_spec_counts.csv")
    export_csv(target_cmp, OUT_DIR / "target_cases.csv")
    export_csv(decision, OUT_DIR / "decision_matrix.csv")

    for variant, (_, _, mapping_dir) in run_dirs.items():
        export_csv(top_unmatched(mapping_dir, "python"), OUT_DIR / f"{variant}_top_python_unmatched.csv")
        export_csv(top_unmatched(mapping_dir, "mt5"), OUT_DIR / f"{variant}_top_mt5_unmatched.csv")

    report = build_report(signal_metrics, dynamic_cmp, mapping_cmp, gap_cmp, target_cmp, invalid_cmp, decision)
    write_text(OUT_DIR / "runtime_rescue_admission_guard_full_chain_review.md", report)
    write_readme()
    print(decision.to_string(index=False))
    print(f"Wrote {OUT_DIR}")


if __name__ == "__main__":
    main()
