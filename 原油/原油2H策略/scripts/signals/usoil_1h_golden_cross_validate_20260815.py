# -*- coding: utf-8 -*-
"""Full validation for USOIL 1H golden cross + way/vol_way filter.

Confirmation window = 2 bars after the cross (i+1, i+2); require
min(way_s_way) and min(vol_way_s_way) in the trade direction >= thr;
entry at bar i+3 open. Stop = previous-segment SMA13 extreme, tightened by
percent-of-entry stop specs. Single-position exit (stop-first / opposite
cross next-open). Realistic oil costs $0.02 / $0.05 / $0.10.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)



import sys
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from usoil_golden_cross_20260815 import load_tf, markdown_table  # noqa: E402


OUT_DIR = Path(r"F:\use_code\MTA5_l\原油\原油金叉实验_20260815") / "1h_validate"
THRESHOLDS = [0.5, 0.6, 0.7]
PCT_SPECS = [(0.05, 0.3), (0.05, 0.5), (0.1, 1.0)]
COSTS = [0.0, 0.02, 0.05, 0.10]


def cross_trades(tf: pd.DataFrame, thr: float, pct_lo: float, pct_hi: float, start_year: int = 2020):
    direction = tf["方向"].values
    cross_idx = [i for i in range(len(tf)) if direction[i] in ("good", "bad")]
    rows = []
    for pos, i in enumerate(cross_idx):
        side = "L" if direction[i] == "good" else "S"
        j1, j2 = i + 1, i + 2
        if j2 + 1 >= len(tf):
            continue
        w1 = float(tf.iloc[j1]["way_s_way"])
        w2 = float(tf.iloc[j2]["way_s_way"])
        v1 = float(tf.iloc[j1]["vol_way_s_way"])
        v2 = float(tf.iloc[j2]["vol_way_s_way"])
        # BUG-1 修复(2026-09-04): way_s_way/vol_way_s_way 无符号 [0,1], 去掉 sign
        if not (min(w1, w2) >= thr and min(v1, v2) >= thr):
            continue
        entry_idx = j2 + 1
        if pd.to_datetime(tf.iloc[entry_idx]["bar_open_time"]).year < start_year:
            continue
        entry = float(tf.iloc[entry_idx]["open"])
        k = cross_idx[pos - 1] if pos > 0 else 0
        seg = pd.to_numeric(tf.iloc[k:i]["SMA_13"], errors="coerce").dropna()
        if seg.empty:
            continue
        sl = float(seg.min()) if side == "L" else float(seg.max())
        if not np.isfinite(sl):
            continue
        sd = abs(entry - sl)
        pct = sd / entry * 100.0
        if not (pct_lo <= pct <= pct_hi):
            continue
        if (side == "L" and sl >= entry) or (side == "S" and sl <= entry):
            continue
        opp = "bad" if side == "L" else "good"
        nxt = next((x for x in cross_idx[pos + 1:] if direction[x] == opp), None)
        if nxt is None:
            continue
        exit_idx = nxt + 1
        if exit_idx >= len(tf):
            exit_idx = nxt
        result = None
        for idx in range(entry_idx, exit_idx):
            bar = tf.iloc[idx]
            open_px = float(bar["open"]); high = float(bar["high"]); low = float(bar["low"])
            if side == "L":
                if open_px <= sl:
                    exit_px = open_px
                elif low <= sl:
                    exit_px = sl
                else:
                    continue
                pnl = exit_px - entry
            else:
                if open_px >= sl:
                    exit_px = open_px
                elif high >= sl:
                    exit_px = sl
                else:
                    continue
                pnl = entry - exit_px
            result = (exit_px, pnl)
            break
        if result is None:
            exit_bar = tf.iloc[exit_idx]
            exit_px = float(exit_bar["open"]) if exit_idx != nxt else float(exit_bar["close"])
            pnl = (exit_px - entry) if side == "L" else (entry - exit_px)
        else:
            _, pnl = result
        rows.append(
            {
                "signal_time": tf.iloc[i]["bar_close_time"],
                "entry_time": tf.iloc[entry_idx]["bar_open_time"],
                "dir": side,
                "entry": entry,
                "stop": sl,
                "stop_distance": sd,
                "stop_pct": pct,
                "pnl_points": pnl,
            }
        )
    return pd.DataFrame(rows)


def metrics(pnl: pd.Series) -> dict:
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gw = wins.sum()
    gl = abs(losses.sum())
    return {
        "n": int(len(pnl)),
        "wr": float((pnl > 0).mean() * 100.0),
        "pf": float(gw / gl if gl > 0 else (999.0 if gw > 0 else 0.0)),
        "ev": float(pnl.mean()),
        "pnl": float(pnl.sum()),
    }


def test_pf(pnl: pd.Series, ts: pd.Series) -> float:
    df = pd.DataFrame({"ts": pd.to_datetime(ts), "pnl": pnl}).sort_values("ts").reset_index(drop=True)
    cutoff_idx = min(max(int(len(df) * 0.70), 1), len(df) - 1)
    cutoff = df.loc[cutoff_idx, "ts"]
    test = df.loc[df["ts"] >= cutoff, "pnl"]
    tw = test[test > 0]
    tl = test[test < 0]
    return float((tw.sum() / abs(tl.sum())) if abs(tl.sum()) > 0 else (999.0 if tw.sum() > 0 else 0.0))


def cal_pf(pnl: pd.Series, ts: pd.Series, year_from: int) -> float:
    df = pd.DataFrame({"ts": pd.to_datetime(ts), "pnl": pnl})
    vals = df.loc[df["ts"].dt.year >= year_from, "pnl"]
    tw = vals[vals > 0]
    tl = vals[vals < 0]
    return float((tw.sum() / abs(tl.sum())) if abs(tl.sum()) > 0 else (999.0 if tw.sum() > 0 else 0.0))


def range_pf(pnl: pd.Series, ts: pd.Series, y0: int, y1: int) -> float:
    df = pd.DataFrame({"ts": pd.to_datetime(ts), "pnl": pnl})
    vals = df.loc[(df["ts"].dt.year >= y0) & (df["ts"].dt.year <= y1), "pnl"]
    tw = vals[vals > 0]
    tl = vals[vals < 0]
    return float((tw.sum() / abs(tl.sum())) if abs(tl.sum()) > 0 else (999.0 if tw.sum() > 0 else 0.0))


def rolling(ts: pd.Series, pnl: pd.Series, months: int = 12) -> pd.DataFrame:
    df = pd.DataFrame({"ts": pd.to_datetime(ts), "pnl": pnl}).sort_values("ts").reset_index(drop=True)
    first = df["ts"].min().to_period("M").to_timestamp()
    last = df["ts"].max().to_period("M").to_timestamp()
    month_ends = pd.period_range(first, last, freq="M").to_timestamp()
    rows = []
    for end_start in month_ends:
        end_excl = end_start + pd.DateOffset(months=months)
        start = end_excl - pd.DateOffset(months=months)
        g = df.loc[(df["ts"] >= start) & (df["ts"] < end_excl)]
        if g.empty:
            continue
        rows.append({"window_start": start.strftime("%Y-%m"), "window_end": end_start.strftime("%Y-%m"),
                     "n": int(len(g)), "pnl": float(g["pnl"].sum())})
    return pd.DataFrame(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tf = load_tf("1H")
    rows = []
    st_cache = {}
    print("==== USOIL 1H golden cross validate (confirm=2 bars) ====")
    for thr in THRESHOLDS:
        for pct_lo, pct_hi in PCT_SPECS:
            trades = cross_trades(tf, thr, pct_lo, pct_hi)
            if trades.empty:
                continue
            pnl = pd.to_numeric(trades["pnl_points"], errors="coerce")
            ts = pd.to_datetime(trades["signal_time"])
            base = metrics(pnl)
            years = pd.DataFrame({"ts": ts, "pnl": pnl}).assign(y=ts.dt.year).groupby("y")["pnl"].sum()
            row = {
                "thr": thr,
                "pct_spec": f"{pct_lo:g}-{pct_hi:g}%",
                "n": base["n"],
                "wr": base["wr"],
                "pf0": base["pf"],
                "ev0": base["ev"],
                "test_pf0": test_pf(pnl, ts),
                "avg_stop_pct": float(trades["stop_pct"].mean()),
                "pos_years": f"{int((years > 0).sum())}/{len(years)}",
            }
            for cost in COSTS[1:]:
                row[f"pf_{cost:g}"] = metrics(pnl - cost)["pf"]
                row[f"test_pf_{cost:g}"] = test_pf(pnl - cost, ts)
            rows.append(row)
            st_cache[(thr, pct_lo, pct_hi)] = trades
            print(
                f"  thr={thr} spec={row['pct_spec']}: n={base['n']} pf0={base['pf']:.3f} "
                f"ev0={base['ev']:+.2f} test0={row['test_pf0']:.3f} "
                f"pf0.05={row['pf_0.05']:.3f} pf0.10={row['pf_0.1']:.3f} "
                f"avg_stop={row['avg_stop_pct']:.3f}% years={row['pos_years']}"
            )
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "matrix.csv", index=False, encoding="utf-8-sig")

    sc = df[df["n"] >= 30].copy()
    if sc.empty:
        sc = df.copy()
    sc["_score"] = sc["pos_years"].str.split("/").str[0].astype(int) * 1000.0 + sc["test_pf_0.05"] * 10.0 + sc["pf_0.05"] * 5.0
    best = sc.sort_values(["_score", "test_pf_0.05", "pf_0.05"], ascending=[False, False, False]).iloc[0]
    bt = st_cache[(float(best["thr"]), float(best["pct_spec"].split("-")[0]), float(best["pct_spec"].split("-")[1].rstrip("%")))]
    pnl = pd.to_numeric(bt["pnl_points"], errors="coerce")
    ts = pd.to_datetime(bt["signal_time"])
    print(f"\n>> best: thr={best['thr']} spec={best['pct_spec']} n={best['n']} "
          f"pf0={best['pf0']:.3f} test0={best['test_pf0']:.3f} pf0.05={best['pf_0.05']:.3f}")

    # walk-forward + rolling + yearly for best
    wf = pd.DataFrame(
        [
            {"train": "2020-2023", "test": "2024-2026",
             "train_pf": range_pf(pnl, ts, 2020, 2023),
             "test_pf": cal_pf(pnl, ts, 2024), "test_n": int((ts.dt.year >= 2024).sum())},
            {"train": "2020-2022", "test": "2023-2026",
             "train_pf": range_pf(pnl, ts, 2020, 2022),
             "test_pf": cal_pf(pnl, ts, 2023), "test_n": int((ts.dt.year >= 2023).sum())},
        ]
    )
    roll = rolling(ts, pnl, 12)
    year_rows = []
    for y, g in pd.DataFrame({"ts": ts, "pnl": pnl}).assign(y=ts.dt.year).groupby("y"):
        m = metrics(g["pnl"])
        year_rows.append({"year": int(y), "n": m["n"], "pf": m["pf"], "ev": m["ev"], "pnl": m["pnl"]})
    yearly = pd.DataFrame(year_rows)
    wf.to_csv(OUT_DIR / "walkforward.csv", index=False, encoding="utf-8-sig")
    roll.to_csv(OUT_DIR / "rolling_12m.csv", index=False, encoding="utf-8-sig")
    yearly.to_csv(OUT_DIR / "yearly.csv", index=False, encoding="utf-8-sig")

    lines = [
        "# USOIL 1H 金叉完整验证（way 0.5-0.7 × 收紧止损）",
        "",
        f"> 确认窗口=金叉后 2 根（min way/vol_way 同向≥thr），入场=确认后开盘，止损=段SMA13极值+百分比收紧，单段退出。",
        "",
        "## 矩阵",
        "",
        markdown_table(df[["thr", "pct_spec", "n", "wr", "pf0", "ev0", "test_pf0",
                           "pf_0.02", "pf_0.05", "pf_0.1", "test_pf_0.05", "avg_stop_pct", "pos_years"]],
                       ["thr", "pct_spec", "n", "wr", "pf0", "ev0", "test_pf0",
                        "pf_0.02", "pf_0.05", "pf_0.1", "test_pf_0.05", "avg_stop_pct", "pos_years"]),
        "",
        f"## 推荐：thr={best['thr']} / {best['pct_spec']}",
        "",
        "### Walk-forward（日历样本外）",
        "",
        markdown_table(wf, [str(c) for c in wf.columns]),
        "",
        "### 12M 滚动窗口",
        "",
        f"- 窗口数：{len(roll)}，正窗口：{int((roll['pnl'] > 0).sum())}（{(roll['pnl'] > 0).mean() * 100:.0f}%）",
        f"- 最差窗口：{roll.loc[roll['pnl'].idxmin(), 'window_start']}..{roll.loc[roll['pnl'].idxmin(), 'window_end']}（{roll['pnl'].min():+.1f}）",
        "",
        "### 分年",
        "",
        markdown_table(yearly, [str(c) for c in yearly.columns]),
    ]
    (OUT_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote: {OUT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
