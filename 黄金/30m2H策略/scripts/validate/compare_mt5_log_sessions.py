# -*- coding: utf-8 -*-
"""Compare MT5 tester log sessions against same-window Python results."""
from __future__ import annotations


import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
ROOT_SCRIPTS_DIR = ROOT / "scripts"

sys.path.insert(0, str(STRATEGY_SCRIPTS_DIR))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT_SCRIPTS_DIR))

from strategy_30m2h_common import (  # noqa: E402
    EXECUTION_PNL_MULTIPLIER,
    START_CAPITAL,
    VALIDATION_DIR,
    ensure_dirs,
    export_csv,
    write_text,
)

import _current_baseline as cb  # type: ignore  # noqa: E402


SESSION_RE = re.compile(
    r"(?P<symbol>[^,\s]+),(?P<timeframe>[^:\s]+): testing of (?P<expert>.+?) "
    r"from (?P<start>\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}) "
    r"to (?P<end>\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}) started with inputs:"
)
INPUT_RE = re.compile(r"\b(?P<key>Inp[A-Za-z0-9_]+)=(?P<value>[^\s\r\n]+)")
FINAL_BALANCE_RE = re.compile(r"final balance\s+(?P<value>-?\d+(?:\.\d+)?)\s+USD", re.IGNORECASE)
BALANCE_RE = re.compile(r"\bBalance:\s*\$?(?P<value>-?\d+(?:\.\d+)?)")
EQUITY_RE = re.compile(r"\bEquity:\s*\$?(?P<value>-?\d+(?:\.\d+)?)")
EA_VERSION_RE = re.compile(r"\b30m\s*x\s*2H\s+EA\s+v(?P<version>\d+(?:\.\d+)*)", re.IGNORECASE)
SIGNAL_RE = re.compile(
    r"(?P<time>\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}).*?"
    r"\[(?P<trigger>M30 CLOSE|M15 SLOT1)\]\s+\[SIGNAL\]\s+"
    r"(?P<side>BUY|SELL)!.*?mode=(?P<mode>[^\s]+).*?"
    r"stop_dist=(?P<stop_dist>-?\d+(?:\.\d+)?).*?"
    r"anchor=(?P<anchor>\d{4}\.\d{2}\.\d{2} \d{2}:\d{2})",
    re.IGNORECASE,
)
MT5_TIME_FMT_MIN = "%Y.%m.%d %H:%M"
MT5_TIME_FMT_SEC = "%Y.%m.%d %H:%M:%S"


@dataclass
class LogSession:
    session_id: int
    log_path: Path
    start_line: int
    symbol: str
    timeframe: str
    expert: str
    start: datetime
    end: datetime
    inputs: dict[str, str] = field(default_factory=dict)
    initial_balance: float | None = None
    initial_equity: float | None = None
    final_balance: float | None = None
    final_line: int | None = None
    ea_version: str | None = None
    signals: list[dict[str, Any]] = field(default_factory=list)


