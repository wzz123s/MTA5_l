# -*- coding: utf-8 -*-

"""Three separate strategies: 4H / 6H / 8H opportunity gate -> 2H execution.

Gate conditions on the higher TF (4H/6H/8H) at the 2H trigger time:
  C1: current segment continuous bars (|way|) >= n_min
  C2: current segment extreme bar (down seg: lowest price; up seg: highest
      price) has way_s_way / vol_way_s_way in direction >= thr
  C3: amplitude between current-segment SMMA13 extreme and the previous
      segment's SMMA13 extreme (|cur_ext - prev_ext| / close) within [lo, hi]
Trigger: 2H golden/death cross (optionally + confirm factor filter).
Stop: 2H structure (segment SMA13 extreme, 0.1-1.0%). Exit: 2H opposite cross.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)


import bisect
import sys
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from usoil_large_tf_golden_cross_20260815 import (  # noqa: E402
    golden_trades,
    load_tf,
    markdown_table,
    metrics,
)


OUT_DIR = Path(r"F:\use_code\MTA5_l\原油\原油金叉实验_20260815") / "4h6h8h_strategies"
N_MIN = [8, 12]
THR = 0.5
AMP_SPECS = [(0.5, 5.0), (1.0, 8.0), (0.5, 8.0)]


def gate_arrays(tf: pd.DataFrame):
    """Per-bar: dir_sign, seg_len, ext wsw/vwsw, SMMA13 current/prev extremes, amplitude."""
    direction = tf["方向_合并后"].values
    raw = tf["方向"].values
    way = pd.to_numeric(tf["way"], errors="coerce").to_numpy()
    wsw = pd.to_numeric(tf["way_s_way"], errors="coerce").to_numpy()
    vwsw = pd.to_numeric(tf["vol_way_s_way"], errors="coerce").to_numpy()
    low = pd.to_numeric(tf["low"], errors="coerce").to_numpy()
    high = pd.to_numeric(tf["high"], errors="coerce").to_numpy()
    sma13 = pd.to_numeric(tf["SMA_13"], errors="coerce").to_numpy()
    close = pd.to_numeric(tf["close"], errors="coerce").to_numpy()
    n = len(tf)
    cross_idx = [i for i in range(n) if raw[i] in ("good", "bad")]
    dir_sign = np.zeros(n, dtype=int)
    seg_len = np.zeros(n, dtype=int)
    ext_wsw = np.full(n, np.nan)
    ext_vwsw = np.full(n, np.nan)
    amp = np.full(n, np.nan)
    run_ext_idx = -1
    cur_sign = 0
    for i in range(n):
        d = direction[i]
        sign = 1 if d in ("good", "up") else (-1 if d in ("bad", "down") else 0)
        if sign != cur_sign:
            cur_sign = sign
            run_ext_idx = i
        else:
            if cur_sign == 1 and high[i] > high[run_ext_idx]:
                run_ext_idx = i
            elif cur_sign == -1 and low[i] < low[run_ext_idx]:
                run_ext_idx = i
        dir_sign[i] = cur_sign
        seg_len[i] = int(abs(way[i])) if np.isfinite(way[i]) else 0
        if run_ext_idx >= 0:
            ext_wsw[i] = wsw[run_ext_idx]
            ext_vwsw[i] = vwsw[run_ext_idx]
        # C3: current-segment SMMA13 extreme vs previous-segment SMMA13 extreme
        ci = bisect.bisect_right(cross_idx, i) - 1
        if ci >= 1 and cur_sign != 0:
            c1 = cross_idx[ci]
            c0 = cross_idx[ci - 1]
            cur_seg = sma13[c1:i + 1]
            prev_seg = sma13[c0:c1]
            cur_seg = cur_seg[np.isfinite(cur_seg)]
            prev_seg = prev_seg[np.isfinite(prev_seg)]
            if len(cur_seg) and len(prev_seg) and np.isfinite(close[i]) and close[i] != 0:
                if cur_sign == -1:
                    cur_ext = cur_seg.min()
                    prev_ext = prev_seg.max()
                else:
                    cur_ext = cur_seg.max()
                    prev_ext = prev_seg.min()
                amp[i] = abs(cur_ext - prev_ext) / close[i] * 100.0
    return dir_sign, seg_len, ext_wsw, ext_vwsw, amp


def apply_gate(trades: pd.DataFrame, gt, n_min: int, thr: float, amp_lo: float, amp_hi: float):
    times = pd.to_datetime(gt["bar_close_time"]).values.astype("datetime64[ns]")
    d, sl, w, v, amp = gate_arrays(gt)
    keep = []
    for _, row in trades.iterrows():
        t = pd.Timestamp(row["signal_time"]).to_datetime64()
        idx = bisect.bisect_right(times, t) - 1
        if idx < 0:
            keep.append(False)
            continue
        need_long = row["dir"] == "L"
        if need_long:
            ok = d[idx] == -1 and sl[idx] >= n_min and w[idx] >= thr and v[idx] >= thr  # BUG修复: way_s_way无符号
        else:
            ok = d[idx] == 1 and sl[idx] >= n_min and w[idx] >= thr and v[idx] >= thr
        if ok and np.isfinite(amp[idx]) and amp_lo <= amp[idx] <= amp_hi:
            keep.append(True)
        else:
            keep.append(False)
    return trades.loc[keep].copy().reset_index(drop=True)


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
    tf2 = load_tf("2H")
    gates = {"4H": load_tf("4H"), "6H": load_tf("6H"), "8H": load_tf("8H")}
    triggers = {"cross": golden_trades(tf2, "base", 0.0), "cross+confirm": golden_trades(tf2, "confirm", 0.5)}
    rows = []
    for tf_name, gt in gates.items():
        for n_min in N_MIN:
            for amp_lo, amp_hi in AMP_SPECS:
                for trig_name, trig in triggers.items():
                    trades = apply_gate(trig, gt, n_min, THR, amp_lo, amp_hi)
                    if trades.empty or len(trades) < 10:
                        continue
                    pnl = pd.to_numeric(trades["pnl_points"], errors="coerce")
                    ts = pd.to_datetime(trades["signal_time"])
                    m = metrics(pnl)
                    years = pd.DataFrame({"ts": ts, "pnl": pnl}).assign(y=ts.dt.year).groupby("y")["pnl"].sum()
                    rows.append({
                        "gate": tf_name, "n_min": n_min, "thr": THR,
                        "amp": f"{amp_lo:g}-{amp_hi:g}%", "trigger": trig_name, "n": m["n"],
                        "wr": m["wr"], "pf0": m["pf"], "ev0": m["ev"], "test_pf0": test_pf(pnl, ts),
                        "pos_years": f"{int((years > 0).sum())}/{len(years)}",
                    })
                    print(
                        f"  {tf_name} n>={n_min} amp={rows[-1]['amp']} {trig_name}: n={m['n']} "
                        f"pf0={m['pf']:.3f} ev0={m['ev']:+.2f} test0={rows[-1]['test_pf0']:.3f} "
                        f"years={rows[-1]['pos_years']}"
                    )
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "matrix.csv", index=False, encoding="utf-8-sig")
    cols = ["gate", "n_min", "thr", "amp", "trigger", "n", "wr", "pf0", "ev0", "test_pf0", "pos_years"]
    lines = [
        "# 三策略：4H/6H/8H 机会门（持续根数+极值bar way/vol_way+SMMA13极值幅度）→ 2H 执行",
        "",
        "> 2H 金叉触发（可选 +确认因子过滤），2H 结构止损 0.1-1.0%，单段退出。",
        "",
        markdown_table(df[cols], cols),
    ]
    # best candidate validation
    sc = df[df["n"] >= 25].copy()
    sc["_score"] = sc["pos_years"].str.split("/").str[0].astype(int) * 1000.0 + sc["test_pf0"] * 10.0 + sc["pf0"] * 5.0
    best = sc.sort_values(["_score", "test_pf0", "pf0"], ascending=[False, False, False]).iloc[0]
    bt = apply_gate(
        triggers[str(best["trigger"])],
        gates[str(best["gate"])],
        int(best["n_min"]), float(best["thr"]),
        float(best["amp"].split("-")[0]), float(best["amp"].split("-")[1].rstrip("%")),
    )
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
        f"## 推荐：{best['gate']}门 n>={int(best['n_min'])} amp={best['amp']} + 2H {best['trigger']}",
        "",
        "### Walk-forward",
        "",
        markdown_table(wf, [str(c) for c in wf.columns]),
        "",
        "### 分年",
        "",
        markdown_table(yearly, [str(c) for c in yearly.columns]),
    ]
    print(f"\n>> best: {best['gate']} n>={int(best['n_min'])} amp={best['amp']} + {best['trigger']}: "
          f"n={best['n']} pf0={best['pf0']:.3f} test0={best['test_pf0']:.3f}")
    print(wf.to_string(index=False))
    (OUT_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote: {OUT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
