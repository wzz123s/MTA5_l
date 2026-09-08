# -*- coding: utf-8 -*-
"""Audit EA/Python SLOT1 post_n counter generation for mt5_0076.

This is diagnostic-only. It does not mutate signal snapshots, EA code, mapping,
or dynamic-risk outputs.
"""

from __future__ import annotations


import re
from pathlib import Path

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_DIR = ROOT / "黄金" / "30m2H策略"
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_ea_python_slot1_counter_generation_mt5_0076_20260717"

ANCHOR_DIR = VALIDATION_DIR / "stage_state_mt5_0076_postn_counter_anchor_audit_20260717"
MT5_STAGE_DIR = VALIDATION_DIR / "mt5_stage_state_full_2018_20260707_20260716"

EA_SOURCE = ROOT / "auto_trade" / "30m2H_Strategy_EA.mq5"
PY_CURRENT_BASELINE = ROOT / "scripts" / "_current_baseline.py"
PY_M15 = ROOT / "scripts" / "_m15_early_entry_test.py"
PY_COMBO = ROOT / "scripts" / "_m15_h2_combo_test.py"

TARGET_ID = "mt5_0076"
TARGET_DATE_DOTTED = "2026.03.24"
TARGET_TIMES = [
    "08:00",
    "08:15",
    "08:30",
    "08:45",
    "09:00",
    "09:15",
    "09:30",
    "09:45",
    "10:00",
    "10:15",
    "10:30",
    "10:45",
    "11:00",
    "11:15",
    "11:30",
    "11:45",
    "12:00",
    "12:15",
    "12:30",
]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def read_lines(path: Path) -> list[str]:
    for enc in ("utf-8-sig", "utf-16", "utf-16-le", "gb18030", "cp936"):
        try:
            return path.read_text(encoding=enc).splitlines()
        except UnicodeError:
            continue
    return path.read_text(errors="ignore").splitlines()


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def write_md(lines: list[str], path: Path) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def find_code_hits() -> pd.DataFrame:
    files = [
        (
            "ea_source",
            EA_SOURCE,
            [
                ("ea_global_merged_counter", r"int\s+g_merged_post_n_counter"),
                ("ea_global_raw_counter", r"int\s+g_post_n_counter"),
                ("ea_update_merged_counter", r"void\s+UpdateMergedPostNState"),
                ("ea_slot1_uses_merged_counter", r"merged_post_n\s*=\s*g_merged_post_n_counter"),
                (
                    "ea_slot1_postn_label_from_merged_counter",
                    r'signal_src\s*=\s*"post_n"\s*\+\s*IntegerToString\((?:-|)merged_post_n\)',
                ),
                ("ea_replace_rescue_suffix_is_after_label", r"signal_src\s*=\s*signal_src\s*\+\s*\"_replace_or_rescue\""),
                ("ea_diag_writes_both_counters", r"post_n_counter=.*merged_post_n_counter"),
                ("ea_m15_diag_header_counters", r'"post_n_counter",\s*"merged_post_n_counter"'),
            ],
        ),
        (
            "python_current_baseline",
            PY_CURRENT_BASELINE,
            [
                ("python_replace_variant_name", r'"ea_slot1_replace"'),
                ("python_runtime_rescue_variant_name", r'variant_name="ea_slot1_runtime_rescue"'),
                ("python_m15_replace_entry", r"apply_replace_variant"),
                ("python_m15_runtime_rescue_entry", r"build_rescued_trades"),
            ],
        ),
        (
            "python_m15_generation",
            PY_M15,
            [
                ("python_postn_from_merged_post_cross_n", r"post_n\s*=\s*df\[POST_COL\]\.values"),
                ("python_raw_postn_label", r'f"post_n\{abs\(pn\)\}"'),
                ("python_replace_only_changes_entry_time", r'out\["entry_time"\]\s*=\s*entry_time'),
                ("python_replace_only_changes_variant", r'out\["variant"\]\s*=\s*variant'),
                ("python_apply_replace_variant", r"def\s+apply_replace_variant"),
                ("python_runtime_rescue", r"def\s+build_rescued_trades"),
            ],
        ),
        (
            "python_combo_generation",
            PY_COMBO,
            [
                ("python_raw_candidate_frames", r"def\s+build_candidate_frames"),
                ("python_accepted_dedupe_anchor", r"accepted\s*=\s*m15t\.dedupe_anchor"),
            ],
        ),
    ]

    rows: list[dict[str, object]] = []
    for source_name, path, patterns in files:
        lines = read_lines(path)
        for line_no, line in enumerate(lines, start=1):
            for pattern_name, pattern in patterns:
                if re.search(pattern, line):
                    rows.append(
                        {
                            "source_name": source_name,
                            "path": str(path.relative_to(ROOT)),
                            "line_number": line_no,
                            "pattern_name": pattern_name,
                            "line": line.strip(),
                        }
                    )
    return pd.DataFrame(rows)