def read_text_auto(path: Path) -> str:
    data = path.read_bytes()
    encodings: list[str]
    if data.startswith((b"\xff\xfe", b"\xfe\xff")) or data.count(b"\x00") > max(len(data) // 10, 1):
        encodings = ["utf-16", "utf-16-le", "utf-8-sig", "gbk"]
    else:
        encodings = ["utf-8-sig", "utf-16", "utf-16-le", "gbk"]

    last_error: Exception | None = None
    for encoding in encodings:
        try:
            return data.decode(encoding).replace("\x00", "")
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error is not None:
        raise RuntimeError(f"Unable to decode log file: {path}") from last_error
    return data.decode("utf-8", errors="replace").replace("\x00", "")


def parse_mt5_time(value: str, with_seconds: bool = False) -> datetime:
    return datetime.strptime(value, MT5_TIME_FMT_SEC if with_seconds else MT5_TIME_FMT_MIN)


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def input_float(session: LogSession, key: str, default: float | None = None) -> float | None:
    value = parse_float(session.inputs.get(key))
    return default if value is None else value


def input_bool(session: LogSession, key: str, default: bool = False) -> bool:
    value = session.inputs.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def mql_points_to_spec_points(value: float | None, default: float) -> float:
    if value is None:
        return default
    return value / 1000.0 if abs(value) > 100.0 else value


def parse_log_sessions(log_path: Path) -> list[LogSession]:
    text = read_text_auto(log_path)
    sessions: list[LogSession] = []
    current: LogSession | None = None

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        session_match = SESSION_RE.search(line)
        if session_match:
            current = LogSession(
                session_id=len(sessions) + 1,
                log_path=log_path,
                start_line=line_no,
                symbol=session_match.group("symbol"),
                timeframe=session_match.group("timeframe"),
                expert=session_match.group("expert"),
                start=parse_mt5_time(session_match.group("start")),
                end=parse_mt5_time(session_match.group("end")),
            )
            sessions.append(current)
            continue

        if current is None:
            continue

        input_match = INPUT_RE.search(line)
        if input_match:
            current.inputs[input_match.group("key")] = input_match.group("value")

        if current.initial_balance is None:
            balance_match = BALANCE_RE.search(line)
            if balance_match:
                current.initial_balance = float(balance_match.group("value"))

        if current.initial_equity is None:
            equity_match = EQUITY_RE.search(line)
            if equity_match:
                current.initial_equity = float(equity_match.group("value"))

        if current.ea_version is None:
            version_match = EA_VERSION_RE.search(line)
            if version_match:
                current.ea_version = version_match.group("version")

        signal_match = SIGNAL_RE.search(line)
        if signal_match:
            current.signals.append(
                {
                    "line": line_no,
                    "time": parse_mt5_time(signal_match.group("time"), with_seconds=True),
                    "anchor_time": parse_mt5_time(signal_match.group("anchor")),
                    "trigger": signal_match.group("trigger").upper(),
                    "side": signal_match.group("side").upper(),
                    "mode": signal_match.group("mode"),
                    "stop_dist": float(signal_match.group("stop_dist")),
                }
            )

        final_match = FINAL_BALANCE_RE.search(line)
        if final_match:
            current.final_balance = float(final_match.group("value"))
            current.final_line = line_no

    return sessions


def session_strategy_params(session: LogSession) -> dict[str, float | bool]:
    stop_lo = mql_points_to_spec_points(input_float(session, "InpStopLo"), cb.DEFAULT_SPEC_LO)
    stop_hi = mql_points_to_spec_points(input_float(session, "InpStopHi"), cb.DEFAULT_SPEC_HI)
    return {
        "spec_lo": stop_lo,
        "spec_hi": stop_hi,
        "top_pct": input_float(session, "InpBias5TopPct", cb.DEFAULT_TOP_PCT),
        "bias55_threshold": input_float(session, "InpBias55Threshold", cb.DEFAULT_BIAS55_THRESHOLD),
        "stage1_r": input_float(session, "InpStage1R", cb.DEFAULT_STAGE1_R),
        "stage2_trail_r": input_float(session, "InpStage2TrailR", cb.DEFAULT_STAGE2_TRAIL_R),
        "stage2_force_r": input_float(session, "InpStage2ForceR", cb.DEFAULT_STAGE2_FORCE_R),
        "use_layer3": input_bool(session, "InpUseLayer3", True),
    }


def params_cache_key(params: dict[str, float | bool], ea_executable_diag: bool) -> tuple[Any, ...]:
    return (
        params["spec_lo"],
        params["spec_hi"],
        params["top_pct"],
        params["bias55_threshold"],
        params["stage1_r"],
        params["stage2_trail_r"],
        params["stage2_force_r"],
        ea_executable_diag,
    )


def params_match_current_mainline(params: dict[str, float | bool]) -> bool:
    checks = [
        (params["spec_lo"], cb.DEFAULT_SPEC_LO),
        (params["spec_hi"], cb.DEFAULT_SPEC_HI),
        (params["top_pct"], cb.DEFAULT_TOP_PCT),
        (params["bias55_threshold"], cb.DEFAULT_BIAS55_THRESHOLD),
        (params["stage1_r"], cb.DEFAULT_STAGE1_R),
        (params["stage2_trail_r"], cb.DEFAULT_STAGE2_TRAIL_R),
        (params["stage2_force_r"], cb.DEFAULT_STAGE2_FORCE_R),
    ]
    return all(abs(float(actual) - float(expected)) < 1e-9 for actual, expected in checks)


def short_params(params: dict[str, float | bool]) -> str:
    return (
        f"top{float(params['top_pct']):.0f}% + "
        f"Stage {float(params['stage1_r']):.1f}/"
        f"{float(params['stage2_trail_r']):.1f}/"
        f"{float(params['stage2_force_r']):.1f} + "
        f"stop [{float(params['spec_lo']):.0f},{float(params['spec_hi']):.0f}]"
    )


def normalize_mode(mode: str) -> str:
    if mode.startswith("pre_cross"):
        return "pre_cross"
    if mode.startswith("cross"):
        return "cross"
    post_match = re.match(r"(post_n\d+)", mode)
    if post_match:
        return post_match.group(1)
    return mode


def build_python_executed_signals(
    result: dict[str, Any],
    start: datetime | pd.Timestamp | None = None,
    end: datetime | pd.Timestamp | None = None,
) -> pd.DataFrame:
    picked = result["picked"].copy()
    trades = result["trades"].copy()
    if trades.empty:
        return pd.DataFrame(
            columns=[
                "anchor_time",
                "dir",
                "trigger",
                "mode_raw",
                "mode_norm",
                "entry_time",
                "variant",
                "sd",
                "stage3_time",
                "total_$",
                "total_points",
            ]
        )

    picked["meta_key"] = pd.to_datetime(picked["date"]).dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + picked["dir"]
    picked = picked.drop_duplicates(subset=["meta_key"], keep="first").set_index("meta_key")
    trades = trades.sort_values("date").reset_index(drop=True)
    start_ts = pd.Timestamp(start) if start is not None else None
    end_ts = pd.Timestamp(end) if end is not None else None
    active_until: pd.Timestamp | None = None
    rows: list[dict[str, Any]] = []

    for _, row in trades.iterrows():
        anchor_time = pd.Timestamp(row["date"])
        stage3_time = pd.Timestamp(row["stage3_time"])
        if start_ts is not None and anchor_time < start_ts:
            continue
        if end_ts is not None and anchor_time >= end_ts:
            continue
        if active_until is not None and anchor_time <= active_until:
            continue

        meta_key = anchor_time.strftime("%Y-%m-%d %H:%M:%S") + "|" + row["dir"]
        meta = picked.loc[meta_key] if meta_key in picked.index else None
        entry_time = pd.Timestamp(meta["entry_time"]) if meta is not None and "entry_time" in meta else anchor_time
        mode_raw = str(row["mode"])
        rows.append(
            {
                "anchor_time": anchor_time,
                "dir": row["dir"],
                "trigger": "M15 SLOT1" if entry_time < anchor_time else "M30 CLOSE",
                "mode_raw": mode_raw,
                "mode_norm": normalize_mode(mode_raw),
                "entry_time": entry_time,
                "variant": meta["variant"] if meta is not None and "variant" in meta else "",
                "sd": float(meta["sd"]) if meta is not None and "sd" in meta and pd.notna(meta["sd"]) else None,
                "stage3_time": stage3_time,
                "total_$": float(row["total_$"]),
                "total_points": float(row["total_points"]),
            }
        )
        active_until = stage3_time

    return pd.DataFrame(rows)


def compare_sessions(sessions: list[LogSession], ea_executable_diag: bool = False) -> pd.DataFrame:
    result_cache: dict[tuple[Any, ...], dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []

    for session in sessions:
        params = session_strategy_params(session)
        cache_key = params_cache_key(params, ea_executable_diag)
        if cache_key not in result_cache:
            result_cache[cache_key] = cb.summarize_strategy(
                spec_lo=float(params["spec_lo"]),
                spec_hi=float(params["spec_hi"]),
                top_pct=float(params["top_pct"]),
                bias55_threshold=float(params["bias55_threshold"]),
                stage1_r=float(params["stage1_r"]),
                stage2_trail_r=float(params["stage2_trail_r"]),
                stage2_force_r=float(params["stage2_force_r"]),
                ea_executable_diag=ea_executable_diag,
            )

        result = result_cache[cache_key]
        window_trades = build_python_executed_signals(result, session.start, session.end)
        all_executed = build_python_executed_signals(result)

        base_profit = float(window_trades["total_$"].sum()) if not window_trades.empty else 0.0
        total_profit = base_profit * EXECUTION_PNL_MULTIPLIER
        initial_balance = session.initial_balance if session.initial_balance is not None else START_CAPITAL
        python_final = initial_balance + total_profit
        final_delta = None if session.final_balance is None else session.final_balance - python_final

        mt5_signal_count = len(session.signals)
        python_window_trade_count = int(len(window_trades))
        same_window_match = (
            mt5_signal_count == python_window_trade_count
            and (final_delta is None or abs(final_delta) < 0.01)
        )

        if not params_match_current_mainline(params):
            status = "参数不等于当前主线"
        elif same_window_match:
            status = "同窗结果一致"
        else:
            status = "需逐笔排查"

        if mt5_signal_count == 0 and python_window_trade_count == 0:
            note = "同一时间窗内，MT5 与 Python 都没有交易。"
        elif mt5_signal_count != python_window_trade_count:
            note = "同一时间窗内，MT5 与 Python 的交易笔数不同，需要逐笔 diff。"
        elif final_delta is not None and abs(final_delta) >= 0.01:
            note = "同一时间窗内交易笔数相同，但最终资金不同，需要检查执行价、滑点或止盈止损处理。"
        else:
            note = "同一时间窗内交易笔数和最终资金都一致。"

        rows.append(
            {
                "会话编号": session.session_id,
                "日志文件": str(session.log_path),
                "开始行": session.start_line,
                "结束行": session.final_line,
                "品种": session.symbol,
                "周期": session.timeframe,
                "EA文件": session.expert,
                "EA版本": session.ea_version,
                "回测开始": session.start.strftime("%Y-%m-%d %H:%M:%S"),
                "回测结束": session.end.strftime("%Y-%m-%d %H:%M:%S"),
                "MT5初始资金": initial_balance,
                "MT5初始净值": session.initial_equity,
                "MT5最终资金": session.final_balance,
                "MT5信号数": mt5_signal_count,
                "MT5信号时间": "; ".join(s["time"].strftime("%Y-%m-%d %H:%M:%S") for s in session.signals),
                "MT5锚点时间": "; ".join(s["anchor_time"].strftime("%Y-%m-%d %H:%M:%S") for s in session.signals),
                "日志止损下限输入": input_float(session, "InpStopLo"),
                "日志止损上限输入": input_float(session, "InpStopHi"),
                "日志Layer3_top_pct": params["top_pct"],
                "日志Layer1阈值": params["bias55_threshold"],
                "日志Stage1手数": input_float(session, "InpStage1Lots"),
                "日志Stage2手数": input_float(session, "InpStage2Lots"),
                "日志Stage3手数": input_float(session, "InpStage3Lots"),
                "日志Stage1_R": params["stage1_r"],
                "日志Stage2_追踪R": params["stage2_trail_r"],
                "日志Stage2_强平R": params["stage2_force_r"],
                "换算后止损下限pt": params["spec_lo"],
                "换算后止损上限pt": params["spec_hi"],
                "Python复算模式": "EA可执行诊断口径" if ea_executable_diag else "基线主线口径",
                "Python全样本候选数": int(len(result["accepted"])),
                "Python全样本Layer3入选数": int(len(result["picked"])),
                "Python全样本执行交易数": int(len(all_executed)),
                "Python全样本Layer3阈值": float(result["threshold"]),
                "Python同窗交易数": python_window_trade_count,
                "Python同窗基础盈利": round(base_profit, 6),
                "Python同窗总盈利": round(total_profit, 6),
                "Python同窗最终资金": round(python_final, 6),
                "MT5减Python资金差": None if final_delta is None else round(final_delta, 6),
                "是否当前主线参数": params_match_current_mainline(params),
                "参数摘要": short_params(params),
                "对比状态": status,
                "说明": note,
            }
        )

    return pd.DataFrame(rows)


def render_markdown(summary: pd.DataFrame, log_path: Path, output_dir: Path) -> str:
    lines: list[str] = [
        "# MT5 日志会话级对比",
        "",
        f"- 日志文件：`{log_path}`",
        f"- 输出目录：`{output_dir}`",
        "- 口径：先把 MT5 日志拆成多次回测会话，再按同参数、同时间窗复算 Python 结果。",
        "",
        "## 总表",
        "",
    ]

    if summary.empty:
        lines.append("未识别到任何 MT5 回测会话。")
    else:
        view_cols = [
            "会话编号",
            "回测开始",
            "回测结束",
            "参数摘要",
            "MT5信号数",
            "MT5最终资金",
            "Python同窗交易数",
            "Python同窗最终资金",
            "对比状态",
            "说明",
        ]
        lines.append(summary[view_cols].to_markdown(index=False))

    lines.extend(["", "## 结论", ""])
    if len(summary) > 1:
        lines.append(f"- 同一份日志里识别到 `{len(summary)}` 次独立回测，不能把不同会话的结果混在一起比较。")

    for _, row in summary.iterrows():
        lines.append(
            f"- 会话 {int(row['会话编号'])}：`{row['回测开始']}` 到 `{row['回测结束']}`，"
            f"MT5 最终资金 `${float(row['MT5最终资金']):.2f}`，"
            f"Python 同窗最终资金 `${float(row['Python同窗最终资金']):.2f}`，"
            f"状态：`{row['对比状态']}`。"
        )
        if not bool(row["是否当前主线参数"]):
            lines.append(
                f"  日志参数不是当前主线参数：`{row['参数摘要']}`，"
                f"当前主线应为 `top{cb.DEFAULT_TOP_PCT:.0f}% + "
                f"Stage {cb.DEFAULT_STAGE1_R:.1f}/{cb.DEFAULT_STAGE2_TRAIL_R:.1f}/{cb.DEFAULT_STAGE2_FORCE_R:.1f}`。"
            )
        lines.append(f"  说明：{row['说明']}")

    lines.extend(
        [
            "",
            "## 使用方式",
            "",
            "```powershell",
            "python 黄金/30m2H策略/scripts/validate/compare_mt5_log_sessions.py <MT5日志路径>",
            "```",
            "",
            "输出文件：",
            "",
            "- `sessions_summary.csv`：每次回测会话的参数、资金、交易数对比表。",
            "- `session_compare.md`：中文总结说明。",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare MT5 Tester log sessions with Python same-window strategy output.")
    parser.add_argument("log_path", type=Path, help="Path to an MT5 Tester log file")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=VALIDATION_DIR / "mt5_log_session_compare",
        help="Directory for sessions_summary.csv and session_compare.md",
    )
    parser.add_argument(
        "--ea-executable-diag",
        action="store_true",
        help="Use Python EA executable diagnostic mode instead of the baseline global Layer3 mode.",
    )
    args = parser.parse_args()

    ensure_dirs()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    sessions = parse_log_sessions(args.log_path)
    summary = compare_sessions(sessions, ea_executable_diag=args.ea_executable_diag) if sessions else pd.DataFrame()

    summary_path = args.output_dir / "sessions_summary.csv"
    report_path = args.output_dir / "session_compare.md"
    export_csv(summary, summary_path)
    write_text(report_path, render_markdown(summary, args.log_path, args.output_dir))

    print(f"Parsed {len(sessions)} MT5 session(s).")
    print(f"Wrote {summary_path}")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
