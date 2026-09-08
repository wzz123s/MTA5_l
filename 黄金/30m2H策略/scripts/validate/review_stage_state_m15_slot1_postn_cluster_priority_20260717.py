# -*- coding: utf-8 -*-
"""Audit M15 SLOT1 post_n cluster priority/ranking for Layer3 rescue candidates.

This script is diagnostic-only. It reviews same-family M15 SLOT1/post_n rescue
clusters and checks whether candidate ordering rules are supported by more than
the single mt5_0076 case.
"""
from __future__ import annotations


from pathlib import Path

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

LIFECYCLE_DIR = VALIDATION_DIR / "stage_state_lifecycle_aware_maxpos_probe_20260717"
GENERALIZATION_DIR = VALIDATION_DIR / "stage_state_layer3_target_only_replacement_generalization_20260717"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"

OUT_DIR = VALIDATION_DIR / "stage_state_m15_slot1_postn_cluster_priority_audit_20260717"

TARGET_TIME = pd.Timestamp("2026-03-24 12:00:00")
TARGET_MT5_ID = "mt5_0076"
FOCUS_VARIANT = "lifecycle_replace_same_family8_stage3time"
FOCUS_POLICY = "lifecycle_stage3time"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def parse_dt(value: object) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT
    text = str(value).strip()
    if not text:
        return pd.NaT
    return pd.to_datetime(text.replace(".", "-"), errors="coerce")


def parse_dt_series(series: pd.Series) -> pd.Series:
    return series.map(parse_dt)


def fmt_dt(value: object) -> str:
    dt = parse_dt(value)
    if pd.isna(dt):
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"S", "SELL", "SHORT", "-1"}:
        return "SELL"
    if text in {"L", "B", "BUY", "LONG", "1"}:
        return "BUY"
    return text


def mode_family(value: object) -> str:
    text = str(value)
    if "post_n" in text:
        return "post_n"
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    return text.strip()


def mode_number(value: object) -> int:
    text = str(value)
    if "post_n" not in text:
        return -1
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else -1


def simple_table(frame: pd.DataFrame, columns: list[str] | None = None, max_rows: int = 80) -> str:
    if frame.empty:
        return "_No rows._"
    display = frame.copy()
    if columns is not None:
        display = display[[col for col in columns if col in display.columns]]
    return display.head(max_rows).to_markdown(index=False)


def load_same_family_candidates() -> pd.DataFrame:
    features = read_csv(GENERALIZATION_DIR / "layer3_target_only_generalization_candidate_features.csv")
    features["row_time_dt"] = parse_dt_series(features["row_time"])
    features["nearest_opposite_layer3_time_dt"] = parse_dt_series(features["nearest_opposite_layer3_time"])
    features["dir_norm"] = features["dir_norm"].map(normalize_dir)
    features["mode_family"] = features["mode_family"].map(mode_family)
    features["mode_n"] = features["mode"].map(mode_number)
    features["source_profit_num"] = pd.to_numeric(features["source_profit"], errors="coerce")
    features["same_family_opposite"] = features["same_family_opposite"].map(as_bool)
    features["target_like_strict"] = features["target_like_strict"].map(as_bool)
    same = features[features["same_family_opposite"]].copy()
    return same.sort_values(["candidate_cluster_key", "row_time_dt"]).reset_index(drop=True)


def load_mt5_unique() -> pd.DataFrame:
    mt5 = read_csv(DYNAMIC_DIR / "mt5_ledger_unique_signals.csv")
    mt5 = mt5.copy()
    mt5["mt5_trade_id"] = [f"mt5_{idx + 1:04d}" for idx in range(len(mt5))]
    mt5["signal_anchor_dt"] = parse_dt_series(mt5["signal_anchor_time"])
    mt5["aligned_target_time"] = mt5["signal_anchor_dt"] + pd.Timedelta(minutes=90)
    mt5["dir_norm"] = mt5["dir"].map(normalize_dir)
    mt5["mode_family"] = mt5["mode_family"].map(mode_family)
    mt5["trigger_family"] = mt5["trigger_family"].astype(str)
    return mt5


