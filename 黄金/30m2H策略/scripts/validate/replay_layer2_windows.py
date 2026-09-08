# -*- coding: utf-8 -*-
"""Replay selected Layer 2 windows for the 30m x 2H mainline."""
from __future__ import annotations


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

from strategy_30m2h_common import VALIDATION_DIR, ensure_dirs, export_csv, write_text  # noqa: E402
import _current_baseline as cb  # type: ignore  # noqa: E402
import _h2_early_gate_test as h2t  # type: ignore  # noqa: E402
import _m15_h2_combo_test as combo  # type: ignore  # noqa: E402
import _m15_early_entry_test as m15t  # type: ignore  # noqa: E402
import _pre_cross_range_test as pct  # type: ignore  # noqa: E402


DIRECTION_COL = "方向"
MERGED_DIRECTION_COL = "方向_合并后"
POST_COL = "merged_post_cross_n"
TARGET_TIMES = [
    pd.Timestamp("2025-04-14 00:00:00"),
    pd.Timestamp("2026-02-03 01:00:00"),
    pd.Timestamp("2026-06-30 08:00:00"),
    pd.Timestamp("2026-06-30 09:00:00"),
]
WINDOW_HOURS = 2


def key_of(anchor_time: pd.Timestamp, direction: str) -> str:
    return pd.Timestamp(anchor_time).strftime("%Y-%m-%d %H:%M:%S") + "|" + direction


def raw_mode_lookup(raw_df: pd.DataFrame) -> dict[tuple[pd.Timestamp, str, str], dict]:
    out: dict[tuple[pd.Timestamp, str, str], dict] = {}
    if raw_df.empty:
        return out
    for _, row in raw_df.iterrows():
        out[(pd.Timestamp(row["anchor_time"]), str(row["dir"]), str(row["mode"]))] = row.to_dict()
    return out


def accepted_key_lookup(accepted: pd.DataFrame) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if accepted.empty:
        return out
    tmp = accepted.copy()
    tmp["anchor_time"] = pd.to_datetime(tmp["date"])
    tmp["key"] = tmp["anchor_time"].dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + tmp["dir"].astype(str)
    for _, row in tmp.iterrows():
        out[str(row["key"])] = row.to_dict()
    return out


def detect_pre_cross(df: pd.DataFrame, i: int) -> tuple[int, bool, bool, float | None]:
    if i < 1:
        return 0, False, False, None
    sma5 = df["SMA_5"].iloc[i]
    sma13 = df["SMA_13"].iloc[i]
    sma13_prev = df["SMA_13"].iloc[i - 1]
    close = df["close"].iloc[i]
    close_prev = df["close"].iloc[i - 1]
    direction = df[DIRECTION_COL].iloc[i]
    if any(pd.isna(x) for x in (sma5, sma13, sma13_prev, close, close_prev)):
        return 0, False, False, None
    if direction in ("good", "bad"):
        return 0, False, False, None
    gap = abs(float(sma5) - float(sma13)) / float(sma13) if float(sma13) != 0 else None
    if gap is None or gap > 0.003:
        return 0, False, False, gap
    long_setup = close_prev <= sma13_prev and close > sma13 and sma5 < sma13
    short_setup = close_prev >= sma13_prev and close < sma13 and sma5 > sma13
    if long_setup:
        return 1, True, False, gap
    if short_setup:
        return -1, False, True, gap
    return 0, False, False, gap


def detect_cross(df: pd.DataFrame, i: int) -> int:
    direction = df[DIRECTION_COL].iloc[i]
    if direction == "good":
        return 1
    if direction == "bad":
        return -1
    return 0


def detect_post_n(df: pd.DataFrame, i: int) -> tuple[int, int]:
    pn = int(df[POST_COL].iloc[i]) if not pd.isna(df[POST_COL].iloc[i]) else 0
    if pct.POST_N_MIN <= pn <= pct.POST_N_MAX:
        return 1, pn
    if -pct.POST_N_MAX <= pn <= -pct.POST_N_MIN:
        return -1, abs(pn)
    return 0, 0


def mode_priority(pre_dir: int, cross_dir: int, post_dir: int, post_n: int) -> tuple[str, str]:
    if pre_dir != 0:
        return "pre_cross", "L" if pre_dir > 0 else "S"
    if cross_dir != 0:
        return "cross", "L" if cross_dir > 0 else "S"
    if post_dir != 0:
        return f"post_n{post_n}", "L" if post_dir > 0 else "S"
    return "", ""


