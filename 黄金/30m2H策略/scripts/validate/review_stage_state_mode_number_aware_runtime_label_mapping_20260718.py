# -*- coding: utf-8 -*-
"""Mode-number-aware mapping audit for the SLOT1 runtime-label prototype.

Diagnostic-only:
- does not modify map_python_mt5_ledger_trades.py
- does not modify EA/Python signal builders
- does not modify dynamic-risk outputs
"""

from __future__ import annotations


from pathlib import Path
import re

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

BASE_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_exec_model_stage_state_metadatafix_20260716"
RUNTIME_LABEL_DIR = VALIDATION_DIR / "stage_state_python_slot1_runtime_label_feasibility_20260717"
DIAG_MAPPING_DIR = RUNTIME_LABEL_DIR / "diagnostic_mapping"
OUT_DIR = VALIDATION_DIR / "stage_state_mode_number_aware_runtime_label_mapping_audit_20260718"

BASE_ALL_CANDIDATES = BASE_MAPPING_DIR / "all_candidate_matches.csv"
DIAG_ALL_CANDIDATES = DIAG_MAPPING_DIR / "all_candidate_matches.csv"
BASE_FAMILY_SUMMARY = BASE_MAPPING_DIR / "unique_match_summary.csv"
DIAG_FAMILY_SUMMARY = DIAG_MAPPING_DIR / "unique_match_summary.csv"
RUNTIME_TARGET_MAP = RUNTIME_LABEL_DIR / "runtime_label_target_mapping_before_after.csv"
RUNTIME_FINAL = RUNTIME_LABEL_DIR / "runtime_label_final_decision.csv"

TARGET_IDS = ["mt5_0052", "mt5_0054", "mt5_0067", "mt5_0068", "mt5_0069"]

