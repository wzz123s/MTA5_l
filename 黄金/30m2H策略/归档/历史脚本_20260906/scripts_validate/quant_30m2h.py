# -*- coding: utf-8 -*-
"""量化日期范围 + stage1 差异影响."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

led = pd.read_csv(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\30m2H_abc_trade_ledger.csv")
exp = pd.read_csv(r"F:\use_code\MTA5_l\黄金\30m2H策略\auto_trade\python_expected_2025_2026\python_expected_30m2h_2025_2026.csv", encoding='utf-8-sig')

# 台账 signal 范围
led_max = pd.to_datetime(led['signal_time']).max()
print("台账 signal max:", led_max)
print("预期 signal max:", pd.to_datetime(exp['signal_time']).max())

# 预期在台账 max 之后的行
exp_dt = pd.to_datetime(exp['signal_time'])
after = exp[exp_dt > led_max]
print("预期在台账 signal max 之后的 stage 行:", len(after), "| 交易:", after.drop_duplicates(['signal_time','dir']).shape[0])
print("其中 mode:", after['mode'].value_counts().to_dict())

# 截断预期到台账范围后重算 matched
cut_exp = exp[exp_dt <= led_max].copy()
cut_exp['dir_n'] = cut_exp['dir'].astype(str).str.upper()
cut_exp['key'] = pd.to_datetime(cut_exp['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + cut_exp['dir_n'] + '|S' + cut_exp['stage'].astype(str)
led2 = led.copy()
led2['dir_n'] = led2['dir'].astype(str).str.upper().map({'BUY':'L','SELL':'S'})
led2['key'] = pd.to_datetime(led2['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + led2['dir_n'] + '|S' + led2['stage'].astype(str)
ek = set(cut_exp['key']); lk = set(led2['key'])
m = len(ek & lk)
print("\n截断后 matched:", m, "/", len(ek), "= %.1f%%" % (m/len(ek)*100))
print("missing:", len(ek-lk), "extra:", len(lk-ek))

# 剩余 missing 的交易级 mode
miss_keys = ek - lk
miss = cut_exp[cut_exp['key'].isin(miss_keys)].drop_duplicates(['signal_time','dir'])
print("\n截断后 missing 交易:", len(miss), "| mode:", miss['mode'].value_counts().to_dict())
# stage1 相关: missing 里 stage=1
print("missing 中 stage1 行:", sum(1 for k in miss_keys if k.endswith('|S1')))
