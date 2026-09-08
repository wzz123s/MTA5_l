# -*- coding: utf-8 -*-
"""对账: Agent 台账 vs 基线预期 vs 改进预期."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

ledger = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_trade_ledger.csv"
base_exp = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\python_expected_2025_2026\python_expected_2h_abc_2025_2026.csv"
reg_exp = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\data\validation\nan\python_expected_reg55_0p5_ledger_2025_2026.csv"

def read_csv_try(path):
    for enc in ['utf-8-sig', 'utf-8', 'gbk', 'mbcs', 'utf-16']:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    raise RuntimeError("无法读取 " + path)

led = read_csv_try(ledger)
print("台账列:", list(led.columns))
print("台账行数(数据):", len(led))

# 归一化 dir
led['dir_n'] = led['dir'].astype(str).str.upper().map({'BUY':'L','SELL':'S'})
led['entry_dt'] = pd.to_datetime(led['entry_time'])
led['key'] = led['entry_dt'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + led['dir_n'] + '|S' + led['stage'].astype(str)

n_trades = led.drop_duplicates(['signal_time','dir']).shape[0]
print("交易数(去重 signal_time+dir):", n_trades)
print("final balance:", led['virtual_balance'].iloc[-1] if len(led) else None)
print("by stage:", led['stage'].value_counts().sort_index().to_dict())

def compare(exp_path, label):
    exp = read_csv_try(exp_path)
    exp['dir_n'] = exp['dir'].astype(str).str.upper().map({'BUY':'L','SELL':'S'}).fillna(exp['dir'].astype(str).str.upper())
    exp['entry_dt'] = pd.to_datetime(exp['entry_time'])
    exp['key'] = exp['entry_dt'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + exp['dir_n'] + '|S' + exp['stage'].astype(str)
    exp_keys = set(exp['key'])
    led_keys = set(led['key'])
    matched = len(exp_keys & led_keys)
    missing = len(exp_keys - led_keys)
    extra = len(led_keys - exp_keys)
    print(f"\n[{label}] 预期={len(exp_keys)} 台账={len(led_keys)}")
    print(f"  matched={matched} missing(预期有台账无)={missing} extra(台账有预期无)={extra}")
    return matched, missing, extra

compare(base_exp, "基线预期 (InpNanRegOn=false)")
compare(reg_exp, "改进预期 (InpNanRegOn=true, 184笔)")
