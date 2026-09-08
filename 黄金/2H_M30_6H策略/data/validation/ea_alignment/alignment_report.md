# 2H_M30_6H Python vs EA Alignment

- status: `mismatch`
- EA ledger: `黄金/2H_M30_6H策略\data\validation\ea_alignment\2H_M30_6H_strategy_trade_ledger.csv`
- stop filter: `12-34pt current profile`
- anchor shift: `30 minutes`
- research set: `2H_M30_6H_Strategy_EA.mt5_raw_research_20260725.set`
- expected rows: `453`
- EA rows: `54`
- matched: `9`
- Python only: `444`
- EA only: `45`
- mode mismatch: `0`
- lot mismatch: `0`
- PnL sign mismatch: `4`

## Diagnosis

The EA ran and exported a ledger, but the EA trade keys do not match the Python expected stage ledger. Deployment remains blocked until the EA signal model, time axis, stop filter, and stage exit model reproduce the Python profile.
