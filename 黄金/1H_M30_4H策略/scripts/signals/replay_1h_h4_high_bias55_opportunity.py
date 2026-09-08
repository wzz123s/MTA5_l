# -*- coding: utf-8 -*-
"""Test 1H_M30_4H opportunities using 4xH1 high-price bias55 bands."""
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

from replay_1h_bias55_h1_stop_optimization import (
    build_signal_plans,
    load_frames,
    replay_with_stop_source,
)
from replay_raw_signals_with_stops import (
    LOT_FOR_REPORT,
    markdown_table,
    metric,
    money,
    split_test,
    yearly_positive_count,
)


STRATEGY = "1H_M30_4H"
ROOT = Path(r"F:\use_code\MTA5_l")
OUT_DIR = ROOT / "黄金" / f"{STRATEGY}策略" / "data" / "validation" / "h4_high_bias55_opportunity"
STOP_VARIANTS = ["h1_last6_hilo", "h1_dir_segment_hilo", "h1_last3_hilo"]
LOWER_THRESHOLDS = [round(value / 10.0, 1) for value in range(20, 61, 2)]
UPPER_THRESHOLD = 6.0
MIN_SAMPLE = 30


def _h1_roll4_features(signal_times: pd.Series, h1: pd.DataFrame, h4: pd.DataFrame) -> pd.DataFrame:
    h1_times = pd.to_datetime(h1["date"]).values.astype("datetime64[ns]")
    h4_times = pd.to_datetime(h4["date"]).values.astype("datetime64[ns]")
    rows: list[dict] = []
    for signal_time in pd.to_datetime(signal_times):
        h1_idx = bisect.bisect_right(h1_times, signal_time.to_datetime64()) - 1
        if h1_idx < 0:
            rows.append(_empty_feature())
            continue

        window = h1.iloc[max(0, h1_idx - 3) : h1_idx + 1].copy()
        h1_sma = pd.to_numeric(window["SMA_55"], errors="coerce")
        high = pd.to_numeric(window["high"], errors="coerce")
        high_bias_h1 = np.where(h1_sma.notna() & h1_sma.ne(0), (high - h1_sma) / h1_sma * 100.0, np.nan)
        high_bias_h1 = pd.Series(high_bias_h1, index=window.index)

        h4_idx = bisect.bisect_right(h4_times, signal_time.to_datetime64()) - 1
        h4_sma55 = float(h4.iloc[h4_idx]["SMA_55"]) if h4_idx >= 0 and not pd.isna(h4.iloc[h4_idx]["SMA_55"]) else np.nan
        highest_high = float(high.max()) if high.notna().any() else np.nan
        h4_basis_bias = (highest_high - h4_sma55) / h4_sma55 * 100.0 if np.isfinite(h4_sma55) and h4_sma55 != 0 else np.nan

        max_bias_idx = high_bias_h1.idxmax() if high_bias_h1.notna().any() else None
        rows.append(
            {
                "h1roll4_high": highest_high,
                "h1roll4_high_time": window.loc[high.idxmax(), "date"] if high.notna().any() else pd.NaT,
                "h1roll4_high_bias55_h1sma_pct": float(high_bias_h1.max()) if high_bias_h1.notna().any() else np.nan,
                "h1roll4_high_bias55_h1sma_time": window.loc[max_bias_idx, "date"] if max_bias_idx is not None else pd.NaT,
                "h1roll4_high_bias55_h4sma_pct": h4_basis_bias,
                "h1roll4_h4_sma55": h4_sma55,
                "h1roll4_closed_h1_count": int(len(window)),
            }
        )
    return pd.DataFrame(rows)


def _empty_feature() -> dict:
    return {
        "h1roll4_high": np.nan,
        "h1roll4_high_time": pd.NaT,
        "h1roll4_high_bias55_h1sma_pct": np.nan,
        "h1roll4_high_bias55_h1sma_time": pd.NaT,
        "h1roll4_high_bias55_h4sma_pct": np.nan,
        "h1roll4_h4_sma55": np.nan,
        "h1roll4_closed_h1_count": 0,
    }


def add_high_bias_features(frame: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame) -> pd.DataFrame:
    features = _h1_roll4_features(frame["signal_time"], h1, h4)
    return pd.concat([frame.reset_index(drop=True), features.reset_index(drop=True)], axis=1)


def opportunity_mask(frame: pd.DataFrame, feature: str, lower: float, upper: float) -> pd.Series:
    values = pd.to_numeric(frame[feature], errors="coerce")
    side = frame["dir"].astype(str).str.upper()
    short_mask = side.eq("S") & values.ge(lower) & values.le(upper)
    long_mask = side.eq("L") & values.le(-lower) & values.ge(-upper)
    return short_mask | long_mask