def scan_logs() -> pd.DataFrame:
    log_paths = [
        ("terminal_20260716", MT5_STAGE_DIR / "terminal_20260716.log"),
        ("tester_agent_20260716", MT5_STAGE_DIR / "tester_agent_20260716.log"),
    ]
    time_patterns = [f"{TARGET_DATE_DOTTED} {time}" for time in TARGET_TIMES]
    keep_tokens = [
        "[M15 SLOT1]",
        "[M30 CLOSE]",
        "[SIGNAL]",
        "[DIAG]",
        "post_n5_m15_slot1_replace_or_rescue",
        "merged_post_n_counter=5",
        "post_n_counter=3",
        "post_n_counter=5",
    ]

    rows: list[dict[str, object]] = []
    for log_name, path in log_paths:
        if not path.exists():
            rows.append(
                {
                    "log_name": log_name,
                    "line_number": None,
                    "match_kind": "missing_log",
                    "line": str(path),
                }
            )
            continue
        for line_no, line in enumerate(read_lines(path), start=1):
            has_target_time = any(token in line for token in time_patterns)
            has_explicit_target = "post_n5_m15_slot1_replace_or_rescue" in line
            has_relevant_token = any(token in line for token in keep_tokens)
            if (has_target_time and has_relevant_token) or has_explicit_target:
                match_kind = "target_window" if has_target_time else "signal_src_all_history"
                rows.append(
                    {
                        "log_name": log_name,
                        "line_number": line_no,
                        "match_kind": match_kind,
                        "line": line.strip(),
                    }
                )
                if len(rows) >= 300:
                    break
    return pd.DataFrame(rows)


def load_legacy_m15_diag_window() -> pd.DataFrame:
    """Use the old M15 diagnostic CSV only as supplemental provenance if present."""
    path = VALIDATION_DIR / "ea_m15_entry_diag_full_20260715" / "30m2H_strategy_m15_entry_diag.csv"
    if not path.exists():
        return pd.DataFrame(
            [
                {
                    "diag_source": "legacy_m15_entry_diag_20260715",
                    "result": "missing",
                    "note": str(path),
                }
            ]
        )
    df = read_csv(path)
    for col in ["time", "current_m30_bar", "completed_m15_open", "anchor_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", format="%Y.%m.%d %H:%M:%S")
    mask = (
        df.get("anchor_time", pd.Series(pd.NaT, index=df.index)).between(
            pd.Timestamp("2026-03-24 08:00"), pd.Timestamp("2026-03-24 12:30")
        )
        | df.get("completed_m15_open", pd.Series(pd.NaT, index=df.index)).between(
            pd.Timestamp("2026-03-24 08:00"), pd.Timestamp("2026-03-24 12:30")
        )
        | df.get("current_m30_bar", pd.Series(pd.NaT, index=df.index)).between(
            pd.Timestamp("2026-03-24 08:00"), pd.Timestamp("2026-03-24 12:30")
        )
    )
    out = df[mask].copy()
    out.insert(0, "diag_source", "legacy_m15_entry_diag_20260715")
    return out


