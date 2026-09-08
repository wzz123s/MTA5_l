# -*- coding: utf-8 -*-
"""Compare USOIL4H_Gate_On2H_EA Tester ledger vs Python expected (72 trades, 2021.01.01-2026.08.15).
Match key = entry_time|dir (EA signal_time is the signal-bar time, 2h earlier; python signal_time == entry bar)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
EXPECTED = ROOT / "原油" / "原油4H门策略" / "data" / "validation" / "experiments_20260815" / "trades.csv"
DEFAULT_EA = ROOT / "原油" / "原油4H门策略" / "auto_trade" / "tester_ledger_4h_gate.csv"
OUT_DIR = ROOT / "原油" / "原油4H门策略" / "auto_trade" / "tester_vs_python_4h_20210101_20260815"
PNL_TOL = 0.01
PRICE_TOL = 0.02
REASON_MAP = {"SL hit": "stop", "opposite cross": "opposite_cross_next_open"}


def norm_time(value) -> str:
    parsed = pd.to_datetime(value, errors="coerce")
    return "" if pd.isna(parsed) else parsed.strftime("%Y-%m-%d %H:%M:%S")


def read_csv_any(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return pd.read_csv(path, encoding=enc)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    return pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ea_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_EA
    exp = read_csv_any(EXPECTED)
    if not ea_path.exists():
        print("EA ledger not found yet: %s" % ea_path)
        return
    ea = read_csv_any(ea_path)
    if ea.empty:
        print("EA ledger empty (0 rows)")
        return

    exp = exp.rename(columns={"pnl_points": "exp_pnl", "exit_reason": "exp_reason"}).copy()
    exp["entry_time_n"] = exp["entry_time"].map(norm_time)
    exp["dir"] = exp["dir"].astype(str).str.upper()
    exp["key"] = exp["entry_time_n"] + "|" + exp["dir"]

    ea = ea.copy()
    ea["entry_time_n"] = ea["entry_time"].map(norm_time)
    ea["dir"] = ea["dir"].map(lambda d: "L" if str(d).upper() in ("L", "BUY", "1", "LONG") else
                              ("S" if str(d).upper() in ("S", "SELL", "-1", "SHORT") else str(d).upper()))
    ea["key"] = ea["entry_time_n"] + "|" + ea["dir"]
    ea["reason_n"] = ea["reason"].map(lambda r: REASON_MAP.get(str(r).strip(), str(r).strip()))
    ea = ea.rename(columns={"entry": "entry_ea", "stop": "stop_ea", "exit_price": "exit_price_ea",
                            "pnl_points": "pnl_ea", "reason_n": "reason_ea"})
    ea = ea.drop(columns=[c for c in ("signal_time", "entry_time", "dir", "entry_time_n") if c in ea.columns])

    matched = exp.merge(ea, on="key", how="inner")
    missing = exp[~exp["key"].isin(ea["key"])]
    extra = ea[~ea["key"].isin(exp["key"])]

    diffs = []
    price_diffs = []
    reason_mm = []
    if not matched.empty:
        matched["pnl_diff"] = (matched["exp_pnl"] - matched["pnl_ea"].astype(float)).abs()
        diffs = matched.loc[matched["pnl_diff"] > PNL_TOL, ["key", "exp_pnl", "pnl_ea", "pnl_diff"]]
        matched["entry_diff"] = (matched["entry"] - matched["entry_ea"].astype(float)).abs()
        matched["exit_diff"] = (matched["exit"] - matched["exit_price_ea"].astype(float)).abs()
        price_diffs = matched.loc[(matched["entry_diff"] > PRICE_TOL) | (matched["exit_diff"] > PRICE_TOL),
                                  ["key", "entry", "entry_ea", "exit", "exit_price_ea", "entry_diff", "exit_diff"]]
        reason_mm = matched.loc[matched["exp_reason"] != matched["reason_ea"], ["key", "exp_reason", "reason_ea"]]
        sign_agree = (matched["exp_pnl"] > 0) == (matched["pnl_ea"].astype(float) > 0)
    else:
        sign_agree = pd.Series(dtype=bool)

    print("=" * 80)
    print("USOIL4H_Gate_On2H_EA  Tester vs Python  对照报告")
    print("区间: 2021.01.01 - 2026.08.15   匹配键: entry_time|dir")
    print("期望台账: %s" % EXPECTED.name)
    print("-" * 80)
    print("expected trades : %d" % len(exp))
    print("EA trades       : %d" % len(ea))
    print("matched         : %d" % len(matched))
    print("missing_in_ea   : %d" % len(missing))
    print("extra_in_ea     : %d" % len(extra))
    if not matched.empty:
        print("pnl sign agree  : %d/%d" % (int(sign_agree.sum()), len(matched)))
        print("pnl diff > %.2f  : %d" % (PNL_TOL, len(diffs)))
        print("entry/exit diff > %.2f : %d" % (PRICE_TOL, len(price_diffs)))
        print("exit reason mismatch : %d" % len(reason_mm))
    print("=" * 80)

    missing.to_csv(OUT_DIR / "tester_vs_python_missing.csv", index=False, encoding="utf-8-sig")
    extra.to_csv(OUT_DIR / "tester_vs_python_extra.csv", index=False, encoding="utf-8-sig")
    if not matched.empty:
        matched.to_csv(OUT_DIR / "tester_vs_python_detail.csv", index=False, encoding="utf-8-sig")
        diffs.to_csv(OUT_DIR / "tester_vs_python_pnl_diffs.csv", index=False, encoding="utf-8-sig")
        price_diffs.to_csv(OUT_DIR / "tester_vs_python_price_diffs.csv", index=False, encoding="utf-8-sig")
        reason_mm.to_csv(OUT_DIR / "tester_vs_python_reason_diffs.csv", index=False, encoding="utf-8-sig")

    ok = (len(missing) == 0 and len(extra) == 0 and len(diffs) == 0
          and len(matched) == len(exp) and len(price_diffs) == 0 and len(reason_mm) == 0)
    print("RESULT:", "PASS - EA 与 Python 完全一致（72 笔全部匹配）" if ok
          else "FAIL - 需排查 missing/extra/pnl/price/reason 差异")
    print("输出目录: %s" % OUT_DIR)


if __name__ == "__main__":
    main()
