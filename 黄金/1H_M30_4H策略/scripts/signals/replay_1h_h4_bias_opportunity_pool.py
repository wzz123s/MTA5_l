# -*- coding: utf-8 -*-
"""Build broad 1H_M30_4H H4-bias opportunity pools before tightening thresholds."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)



import bisect
from pathlib import Path

import numpy as np
import pandas as pd

from replay_1h_bias55_h1_stop_optimization import build_signal_plans, load_frames, replay_with_stop_source
from replay_raw_signals_with_stops import LOT_FOR_REPORT, markdown_table, metric, split_test, trade_sign, yearly_positive_count


STRATEGY = "1H_M30_4H"
ROOT = Path(r"F:\use_code\MTA5_l")
OUT_DIR = ROOT / "黄金" / f"{STRATEGY}策略" / "data" / "validation" / "h4_bias_opportunity_pool"
STOP_VARIANTS = ["h1_last6_hilo", "h1_last3_hilo", "h1_dir_segment_hilo"]
BIAS55_THRESHOLDS = [round(value / 10.0, 1) for value in range(10, 41, 2)]
BIAS55_FOCUS_THRESHOLD = 2.0
BIAS13_THRESHOLDS = [round(value / 10.0, 1) for value in range(5, 41, 5)]
BIAS55_COMBO_THRESHOLDS = [1.5, 2.0, 2.4, 3.0]
MIN_SAMPLE = 30


def high_bias_features(signal_times: pd.Series, h1: pd.DataFrame, h4: pd.DataFrame) -> pd.DataFrame:
    h1_times = pd.to_datetime(h1["date"]).values.astype("datetime64[ns]")
    h4_times = pd.to_datetime(h4["date"]).values.astype("datetime64[ns]")
    rows: list[dict] = []
    for signal_time in pd.to_datetime(signal_times):
        h1_idx = bisect.bisect_right(h1_times, signal_time.to_datetime64()) - 1
        h4_idx = bisect.bisect_right(h4_times, signal_time.to_datetime64()) - 1
        if h1_idx < 0 or h4_idx < 0:
            rows.append(
                {
                    "h1roll4_high": np.nan,
                    "h1roll4_high_time": pd.NaT,
                    "h1roll4_high_bias13_h4sma_pct": np.nan,
                    "h1roll4_high_bias55_h4sma_pct": np.nan,
                    "h1roll4_closed_h1_count": 0,
                }
            )
            continue
        window = h1.iloc[max(0, h1_idx - 3) : h1_idx + 1].copy()
        high = pd.to_numeric(window["high"], errors="coerce")
        highest_high = float(high.max()) if high.notna().any() else np.nan
        high_idx = high.idxmax() if high.notna().any() else None
        h4_row = h4.iloc[h4_idx]
        sma13 = float(h4_row["SMA_13"]) if not pd.isna(h4_row["SMA_13"]) else np.nan
        sma55 = float(h4_row["SMA_55"]) if not pd.isna(h4_row["SMA_55"]) else np.nan
        rows.append(
            {
                "h1roll4_high": highest_high,
                "h1roll4_high_time": window.loc[high_idx, "date"] if high_idx is not None else pd.NaT,
                "h1roll4_high_bias13_h4sma_pct": (highest_high - sma13) / sma13 * 100.0
                if np.isfinite(highest_high) and np.isfinite(sma13) and sma13 != 0
                else np.nan,
                "h1roll4_high_bias55_h4sma_pct": (highest_high - sma55) / sma55 * 100.0
                if np.isfinite(highest_high) and np.isfinite(sma55) and sma55 != 0
                else np.nan,
                "h1roll4_closed_h1_count": int(len(window)),
            }
        )
    return pd.DataFrame(rows)


def add_high_bias_features(frame: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame) -> pd.DataFrame:
    return pd.concat([frame.reset_index(drop=True), high_bias_features(frame["signal_time"], h1, h4)], axis=1)


def threshold_mask(frame: pd.DataFrame, column: str, threshold: float) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="coerce")
    side = frame["dir"].astype(str).str.upper()
    short_mask = side.eq("S") & values.ge(threshold)
    long_mask = side.eq("L") & values.le(-threshold)
    return short_mask | long_mask


def combo_mask(frame: pd.DataFrame, threshold55: float, threshold13: float) -> pd.Series:
    values55 = pd.to_numeric(frame["h1roll4_high_bias55_h4sma_pct"], errors="coerce")
    values13 = pd.to_numeric(frame["h1roll4_high_bias13_h4sma_pct"], errors="coerce")
    side = frame["dir"].astype(str).str.upper()
    short_mask = side.eq("S") & values55.ge(threshold55) & values13.ge(threshold13)
    long_mask = side.eq("L") & values55.le(-threshold55) & values13.le(-threshold13)
    return short_mask | long_mask


def second_filter_mask(frame: pd.DataFrame, name: str) -> pd.Series:
    if name == "base":
        return pd.Series(True, index=frame.index)
    sign = frame["dir"].map(lambda value: trade_sign(value)).astype(int)
    if name == "1h_dir_align":
        return pd.to_numeric(frame["1h_dir"], errors="coerce").fillna(0).astype(int).eq(sign)
    if name == "1h_dir_against":
        return pd.to_numeric(frame["1h_dir"], errors="coerce").fillna(0).astype(int).eq(-sign)
    if name == "1h_close_side":
        return pd.to_numeric(frame["1h_close_side"], errors="coerce").fillna(0).astype(int).eq(sign)
    if name == "m30_close_side":
        return pd.to_numeric(frame["30m_close_side"], errors="coerce").fillna(0).astype(int).eq(sign)
    if name == "1h_bias5_pos":
        return pd.to_numeric(frame["1h_bias5_signed_pct"], errors="coerce").gt(0)
    if name == "1h_bias13_pos":
        return pd.to_numeric(frame["1h_bias13_signed_pct"], errors="coerce").gt(0)
    if name == "1h_bias55_pos":
        return pd.to_numeric(frame["1h_bias55_signed_pct"], errors="coerce").gt(0)
    if name == "1h_bias5_13_pos":
        return pd.to_numeric(frame["1h_bias5_signed_pct"], errors="coerce").gt(0) & pd.to_numeric(
            frame["1h_bias13_signed_pct"], errors="coerce"
        ).gt(0)
    if name == "m30_bias5_pos":
        return pd.to_numeric(frame["30m_bias5_signed_pct"], errors="coerce").gt(0)
    if name == "m30_bias13_pos":
        return pd.to_numeric(frame["30m_bias13_signed_pct"], errors="coerce").gt(0)
    if name == "m30_bias5_13_pos":
        return pd.to_numeric(frame["30m_bias5_signed_pct"], errors="coerce").gt(0) & pd.to_numeric(
            frame["30m_bias13_signed_pct"], errors="coerce"
        ).gt(0)
    if name == "buy_only":
        return frame["dir"].astype(str).str.upper().eq("L")
    if name == "sell_only":
        return frame["dir"].astype(str).str.upper().eq("S")
    raise KeyError(name)


SECOND_FILTERS = [
    ("base", "仅机会池"),
    ("1h_dir_align", "1H方向同向"),
    ("1h_dir_against", "1H方向反向"),
    ("1h_close_side", "1H close在交易方向侧"),
    ("m30_close_side", "M30 close在交易方向侧"),
    ("1h_bias5_pos", "1H bias5同向"),
    ("1h_bias13_pos", "1H bias13同向"),
    ("1h_bias55_pos", "1H bias55同向"),
    ("1h_bias5_13_pos", "1H bias5&bias13同向"),
    ("m30_bias5_pos", "M30 bias5同向"),
    ("m30_bias13_pos", "M30 bias13同向"),
    ("m30_bias5_13_pos", "M30 bias5&bias13同向"),
    ("buy_only", "只做多"),
    ("sell_only", "只做空"),
]


def summarize(frame: pd.DataFrame, *, stop_variant: str, category: str, name: str, desc: str, threshold55: float = np.nan, threshold13: float = np.nan) -> dict:
    m = metric(frame["pnl_points"])
    test = split_test(frame, "pnl_points")
    pos_years, total_years = yearly_positive_count(frame, "pnl_points")
    side = frame["dir"].astype(str).str.upper() if len(frame) else pd.Series(dtype=str)
    return {
        "stop_variant": stop_variant,
        "category": category,
        "name": name,
        "desc": desc,
        "bias55_threshold": threshold55,
        "bias13_threshold": threshold13,
        "n": m["n"],
        "long_n": int(side.eq("L").sum()) if len(frame) else 0,
        "short_n": int(side.eq("S").sum()) if len(frame) else 0,
        "pf": m["pf"],
        "test_pf": test["test_pf"],
        "ev_points": m["ev"],
        "pnl_points": m["pnl"],
        "pnl_usd_001": m["pnl"] * 100.0 * LOT_FOR_REPORT,
        "test_n": test["test_n"],
        "test_ev_points": test["test_ev"],
        "test_pnl_points": test["test_pnl"],
        "stop_hits": int(frame["stop_hit"].sum()) if len(frame) else 0,
        "stop_hit_rate_pct": float(frame["stop_hit"].mean() * 100.0) if len(frame) else 0.0,
        "avg_stop_distance": float(pd.to_numeric(frame["stop_distance"], errors="coerce").mean()) if len(frame) else 0.0,
        "positive_years": pos_years,
        "total_years": total_years,
        "sample_status": "ok" if m["n"] >= MIN_SAMPLE else "insufficient",
    }


def score(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["sample_ok"] = out["n"].astype(float).ge(MIN_SAMPLE)
    out["score"] = (
        out["sample_ok"].astype(int) * 1000.0
        + out["test_pf"].astype(float).clip(upper=50) * 20.0
        + out["pf"].astype(float).clip(upper=50) * 8.0
        + out["pnl_usd_001"].astype(float) * 0.01
        + out["positive_years"].astype(float) * 3.0
        + out["n"].astype(float).clip(upper=300) * 0.01
    )
    return out.sort_values(["score", "test_pf", "pf", "n"], ascending=[False, False, False, False]).reset_index(drop=True)


def write_report(base_scan: pd.DataFrame, second_filters: pd.DataFrame, combo_scan: pd.DataFrame) -> None:
    cols = [
        "stop_variant",
        "name",
        "bias55_threshold",
        "bias13_threshold",
        "n",
        "long_n",
        "short_n",
        "pf",
        "test_pf",
        "pnl_usd_001",
        "stop_hits",
        "positive_years",
        "total_years",
        "sample_status",
    ]
    base_focus = base_scan.loc[base_scan["bias55_threshold"].eq(BIAS55_FOCUS_THRESHOLD)].head(12)
    lines = [
        "# 1H_M30_4H 4H高价bias机会池测试",
        "",
        "日期：2026-07-25",
        "",
        "## 口径",
        "",
        "- 机会池先保留样本，不再设置 6% 上限。",
        "- 做空：`H1roll4最高价 vs H4 SMA55 >= bias55阈值`，且只接 M30 空信号。",
        "- 做多：`H1roll4最高价 vs H4 SMA55 <= -bias55阈值`，且只接 M30 多信号。",
        "- 第一层默认观察阈值：`bias55 >= 2.0%` 或 `bias55 <= -2.0%`。",
        "- 组合测试：`bias55` 与 `bias13` 使用不同阈值，二者同时满足才进入机会池。",
        "- 止损：1H 结构止损候选。",
        "- 收益：`pnl_points * 100 * 0.01 lot`，未扣点差、滑点、手续费。",
        "",
        "## bias55=2.0% 机会池",
        "",
        markdown_table(base_focus[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## bias55 阈值扫描 Top",
        "",
        markdown_table(base_scan.head(15)[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## bias55=2.0 后续过滤 Top",
        "",
        markdown_table(second_filters.head(20)[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## bias55 + bias13 不同阈值组合 Top",
        "",
        markdown_table(combo_scan.head(20)[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## 输出文件",
        "",
        "- `h4_bias_opportunity_pool_trades.csv`",
        "- `h4_bias55_pool_threshold_scan.csv`",
        "- `h4_bias55_pool_second_filter_summary.csv`",
        "- `h4_bias55_bias13_combo_scan.csv`",
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = "\n".join(lines) + "\n"
    (OUT_DIR / "h4_bias_opportunity_pool_report.md").write_text(report, encoding="utf-8")
    (ROOT / "1H_4H高价bias机会池测试记录.md").write_text(report, encoding="utf-8")


def main() -> None:
    _, m30, h1, contexts = load_frames()
    h4 = contexts["4H"]
    plans = build_signal_plans(m30)
    replay_frames = []
    base_rows = []
    second_rows = []
    combo_rows = []

    for stop_variant in STOP_VARIANTS:
        replay = replay_with_stop_source(plans, m30, h1, contexts, stop_variant, 100.0)
        replay = pd.concat([replay.reset_index(drop=True), high_bias_features(replay["signal_time"], h1, h4)], axis=1)
        replay_frames.append(replay)

        for threshold in BIAS55_THRESHOLDS:
            mask = threshold_mask(replay, "h1roll4_high_bias55_h4sma_pct", threshold)
            base_rows.append(
                summarize(
                    replay.loc[mask].copy(),
                    stop_variant=stop_variant,
                    category="bias55_pool",
                    name=f"bias55_abs_ge_{threshold:.1f}",
                    desc="bias55无上限机会池",
                    threshold55=threshold,
                )
            )

        focus_base = replay.loc[threshold_mask(replay, "h1roll4_high_bias55_h4sma_pct", BIAS55_FOCUS_THRESHOLD)].copy()
        for filter_name, desc in SECOND_FILTERS:
            scoped = focus_base.loc[second_filter_mask(focus_base, filter_name)].copy()
            second_rows.append(
                summarize(
                    scoped,
                    stop_variant=stop_variant,
                    category="bias55_2_second_filter",
                    name=filter_name,
                    desc=desc,
                    threshold55=BIAS55_FOCUS_THRESHOLD,
                )
            )

        for threshold55 in BIAS55_COMBO_THRESHOLDS:
            for threshold13 in BIAS13_THRESHOLDS:
                mask = combo_mask(replay, threshold55, threshold13)
                combo_rows.append(
                    summarize(
                        replay.loc[mask].copy(),
                        stop_variant=stop_variant,
                        category="bias55_bias13_combo",
                        name=f"bias55_{threshold55:.1f}_bias13_{threshold13:.1f}",
                        desc="bias55+bias13无上限机会池",
                        threshold55=threshold55,
                        threshold13=threshold13,
                    )
                )

    all_replay = pd.concat(replay_frames, ignore_index=True)
    base_scan = score(pd.DataFrame(base_rows))
    second_filters = score(pd.DataFrame(second_rows))
    combo_scan = score(pd.DataFrame(combo_rows))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_replay.to_csv(OUT_DIR / "h4_bias_opportunity_pool_trades.csv", index=False, encoding="utf-8-sig")
    base_scan.to_csv(OUT_DIR / "h4_bias55_pool_threshold_scan.csv", index=False, encoding="utf-8-sig")
    second_filters.to_csv(OUT_DIR / "h4_bias55_pool_second_filter_summary.csv", index=False, encoding="utf-8-sig")
    combo_scan.to_csv(OUT_DIR / "h4_bias55_bias13_combo_scan.csv", index=False, encoding="utf-8-sig")
    write_report(base_scan, second_filters, combo_scan)

    print(f"{STRATEGY}: H4 high-bias opportunity pool")
    for _, row in base_scan.loc[base_scan["bias55_threshold"].eq(BIAS55_FOCUS_THRESHOLD)].head(3).iterrows():
        print(
            f"  bias55>=2 stop={row['stop_variant']} n={int(row['n'])} "
            f"L/S={int(row['long_n'])}/{int(row['short_n'])} pf={float(row['pf']):.4f} "
            f"test_pf={float(row['test_pf']):.4f} usd001={float(row['pnl_usd_001']):.2f}"
        )
    best_second = second_filters.iloc[0]
    print(
        f"best_second stop={best_second['stop_variant']} filter={best_second['name']} "
        f"n={int(best_second['n'])} pf={float(best_second['pf']):.4f} "
        f"test_pf={float(best_second['test_pf']):.4f} usd001={float(best_second['pnl_usd_001']):.2f}"
    )
    best_combo = combo_scan.iloc[0]
    print(
        f"best_combo stop={best_combo['stop_variant']} bias55={float(best_combo['bias55_threshold']):.1f} "
        f"bias13={float(best_combo['bias13_threshold']):.1f} n={int(best_combo['n'])} "
        f"pf={float(best_combo['pf']):.4f} test_pf={float(best_combo['test_pf']):.4f} "
        f"usd001={float(best_combo['pnl_usd_001']):.2f}"
    )


if __name__ == "__main__":
    main()
