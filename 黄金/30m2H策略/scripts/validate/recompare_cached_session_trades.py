# -*- coding: utf-8 -*-
"""Rebuild a session trade diff using cached MT5 signals plus current Python logic."""
from __future__ import annotations


import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
ROOT_SCRIPTS_DIR = ROOT / "scripts"

sys.path.insert(0, str(STRATEGY_SCRIPTS_DIR))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT_SCRIPTS_DIR))

from strategy_30m2h_common import export_csv, read_csv_with_fallback, write_text  # noqa: E402
import _current_baseline as cb  # type: ignore  # noqa: E402
from compare_mt5_log_sessions import build_python_executed_signals, normalize_mode  # noqa: E402


def build_python_signal_frame(
    start: pd.Timestamp,
    end: pd.Timestamp,
    spec_lo: float,
    spec_hi: float,
    top_pct: float,
    bias55_threshold: float,
    stage1_r: float,
    stage2_trail_r: float,
    stage2_force_r: float,
    ea_executable_diag: bool,
) -> pd.DataFrame:
    result = cb.summarize_strategy(
        spec_lo=spec_lo,
        spec_hi=spec_hi,
        top_pct=top_pct,
        bias55_threshold=bias55_threshold,
        stage1_r=stage1_r,
        stage2_trail_r=stage2_trail_r,
        stage2_force_r=stage2_force_r,
        ea_executable_diag=ea_executable_diag,
    )
    frame = build_python_executed_signals(result, start, end)
    if frame.empty:
        frame["key"] = pd.Series(dtype=str)
        frame["python_stop_dist_1dp"] = pd.Series(dtype=float)
        return frame
    frame = frame.copy()
    frame["key"] = frame["anchor_time"].dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + frame["dir"]
    frame["python_stop_dist_1dp"] = frame["sd"].round(1)
    return frame.sort_values(["anchor_time", "dir"]).reset_index(drop=True)


def build_diff(mt5: pd.DataFrame, py: pd.DataFrame) -> dict[str, pd.DataFrame]:
    mt5 = mt5.copy()
    py = py.copy()
    if "key" not in mt5.columns:
        mt5["key"] = pd.to_datetime(mt5["anchor_time"]).dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + mt5["dir"]
    if "mode_norm" not in mt5.columns:
        mt5["mode_norm"] = mt5["mode_raw"].map(normalize_mode)

    mt5_keys = set(mt5["key"]) if not mt5.empty else set()
    py_keys = set(py["key"]) if not py.empty else set()
    shared_keys = mt5_keys & py_keys

    mt5_only = mt5[mt5["key"].isin(mt5_keys - py_keys)].copy()
    python_only = py[py["key"].isin(py_keys - mt5_keys)].copy()
    shared = mt5.merge(
        py[
            [
                "key",
                "anchor_time",
                "dir",
                "trigger",
                "mode_raw",
                "mode_norm",
                "entry_time",
                "variant",
                "sd",
                "python_stop_dist_1dp",
                "stage3_time",
                "total_$",
                "total_points",
            ]
        ],
        on="key",
        how="inner",
        suffixes=("_mt5", "_python"),
    )

    if shared.empty:
        shared["模式一致"] = pd.Series(dtype=bool)
        shared["触发一致"] = pd.Series(dtype=bool)
        shared["止损一致"] = pd.Series(dtype=bool)
        shared["差异说明"] = pd.Series(dtype=str)
        shared_mismatch = shared.copy()
    else:
        shared["模式一致"] = shared["mode_norm_mt5"] == shared["mode_norm_python"]
        shared["触发一致"] = shared["trigger_mt5"] == shared["trigger_python"]
        shared["止损一致"] = shared["mt5_stop_dist"].round(1) == shared["python_stop_dist_1dp"].round(1)

        def build_reason(row: pd.Series) -> str:
            reasons: list[str] = []
            if not bool(row["模式一致"]):
                reasons.append(f"模式: MT5={row['mode_raw_mt5']} / Python={row['mode_raw_python']}")
            if not bool(row["触发一致"]):
                reasons.append(f"触发: MT5={row['trigger_mt5']} / Python={row['trigger_python']}")
            if not bool(row["止损一致"]):
                reasons.append(f"止损: MT5={row['mt5_stop_dist']:.1f} / Python={row['python_stop_dist_1dp']:.1f}")
            return "；".join(reasons)

        shared["差异说明"] = shared.apply(build_reason, axis=1)
        shared_mismatch = shared[
            (~shared["模式一致"]) | (~shared["触发一致"]) | (~shared["止损一致"])
        ].copy()

    return {
        "mt5": mt5,
        "python": py,
        "shared": shared,
        "shared_mismatch": shared_mismatch,
        "mt5_only": mt5_only,
        "python_only": python_only,
        "shared_count": pd.DataFrame([{"共同信号数": len(shared_keys)}]),
    }


