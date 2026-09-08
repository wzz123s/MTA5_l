# -*- coding: utf-8 -*-

"""USOIL reversal signals by previous-segment continuity + extreme-bar way.

User semantics (6H/8H): the opportunity is NOT a golden cross + confirm.
It is:
  - previous segment must have >= N consecutive bars (持续K线根数),
  - BUY (golden cross): the previous DOWN segment's LOWEST-PRICE bar must have
    way_s_way / vol_way_s_way in direction (<= -thr);
  - SELL (death cross): the previous UP segment's HIGHEST-PRICE bar must have
    way_s_way / vol_way_s_way (>= thr).
Entry: next bar open after the cross. Stop: previous segment price extreme
(BUY: seg low; SELL: seg high), filtered by 0.1-1.0% (and 0.05-2.0%).
Exit: opposite cross next-open (single position).
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

from usoil_large_tf_golden_cross_20260815 import (  # noqa: E402
    load_tf,
    markdown_table,
    metrics,
)


OUT_DIR = Path(r"F:\use_code\MTA5_l\原油\原油金叉实验_20260815") / "segment_len_extreme_way"
N_MIN = [8, 12, 16]
THRESHOLDS = [0.5, 0.7]
PCT_SPECS = [(0.1, 1.0), (0.05, 2.0)]


def signal_trades(tf: pd.DataFrame, n_min: int, thr: float, pct_lo: float, pct_hi: float, start_year: int = 2020):
    direction = tf["方向"].values
    low = pd.to_numeric(tf["low"], errors="coerce").to_numpy()
    high = pd.to_numeric(tf["high"], errors="coerce").to_numpy()
    cross_idx = [i for i in range(len(tf)) if direction[i] in ("good", "bad")]
    rows = []
    for pos, i in enumerate(cross_idx):
        side = "L" if direction[i] == "good" else "S"
        k = cross_idx[pos - 1] if pos > 0 else 0
        seg_len = i - k
        if seg_len < n_min:
            continue
        seg_low = low[k:i]
        seg_high = high[k:i]
        if side == "L":
            valid = np.where(~np.isnan(seg_low))[0]
            if len(valid) == 0:
                continue
            ext_rel = valid[np.nanargmin(seg_low[valid])]
            ext_price = seg_low[ext_rel]
        else:
            valid = np.where(~np.isnan(seg_high))[0]
            if len(valid) == 0:
                continue
            ext_rel = valid[np.nanargmax(seg_high[valid])]
            ext_price = seg_high[ext_rel]
        ext_idx = k + ext_rel
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
        sl = float(ext_price)
        pct = abs(entry - sl) / entry * 100.0
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
        for j in range(entry_idx, exit_idx):
            b = tf.iloc[j]
            open_px = float(b["open"]); h = float(b["high"]); lo = float(b["low"])
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
        rows.append({"signal_time": tf.iloc[i]["bar_close_time"], "dir": side,
                     "entry": entry, "stop": sl, "stop_pct": pct, "pnl_points": pnl})
    return pd.DataFrame(rows)


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
    rows = []
    for tf_name in ["2H", "4H", "6H", "8H"]:
        tf = load_tf(tf_name)
        print(f"==== {tf_name} ====")
        for n_min in N_MIN:
            for thr in THRESHOLDS:
                for pct_lo, pct_hi in PCT_SPECS:
                    trades = signal_trades(tf, n_min, thr, pct_lo, pct_hi)
                    if trades.empty:
                        print(f"  n>={n_min} thr={thr} spec={pct_lo:g}-{pct_hi:g}%: 0")
                        continue
                    if len(trades) < 10:
                        print(f"  n>={n_min} thr={thr} spec={pct_lo:g}-{pct_hi:g}%: n={len(trades)} (<10, skipped)")
                        continue
                    pnl = pd.to_numeric(trades["pnl_points"], errors="coerce")
                    ts = pd.to_datetime(trades["signal_time"])
                    m = metrics(pnl)
                    years = pd.DataFrame({"ts": ts, "pnl": pnl}).assign(y=ts.dt.year).groupby("y")["pnl"].sum()
                    rows.append({
                        "tf": tf_name, "n_min": n_min, "thr": thr,
                        "pct_spec": f"{pct_lo:g}-{pct_hi:g}%", "n": m["n"], "wr": m["wr"],
                        "pf0": m["pf"], "ev0": m["ev"], "test_pf0": test_pf(pnl, ts),
                        "avg_stop_pct": float(trades["stop_pct"].mean()),
                        "pos_years": f"{int((years > 0).sum())}/{len(years)}",
                    })
                    print(
                        f"  n>={n_min} thr={thr} spec={rows[-1]['pct_spec']}: n={m['n']} "
                        f"pf0={m['pf']:.3f} ev0={m['ev']:+.2f} test0={rows[-1]['test_pf0']:.3f} "
                        f"years={rows[-1]['pos_years']}"
                    )
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "matrix.csv", index=False, encoding="utf-8-sig")
    cols = ["tf", "n_min", "thr", "pct_spec", "n", "wr", "pf0", "ev0", "test_pf0",
            "avg_stop_pct", "pos_years"]
    lines = [
        "# 原油：上一段持续根数 + 极值 bar way/vol_way（用户语义）",
        "",
        "> 金叉看上一段 down 段最低价 bar、死叉看上一段 up 段最高价 bar 的 way/vol_way（同向≥thr），",
        "且上一段持续 K 线根数 ≥ n_min；止损=上一段价格极值（0.1-1.0% 或 0.05-2.0%）。",
        "",
        markdown_table(df[cols], cols),
    ]
    (OUT_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote: {OUT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
