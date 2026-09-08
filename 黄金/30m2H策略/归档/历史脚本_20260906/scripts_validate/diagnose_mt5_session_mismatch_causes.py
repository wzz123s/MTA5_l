# -*- coding: utf-8 -*-
"""Diagnose root causes for MT5 vs Python session mismatches."""
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
import _h2_early_gate_test as h2t  # type: ignore  # noqa: E402
import _m15_early_entry_test as m15t  # type: ignore  # noqa: E402
import _m15_h2_combo_test as combo  # type: ignore  # noqa: E402
import _pre_cross_range_test as pct  # type: ignore  # noqa: E402
from compare_mt5_log_session_trades import compare_session  # noqa: E402
from compare_mt5_log_sessions import (  # noqa: E402
    LogSession,
    parse_log_sessions,
    session_strategy_params,
    short_params,
)


def make_key(anchor_time: pd.Timestamp, direction: str) -> str:
    return pd.Timestamp(anchor_time).strftime("%Y-%m-%d %H:%M:%S") + "|" + str(direction)


def build_result_for_session(session: LogSession, ea_executable_diag: bool = False) -> dict:
    params = session_strategy_params(session)
    return cb.summarize_strategy(
        spec_lo=float(params["spec_lo"]),
        spec_hi=float(params["spec_hi"]),
        top_pct=float(params["top_pct"]),
        bias55_threshold=float(params["bias55_threshold"]),
        stage1_r=float(params["stage1_r"]),
        stage2_trail_r=float(params["stage2_trail_r"]),
        stage2_force_r=float(params["stage2_force_r"]),
        ea_executable_diag=ea_executable_diag,
    )


def build_raw_frames_for_session(session: LogSession) -> tuple[pd.DataFrame, pd.DataFrame]:
    params = session_strategy_params(session)
    df, h2, _ = cb.load_market_context()

    old_pct_lo, old_pct_hi = pct.SPEC_LO, pct.SPEC_HI
    old_bias55 = pct.BIAS_55_THRESHOLD
    old_m15_lo, old_m15_hi = m15t.SPEC_LO, m15t.SPEC_HI
    try:
        pct.SPEC_LO, pct.SPEC_HI = float(params["spec_lo"]), float(params["spec_hi"])
        pct.BIAS_55_THRESHOLD = float(params["bias55_threshold"])
        m15t.SPEC_LO, m15t.SPEC_HI = float(params["spec_lo"]), float(params["spec_hi"])

        q2_pass_set, q2_factor_map, _, _ = h2t.early_precompute(h2, df, 2, False)
        raw_df, accepted = combo.build_candidate_frames(df, q2_pass_set, q2_factor_map)
    finally:
        pct.SPEC_LO, pct.SPEC_HI = old_pct_lo, old_pct_hi
        pct.BIAS_55_THRESHOLD = old_bias55
        m15t.SPEC_LO, m15t.SPEC_HI = old_m15_lo, old_m15_hi

    for frame in (raw_df, accepted):
        if not frame.empty:
            frame["anchor_time"] = pd.to_datetime(frame["date"])
            frame["key"] = frame["anchor_time"].dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + frame["dir"].astype(str)
    return raw_df, accepted


def build_meta_maps(result: dict) -> tuple[dict[str, dict], dict[str, dict]]:
    picked = result["picked"].copy()
    accepted = result["accepted"].copy()
    out = []
    for frame in (picked, accepted):
        if not frame.empty:
            frame["anchor_time"] = pd.to_datetime(frame["date"])
            frame["key"] = frame["anchor_time"].dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + frame["dir"].astype(str)
        out.append(frame)

    picked_map = out[0].drop_duplicates(subset=["key"], keep="first").set_index("key").to_dict("index") if not out[0].empty else {}
    accepted_map = out[1].drop_duplicates(subset=["key"], keep="first").set_index("key").to_dict("index") if not out[1].empty else {}
    return picked_map, accepted_map


def find_blocking_trade(py_executed: pd.DataFrame, anchor_time: pd.Timestamp) -> dict[str, object]:
    if py_executed.empty:
        return {}
    subset = py_executed[
        (pd.to_datetime(py_executed["anchor_time"]) < pd.Timestamp(anchor_time))
        & (pd.to_datetime(py_executed["stage3_time"]) >= pd.Timestamp(anchor_time))
    ].copy()
    if subset.empty:
        return {}
    row = subset.sort_values("anchor_time").iloc[-1]
    return {
        "blocked_by_anchor": pd.Timestamp(row["anchor_time"]),
        "blocked_by_trigger": row.get("trigger", ""),
        "blocked_by_mode": row.get("mode_raw", ""),
        "blocked_until": pd.Timestamp(row["stage3_time"]),
        "blocked_total_points": row.get("total_points", None),
    }


