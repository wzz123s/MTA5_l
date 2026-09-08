# -*- coding: utf-8 -*-
"""Prototype M15 SLOT1 post_n raw-parent gates before touching the EA.

The output is a policy evaluation, not a strategy rewrite. It shows which
rules would reject MT5-side M15 SLOT1 post_n trades and whether they would
damage already matched trades.
"""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
DYNAMIC_DIR = DATA_DIR / "validation" / "dynamic_risk_alignment_magic0fix_20260713"
MAPPED_DIR = DATA_DIR / "validation" / "mapped_trade_alignment_20260713"
CAUSE_DIR = DATA_DIR / "validation" / "unmatched_signal_cause_20260713"
OUT_DIR = DATA_DIR / "validation" / "prototype_m15_raw_parent_gate_20260713"

WINDOWS = [0, 30, 60, 90, 120, 180]
NEAR_SAME_M15_MINUTES = 180

REJECT_CAUSE_BUCKETS = {
    "missing_raw_parent",
    "trigger_family_drift",
    "stage_execution_diff_or_family_drift",
}
PROTECT_CAUSE_BUCKETS = {
    "mapping_conflict_or_profit_diff",
    "layer3_reject",
    "stage_execution_diff",
}


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"S", "SELL"}:
        return "SELL"
    if text in {"B", "BUY", "L"}:
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
    return text


def trigger_family_from_variant(value: object) -> str:
    text = str(value)
    if any(tag in text for tag in ["slot1", "replace", "rescue"]):
        return "M15 SLOT1"
    return "M30 CLOSE"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def find_one(directory: Path, token: str) -> Path:
    matches = sorted(p for p in directory.glob("*.csv") if token in p.name)
    if not matches:
        raise FileNotFoundError(f"No csv containing {token!r} in {directory}")
    return matches[0]


def load_mt5_signals() -> pd.DataFrame:
    df = read_csv(DYNAMIC_DIR / "mt5_ledger_unique_signals.csv")
    df = df.copy()
    df["mt5_trade_id"] = [f"mt5_{i + 1:04d}" for i in range(len(df))]
    df["signal_anchor_time"] = pd.to_datetime(df["signal_anchor_time"], errors="coerce")
    df["aligned_time"] = df["signal_anchor_time"] + pd.Timedelta(minutes=90)
    df["dir_norm"] = df["dir"].map(normalize_dir)
    return df


def load_accepted(source: str) -> pd.DataFrame:
    signal_dir = DATA_DIR / ("signals" if source == "python_only" else "signals_mt5")
    df = read_csv(find_one(signal_dir, "Layer1_Layer2"))
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["dir_norm"] = df["dir"].map(normalize_dir)
    df["mode_family"] = df["mode"].map(mode_family)
    df["trigger_family"] = df["variant"].map(trigger_family_from_variant)
    return df


def load_matches(source: str) -> tuple[set[str], set[str], set[str]]:
    matches = read_csv(MAPPED_DIR / "all_unique_matches.csv")
    src = matches[matches["source"] == source].copy()
    all_matched = set(src["mt5_trade_id"].astype(str))
    reliable = set(src[src["is_reliable_tier"].astype(str) == "True"]["mt5_trade_id"].astype(str))
    relaxed = all_matched - reliable
    return all_matched, reliable, relaxed


def load_cause(source: str) -> pd.DataFrame:
    path = CAUSE_DIR / f"{source}_mt5_unmatched_cause.csv"
    if not path.exists():
        return pd.DataFrame()
    df = read_csv(path)
    return df.set_index("trade_id", drop=False)


def nearest_parent(row: pd.Series, accepted: pd.DataFrame, window: int) -> dict[str, object]:
    candidates = accepted[
        (accepted["dir_norm"] == row["dir_norm"])
        & (accepted["trigger_family"] == "M30 CLOSE")
    ].copy()
    if candidates.empty:
        return {"has_parent": False, "parent_time": "", "parent_mode_family": "", "parent_abs_minutes": ""}
    candidates["abs_minutes"] = (candidates["date"] - row["aligned_time"]).dt.total_seconds().abs() / 60.0
    candidates = candidates[candidates["abs_minutes"] <= window]
    if candidates.empty:
        return {"has_parent": False, "parent_time": "", "parent_mode_family": "", "parent_abs_minutes": ""}
    best = candidates.sort_values(["abs_minutes", "date"]).iloc[0]
    return {
        "has_parent": True,
        "parent_time": best["date"],
        "parent_mode_family": best["mode_family"],
        "parent_abs_minutes": round(float(best["abs_minutes"]), 6),
    }


def has_near_same_m15(row: pd.Series, accepted: pd.DataFrame) -> bool:
    candidates = accepted[
        (accepted["dir_norm"] == row["dir_norm"])
        & (accepted["trigger_family"] == "M15 SLOT1")
        & (accepted["mode_family"] == "post_n")
    ].copy()
    if candidates.empty:
        return False
    abs_minutes = (candidates["date"] - row["aligned_time"]).dt.total_seconds().abs() / 60.0
    return bool((abs_minutes <= NEAR_SAME_M15_MINUTES).any())


def matched_status(trade_id: str, reliable: set[str], relaxed: set[str]) -> str:
    if trade_id in reliable:
        return "reliable_matched"
    if trade_id in relaxed:
        return "relaxed_matched"
    return "unmatched"


