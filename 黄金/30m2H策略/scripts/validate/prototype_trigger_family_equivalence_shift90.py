# -*- coding: utf-8 -*-
"""Prototype trigger-family equivalence mapping for shift90 Python-MT5 candidates."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
MAPPED_DIR = DATA_DIR / "validation" / "mapped_trade_alignment_shift90_20260713"
DYNAMIC_DIR = DATA_DIR / "validation" / "dynamic_risk_alignment_shift90_20260713"
OUT_DIR = DATA_DIR / "validation" / "trigger_family_equivalence_shift90_20260713"

BASE_RELIABLE_TIERS = {
    "exact_align90_all",
    "nearby_60_all",
    "nearby_180_all",
    "nearby_1d_all",
    "nearby_7d_all",
}

TIER_ORDER = {
    "exact_align90_all": 1,
    "equiv_m30_to_m15_replace_30": 2,
    "equiv_m30_to_m15_replace_30_profit20": 3,
    "equiv_bidirectional_m30_m15_30": 4,
    "equiv_bidirectional_m30_m15_90": 5,
    "equiv_bidirectional_m30_m15_90_profit20": 6,
    "nearby_60_all": 7,
    "nearby_180_all": 8,
    "nearby_1d_all": 9,
    "nearby_7d_all": 10,
    "nearby_60_trigger_relaxed": 20,
    "nearby_60_mode_relaxed": 21,
    "nearby_7d_trigger_relaxed": 22,
    "nearby_7d_mode_relaxed": 23,
    "same_dir_7d_unclassified": 99,
}


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def load_candidates() -> pd.DataFrame:
    df = pd.read_csv(MAPPED_DIR / "all_candidate_matches.csv", encoding="utf-8-sig")
    df = df[df["source"] == "python_mt5"].copy()
    for col in ["abs_time_diff_minutes", "time_diff_minutes", "profit_diff"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def policy_candidates(base: pd.DataFrame, policy: str) -> pd.DataFrame:
    df = base.copy()
    df["policy"] = policy
    df["effective_match_tier"] = df["match_tier"]
    df["effective_is_reliable"] = df["match_tier"].isin(BASE_RELIABLE_TIERS)

    mode_same = df["mode_same"].astype(str).str.lower().isin({"true", "1"})
    profit_abs_diff = pd.to_numeric(df["profit_diff"], errors="coerce").abs()
    py_is_m15_replace = (
        (df["py_trigger_family"] == "M15 SLOT1")
        & df["py_variant"].astype(str).str.contains("ea_slot1_replace", regex=False)
    )
    mt5_is_m30 = df["mt5_trigger_family"] == "M30 CLOSE"
    py_is_m30 = df["py_trigger_family"] == "M30 CLOSE"
    mt5_is_m15 = df["mt5_trigger_family"] == "M15 SLOT1"

    if policy in {
        "m30_to_m15_replace_30",
        "m30_to_m15_replace_30_profit20",
        "bidirectional_m30_m15_30",
        "bidirectional_m30_m15_90",
        "bidirectional_m30_m15_90_profit20",
    }:
        mask = mode_same & mt5_is_m30 & py_is_m15_replace & (df["abs_time_diff_minutes"] <= 30)
        if policy in {"m30_to_m15_replace_30_profit20", "bidirectional_m30_m15_90_profit20"}:
            mask = mask & (profit_abs_diff <= 20)
            tier_name = "equiv_m30_to_m15_replace_30_profit20"
        else:
            tier_name = "equiv_m30_to_m15_replace_30"
        df.loc[mask, "effective_match_tier"] = tier_name
        df.loc[mask, "effective_is_reliable"] = True

    if policy == "bidirectional_m30_m15_30":
        mask = mode_same & mt5_is_m15 & py_is_m30 & (df["abs_time_diff_minutes"] <= 30)
        df.loc[mask, "effective_match_tier"] = "equiv_bidirectional_m30_m15_30"
        df.loc[mask, "effective_is_reliable"] = True

    if policy == "bidirectional_m30_m15_90":
        mask = mode_same & mt5_is_m15 & py_is_m30 & (df["abs_time_diff_minutes"] <= 90)
        df.loc[mask, "effective_match_tier"] = "equiv_bidirectional_m30_m15_90"
        df.loc[mask, "effective_is_reliable"] = True

    if policy == "bidirectional_m30_m15_90_profit20":
        mask = mode_same & mt5_is_m15 & py_is_m30 & (df["abs_time_diff_minutes"] <= 90) & (profit_abs_diff <= 20)
        df.loc[mask, "effective_match_tier"] = "equiv_bidirectional_m30_m15_90_profit20"
        df.loc[mask, "effective_is_reliable"] = True

    df["effective_tier_rank"] = df["effective_match_tier"].map(TIER_ORDER).fillna(999).astype(int)
    return df


def greedy_unique_matches(candidates: pd.DataFrame) -> pd.DataFrame:
    eligible = candidates[candidates["effective_match_tier"] != "same_dir_7d_unclassified"].copy()
    if eligible.empty:
        return eligible
    eligible["profit_abs_diff"] = pd.to_numeric(eligible["profit_diff"], errors="coerce").abs()
    eligible = eligible.sort_values(
        ["effective_tier_rank", "abs_time_diff_minutes", "profit_abs_diff", "py_trade_id", "mt5_trade_id"],
        ascending=[True, True, True, True, True],
    )
    used_py: set[str] = set()
    used_mt5: set[str] = set()
    rows: list[pd.Series] = []
    for _, row in eligible.iterrows():
        py_id = str(row["py_trade_id"])
        mt5_id = str(row["mt5_trade_id"])
        if py_id in used_py or mt5_id in used_mt5:
            continue
        rows.append(row)
        used_py.add(py_id)
        used_mt5.add(mt5_id)
    return pd.DataFrame(rows).reset_index(drop=True) if rows else pd.DataFrame(columns=eligible.columns)


def summarize(policy: str, matches: pd.DataFrame, python_count: int, mt5_count: int) -> dict[str, object]:
    matched = int(len(matches))
    reliable = int(matches["effective_is_reliable"].fillna(False).astype(bool).sum()) if matched else 0
    equiv = int(matches["effective_match_tier"].astype(str).str.startswith("equiv_").sum()) if matched else 0
    py_profit = pd.to_numeric(matches.get("py_profit", pd.Series(dtype=float)), errors="coerce").sum()
    mt5_profit = pd.to_numeric(matches.get("mt5_profit", pd.Series(dtype=float)), errors="coerce").sum()
    return {
        "policy": policy,
        "python_trades": python_count,
        "mt5_trades": mt5_count,
        "matched_unique": matched,
        "reliable_tier_matched": reliable,
        "relaxed_tier_matched": matched - reliable,
        "equivalence_matches": equiv,
        "python_unmatched": python_count - matches["py_trade_id"].nunique() if matched else python_count,
        "mt5_unmatched": mt5_count - matches["mt5_trade_id"].nunique() if matched else mt5_count,
        "matched_python_profit": round(float(py_profit), 6),
        "matched_mt5_profit": round(float(mt5_profit), 6),
        "matched_profit_diff": round(float(py_profit - mt5_profit), 6),
    }


def tier_counts(matches: pd.DataFrame) -> pd.DataFrame:
    if matches.empty:
        return pd.DataFrame(columns=["policy", "effective_match_tier", "rows"])
    return (
        matches.groupby(["policy", "effective_match_tier"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["policy", "effective_match_tier"])
    )


def render_report(summary: pd.DataFrame, tiers: pd.DataFrame, new_equiv: pd.DataFrame) -> str:
    lines = [
        "# Trigger Family Equivalence Shift90 Prototype",
        "",
        "## Policy Summary",
        "",
        summary.to_markdown(index=False),
        "",
        "## Tier Counts",
        "",
        tiers.to_markdown(index=False) if not tiers.empty else "_No tier rows_",
        "",
        "## Selected Equivalence Matches",
        "",
        new_equiv.to_markdown(index=False) if not new_equiv.empty else "_No equivalence matches selected_",
        "",
        "## Interpretation",
        "",
        "- `m30_to_m15_replace_30` only promotes Python `ea_slot1_replace` rows when MT5 is `M30 CLOSE`, direction and mode family match, and time distance is within 30 minutes.",
        "- Bidirectional policies additionally allow MT5 `M15 SLOT1` to match Python `M30 CLOSE` parent rows within 30 or 90 minutes.",
        "- This is a mapping prototype only; it does not change Python or EA trading behavior.",
        "",
        "## Output Files",
        "",
        "- `trigger_family_equivalence_policy_summary.csv`",
        "- `trigger_family_equivalence_tier_counts.csv`",
        "- `trigger_family_equivalence_all_selected_matches.csv`",
        "- `trigger_family_equivalence_selected_equiv_matches.csv`",
    ]
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base_candidates = load_candidates()
    python_count = int(pd.read_csv(DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv", encoding="utf-8-sig").shape[0])
    mt5_count = int(pd.read_csv(DYNAMIC_DIR / "mt5_ledger_unique_signals.csv", encoding="utf-8-sig").shape[0])

    policies = [
        "baseline",
        "m30_to_m15_replace_30",
        "m30_to_m15_replace_30_profit20",
        "bidirectional_m30_m15_30",
        "bidirectional_m30_m15_90",
        "bidirectional_m30_m15_90_profit20",
    ]
    selected_frames: list[pd.DataFrame] = []
    summary_rows: list[dict[str, object]] = []
    for policy in policies:
        candidates = policy_candidates(base_candidates, policy)
        selected = greedy_unique_matches(candidates)
        selected_frames.append(selected)
        summary_rows.append(summarize(policy, selected, python_count, mt5_count))
        export_csv(candidates, OUT_DIR / f"{policy}_candidate_matches.csv")
        export_csv(selected, OUT_DIR / f"{policy}_selected_matches.csv")

    all_selected = pd.concat(selected_frames, ignore_index=True) if selected_frames else pd.DataFrame()
    summary = pd.DataFrame(summary_rows)
    tiers = tier_counts(all_selected)
    selected_equiv = all_selected[all_selected["effective_match_tier"].astype(str).str.startswith("equiv_")].copy()
    equiv_cols = [
        "policy",
        "effective_match_tier",
        "py_trade_id",
        "mt5_trade_id",
        "py_date",
        "mt5_aligned_time",
        "abs_time_diff_minutes",
        "dir_norm",
        "py_trigger_family",
        "mt5_trigger_family",
        "py_mode_family",
        "mt5_mode_family",
        "py_mode",
        "mt5_signal_src",
        "py_variant",
        "py_profit",
        "mt5_profit",
        "profit_diff",
    ]
    selected_equiv_view = selected_equiv[equiv_cols].copy() if not selected_equiv.empty else pd.DataFrame(columns=equiv_cols)

    export_csv(summary, OUT_DIR / "trigger_family_equivalence_policy_summary.csv")
    export_csv(tiers, OUT_DIR / "trigger_family_equivalence_tier_counts.csv")
    export_csv(all_selected, OUT_DIR / "trigger_family_equivalence_all_selected_matches.csv")
    export_csv(selected_equiv_view, OUT_DIR / "trigger_family_equivalence_selected_equiv_matches.csv")
    write_text(OUT_DIR / "trigger_family_equivalence_report.md", render_report(summary, tiers, selected_equiv_view))

    print(summary.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