def find_nearest_raw_candidate(raw_df: pd.DataFrame, anchor_time: pd.Timestamp, direction: str, hours: int = 2) -> dict[str, object]:
    if raw_df.empty:
        return {}
    subset = raw_df[
        (raw_df["dir"] == direction)
        & (pd.to_datetime(raw_df["anchor_time"]) >= pd.Timestamp(anchor_time) - pd.Timedelta(hours=hours))
        & (pd.to_datetime(raw_df["anchor_time"]) <= pd.Timestamp(anchor_time) + pd.Timedelta(hours=hours))
    ].copy()
    if subset.empty:
        return {}
    subset["delta_minutes"] = (pd.to_datetime(subset["anchor_time"]) - pd.Timestamp(anchor_time)).abs() / pd.Timedelta(minutes=1)
    row = subset.sort_values(["delta_minutes", "anchor_time"]).iloc[0]
    return {
        "nearest_raw_anchor": pd.Timestamp(row["anchor_time"]),
        "nearest_raw_mode": row.get("mode", ""),
        "nearest_raw_sd": row.get("sd", None),
        "nearest_raw_spec_pass": row.get("spec_pass", None),
        "nearest_raw_spec_reason": row.get("spec_reason", ""),
        "nearest_raw_delta_minutes": row.get("delta_minutes", None),
    }


def find_nearest_python_executed(
    py_executed: pd.DataFrame,
    anchor_time: pd.Timestamp,
    direction: str,
    hours: int = 2,
) -> dict[str, object]:
    if py_executed.empty:
        return {}
    subset = py_executed[
        (py_executed["dir"] == direction)
        & (pd.to_datetime(py_executed["anchor_time"]) >= pd.Timestamp(anchor_time) - pd.Timedelta(hours=hours))
        & (pd.to_datetime(py_executed["anchor_time"]) <= pd.Timestamp(anchor_time) + pd.Timedelta(hours=hours))
    ].copy()
    if subset.empty:
        return {}
    subset["delta_minutes_signed"] = (
        pd.to_datetime(subset["anchor_time"]) - pd.Timestamp(anchor_time)
    ) / pd.Timedelta(minutes=1)
    subset["delta_minutes_abs"] = subset["delta_minutes_signed"].abs()
    row = subset.sort_values(["delta_minutes_abs", "anchor_time"]).iloc[0]
    return {
        "nearest_python_anchor": pd.Timestamp(row["anchor_time"]),
        "nearest_python_trigger": row.get("trigger", ""),
        "nearest_python_mode_raw": row.get("mode_raw", ""),
        "nearest_python_mode_norm": row.get("mode_norm", ""),
        "nearest_python_entry_time": pd.Timestamp(row["entry_time"]) if pd.notna(row.get("entry_time")) else pd.NaT,
        "nearest_python_stage3_time": pd.Timestamp(row["stage3_time"]) if pd.notna(row.get("stage3_time")) else pd.NaT,
        "nearest_python_stop_dist_1dp": row.get("python_stop_dist_1dp", None),
        "nearest_python_total_points": row.get("total_points", None),
        "nearest_python_delta_minutes": row.get("delta_minutes_signed", None),
    }


def slot1_snapshot(m15: pd.DataFrame, anchor_time: pd.Timestamp, direction: str, stop_price: float | None) -> dict[str, object]:
    seg = m15t.m15_window(m15, pd.Timestamp(anchor_time))
    if seg.empty:
        return {
            "slot1_time": pd.NaT,
            "slot1_close": None,
            "slot1_sma13": None,
            "slot1_same_side": False,
            "slot1_stop_dist": None,
            "slot1_stop_side_ok": None,
        }

    row = seg.iloc[0]
    close = float(row["close"])
    sma13 = float(row["SMA_13"]) if pd.notna(row["SMA_13"]) else None
    is_long = direction == "L"
    same_side = bool(sma13 is not None and ((is_long and close > sma13) or ((not is_long) and close < sma13)))
    stop_dist = abs(close - stop_price) if stop_price is not None else None
    stop_side_ok = None
    if stop_price is not None:
        stop_side_ok = (stop_price < close) if is_long else (stop_price > close)
    return {
        "slot1_time": pd.Timestamp(row["date"]),
        "slot1_close": close,
        "slot1_sma13": sma13,
        "slot1_same_side": same_side,
        "slot1_stop_dist": stop_dist,
        "slot1_stop_side_ok": stop_side_ok,
    }