def render_summary(
    outputs: dict[str, pd.DataFrame],
    output_dir: Path,
    start: pd.Timestamp,
    end: pd.Timestamp,
    params_text: str,
    ea_executable_diag: bool,
) -> str:
    mt5 = outputs["mt5"]
    py = outputs["python"]
    shared = outputs["shared"]
    shared_mismatch = outputs["shared_mismatch"]
    mt5_only = outputs["mt5_only"]
    python_only = outputs["python_only"]

    lines = [
        "# MT5 缓存信号逐笔差异对比",
        "",
        f"- 回测区间：`{start:%Y-%m-%d %H:%M:%S}` 到 `{end:%Y-%m-%d %H:%M:%S}`",
        f"- 参数摘要：`{params_text}`",
        f"- Python 复算模式：`{'EA可执行诊断口径' if ea_executable_diag else '基础主线口径'}`",
        f"- 输出目录：`{output_dir}`",
        "",
        "## 汇总",
        "",
        f"- MT5 信号数：`{len(mt5)}`",
        f"- Python 执行信号数：`{len(py)}`",
        f"- 共同信号数：`{len(shared)}`",
        f"- 共同但字段不一致：`{len(shared_mismatch)}`",
        f"- MT5 独有：`{len(mt5_only)}`",
        f"- Python 独有：`{len(python_only)}`",
        "",
    ]

    if not shared_mismatch.empty:
        lines.extend(
            [
                "## 共同但不一致",
                "",
                shared_mismatch[
                    [
                        "anchor_time_mt5",
                        "dir_mt5",
                        "trigger_mt5",
                        "trigger_python",
                        "mode_raw_mt5",
                        "mode_raw_python",
                        "mt5_stop_dist",
                        "python_stop_dist_1dp",
                        "差异说明",
                    ]
                ].to_markdown(index=False),
                "",
            ]
        )

    if not mt5_only.empty:
        lines.extend(
            [
                "## MT5 独有样本",
                "",
                mt5_only[["mt5_raw_anchor_time", "anchor_time", "dir", "trigger", "mode_raw", "mt5_stop_dist"]]
                .to_markdown(index=False),
                "",
            ]
        )

    if not python_only.empty:
        lines.extend(
            [
                "## Python 独有样本",
                "",
                python_only[["anchor_time", "dir", "trigger", "mode_raw", "python_stop_dist_1dp", "variant"]]
                .to_markdown(index=False),
                "",
            ]
        )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Recompare cached MT5 signals against current Python logic.")
    parser.add_argument("--session-dir", type=Path, required=True, help="Directory containing cached mt5_signals.csv")
    parser.add_argument("--start", required=True, help="Backtest start time, e.g. 2018-01-01 00:00:00")
    parser.add_argument("--end", required=True, help="Backtest end time, e.g. 2026-07-04 00:00:00")
    parser.add_argument("--spec-lo", type=float, required=True)
    parser.add_argument("--spec-hi", type=float, required=True)
    parser.add_argument("--top-pct", type=float, required=True)
    parser.add_argument("--bias55-threshold", type=float, required=True)
    parser.add_argument("--stage1-r", type=float, required=True)
    parser.add_argument("--stage2-trail-r", type=float, required=True)
    parser.add_argument("--stage2-force-r", type=float, required=True)
    parser.add_argument("--ea-executable-diag", action="store_true")
    args = parser.parse_args()

    output_dir = args.session_dir
    mt5_path = output_dir / "mt5_signals.csv"
    if not mt5_path.exists():
        raise SystemExit(f"Missing cached MT5 signals: {mt5_path}")

    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end)
    mt5 = read_csv_with_fallback(mt5_path)
    for col in ["anchor_time", "mt5_raw_anchor_time", "log_time"]:
        if col in mt5.columns:
            mt5[col] = pd.to_datetime(mt5[col])

    py = build_python_signal_frame(
        start=start,
        end=end,
        spec_lo=args.spec_lo,
        spec_hi=args.spec_hi,
        top_pct=args.top_pct,
        bias55_threshold=args.bias55_threshold,
        stage1_r=args.stage1_r,
        stage2_trail_r=args.stage2_trail_r,
        stage2_force_r=args.stage2_force_r,
        ea_executable_diag=args.ea_executable_diag,
    )
    outputs = build_diff(mt5, py)

    export_csv(outputs["python"].drop(columns=["key"], errors="ignore"), output_dir / "python_executed_signals.csv")
    export_csv(outputs["shared"].drop(columns=["key"], errors="ignore"), output_dir / "shared_signals.csv")
    export_csv(outputs["shared_mismatch"].drop(columns=["key"], errors="ignore"), output_dir / "shared_mismatch.csv")
    export_csv(outputs["mt5_only"].drop(columns=["key"], errors="ignore"), output_dir / "mt5_only_signals.csv")
    export_csv(outputs["python_only"].drop(columns=["key"], errors="ignore"), output_dir / "python_only_signals.csv")

    params_text = (
        f"top{args.top_pct:.0f}% + "
        f"Stage {args.stage1_r:.1f}/{args.stage2_trail_r:.1f}/{args.stage2_force_r:.1f} + "
        f"stop [{args.spec_lo:.0f},{args.spec_hi:.0f}]"
    )
    md = render_summary(outputs, output_dir, start, end, params_text, args.ea_executable_diag)
    write_text(output_dir / "session_trade_diff.md", md)
    print(f"Wrote {output_dir}")


if __name__ == "__main__":
    main()
