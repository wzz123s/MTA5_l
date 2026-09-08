# -*- coding: utf-8 -*-

"""Pure out-of-sample re-test for USOIL 2H golden-cross confirm filter.

Rule: golden/death cross + 2-bar confirmation min(way/vol_way) >= thr,
entry next-open, SL = segment SMA13 extreme (0.1-1.0%), single-position exit.

Honest protocol:
  1) train window 2020-2023 -> scan thr {0.4,0.5,0.6} (require n>=10), pick best
  2) apply chosen thr to OOS 2024-2026 (untouched)
  3) also report the pre-specified thr=0.5 OOS for reference
  4) cost sensitivity (0.02/0.05/0.10/0.20) + rolling 12M + yearly + equity DD
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
    PCT_LO,
    PCT_HI,
    golden_trades,
    load_tf,
    markdown_table,
    metrics,
)


OUT_DIR = Path(r"F:\use_code\MTA5_l\原油\原油金叉实验_20260815") / "2h_confirm_oos"
COSTS = [0.0, 0.02, 0.05, 0.10, 0.20]
TRAIN_END = 2023


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tf = load_tf("2H")
    rows = []
    trades_cache = {}
    for thr in [0.4, 0.5, 0.6]:
        trades = golden_trades(tf, "confirm", thr)
        if trades.empty:
            continue
        pnl = pd.to_numeric(trades["pnl_points"], errors="coerce")
        ts = pd.to_datetime(trades["signal_time"])
        train_mask = ts.dt.year <= TRAIN_END
        test_mask = ~train_mask
        m_tr = metrics(pnl[train_mask])
        m_te = metrics(pnl[test_mask])
        rows.append(
            {
                "thr": thr,
                "train_n": m_tr["n"],
                "train_pf": m_tr["pf"],
                "train_ev": m_tr["ev"],
                "train_pnl": m_tr["pnl"],
                "test_n": m_te["n"],
                "test_pf": m_te["pf"],
                "test_ev": m_te["ev"],
                "test_pnl": m_te["pnl"],
            }
        )
        trades_cache[thr] = (trades, pnl, ts)
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "thr_scan.csv", index=False, encoding="utf-8-sig")
    print("thr scan (train 2020-2023 -> test 2024-2026):")
    print(df.to_string(index=False))

    # train-based pick (require train n>=10)
    train_ok = df[df["train_n"] >= 10]
    if not train_ok.empty:
        picked = train_ok.sort_values(["train_pf", "train_ev", "train_n"], ascending=[False, False, False]).iloc[0]
    else:
        picked = df.sort_values(["train_pf", "train_ev"], ascending=[False, False]).iloc[0]
    picked_thr = float(picked["thr"])
    print(f"\n>> train-based pick: thr={picked_thr} (train_pf={picked['train_pf']:.3f})")

    results = []
    for label, thr in [("picked", picked_thr), ("prespecified_0.5", 0.5)]:
        trades, pnl, ts = trades_cache[thr]
        test_mask = ts.dt.year > TRAIN_END
        tpnl = pnl[test_mask]
        tts = ts[test_mask]
        m = metrics(tpnl)
        row = {
            "candidate": label,
            "thr": thr,
            "test_n": m["n"],
            "test_wr": m["wr"],
            "test_pf": m["pf"],
            "test_ev": m["ev"],
            "test_pnl": m["pnl"],
        }
        for cost in COSTS[1:]:
            mc = metrics(tpnl - cost)
            row[f"test_pf_{cost:g}"] = mc["pf"]
        results.append(row)
        print(
            f"  {label} (thr={thr}): test_n={m['n']} test_pf={m['pf']:.3f} "
            f"test_ev={m['ev']:+.2f} test_pnl={m['pnl']:+.1f}"
        )
        for cost in COSTS[1:]:
            print(f"    cost {cost:g}: test_pf={metrics(tpnl - cost)['pf']:.3f}")
        # yearly within OOS
        yrs = pd.DataFrame({"ts": tts, "pnl": tpnl}).assign(y=tts.dt.year).groupby("y")["pnl"].agg(["count", "sum"])
        print("    OOS yearly:", {int(y): (int(r["count"]), round(float(r["sum"]), 1)) for y, r in yrs.iterrows()})
        # full-sample yearly + rolling for reference
        full_years = pd.DataFrame({"ts": ts, "pnl": pnl}).assign(y=ts.dt.year).groupby("y")["pnl"].sum()
        full_years.to_csv(OUT_DIR / f"{label}_full_yearly.csv", encoding="utf-8-sig")
        # equity / max DD (full sample, cost 0.05)
        eq = (pnl - 0.05).cumsum()
        peak = eq.cummax()
        dd = (peak - eq).max()
        print(f"    full equity pnl(0.05 cost)={eq.iloc[-1]:+.1f} maxDD={dd:.1f}")
    res_df = pd.DataFrame(results)
    res_df.to_csv(OUT_DIR / "oos_summary.csv", index=False, encoding="utf-8-sig")

    lines = [
        "# USOIL 2H 金叉后确认：纯样本外复测（2020-2023 定参 → 2024-2026 验证）",
        "",
        "## 阈值扫描（训练期 2020-2023）",
        "",
        markdown_table(df, [str(c) for c in df.columns]),
        "",
        f"## 训练期选参：thr={picked_thr}（train_n≥10，按训练 PF 选）",
        "",
        "## 样本外（2024-2026）",
        "",
        markdown_table(res_df, [str(c) for c in res_df.columns]),
        "",
        "> 注：样本外仅 3 年、26 笔（thr=0.5），2026 年仅 1 笔；结论需谨慎。",
    ]
    (OUT_DIR / "oos_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote: {OUT_DIR / 'oos_report.md'}")


if __name__ == "__main__":
    main()
