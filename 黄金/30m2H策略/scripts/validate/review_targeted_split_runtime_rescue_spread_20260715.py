# -*- coding: utf-8 -*-
"""Targeted split runtime_rescue prototype plus spread-adjusted stop test."""
from __future__ import annotations


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
import review_runtime_rescue_admission_guard_20260715 as guard  # noqa: E402


STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"

CURRENT_SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "python_h2_context_q2early"
CURRENT_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_shift90_metadatafix_close_retry_20260714"
CURRENT_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_shift90_metadatafix_close_retry_20260714"

OUT_DIR = VALIDATION_DIR / "targeted_split_runtime_rescue_spread_review_20260715"
PROTO_SIGNAL_ROOT = OUT_DIR / "signals"
PROTO_INPUT_ROOT = VALIDATION_DIR / "dynamic_risk_inputs_targeted_split_runtime_rescue_spread_20260715"
PROTO_DYNAMIC_ROOT = VALIDATION_DIR / "dynamic_risk_alignment_targeted_split_runtime_rescue_spread_20260715"
PROTO_MAPPING_ROOT = VALIDATION_DIR / "mapped_trade_alignment_targeted_split_runtime_rescue_spread_20260715"
SHIFT90_M30 = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "m30_prepared_with_mt5_shift90.csv"

TARGET_20251017 = pd.Timestamp("2025-10-17 11:00:00")
TARGET_20251021 = pd.Timestamp("2025-10-21 10:00:00")
SPEC_LO = 5.0
SPEC_HI = 35.0
SPREAD_POINT = 0.001


@dataclass(frozen=True)
class SplitConfig:
    name: str
    targeted_split: bool
    add_spread_to_stop: bool
    strict_spec_filter: bool = True


CONFIGS = [
    SplitConfig(
        "python_h2_context_q2early_current_spread_stop_nofilter",
        targeted_split=False,
        add_spread_to_stop=True,
        strict_spec_filter=False,
    ),
    SplitConfig(
        "python_h2_context_q2early_current_spread_stop_strict",
        targeted_split=False,
        add_spread_to_stop=True,
    ),
    SplitConfig(
        "python_h2_context_q2early_targeted_split_strict",
        targeted_split=True,
        add_spread_to_stop=False,
    ),
    SplitConfig(
        "python_h2_context_q2early_targeted_split_spread_stop_strict",
        targeted_split=True,
        add_spread_to_stop=True,
    ),
    SplitConfig(
        "python_h2_context_q2early_targeted_split_spread_stop_nofilter",
        targeted_split=True,
        add_spread_to_stop=True,
        strict_spec_filter=False,
    ),
]


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def safe_num(value: object, default: float = 0.0) -> float:
    return guard.safe_num(value, default)


def parse_dt_series(series: pd.Series) -> pd.Series:
    return guard.parse_dt_series(series)


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None, max_rows: int | None = None) -> str:
    return guard.markdown_table(frame, columns=columns, max_rows=max_rows)


