# -*- coding: utf-8 -*-

"""1H golden cross with previous-segment extreme-bar way/vol_way filter.

Semantics (user spec): the filter reads way_s_way / vol_way_s_way at the
extreme bar of the segment BEFORE the cross, reflecting whether the previous
move was continuous and free of heavy volume accumulation.

  - BUY  (golden cross): previous DOWN segment -> bar with min(low)
  - SELL (death cross):  previous UP segment ->
        V1: bar with min(low)   (literal user wording)
        V2: bar with max(high)  (symmetric extreme)

Filter: |way_s_way| >= thr AND |vol_way_s_way| >= thr in segment direction.
Entry: next bar open after the cross. SL: previous-segment SMA13 extreme,
stop spec 0.1-1.0% (validated sweet spot). Single-position exit.
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


OUT_DIR = Path(r"F:\use_code\MTA5_l\原油\原油金叉实验_20260815") / "prev_segment_filter"
THRESHOLDS = [0.5, 0.6, 0.7]
PCT_LO, PCT_HI = 0.1, 1.0
COSTS = [0.0, 0.02, 0.05, 0.10]


def cross_trades(tf: pd.DataFrame, thr: float, variant: str, start_year: int = 2020):
    direction = tf["方向"].values
    low = pd.to_numeric(tf["low"], errors="coerce").to_numpy()
    high = pd.to_numeric(tf["high"], errors="coerce").to_numpy()
    cross_idx = [i for i in range(len(tf)) if direction[i] in ("good", "bad")]
    rows = []
    for pos, i in enumerate(cross_idx):
        side = "L" if direction[i] == "good" else "S"
        k = cross_idx[pos - 1] if pos > 0 else 0
        if i - k < 1:
            continue
        seg_low = low[k:i]
        seg_high = high[k:i]
        if side == "L":
            valid = np.where(~np.isnan(seg_low))[0]
            if len(valid) == 0:
                continue
            idx_rel = valid[np.nanargmin(seg_low[valid])]
            ext_idx = k + idx_rel
        else:
            if variant == "V1":
                valid = np.where(~np.isnan(seg_low))[0]
                if len(valid) == 0:
                    continue
                idx_rel = valid[np.nanargmin(seg_low[valid])]
            else:
                valid = np.where(~np.isnan(seg_high))[0]
                if len(valid) == 0:
                    continue
                idx_rel = valid[np.nanargmax(seg_high[valid])]
            ext_idx = k + idx_rel
        if variant in ("V3", "V4"):
            seg_w = pd.to_numeric(tf.iloc[k:i]["way_s_way"], errors="coerce").abs().dropna()
            seg_v = pd.to_numeric(tf.iloc[k:i]["vol_way_s_way"], errors="coerce").abs().dropna()
            if seg_w.empty or seg_v.empty:
                continue
            if variant == "V3":
                wsw = float(seg_w.mean())
                vwsw = float(seg_v.mean())
            else:
                wsw = float(seg_w.min())
                vwsw = float(seg_v.min())
        else:
            wsw = float(tf.iloc[ext_idx]["way_s_way"])
            vwsw = float(tf.iloc[ext_idx]["vol_way_s_way"])
        if side == "L":
            ok = wsw >= thr and vwsw >= thr  # BUG修复(2026-09-04): way_s_way无符号[0,1], 不能判负值
        else:
            ok = wsw >= thr and vwsw >= thr
        if not ok:
            continue
        entry_idx = i + 1
        if entry_idx >= len(tf):
            continue
        if pd.to_datetime(tf.iloc[entry_idx]["bar_open_time"]).year < start_year:
            continue
        entry = float(tf.iloc[entry_idx]["open"])
        seg_sma = pd.to_numeric(tf.iloc[k:i]["SMA_13"], errors="coerce").dropna()
        if seg_sma.empty:
            continue
        sl = float(seg_sma.min()) if side == "L" else float(seg_sma.max())
        if not np.isfinite(sl):
            continue
        sd = abs(entry - sl)
        pct = sd / entry * 100.0
        if not (PCT_LO <= pct <= PCT_HI):
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
            open_px = float(bar["open"]); h = float(bar["high"]); lo = float(bar["low"])
            if side == "L":
                if open_px <= sl:
                    exit_px = open_px
                elif lo <= sl:
                    exit_px = sl
                else:
                    continue
                pnl = exit_px - entry
            else:
                if open_px >= sl:
                    exit_px = open_px
                elif h >= sl:
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


def range_pf(pnl: pd.Series, ts: pd.Series, y0: int, y1: int) -> float:
    df = pd.DataFrame({"ts": pd.to_datetime(ts), "pnl": pnl})
    vals = df.loc[(df["ts"].dt.year >= y0) & (df["ts"].dt.year <= y1), "pnl"]
    tw = vals[vals > 0]
    tl = vals[vals < 0]
    return float((tw.sum() / abs(tl.sum())) if abs(tl.sum()) > 0 else (999.0 if tw.sum() > 0 else 0.0))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tf = load_tf("1H")
    rows = []
    st_cache = {}
    print("==== 1H prev-segment extreme way filter ====")
    for variant in ["V1", "V2", "V3", "V4"]:
        for thr in (THRESHOLDS if variant in ("V1", "V2") else [0.5, 0.6]):
            trades = cross_trades(tf, thr, variant)
            if trades.empty:
                continue
            pnl = pd.to_numeric(trades["pnl_points"], errors="coerce")
            ts = pd.to_datetime(trades["signal_time"])
            base = metrics(pnl)
            years = pd.DataFrame({"ts": ts, "pnl": pnl}).assign(y=ts.dt.year).groupby("y")["pnl"].sum()
            row = {
                "variant": variant,
                "thr": thr,
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
            st_cache[(variant, thr)] = trades
            print(
                f"  {variant} thr={thr}: n={base['n']} pf0={base['pf']:.3f} ev0={base['ev']:+.2f} "
                f"test0={row['test_pf0']:.3f} pf0.05={row['pf_0.05']:.3f} pf0.10={row['pf_0.1']:.3f} "
                f"years={row['pos_years']}"
            )
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "matrix.csv", index=False, encoding="utf-8-sig")
    sc = df[df["n"] >= 30].copy()
    sc["_score"] = sc["pos_years"].str.split("/").str[0].astype(int) * 1000.0 + sc["test_pf_0.05"] * 10.0 + sc["pf_0.05"] * 5.0
    best = sc.sort_values(["_score", "test_pf_0.05", "pf_0.05"], ascending=[False, False, False]).iloc[0]
    bt = st_cache[(str(best["variant"]), float(best["thr"]))]
    pnl = pd.to_numeric(bt["pnl_points"], errors="coerce")
    ts = pd.to_datetime(bt["signal_time"])
    print(f"\n>> best: {best['variant']} thr={best['thr']} n={best['n']} "
          f"pf0={best['pf0']:.3f} test0={best['test_pf0']:.3f} pf0.05={best['pf_0.05']:.3f}")

    wf = pd.DataFrame(
        [
            {"train": "2020-2023", "test": "2024-2026",
             "train_pf": range_pf(pnl, ts, 2020, 2023),
             "test_pf": range_pf(pnl, ts, 2024, 2026), "test_n": int((ts.dt.year >= 2024).sum())},
            {"train": "2020-2022", "test": "2023-2026",
             "train_pf": range_pf(pnl, ts, 2020, 2022),
             "test_pf": range_pf(pnl, ts, 2023, 2026), "test_n": int((ts.dt.year >= 2023).sum())},
        ]
    )
    year_rows = []
    for y, g in pd.DataFrame({"ts": ts, "pnl": pnl}).assign(y=ts.dt.year).groupby("y"):
        m = metrics(g["pnl"])
        year_rows.append({"year": int(y), "n": m["n"], "pf": m["pf"], "ev": m["ev"], "pnl": m["pnl"]})
    yearly = pd.DataFrame(year_rows)
    wf.to_csv(OUT_DIR / "walkforward.csv", index=False, encoding="utf-8-sig")
    yearly.to_csv(OUT_DIR / "yearly.csv", index=False, encoding="utf-8-sig")

    lines = [
        "# 1H 金叉：上一段极值 bar 的 way/vol_way 过滤",
        "",
        "> 金叉(BUY)看上一段 down 段最低价 bar；死叉(SELL) V1=上一段 up 段最低价 bar（字面），V2=最高价 bar（对称）。",
        "> 语义：上一段走势连续（|way_s_way| 高）且没有筹码堆积（|vol_way_s_way| 高）。止损 0.1-1.0%，单段退出。",
        "",
        "## 矩阵",
        "",
        markdown_table(df[["variant", "thr", "n", "wr", "pf0", "ev0", "test_pf0",
                           "pf_0.02", "pf_0.05", "pf_0.1", "test_pf_0.05", "avg_stop_pct", "pos_years"]],
                       ["variant", "thr", "n", "wr", "pf0", "ev0", "test_pf0",
                        "pf_0.02", "pf_0.05", "pf_0.1", "test_pf_0.05", "avg_stop_pct", "pos_years"]),
        "",
        f"## 推荐：{best['variant']} / thr={best['thr']}",
        "",
        "### Walk-forward",
        "",
        markdown_table(wf, [str(c) for c in wf.columns]),
        "",
        "### 分年",
        "",
        markdown_table(yearly, [str(c) for c in yearly.columns]),
    ]
    (OUT_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote: {OUT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
