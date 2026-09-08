# -*- coding: utf-8 -*-
"""Run dynamic-risk alignment from the shift90 input snapshot."""
from __future__ import annotations


import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import simulate_dynamic_risk_alignment as base  # noqa: E402


STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
INPUT_DIR = STRATEGY_DIR / "data" / "validation" / "dynamic_risk_inputs_shift90_20260713"
OUT_DIR = STRATEGY_DIR / "data" / "validation" / "dynamic_risk_alignment_shift90_20260713"


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    sources = [
        base.DynamicSource("python_only", INPUT_DIR / "python_only_dynamic_risk_inputs.csv"),
        base.DynamicSource("python_mt5", INPUT_DIR / "python_mt5_dynamic_risk_inputs.csv"),
    ]

    dynamic_summaries: list[dict[str, object]] = []
    overlap_frames: list[pd.DataFrame] = []

    mt5_df, mt5_summary = base.build_mt5_ledger_summary()
    export_csv(mt5_df, OUT_DIR / "mt5_ledger_unique_signals.csv")

    for cfg in sources:
        detail_df, summary = base.simulate_dynamic_source(cfg)
        detail_df["source_variant"] = "shift90_python_h2_context_q2early" if cfg.name == "python_mt5" else "baseline"
        summary["source_variant"] = "shift90_python_h2_context_q2early" if cfg.name == "python_mt5" else "baseline"
        dynamic_summaries.append(summary)
        export_csv(detail_df, OUT_DIR / f"{cfg.name}_dynamic_risk_trades.csv")

        overlap = base.compare_key_overlap(detail_df, mt5_df, cfg.name)
        overlap_frames.append(overlap)
        export_csv(overlap, OUT_DIR / f"{cfg.name}_vs_mt5_ledger_key_overlap.csv")

    mt5_summary["source_variant"] = "ledger_deinitfix_full_20260713_v1"
    summary_df = pd.DataFrame(dynamic_summaries + [mt5_summary])
    export_csv(summary_df, OUT_DIR / "dynamic_risk_compare_summary.csv")

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
    export_csv(overlap_summary_df, OUT_DIR / "dynamic_risk_key_overlap_summary.csv")

    report_lines = [
        "# Dynamic Risk Alignment - shift90",
        "",
        "## Summary",
        "",
        summary_df.to_markdown(index=False),
        "",
        "## Exact Key Overlap",
        "",
        overlap_summary_df.to_markdown(index=False) if not overlap_summary_df.empty else "No overlap rows.",
        "",
        "## Notes",
        "- Python-MT5 uses `dynamic_risk_inputs_shift90_20260713`.",
        "- Exact key overlap is kept as a coarse diagnostic; mapped trade alignment is the authoritative next step.",
        "- This output intentionally does not overwrite `dynamic_risk_alignment_magic0fix_20260713`.",
    ]
    write_text(OUT_DIR / "dynamic_risk_alignment_report.md", "\n".join(report_lines))

    print(summary_df.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