MAX_CANDIDATE_WINDOW_MINUTES = 7 * 24 * 60
TIER_ORDER = {
    "exact_align90_all": 1,
    "nearby_60_all": 2,
    "nearby_180_all": 3,
    "nearby_1d_all": 4,
    "nearby_7d_all": 5,
    "nearby_60_trigger_relaxed": 6,
    "nearby_60_mode_relaxed": 7,
    "nearby_7d_trigger_relaxed": 8,
    "nearby_7d_mode_relaxed": 9,
    "same_dir_7d_unclassified": 99,
}
RELIABLE_TIERS = {
    "exact_align90_all",
    "nearby_60_all",
    "nearby_180_all",
    "nearby_1d_all",
    "nearby_7d_all",
}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_md(lines: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8-sig")


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def num(value: object, default: float = 0.0) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(parsed):
        return default
    return float(parsed)


def mode_family(value: object) -> str:
    text = str(value).lower()
    if "post_n" in text:
        return "post_n"
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    return str(value).strip()


def postn_key(value: object) -> str:
    match = re.search(r"post_n(\d+)", str(value))
    if not match:
        return ""
    return f"post_n{match.group(1)}"


def mode_key(value: object) -> str:
    postn = postn_key(value)
    if postn:
        return postn
    return mode_family(value)


def classify_candidate(abs_minutes: float, trigger_same: bool, mode_key_same: bool) -> str:
    if abs_minutes == 0 and trigger_same and mode_key_same:
        return "exact_align90_all"
    if abs_minutes <= 60 and trigger_same and mode_key_same:
        return "nearby_60_all"
    if abs_minutes <= 180 and trigger_same and mode_key_same:
        return "nearby_180_all"
    if abs_minutes <= 24 * 60 and trigger_same and mode_key_same:
        return "nearby_1d_all"
    if abs_minutes <= MAX_CANDIDATE_WINDOW_MINUTES and trigger_same and mode_key_same:
        return "nearby_7d_all"
    if abs_minutes <= 60 and mode_key_same:
        return "nearby_60_trigger_relaxed"
    if abs_minutes <= 60 and trigger_same:
        return "nearby_60_mode_relaxed"
    if abs_minutes <= MAX_CANDIDATE_WINDOW_MINUTES and mode_key_same:
        return "nearby_7d_trigger_relaxed"
    if abs_minutes <= MAX_CANDIDATE_WINDOW_MINUTES and trigger_same:
        return "nearby_7d_mode_relaxed"
    return "same_dir_7d_unclassified"


def enrich_candidates(candidates: pd.DataFrame, scenario: str) -> pd.DataFrame:
    out = candidates.copy()
    out["scenario"] = scenario
    out["py_mode_key"] = out["py_mode"].map(mode_key)
    out["mt5_mode_key"] = out["mt5_signal_src"].map(mode_key)
    out["py_postn_key"] = out["py_mode"].map(postn_key)
    out["mt5_postn_key"] = out["mt5_signal_src"].map(postn_key)
    out["mode_key_same"] = out["py_mode_key"].astype(str).eq(out["mt5_mode_key"].astype(str))
    out["postn_number_compared"] = out["py_postn_key"].astype(str).ne("") | out["mt5_postn_key"].astype(str).ne("")
    out["postn_number_same"] = out["py_postn_key"].astype(str).eq(out["mt5_postn_key"].astype(str))
    out["postn_number_mismatch"] = out["postn_number_compared"] & ~out["postn_number_same"]
    out["family_match_tier"] = out["match_tier"]
    out["family_tier_rank"] = out["tier_rank"]
    out["family_is_reliable_tier"] = out["is_reliable_tier"].map(boolish)
    out["strict_match_tier"] = [
        classify_candidate(float(abs_minutes), boolish(trigger_same), boolish(mode_key_same))
        for abs_minutes, trigger_same, mode_key_same in zip(
            out["abs_time_diff_minutes"],
            out["trigger_same"],
            out["mode_key_same"],
        )
    ]
    out["strict_tier_rank"] = out["strict_match_tier"].map(TIER_ORDER)
    out["strict_is_reliable_tier"] = out["strict_match_tier"].isin(RELIABLE_TIERS)
    out["tier_changed_by_mode_number"] = out["strict_match_tier"].astype(str).ne(out["family_match_tier"].astype(str))
    return out


def greedy_unique_matches(candidates: pd.DataFrame) -> pd.DataFrame:
    if candidates.empty:
        return candidates.copy()
    eligible = candidates[candidates["strict_match_tier"].ne("same_dir_7d_unclassified")].copy()
    if eligible.empty:
        return eligible
    eligible["profit_abs_diff"] = pd.to_numeric(eligible["profit_diff"], errors="coerce").abs()
    eligible = eligible.sort_values(
        [
            "strict_tier_rank",
            "abs_time_diff_minutes",
            "profit_abs_diff",
            "py_trade_id",
            "mt5_trade_id",
        ],
        ascending=[True, True, True, True, True],
    )
    used_py: set[str] = set()
    used_mt5: set[str] = set()
    selected_rows: list[pd.Series] = []
    for _, row in eligible.iterrows():
        py_id = str(row["py_trade_id"])
        mt5_id = str(row["mt5_trade_id"])
        if py_id in used_py or mt5_id in used_mt5:
            continue
        selected_rows.append(row)
        used_py.add(py_id)
        used_mt5.add(mt5_id)
    if not selected_rows:
        return pd.DataFrame(columns=eligible.columns)
    return pd.DataFrame(selected_rows).reset_index(drop=True)


def summarize_strict(scenario: str, source: str, candidates: pd.DataFrame, unique: pd.DataFrame) -> dict[str, object]:
    src_candidates = candidates[candidates["source"].astype(str).eq(source)]
    source_py = int(src_candidates["py_trade_id"].nunique()) if not src_candidates.empty else 0
    source_mt5 = int(src_candidates["mt5_trade_id"].nunique()) if not src_candidates.empty else 0
    src_unique = unique[unique["source"].astype(str).eq(source)].copy() if not unique.empty else unique
    matched = int(len(src_unique))
    reliable = int(src_unique["strict_is_reliable_tier"].map(boolish).sum()) if matched else 0
    py_profit = pd.to_numeric(src_unique.get("py_profit", pd.Series(dtype=float)), errors="coerce").sum()
    mt5_profit = pd.to_numeric(src_unique.get("mt5_profit", pd.Series(dtype=float)), errors="coerce").sum()
    postn_mismatch = int(src_unique["postn_number_mismatch"].map(boolish).sum()) if matched else 0
    reliable_postn_mismatch = (
        int(
            (
                src_unique["postn_number_mismatch"].map(boolish)
                & src_unique["strict_is_reliable_tier"].map(boolish)
            ).sum()
        )
        if matched
        else 0
    )
    return {
        "scenario": scenario,
        "source": source,
        "python_trades": source_py,
        "mt5_trades": source_mt5,
        "matched_unique": matched,
        "reliable_tier_matched": reliable,
        "relaxed_tier_matched": matched - reliable,
        "python_unmatched": source_py - int(src_unique["py_trade_id"].nunique()) if matched else source_py,
        "mt5_unmatched": source_mt5 - int(src_unique["mt5_trade_id"].nunique()) if matched else source_mt5,
        "matched_python_profit": round(float(py_profit), 6),
        "matched_mt5_profit": round(float(mt5_profit), 6),
        "matched_profit_diff": round(float(py_profit - mt5_profit), 6),
        "postn_number_mismatch_in_unique": postn_mismatch,
        "reliable_postn_number_mismatch_in_unique": reliable_postn_mismatch,
    }


def build_strict_outputs(candidates: pd.DataFrame, scenario: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    enriched = enrich_candidates(candidates, scenario)
    unique = greedy_unique_matches(enriched)
    summaries = [
        summarize_strict(scenario, source, enriched, unique)
        for source in sorted(enriched["source"].astype(str).unique())
    ]
    return enriched, unique, pd.DataFrame(summaries)


def apply_total_counts(strict_summary: pd.DataFrame, family_summary: pd.DataFrame) -> pd.DataFrame:
    out = strict_summary.copy()
    for idx, row in out.iterrows():
        source = str(row["source"])
        family_hit = family_summary[family_summary["source"].astype(str).eq(source)]
        if family_hit.empty:
            continue
        family_row = family_hit.iloc[0]
        python_trades = int(num(family_row["python_trades"]))
        mt5_trades = int(num(family_row["mt5_trades"]))
        matched_unique = int(num(row["matched_unique"]))
        out.loc[idx, "python_trades"] = python_trades
        out.loc[idx, "mt5_trades"] = mt5_trades
        out.loc[idx, "python_unmatched"] = python_trades - matched_unique
        out.loc[idx, "mt5_unmatched"] = mt5_trades - matched_unique
        out.loc[idx, "count_basis"] = "family_summary_total_trades"
    return out


def family_summary_rows(frame: pd.DataFrame, scenario: str, family_label: str) -> pd.DataFrame:
    out = frame.copy()
    out["scenario"] = scenario
    out["mapping口径"] = family_label
    return out


def strict_summary_rows(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["mapping口径"] = "mode_number_aware"
    return out


def source_row(frame: pd.DataFrame, scenario: str, source: str) -> pd.Series:
    hit = frame[frame["scenario"].astype(str).eq(scenario) & frame["source"].astype(str).eq(source)]
    if hit.empty:
        raise ValueError(f"missing scenario={scenario} source={source}")
    return hit.iloc[0]


def build_delta_summary(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for source in sorted(summary["source"].astype(str).unique()):
        base = source_row(summary, "baseline_mode_number", source)
        diag = source_row(summary, "diagnostic_mode_number", source)
        row = {"source": source, "comparison": "diagnostic_minus_baseline_mode_number"}
        for col in [
            "python_trades",
            "mt5_trades",
            "matched_unique",
            "reliable_tier_matched",
            "relaxed_tier_matched",
            "python_unmatched",
            "mt5_unmatched",
            "matched_profit_diff",
            "postn_number_mismatch_in_unique",
            "reliable_postn_number_mismatch_in_unique",
        ]:
            row[f"baseline_{col}"] = base[col]
            row[f"diagnostic_{col}"] = diag[col]
            row[f"delta_{col}"] = num(diag[col]) - num(base[col])
        rows.append(row)
    return pd.DataFrame(rows)


def build_family_vs_strict_summary(
    base_family: pd.DataFrame,
    diag_family: pd.DataFrame,
    base_strict_summary: pd.DataFrame,
    diag_strict_summary: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for label, frame in [
        ("baseline_family", base_family),
        ("diagnostic_family", diag_family),
        ("baseline_mode_number", base_strict_summary),
        ("diagnostic_mode_number", diag_strict_summary),
    ]:
        temp = frame.copy()
        temp["scenario"] = label
        rows.append(temp)
    return pd.concat(rows, ignore_index=True, sort=False)


def build_target_strict_review(
    base_unique: pd.DataFrame,
    diag_unique: pd.DataFrame,
    runtime_target_map: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for mt5_id in TARGET_IDS:
        base = base_unique[base_unique["source"].astype(str).eq("python_mt5") & base_unique["mt5_trade_id"].astype(str).eq(mt5_id)]
        diag = diag_unique[diag_unique["source"].astype(str).eq("python_mt5") & diag_unique["mt5_trade_id"].astype(str).eq(mt5_id)]
        family = runtime_target_map[runtime_target_map["mt5_trade_id"].astype(str).eq(mt5_id)]
        b = base.iloc[0] if not base.empty else None
        d = diag.iloc[0] if not diag.empty else None
        f = family.iloc[0] if not family.empty else None
        rows.append(
            {
                "mt5_trade_id": mt5_id,
                "family_diagnostic_matched": f.get("diagnostic_matched", "") if f is not None else "",
                "family_diagnostic_match_tier": f.get("diagnostic_match_tier", "") if f is not None else "",
                "family_diagnostic_py_mode": f.get("diagnostic_py_mode", "") if f is not None else "",
                "family_diagnostic_postn_number_mismatch": f.get("diagnostic_postn_number_mismatch", "") if f is not None else "",
                "strict_baseline_matched": b is not None,
                "strict_baseline_tier": b.get("strict_match_tier", "") if b is not None else "",
                "strict_baseline_py_trade_id": b.get("py_trade_id", "") if b is not None else "",
                "strict_baseline_py_mode": b.get("py_mode", "") if b is not None else "",
                "strict_baseline_mt5_signal_src": b.get("mt5_signal_src", "") if b is not None else "",
                "strict_baseline_postn_number_same": b.get("postn_number_same", "") if b is not None else "",
                "strict_diagnostic_matched": d is not None,
                "strict_diagnostic_tier": d.get("strict_match_tier", "") if d is not None else "",
                "strict_diagnostic_py_trade_id": d.get("py_trade_id", "") if d is not None else "",
                "strict_diagnostic_py_mode": d.get("py_mode", "") if d is not None else "",
                "strict_diagnostic_mt5_signal_src": d.get("mt5_signal_src", "") if d is not None else "",
                "strict_diagnostic_postn_number_same": d.get("postn_number_same", "") if d is not None else "",
                "strict_diagnostic_postn_number_mismatch": d.get("postn_number_mismatch", False) if d is not None else False,
            }
        )
    return pd.DataFrame(rows)


def build_changed_tier_summary(enriched: pd.DataFrame, scenario: str) -> pd.DataFrame:
    changed = enriched[enriched["tier_changed_by_mode_number"].map(boolish)].copy()
    if changed.empty:
        return pd.DataFrame(
            columns=[
                "scenario",
                "source",
                "family_match_tier",
                "strict_match_tier",
                "rows",
                "mt5_ids",
            ]
        )
    rows = (
        changed.groupby(["source", "family_match_tier", "strict_match_tier"], dropna=False)
        .agg(
            rows=("mt5_trade_id", "count"),
            mt5_ids=("mt5_trade_id", lambda s: ";".join(s.astype(str).drop_duplicates().head(20))),
        )
        .reset_index()
    )
    rows["scenario"] = scenario
    return rows[["scenario", "source", "family_match_tier", "strict_match_tier", "rows", "mt5_ids"]]


def simple_table(frame: pd.DataFrame, max_rows: int = 40) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def build_final_decision(delta: pd.DataFrame, target_review: pd.DataFrame) -> pd.DataFrame:
    py = delta[delta["source"].astype(str).eq("python_mt5")]
    if py.empty:
        raise ValueError("missing python_mt5 delta")
    row = py.iloc[0]
    target_mismatch = int(target_review["strict_diagnostic_postn_number_mismatch"].map(boolish).sum())
    global_mismatch = int(num(row["diagnostic_postn_number_mismatch_in_unique"]))
    reliable_mismatch = int(num(row["diagnostic_reliable_postn_number_mismatch_in_unique"]))
    reliable_delta = num(row["delta_reliable_tier_matched"])
    matched_delta = num(row["delta_matched_unique"])
    py_unmatched_delta = num(row["delta_python_unmatched"])
    mt5_unmatched_delta = num(row["delta_mt5_unmatched"])
    strict_pass = (
        global_mismatch == 0
        and target_mismatch == 0
        and matched_delta >= 0
        and py_unmatched_delta <= 0
        and mt5_unmatched_delta <= 0
        and reliable_delta > 0
    )
    return pd.DataFrame(
        [
            {
                "python_mt5_baseline_matched_unique": row["baseline_matched_unique"],
                "python_mt5_diagnostic_matched_unique": row["diagnostic_matched_unique"],
                "delta_matched_unique": matched_delta,
                "python_mt5_baseline_reliable_tier_matched": row["baseline_reliable_tier_matched"],
                "python_mt5_diagnostic_reliable_tier_matched": row["diagnostic_reliable_tier_matched"],
                "delta_reliable_tier_matched": reliable_delta,
                "python_mt5_baseline_python_unmatched": row["baseline_python_unmatched"],
                "python_mt5_diagnostic_python_unmatched": row["diagnostic_python_unmatched"],
                "delta_python_unmatched": py_unmatched_delta,
                "python_mt5_baseline_mt5_unmatched": row["baseline_mt5_unmatched"],
                "python_mt5_diagnostic_mt5_unmatched": row["diagnostic_mt5_unmatched"],
                "delta_mt5_unmatched": mt5_unmatched_delta,
                "diagnostic_postn_number_mismatch_count": row["diagnostic_postn_number_mismatch_in_unique"],
                "diagnostic_reliable_postn_number_mismatch_count": row[
                    "diagnostic_reliable_postn_number_mismatch_in_unique"
                ],
                "target_diagnostic_postn_number_mismatch_count": target_mismatch,
                "mode_number_aware_pass": strict_pass,
                "runtime_label_direction_closed": not strict_pass,
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "merge_gate_pass": False,
                "recommended_next_action": (
                    "runtime_label_variant_remains_diagnostic_only_review_relaxed_postn_mismatches"
                    if reliable_mismatch == 0 and global_mismatch > 0
                    else "close_runtime_label_variant_and_audit_layer3_admission_missing_targets"
                ),
            }
        ]
    )


def build_report(
    final: pd.DataFrame,
    family_vs_strict: pd.DataFrame,
    delta: pd.DataFrame,
    target_review: pd.DataFrame,
    changed_tiers: pd.DataFrame,
) -> list[str]:
    f = final.iloc[0].to_dict()
    return [
        "# Stage-State Mode-Number-Aware Runtime-Label Mapping Audit",
        "",
        "## Final Decision",
        "",
        f"- Diagnostic matched unique delta: `{f['delta_matched_unique']}`.",
        f"- Diagnostic reliable-tier delta: `{f['delta_reliable_tier_matched']}`.",
        f"- Diagnostic Python-unmatched delta: `{f['delta_python_unmatched']}`.",
        f"- Diagnostic MT5-unmatched delta: `{f['delta_mt5_unmatched']}`.",
        f"- Target post_n number mismatch count: `{f['target_diagnostic_postn_number_mismatch_count']}`.",
        f"- Global post_n number mismatch count: `{f['diagnostic_postn_number_mismatch_count']}`.",
        f"- Reliable post_n number mismatch count: `{f['diagnostic_reliable_postn_number_mismatch_count']}`.",
        f"- Mode-number-aware pass: `{f['mode_number_aware_pass']}`.",
        f"- Runtime-label direction closed: `{f['runtime_label_direction_closed']}`.",
        f"- Main signal gate: `{f['main_signal_change_gate_open']}`.",
        f"- EA behavior gate: `{f['ea_behavior_gate_open']}`.",
        f"- Mapping gate: `{f['mapping_change_gate_open']}`.",
        f"- Merge gate: `{f['merge_gate_pass']}`.",
        "",
        "## Family Vs Strict Summary",
        "",
        simple_table(family_vs_strict),
        "",
        "## Diagnostic Minus Baseline Strict Delta",
        "",
        simple_table(delta),
        "",
        "## Target Strict Review",
        "",
        simple_table(target_review),
        "",
        "## Tier Changes Caused By post_nN Strictness",
        "",
        simple_table(changed_tiers, max_rows=80),
        "",
        "## Interpretation",
        "",
        "- The previous runtime-label prototype's reliable-tier gain was not safe because the family-level mapper treats all post_n values as the same mode family.",
        "- This audit recomputes unique matching with full post_nN keys for post_n trades while leaving cross/pre_cross at family level.",
        "- Under the stricter key, reliable matches no longer carry post_n number mismatches, but relaxed unique matches still do. The variant remains diagnostic-only until those relaxed mismatches are explained.",
        "- The remaining useful lead is not a relabel merge; it is the Layer3/dynamic admission gap for targets that only exist at Layer1/2.",
    ]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base_candidates = read_csv(BASE_ALL_CANDIDATES)
    diag_candidates = read_csv(DIAG_ALL_CANDIDATES)
    base_family = read_csv(BASE_FAMILY_SUMMARY)
    diag_family = read_csv(DIAG_FAMILY_SUMMARY)
    runtime_target_map = read_csv(RUNTIME_TARGET_MAP)

    base_enriched, base_unique, base_strict_summary = build_strict_outputs(base_candidates, "baseline_mode_number")
    diag_enriched, diag_unique, diag_strict_summary = build_strict_outputs(diag_candidates, "diagnostic_mode_number")
    base_strict_summary = apply_total_counts(base_strict_summary, base_family)
    diag_strict_summary = apply_total_counts(diag_strict_summary, diag_family)
    family_vs_strict = build_family_vs_strict_summary(base_family, diag_family, base_strict_summary, diag_strict_summary)
    delta = build_delta_summary(pd.concat([base_strict_summary, diag_strict_summary], ignore_index=True))
    target_review = build_target_strict_review(base_unique, diag_unique, runtime_target_map)
    changed_tiers = pd.concat(
        [
            build_changed_tier_summary(base_enriched, "baseline_mode_number"),
            build_changed_tier_summary(diag_enriched, "diagnostic_mode_number"),
        ],
        ignore_index=True,
    )
    final = build_final_decision(delta, target_review)

    write_csv(base_enriched, OUT_DIR / "baseline_mode_number_candidate_matches.csv")
    write_csv(diag_enriched, OUT_DIR / "diagnostic_mode_number_candidate_matches.csv")
    write_csv(base_unique, OUT_DIR / "baseline_mode_number_unique_matches.csv")
    write_csv(diag_unique, OUT_DIR / "diagnostic_mode_number_unique_matches.csv")
    write_csv(base_strict_summary, OUT_DIR / "baseline_mode_number_unique_summary.csv")
    write_csv(diag_strict_summary, OUT_DIR / "diagnostic_mode_number_unique_summary.csv")
    write_csv(family_vs_strict, OUT_DIR / "family_vs_mode_number_summary.csv")
    write_csv(delta, OUT_DIR / "mode_number_diagnostic_delta_summary.csv")
    write_csv(target_review, OUT_DIR / "mode_number_target_strict_review.csv")
    write_csv(changed_tiers, OUT_DIR / "mode_number_tier_change_summary.csv")
    write_csv(final, OUT_DIR / "mode_number_final_decision.csv")
    write_md(build_report(final, family_vs_strict, delta, target_review, changed_tiers), OUT_DIR / "mode_number_mapping_audit.md")
    write_md(
        [
            "# Mode-Number-Aware Runtime-Label Mapping Audit",
            "",
            f"- Matched unique delta: `{num(final.loc[0, 'delta_matched_unique'])}`.",
            f"- Reliable-tier delta: `{num(final.loc[0, 'delta_reliable_tier_matched'])}`.",
            f"- Target post_n mismatch count: `{int(final.loc[0, 'target_diagnostic_postn_number_mismatch_count'])}`.",
            f"- Merge gate: `{bool(final.loc[0, 'merge_gate_pass'])}`.",
        ],
        OUT_DIR / "README.md",
    )
    print(f"Wrote {OUT_DIR}")
    print(final.to_string(index=False))


if __name__ == "__main__":
    main()