def recalc_spec(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if not {"entry", "stop"}.issubset(out.columns):
        return out
    out["entry"] = pd.to_numeric(out["entry"], errors="coerce")
    out["stop"] = pd.to_numeric(out["stop"], errors="coerce")
    out["sd"] = (out["entry"] - out["stop"]).abs()
    out["spec_pass"] = out["sd"].between(SPEC_LO, SPEC_HI, inclusive="both")
    out["spec_reason"] = "ok"
    out.loc[out["sd"] < SPEC_LO, "spec_reason"] = "too_tight"
    out.loc[out["sd"] > SPEC_HI, "spec_reason"] = "too_wide"
    out.loc[out["sd"].isna(), "spec_reason"] = "nan"
    out.loc[out["sd"].isna(), "spec_pass"] = False
    return out


def latest_completed_by_distance(m15t, seg: pd.DataFrame, is_long: bool, stop: float):
    if len(seg) == 0:
        return None
    row = seg.iloc[-1]
    entry = float(row["close"])
    sd = abs(entry - stop)
    if not m15t.m15_same_side(row, is_long):
        return None
    if not (m15t.SPEC_LO <= sd <= m15t.SPEC_HI):
        return None
    return row


def build_spread_lookup(df: pd.DataFrame, m15: pd.DataFrame) -> tuple[dict[pd.Timestamp, float], dict[pd.Timestamp, float]]:
    m30 = df.copy()
    m30["date_dt"] = pd.to_datetime(m30["date"], errors="coerce")
    m30["spread_price"] = pd.to_numeric(m30.get("spread", 0), errors="coerce").fillna(0.0) * SPREAD_POINT
    m15c = m15.copy()
    m15c["date_dt"] = pd.to_datetime(m15c["date"], errors="coerce")
    m15c["spread_price"] = pd.to_numeric(m15c.get("spread", 0), errors="coerce").fillna(0.0) * SPREAD_POINT
    m30_map = dict(zip(m30["date_dt"], m30["spread_price"]))
    m15_map = dict(zip(m15c["date_dt"], m15c["spread_price"]))
    return m30_map, m15_map


def apply_spread_to_stop(frame: pd.DataFrame, df: pd.DataFrame, m15: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    out = frame.copy()
    m30_spread, m15_spread = build_spread_lookup(df, m15)
    out["date_dt_tmp"] = pd.to_datetime(out["date"], errors="coerce")
    out["entry_time_dt_tmp"] = pd.to_datetime(out["entry_time"], errors="coerce")
    spread_prices = []
    for _, row in out.iterrows():
        entry_time = row["entry_time_dt_tmp"]
        date = row["date_dt_tmp"]
        use_m15 = pd.notna(entry_time) and pd.notna(date) and entry_time < date
        if use_m15:
            spread = m15_spread.get(pd.Timestamp(entry_time), 0.0)
        else:
            spread = m30_spread.get(pd.Timestamp(date), 0.0)
        spread_prices.append(float(spread))
    out["spread_price_added_to_stop"] = spread_prices
    out["spread_points_added_to_stop"] = out["spread_price_added_to_stop"] / SPREAD_POINT
    out["entry"] = pd.to_numeric(out["entry"], errors="coerce")
    out["stop"] = pd.to_numeric(out["stop"], errors="coerce")
    out["sd_before_spread"] = (out["entry"] - out["stop"]).abs()
    is_long = out["dir"].astype(str).str.upper().str.startswith("L")
    widened = out["sd_before_spread"] + out["spread_price_added_to_stop"]
    out.loc[is_long, "stop"] = out.loc[is_long, "entry"] - widened.loc[is_long]
    out.loc[~is_long, "stop"] = out.loc[~is_long, "entry"] + widened.loc[~is_long]
    out["sd"] = (out["entry"] - out["stop"]).abs()
    out["spread_stop_adjusted"] = True
    return out.drop(columns=["date_dt_tmp", "entry_time_dt_tmp"])


def selected_mode_required(mode: str) -> bool:
    return mode in {"pre_cross", "cross"}


def build_targeted_rescued(rejected: pd.DataFrame, m15: pd.DataFrame, m15t, mode_map: dict[pd.Timestamp, dict[str, int]]) -> tuple[pd.DataFrame, int]:
    rows = []
    rescue_count = 0
    for _, trade in rejected.iterrows():
        mode = str(trade.get("mode", ""))
        is_long = str(trade.get("dir", "")).upper().startswith("L")
        stop = float(trade["stop"])
        seg = m15t.m15_window(m15, trade["date"])
        if mode.startswith("post_n"):
            chosen = latest_completed_by_distance(m15t, seg, is_long, stop)
        else:
            chosen = m15t.choose_slot1_by_distance(seg, is_long, stop)
        if chosen is None:
            continue
        if selected_mode_required(mode) and not guard.selected_m15_mode_ok(trade, chosen, mode_map):
            continue
        row = trade.to_dict()
        row = m15t.recalc_trade(
            row,
            pd.Timestamp(chosen["date"]),
            float(chosen["close"]),
            "ea_slot1_runtime_rescue",
            m15,
            reanchor_stop_by_distance=True,
        )
        row = m15t.finalize_trade(m15t.df_global, row, m15) if pd.isna(row["pnl"]) else row
        rows.append(row)
        rescue_count += 1
    return pd.DataFrame(rows), rescue_count


def run_custom_variant(rebuild, df: pd.DataFrame, h2: pd.DataFrame, m15: pd.DataFrame, config: SplitConfig) -> dict[str, object]:
    pct = rebuild.pct
    m15t = rebuild.m15t
    h2t = rebuild.h2t
    combo = rebuild.combo
    cb = rebuild.cb
    s12 = rebuild.s12

    old_pct_lo, old_pct_hi = pct.SPEC_LO, pct.SPEC_HI
    old_bias55 = pct.BIAS_55_THRESHOLD
    old_m15_lo, old_m15_hi = m15t.SPEC_LO, m15t.SPEC_HI
    try:
        pct.SPEC_LO, pct.SPEC_HI = rebuild.SPEC_LO, rebuild.SPEC_HI
        pct.BIAS_55_THRESHOLD = rebuild.BIAS55_THRESHOLD
        m15t.SPEC_LO, m15t.SPEC_HI = rebuild.SPEC_LO, rebuild.SPEC_HI
        m15t.df_global = df
        h2t.df_global = df

        pass_set, factor_map, pass_bars, early_bar_count = h2t.early_precompute(h2, df, 2, False)
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
        if config.targeted_split:
            mode_map = guard.build_m15_mode_map(m15)
            rescued, rescued_count = build_targeted_rescued(rejected_runtime, m15, m15t, mode_map)
        else:
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
        if config.add_spread_to_stop:
            final_acc = apply_spread_to_stop(final_acc, df, m15)
        if config.strict_spec_filter:
            final_acc = recalc_spec(final_acc)
            final_acc = final_acc[final_acc["spec_pass"]].reset_index(drop=True)

        threshold, picked = cb.apply_layer3_ea_executable(final_acc, h2, top_pct=rebuild.TOP_PCT)
        picked_limited = rebuild.apply_max_pos_3(picked)
        trades = s12.summarize_variant(df, picked_limited, rebuild.STAGE1_R, rebuild.STAGE2_TRAIL_R, rebuild.STAGE2_FORCE_R)

        variant_dir = PROTO_SIGNAL_ROOT / config.name
        export_csv(raw_df, variant_dir / "raw_candidates.csv")
        export_csv(final_acc, variant_dir / "候选信号_Layer1_Layer2通过.csv")
        export_csv(picked_limited, variant_dir / "最终信号_Layer3入选.csv")
        export_csv(trades, variant_dir / "执行交易_Stage结果.csv")

        metrics: dict[str, object] = {
            "variant": config.name,
            "targeted_split": config.targeted_split,
            "add_spread_to_stop": config.add_spread_to_stop,
            "strict_spec_filter": config.strict_spec_filter,
            "mt5_time_shift_minutes": rebuild.TIME_SHIFT_MINUTES,
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
        metrics.update(rebuild.stage_stop_metrics(trades))
        return metrics
    finally:
        pct.SPEC_LO, pct.SPEC_HI = old_pct_lo, old_pct_hi
        pct.BIAS_55_THRESHOLD = old_bias55
        m15t.SPEC_LO, m15t.SPEC_HI = old_m15_lo, old_m15_hi


def generate_signals() -> pd.DataFrame:
    rebuild = guard.load_module_from_path(
        "rebuild_python_mt5_shift90_targeted_split_spread",
        STRATEGY_DIR / "scripts" / "signals" / "rebuild_python_mt5_shift90.py",
    )
    old_out_root = rebuild.OUT_ROOT
    try:
        rebuild.OUT_ROOT = PROTO_SIGNAL_ROOT
        mt5 = rebuild.load_mt5_export()
        mt5_m30 = rebuild.build_m30_smma(mt5)
        df, _ = rebuild.prepare(str(rebuild.M30_RAW_CSV), min_len=8, mt5_smma=mt5_m30)
        m15 = rebuild.m15t.load_m15()
        h2 = rebuild.load_h2_context()
        PROTO_SIGNAL_ROOT.mkdir(parents=True, exist_ok=True)
        metrics = [run_custom_variant(rebuild, df, h2, m15, config) for config in CONFIGS]
    finally:
        rebuild.OUT_ROOT = old_out_root
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


def dynamic_summary_for(run: str, dynamic_dir: Path) -> list[dict[str, object]]:
    return guard.dynamic_summary_for(run, dynamic_dir)


def mapping_summary_for(run: str, mapping_dir: Path) -> dict[str, object]:
    return guard.mapping_summary_for(run, mapping_dir)


def gap_components_for(run: str, dynamic_dir: Path, mapping_dir: Path) -> dict[str, object]:
    return guard.gap_components_for(run, dynamic_dir, mapping_dir)


def invalid_spec_counts_for(run: str, signal_dir: Path, dynamic_dir: Path) -> dict[str, object]:
    return guard.invalid_spec_counts_for(run, signal_dir, dynamic_dir)


def target_cases_for(run: str, dynamic_dir: Path, mapping_dir: Path) -> list[dict[str, object]]:
    return guard.target_cases_for(run, dynamic_dir, mapping_dir)


def build_decision_matrix(dynamic_cmp: pd.DataFrame, mapping_cmp: pd.DataFrame, gap_cmp: pd.DataFrame, target_cmp: pd.DataFrame, invalid_cmp: pd.DataFrame) -> pd.DataFrame:
    current_dyn = dynamic_cmp[(dynamic_cmp["run"].eq("current_metadatafix")) & (dynamic_cmp["source"].eq("python_mt5"))].iloc[0]
    current_map = mapping_cmp[mapping_cmp["run"].eq("current_metadatafix")].iloc[0]
    current_gap = gap_cmp[gap_cmp["run"].eq("current_metadatafix")].iloc[0]
    current_invalid = invalid_cmp[invalid_cmp["run"].eq("current_metadatafix")].iloc[0]
    rows = []
    for config in CONFIGS:
        run = config.name
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


def build_report(signal_metrics: pd.DataFrame, dynamic_cmp: pd.DataFrame, mapping_cmp: pd.DataFrame, gap_cmp: pd.DataFrame, target_cmp: pd.DataFrame, invalid_cmp: pd.DataFrame, decision: pd.DataFrame) -> str:
    merge_ready = decision[
        decision["target_20251017_removed"]
        & decision["target_20251021_removed"]
        & (decision["dynamic_invalid_spec_delta"] <= 0)
        & (decision["matched_unique_delta"] >= 0)
        & (decision["direct_gap_delta"] >= -50.0)
        & (decision["matched_profit_diff_delta"] >= -50.0)
    ].copy()
    if merge_ready.empty:
        decision_note = "No split/spread variant passes the merge gate."
    else:
        merge_ready["_score"] = merge_ready["direct_gap_delta"].abs() + merge_ready["matched_profit_diff_delta"].abs()
        best = merge_ready.sort_values(["_score", "python_unmatched_delta"]).iloc[0]
        decision_note = f"Merge candidate by current gate: `{best['run']}`."
    lines = [
        "# Targeted Split Runtime Rescue + Spread Stop Review",
        "",
        "## Decision",
        "",
        f"- {decision_note}",
        "- Spread test uses `spread_points * 0.001` and widens stop distance on the trade direction side.",
        "- All variants are Python-MT5 prototypes only; EA is unchanged.",
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
        "- `current_spread_stop_strict` isolates the effect of adding spread to stop distance without split runtime_rescue rules.",
        "- `targeted_split_strict` applies M15 selected-mode guard to pre_cross/cross runtime_rescue and latest-completed chooser only to post_n runtime_rescue.",
        "- `targeted_split_spread_stop_strict` adds the spread-distance test on top of the targeted split.",
    ]
    return "\n".join(lines)


def write_readme() -> None:
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# targeted_split_runtime_rescue_spread_review_20260715",
                "",
                "Full-chain review for targeted split runtime_rescue plus spread-adjusted stop distance.",
                "",
                "Primary report: `targeted_split_runtime_rescue_spread_review.md`.",
            ]
        ),
    )


