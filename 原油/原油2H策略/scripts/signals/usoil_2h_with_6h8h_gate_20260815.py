# -*- coding: utf-8 -*-
"""2H execution with 6H/8H opportunity gate (user's multi-TF design).

Gate (6H or 8H): the latest closed high-TF bar is in a down/up segment with
  - continuous-bar count (|way|) >= N,
  - the segment extreme bar's way_s_way / vol_way_s_way in direction >= thr
    (down segment -> lowest-price bar; up segment -> highest-price bar).
Trigger: 2H golden/death cross. Stop: 2H structure (segment SMA13 extreme,
0.1-1.0%). Exit: 2H opposite cross next-open.
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
    PCT_LO,
    PCT_HI,
    golden_trades,
    load_tf,
    markdown_table,
    metrics,
)


OUT_DIR = Path(r"F:\use_code\MTA5_l\原油\原油金叉实验_20260815") / "2h_with_6h8h_gate"
N_MIN = [8, 12]
THRESHOLDS = [0.5, 0.7]


def tf_gate_arrays(tf: pd.DataFrame):
    """Return per-bar gate fields: dir_sign, seg_len, ext_wsw, ext_vwsw."""
    direction = tf["方向_合并后"].values
    way = pd.to_numeric(tf["way"], errors="coerce").to_numpy()
    wsw = pd.to_numeric(tf["way_s_way"], errors="coerce").to_numpy()
    vwsw = pd.to_numeric(tf["vol_way_s_way"], errors="coerce").to_numpy()
    low = pd.to_numeric(tf["low"], errors="coerce").to_numpy()
    high = pd.to_numeric(tf["high"], errors="coerce").to_numpy()
    n = len(tf)
    dir_sign = np.zeros(n, dtype=int)
    seg_len = np.zeros(n, dtype=int)
    ext_wsw = np.full(n, np.nan)
    ext_vwsw = np.full(n, np.nan)
    run_ext_idx = -1
    cur_sign = 0
    for i in range(n):
        d = direction[i]
        if d in ("good", "up"):
            sign = 1
        elif d in ("bad", "down"):
            sign = -1
        else:
            sign = 0
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
    return dir_sign, seg_len, ext_wsw, ext_vwsw


def gate_pass_at(tf, times, idx, dir_sign, seg_len, ext_wsw, ext_vwsw, n_min, thr, need_long):
    if idx < 0:
        return False
    if need_long:  # 2H BUY -> gate needs 6H/8H down segment (continuity down)
        if dir_sign[idx] != -1:
            return False
        return seg_len[idx] >= n_min and ext_wsw[idx] >= thr and ext_vwsw[idx] >= thr  # BUG修复: way_s_way无符号
    else:  # 2H SELL -> gate needs 6H/8H up segment
        if dir_sign[idx] != 1:
            return False
        return seg_len[idx] >= n_min and ext_wsw[idx] >= thr and ext_vwsw[idx] >= thr


def apply_gate(trades: pd.DataFrame, gt, n_min: float, thr: float):
    times = pd.to_datetime(gt["bar_close_time"]).values.astype("datetime64[ns]")
    d, sl, w, v = tf_gate_arrays(gt)
    keep = []
    for _, row in trades.iterrows():
        t = pd.Timestamp(row["signal_time"]).to_datetime64()
        idx = bisect.bisect_right(times, t) - 1
        need_long = row["dir"] == "L"
        if gate_pass_at(gt, times, idx, d, sl, w, v, n_min, thr, need_long):
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


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tf2 = load_tf("2H")
    g6 = load_tf("6H")
    g8 = load_tf("8H")
    base = golden_trades(tf2, "base", 0.0)      # 2H cross, 2H stop, 0.1-1.0%
    confirm = golden_trades(tf2, "confirm", 0.5)  # 2H cross + confirm (reference)
    rows = []
    for src_name, src_trades in [("cross", base), ("cross+confirm", confirm)]:
        for label, gt in [("6H", g6), ("8H", g8)]:
            for n_min in N_MIN:
                for thr in THRESHOLDS:
                    trades = apply_gate(src_trades, gt, n_min, thr)
                    if trades.empty or len(trades) < 10:
                        continue
                    pnl = pd.to_numeric(trades["pnl_points"], errors="coerce")
                    ts = pd.to_datetime(trades["signal_time"])
                    m = metrics(pnl)
                    years = pd.DataFrame({"ts": ts, "pnl": pnl}).assign(y=ts.dt.year).groupby("y")["pnl"].sum()
                    rows.append({
                        "gate": f"{src_name}+{label}", "n_min": n_min, "thr": thr, "n": m["n"],
                        "wr": m["wr"], "pf0": m["pf"], "ev0": m["ev"], "test_pf0": test_pf(pnl, ts),
                        "pos_years": f"{int((years > 0).sum())}/{len(years)}",
                    })
                    print(
                        f"  {src_name}+{label} n>={n_min} thr={thr}: n={m['n']} pf0={m['pf']:.3f} "
                        f"ev0={m['ev']:+.2f} test0={rows[-1]['test_pf0']:.3f} years={rows[-1]['pos_years']}"
                    )
    # reference rows
    for label, trades in [("base_2H", base), ("confirm_2H", confirm)]:
        pnl = pd.to_numeric(trades["pnl_points"], errors="coerce")
        ts = pd.to_datetime(trades["signal_time"])
        m = metrics(pnl)
        years = pd.DataFrame({"ts": ts, "pnl": pnl}).assign(y=ts.dt.year).groupby("y")["pnl"].sum()
        rows.append({
            "gate": label, "n_min": 0, "thr": 0, "n": m["n"], "wr": m["wr"],
            "pf0": m["pf"], "ev0": m["ev"], "test_pf0": test_pf(pnl, ts),
            "pos_years": f"{int((years > 0).sum())}/{len(years)}",
        })
        print(f"  {label}: n={m['n']} pf0={m['pf']:.3f} ev0={m['ev']:+.2f} test0={rows[-1]['test_pf0']:.3f}")
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "matrix.csv", index=False, encoding="utf-8-sig")
    cols = ["gate", "n_min", "thr", "n", "wr", "pf0", "ev0", "test_pf0", "pos_years"]
    lines = [
        "# 2H 交易 + 6H/8H 机会门（持续根数 + 极值bar way/vol_way）",
        "",
        "> 2H 金叉触发、2H 结构止损（0.1-1.0%）、单段退出；门=6H/8H 上一段持续≥N 根且",
        "极值bar（down段最低价/up段最高价）way/vol_way 同向≥thr。",
        "",
        markdown_table(df[cols], cols),
    ]
    (OUT_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote: {OUT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