def classify(
    code_hits: pd.DataFrame,
    log_hits: pd.DataFrame,
    alignment: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, object]]:
    hit_names = set(code_hits["pattern_name"].astype(str)) if len(code_hits) else set()

    ea_uses_merged_counter = {
        "ea_global_merged_counter",
        "ea_slot1_uses_merged_counter",
        "ea_slot1_postn_label_from_merged_counter",
        "ea_replace_rescue_suffix_is_after_label",
    }.issubset(hit_names)
    python_preserves_raw_label = {
        "python_postn_from_merged_post_cross_n",
        "python_raw_postn_label",
        "python_replace_only_changes_entry_time",
        "python_replace_only_changes_variant",
    }.issubset(hit_names)

    actual_anchor_rows = alignment[
        (alignment["source_table"].eq("python_layer12_pass"))
        & (alignment["matches_actual_anchor_time"].astype(str).str.lower().eq("true"))
    ].copy()
    same_label_rows = alignment[
        (alignment["source_table"].eq("python_layer12_pass"))
        & (alignment["matches_mt5_mode_label"].astype(str).str.lower().eq("true"))
    ].copy()
    aligned_rows = alignment[
        (alignment["source_table"].eq("python_layer12_pass"))
        & (alignment["matches_aligned_plus90_time"].astype(str).str.lower().eq("true"))
    ].copy()

    line_text = log_hits["line"].astype(str) if len(log_hits) else pd.Series(dtype=str)
    target_log_lines = log_hits[line_text.str.contains(TARGET_DATE_DOTTED, na=False)].copy() if len(log_hits) else log_hits
    target_line_text = target_log_lines["line"].astype(str) if len(target_log_lines) else pd.Series(dtype=str)

    signal_src_all_history_hits = (
        int(line_text.str.contains("post_n5_m15_slot1_replace_or_rescue", na=False).sum())
        if len(log_hits)
        else 0
    )
    target_log_signal_hits = (
        int(target_line_text.str.contains("post_n5_m15_slot1_replace_or_rescue", na=False).sum())
        if len(target_log_lines)
        else 0
    )
    target_log_merged_counter5_hits = (
        int(target_line_text.str.contains("merged_post_n_counter=5", na=False).sum())
        if len(target_log_lines)
        else 0
    )
    target_log_raw_counter5_hits = (
        int(target_line_text.str.contains("post_n_counter=5", na=False).sum()) if len(target_log_lines) else 0
    )
    target_log_both_counter5_hits = (
        int(
            (
                target_line_text.str.contains("post_n_counter=5", na=False)
                & target_line_text.str.contains("merged_post_n_counter=5", na=False)
            ).sum()
        )
        if len(target_log_lines)
        else 0
    )

    classifications: list[str] = []
    if ea_uses_merged_counter:
        classifications.append("merged_postn_counter_offset")
    else:
        classifications.append("log_insufficient")
    if python_preserves_raw_label:
        classifications.append("python_slot1_relabel_gap")
    if target_log_signal_hits == 0 or target_log_both_counter5_hits == 0:
        classifications.append("log_insufficient")

    primary = "merged_postn_counter_offset" if ea_uses_merged_counter else "log_insufficient"
    prototype_gate = bool(ea_uses_merged_counter and python_preserves_raw_label and target_log_both_counter5_hits > 0)

    summary = {
        "target_mt5_id": TARGET_ID,
        "ea_counter_source": "g_merged_post_n_counter" if ea_uses_merged_counter else "unproven",
        "ea_counter_source_classification": primary,
        "python_counter_source": (
            "raw M30 merged_post_cross_n label preserved through SLOT1 replace/rescue"
            if python_preserves_raw_label
            else "unproven"
        ),
        "actual_anchor_python_modes": ";".join(actual_anchor_rows.get("mode", pd.Series(dtype=str)).astype(str).tolist()),
        "same_mode_label_python_times": ";".join(same_label_rows.get("row_time", pd.Series(dtype=str)).astype(str).tolist()),
        "aligned_plus90_python_modes": ";".join(aligned_rows.get("mode", pd.Series(dtype=str)).astype(str).tolist()),
        "target_log_signal_src_hits": int(target_log_signal_hits),
        "target_log_raw_counter5_hits": int(target_log_raw_counter5_hits),
        "target_log_merged_counter5_hits": int(target_log_merged_counter5_hits),
        "target_log_both_counter5_hits": int(target_log_both_counter5_hits),
        "signal_src_all_history_hits": int(signal_src_all_history_hits),
        "classifications": ";".join(dict.fromkeys(classifications)),
        "primary_classification": primary,
        "main_signal_change_gate_open": False,
        "ea_behavior_gate_open": False,
        "mapping_change_gate_open": False,
        "low_blast_prototype_gate_open": prototype_gate,
        "merge_gate_pass": False,
        "recommended_next_action": (
            "quantify_all_m15_slot1_postn_legacy_merged_counter_drift_before_any_code_prototype"
        ),
    }

    decision = pd.DataFrame([summary])
    return decision, summary


