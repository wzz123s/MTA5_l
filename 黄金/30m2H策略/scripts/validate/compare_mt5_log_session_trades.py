# -*- coding: utf-8 -*-
"""Detailed MT5 session signal diff against same-window Python executed signals."""
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

from strategy_30m2h_common import VALIDATION_DIR, ensure_dirs, export_csv, write_text  # noqa: E402
import _current_baseline as cb  # type: ignore  # noqa: E402
from _ea_python_signal_diff import EA_ALIGN_DELTA  # type: ignore  # noqa: E402
from compare_mt5_log_sessions import (  # noqa: E402
    LogSession,
    build_python_executed_signals,
    normalize_mode,
    params_match_current_mainline,
    parse_log_sessions,
    session_strategy_params,
    short_params,
)


def build_mt5_signal_frame(session: LogSession) -> pd.DataFrame:
    rows = []
    for item in session.signals:
        side = item["side"].upper()
        direction = "L" if side == "BUY" else "S"
        mode_raw = str(item["mode"])
        anchor_time = pd.Timestamp(item["anchor_time"])
        aligned_anchor_time = anchor_time + EA_ALIGN_DELTA
        rows.append(
            {
                "anchor_time": aligned_anchor_time,
                "mt5_raw_anchor_time": anchor_time,
                "dir": direction,
                "trigger": str(item["trigger"]).upper(),
                "mode_raw": mode_raw,
                "mode_norm": normalize_mode(mode_raw),
                "log_time": pd.Timestamp(item["time"]),
                "mt5_stop_dist": float(item["stop_dist"]),
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["key"] = frame["anchor_time"].dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + frame["dir"]
    return frame.sort_values(["anchor_time", "dir"]).reset_index(drop=True)


def build_python_signal_frame(session: LogSession, ea_executable_diag: bool = False) -> pd.DataFrame:
    params = session_strategy_params(session)
    result = cb.summarize_strategy(
        spec_lo=float(params["spec_lo"]),
        spec_hi=float(params["spec_hi"]),
        top_pct=float(params["top_pct"]),
        bias55_threshold=float(params["bias55_threshold"]),
        stage1_r=float(params["stage1_r"]),
        stage2_trail_r=float(params["stage2_trail_r"]),
        stage2_force_r=float(params["stage2_force_r"]),
        ea_executable_diag=ea_executable_diag,
    )
    frame = build_python_executed_signals(result, session.start, session.end)
    if frame.empty:
        frame["key"] = pd.Series(dtype=str)
        return frame
    frame = frame.copy()
    frame["key"] = frame["anchor_time"].dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + frame["dir"]
    frame["python_stop_dist_1dp"] = frame["sd"].round(1)
    return frame.sort_values(["anchor_time", "dir"]).reset_index(drop=True)


def compare_session(session: LogSession, ea_executable_diag: bool = False) -> dict[str, pd.DataFrame]:
    mt5 = build_mt5_signal_frame(session)
    py = build_python_signal_frame(session, ea_executable_diag=ea_executable_diag)

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
        shared["模式是否一致"] = pd.Series(dtype=bool)
        shared["触发是否一致"] = pd.Series(dtype=bool)
        shared["止损是否一致"] = pd.Series(dtype=bool)
        shared["差异说明"] = pd.Series(dtype=str)
        shared_mismatch = shared.copy()
    else:
        shared["模式是否一致"] = shared["mode_norm_mt5"] == shared["mode_norm_python"]
        shared["触发是否一致"] = shared["trigger_mt5"] == shared["trigger_python"]
        shared["止损是否一致"] = shared["mt5_stop_dist"].round(1) == shared["python_stop_dist_1dp"].round(1)

        def build_reason(row: pd.Series) -> str:
            reasons: list[str] = []
            if not bool(row["模式是否一致"]):
                reasons.append(f"模式: MT5={row['mode_raw_mt5']} / Python={row['mode_raw_python']}")
            if not bool(row["触发是否一致"]):
                reasons.append(f"触发: MT5={row['trigger_mt5']} / Python={row['trigger_python']}")
            if not bool(row["止损是否一致"]):
                reasons.append(f"止损: MT5={row['mt5_stop_dist']:.1f} / Python={row['python_stop_dist_1dp']:.1f}")
            return "；".join(reasons)

        shared["差异说明"] = shared.apply(build_reason, axis=1)
        shared_mismatch = shared[
            (~shared["模式是否一致"]) | (~shared["触发是否一致"]) | (~shared["止损是否一致"])
        ].copy()

    return {
        "mt5": mt5,
        "python": py,
        "shared": shared,
        "shared_mismatch": shared_mismatch,
        "mt5_only": mt5_only,
        "python_only": python_only,
    }


def render_summary(
    session: LogSession,
    outputs: dict[str, pd.DataFrame],
    output_dir: Path,
    ea_executable_diag: bool = False,
) -> str:
    params = session_strategy_params(session)
    mt5 = outputs["mt5"]
    py = outputs["python"]
    shared = outputs["shared"]
    shared_mismatch = outputs["shared_mismatch"]
    mt5_only = outputs["mt5_only"]
    python_only = outputs["python_only"]

    lines = [
        "# MT5 会话逐笔差异对比",
        "",
        f"- 会话编号：`{session.session_id}`",
        f"- 回测区间：`{session.start:%Y-%m-%d %H:%M:%S}` 到 `{session.end:%Y-%m-%d %H:%M:%S}`",
        f"- 参数摘要：`{short_params(params)}`",
        f"- 是否当前主线参数：`{'是' if params_match_current_mainline(params) else '否'}`",
        f"- Python 复算模式：`{'EA可执行诊断口径' if ea_executable_diag else '基线主线口径'}`",
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
                ]
                .head(20)
                .to_markdown(index=False),
                "",
            ]
        )

    if not mt5_only.empty:
        lines.extend(
            [
                "## MT5 独有样本",
                "",
                mt5_only[["mt5_raw_anchor_time", "anchor_time", "dir", "trigger", "mode_raw", "mt5_stop_dist"]]
                .head(20)
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
                .head(20)
                .to_markdown(index=False),
                "",
            ]
        )

    lines.extend(
        [
            "## 输出文件",
            "",
            "- `mt5_signals.csv`",
            "- `python_executed_signals.csv`",
            "- `shared_signals.csv`",
            "- `shared_mismatch.csv`",
            "- `mt5_only_signals.csv`",
            "- `python_only_signals.csv`",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Detailed MT5 session signal diff against Python executed signals.")
    parser.add_argument("log_path", type=Path, help="Path to MT5 tester log file")
    parser.add_argument("--session-id", type=int, required=True, help="Session id from sessions_summary.csv")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=VALIDATION_DIR / "mt5_log_session_diff",
        help="Directory for detailed diff outputs",
    )
    parser.add_argument(
        "--ea-executable-diag",
        action="store_true",
        help="Use Python EA executable diagnostic mode.",
    )
    args = parser.parse_args()

    ensure_dirs()
    sessions = parse_log_sessions(args.log_path)
    target = next((session for session in sessions if session.session_id == args.session_id), None)
    if target is None:
        raise SystemExit(f"Session id {args.session_id} not found in log: {args.log_path}")

    output_dir = args.output_dir / f"session_{args.session_id:02d}"
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = compare_session(target, ea_executable_diag=args.ea_executable_diag)
    export_csv(outputs["mt5"].drop(columns=["key"], errors="ignore"), output_dir / "mt5_signals.csv")
    export_csv(outputs["python"].drop(columns=["key"], errors="ignore"), output_dir / "python_executed_signals.csv")
    export_csv(outputs["shared"].drop(columns=["key"], errors="ignore"), output_dir / "shared_signals.csv")
    export_csv(outputs["shared_mismatch"].drop(columns=["key"], errors="ignore"), output_dir / "shared_mismatch.csv")
    export_csv(outputs["mt5_only"].drop(columns=["key"], errors="ignore"), output_dir / "mt5_only_signals.csv")
    export_csv(outputs["python_only"].drop(columns=["key"], errors="ignore"), output_dir / "python_only_signals.csv")
    write_text(output_dir / "session_trade_diff.md", render_summary(target, outputs, output_dir, args.ea_executable_diag))

    print(f"Compared session {args.session_id}.")
    print(f"Wrote {output_dir}")


if __name__ == "__main__":
    main()
