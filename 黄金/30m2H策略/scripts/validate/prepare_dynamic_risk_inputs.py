from __future__ import annotations


from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_DIR = ROOT / "黄金" / "30m2H策略"
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation" / "dynamic_risk_inputs_20260712"


@dataclass(frozen=True)
class SourceConfig:
    name: str
    signals_dir: Path


SOURCES = [
    SourceConfig("python_only", STRATEGY_DIR / "data" / "signals"),
    SourceConfig("python_mt5", STRATEGY_DIR / "data" / "signals_mt5"),
]


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def prepare_source(cfg: SourceConfig) -> tuple[pd.DataFrame, dict[str, int | str]]:
    layer3_path = cfg.signals_dir / "最终信号_Layer3入选.csv"
    stage_path = cfg.signals_dir / "执行交易_Stage结果.csv"

    layer3 = load_csv(layer3_path).copy()
    stage = load_csv(stage_path).copy()

    if "信号层级" in layer3.columns:
        layer3 = layer3.drop(columns=["信号层级"])
    if "信号层级" in stage.columns:
        stage = stage.drop(columns=["信号层级"])
    if "year" in stage.columns and "year" in layer3.columns:
        stage = stage.drop(columns=["year"])

    key_cols = ["date", "mode", "dir"]
    layer3["date"] = pd.to_datetime(layer3["date"])
    stage["date"] = pd.to_datetime(stage["date"])

    layer3_dupes = int(layer3.duplicated(subset=key_cols).sum())
    stage_dupes = int(stage.duplicated(subset=key_cols).sum())

    merged = layer3.merge(
        stage,
        on=key_cols,
        how="outer",
        indicator=True,
        suffixes=("_signal", "_stage"),
    )

    merged["source"] = cfg.name
    merged["stop_price_diff"] = (merged["entry"] - merged["stop"]).abs()
    merged["stop_pts_spec"] = merged["stop_price_diff"]
    merged["stop_pts_mql5"] = merged["stop_price_diff"] * 1000.0
    merged["signal_stage_pnl_gap"] = merged["pnl"] - merged["total_$"]

    stats = {
        "source": cfg.name,
        "layer3_rows": int(len(layer3)),
        "stage_rows": int(len(stage)),
        "merged_rows": int(len(merged)),
        "signal_only_rows": int((merged["_merge"] == "left_only").sum()),
        "stage_only_rows": int((merged["_merge"] == "right_only").sum()),
        "matched_rows": int((merged["_merge"] == "both").sum()),
        "layer3_dupe_keys": layer3_dupes,
        "stage_dupe_keys": stage_dupes,
        "min_stop_pts_spec": round(float(merged["stop_pts_spec"].dropna().min()), 6) if merged["stop_pts_spec"].notna().any() else "",
        "max_stop_pts_spec": round(float(merged["stop_pts_spec"].dropna().max()), 6) if merged["stop_pts_spec"].notna().any() else "",
    }
    return merged, stats


def main() -> None:
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)

    merged_frames: list[pd.DataFrame] = []
    stats_rows: list[dict[str, int | str]] = []

    for cfg in SOURCES:
        merged, stats = prepare_source(cfg)
        merged_frames.append(merged)
        stats_rows.append(stats)
        merged.to_csv(
            VALIDATION_DIR / f"{cfg.name}_dynamic_risk_inputs.csv",
            index=False,
            encoding="utf-8-sig",
        )

    stats_df = pd.DataFrame(stats_rows)
    stats_df.to_csv(
        VALIDATION_DIR / "dynamic_risk_input_prepare_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    report_lines = [
        "# Dynamic Risk Input Preparation",
        "",
        "## Summary",
    ]
    for row in stats_rows:
        report_lines.extend(
            [
                f"### {row['source']}",
                f"- Layer3 rows: `{row['layer3_rows']}`",
                f"- Stage rows: `{row['stage_rows']}`",
                f"- Matched rows: `{row['matched_rows']}`",
                f"- Signal-only rows: `{row['signal_only_rows']}`",
                f"- Stage-only rows: `{row['stage_only_rows']}`",
                f"- Layer3 duplicate keys: `{row['layer3_dupe_keys']}`",
                f"- Stage duplicate keys: `{row['stage_dupe_keys']}`",
                f"- Stop range (spec pts): `{row['min_stop_pts_spec']} ~ {row['max_stop_pts_spec']}`",
                "",
            ]
        )
    report_lines.extend(
        [
            "## Notes",
            "- `stop_pts_spec = abs(entry - stop)`.",
            "- `stop_pts_mql5 = stop_pts_spec * 1000` aligns with the EA comment `1 spec 点 = 1000 MQL5 points`.",
            "- `signal_stage_pnl_gap = Layer3 pnl - Stage total_$` is kept only as a diagnostic helper; it is not yet the final dynamic-risk formula.",
        ]
    )

    (VALIDATION_DIR / "dynamic_risk_input_prepare_report.md").write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8-sig",
    )


if __name__ == "__main__":
    main()