def classify_shared_mismatch(row: pd.Series, picked_map: dict[str, dict], m15: pd.DataFrame, spec_lo: float, spec_hi: float) -> tuple[str, dict[str, object]]:
    key = make_key(pd.Timestamp(row["anchor_time_mt5"]), str(row["dir_mt5"]))
    picked = picked_map.get(key, {})
    stop_price = float(picked["stop"]) if picked and pd.notna(picked.get("stop")) else None
    slot1 = slot1_snapshot(m15, pd.Timestamp(row["anchor_time_mt5"]), str(row["dir_mt5"]), stop_price)
    slot1_dist = slot1["slot1_stop_dist"]
    slot1_in_spec = bool(slot1_dist is not None and spec_lo <= float(slot1_dist) <= spec_hi)
    if bool(row.get("trigger_mt5") == row.get("trigger_python")) and bool(row.get("mode_norm_mt5") == row.get("mode_norm_python")):
        if row.get("trigger_mt5") == "M30 CLOSE":
            cause = "同锚点同模式，仅止损距离不同：EA 用信号时实时报价，Python 用K线价"
        else:
            cause = "同锚点同模式，仅止损距离不同：EA 用 slot1 触发时的实时报价，Python 用M15收盘价"
    elif row.get("trigger_mt5") == "M15 SLOT1" and row.get("trigger_python") == "M30 CLOSE":
        if slot1_in_spec and bool(slot1["slot1_same_side"]) and slot1["slot1_stop_side_ok"] is False:
            cause = "EA 将 stop 当距离参考并重锚真实SL；Python 把 stop 当绝对价，slot1 被侧向校验挡掉"
        elif slot1_in_spec and bool(slot1["slot1_same_side"]):
            cause = "slot1 条件本身可过，但 Python 当前主线仍保留到 M30 CLOSE"
        else:
            cause = "EA 触发为 slot1，但 Python 当前样本在 slot1 侧复算未通过"
    else:
        cause = "共享样本存在触发或模式口径差异，需要逐笔复核"

    extra = {
        "python_variant": picked.get("variant", ""),
        "python_entry": picked.get("entry", None),
        "python_stop": picked.get("stop", None),
        "slot1_time": slot1["slot1_time"],
        "slot1_close": slot1["slot1_close"],
        "slot1_sma13": slot1["slot1_sma13"],
        "slot1_same_side": slot1["slot1_same_side"],
        "slot1_stop_dist": slot1["slot1_stop_dist"],
        "slot1_stop_side_ok": slot1["slot1_stop_side_ok"],
        "slot1_stop_in_spec": slot1_in_spec,
    }
    return cause, extra