def theoretical_stop(df: pd.DataFrame, i: int, mode_name: str, direction: str) -> tuple[float | None, float | None, str]:
    is_long = direction == "L"
    entry = float(df["close"].iloc[i])
    if mode_name in {"pre_cross", "cross"}:
        stop = pct.prior_segment_stop(i, is_long, df[DIRECTION_COL].values, df["SMA_13"].values)
    elif mode_name.startswith("post_n"):
        stop = float(df["SMA_13"].iloc[i]) if pd.notna(df["SMA_13"].iloc[i]) else np.nan
    else:
        return None, None, ""

    if pd.isna(stop):
        return None, None, "no_stop"
    stop = float(stop)
    if is_long and stop >= entry:
        return stop, None, "wrong_side"
    if (not is_long) and stop <= entry:
        return stop, None, "wrong_side"
    sd = abs(entry - stop)
    if sd < pct.SPEC_LO:
        return stop, sd, "too_tight"
    if sd > pct.SPEC_HI:
        return stop, sd, "too_wide"
    return stop, sd, "ok"


def build_replay_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df, h2, m15 = cb.load_market_context()
    q2_pass_set, q2_factor_map, _, _ = h2t.early_precompute(h2, df, 2, False)
    raw_df, accepted = combo.build_candidate_frames(df, q2_pass_set, q2_factor_map)
    raw_df = raw_df.copy()
    raw_df["anchor_time"] = pd.to_datetime(raw_df["date"])
    accepted_lookup = accepted_key_lookup(accepted)
    raw_lookup = raw_mode_lookup(raw_df)

    bar_rows: list[dict] = []
    summary_rows: list[dict] = []
    raw_rows: list[pd.DataFrame] = []
    m15_rows: list[pd.DataFrame] = []

    for target_time in TARGET_TIMES:
        mask = (
            (pd.to_datetime(df["date"]) >= target_time - pd.Timedelta(hours=WINDOW_HOURS))
            & (pd.to_datetime(df["date"]) <= target_time + pd.Timedelta(hours=WINDOW_HOURS))
        )
        window = df.loc[mask].copy().reset_index()
        if not window.empty:
            m15_window = m15[
                (pd.to_datetime(m15["date"]) >= target_time - pd.Timedelta(minutes=30))
                & (pd.to_datetime(m15["date"]) <= target_time + pd.Timedelta(minutes=30))
            ].copy()
            if not m15_window.empty:
                m15_window.insert(0, "目标时间", target_time)
                m15_rows.append(m15_window)

        nearby_raw = raw_df[
            (raw_df["anchor_time"] >= target_time - pd.Timedelta(hours=WINDOW_HOURS))
            & (raw_df["anchor_time"] <= target_time + pd.Timedelta(hours=WINDOW_HOURS))
        ].copy()
        if not nearby_raw.empty:
            nearby_raw.insert(0, "目标时间", target_time)
            raw_rows.append(nearby_raw)

        target_summary: dict[str, object] = {
            "目标时间": target_time,
            "窗口内原始候选数": int(len(nearby_raw)),
        }

        for _, row in window.iterrows():
            i = int(row["index"])
            anchor_time = pd.Timestamp(row["date"])
            pre_dir, pre_long, pre_short, gap = detect_pre_cross(df, i)
            cross_dir = detect_cross(df, i)
            post_dir, post_n = detect_post_n(df, i)
            mode_name, direction = mode_priority(pre_dir, cross_dir, post_dir, post_n)
            stop_price, stop_dist, stop_reason = theoretical_stop(df, i, mode_name, direction) if mode_name else (None, None, "")
            exact_raw = raw_lookup.get((anchor_time, direction, mode_name)) if mode_name else None
            accepted_key = key_of(anchor_time, direction) if direction else ""
            accepted_exact = accepted_lookup.get(accepted_key)
            factors = q2_factor_map.get(i, {})

            record = {
                "目标时间": target_time,
                "bar_time": anchor_time,
                "是否目标bar": anchor_time == target_time,
                "close": row["close"],
                "SMA_5": row["SMA_5"],
                "SMA_13": row["SMA_13"],
                "方向": row[DIRECTION_COL],
                "方向_合并后": row[MERGED_DIRECTION_COL],
                "merged_post_cross_n": row[POST_COL],
                "Layer1通过": i in q2_pass_set,
                "Bias_5": factors.get("Bias_5"),
                "Bias_13": factors.get("Bias_13"),
                "Bias_55": factors.get("Bias_55"),
                "pre_cross_dir": pre_dir,
                "pre_cross_gap": gap,
                "pre_cross_long_setup": pre_long,
                "pre_cross_short_setup": pre_short,
                "cross_dir": cross_dir,
                "post_n_dir": post_dir,
                "post_n_value": post_n,
                "优先模式": mode_name,
                "优先方向": direction,
                "理论stop": stop_price,
                "理论sd": stop_dist,
                "理论spec判断": stop_reason,
                "原始候选命中": bool(exact_raw is not None),
                "原始候选spec": exact_raw.get("spec_reason") if exact_raw else "",
                "原始候选sd": exact_raw.get("sd") if exact_raw else None,
                "accepted命中": bool(accepted_exact is not None),
                "accepted模式": accepted_exact.get("mode") if accepted_exact else "",
                "accepted_sd": accepted_exact.get("sd") if accepted_exact else None,
            }
            bar_rows.append(record)

            if anchor_time == target_time:
                target_summary.update(
                    {
                        "目标bar方向": row[DIRECTION_COL],
                        "目标bar方向_合并后": row[MERGED_DIRECTION_COL],
                        "目标bar_post_n": row[POST_COL],
                        "目标bar_Layer1通过": i in q2_pass_set,
                        "目标bar_pre_cross_dir": pre_dir,
                        "目标bar_cross_dir": cross_dir,
                        "目标bar_post_n_dir": post_dir,
                        "目标bar_优先模式": mode_name,
                        "目标bar_优先方向": direction,
                        "目标bar_理论stop": stop_price,
                        "目标bar_理论sd": stop_dist,
                        "目标bar_理论spec判断": stop_reason,
                        "目标bar_原始候选命中": bool(exact_raw is not None),
                        "目标bar_accepted命中": bool(accepted_exact is not None),
                    }
                )

        if nearby_raw.empty:
            target_summary["最近原始候选"] = ""
            target_summary["最近原始spec"] = "无候选"
        else:
            nearby_raw = nearby_raw.copy()
            nearby_raw["delta_minutes"] = (
                nearby_raw["anchor_time"] - target_time
            ).abs() / pd.Timedelta(minutes=1)
            nearest = nearby_raw.sort_values(["delta_minutes", "anchor_time"]).iloc[0]
            target_summary["最近原始候选"] = f"{nearest['anchor_time']} {nearest['dir']} {nearest['mode']}"
            target_summary["最近原始spec"] = nearest["spec_reason"]
            target_summary["最近原始sd"] = nearest["sd"]
            target_summary["最近原始相差分钟"] = nearest["delta_minutes"]

        summary_rows.append(target_summary)

    bar_frame = pd.DataFrame(bar_rows)
    summary_frame = pd.DataFrame(summary_rows)
    raw_frame = pd.concat(raw_rows, ignore_index=True) if raw_rows else pd.DataFrame()
    m15_frame = pd.concat(m15_rows, ignore_index=True) if m15_rows else pd.DataFrame()
    return summary_frame, bar_frame, raw_frame, m15_frame


