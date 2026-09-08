# -*- coding: utf-8 -*-
"""Multi-TF signal -> 2H execution experiment for USOIL.

Signals: golden/death cross + 2-bar confirm filter (way/vol_way>=0.5) on the
source TF (1H/4H/6H/8H). Execution: next 2H bar open after the signal.
Stop modes:
  SL_2H : previous-segment SMA13 extreme on 2H at the entry bar
  SL_SRC: previous-segment SMA13 extreme on the source TF (signal-side stop)
Stop spec 0.1-1.0%, exit = 2H opposite cross next-open (stop-first).
Baseline: pure 2H signal -> 2H execution (40 trades, PF0 2.85).
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
    PCT_LO,
    PCT_HI,
    golden_trades,
    load_tf,
    markdown_table,
    metrics,
)


OUT_DIR = Path(r"F:\use_code\MTA5_l\原油\原油金叉实验_20260815") / "2h_execute_other_tf"
THR = 0.5
COSTS = [0.0, 0.05, 0.10]


def source_signals(src: str):
    if src == "1H":
        from usoil_golden_cross_20260815 import load_tf as load_tf_1h
        tf = load_tf_1h("1H")
    else:
        tf = load_tf(src)
    trades = golden_trades(tf, "confirm", THR)
    if trades.empty:
        return tf, trades
    out = trades[["signal_time", "dir"]].copy()
    # add source-TF prev-seg SMA13 extreme stop (SL_SRC)
    direction = tf["方向"].values
    cross_idx = [i for i in range(len(tf)) if direction[i] in ("good", "bad")]
    sls = []
    for _, row in out.iterrows():
        t = row["signal_time"]
        i = None
        for ci in range(len(cross_idx)):
            if tf.iloc[cross_idx[ci]]["bar_close_time"] == t:
                i = cross_idx[ci]
                break
        if i is None:
            sls.append(np.nan)
            continue
        pos = cross_idx.index(i)
        k = cross_idx[pos - 1] if pos > 0 else 0
        seg = pd.to_numeric(tf.iloc[k:i]["SMA_13"], errors="coerce").dropna()
        if seg.empty:
            sls.append(np.nan)
        else:
            sls.append(float(seg.min()) if row["dir"] == "L" else float(seg.max()))
    out["src_stop"] = sls
    return tf, out


def execute_on_2h(signals: pd.DataFrame, tf2: pd.DataFrame, stop_mode: str):
    open_times = pd.to_datetime(tf2["bar_open_time"]).values
    direction = tf2["方向"].values
    cross_idx = [i for i in range(len(tf2)) if direction[i] in ("good", "bad")]
    rows = []
    for _, s in signals.iterrows():
        t = pd.to_datetime(s["signal_time"]).to_datetime64()
        idxs = np.searchsorted(open_times, t, side="right")
        if idxs >= len(tf2):
            continue
        idx = int(idxs)
        side = str(s["dir"])
        entry = float(tf2.iloc[idx]["open"])
        # 2H prev-seg SMA13 extreme (last 2H cross strictly before idx)
        k = -1
        for ci in cross_idx:
            if ci < idx:
                k = ci
            else:
                break
        if k < 0:
            continue
        seg = pd.to_numeric(tf2.iloc[k:idx]["SMA_13"], errors="coerce").dropna()
        if seg.empty:
            continue
        if stop_mode == "SL_2H":
            sl = float(seg.min()) if side == "L" else float(seg.max())
        else:
            sl = float(s["src_stop"])
        if not np.isfinite(sl):
            continue
        pct = abs(entry - sl) / entry * 100.0
        if not (PCT_LO <= pct <= PCT_HI):
            continue
        if (side == "L" and sl >= entry) or (side == "S" and sl <= entry):
            continue
        opp = "bad" if side == "L" else "good"
        nxt = next((x for x in cross_idx if x > idx and direction[x] == opp), None)
        if nxt is None:
            continue
        exit_idx = nxt + 1
        if exit_idx >= len(tf2):
            exit_idx = nxt
        result = None
        for j in range(idx, exit_idx):
            b = tf2.iloc[j]
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
            exit_bar = tf2.iloc[exit_idx]
            exit_px = float(exit_bar["open"]) if exit_idx != nxt else float(exit_bar["close"])
            pnl = (exit_px - entry) if side == "L" else (entry - exit_px)
        else:
            _, pnl = result
        rows.append({"signal_time": t, "dir": side, "entry": entry, "stop": sl,
                     "stop_pct": pct, "pnl_points": pnl})
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
    tf2 = load_tf("2H")
    rows = []
    for src in ["1H", "4H", "6H", "8H"]:
        _, signals = source_signals(src)
        if signals.empty:
            print(f"{src}: no signals")
            continue
        for stop_mode in ["SL_2H", "SL_SRC"]:
            trades = execute_on_2h(signals, tf2, stop_mode)
            if trades.empty or len(trades) < 10:
                print(f"{src} {stop_mode}: too few ({len(trades)})")
                continue
            pnl = pd.to_numeric(trades["pnl_points"], errors="coerce")
            ts = pd.to_datetime(trades["signal_time"])
            m = metrics(pnl)
            years = pd.DataFrame({"ts": ts, "pnl": pnl}).assign(y=ts.dt.year).groupby("y")["pnl"].sum()
            row = {
                "src": src, "stop": stop_mode, "n": m["n"], "wr": m["wr"], "pf0": m["pf"],
                "ev0": m["ev"], "test_pf0": test_pf(pnl, ts),
                "avg_stop_pct": float(trades["stop_pct"].mean()),
                "pos_years": f"{int((years > 0).sum())}/{len(years)}",
            }
            for cost in COSTS[1:]:
                row[f"pf_{cost:g}"] = metrics(pnl - cost)["pf"]
            rows.append(row)
            print(
                f"  {src} {stop_mode}: n={m['n']} pf0={m['pf']:.3f} ev0={m['ev']:+.2f} "
                f"test0={row['test_pf0']:.3f} pf0.10={row['pf_0.1']:.3f} years={row['pos_years']}"
            )
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "matrix.csv", index=False, encoding="utf-8-sig")
    cols = ["src", "stop", "n", "wr", "pf0", "ev0", "test_pf0", "pf_0.05", "pf_0.1",
            "avg_stop_pct", "pos_years"]
    lines = [
        "# 多周期信号 → 2H 执行（USOIL 金叉 + 确认过滤 thr=0.5）",
        "",
        "> 基准：纯 2H 信号→2H 执行 = 40 笔 / PF0 2.85 / 样本外 5.97 / 0.10成本PF 2.24 / 4/6年。",
        "",
        markdown_table(df[cols], cols),
    ]
    (OUT_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote: {OUT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