def classify_mt5_only(
    row: pd.Series,
    picked_map: dict[str, dict],
    accepted_map: dict[str, dict],
    raw_df: pd.DataFrame,
    py_executed: pd.DataFrame,
    m15: pd.DataFrame,
    spec_lo: float,
    spec_hi: float,
) -> tuple[str, str, dict[str, object]]:
    key = str(row["key"])
    picked = picked_map.get(key)
    accepted = accepted_map.get(key)
    raw_same = raw_df[raw_df["key"] == key].copy() if not raw_df.empty and "key" in raw_df.columns else pd.DataFrame()

    stop_price = None
    if picked and pd.notna(picked.get("stop")):
        stop_price = float(picked["stop"])
    elif accepted and pd.notna(accepted.get("stop")):
        stop_price = float(accepted["stop"])
    elif not raw_same.empty and pd.notna(raw_same.iloc[0].get("stop")):
        stop_price = float(raw_same.iloc[0]["stop"])

    slot1 = slot1_snapshot(m15, pd.Timestamp(row["anchor_time"]), str(row["dir"]), stop_price)
    slot1_dist = slot1["slot1_stop_dist"]
    slot1_in_spec = bool(slot1_dist is not None and spec_lo <= float(slot1_dist) <= spec_hi)

    if picked is not None:
        cause = "Python 已通过 Layer3，但执行阶段被持仓互斥或前序交易占用挡掉"
        blocking = find_blocking_trade(py_executed, pd.Timestamp(row["anchor_time"]))
    elif accepted is not None:
        cause = "Python 已进入 accepted，但被 Layer3 过滤"
        blocking = {}
    elif not raw_same.empty:
        first = raw_same.iloc[0]
        spec_reason = str(first.get("spec_reason", ""))
        if spec_reason == "too_wide":
            cause = "Python 原始候选存在，但按当前口径止损过宽"
        elif spec_reason == "too_tight":
            cause = "Python 原始候选存在，但按当前口径止损过窄"
        else:
            cause = "Python 原始候选存在，但未进入 accepted"
        blocking = {}
    elif row.get("trigger") == "M15 SLOT1" and slot1_in_spec and bool(slot1["slot1_same_side"]) and slot1["slot1_stop_side_ok"] is False:
        cause = "EA 的 slot1 距离口径可过；Python 因绝对 stop 侧校验没有生成对应候选"
        blocking = {}
    else:
        cause = "Python 当前口径下未找到同锚点候选，需要进一步复核 Layer2/stop 生成过程"
        blocking = {}

    nearest = find_nearest_raw_candidate(raw_df, pd.Timestamp(row["anchor_time"]), str(row["dir"]))
    nearest_python = find_nearest_python_executed(py_executed, pd.Timestamp(row["anchor_time"]), str(row["dir"]))

    refined_cause = cause
    if (
        picked is None
        and accepted is None
        and raw_same.empty
        and not (
            row.get("trigger") == "M15 SLOT1"
            and slot1_in_spec
            and bool(slot1["slot1_same_side"])
            and slot1["slot1_stop_side_ok"] is False
        )
        and nearest_python
    ):
        same_trigger = str(nearest_python.get("nearest_python_trigger", "")) == str(row.get("trigger", ""))
        same_mode = str(nearest_python.get("nearest_python_mode_norm", "")) == str(row.get("mode_norm", ""))
        delta_minutes = nearest_python.get("nearest_python_delta_minutes", None)
        delta_text = ""
        if delta_minutes is not None and pd.notna(delta_minutes):
            delta_text = f"（最近 executed 偏移 {float(delta_minutes):.0f} 分钟）"
        if same_trigger and same_mode:
            refined_cause = f"Python 已有近邻 executed，同方向/同触发/同模式，但锚点偏移{delta_text}"
        elif same_trigger and not same_mode:
            refined_cause = f"Python 已有近邻 executed，同方向/同触发，但模式不同{delta_text}"
        elif (not same_trigger) and same_mode:
            refined_cause = f"Python 已有近邻 executed，同方向/同模式，但属于跨触发映射{delta_text}"
        else:
            refined_cause = f"Python 已有近邻 executed，但属于跨触发/跨模式映射{delta_text}"

    extra = {
        "python_picked": picked is not None,
        "python_accepted": accepted is not None,
        "raw_match_count": int(len(raw_same)),
        "slot1_time": slot1["slot1_time"],
        "slot1_close": slot1["slot1_close"],
        "slot1_sma13": slot1["slot1_sma13"],
        "slot1_same_side": slot1["slot1_same_side"],
        "slot1_stop_dist": slot1["slot1_stop_dist"],
        "slot1_stop_side_ok": slot1["slot1_stop_side_ok"],
        "slot1_stop_in_spec": slot1_in_spec,
    }
    extra.update(blocking)
    extra.update(nearest)
    extra.update(nearest_python)
    return cause, refined_cause, extra


