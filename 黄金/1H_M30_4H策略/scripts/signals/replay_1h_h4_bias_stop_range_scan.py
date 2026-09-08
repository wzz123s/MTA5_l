# -*- coding: utf-8 -*-
"""Scan H1 stop-distance ranges after the H4 high-bias opportunity pool."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)



from pathlib import Path

import numpy as np
import pandas as pd

from replay_raw_signals_with_stops import LOT_FOR_REPORT, markdown_table, metric, split_test, yearly_positive_count, trade_sign


STRATEGY = "1H_M30_4H"
ROOT = Path(r"F:\use_code\MTA5_l")
IN_PATH = ROOT / "黄金" / f"{STRATEGY}策略" / "data" / "validation" / "h4_bias_opportunity_pool" / "h4_bias_opportunity_pool_trades.csv"
OUT_DIR = ROOT / "黄金" / f"{STRATEGY}策略" / "data" / "validation" / "h4_bias_stop_range"
BIAS55_THRESHOLD = 2.0
STOP_VARIANTS = ["h1_last3_hilo", "h1_last6_hilo", "h1_dir_segment_hilo"]
STOP_LOS = [0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0]
STOP_HIS = [8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 28.0, 32.0, 40.0]
MIN_SAMPLE = 50


THIRD_FILTERS = [
    ("none", "仅StopSpec"),
    ("1h_bias5_13_pos", "1H bias5&bias13 同向"),
    ("1h_bias13_pos", "1H bias13 同向"),
    ("1h_close_side", "1H close_side 同向"),
    ("1h_bias5_pos", "1H bias5 同向"),
    ("1h_dir_against", "1H方向反向"),
    ("1h_dir_align", "1H方向同向"),
    ("buy_only", "只做多"),
    ("sell_only", "只做空"),
]


def read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def opportunity_mask(frame: pd.DataFrame) -> pd.Series:
    bias = pd.to_numeric(frame["h1roll4_high_bias55_h4sma_pct"], errors="coerce")
    side = frame["dir"].astype(str).str.upper()
    return (side.eq("S") & bias.ge(BIAS55_THRESHOLD)) | (side.eq("L") & bias.le(-BIAS55_THRESHOLD))


def third_filter_mask(frame: pd.DataFrame, name: str) -> pd.Series:
    if name == "none":
        return pd.Series(True, index=frame.index)
    side = frame["dir"].astype(str).str.upper()
    sign = side.map(lambda value: trade_sign(value)).astype(int)
    if name == "1h_bias5_13_pos":
        return pd.to_numeric(frame["1h_bias5_signed_pct"], errors="coerce").gt(0) & pd.to_numeric(
            frame["1h_bias13_signed_pct"], errors="coerce"
        ).gt(0)
    if name == "1h_bias13_pos":
        return pd.to_numeric(frame["1h_bias13_signed_pct"], errors="coerce").gt(0)
    if name == "1h_close_side":
        return pd.to_numeric(frame["1h_close_side"], errors="coerce").fillna(0).astype(int).eq(sign)
    if name == "1h_bias5_pos":
        return pd.to_numeric(frame["1h_bias5_signed_pct"], errors="coerce").gt(0)
    if name == "1h_dir_against":
        return pd.to_numeric(frame["1h_dir"], errors="coerce").fillna(0).astype(int).eq(-sign)
    if name == "1h_dir_align":
        return pd.to_numeric(frame["1h_dir"], errors="coerce").fillna(0).astype(int).eq(sign)
    if name == "buy_only":
        return side.eq("L")
    if name == "sell_only":
        return side.eq("S")
    raise KeyError(name)


def stop_range_label(lo: float, hi: float) -> str:
    return f"{lo:g}-{hi:g}pt"


def summarize(frame: pd.DataFrame, *, stop_variant: str, stop_lo: float, stop_hi: float, third_filter: str, third_desc: str) -> dict:
    m = metric(frame["pnl_points"])
    test = split_test(frame, "pnl_points")
    pos_years, total_years = yearly_positive_count(frame, "pnl_points")
    side = frame["dir"].astype(str).str.upper() if len(frame) else pd.Series(dtype=str)
    return {
        "stop_variant": stop_variant,
        "stop_range": stop_range_label(stop_lo, stop_hi),
        "stop_lo": stop_lo,
        "stop_hi": stop_hi,
        "third_filter": third_filter,
        "third_desc": third_desc,
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
        "median_stop_distance": float(pd.to_numeric(frame["stop_distance"], errors="coerce").median()) if len(frame) else 0.0,
        "positive_years": pos_years,
        "total_years": total_years,
        "sample_status": "ok" if m["n"] >= MIN_SAMPLE else "insufficient",
    }


def score(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["sample_ok"] = out["n"].astype(float).ge(MIN_SAMPLE)
    metric_score = (
        out["test_pf"].astype(float).clip(upper=10) * 22.0
        + out["pf"].astype(float).clip(upper=10) * 9.0
        + out["pnl_usd_001"].astype(float) * 0.012
        + out["positive_years"].astype(float) * 5.0
        + out["n"].astype(float).clip(upper=200) * 0.015
    )
    out["score"] = np.where(out["sample_ok"], 1000.0 + metric_score, -1000.0 + out["n"].astype(float))
    return out.sort_values(["score", "test_pf", "pf", "pnl_usd_001", "n"], ascending=[False, False, False, False, False]).reset_index(drop=True)


def scan() -> tuple[pd.DataFrame, pd.DataFrame]:
    trades = read_csv(IN_PATH)
    trades["signal_time"] = pd.to_datetime(trades["signal_time"])
    trades["stop_distance"] = pd.to_numeric(trades["stop_distance"], errors="coerce")
    trades["pnl_points"] = pd.to_numeric(trades["pnl_points"], errors="coerce")

    base_rows = []
    third_rows = []
    for stop_variant in STOP_VARIANTS:
        scoped_variant = trades.loc[trades["stop_variant"].astype(str).eq(stop_variant) & opportunity_mask(trades)].copy()
        for lo in STOP_LOS:
            for hi in STOP_HIS:
                if hi <= lo:
                    continue
                stop_mask = scoped_variant["stop_distance"].between(lo, hi, inclusive="both")
                stopped = scoped_variant.loc[stop_mask].copy()
                base_rows.append(
                    summarize(
                        stopped,
                        stop_variant=stop_variant,
                        stop_lo=lo,
                        stop_hi=hi,
                        third_filter="none",
                        third_desc="仅StopSpec",
                    )
                )
                for filter_name, filter_desc in THIRD_FILTERS:
                    if filter_name == "none":
                        continue
                    filtered = stopped.loc[third_filter_mask(stopped, filter_name)].copy()
                    third_rows.append(
                        summarize(
                            filtered,
                            stop_variant=stop_variant,
                            stop_lo=lo,
                            stop_hi=hi,
                            third_filter=filter_name,
                            third_desc=filter_desc,
                        )
                    )
    return score(pd.DataFrame(base_rows)), score(pd.DataFrame(third_rows))


def write_report(base_scan: pd.DataFrame, third_scan: pd.DataFrame) -> None:
    cols = [
        "stop_variant",
        "stop_range",
        "third_filter",
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
    main_filter = third_scan.loc[third_scan["third_filter"].eq("1h_bias5_13_pos")].copy()
    third_ok = third_scan.loc[third_scan["sample_status"].eq("ok")].copy()
    lines = [
        "# 1H_M30_4H 4H高价bias机会池 StopSpec 扫描",
        "",
        "日期：2026-07-25",
        "",
        "## 口径",
        "",
        "- 第一层：`H1roll4最高价 vs H4 SMA55 >= 2%` 做空，`<= -2%` 做多。",
        "- 第二层：只用 `stop_distance = abs(entry - 1H结构止损价)` 扫描止损范围。",
        "- 第三层：在 StopSpec 后再叠加 1H/M30 过滤；主看 `1H bias5&bias13 同向`。",
        "- 入场：M30 交叉收盘确认，下一根 M30 开盘。",
        "- 收益：`pnl_points * 100 * 0.01 lot`，未扣点差、滑点、手续费。",
        "",
        "## StopSpec 单独扫描 Top",
        "",
        markdown_table(base_scan.head(15)[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## StopSpec + 1H bias5&bias13 Top",
        "",
        markdown_table(main_filter.head(15)[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## StopSpec + 所有第三层过滤 Top",
        "",
        markdown_table(third_ok.head(20)[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## 输出文件",
        "",
        "- `h4_bias_stop_range_base_scan.csv`",
        "- `h4_bias_stop_range_third_filter_scan.csv`",
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = "\n".join(lines) + "\n"
    (OUT_DIR / "h4_bias_stop_range_report.md").write_text(report, encoding="utf-8")
    (ROOT / "1H_4H高价bias止损范围优化记录.md").write_text(report, encoding="utf-8")


def main() -> None:
    base_scan, third_scan = scan()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base_scan.to_csv(OUT_DIR / "h4_bias_stop_range_base_scan.csv", index=False, encoding="utf-8-sig")
    third_scan.to_csv(OUT_DIR / "h4_bias_stop_range_third_filter_scan.csv", index=False, encoding="utf-8-sig")
    write_report(base_scan, third_scan)

    print(f"{STRATEGY}: H4 high-bias opportunity StopSpec scan")
    for _, row in base_scan.head(5).iterrows():
        print(
            f"  base stop={row['stop_variant']} range={row['stop_range']} n={int(row['n'])} "
            f"pf={float(row['pf']):.4f} test_pf={float(row['test_pf']):.4f} "
            f"usd001={float(row['pnl_usd_001']):.2f}"
        )
    main_filter = third_scan.loc[third_scan["third_filter"].eq("1h_bias5_13_pos")]
    best = main_filter.iloc[0]
    print(
        f"best_main stop={best['stop_variant']} range={best['stop_range']} n={int(best['n'])} "
        f"pf={float(best['pf']):.4f} test_pf={float(best['test_pf']):.4f} "
        f"usd001={float(best['pnl_usd_001']):.2f}"
    )


if __name__ == "__main__":
    main()
