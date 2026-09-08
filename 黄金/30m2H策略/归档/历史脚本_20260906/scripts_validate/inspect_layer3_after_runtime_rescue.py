# -*- coding: utf-8 -*-
"""Inspect why EA-executable accepted samples fail Layer 3 after runtime rescue."""
from __future__ import annotations


import bisect
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
ROOT_SCRIPTS_DIR = ROOT / "scripts"

sys.path.insert(0, str(STRATEGY_SCRIPTS_DIR))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT_SCRIPTS_DIR))

from strategy_30m2h_common import VALIDATION_DIR, export_csv, write_text  # noqa: E402
import _current_baseline as cb  # type: ignore  # noqa: E402


OUTPUT_DIR = VALIDATION_DIR / "mt5_log_session_diag_current_mainline_20260708" / "session_01" / "session_01"
TARGET_START = pd.Timestamp("2026-06-11 08:00:00")
TARGET_END = pd.Timestamp("2026-06-11 09:00:00")


def annotate_all_layer3(final_acc: pd.DataFrame, h2: pd.DataFrame, top_pct: float = cb.DEFAULT_TOP_PCT) -> tuple[float, pd.DataFrame]:
    if final_acc.empty:
        out = final_acc.copy()
        out["layer3_eval_time"] = pd.NaT
        out["Bias_5_ea"] = np.nan
        out["layer3_threshold_ea"] = np.nan
        out["layer3_pass_ea"] = False
        return np.nan, out

    h2_bias = cb._build_h2_bias5_lookup(h2)
    h2_times = pd.to_datetime(h2_bias["date"]).tolist()
    h2_bias_values = h2_bias["Bias_5_calc"].tolist()

    out = cb.annotate_trigger_type(final_acc)
    eval_times: list[pd.Timestamp] = []
    bias5_vals: list[float] = []
    threshold_vals: list[float] = []
    pass_flags: list[bool] = []

    for _, row in out.iterrows():
        eval_time = pd.Timestamp(row["date"])
        if row["trigger"] == "M30 CLOSE":
            eval_time = eval_time + pd.Timedelta(minutes=cb.EA_DIAG_M30_LAYER3_SHIFT_MINUTES)
        eval_times.append(eval_time)

        idx = bisect.bisect_right(h2_times, eval_time) - 1
        if idx < 0:
            bias5_vals.append(np.nan)
            threshold_vals.append(np.nan)
            pass_flags.append(False)
            continue

        start = max(0, idx - cb.EA_DIAG_H2_LOOKBACK + 1)
        hist = h2_bias_values[start : idx + 1]
        current_bias5 = float(h2_bias_values[idx])
        threshold = cb._rolling_top_threshold(hist, top_pct)
        bias5_vals.append(current_bias5)
        threshold_vals.append(threshold)
        pass_flags.append(bool(pd.isna(threshold) or current_bias5 >= threshold))

    out["layer3_eval_time"] = eval_times
    out["Bias_5_ea"] = bias5_vals
    out["layer3_threshold_ea"] = threshold_vals
    out["layer3_pass_ea"] = pass_flags
    threshold_series = out["layer3_threshold_ea"].dropna()
    threshold = float(threshold_series.median()) if not threshold_series.empty else np.nan
    return threshold, out


def render_markdown(summary: pd.DataFrame, detail: pd.DataFrame) -> str:
    lines = [
        "# runtime rescue 后 Layer3 复核",
        "",
        "## 汇总",
        "",
        summary.to_markdown(index=False),
        "",
        "## 目标窗口明细",
        "",
        detail.to_markdown(index=False),
        "",
        "## 结论",
        "",
        "- 这份诊断针对 `EA 可执行口径` 下已经进入 `accepted` 的样本，继续检查它们为什么没进入 `picked`。",
        "- 如果 `layer3_pass_ea = False`，说明问题已经收敛到 Layer 3，而不是 runtime rescue 本身。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    df, final_acc = cb.build_final_accepted(ea_executable_diag=True)
    h2 = cb.load_h2_context()
    _, annotated = annotate_all_layer3(final_acc, h2, top_pct=cb.DEFAULT_TOP_PCT)
    annotated["date"] = pd.to_datetime(annotated["date"])
    annotated["entry_time"] = pd.to_datetime(annotated["entry_time"])

    target = annotated[(annotated["date"] >= TARGET_START) & (annotated["date"] <= TARGET_END)].copy()
    detail = target[
        [
            "date",
            "dir",
            "mode",
            "trigger",
            "entry_time",
            "entry",
            "stop",
            "sd",
            "Bias_5",
            "Bias_5_ea",
            "layer3_eval_time",
            "layer3_threshold_ea",
            "layer3_pass_ea",
            "variant",
        ]
    ].reset_index(drop=True)

    summary = pd.DataFrame(
        [
            {
                "目标窗口accepted数": int(len(detail)),
                "目标窗口Layer3通过数": int(detail["layer3_pass_ea"].fillna(False).sum()) if not detail.empty else 0,
                "目标窗口Layer3未通过数": int((~detail["layer3_pass_ea"].fillna(False)).sum()) if not detail.empty else 0,
            }
        ]
    )

    export_csv(detail, OUTPUT_DIR / "runtime_rescue后Layer3明细_20260709.csv")
    export_csv(summary, OUTPUT_DIR / "runtime_rescue后Layer3汇总_20260709.csv")
    write_text(OUTPUT_DIR / "runtime_rescue后Layer3复核_20260709.md", render_markdown(summary, detail))
    print(f"Wrote {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
