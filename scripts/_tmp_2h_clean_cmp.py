# -*- coding: utf-8 -*-
"""2H V4 干净对账: EA(>=2025-01-01) vs expected 2025-26."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
def rd(p):
    for e in ["utf-8-sig","utf-8","gbk","mbcs"]:
        try: return pd.read_csv(p,encoding=e)
        except Exception: continue
    raise RuntimeError(p)
led=rd(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_trade_ledger.csv")
exp=rd(r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\python_expected_2025_2026\python_expected_2h_abc_2025_2026.csv")
def key(f):
    f=f.copy(); f['dn']=f['dir'].astype(str).str.upper().map({'BUY':'L','SELL':'S','L':'L','S':'S'})
    f['k']=pd.to_datetime(f['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S')+'|'+f['dn']+'|S'+f['stage'].astype(str)
    return f
exp=key(exp); led=key(led)
# EA 过滤 >=2025-01-01
led['et']=pd.to_datetime(led['entry_time'])
led25=led[led['et']>=pd.Timestamp("2025-01-01")]
ek=set(exp['k']); lk=set(led25['k'])
print("EA(>=2025) rows:", len(led25), "trades:", led25.drop_duplicates(['et','dn']).shape[0], "| exp trades:", exp.drop_duplicates(['signal_time','dn']).shape[0])
print("matched %d/%d = %.2f%%"%(len(ek&lk), len(ek), len(ek&lk)/len(ek)*100))
miss=ek-lk; extra=lk-ek
print("missing:", len(miss), "| extra:", len(extra))
mexp=exp[exp['k'].isin(miss)]
print("missing by stage:", mexp['stage'].value_counts().sort_index().to_dict())
print("missing by mode:", mexp.drop_duplicates('k')['mode'].value_counts().to_dict())
if len(extra)<=12: print("extra samples:", sorted(extra))
