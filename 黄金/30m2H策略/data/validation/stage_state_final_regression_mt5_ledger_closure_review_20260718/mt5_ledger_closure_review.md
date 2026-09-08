# Final Regression: MT5 Full Stage-state Ledger Closure Review

- Decision date: 2026-07-18
- Check id: `mt5_full_stage_state_ledger_closure_review`
- Status: `pass`
- Pass: `True`
- Reason: `mt5_deal_history_trade_ledger_unique_signals_and_tester_final_balance_close`

## Closure Snapshot

| metric | value |
|---|---:|
| `trade_ledger_stage_rows` | 246 |
| `trade_ledger_unique_signals` | 82 |
| `deal_history_rows` | 492 |
| `deal_history_in_rows` | 246 |
| `deal_history_out_rows` | 246 |
| `trade_ledger_net_profit` | 1149.84 |
| `deal_history_out_net_profit` | 1149.84 |
| `unique_signals_net_profit` | 1149.84 |
| `initial_balance` | 500.0 |
| `computed_final_balance` | 1649.84 |
| `unique_final_balance` | 1649.84 |
| `tester_final_balance` | 1649.84 |
| `deinit_rows` | 0 |

## Check Result

- Failed checks: `0`
- Stage group anomalies: `0`
- Position closure anomalies: `0`
- Ticket profit mismatches: `0`
- Unique signal mismatches: `0`

## Boundary

This review validates ledger/accounting closure only. It does not rerun the tester and does not modify EA or Python strategy logic.