def policy_decision(
    policy: str,
    has_parent: bool,
    status: str,
    cause_bucket: str,
    near_same_m15: bool,
) -> str:
    if policy == "strict_parent":
        return "keep" if has_parent else "reject"
    if policy == "protect_reliable_parent":
        if status == "reliable_matched":
            return "protect"
        return "keep" if has_parent else "reject"
    if policy == "conservative_cause":
        if status != "unmatched":
            return "protect"
        if cause_bucket in PROTECT_CAUSE_BUCKETS:
            return "protect"
        if near_same_m15:
            return "protect"
        if (not has_parent) and cause_bucket in REJECT_CAUSE_BUCKETS:
            return "reject"
        return "keep"
    raise ValueError(policy)


def build_policy_details(source: str, window: int) -> pd.DataFrame:
    mt5 = load_mt5_signals()
    accepted = load_accepted(source)
    _, reliable, relaxed = load_matches(source)
    cause = load_cause(source)

    target = mt5[(mt5["trigger_family"] == "M15 SLOT1") & (mt5["mode_family"] == "post_n")].copy()
    rows: list[dict[str, object]] = []
    for _, row in target.iterrows():
        trade_id = str(row["mt5_trade_id"])
        parent = nearest_parent(row, accepted, window)
        status = matched_status(trade_id, reliable, relaxed)
        cause_bucket = ""
        if trade_id in cause.index:
            cause_bucket = str(cause.loc[trade_id, "cause_bucket"])
        near_same = has_near_same_m15(row, accepted)

        base = {
            "source": source,
            "window_minutes": window,
            "mt5_trade_id": trade_id,
            "aligned_time": row["aligned_time"],
            "dir_norm": row["dir_norm"],
            "signal_src": row["signal_src"],
            "net_profit": row["net_profit"],
            "match_status": status,
            "cause_bucket": cause_bucket,
            "near_same_m15_postn": near_same,
            **parent,
        }
        for policy in ["strict_parent", "protect_reliable_parent", "conservative_cause"]:
            base[f"{policy}_decision"] = policy_decision(
                policy,
                bool(parent["has_parent"]),
                status,
                cause_bucket,
                near_same,
            )
        rows.append(base)
    return pd.DataFrame(rows)


def summarize_policy(details: pd.DataFrame, policy: str) -> pd.DataFrame:
    if details.empty:
        return pd.DataFrame()
    rows = []
    for (source, window), grp in details.groupby(["source", "window_minutes"], dropna=False):
        decision_col = f"{policy}_decision"
        rejected = grp[grp[decision_col] == "reject"]
        reliable_rejected = rejected[rejected["match_status"] == "reliable_matched"]
        relaxed_rejected = rejected[rejected["match_status"] == "relaxed_matched"]
        unmatched_rejected = rejected[rejected["match_status"] == "unmatched"]
        rows.append(
            {
                "source": source,
                "policy": policy,
                "window_minutes": int(window),
                "mt5_m15_postn_total": int(len(grp)),
                "reject_count": int(len(rejected)),
                "reliable_matched_rejected": int(len(reliable_rejected)),
                "relaxed_matched_rejected": int(len(relaxed_rejected)),
                "unmatched_rejected": int(len(unmatched_rejected)),
                "protected_or_kept": int(len(grp) - len(rejected)),
                "reject_net_profit_sum": round(float(pd.to_numeric(rejected["net_profit"], errors="coerce").sum()), 6),
                "unmatched_reject_ids": ";".join(unmatched_rejected["mt5_trade_id"].astype(str).tolist()),
            }
        )
    return pd.DataFrame(rows)


def simple_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No data_"
    return frame.to_markdown(index=False)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    details = pd.concat(
        [build_policy_details(source, window) for source in ["python_only", "python_mt5"] for window in WINDOWS],
        ignore_index=True,
    )
    export_csv(details, OUT_DIR / "m15_raw_parent_gate_policy_details.csv")

    summaries = pd.concat(
        [summarize_policy(details, policy) for policy in ["strict_parent", "protect_reliable_parent", "conservative_cause"]],
        ignore_index=True,
    )
    export_csv(summaries, OUT_DIR / "m15_raw_parent_gate_policy_summary.csv")

    best_safe = summaries[summaries["reliable_matched_rejected"] == 0].copy()
    if not best_safe.empty:
        best_safe = best_safe.sort_values(
            ["unmatched_rejected", "relaxed_matched_rejected", "window_minutes"],
            ascending=[False, True, True],
        )
    export_csv(best_safe, OUT_DIR / "m15_raw_parent_gate_safe_policy_candidates.csv")

    strict = summaries[summaries["policy"] == "strict_parent"].copy()
    conservative = summaries[summaries["policy"] == "conservative_cause"].copy()
    report = [
        "# M15 Raw Parent Gate Prototype",
        "",
        "## Strict Parent Policy",
        simple_table(strict),
        "",
        "## Conservative Cause Policy",
        simple_table(conservative),
        "",
        "## Safe Policy Candidates",
        simple_table(best_safe.head(20)),
        "",
        "## Interpretation",
        "- `strict_parent` is the direct rule: reject every MT5 M15 SLOT1 post_n without a nearby Python M30 accepted parent.",
        "- `protect_reliable_parent` is a diagnostic upper bound; it shows what happens if already reliable matches are protected.",
        "- `conservative_cause` rejects only unmatched rows with no parent, no nearby same M15 post_n, and a rejectable cause bucket.",
        "- A policy is not safe for EA migration if `reliable_matched_rejected > 0`.",
        "",
        "## Output Files",
        "- `m15_raw_parent_gate_policy_details.csv`",
        "- `m15_raw_parent_gate_policy_summary.csv`",
        "- `m15_raw_parent_gate_safe_policy_candidates.csv`",
    ]
    write_text(OUT_DIR / "m15_raw_parent_gate_prototype_report.md", "\n".join(report))


if __name__ == "__main__":
    main()
