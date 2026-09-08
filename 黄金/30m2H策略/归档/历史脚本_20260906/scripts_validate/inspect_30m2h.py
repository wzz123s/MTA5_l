# -*- coding: utf-8 -*-
"""检查预期台账格式 + 台账 vs 预期入场时间."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

exp_path = r"F:\use_code\MTA5_l\黄金\30m2H策略\auto_trade\python_expected_2025_2026\python_expected_30m2h_2025_2026.csv"
led_path = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\30m2H_abc_trade_ledger.csv"

exp = pd.read_csv(exp_path, encoding='utf-8-sig')
led = pd.read_csv(led_path)
print("=== 预期 CSV 列:", list(exp.columns))
print("=== 预期 head 3 ===")
print(exp.head(3).to_string())
print("\n=== 预期 trade_key 唯一值数:", exp['trade_key'].nunique(), "/", len(exp))
print("=== 台账 head 5 ===")
print(led.head(5).to_string())

# 对比 signal_time 范围
print("\n预期 signal_time:", pd.to_datetime(exp['signal_time']).min(), "~", pd.to_datetime(exp['signal_time']).max())
print("台账 signal_time:", pd.to_datetime(led['signal_time']).min(), "~", pd.to_datetime(led['signal_time']).max())

# 台账是否含预期第一笔的 entry?
print("\n=== 台账里的 entry_time 值 (前 10) ===")
print(sorted(pd.to_datetime(led['entry_time']).unique())[:10])
print("=== 预期 entry_time (前 10) ===")
print(sorted(pd.to_datetime(exp['entry_time']).unique())[:10])
