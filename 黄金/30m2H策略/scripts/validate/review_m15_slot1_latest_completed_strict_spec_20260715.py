# -*- coding: utf-8 -*-
"""Full-chain review for latest-completed M15 SLOT1 with strict spec recalc/filter."""
from __future__ import annotations


import importlib.util
import sys
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

BROAD_SIGNAL_DIR = (
    VALIDATION_DIR
    / "m15_slot1_latest_completed_prototype_20260715"
    / "signals"
    / "python_h2_context_q2early_latest_slot1"
)
BROAD_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_m15_slot1_latest_completed_close_retry_20260715"
BROAD_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_m15_slot1_latest_completed_close_retry_20260715"

STRICT_PROTO_DIR = VALIDATION_DIR / "m15_slot1_latest_completed_strict_spec_prototype_20260715"
STRICT_SIGNAL_ROOT = STRICT_PROTO_DIR / "signals"
STRICT_VARIANT = "python_h2_context_q2early_latest_slot1_strict_spec"
STRICT_SIGNAL_DIR = STRICT_SIGNAL_ROOT / STRICT_VARIANT
STRICT_INPUT_DIR = VALIDATION_DIR / "dynamic_risk_inputs_m15_slot1_latest_completed_strict_spec_20260715"
STRICT_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_m15_slot1_latest_completed_strict_spec_close_retry_20260715"
STRICT_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_m15_slot1_latest_completed_strict_spec_close_retry_20260715"
OUT_DIR = VALIDATION_DIR / "m15_slot1_latest_completed_strict_spec_full_chain_review_20260715"

SHIFT90_M30 = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "m30_prepared_with_mt5_shift90.csv"
TARGET_TIME = pd.Timestamp("2025-10-21 10:00:00")
SPEC_LO = 5.0
SPEC_HI = 35.0


