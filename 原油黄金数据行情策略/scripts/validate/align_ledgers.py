# -*- coding: utf-8 -*-
"""M4.4 逐笔对齐：expected ledger vs MT5 Tester actual ledger。
匹配键：entry_time + dir；比较 entry/stop/exit/pnl（容差）。
用法: python align_ledgers.py --expected xxx --actual yyy --name gold
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[2]

MATCH_KEYS = ["entry_time", "dir"]
TOL = {"entry": 0.5, "stop": 0.5, "exit_price": 1.0, "pnl": 0.5}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expected", required=True)
    ap.add_argument("--actual", required=True)
    ap.add_argument("--name", required=True)
    args = ap.parse_args()
    exp = pd.read_csv(args.expected, parse_dates=["entry_time"])
    act = pd.read_csv(args.actual, parse_dates=["entry_time"])
    # 归一化 dir
    exp["dir_n"] = exp["dir"].map({"BUY": "L", "SELL": "S", "L": "L", "S": "S", "buy": "L", "sell": "S"})
    act["dir_n"] = act["dir"].map({"BUY": "L", "SELL": "S", "L": "L", "S": "S", "buy": "L", "sell": "S"})
    # 对齐
    exp_k = exp.set_index(["entry_time", "dir_n"])
    act_k = act.set_index(["entry_time", "dir_n"])
    common = exp_k.index.intersection(act_k.index)
    only_exp = len(exp_k.index.difference(act_k.index))
    only_act = len(act_k.index.difference(exp_k.index))
    print(f"[{args.name}] expected={len(exp)} actual={len(act)} matched={len(common)} only_expected={only_exp} only_actual={only_act}")
    # 字段比较
    diffs = []
    for key in common:
        e = exp_k.loc[key]
        a = act_k.loc[key]
        if isinstance(e, pd.DataFrame):
            e = e.iloc[0]
        if isinstance(a, pd.DataFrame):
            a = a.iloc[0]
        for col, tol in TOL.items():
            if col in e.index and col in a.index:
                ev = pd.to_numeric(e[col], errors="coerce")
                av = pd.to_numeric(a[col], errors="coerce")
                if pd.notna(ev) and pd.notna(av) and abs(ev - av) > tol:
                    diffs.append((str(key), col, float(ev), float(av)))
    print(f"字段差异数: {len(diffs)}")
    for d in diffs[:20]:
        print("  ", d)
    # 匹配率
    total = len(exp_k)
    rate = len(common) / total * 100 if total else 0
    print(f"匹配率: {rate:.1f}% ({len(common)}/{total})")
    ok = len(common) == total and only_act == 0 and len(diffs) == 0
    print("ALIGN:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