def render_markdown(summary_frame: pd.DataFrame, raw_frame: pd.DataFrame) -> str:
    lines = [
        "# Layer2 窗口逐笔回放",
        "",
        "## 回放目标",
        "",
        "- 2025-04-14 00:00:00",
        "- 2026-02-03 01:00:00",
        "- 2026-06-30 08:00:00",
        "- 2026-06-30 09:00:00",
        "",
        "## 目标摘要",
        "",
        summary_frame.to_markdown(index=False),
        "",
    ]

    if not raw_frame.empty:
        for target_time, group in raw_frame.groupby("目标时间", sort=False):
            lines.extend(
                [
                    f"## 附近原始候选 {target_time}",
                    "",
                    group[
                        ["anchor_time", "dir", "mode", "entry", "stop", "sd", "spec_pass", "spec_reason"]
                    ].to_markdown(index=False),
                    "",
                ]
            )
    return "\n".join(lines)


def main() -> None:
    ensure_dirs()
    summary_frame, bar_frame, raw_frame, m15_frame = build_replay_frames()
    output_dir = VALIDATION_DIR / "layer2_window_replay_20260708"
    output_dir.mkdir(parents=True, exist_ok=True)
    export_csv(summary_frame, output_dir / "layer2_targets_summary.csv")
    export_csv(bar_frame, output_dir / "layer2_replay_bars.csv")
    export_csv(raw_frame, output_dir / "layer2_replay_raw_candidates.csv")
    export_csv(m15_frame, output_dir / "layer2_replay_m15.csv")
    write_text(output_dir / "layer2_window_replay.md", render_markdown(summary_frame, raw_frame))
    print(f"Wrote {output_dir}")


if __name__ == "__main__":
    main()