def main() -> None:
    signal_metrics = generate_signals()
    export_csv(signal_metrics, OUT_DIR / "split_spread_signal_metrics.csv")

    dynamic_rows = []
    mapping_rows = []
    gap_rows = []
    invalid_rows = []
    target_rows = []
    run_dirs: dict[str, tuple[Path, Path, Path]] = {}

    dynamic_rows.extend(dynamic_summary_for("current_metadatafix", CURRENT_DYNAMIC_DIR))
    mapping_rows.append(mapping_summary_for("current_metadatafix", CURRENT_MAPPING_DIR))
    gap_rows.append(gap_components_for("current_metadatafix", CURRENT_DYNAMIC_DIR, CURRENT_MAPPING_DIR))
    invalid_rows.append(invalid_spec_counts_for("current_metadatafix", CURRENT_SIGNAL_DIR, CURRENT_DYNAMIC_DIR))
    target_rows.extend(target_cases_for("current_metadatafix", CURRENT_DYNAMIC_DIR, CURRENT_MAPPING_DIR))

    for config in CONFIGS:
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
        export_csv(guard.top_unmatched(mapping_dir, "python"), OUT_DIR / f"{variant}_top_python_unmatched.csv")
        export_csv(guard.top_unmatched(mapping_dir, "mt5"), OUT_DIR / f"{variant}_top_mt5_unmatched.csv")

    write_text(
        OUT_DIR / "targeted_split_runtime_rescue_spread_review.md",
        build_report(signal_metrics, dynamic_cmp, mapping_cmp, gap_cmp, target_cmp, invalid_cmp, decision),
    )
    write_readme()
    print(decision.to_string(index=False))
    print(f"Wrote {OUT_DIR}")


if __name__ == "__main__":
    main()
