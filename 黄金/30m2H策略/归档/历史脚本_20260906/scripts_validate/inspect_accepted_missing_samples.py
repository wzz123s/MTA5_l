# -*- coding: utf-8 -*-
"""Inspect full-history accepted-missing samples in detail."""
from __future__ import annotations


import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
ROOT_SCRIPTS_DIR = ROOT / "scripts"

sys.path.insert(0, str(STRATEGY_SCRIPTS_DIR))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT_SCRIPTS_DIR))

from strategy_30m2h_common import VALIDATION_DIR, export_csv, write_text  # noqa: E402
import _current_baseline as cb  # noqa: E402
import _h2_early_gate_test as h2t  # noqa: E402
import _m15_early_entry_test as m15t  # noqa: E402
import _m15_h2_combo_test as combo  # noqa: E402


OUTPUT_DIR = VALIDATION_DIR / "ea_python_full_history_alignment_20260709"
CLASSIFIED_PATH = OUTPUT_DIR / "普通剩余样本分层分类明细_20260709.csv"


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "| 空 | 空 |\n| --- | --- |"
    headers = list(frame.columns)
    lines = [
        "| " + " | ".join(str(x) for x in headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in headers) + " |")
    return "\n".join(lines)


def classify_row(raw_spec_reason: str, base_final_n: int, ea_final_n: int) -> str:
    if raw_spec_reason == "too_tight" and base_final_n == 0 and ea_final_n == 0:
        return "原始候选too_tight"
    if raw_spec_reason == "too_wide" and base_final_n == 1 and ea_final_n == 0:
        return "原始too_wide_旧rescue可救_当前EA口径未救回"
    if raw_spec_reason == "too_wide" and base_final_n == 0 and ea_final_n == 0:
        return "原始候选too_wide"
    if raw_spec_reason == "ok" and base_final_n == 0 and ea_final_n == 0:
        return "原始候选存在_但未进入accepted"
    return "待复核"