RUNS = [
    ("current_metadatafix", CURRENT_SIGNAL_DIR, CURRENT_DYNAMIC_DIR, CURRENT_MAPPING_DIR),
    ("latest_completed_broad", BROAD_SIGNAL_DIR, BROAD_DYNAMIC_DIR, BROAD_MAPPING_DIR),
    ("latest_completed_strict_spec", STRICT_SIGNAL_DIR, STRICT_DYNAMIC_DIR, STRICT_MAPPING_DIR),
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


def latest_completed_by_distance_factory(m15t):
    def choose_slot1_latest_by_distance(seg, is_long, stop):
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

    return choose_slot1_latest_by_distance


def recalc_spec(frame: pd.DataFrame, spec_lo: float = SPEC_LO, spec_hi: float = SPEC_HI) -> pd.DataFrame:
    out = frame.copy()
    if not {"entry", "stop"}.issubset(out.columns):
        return out
    out["entry"] = pd.to_numeric(out["entry"], errors="coerce")
    out["stop"] = pd.to_numeric(out["stop"], errors="coerce")
    out["sd"] = (out["entry"] - out["stop"]).abs()
    out["spec_pass"] = out["sd"].between(spec_lo, spec_hi, inclusive="both")
    out["spec_reason"] = "ok"
    out.loc[out["sd"] > spec_hi, "spec_reason"] = "too_wide"
    out.loc[out["sd"] < spec_lo, "spec_reason"] = "too_tight"
    out.loc[out["sd"].isna(), "spec_reason"] = "nan"
    out.loc[out["sd"].isna(), "spec_pass"] = False
    return out


def generate_strict_signals() -> pd.DataFrame:
    rebuild = load_module_from_path(
        "rebuild_python_mt5_shift90_for_latest_slot1_strict_spec",
        STRATEGY_DIR / "scripts" / "signals" / "rebuild_python_mt5_shift90.py",
    )
    m15t = rebuild.m15t
    old_out_root = rebuild.OUT_ROOT
    old_chooser = m15t.choose_slot1_by_distance
    old_proxy = rebuild.cb.apply_m30_close_proxy

    def strict_apply_m30_close_proxy(final_acc, df):
        proxied = old_proxy(final_acc, df)
        strict = recalc_spec(proxied)
        return strict[strict["spec_pass"]].reset_index(drop=True)

    try:
        rebuild.OUT_ROOT = STRICT_SIGNAL_ROOT
        m15t.choose_slot1_by_distance = latest_completed_by_distance_factory(m15t)
        rebuild.cb.apply_m30_close_proxy = strict_apply_m30_close_proxy

        mt5 = rebuild.load_mt5_export()
        mt5_m30 = rebuild.build_m30_smma(mt5)
        df, _ = rebuild.prepare(str(rebuild.M30_RAW_CSV), min_len=8, mt5_smma=mt5_m30)
        m15 = m15t.load_m15()
        h2 = rebuild.load_h2_context()
        STRICT_SIGNAL_ROOT.mkdir(parents=True, exist_ok=True)
        metrics = pd.DataFrame(
            [
                rebuild.run_variant(
                    df,
                    h2,
                    m15,
                    STRICT_VARIANT,
                    use_q2_early=True,
                )
            ]
        )
    finally:
        rebuild.OUT_ROOT = old_out_root
        m15t.choose_slot1_by_distance = old_chooser
        rebuild.cb.apply_m30_close_proxy = old_proxy
    return metrics


def run_prepare_inputs() -> None:
    prep.OUT_DIR = STRICT_INPUT_DIR
    prep.SHIFT90_SIGNAL_DIR = STRICT_SIGNAL_DIR
    prep.SHIFT90_M30 = SHIFT90_M30
    prep.SOURCES = [
        prep.SourceConfig("python_only", DATA_DIR / "signals"),
        prep.SourceConfig("python_mt5", STRICT_SIGNAL_DIR, SHIFT90_M30),
    ]
    prep.main()


def run_dynamic_alignment() -> None:
    sim.INPUT_DIR = STRICT_INPUT_DIR
    sim.OUT_DIR = STRICT_DYNAMIC_DIR
    sim.main()


def run_mapping() -> None:
    mapper.INPUT_DIR = STRICT_DYNAMIC_DIR
    mapper.OUT_DIR = STRICT_MAPPING_DIR
    mapper.main()


def source_row(frame: pd.DataFrame, source: str) -> pd.Series:
    rows = frame[frame["source"].astype(str).eq(source)]
    if rows.empty:
        raise ValueError(f"Missing source={source}")
    return rows.iloc[0]


def dynamic_summary() -> pd.DataFrame:
    rows = []
    for run, _, dynamic_dir, _ in RUNS:
        summary = read_csv(dynamic_dir / "dynamic_risk_compare_summary.csv")
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


def mapping_summary() -> pd.DataFrame:
    rows = []
    for run, _, _, mapping_dir in RUNS:
        row = source_row(read_csv(mapping_dir / "unique_match_summary.csv"), "python_mt5")
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
    return {
        "run": run,
        "python_mt5_total_profit": round(safe_num(py_summary["dynamic_total_profit"]), 6),
        "mt5_total_profit": round(safe_num(mt5_summary["dynamic_total_profit"]), 6),
        "direct_dynamic_gap_python_minus_mt5": round(
            safe_num(py_summary["dynamic_total_profit"]) - safe_num(mt5_summary["dynamic_total_profit"]),
            6,
        ),
        "matched_profit_diff": round(matched_profit_diff, 6),
        "python_unmatched_gap_effect": round(py_unmatched_profit, 6),
        "mt5_unmatched_gap_effect": round(mt5_unmatched_gap, 6),
        "signal_set_gap_effect": round(py_unmatched_profit + mt5_unmatched_gap, 6),
        "reconstructed_dynamic_gap": round(matched_profit_diff + py_unmatched_profit + mt5_unmatched_gap, 6),
    }


def gap_summary() -> pd.DataFrame:
    return pd.DataFrame([gap_components_for(run, dynamic_dir, mapping_dir) for run, _, dynamic_dir, mapping_dir in RUNS])


def signal_file(signal_dir: Path, kind: str) -> Path:
    names = {
        "accepted": "候选信号_Layer1_Layer2通过.csv",
        "picked": "最终信号_Layer3入选.csv",
        "stage": "执行交易_Stage结果.csv",
    }
    return signal_dir / names[kind]


def invalid_spec_counts() -> pd.DataFrame:
    rows = []
    for run, signal_dir, dynamic_dir, _ in RUNS:
        for layer, path in [
            ("accepted", signal_file(signal_dir, "accepted")),
            ("picked", signal_file(signal_dir, "picked")),
            ("dynamic_inputs", STRICT_INPUT_DIR / "python_mt5_dynamic_risk_inputs.csv" if run == "latest_completed_strict_spec" else None),
        ]:
            if layer == "dynamic_inputs" and path is None:
                path = (
                    VALIDATION_DIR
                    / ("dynamic_risk_inputs_shift90_metadatafix_20260714" if run == "current_metadatafix" else "dynamic_risk_inputs_m15_slot1_latest_completed_20260715")
                    / "python_mt5_dynamic_risk_inputs.csv"
                )
            frame = read_csv(path)
            if "sd" in frame.columns:
                dist = pd.to_numeric(frame["sd"], errors="coerce")
            else:
                dist = pd.to_numeric(frame["stop_pts_spec"], errors="coerce")
            bad = frame[(dist < SPEC_LO) | (dist > SPEC_HI)].copy()
            rows.append(
                {
                    "run": run,
                    "layer": layer,
                    "rows": int(len(frame)),
                    "invalid_spec_rows": int(len(bad)),
                    "min_dist": round(float(dist.min()), 6) if dist.notna().any() else "",
                    "max_dist": round(float(dist.max()), 6) if dist.notna().any() else "",
                }
            )
    return pd.DataFrame(rows)


def target_case_summary() -> pd.DataFrame:
    rows = []
    for run, _, dynamic_dir, mapping_dir in RUNS:
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
            }
        )
    return pd.DataFrame(rows)


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


