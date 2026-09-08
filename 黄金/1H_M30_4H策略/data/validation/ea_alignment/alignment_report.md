# 1H_M30_4H Python vs EA Alignment

- status: `mismatch`
- EA ledger: `黄金/1H_M30_4H策略\data\validation\ea_alignment\1H_M30_4H_strategy_trade_ledger.csv`
- stop filter: `6-20pt current profile`
- anchor shift: `30 minutes`
- research set: `1H_M30_4H_Strategy_EA.mt5_raw_research_20260725.set`
- expected rows: `294`
- EA rows: `1177`
- matched: `147`
- Python only: `147`
- EA only: `1030`
- mode mismatch: `0`
- lot mismatch: `0`
- PnL sign mismatch: `28`

## Diagnosis

The EA ran and exported a ledger, but the EA trade keys do not match the Python expected stage ledger. Deployment remains blocked until the EA signal model, time axis, stop filter, and stage exit model reproduce the Python profile.
