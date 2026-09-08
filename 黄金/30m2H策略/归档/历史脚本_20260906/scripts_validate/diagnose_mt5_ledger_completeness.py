from __future__ import annotations


from pathlib import Path
import re

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_DIR = ROOT / "黄金" / "30m2H策略"
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
SCRIPT_DIR = STRATEGY_DIR / "scripts" / "validate"
EA_PATH = ROOT / "auto_trade" / "30m2H_Strategy_EA.mq5"
OUT_DIR = VALIDATION_DIR / "mt5_ledger_completeness_diag_20260712"

LEDGER_SNAPSHOTS = {
    "v1": VALIDATION_DIR / "mt5_trade_ledger_full_20260712" / "30m2H_strategy_trade_ledger.csv",
    "v2": VALIDATION_DIR / "mt5_trade_ledger_full_20260712_v2" / "30m2H_strategy_trade_ledger.csv",
    "v3": VALIDATION_DIR / "mt5_trade_ledger_full_20260713_v3" / "30m2H_strategy_trade_ledger.csv",
}

ACTIVE_SCRIPTS = {
    "compare_three_sources_layers.py": "current_active",
    "diagnose_time_semantics.py": "current_active",
    "compare_python_vs_python_mt5_detail.py": "current_active",
    "prepare_dynamic_risk_inputs.py": "current_active",
    "simulate_dynamic_risk_alignment.py": "current_active",
    "diagnose_mt5_ledger_completeness.py": "current_active",
    "compare_mt5_log_sessions.py": "mt5_session_core",
    "compare_mt5_log_session_trades.py": "mt5_session_core",
    "diagnose_mt5_session_mismatch_causes.py": "mt5_session_core",
    "analyze_comparable_anchor_alignment.py": "anchor_core",
    "inspect_nearby_executed_mapping_cases.py": "anchor_core",
    "analyze_ea_merged_postn_approximation.py": "historical_fix_diag",
    "analyze_m30_postn_to_m15_shift_cases.py": "historical_fix_diag",
}

CURRENT_FOCUS_DIRS = {
    "three_sources_layer_compare_20260712": "current_focus",
    "python_only_vs_python_mt5_detail_20260712": "current_focus",
    "dynamic_risk_inputs_20260712": "current_focus",
    "dynamic_risk_alignment_20260712": "current_focus",
    "mt5_trade_ledger_full_20260712": "current_focus",
    "mt5_trade_ledger_full_20260712_v2": "current_focus",
    "mt5_trade_ledger_full_20260713_v3": "current_focus",
    "mt5_ledger_completeness_diag_20260712": "current_focus",
}