def summarize(frame: pd.DataFrame, stop_variant: str, feature: str, lower: float, upper: float) -> dict:
    m = metric(frame["pnl_points"])
    test = split_test(frame, "pnl_points")
    pos_years, total_years = yearly_positive_count(frame, "pnl_points")
    side = frame["dir"].astype(str).str.upper() if len(frame) else pd.Series(dtype=str)
    return {
        "stop_variant": stop_variant,
        "feature": feature,
        "lower_pct": lower,
        "upper_pct": upper,
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


def score_summary(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["sample_ok"] = out["n"].astype(float).ge(MIN_SAMPLE)
    out["score"] = (
        out["sample_ok"].astype(int) * 1000.0
        + out["test_pf"].astype(float).clip(upper=50) * 20.0
        + out["pf"].astype(float).clip(upper=50) * 8.0
        + out["pnl_usd_001"].astype(float) * 0.01
        + out["positive_years"].astype(float) * 3.0
    )
    return out.sort_values(["score", "test_pf", "pf", "n"], ascending=[False, False, False, False]).reset_index(drop=True)


def write_report(summary: pd.DataFrame) -> None:
    cols = [
        "stop_variant",
        "feature",
        "lower_pct",
        "upper_pct",
        "n",
        "long_n",
        "short_n",
        "pf",
        "test_pf",
        "pnl_usd_001",
        "stop_hits",
        "stop_hit_rate_pct",
        "avg_stop_distance",
        "positive_years",
        "total_years",
        "sample_status",
    ]
    fixed = summary.loc[summary["lower_pct"].eq(2.0)].copy().head(12)
    top = summary.head(15)
    lines = [
        "# 1H_M30_4H 4H高价bias55反向机会测试",
        "",
        "日期：2026-07-25",
        "",
        "## 口径",
        "",
        "- 将 4H 拆成最近 4 根已收盘 H1 K 线。",
        "- 取这 4 根 H1 的最高价，计算 high-price bias55。",
        "- 做空机会：bias55 在 `+2%` 到 `+6%` 之间，只接 M30 空信号。",
        "- 做多机会：bias55 在 `-6%` 到 `-2%` 之间，只接 M30 多信号。",
        "- 入场：M30 SMA5/SMA13 交叉收盘确认，下一根 M30 开盘。",
        "- 止损：仍使用 1H 结构止损候选。",
        "- 收益：`pnl_points * 100 * 0.01 lot`，未扣点差、滑点、手续费。",
        "",
        "## 固定 2%-6% 区间",
        "",
        markdown_table(fixed[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## Lower 阈值扫描 Top",
        "",
        markdown_table(top[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## 输出文件",
        "",
        "- `h4_high_bias55_opportunity_trades.csv`",
        "- `h4_high_bias55_opportunity_summary.csv`",
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = "\n".join(lines) + "\n"
    (OUT_DIR / "h4_high_bias55_opportunity_report.md").write_text(report, encoding="utf-8")
    (ROOT / "1H_4H高价bias55机会测试记录.md").write_text(report, encoding="utf-8")


def main() -> None:
    manifest, m30, h1, contexts = load_frames()
    h4 = contexts["4H"]
    plans = build_signal_plans(m30)

    replay_frames = []
    rows = []
    for stop_variant in STOP_VARIANTS:
        replay = replay_with_stop_source(plans, m30, h1, contexts, stop_variant, 100.0)
        replay = add_high_bias_features(replay, h1, h4)
        replay_frames.append(replay)
        for feature in ["h1roll4_high_bias55_h1sma_pct", "h1roll4_high_bias55_h4sma_pct"]:
            for lower in LOWER_THRESHOLDS:
                scoped = replay.loc[opportunity_mask(replay, feature, lower, UPPER_THRESHOLD)].copy()
                rows.append(summarize(scoped, stop_variant, feature, lower, UPPER_THRESHOLD))

    all_replay = pd.concat(replay_frames, ignore_index=True)
    summary = score_summary(pd.DataFrame(rows))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_replay.to_csv(OUT_DIR / "h4_high_bias55_opportunity_trades.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT_DIR / "h4_high_bias55_opportunity_summary.csv", index=False, encoding="utf-8-sig")
    write_report(summary)

    print(f"{STRATEGY}: 4xH1 high-price bias55 opportunity")
    for _, row in summary.loc[summary["lower_pct"].eq(2.0)].head(6).iterrows():
        print(
            f"  fixed stop={row['stop_variant']} feature={row['feature']} "
            f"n={int(row['n'])} L/S={int(row['long_n'])}/{int(row['short_n'])} "
            f"pf={float(row['pf']):.4f} test_pf={float(row['test_pf']):.4f} "
            f"usd001={float(row['pnl_usd_001']):.2f}"
        )
    best = summary.iloc[0]
    print(
        f"best stop={best['stop_variant']} feature={best['feature']} "
        f"band={float(best['lower_pct']):.1f}-{float(best['upper_pct']):.1f}% "
        f"n={int(best['n'])} pf={float(best['pf']):.4f} "
        f"test_pf={float(best['test_pf']):.4f} usd001={float(best['pnl_usd_001']):.2f}"
    )


if __name__ == "__main__":
    main()