def enrich_with_mt5_proximity(candidates: pd.DataFrame, mt5: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, cand in candidates.iterrows():
        same_family = mt5[
            mt5["dir_norm"].eq(cand["dir_norm"])
            & mt5["trigger_family"].eq("M15 SLOT1")
            & mt5["mode_family"].eq("post_n")
        ].copy()
        any_near = mt5[mt5["dir_norm"].eq(cand["dir_norm"])].copy()
        out = cand.to_dict()

        for prefix, pool in [("nearest_same_family_mt5", same_family), ("nearest_same_dir_mt5", any_near)]:
            if pool.empty:
                out[f"{prefix}_id"] = ""
                out[f"{prefix}_aligned_time"] = ""
                out[f"{prefix}_signal_src"] = ""
                out[f"{prefix}_abs_minutes"] = pd.NA
                out[f"{prefix}_net_profit"] = pd.NA
                continue
            pool = pool.copy()
            pool["abs_minutes"] = (
                pool["aligned_target_time"] - cand["row_time_dt"]
            ).dt.total_seconds().abs() / 60.0
            hit = pool.sort_values(["abs_minutes", "aligned_target_time"]).iloc[0]
            out[f"{prefix}_id"] = hit.get("mt5_trade_id", "")
            out[f"{prefix}_aligned_time"] = fmt_dt(hit.get("aligned_target_time"))
            out[f"{prefix}_signal_src"] = hit.get("signal_src", "")
            out[f"{prefix}_abs_minutes"] = hit.get("abs_minutes", pd.NA)
            out[f"{prefix}_net_profit"] = hit.get("net_profit", pd.NA)

        same_family_exact = same_family[same_family["aligned_target_time"].eq(cand["row_time_dt"])]
        out["exact_same_family_mt5_id"] = (
            ";".join(same_family_exact["mt5_trade_id"].astype(str).tolist()) if not same_family_exact.empty else ""
        )
        out["exact_same_family_mt5_profit"] = (
            float(pd.to_numeric(same_family_exact["net_profit"], errors="coerce").sum())
            if not same_family_exact.empty
            else pd.NA
        )
        out["is_target_time"] = cand["row_time_dt"] == TARGET_TIME
        rows.append(out)
    return pd.DataFrame(rows)


def build_cluster_summary(candidates: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, grp in candidates.groupby("candidate_cluster_key", dropna=False):
        exact_rows = grp[grp["exact_same_family_mt5_id"].astype(str).ne("")]
        rows.append(
            {
                "candidate_cluster_key": key,
                "cluster_rows": int(len(grp)),
                "dir_norm": ";".join(sorted(set(grp["dir_norm"].astype(str)))),
                "cluster_min_time": fmt_dt(grp["row_time_dt"].min()),
                "cluster_max_time": fmt_dt(grp["row_time_dt"].max()),
                "mode_list": ";".join(grp.sort_values("row_time_dt")["mode"].astype(str).tolist()),
                "mode_n_min": int(grp["mode_n"].min()),
                "mode_n_max": int(grp["mode_n"].max()),
                "source_profit_min": round(float(grp["source_profit_num"].min()), 6),
                "source_profit_max": round(float(grp["source_profit_num"].max()), 6),
                "negative_rows": int((grp["source_profit_num"] < 0).sum()),
                "all_negative": bool((grp["source_profit_num"] < 0).all()),
                "exact_same_family_mt5_candidate_count": int(len(exact_rows)),
                "exact_same_family_mt5_ids": ";".join(
                    exact_rows["exact_same_family_mt5_id"].astype(str).tolist()
                ),
                "min_same_family_mt5_abs_minutes": round(
                    float(pd.to_numeric(grp["nearest_same_family_mt5_abs_minutes"], errors="coerce").min()), 6
                )
                if pd.to_numeric(grp["nearest_same_family_mt5_abs_minutes"], errors="coerce").notna().any()
                else pd.NA,
                "contains_mt5_0076_target_time": bool(grp["is_target_time"].map(as_bool).any()),
            }
        )
    return pd.DataFrame(rows).sort_values("candidate_cluster_key").reset_index(drop=True)


def choose_row(grp: pd.DataFrame, rule: str) -> tuple[pd.Series | None, bool]:
    work = grp.copy()
    if rule == "earliest":
        return work.sort_values(["row_time_dt", "mode_n"]).iloc[0], True
    if rule == "latest":
        return work.sort_values(["row_time_dt", "mode_n"], ascending=[False, False]).iloc[0], True
    if rule == "max_mode_n":
        return work.sort_values(["mode_n", "row_time_dt"], ascending=[False, False]).iloc[0], True
    if rule == "min_source_profit":
        return work.sort_values(["source_profit_num", "row_time_dt"], ascending=[True, False]).iloc[0], True
    if rule == "max_source_profit":
        return work.sort_values(["source_profit_num", "row_time_dt"], ascending=[False, True]).iloc[0], True
    if rule == "latest_negative":
        neg = work[work["source_profit_num"] < 0].copy()
        if neg.empty:
            return work.sort_values(["row_time_dt", "mode_n"], ascending=[False, False]).iloc[0], False
        return neg.sort_values(["row_time_dt", "mode_n"], ascending=[False, False]).iloc[0], True
    if rule == "max_mode_negative":
        neg = work[work["source_profit_num"] < 0].copy()
        if neg.empty:
            return work.sort_values(["mode_n", "row_time_dt"], ascending=[False, False]).iloc[0], False
        return neg.sort_values(["mode_n", "row_time_dt"], ascending=[False, False]).iloc[0], True
    if rule == "nearest_same_family_mt5":
        work["nearest_same_family_num"] = pd.to_numeric(
            work["nearest_same_family_mt5_abs_minutes"], errors="coerce"
        )
        available = work[work["nearest_same_family_num"].notna()].copy()
        if available.empty:
            return None, False
        return available.sort_values(["nearest_same_family_num", "row_time_dt"]).iloc[0], True
    raise ValueError(rule)


def build_rule_choices(candidates: pd.DataFrame) -> pd.DataFrame:
    rules = [
        "earliest",
        "latest",
        "max_mode_n",
        "min_source_profit",
        "max_source_profit",
        "latest_negative",
        "max_mode_negative",
        "nearest_same_family_mt5",
    ]
    rows = []
    for key, grp in candidates.groupby("candidate_cluster_key", dropna=False):
        for rule in rules:
            choice, applicable = choose_row(grp, rule)
            if choice is None:
                rows.append(
                    {
                        "rule": rule,
                        "candidate_cluster_key": key,
                        "rule_applicable": applicable,
                        "selected_time": "",
                        "selected_dir": "",
                        "selected_mode": "",
                        "selected_mode_n": pd.NA,
                        "selected_source_profit": pd.NA,
                        "exact_same_family_mt5_id": "",
                        "nearest_same_family_mt5_id": "",
                        "nearest_same_family_mt5_abs_minutes": pd.NA,
                        "selects_mt5_0076_target_time": False,
                    }
                )
                continue
            rows.append(
                {
                    "rule": rule,
                    "candidate_cluster_key": key,
                    "rule_applicable": applicable,
                    "selected_time": fmt_dt(choice["row_time_dt"]),
                    "selected_dir": choice["dir_norm"],
                    "selected_mode": choice["mode"],
                    "selected_mode_n": int(choice["mode_n"]),
                    "selected_source_profit": round(float(choice["source_profit_num"]), 6),
                    "exact_same_family_mt5_id": choice.get("exact_same_family_mt5_id", ""),
                    "nearest_same_family_mt5_id": choice.get("nearest_same_family_mt5_id", ""),
                    "nearest_same_family_mt5_abs_minutes": choice.get(
                        "nearest_same_family_mt5_abs_minutes", pd.NA
                    ),
                    "nearest_same_family_mt5_signal_src": choice.get(
                        "nearest_same_family_mt5_signal_src", ""
                    ),
                    "selects_mt5_0076_target_time": bool(choice["row_time_dt"] == TARGET_TIME),
                }
            )
    return pd.DataFrame(rows)


def build_rule_summary(choices: pd.DataFrame, cluster_summary: pd.DataFrame) -> pd.DataFrame:
    supported_clusters = set(
        cluster_summary[
            cluster_summary["exact_same_family_mt5_candidate_count"].astype(int) > 0
        ]["candidate_cluster_key"].astype(str)
    )
    rows = []
    for rule, grp in choices.groupby("rule", dropna=False):
        exact = grp[grp["exact_same_family_mt5_id"].astype(str).ne("")]
        exact_supported = exact[exact["candidate_cluster_key"].astype(str).isin(supported_clusters)]
        target_selected = bool(grp["selects_mt5_0076_target_time"].map(as_bool).any())
        choices_within_60 = int(
            (pd.to_numeric(grp["nearest_same_family_mt5_abs_minutes"], errors="coerce") <= 60).sum()
        )
        gate = bool(len(exact_supported) >= 2 and target_selected)
        if gate:
            decision = "ranking_rule_candidate_needs_full_chain_prototype"
        elif target_selected and len(exact_supported) == 1:
            decision = "single_mt5_supported_cluster_not_proven"
        elif len(exact_supported) == 0:
            decision = "no_exact_mt5_support"
        else:
            decision = "diagnostic_only"
        rows.append(
            {
                "rule": rule,
                "clusters_considered": int(grp["candidate_cluster_key"].nunique()),
                "clusters_with_choice": int(grp["selected_time"].astype(str).ne("").sum()),
                "mt5_supported_clusters_total": int(len(supported_clusters)),
                "choices_with_exact_same_family_mt5": int(len(exact)),
                "choices_with_exact_supported_cluster": int(len(exact_supported)),
                "choices_within_60m_same_family_mt5": choices_within_60,
                "selects_mt5_0076_target_time": target_selected,
                "ranking_rule_gate_pass": gate,
                "decision": decision,
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["ranking_rule_gate_pass", "choices_with_exact_supported_cluster", "selects_mt5_0076_target_time"],
        ascending=[False, False, False],
    )


def build_lifecycle_cluster_trace(candidates: pd.DataFrame) -> pd.DataFrame:
    trace = read_csv(LIFECYCLE_DIR / "lifecycle_maxpos_trace.csv")
    focus = trace[
        trace["variant"].astype(str).eq(FOCUS_VARIANT)
        & trace["policy"].astype(str).eq(FOCUS_POLICY)
        & trace["prototype_added_candidate"].map(as_bool)
    ].copy()
    focus["row_time_dt"] = parse_dt_series(focus["row_time"])
    focus["dir_norm"] = focus["dir_norm"].map(normalize_dir)
    focus["mode_n"] = focus["mode"].map(mode_number)
    key_cols = ["row_time_dt", "dir_norm", "mode_n"]
    lookup = candidates[["candidate_cluster_key", "row_time_dt", "dir_norm", "mode_n"]].drop_duplicates(key_cols)
    merged = focus.merge(lookup, on=key_cols, how="left")
    return merged[
        [
            "candidate_cluster_key",
            "row_time",
            "active_until",
            "dir_norm",
            "mode",
            "mode_n",
            "is_target_candidate",
            "active_count_before",
            "active_blockers_before",
            "accepted",
            "stage1_exit",
            "stage2_exit",
            "stage3_exit",
            "stage_total_$",
        ]
    ].sort_values(["candidate_cluster_key", "row_time"]).reset_index(drop=True)


def build_final_decision(rule_summary: pd.DataFrame, cluster_summary: pd.DataFrame) -> pd.DataFrame:
    same_family_cluster_count = int(len(cluster_summary))
    mt5_supported_clusters = int(
        (cluster_summary["exact_same_family_mt5_candidate_count"].astype(int) > 0).sum()
    )
    gate_pass_count = int(rule_summary["ranking_rule_gate_pass"].map(as_bool).sum())
    target_selecting_rules = int(rule_summary["selects_mt5_0076_target_time"].map(as_bool).sum())
    return pd.DataFrame(
        [
            {
                "same_family_cluster_count": same_family_cluster_count,
                "mt5_exact_supported_cluster_count": mt5_supported_clusters,
                "ranking_rules_tested": int(len(rule_summary)),
                "rules_selecting_mt5_0076_target": target_selecting_rules,
                "ranking_rule_gate_pass_count": gate_pass_count,
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "merge_gate_pass": False,
                "decision": "ranking_rule_not_proven_single_mt5_supported_cluster"
                if gate_pass_count == 0
                else "ranking_rule_candidate_needs_full_chain_prototype",
                "recommended_next_action": "audit_mt5_0076_postn_counter_anchor_before_ranking_prototype"
                if gate_pass_count == 0
                else "build_low_blast_cluster_ranking_full_chain_prototype",
            }
        ]
    )


def write_report(
    candidates: pd.DataFrame,
    cluster_summary: pd.DataFrame,
    rule_choices: pd.DataFrame,
    rule_summary: pd.DataFrame,
    lifecycle_trace: pd.DataFrame,
    final_decision: pd.DataFrame,
) -> None:
    final = final_decision.iloc[0]
    lines = [
        "# Stage-State M15 SLOT1 post_n Cluster Priority / Ranking Audit",
        "",
        "## Scope",
        "",
        "- Diagnostic-only audit for same-family M15 SLOT1/post_n rescue clusters.",
        "- Compares earliest/latest/max-mode/min-profit/MT5-proximity choices.",
        "- Uses lifecycle trace from the prior non-destructive probe.",
        "- Does not modify baseline signals, EA behavior, dynamic risk, or mapping.",
        "",
        "## Final Decision",
        "",
        f"- Same-family cluster count: `{int(final['same_family_cluster_count'])}`.",
        f"- MT5 exact-supported cluster count: `{int(final['mt5_exact_supported_cluster_count'])}`.",
        f"- Ranking rules tested: `{int(final['ranking_rules_tested'])}`.",
        f"- Rules selecting `mt5_0076` target: `{int(final['rules_selecting_mt5_0076_target'])}`.",
        f"- Ranking rule gate pass count: `{int(final['ranking_rule_gate_pass_count'])}`.",
        f"- Decision: `{final['decision']}`.",
        f"- Recommended next action: `{final['recommended_next_action']}`.",
        f"- `main_signal_change_gate_open = {as_bool(final['main_signal_change_gate_open'])}`.",
        f"- `ea_behavior_gate_open = {as_bool(final['ea_behavior_gate_open'])}`.",
        f"- `mapping_change_gate_open = {as_bool(final['mapping_change_gate_open'])}`.",
        f"- `merge_gate_pass = {as_bool(final['merge_gate_pass'])}`.",
        "",
        "## Cluster Summary",
        "",
        simple_table(cluster_summary),
        "",
        "## Rule Summary",
        "",
        simple_table(rule_summary),
        "",
        "## Lifecycle Trace For Same-Family8",
        "",
        simple_table(lifecycle_trace),
        "",
        "## Candidate Rows",
        "",
        simple_table(
            candidates,
            [
                "candidate_cluster_key",
                "row_time",
                "dir_norm",
                "mode",
                "source_profit_num",
                "exact_same_family_mt5_id",
                "nearest_same_family_mt5_id",
                "nearest_same_family_mt5_abs_minutes",
                "target_like_strict",
            ],
        ),
        "",
        "## Rule Choices",
        "",
        simple_table(rule_choices),
        "",
        "## Interpretation",
        "",
        "- Rules such as latest/max-mode/min-profit can select the `mt5_0076` target row.",
        "- The support comes from only one MT5 exact-supported cluster; the 2025-10-21 SELL cluster has no same-family MT5 exact counterpart.",
        "- Therefore cluster ranking is not proven enough for a main signal change or a merge gate.",
        "",
        "## Output Files",
        "",
        "- `cluster_priority_candidate_rows.csv`",
        "- `cluster_priority_cluster_summary.csv`",
        "- `cluster_priority_rule_choices.csv`",
        "- `cluster_priority_rule_summary.csv`",
        "- `cluster_priority_lifecycle_trace.csv`",
        "- `cluster_priority_final_decision.csv`",
    ]
    write_text(OUT_DIR / "m15_slot1_postn_cluster_priority_audit.md", "\n".join(lines))
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# stage_state_m15_slot1_postn_cluster_priority_audit_20260717",
                "",
                "Diagnostic-only M15 SLOT1 post_n cluster priority/ranking audit.",
                "",
                "No baseline strategy, EA, dynamic-risk, or mapping logic is changed.",
            ]
        ),
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = load_same_family_candidates()
    mt5 = load_mt5_unique()
    enriched = enrich_with_mt5_proximity(candidates, mt5)
    cluster_summary = build_cluster_summary(enriched)
    rule_choices = build_rule_choices(enriched)
    rule_summary = build_rule_summary(rule_choices, cluster_summary)
    lifecycle_trace = build_lifecycle_cluster_trace(enriched)
    final_decision = build_final_decision(rule_summary, cluster_summary)

    export_csv(enriched, OUT_DIR / "cluster_priority_candidate_rows.csv")
    export_csv(cluster_summary, OUT_DIR / "cluster_priority_cluster_summary.csv")
    export_csv(rule_choices, OUT_DIR / "cluster_priority_rule_choices.csv")
    export_csv(rule_summary, OUT_DIR / "cluster_priority_rule_summary.csv")
    export_csv(lifecycle_trace, OUT_DIR / "cluster_priority_lifecycle_trace.csv")
    export_csv(final_decision, OUT_DIR / "cluster_priority_final_decision.csv")
    write_report(enriched, cluster_summary, rule_choices, rule_summary, lifecycle_trace, final_decision)


if __name__ == "__main__":
    main()
