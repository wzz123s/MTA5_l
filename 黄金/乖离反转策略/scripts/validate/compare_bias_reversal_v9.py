# -*- coding: utf-8 -*-
"""乖离反转 Tester 回放对账(2026-09-06 v2, 台账列改造后)
匹配键: signal_time 精确到秒 + dir + pnl 差 < 0.05; 输出 matched/missing/wrong/extra.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
from pathlib import Path

ledger = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\bias_reversal_combo_trade_ledger.csv")
expected = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\data\validation\bias_reversal_v9_ea_baseline_long.csv")

def rd(p):
    for e in ["utf-8-sig", "utf-8", "gbk", "mbcs"]:
        try:
            return pd.read_csv(p, encoding=e)
        except Exception:
            continue
    raise RuntimeError(p)

ea = rd(ledger); exp = rd(expected)
ea.columns = [str(c).strip().lower() for c in ea.columns]
exp.columns = [str(c).strip().lower() for c in exp.columns]
print("EA rows:", len(ea), "| v9 期望:", len(exp))
if "signal_time" not in ea.columns:
    raise SystemExit("EA 台账列不符(期望新回放头): " + str(list(ea.columns)))
ea["sig"] = pd.to_datetime(ea["signal_time"], errors="coerce")
exp["sig"] = pd.to_datetime(exp["signal_time"], errors="coerce")
ea["d"] = ea["dir"].astype(str).str.strip().map({"1": "L", "BUY": "L", "SELL": "S", "-1": "S"})
exp["d"] = exp["dir"].astype(str).str.strip().map({"1": "L", "BUY": "L", "SELL": "S", "-1": "S"})

matched = miss = wrong = 0
for _, r in exp.iterrows():
    m = ea[(ea["sig"].notna()) & (abs((ea["sig"] - r["sig"]).dt.total_seconds()) == 0) & (ea["d"] == r["d"])]
    if len(m):
        d = abs(float(m["pnl_points"].iloc[0]) - float(r["pnl_points"]))
        if d < 0.05:
            matched += 1
        else:
            wrong += 1
            print("  PNL_DIFF", r["sig"], round(float(d), 4))
    else:
        miss += 1
        print("  MISS", r["sig"], r["d"], r.get("exit_reason"))
ek = set(zip(ea["sig"].dt.strftime("%Y-%m-%d %H:%M:%S"), ea["d"]))
sk = set(zip(exp["sig"].dt.strftime("%Y-%m-%d %H:%M:%S"), exp["d"]))
extra = len(ek - sk)
print("matched=%d/%d=%.1f%% | missing=%d | wrong_pnl=%d | EA extra=%d" % (matched, len(exp), matched / max(1, len(exp)) * 100, miss, wrong, extra))
if "exit_reason" in ea.columns:
    print("\n=== EA 台账 exit_reason 分布 ===")
    print(ea["exit_reason"].value_counts().to_string())
print("=== 期望 exit_reason 分布 ===")
print(exp["exit_reason"].value_counts().to_string())