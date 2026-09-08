# MT5 trade ledger full-run summary

## Scope
- EA binary: terminal-side `Experts\Advisors\30m2H_Strategy_EA.ex5` synced from the `2026-07-12 17:41:32` ledger-enabled build
- Tester window: `2018-01-01 ~ 2026-07-07`
- Baseline target: `3940.37 USD / 78 signals`

## Verification result
- Full tester final balance: `3940.37 USD`
- Trade ledger file generated: `30m2H_strategy_trade_ledger.csv`
- Matching bar export generated: `30m2H_strategy_signals_export.csv`
- Tester log contains:
  - `Trade ledger export: 30m2H_strategy_trade_ledger.csv`
  - `Trade ledger export closed`

## Ledger snapshot
- File size: `36511`
- Total rows: `156` (including header)
- Stage close rows: `155`
- Unique executed signal keys: `66`
- Stage counts:
  - `stage1 = 45`
  - `stage2 = 65`
  - `stage3 = 45`
- Top local exit reasons:
  - `deal_exit = 149`
  - `position_gone = 4`
  - `stage1_tp = 1`
  - `stage3_cross_exit = 1`

## Current interpretation
- Ledger export itself is verified and does not change the current MT5 baseline.
- The next comparison step must not assume `ledger unique signals == MT5 log signal count`.
- The immediate gap to explain is:
  - MT5 log signals: `78`
  - Ledger unique executed signals: `66`

## Next use
- Use this ledger snapshot as the MT5 side truth set for:
  - Python dynamic-risk lot simulation
  - exit reason comparison
  - stop-loss count and equity curve reconstruction