def render_markdown(session: LogSession, shared_diag: pd.DataFrame, mt5_only_diag: pd.DataFrame, output_dir: Path) -> str:
    params = session_strategy_params(session)
    lines = [
        "# MT5 / Python 成因诊断",
        "",
        f"- 会话编号：`{session.session_id}`",
        f"- 回测区间：`{session.start:%Y-%m-%d %H:%M:%S}` 到 `{session.end:%Y-%m-%d %H:%M:%S}`",
        f"- 参数摘要：`{short_params(params)}`",
        f"- 输出目录：`{output_dir}`",
        "",
    ]

    if not shared_diag.empty:
        cause_count = shared_diag["成因分类"].value_counts().reset_index()
        cause_count.columns = ["成因分类", "笔数"]
        lines.extend(
            [
                "## 共享错配成因",
                "",
                cause_count.to_markdown(index=False),
                "",
                shared_diag[
                    [
                        "anchor_time_mt5",
                        "dir_mt5",
                        "trigger_mt5",
                        "trigger_python",
                        "mt5_stop_dist",
                        "python_stop_dist_1dp",
                        "成因分类",
                    ]
                ]
                .head(20)
                .to_markdown(index=False),
                "",
            ]
        )

    if not mt5_only_diag.empty:
        cause_count = mt5_only_diag["成因分类"].value_counts().reset_index()
        cause_count.columns = ["成因分类", "笔数"]
        lines.extend(
            [
                "## MT5 独有成因",
                "",
                cause_count.to_markdown(index=False),
                "",
                mt5_only_diag[
                    [
                        "anchor_time",
                        "dir",
                        "trigger",
                        "mode_raw",
                        "mt5_stop_dist",
                        "成因分类",
                    ]
                ]
                .head(20)
                .to_markdown(index=False),
                "",
            ]
        )

    if not mt5_only_diag.empty and "缁嗗垎鎴愬洜" in mt5_only_diag.columns:
        refined_count = mt5_only_diag["缁嗗垎鎴愬洜"].value_counts().reset_index()
        refined_count.columns = ["缁嗗垎鎴愬洜", "绗旀暟"]
        lines.extend(
            [
                "## MT5 鐙湁缁嗗垎鎴愬洜",
                "",
                refined_count.to_markdown(index=False),
                "",
                mt5_only_diag[
                    [
                        "anchor_time",
                        "dir",
                        "trigger",
                        "mode_raw",
                        "nearest_python_anchor",
                        "nearest_python_trigger",
                        "nearest_python_mode_norm",
                        "缁嗗垎鎴愬洜",
                    ]
                ]
                .head(20)
                .to_markdown(index=False),
                "",
            ]
        )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose root causes for MT5 vs Python session mismatches.")
    parser.add_argument("log_path", type=Path, help="Path to MT5 tester log file")
    parser.add_argument("--session-id", type=int, required=True, help="Session id from sessions_summary.csv")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=VALIDATION_DIR / "mt5_log_session_diag",
        help="Directory for diagnosis outputs",
    )
    parser.add_argument(
        "--ea-executable-diag",
        action="store_true",
        help="Use Python EA executable diagnostic mode for baseline rebuild.",
    )
    args = parser.parse_args()

    ensure_dirs()
    sessions = parse_log_sessions(args.log_path)
    target = next((session for session in sessions if session.session_id == args.session_id), None)
    if target is None:
        raise SystemExit(f"Session id {args.session_id} not found in log: {args.log_path}")

    output_dir = args.output_dir / f"session_{args.session_id:02d}"
    output_dir.mkdir(parents=True, exist_ok=True)

    params = session_strategy_params(target)
    spec_lo = float(params["spec_lo"])
    spec_hi = float(params["spec_hi"])
    outputs = compare_session(target, ea_executable_diag=args.ea_executable_diag)
    result = build_result_for_session(target, ea_executable_diag=args.ea_executable_diag)
    raw_df, _ = build_raw_frames_for_session(target)
    picked_map, accepted_map = build_meta_maps(result)
    _, _, m15 = cb.load_market_context()

    shared_diag = outputs["shared_mismatch"].copy()
    if not shared_diag.empty:
        shared_causes = []
        extras = []
        for _, row in shared_diag.iterrows():
            cause, extra = classify_shared_mismatch(row, picked_map, m15, spec_lo, spec_hi)
            shared_causes.append(cause)
            extras.append(extra)
        shared_diag["成因分类"] = shared_causes
        shared_diag = pd.concat([shared_diag.reset_index(drop=True), pd.DataFrame(extras)], axis=1)

    mt5_only_diag = outputs["mt5_only"].copy()
    py_executed = outputs["python"].copy()
    if not mt5_only_diag.empty:
        causes = []
        refined_causes = []
        extras = []
        for _, row in mt5_only_diag.iterrows():
            cause, refined_cause, extra = classify_mt5_only(
                row,
                picked_map,
                accepted_map,
                raw_df,
                py_executed,
                m15,
                spec_lo,
                spec_hi,
            )
            causes.append(cause)
            refined_causes.append(refined_cause)
            extras.append(extra)
        mt5_only_diag["成因分类"] = causes
        mt5_only_diag["缁嗗垎鎴愬洜"] = refined_causes
        mt5_only_diag = pd.concat([mt5_only_diag.reset_index(drop=True), pd.DataFrame(extras)], axis=1)

    export_csv(shared_diag, output_dir / "shared_mismatch_cause_diag.csv")
    export_csv(mt5_only_diag, output_dir / "mt5_only_cause_diag.csv")
    write_text(output_dir / "mismatch_cause_diag.md", render_markdown(target, shared_diag, mt5_only_diag, output_dir))

    print(f"Diagnosed session {target.session_id}.")
    print(f"Wrote {output_dir}")


if __name__ == "__main__":
    main()
