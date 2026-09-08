# -*- coding: utf-8 -*-
"""missing 交易邻近匹配: 是否时间偏移 1 bar."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

led = pd.read_csv(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\30m2H_abc_trade_ledger.csv")
exp = pd.read_csv(r"F:\use_code\MTA5_l\黄金\30m2H策略\auto_trade\python_expected_2025_2026\python_expected_30m2h_2025_2026.csv", encoding='utf-8-sig')

exp['dir_n'] = exp['dir'].astype(str).str.upper()
exp['key'] = pd.to_datetime(exp['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + exp['dir_n'] + '|S' + exp['stage'].astype(str)
led['dir_n'] = led['dir'].astype(str).str.upper().map({'BUY':'L','SELL':'S'})
led['key'] = pd.to_datetime(led['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + led['dir_n'] + '|S' + led['stage'].astype(str)
exp['entry_dt'] = pd.to_datetime(exp['entry_time'])
led['entry_dt'] = pd.to_datetime(led['entry_time'])
exp['sig_dt'] = pd.to_datetime(exp['signal_time'])
led['sig_dt'] = pd.to_datetime(led['signal_time'])

exp_keys = set(exp['key']); led_keys = set(led['key'])
miss_trades = exp[exp['key'].isin(exp_keys - led_keys)].drop_duplicates(['signal_time','dir'])
extra_trades = led[led['key'].isin(led_keys - exp_keys)].drop_duplicates(['signal_time','dir'])

print("=== missing 交易: 预期 signal/entry vs 台账最近交易 ===")
led_trades = led.drop_duplicates(['signal_time','dir'])
for _, mt in miss_trades.iterrows():
    # 台账里同方向最近 entry
    cand = led_trades[(led_trades['dir_n'] == mt['dir_n'])]
    if len(cand):
        cand = cand.copy()
        cand['diff'] = abs(cand['entry_dt'] - mt['entry_dt'])
        best = cand.sort_values('diff').iloc[0]
        note = ""
        if best['diff'] <= pd.Timedelta('1h'):
            note = " <-- 台账有相近(差%s)" % best['diff']
        print("预期 sig=%s entry=%s %s %s | 台账最近 entry=%s %s (差%s)%s" % (
            mt['sig_dt'], mt['entry_dt'], mt['dir_n'], mt['mode'],
            best['entry_dt'], best['dir_n'], best['diff'], note))
print("\n=== extra 交易 ===")
for _, et in extra_trades.iterrows():
    cand = exp[(exp['dir_n']==et['dir_n'])].copy()
    if len(cand):
        cand['diff'] = abs(cand['entry_dt'] - et['entry_dt'])
        best = cand.sort_values('diff').iloc[0]
        print("extra sig=%s entry=%s %s %s | 预期最近 entry=%s %s (差%s)" % (et['sig_dt'], et['entry_dt'], et['dir_n'], et['mode'], best['entry_dt'], best['dir_n'], best['diff']))
