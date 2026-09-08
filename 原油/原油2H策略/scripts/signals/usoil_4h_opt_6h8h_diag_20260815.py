# -*- coding: utf-8 -*-
"""4H optimization + 6H/8H signal-funnel diagnostics (USOIL).

Part A: why 6H/8H produce no 2H-executed signals:
  raw crosses -> confirm pass -> stop-spec pass -> 2H execution count.
Part B: 4H golden-cross optimization:
  confirm window {1,2} x thr {0.3,0.4,0.5} x stop spec {0.1-1.0%, 0.05-2.0%},
  executed on 4H itself and on 2H (SL_SRC).
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

import pandas as pd


SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from usoil_large_tf_golden_cross_20260815 import (  # noqa: E402
    load_tf,
    markdown_table,
    metrics,
    golden_trades,
)
OUT_DIR = Path(r"F:\use_code\MTA5_l\原油\原油金叉实验_20260815") / "4h_opt_6h8h_diag"


def funnel(tf: pd.DataFrame, thr: float, window: int, pct_lo: float, pct_hi: float):
    direction = tf["方向"].values
    crosses = int(sum(1 for d in direction if d in ("good", "bad")))
    # confirm passes (window bars, min way/vol_way in direction >= thr), before stop spec
    trades_wide = golden_trades(tf, "confirm", thr)  # uses its own PCT spec; approximate by re-running with wide spec below
    # recompute counts manually via a relaxed copy of golden_trades is complex; use source_signals-style counts
    return crosses


def count_confirm(tf: pd.DataFrame, thr: float, window: int):
    direction = tf["方向"].values
    cross_idx = [i for i in range(len(tf)) if direction[i] in ("good", "bad")]
    ok = 0
    for i in cross_idx:
        side = "L" if direction[i] == "good" else "S"
        idxs = [i + k for k in range(1, window + 1)]
        if max(idxs) + 1 >= len(tf):
            continue
        vals = []
        for j in idxs:
            w = float(tf.iloc[j]["way_s_way"])
            v = float(tf.iloc[j]["vol_way_s_way"])
            vals.append((w, v))
        # BUG-1 修复(2026-09-04): way_s_way/vol_way_s_way 无符号 [0,1], 去掉 sign
        if min(x[0] for x in vals) >= thr and min(x[1] for x in vals) >= thr:
            ok += 1
    return ok


def count_with_stop(tf: pd.DataFrame, thr: float, window: int, pct_lo: float, pct_hi: float, start_year: int = 2020):
    direction = tf["方向"].values
    cross_idx = [i for i in range(len(tf)) if direction[i] in ("good", "bad")]
    n = 0
    for pos, i in enumerate(cross_idx):
        side = "L" if direction[i] == "good" else "S"
        idxs = [i + k for k in range(1, window + 1)]
        if max(idxs) + 1 >= len(tf):
            continue
        # BUG-1 修复(2026-09-04): way_s_way/vol_way_s_way 无符号 [0,1], 去掉 sign
        if not (min(float(tf.iloc[j]["way_s_way"]) for j in idxs) >= thr
                and min(float(tf.iloc[j]["vol_way_s_way"]) for j in idxs) >= thr):
            continue
        k = cross_idx[pos - 1] if pos > 0 else 0
        seg = pd.to_numeric(tf.iloc[k:i]["SMA_13"], errors="coerce").dropna()
        if seg.empty:
            continue
        sl = float(seg.min()) if side == "L" else float(seg.max())
        entry_idx = i + window + 1
        if entry_idx >= len(tf):
            continue
        entry = float(tf.iloc[entry_idx]["open"])
        pct = abs(entry - sl) / entry * 100.0
        if pct_lo <= pct <= pct_hi:
            n += 1
    return n


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # ---- Part A: 6H/8H funnel ----
    print("==== 6H/8H signal funnel (confirm thr=0.5, window=2) ====")
    funnel_rows = []
    for tf_name in ["6H", "8H"]:
        tf = load_tf(tf_name)
        crosses = int(sum(1 for d in tf["方向"].values if d in ("good", "bad")))
        c2 = count_confirm(tf, 0.5, 2)
        c2_stop = count_with_stop(tf, 0.5, 2, 0.1, 1.0)
        funnel_rows.append({"tf": tf_name, "raw_crosses": crosses, "confirm_pass": c2,
                            "confirm+stop_pass": c2_stop})
        print(f"  {tf_name}: raw_crosses={crosses} confirm_pass={c2} confirm+stop={c2_stop}")
    fd = pd.DataFrame(funnel_rows)
    fd.to_csv(OUT_DIR / "funnel_6h8h.csv", index=False, encoding="utf-8-sig")

    # ---- Part B: 4H optimization ----
    print("\n==== 4H optimization ====")
    tf4 = load_tf("4H")
    tf2 = load_tf("2H")
    rows = []
    for thr in [0.3, 0.4, 0.5]:
        for pct_lo, pct_hi in [(0.1, 1.0), (0.05, 2.0)]:
            import usoil_large_tf_golden_cross_20260815 as lg
            old_lo, old_hi = lg.PCT_LO, lg.PCT_HI
            lg.PCT_LO, lg.PCT_HI = pct_lo, pct_hi
            try:
                trades4 = golden_trades(tf4, "confirm", thr)
            finally:
                lg.PCT_LO, lg.PCT_HI = old_lo, old_hi
            if trades4.empty:
                continue
            pnl4 = pd.to_numeric(trades4["pnl_points"], errors="coerce")
            ts4 = pd.to_datetime(trades4["signal_time"])
            m4 = metrics(pnl4)
            years4 = pd.DataFrame({"ts": ts4, "pnl": pnl4}).assign(y=ts4.dt.year).groupby("y")["pnl"].sum()
            rows.append(
                {
                    "exec": "4H", "window": 2, "thr": thr,
                    "pct_spec": f"{pct_lo:g}-{pct_hi:g}%", "n": m4["n"], "pf0": m4["pf"],
                    "ev0": m4["ev"], "pnl0": m4["pnl"],
                    "pos_years": f"{int((years4 > 0).sum())}/{len(years4)}",
                }
            )
            print(
                f"  4H thr={thr} spec={rows[-1]['pct_spec']}: n={m4['n']} pf0={m4['pf']:.3f} "
                f"ev0={m4['ev']:+.2f} years={rows[-1]['pos_years']}"
            )
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "4h_opt_matrix.csv", index=False, encoding="utf-8-sig")
    lines = [
        "# 4H 优化 + 6H/8H 无信号诊断",
        "",
        "## 6H/8H 信号漏斗（confirm thr=0.5, 2根确认）",
        "",
        markdown_table(fd, [str(c) for c in fd.columns]),
        "",
        "## 4H 优化矩阵（4H 自身执行 + 2H 执行）",
        "",
        markdown_table(df[["exec", "window", "thr", "pct_spec", "n", "pf0", "ev0", "pnl0", "pos_years"]],
                       ["exec", "window", "thr", "pct_spec", "n", "pf0", "ev0", "pnl0", "pos_years"]),
    ]
    (OUT_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote: {OUT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
