# -*- coding: utf-8 -*-
"""读 v64 台账的收益汇总"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

EA = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_trade_ledger.csv"
ea = pd.read_csv(EA, encoding='utf-8-sig')

print("=== 2H_M30_6H_ABC_EA Tester 回测收益 ===")
print("交易数(entry|dir):", ea.groupby(['entry_time','dir']).ngroups)
print("初始余额: 500 USD")
print("最终余额:", round(ea['virtual_balance'].iloc[-1], 2), "USD")
print("总盈亏:", round(ea['virtual_balance'].iloc[-1] - 500, 2), "USD")

# 分方向
ea['dir_n'] = ea['dir'].map({'BUY':'L','SELL':'S'})
# 每笔交易的盈亏（按 entry|dir 聚合 pnl_usd）
trade_pnl = ea.groupby(['entry_time','dir']).agg(
    pnl=('pnl_usd','sum'), dir_n=('dir_n','first')
).reset_index()
for d in ['L','S']:
    sub = trade_pnl[trade_pnl['dir_n']==d]
    wins = (sub['pnl']>0).sum()
    total = len(sub)
    print("\n%s: %d 笔, 胜率 %.1f%%, 总盈亏 %.2f USD, 平均 %.2f USD" % (
        '多头L' if d=='L' else '空头S', total, 100*wins/max(total,1), sub['pnl'].sum(), sub['pnl'].mean()))
