# MT5 Ledger Deinit Fix Full 20260713 v1 Summary

## Snapshot
- Window: `2018-01-01 ~ 2026-07-07`
- Tester start balance: `500`
- Tester final balance: `3940.37`
- Files:
  - `30m2H_strategy_trade_ledger.csv`
  - `30m2H_strategy_deal_history.csv`
  - `30m2H_strategy_signals_export.csv`

## Fixes Validated
- `magic=0` close deals are now matched by `position_id` before magic fallback.
- Active ledger slots are finalized from history during `OnDeinit`.
- Raw deal history export is available as `30m2H_strategy_deal_history.csv`.

## Reconciliation
- Raw deal history OUT net profit: `3440.37`
- Trade ledger net profit: `3440.37`
- Difference: `0.00`
- Ledger rows: `234`
- Unique signals: `78`
- Missing OUT deals: `0`
- Extra ledger deals: `0`

## MT5 Metrics
- Final balance: `3940.37`
- Win count: `33 / 78`
- Win rate: `42.3077%`
- Any-stage SL count: `72`
- All-stage SL count: `36`

## Current Judgement
- MT5 trade ledger is now reliable enough for Python dynamic-risk and signal-level alignment.
- Remaining mismatch is no longer ledger completeness.
- Next step should rebuild Python-vs-MT5 mapping with the known MT5 anchor semantics instead of exact key matching.