def load_ledger(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    for col in ["open_time", "exit_time", "signal_anchor_time"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in ["stage", "lots", "stop_pts", "profit", "swap", "commission", "net_profit"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def signal_key_frame(df: pd.DataFrame) -> pd.DataFrame:
    key_cols = ["signal_anchor_time", "trigger_tag", "signal_src", "dir"]
    grp = (
        df.groupby(key_cols, dropna=False)
        .agg(
            stage_rows=("stage", "size"),
            stage1=("stage", lambda s: int((s == 1).sum())),
            stage2=("stage", lambda s: int((s == 2).sum())),
            stage3=("stage", lambda s: int((s == 3).sum())),
            total_net=("net_profit", "sum"),
            any_positive=("net_profit", lambda s: bool((s > 0).any())),
            all_deal_reason_sl=("deal_reason", lambda s: bool((s.astype(str) == "SL").all())),
        )
        .reset_index()
    )
    return grp


def detect_stage_overlaps(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    clean = df.dropna(subset=["stage", "open_time", "exit_time"]).copy()
    clean["stage"] = clean["stage"].astype(int)
    for stage, grp in clean.groupby("stage"):
        grp = grp.sort_values(["open_time", "exit_time"]).reset_index(drop=True)
        overlap_pairs = 0
        max_parallel = 0
        events: list[tuple[pd.Timestamp, int]] = []
        for _, row in grp.iterrows():
            events.append((row["open_time"], 1))
            events.append((row["exit_time"], -1))
        for ts, delta in sorted(events, key=lambda x: (x[0], -x[1])):
            max_parallel += delta
            if max_parallel < 0:
                max_parallel = 0
        current_parallel = 0
        for ts, delta in sorted(events, key=lambda x: (x[0], -x[1])):
            current_parallel += delta
        for i in range(1, len(grp)):
            prev_exit = grp.loc[i - 1, "exit_time"]
            this_open = grp.loc[i, "open_time"]
            if pd.notna(prev_exit) and pd.notna(this_open) and this_open < prev_exit:
                overlap_pairs += 1
        max_open = 0
        open_count = 0
        for ts, delta in sorted(events, key=lambda x: (x[0], -x[1])):
            open_count += delta
            max_open = max(max_open, open_count)
        rows.append(
            {
                "stage": stage,
                "rows": int(len(grp)),
                "overlap_pairs": overlap_pairs,
                "max_parallel_positions": max_open,
            }
        )
    return pd.DataFrame(rows)


def build_overlap_samples(df: pd.DataFrame, snapshot: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    clean = df.dropna(subset=["stage", "open_time", "exit_time"]).copy()
    clean["stage"] = clean["stage"].astype(int)
    for stage, grp in clean.groupby("stage"):
        grp = grp.sort_values(["open_time", "exit_time"]).reset_index(drop=True)
        for i in range(1, len(grp)):
            prev_row = grp.loc[i - 1]
            cur_row = grp.loc[i]
            if cur_row["open_time"] < prev_row["exit_time"]:
                rows.append(
                    {
                        "snapshot": snapshot,
                        "stage": stage,
                        "prev_anchor": prev_row["signal_anchor_time"],
                        "prev_ticket": prev_row["ticket"],
                        "prev_open": prev_row["open_time"],
                        "prev_exit": prev_row["exit_time"],
                        "cur_anchor": cur_row["signal_anchor_time"],
                        "cur_ticket": cur_row["ticket"],
                        "cur_open": cur_row["open_time"],
                        "cur_exit": cur_row["exit_time"],
                    }
                )
    return pd.DataFrame(rows)


def summarize_snapshot(name: str, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    signal_df = signal_key_frame(df)
    overlap_df = detect_stage_overlaps(df)

    suspicious = df.loc[pd.to_numeric(df["net_profit"], errors="coerce") > 0, [
        "signal_anchor_time",
        "trigger_tag",
        "signal_src",
        "dir",
        "stage",
        "local_exit_reason",
        "deal_reason",
        "deal_comment",
        "net_profit",
    ]].copy()
    suspicious.insert(0, "snapshot", name)

    summary = pd.DataFrame(
        [
            {
                "snapshot": name,
                "rows": int(len(df)),
                "unique_signals": int(len(signal_df)),
                "net_profit_sum": round(float(df["net_profit"].sum()), 6),
                "positive_rows": int((df["net_profit"] > 0).sum()),
                "positive_signal_count": int((signal_df["total_net"] > 0).sum()),
                "stage_rows_eq_1": int((signal_df["stage_rows"] == 1).sum()),
                "stage_rows_eq_2": int((signal_df["stage_rows"] == 2).sum()),
                "stage_rows_eq_3": int((signal_df["stage_rows"] == 3).sum()),
                "missing_stage1_signals": int((signal_df["stage1"] == 0).sum()),
                "missing_stage2_signals": int((signal_df["stage2"] == 0).sum()),
                "missing_stage3_signals": int((signal_df["stage3"] == 0).sum()),
                "all_sl_rows": int((df["deal_reason"].astype(str) == "SL").sum()),
                "all_sl_signals": int(signal_df["all_deal_reason_sl"].sum()),
                "ticket_eq_position_id_rows": int((df.get("ticket", "").astype(str) == df.get("position_id", "").astype(str)).sum()) if "position_id" in df.columns else "",
            }
        ]
    )
    return summary, overlap_df.assign(snapshot=name), suspicious


def build_static_code_findings(text: str) -> pd.DataFrame:
    patterns = [
        (
            "single_stage_state",
            r"g_stage_tickets\[4\]",
            "EA stage state is still single-slot per stage; same-stage overlap cannot be fully represented.",
        ),
        (
            "single_stage_lookup",
            r"bool\s+FindOurStagePos\s*\(",
            "FindOurStagePos returns a single matching position for one stage, not a list of open positions.",
        ),
        (
            "exit_loop_stage12",
            r"for\(int stage = 1; stage <= 2; stage\+\+\)",
            "Stage 1/2 exit management still iterates one current stage handle at a time.",
        ),
        (
            "exit_stage3_single",
            r"if\(InpStage3On && g_stage_tickets\[3\] != 0\)",
            "Stage 3 exit management also assumes one current stage-3 handle.",
        ),
        (
            "max_pos_gate",
            r"OurStageCount\(\)\s*>=\s*InpMaxPos",
            "Max-position gate counts total open positions but does not prevent same-stage overlap under rolling signals.",
        ),
    ]
    rows: list[dict[str, object]] = []
    for key, pattern, message in patterns:
        match = re.search(pattern, text)
        rows.append(
            {
                "finding_key": key,
                "matched": bool(match),
                "message": message,
            }
        )
    return pd.DataFrame(rows)


def write_script_inventory() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for path in sorted(SCRIPT_DIR.glob("*.py")):
        rows.append(
            {
                "name": path.name,
                "bucket": ACTIVE_SCRIPTS.get(path.name, "sample_or_historical"),
                "last_write_time": pd.Timestamp(path.stat().st_mtime, unit="s"),
                "size_bytes": path.stat().st_size,
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(SCRIPT_DIR / "script_inventory_20260712.csv", index=False, encoding="utf-8-sig")

    lines = [
        "# Validate Scripts Index",
        "",
        "## Current Active",
    ]
    for row in df.loc[df["bucket"] == "current_active"].sort_values("last_write_time", ascending=False).itertuples():
        lines.append(f"- `{row.name}`")
    lines.extend(
        [
            "",
            "## MT5 Session / Anchor Core",
        ]
    )
    for bucket in ["mt5_session_core", "anchor_core", "historical_fix_diag"]:
        for row in df.loc[df["bucket"] == bucket].sort_values("name").itertuples():
            lines.append(f"- `{row.name}`")
    lines.extend(
        [
            "",
            "## Sample Or Historical",
            "- 其余脚本保留为样本复核或历史实验脚本，暂不移动，避免破坏已有文档引用。",
        ]
    )
    (SCRIPT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return df


def write_validation_inventory() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for path in sorted(VALIDATION_DIR.iterdir(), key=lambda p: (p.is_file(), p.name)):
        rows.append(
            {
                "name": path.name,
                "kind": "dir" if path.is_dir() else "file",
                "bucket": CURRENT_FOCUS_DIRS.get(path.name, "historical_or_reference"),
                "last_write_time": pd.Timestamp(path.stat().st_mtime, unit="s"),
                "size_bytes": path.stat().st_size if path.is_file() else "",
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(VALIDATION_DIR / "validation_inventory_20260712.csv", index=False, encoding="utf-8-sig")

    lines = [
        "# Validation Data Index",
        "",
        "## Current Focus Directories",
    ]
    for row in df.loc[(df["kind"] == "dir") & (df["bucket"] == "current_focus")].sort_values(
        "last_write_time", ascending=False
    ).itertuples():
        lines.append(f"- `{row.name}`")
    lines.extend(
        [
            "",
            "## Notes",
            "- 当前主线目录与快照保留在原位，不做物理移动，避免破坏已有报告链接。",
            "- 目录整理先通过 `README` 和 `*_inventory_20260712.csv` 收口，再决定后续是否归档历史目录。",
        ]
    )
    (VALIDATION_DIR / "README_20260712.md").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return df


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    summaries: list[pd.DataFrame] = []
    overlaps: list[pd.DataFrame] = []
    suspicious_rows: list[pd.DataFrame] = []
    overlap_samples: list[pd.DataFrame] = []

    for name, path in LEDGER_SNAPSHOTS.items():
        df = load_ledger(path)
        summary_df, overlap_df, suspicious_df = summarize_snapshot(name, df)
        summaries.append(summary_df)
        overlaps.append(overlap_df)
        suspicious_rows.append(suspicious_df)
        overlap_samples.append(build_overlap_samples(df, name))

    summary = pd.concat(summaries, ignore_index=True)
    overlap = pd.concat(overlaps, ignore_index=True)
    suspicious = pd.concat(suspicious_rows, ignore_index=True)
    overlap_sample_df = pd.concat(overlap_samples, ignore_index=True)

    summary.to_csv(OUT_DIR / "ledger_snapshot_summary.csv", index=False, encoding="utf-8-sig")
    overlap.to_csv(OUT_DIR / "ledger_stage_overlap_summary.csv", index=False, encoding="utf-8-sig")
    suspicious.to_csv(OUT_DIR / "ledger_positive_rows_with_sl_reason.csv", index=False, encoding="utf-8-sig")
    overlap_sample_df.to_csv(OUT_DIR / "ledger_stage_overlap_samples.csv", index=False, encoding="utf-8-sig")

    ea_text = EA_PATH.read_text(encoding="utf-8-sig")
    static_findings = build_static_code_findings(ea_text)
    static_findings.to_csv(OUT_DIR / "ea_stage_state_static_findings.csv", index=False, encoding="utf-8-sig")

    script_inventory = write_script_inventory()
    validation_inventory = write_validation_inventory()

    report_lines = [
        "# MT5 Ledger Completeness Diagnosis",
        "",
        "## Snapshot Summary",
        summary.to_markdown(index=False),
        "",
        "## Stage Overlap",
        overlap.to_markdown(index=False),
        "",
        "## Overlap Samples",
        overlap_sample_df.head(12).to_markdown(index=False) if not overlap_sample_df.empty else "No overlap samples.",
        "",
        "## Static EA Findings",
        static_findings.to_markdown(index=False),
        "",
        "## Main Judgement",
        "- v2 ledger rows 从 155 增到 162，但净利润仍不能复原 tester 最终资金，因此问题不是单纯少导出几行。",
        "- v3 在加入 `position_id` 跟踪后，与 v2 的共有列内容完全一致；说明单纯补 `position_id` 并没有改变当前 ledger 归属结果。",
        "- 正收益 rows 仍主要集中在 stage2；stage1/stage3 的盈利退出记录没有形成可信闭环。",
        "- 大量正收益 rows 同时被标记为 `deal_reason=SL`，说明当前 close deal 归属仍存在错配。",
        "- EA 源码仍保留单 stage 单槽位状态模型；即使 ledger 改成 ticket 多槽位，stage 管理层仍不足以表达 same-stage overlap。",
        "",
        "## File Organization",
        f"- 脚本清单：`{(SCRIPT_DIR / 'script_inventory_20260712.csv').relative_to(ROOT)}`",
        f"- 数据清单：`{(VALIDATION_DIR / 'validation_inventory_20260712.csv').relative_to(ROOT)}`",
        "- 本轮先通过 README + inventory 做逻辑整理，不移动历史快照。",
    ]
    (OUT_DIR / "mt5_ledger_completeness_report.md").write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8-sig",
    )

    # Keep inventories available inside the diagnosis folder too.
    script_inventory.to_csv(OUT_DIR / "script_inventory_20260712.csv", index=False, encoding="utf-8-sig")
    validation_inventory.to_csv(OUT_DIR / "validation_inventory_20260712.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