def main() -> None:
    detail = pd.read_csv(CLASSIFIED_PATH, encoding="utf-8-sig")
    missing = detail[detail["分层分类"] == "accepted层缺失"].copy().reset_index(drop=True)
    missing["对齐后时间"] = pd.to_datetime(missing["对齐后时间"])

    df, h2, m15 = cb.load_market_context()
    m15t.df_global = df
    q2_pass_set, q2_factor_map, _, _ = h2t.early_precompute(h2, df, 2, False)
    raw_df, accepted_raw = combo.build_candidate_frames(df, q2_pass_set, q2_factor_map)
    _, final_acc_ea = cb.build_final_accepted(ea_executable_diag=True)
    _, final_acc_base = cb.build_final_accepted(ea_executable_diag=False)

    for frame in [raw_df, accepted_raw, final_acc_ea, final_acc_base]:
        if not frame.empty:
            frame["date"] = pd.to_datetime(frame["date"])

    rows = []
    rescue_probe_targets = []
    for _, row in missing.iterrows():
        anchor = pd.Timestamp(row["对齐后时间"])
        direction = row["方向"]
        raw_same = raw_df[(raw_df["date"] == anchor) & (raw_df["dir"] == direction)].copy()
        accepted_same = accepted_raw[(accepted_raw["date"] == anchor) & (accepted_raw["dir"] == direction)].copy()
        base_same = final_acc_base[(final_acc_base["date"] == anchor) & (final_acc_base["dir"] == direction)].copy()
        ea_same = final_acc_ea[(final_acc_ea["date"] == anchor) & (final_acc_ea["dir"] == direction)].copy()

        raw_spec_reason = "/".join(raw_same["spec_reason"].astype(str).tolist()) if len(raw_same) else ""
        raw_modes = "/".join(raw_same["mode"].astype(str).tolist()) if len(raw_same) else ""
        raw_sd = "/".join(f"{float(x):.2f}" for x in raw_same["sd"].astype(float).tolist()) if len(raw_same) else ""
        classification = classify_row(raw_spec_reason, len(base_same), len(ea_same))

        if classification == "原始too_wide_旧rescue可救_当前EA口径未救回":
            rescue_probe_targets.append((anchor, direction))

        rows.append(
            {
                "对齐后时间": anchor,
                "方向": direction,
                "触发类型": row["触发类型"],
                "模式": row["模式"],
                "raw候选数": int(len(raw_same)),
                "raw模式": raw_modes,
                "raw_spec原因": raw_spec_reason,
                "raw_sd": raw_sd,
                "raw_accept后数量": int(len(accepted_same)),
                "旧口径final_acc数量": int(len(base_same)),
                "当前EA口径final_acc数量": int(len(ea_same)),
                "accepted缺失分类": classification,
            }
        )

    summary_detail = pd.DataFrame(rows)

    rescue_probe = raw_df[
        [(pd.Timestamp(d), dr) in set(rescue_probe_targets) for d, dr in zip(raw_df["date"], raw_df["dir"])]
    ].copy()
    rescued_any, _ = m15t.build_rescued_trades(rescue_probe, m15, m15t.choose_any)
    rescued_slot1, _ = m15t.build_rescued_trades(
        rescue_probe,
        m15,
        m15t.choose_slot1_by_distance,
        variant_name="ea_slot1_runtime_rescue",
        reanchor_stop_by_distance=True,
    )

    if len(rescued_any):
        rescued_any["date"] = pd.to_datetime(rescued_any["date"])
    if len(rescued_slot1):
        rescued_slot1["date"] = pd.to_datetime(rescued_slot1["date"])

    rescue_rows = []
    for anchor, direction in rescue_probe_targets:
        any_same = (
            rescued_any[(rescued_any["date"] == anchor) & (rescued_any["dir"] == direction)].copy()
            if len(rescued_any)
            else rescued_any.copy()
        )
        slot1_same = (
            rescued_slot1[(rescued_slot1["date"] == anchor) & (rescued_slot1["dir"] == direction)].copy()
            if len(rescued_slot1)
            else rescued_slot1.copy()
        )
        any_entry_time = pd.Timestamp(any_same.iloc[0]["entry_time"]) if len(any_same) else pd.NaT
        rescue_rows.append(
            {
                "对齐后时间": anchor,
                "方向": direction,
                "旧rescue_any可救回": bool(len(any_same) > 0),
                "旧rescue_any_entry_time": any_entry_time,
                "旧rescue_any是否落在anchor当根M15": bool(pd.notna(any_entry_time) and any_entry_time == anchor),
                "旧rescue_any_sd": "/".join(f"{float(x):.2f}" for x in any_same["sd"].astype(float).tolist()) if len(any_same) else "",
                "当前EA_slot1_rescue可救回": bool(len(slot1_same) > 0),
                "当前EA_slot1_rescue_sd": "/".join(f"{float(x):.2f}" for x in slot1_same["sd"].astype(float).tolist()) if len(slot1_same) else "",
            }
        )
    rescue_detail = pd.DataFrame(rescue_rows)

    summary = (
        summary_detail.groupby("accepted缺失分类", as_index=False)
        .size()
        .rename(columns={"size": "样本数"})
        .sort_values("样本数", ascending=False)
        .reset_index(drop=True)
    )
    summary["占比(%)"] = (summary["样本数"] / len(summary_detail) * 100.0).round(4) if len(summary_detail) else 0.0

    lines = [
        "# accepted层缺失样本复核",
        "",
        "## 总览",
        "",
        markdown_table(summary),
        "",
        "## 结论",
        "",
        "- 这份表只看 `accepted层缺失 = 8` 的样本。",
        "- 优先判断它们在 `raw_df` 是否已经存在同锚点候选，以及 `spec_reason` 是什么。",
        "- 如果旧 `replace_any + rescue` 能救回、但当前 `EA executable` 口径救不回，就单独归为执行口径未复原样本。",
        "",
        "## accepted缺失明细",
        "",
        markdown_table(summary_detail),
        "",
    ]
    if not rescue_detail.empty:
        lines.extend(
            [
                "## 旧rescue可救 / 当前EA口径未救回样本",
                "",
                markdown_table(rescue_detail),
                "",
            ]
        )

    export_csv(summary, OUTPUT_DIR / "accepted缺失样本汇总_20260709.csv")
    export_csv(summary_detail, OUTPUT_DIR / "accepted缺失样本明细_20260709.csv")
    if not rescue_detail.empty:
        export_csv(rescue_detail, OUTPUT_DIR / "accepted缺失样本_rescue差异明细_20260709.csv")
    write_text(OUTPUT_DIR / "accepted缺失样本复核_20260709.md", "\n".join(lines))
    print(f"Wrote {OUTPUT_DIR}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