def build_markdown(
    summary: dict[str, object],
    code_hits: pd.DataFrame,
    log_hits: pd.DataFrame,
    alignment: pd.DataFrame,
) -> list[str]:
    def val(key: str) -> object:
        return summary.get(key, "")

    actual_anchor = alignment[
        (alignment["source_table"].eq("python_layer12_pass"))
        & (alignment["matches_actual_anchor_time"].astype(str).str.lower().eq("true"))
    ]
    same_label = alignment[
        (alignment["source_table"].eq("python_layer12_pass"))
        & (alignment["matches_mt5_mode_label"].astype(str).str.lower().eq("true"))
    ]
    aligned = alignment[
        (alignment["source_table"].eq("python_layer12_pass"))
        & (alignment["matches_aligned_plus90_time"].astype(str).str.lower().eq("true"))
    ]

    lines = [
        "# Stage-State EA/Python SLOT1 Counter Generation Audit for mt5_0076",
        "",
        "## Final Decision",
        "",
        f"- Target: `{TARGET_ID}`.",
        f"- Primary classification: `{val('primary_classification')}`.",
        f"- Full classifications: `{val('classifications')}`.",
        f"- EA counter source: `{val('ea_counter_source')}`.",
        f"- Python counter source: `{val('python_counter_source')}`.",
        f"- Main signal gate: `{val('main_signal_change_gate_open')}`.",
        f"- EA behavior gate: `{val('ea_behavior_gate_open')}`.",
        f"- Mapping gate: `{val('mapping_change_gate_open')}`.",
        f"- Low-blast prototype gate: `{val('low_blast_prototype_gate_open')}`.",
        f"- Merge gate: `{val('merge_gate_pass')}`.",
        "",
        "## Evidence",
        "",
        "- EA `TryM15EarlyEntry()` assigns `merged_post_n = g_merged_post_n_counter`, then formats `post_nN_m15_slot1`; `_replace_or_rescue` is appended after the label is already created.",
        "- No independent M15 SLOT1 post_n counter is visible in the current EA source; the M15 path borrows the legacy merged counter.",
        "- Python builds `post_nN` from the M30 row's `merged_post_cross_n`; `ea_slot1_replace` / `ea_slot1_runtime_rescue` only changes `entry_time`, `entry`, stop handling and `variant`, not the `mode` label.",
        f"- At the MT5 real anchor, Python Layer1/2 rows: `{len(actual_anchor)}`; modes: `{';'.join(actual_anchor.get('mode', pd.Series(dtype=str)).astype(str).tolist())}`.",
        f"- Python same-label `post_n5` occurs at: `{';'.join(same_label.get('row_time', pd.Series(dtype=str)).astype(str).tolist())}`.",
        f"- Python +90 aligned rows: `{len(aligned)}`; modes: `{';'.join(aligned.get('mode', pd.Series(dtype=str)).astype(str).tolist())}`.",
        f"- Target-window log `post_n5_m15_slot1_replace_or_rescue` hits: `{val('target_log_signal_src_hits')}`.",
        f"- Target-window log `post_n_counter=5` hits: `{val('target_log_raw_counter5_hits')}`.",
        f"- Target-window log `merged_post_n_counter=5` hits: `{val('target_log_merged_counter5_hits')}`.",
        f"- Target-window log both counters equal 5 hits: `{val('target_log_both_counter5_hits')}`.",
        f"- Full-log same signal-src hits: `{val('signal_src_all_history_hits')}`.",
        "",
        "## Interpretation",
        "",
        "- `post_n5_m15_slot1_replace_or_rescue` is not created by replace/rescue recalculating a SLOT1-local counter.",
        "- It is best explained as the EA M15 branch inheriting the EA legacy `g_merged_post_n_counter` value at runtime.",
        "- Python's `post_n3` at `2026-03-24 10:30` is the raw M30 `post_n3` candidate whose entry is moved to `10:15` by SLOT1 replace.",
        "- Therefore, the mismatch is a counter-source gap first, and a replace/rescue relabeling gap second.",
        "",
        "## Risk",
        "",
        "- A direct change to `g_merged_post_n_counter` is not safe: earlier global and M15 strict-counter expansions were rejected by full tester.",
        "- The next step should quantify all M15 SLOT1 post_n cases where EA's legacy merged counter disagrees with Python `merged_post_cross_n`, then design a low-blast prototype only if the cohort is coherent.",
        "",
        "## Outputs",
        "",
        "- `slot1_counter_generation_final_decision.csv`",
        "- `slot1_counter_generation_code_hits.csv`",
        "- `slot1_counter_generation_log_hits.csv`",
        "- `slot1_counter_generation_candidate_alignment.csv`",
        "- `slot1_counter_generation_legacy_m15_diag_window.csv`",
    ]

    code_count = len(code_hits)
    log_count = len(log_hits)
    lines.extend(
        [
            "",
            "## Counts",
            "",
            f"- Code evidence rows: `{code_count}`.",
            f"- Current log evidence rows: `{log_count}`.",
        ]
    )
    return lines


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    alignment = read_csv(ANCHOR_DIR / "postn_counter_anchor_candidate_alignment.csv")
    code_hits = find_code_hits()
    log_hits = scan_logs()
    legacy_diag = load_legacy_m15_diag_window()
    decision, summary = classify(code_hits, log_hits, alignment)
    md_lines = build_markdown(summary, code_hits, log_hits, alignment)

    write_csv(code_hits, OUT_DIR / "slot1_counter_generation_code_hits.csv")
    write_csv(log_hits, OUT_DIR / "slot1_counter_generation_log_hits.csv")
    write_csv(alignment, OUT_DIR / "slot1_counter_generation_candidate_alignment.csv")
    write_csv(legacy_diag, OUT_DIR / "slot1_counter_generation_legacy_m15_diag_window.csv")
    write_csv(decision, OUT_DIR / "slot1_counter_generation_final_decision.csv")
    write_md(md_lines, OUT_DIR / "slot1_counter_generation_audit.md")
    write_md(
        [
            "# Stage-State EA/Python SLOT1 Counter Generation Audit",
            "",
            "Diagnostic-only audit output for `mt5_0076`.",
            "",
            f"- Final decision: `{decision.loc[0, 'primary_classification']}`.",
            f"- Merge gate: `{decision.loc[0, 'merge_gate_pass']}`.",
        ],
        OUT_DIR / "README.md",
    )

    print(f"Wrote {OUT_DIR}")
    print(decision.to_string(index=False))


if __name__ == "__main__":
    main()
