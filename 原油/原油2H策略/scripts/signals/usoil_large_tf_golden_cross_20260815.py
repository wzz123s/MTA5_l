# -*- coding: utf-8 -*-
"""USOIL golden cross on larger timeframes: 2H/4H/6H/8H.

Filters compared per TF:
  base   : no way filter (entry next-open, SL segment SMA13 extreme, single pos)
  prevseg: rule-file prev_seg_low/high (SMA13 extreme bar) way/vol_way >= thr
  confirm: post-cross 2-bar confirmation min(way/vol_way) >= thr  (1H best)
Stop spec 0.1-1.0% (tightened for oil), realistic costs.
8H is resampled from M30 (no raw 8H file).
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

from replay_raw_signals_with_stops import (  # noqa: E402
    add_indicators,
    manifest_file,
    read_json,
    standardize_mt5_csv,
)
from replay_1h_way_momentum_filter_scan import (  # noqa: E402
    add_way_grade,
    filter_short_segments,
    mark_direction,
)
from usoil_golden_cross_20260815 import markdown_table  # noqa: E402


OUT_DIR = Path(r"F:\use_code\MTA5_l\原油\原油金叉实验_20260815") / "large_tf"
THRESHOLDS = [0.5, 0.6]
PCT_LO, PCT_HI = 0.1, 1.0
COSTS = [0.0, 0.05, 0.10]


def load_tf(tf_name: str) -> pd.DataFrame:
    if tf_name == "2H":
        strategy_dir = Path(r"F:\use_code\MTA5_l\原油\USOIL_30m2H策略")
        manifest = read_json(strategy_dir / "data" / "raw" / "raw_source_manifest.json")
        frame = add_indicators(standardize_mt5_csv(manifest_file(manifest, "H2"), "2H", closed_time=True))
    elif tf_name == "4H":
        strategy_dir = Path(r"F:\use_code\MTA5_l\原油\USOIL_1H_M30_4H策略")
        manifest = read_json(strategy_dir / "data" / "raw" / "raw_source_manifest.json")
        frame = add_indicators(standardize_mt5_csv(manifest_file(manifest, "H4"), "4H", closed_time=True))
    elif tf_name == "6H":
        strategy_dir = Path(r"F:\use_code\MTA5_l\原油\USOIL_2H_M30_6H策略")
        manifest = read_json(strategy_dir / "data" / "raw" / "raw_source_manifest.json")
        frame = add_indicators(standardize_mt5_csv(manifest_file(manifest, "H6"), "6H", closed_time=True))
    elif tf_name == "8H":
        strategy_dir = Path(r"F:\use_code\MTA5_l\原油\USOIL_30m2H策略")
        manifest = read_json(strategy_dir / "data" / "raw" / "raw_source_manifest.json")
        m30 = standardize_mt5_csv(manifest_file(manifest, "M30"), "30M", closed_time=False)
        m30 = m30.set_index("date")
        frame = (
            m30.resample("8h", label="right", closed="right")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last",
                  "volume": "sum", "spread": "mean", "real_volume": "sum",
                  "symbol": "last", "time_diff": "last"})
            .dropna(subset=["open", "high", "low", "close"])
            .reset_index()
        )
        frame["bar_open_time"] = frame["date"] - pd.Timedelta(hours=8)
        frame["bar_close_time"] = frame["date"]
        frame = add_indicators(frame)
    else:
        raise KeyError(tf_name)
    frame["vol_ma_120"] = pd.to_numeric(frame["volume"], errors="coerce").fillna(0).rolling(120, min_periods=1).mean()
    return add_way_grade(filter_short_segments(mark_direction(frame), min_len=8)).reset_index(drop=True)


def prev_seg_extreme_sma13(tf: pd.DataFrame, k: int, i: int, is_long: bool):
    sma13 = pd.to_numeric(tf.iloc[k:i]["SMA_13"], errors="coerce").to_numpy()
    wsw = pd.to_numeric(tf.iloc[k:i]["way_s_way"], errors="coerce").to_numpy()
    vwsw = pd.to_numeric(tf.iloc[k:i]["vol_way_s_way"], errors="coerce").to_numpy()
    valid = np.where(~np.isnan(sma13))[0]
    if len(valid) == 0:
        return None
    ext_val, ext_idx = None, None
    for r in valid:
        v = sma13[r]
        if ext_val is None or (v < ext_val if is_long else v > ext_val):
            ext_val, ext_idx = v, r
    return ext_val, float(wsw[ext_idx]), float(vwsw[ext_idx])


def replay_trade(tf, entry_idx, side, entry, sl, nxt):
    exit_idx = nxt + 1
    if exit_idx >= len(tf):
        exit_idx = nxt
    for idx in range(entry_idx, exit_idx):
        b = tf.iloc[idx]
        open_px = float(b["open"]); h = float(b["high"]); lo = float(b["low"])
        if side == "L":
            if open_px <= sl:
                exit_px = open_px
            elif lo <= sl:
                exit_px = sl
            else:
                continue
            return exit_px - entry
        else:
            if open_px >= sl:
                exit_px = open_px
            elif h >= sl:
                exit_px = sl
            else:
                continue
            return entry - exit_px
    exit_bar = tf.iloc[exit_idx]
    exit_px = float(exit_bar["open"]) if exit_idx != nxt else float(exit_bar["close"])
    return (exit_px - entry) if side == "L" else (entry - exit_px)


def golden_trades(tf: pd.DataFrame, mode: str, thr: float, start_year: int = 2020):
    direction = tf["方向"].values
    cross_idx = [i for i in range(len(tf)) if direction[i] in ("good", "bad")]
    rows = []
    for pos, i in enumerate(cross_idx):
        side = "L" if direction[i] == "good" else "S"
        k = cross_idx[pos - 1] if pos > 0 else 0
        if i - k < 1:
            continue
        if mode == "base":
            ok = True
        elif mode == "prevseg":
            ext = prev_seg_extreme_sma13(tf, k, i, side == "L")
            if ext is None:
                continue
            _, wsw, vwsw = ext
            if side == "L":
                ok = wsw >= thr and vwsw >= thr  # BUG修复(2026-09-04): way_s_way无符号[0,1], 不能判负值
            else:
                ok = wsw >= thr and vwsw >= thr
        else:  # confirm
            j1, j2 = i + 1, i + 2
            if j2 + 1 >= len(tf):
                continue
            w1 = float(tf.iloc[j1]["way_s_way"]); w2 = float(tf.iloc[j2]["way_s_way"])
            v1 = float(tf.iloc[j1]["vol_way_s_way"]); v2 = float(tf.iloc[j2]["vol_way_s_way"])
            # BUG-1 修复(2026-09-04): way_s_way/vol_way_s_way 无符号 [0,1], 去掉 sign
            ok = min(w1, w2) >= thr and min(v1, v2) >= thr
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
        pct = abs(entry - sl) / entry * 100.0
        if not (PCT_LO <= pct <= PCT_HI):
            continue
        if (side == "L" and sl >= entry) or (side == "S" and sl <= entry):
            continue
        opp = "bad" if side == "L" else "good"
        nxt = next((x for x in cross_idx[pos + 1:] if direction[x] == opp), None)
        if nxt is None:
            continue
        rows.append(
            {
                "signal_time": tf.iloc[i]["bar_close_time"],
                "entry_time": tf.iloc[entry_idx]["bar_open_time"],
                "dir": side,
                "pnl_points": replay_trade(tf, entry_idx, side, entry, sl, nxt),
                "stop_pct": pct,
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
    rows = []
    st_cache = {}
    for tf_name in ["2H", "4H", "6H", "8H"]:
        tf = load_tf(tf_name)
        print(f"==== {tf_name} (bars={len(tf)}) ====")
        for mode, thrs in [("base", [0.0]), ("prevseg", THRESHOLDS), ("confirm", THRESHOLDS)]:
            for thr in thrs:
                trades = golden_trades(tf, mode, thr)
                if trades.empty or len(trades) < 15:
                    continue
                pnl = pd.to_numeric(trades["pnl_points"], errors="coerce")
                ts = pd.to_datetime(trades["signal_time"])
                base = metrics(pnl)
                years = pd.DataFrame({"ts": ts, "pnl": pnl}).assign(y=ts.dt.year).groupby("y")["pnl"].sum()
                row = {
                    "tf": tf_name, "mode": mode, "thr": thr, "n": base["n"], "wr": base["wr"],
                    "pf0": base["pf"], "ev0": base["ev"], "test_pf0": test_pf(pnl, ts),
                    "avg_stop_pct": float(trades["stop_pct"].mean()),
                    "pos_years": f"{int((years > 0).sum())}/{len(years)}",
                }
                for cost in COSTS[1:]:
                    row[f"pf_{cost:g}"] = metrics(pnl - cost)["pf"]
                    row[f"test_pf_{cost:g}"] = test_pf(pnl - cost, ts)
                rows.append(row)
                st_cache[(tf_name, mode, thr)] = trades
                print(
                    f"  {mode} thr={thr}: n={base['n']} pf0={base['pf']:.3f} ev0={base['ev']:+.2f} "
                    f"test0={row['test_pf0']:.3f} pf0.05={row['pf_0.05']:.3f} pf0.10={row['pf_0.1']:.3f} "
                    f"years={row['pos_years']}"
                )
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "matrix.csv", index=False, encoding="utf-8-sig")
    cols = ["tf", "mode", "thr", "n", "wr", "pf0", "ev0", "test_pf0",
            "pf_0.05", "pf_0.1", "test_pf_0.05", "avg_stop_pct", "pos_years"]
    lines = [
        "# 原油大周期金叉：2H/4H/6H/8H × base/prevseg/confirm",
        "",
        "> 止损 0.1-1.0%（收紧），单段退出，真实成本；8H 由 M30 重采样。",
        "",
        markdown_table(df[cols], cols),
    ]
    # best candidate validation
    sc = df[df["n"] >= 30].copy()
    sc["_score"] = sc["pos_years"].str.split("/").str[0].astype(int) * 1000.0 + sc["test_pf_0.05"] * 10.0 + sc["pf_0.05"] * 5.0
    best = sc.sort_values(["_score", "test_pf_0.05", "pf_0.05"], ascending=[False, False, False]).iloc[0]
    bt = st_cache[(str(best["tf"]), str(best["mode"]), float(best["thr"]))]
    pnl = pd.to_numeric(bt["pnl_points"], errors="coerce")
    ts = pd.to_datetime(bt["signal_time"])
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
    wf.to_csv(OUT_DIR / "best_walkforward.csv", index=False, encoding="utf-8-sig")
    yearly.to_csv(OUT_DIR / "best_yearly.csv", index=False, encoding="utf-8-sig")
    lines += [
        "",
        f"## 推荐：{best['tf']} / {best['mode']} / thr={best['thr']}",
        "",
        "### Walk-forward",
        "",
        markdown_table(wf, [str(c) for c in wf.columns]),
        "",
        "### 分年",
        "",
        markdown_table(yearly, [str(c) for c in yearly.columns]),
    ]
    print(f"\n>> best: {best['tf']} {best['mode']} thr={best['thr']} n={best['n']} "
          f"pf0={best['pf0']:.3f} test0={best['test_pf0']:.3f} pf0.10={best['pf_0.1']:.3f}")
    print(wf.to_string(index=False))
    (OUT_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote: {OUT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
