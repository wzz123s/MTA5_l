# -*- coding: utf-8 -*-
"""2H triggers (cross + post_n) gated by 4H/6H/8H three-condition opportunity.

Trigger (on 2H): golden/death cross, or n bars after the cross (post_n 2-6),
entry next 2H open; stop = 2H structure (cross: prev-seg SMA13 extreme;
post_n: current bar SMA13), pct spec 0.1-1.0%; single-position exit.
Gate (4H/6H/8H): continuous bars >= n_min, extreme-bar way/vol_way >= thr,
SMMA13-extreme amplitude within [lo,hi].
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

import pandas as pd


SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from combined_abc_30m2h_2h_20260814 import (  # noqa: E402
    build_three_opportunities,
    replay_signals,
)
from usoil_large_tf_golden_cross_20260815 import (  # noqa: E402
    load_tf,
    markdown_table,
    metrics,
)
from usoil_4h6h8h_strategies_20260815 import gate_arrays  # noqa: E402


OUT_DIR = Path(r"F:\use_code\MTA5_l\原油\原油金叉实验_20260815") / "2h_cross_postn_gate"
PCT_LO, PCT_HI = 0.1, 1.0
GATES = {
    "4H": (8, 0.5, 0.5, 5.0),
    "6H": (8, 0.5, 1.0, 8.0),
    "8H": (12, 0.5, 1.0, 8.0),
}


def build_2h_triggers(tf2):
    sig = build_three_opportunities(tf2, spec_lo=0.001, spec_hi=100.0)
    replayed = replay_signals(sig, tf2)
    replayed["stop_pct"] = (
        pd.to_numeric(replayed["stop_distance"], errors="coerce")
        / pd.to_numeric(replayed["entry"], errors="coerce")
        * 100.0
    )
    return replayed.loc[
        replayed["stop_pct"].between(PCT_LO, PCT_HI)
    ].copy().reset_index(drop=True)


def gate_lookup(gt, n_min, thr, amp_lo, amp_hi):
    times = pd.to_datetime(gt["bar_close_time"]).values.astype("datetime64[ns]")
    d, sl, w, v, amp = gate_arrays(gt)

    def check(t, need_long):
        idx = bisect.bisect_right(times, pd.Timestamp(t).to_datetime64()) - 1
        if idx < 0:
            return False
        if need_long:
            ok = d[idx] == -1 and sl[idx] >= n_min and w[idx] >= thr and v[idx] >= thr  # BUG修复: way_s_way无符号
        else:
            ok = d[idx] == 1 and sl[idx] >= n_min and w[idx] >= thr and v[idx] >= thr
        return ok and amp_lo <= amp[idx] <= amp_hi

    return check


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
    trig = build_2h_triggers(tf2)
    trig["is_post"] = trig["mode"].str.startswith("post_n")
    print("2H triggers (0.1-1.0%): cross=", int((~trig["is_post"]).sum()),
          "post_n=", int(trig["is_post"].sum()), "total=", len(trig))

    gates = {tf: (load_tf(tf),) + GATES[tf] for tf in GATES}
    rows = []
    for gt_name, (gt, n_min, thr, amp_lo, amp_hi) in gates.items():
        check = gate_lookup(gt, n_min, thr, amp_lo, amp_hi)
        trig_g = trig.loc[[check(t, r["dir"] == "L") for t, r in zip(trig["signal_time"], trig.to_dict("records"))]].copy()
        for mode_name, mask in [
            ("cross", ~trig_g["is_post"]),
            ("post_n", trig_g["is_post"]),
            ("both", pd.Series(True, index=trig_g.index)),
        ]:
            sub = trig_g.loc[mask]
            if sub.empty or len(sub) < 10:
                continue
            pnl = pd.to_numeric(sub["pnl_points"], errors="coerce")
            ts = pd.to_datetime(sub["signal_time"])
            m = metrics(pnl)
            years = pd.DataFrame({"ts": ts, "pnl": pnl}).assign(y=ts.dt.year).groupby("y")["pnl"].sum()
            rows.append({
                "gate": gt_name, "trigger": mode_name, "n": m["n"], "wr": m["wr"],
                "pf0": m["pf"], "ev0": m["ev"], "test_pf0": test_pf(pnl, ts),
                "pos_years": f"{int((years > 0).sum())}/{len(years)}",
            })
            print(
                f"  {gt_name} {mode_name}: n={m['n']} pf0={m['pf']:.3f} ev0={m['ev']:+.2f} "
                f"test0={rows[-1]['test_pf0']:.3f} years={rows[-1]['pos_years']}"
            )
        if not trig_g.empty:
            pnl = pd.to_numeric(trig_g["pnl_points"], errors="coerce")
            ts = pd.to_datetime(trig_g["signal_time"])
            m = metrics(pnl)
            years = pd.DataFrame({"ts": ts, "pnl": pnl}).assign(y=ts.dt.year).groupby("y")["pnl"].sum()
            print(f"  {gt_name} (gate-only, no trigger split): n={m['n']} pf0={m['pf']:.3f} "
                  f"test0={test_pf(pnl, ts):.3f} years={int((years > 0).sum())}/{len(years)}")

    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "matrix.csv", index=False, encoding="utf-8-sig")
    cols = ["gate", "trigger", "n", "wr", "pf0", "ev0", "test_pf0", "pos_years"]
    lines = [
        "# 2H 触发（cross + post_n） × 4H/6H/8H 三条件门",
        "",
        "> 2H 结构止损 0.1-1.0%，单段退出；门参数取各周期最优（4H:n8/amp0.5-5, 6H:n8/1-8, 8H:n12/1-8）。",
        "",
        markdown_table(df[cols], cols),
    ]
    (OUT_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote: {OUT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
