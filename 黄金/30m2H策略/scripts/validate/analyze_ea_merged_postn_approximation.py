# -*- coding: utf-8 -*-
"""Compare EA merged-post_n approximation against Python merged_post_cross_n."""
from __future__ import annotations


import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
ROOT_SCRIPTS_DIR = ROOT / "scripts"
STRATEGY_SCRIPTS_DIR = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT_SCRIPTS_DIR))
sys.path.insert(0, str(STRATEGY_SCRIPTS_DIR))

import _current_baseline as cb  # type: ignore  # noqa: E402
from strategy_30m2h_common import VALIDATION_DIR, export_csv, write_text  # noqa: E402


OUTPUT_DIR = VALIDATION_DIR / "ea_merged_postn_approx_diag_20260711"
WINDOW_BARS = 500
MIN_LEN = 8
HOT_TIMES = [
    "2023-03-15 14:30:00",
    "2025-10-09 02:30:00",
    "2026-02-02 17:00:00",
    "2026-02-02 18:00:00",
    "2026-02-02 19:00:00",
]


def raw_dir_code(curr_above: bool, prev_above: bool) -> int:
    if curr_above and not prev_above:
        return 2
    if (not curr_above) and prev_above:
        return -2
    if curr_above and prev_above:
        return 1
    return -1


def raw_dir_sign(code: int) -> int:
    return 1 if code > 0 else -1


def merged_last_sign_for_window(sign_codes: list[int], min_len: int = MIN_LEN) -> int:
    completed = len(sign_codes)
    if completed <= 0:
        return 0

    dir_codes = list(sign_codes)
    crossings: list[int] = []
    cross_types: list[int] = []
    for i, code in enumerate(dir_codes):
        if abs(code) == 2:
            crossings.append(i)
            cross_types.append(code)

    if not crossings:
        return raw_dir_sign(dir_codes[-1])

    first_type = cross_types[0]
    state = -1 if first_type == 2 else 1
    i = 0
    while i < len(crossings):
        pos = crossings[i]
        type_ = cross_types[i]
        if i + 1 >= len(crossings):
            break

        next_pos = crossings[i + 1]
        region_count = 0
        for k in range(pos + 1, next_pos):
            if type_ == 2 and dir_codes[k] == 1:
                region_count += 1
            if type_ == -2 and dir_codes[k] == -1:
                region_count += 1

        if region_count < min_len:
            dir_codes[pos] = state
            for k in range(pos + 1, next_pos):
                dir_codes[k] = state
            dir_codes[next_pos] = state

            del crossings[i : i + 2]
            del cross_types[i : i + 2]
            if not crossings:
                break
            continue

        state = 1 if type_ == 2 else -1
        i += 1

    return raw_dir_sign(dir_codes[-1])


def build_raw_codes(df: pd.DataFrame) -> list[int]:
    sma5 = df["SMA_5"].tolist()
    sma13 = df["SMA_13"].tolist()
    prev_above = sma5[0] > sma13[0]
    out = [1 if prev_above else -1]
    for i in range(1, len(df)):
        curr_above = sma5[i] > sma13[i]
        out.append(raw_dir_code(curr_above, prev_above))
        prev_above = curr_above
    return out


def simulate(df: pd.DataFrame) -> pd.DataFrame:
    raw_codes = build_raw_codes(df)
    approx_signs: list[int] = []
    counter = 0
    last_dir = 0
    ea_counter: list[int] = []

    for i in range(len(df)):
        start = max(0, i - WINDOW_BARS + 1)
        approx_sign = merged_last_sign_for_window(raw_codes[start : i + 1])
        approx_signs.append(approx_sign)

        if approx_sign == 0:
            ea_counter.append(counter)
            continue

        if last_dir == 0:
            counter = 1 if approx_sign > 0 else -1
            last_dir = approx_sign
        elif approx_sign != last_dir:
            counter = 1 if approx_sign > 0 else -1
            last_dir = approx_sign
        elif counter > 0:
            counter += 1
        elif counter < 0:
            counter -= 1
        else:
            counter = 1 if approx_sign > 0 else -1

        ea_counter.append(counter)

    out = df[["date", "方向", "方向_合并后", "merged_post_cross_n"]].copy()
    out["ea_approx_merged_sign"] = approx_signs
    out["ea_approx_merged_post_n"] = ea_counter
    out["counter_diff"] = out["ea_approx_merged_post_n"] - out["merged_post_cross_n"]
    out["abs_counter_diff"] = out["counter_diff"].abs()
    out["python_is_signal_band"] = out["merged_post_cross_n"].abs().between(2, 6)
    out["ea_is_signal_band"] = out["ea_approx_merged_post_n"].abs().between(2, 6)
    out["band_mismatch"] = out["python_is_signal_band"] != out["ea_is_signal_band"]
    return out


def render_markdown(summary: pd.DataFrame, mismatches: pd.DataFrame, hot_windows: dict[str, pd.DataFrame]) -> str:
    lines = [
        "# EA merged_post_n Approximation Diagnosis",
        "",
        "## Summary",
        "",
        summary.to_markdown(index=False),
        "",
        "## Hot Windows",
        "",
    ]
    for ts, window in hot_windows.items():
        lines.append(f"### {ts}")
        lines.append("")
        lines.append(window.to_markdown(index=False))
        lines.append("")

    lines.extend(
        [
            "## Largest Band Mismatches",
            "",
            mismatches.to_markdown(index=False),
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    df, _, _ = cb.load_market_context()
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    frame = simulate(df)

    summary = pd.DataFrame(
        [
            {"metric": "rows", "value": int(len(frame))},
            {"metric": "band_mismatch_rows", "value": int(frame["band_mismatch"].sum())},
            {
                "metric": "python_signal_band_rows",
                "value": int(frame["python_is_signal_band"].sum()),
            },
            {
                "metric": "ea_signal_band_rows",
                "value": int(frame["ea_is_signal_band"].sum()),
            },
            {
                "metric": "max_abs_counter_diff",
                "value": float(frame["abs_counter_diff"].max()),
            },
        ]
    )

    mismatches = (
        frame[frame["band_mismatch"]]
        .sort_values(["abs_counter_diff", "date"], ascending=[False, True])
        .head(40)
        .reset_index(drop=True)
    )

    hot_windows: dict[str, pd.DataFrame] = {}
    for ts in HOT_TIMES:
        anchor = pd.Timestamp(ts)
        hot_windows[ts] = frame[
            (frame["date"] >= anchor - pd.Timedelta(hours=2))
            & (frame["date"] <= anchor + pd.Timedelta(hours=2))
        ].reset_index(drop=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    export_csv(summary, OUTPUT_DIR / "summary.csv")
    export_csv(frame, OUTPUT_DIR / "full_compare.csv")
    export_csv(mismatches, OUTPUT_DIR / "band_mismatches_top40.csv")
    for ts, window in hot_windows.items():
        stamp = pd.Timestamp(ts).strftime("%Y%m%d_%H%M%S")
        export_csv(window, OUTPUT_DIR / f"hot_window_{stamp}.csv")
    write_text(OUTPUT_DIR / "ea_merged_postn_approx_diag.md", render_markdown(summary, mismatches, hot_windows))

    print(summary.to_string(index=False))
    print(f"\nWrote {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