def build_report(
    metrics: pd.DataFrame,
    dynamic_cmp: pd.DataFrame,
    mapping_cmp: pd.DataFrame,
    gap_cmp: pd.DataFrame,
    invalid_cmp: pd.DataFrame,
    target_cmp: pd.DataFrame,
    top_py: pd.DataFrame,
    top_mt5: pd.DataFrame,
) -> str:
    current_gap = gap_cmp[gap_cmp["run"].eq("current_metadatafix")].iloc[0]
    strict_gap = gap_cmp[gap_cmp["run"].eq("latest_completed_strict_spec")].iloc[0]
    gap_delta = safe_num(strict_gap["direct_dynamic_gap_python_minus_mt5"]) - safe_num(current_gap["direct_dynamic_gap_python_minus_mt5"])
    lines = [
        "# M15 SLOT1 latest-completed strict-spec full-chain review",
        "",
        "## 结论",
        "",
        "- 本版本在 latest-completed bar 语义后，强制重算 `sd/spec_pass/spec_reason`，并在 Layer3/max-pos 前过滤 actual `sd` 超出 `[5,35]` 的行。",
        "- 该脚本不修改 EA，不覆盖 current metadatafix 或 broad latest-completed 快照。",
        f"- strict direct dynamic gap delta vs current = `{gap_delta:.6f}`；负数表示 Python-MT5 相对 MT5 更低。",
        "- 是否能进入主线，取决于 strict 版本是否同时满足：target 假阳性消失、invalid spec rows 不放大、mapping/gap 不显著恶化。",
        "",
        "## Strict Prototype Metrics",
        "",
        markdown_table(metrics),
        "",
        "## Dynamic Risk Summary",
        "",
        markdown_table(dynamic_cmp),
        "",
        "## Mapping Summary",
        "",
        markdown_table(mapping_cmp),
        "",
        "## Gap Components",
        "",
        markdown_table(gap_cmp),
        "",
        "## Invalid Spec Counts",
        "",
        markdown_table(invalid_cmp),
        "",
        "## Target Case",
        "",
        markdown_table(target_cmp),
        "",
        "## Strict Top Python-Unmatched",
        "",
        markdown_table(top_py, max_rows=12),
        "",
        "## Strict Top MT5-Unmatched",
        "",
        markdown_table(top_mt5, max_rows=12),
    ]
    return "\n".join(lines)


def write_readme() -> None:
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# m15_slot1_latest_completed_strict_spec_full_chain_review_20260715",
                "",
                "Strict-spec full-chain review for the latest-completed M15 SLOT1 prototype.",
                "",
                "Generated by `review_m15_slot1_latest_completed_strict_spec_20260715.py`.",
            ]
        ),
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics = generate_strict_signals()
    run_prepare_inputs()
    run_dynamic_alignment()
    run_mapping()

    dynamic_cmp = dynamic_summary()
    mapping_cmp = mapping_summary()
    gap_cmp = gap_summary()
    invalid_cmp = invalid_spec_counts()
    target_cmp = target_case_summary()
    top_py = top_unmatched(STRICT_MAPPING_DIR, "python")
    top_mt5 = top_unmatched(STRICT_MAPPING_DIR, "mt5")

    export_csv(metrics, OUT_DIR / "strict_prototype_metrics.csv")
    export_csv(dynamic_cmp, OUT_DIR / "dynamic_risk_three_way.csv")
    export_csv(mapping_cmp, OUT_DIR / "mapping_three_way.csv")
    export_csv(gap_cmp, OUT_DIR / "gap_components_three_way.csv")
    export_csv(invalid_cmp, OUT_DIR / "invalid_spec_counts_three_way.csv")
    export_csv(target_cmp, OUT_DIR / "target_case_three_way.csv")
    export_csv(top_py, OUT_DIR / "strict_top_python_unmatched.csv")
    export_csv(top_mt5, OUT_DIR / "strict_top_mt5_unmatched.csv")
    write_text(
        OUT_DIR / "m15_slot1_latest_completed_strict_spec_full_chain_review.md",
        build_report(metrics, dynamic_cmp, mapping_cmp, gap_cmp, invalid_cmp, target_cmp, top_py, top_mt5),
    )
    write_readme()

    print(mapping_cmp.to_string(index=False))
    print()
    print(gap_cmp.to_string(index=False))
    print()
    print(invalid_cmp.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
