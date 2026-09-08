# SIM Continuous Runner Finite Trial

## Decision

- status: `pass`
- ready_to_sim_continuous_runner_execution: `True`
- ready_to_live_trade: `False`
- cycles_requested: `12`
- cycles_completed: `12`
- failed_cycles_count: `0`
- blocker_failure_count: `0`
- last_signal_csv_rows: `29`
- last_trade_ledger_rows: `0`
- last_positions_count: `0`
- last_orders_count: `0`

## Boundary

- This is a bounded SIM_ONLY continuous monitor trial.
- It does not launch MT5, does not call `auto_trade/auto_trader.py`, and does not enable live trading.
- `ready_to_live_trade` remains false.
- The kill switch is `auto_trade/RUNNER_STOP.flag`; if present, the trial stops before the next cycle.

## Cycle Summary

- cycle `1`: status `pass`, monitor `pass`, signal rows `27`, ledger rows `0`, positions `0`, orders `0`
- cycle `2`: status `pass`, monitor `pass`, signal rows `27`, ledger rows `0`, positions `0`, orders `0`
- cycle `3`: status `pass`, monitor `pass`, signal rows `27`, ledger rows `0`, positions `0`, orders `0`
- cycle `4`: status `pass`, monitor `pass`, signal rows `27`, ledger rows `0`, positions `0`, orders `0`
- cycle `5`: status `pass`, monitor `pass`, signal rows `27`, ledger rows `0`, positions `0`, orders `0`
- cycle `6`: status `pass`, monitor `pass`, signal rows `28`, ledger rows `0`, positions `0`, orders `0`
- cycle `7`: status `pass`, monitor `pass`, signal rows `28`, ledger rows `0`, positions `0`, orders `0`
- cycle `8`: status `pass`, monitor `pass`, signal rows `28`, ledger rows `0`, positions `0`, orders `0`
- cycle `9`: status `pass`, monitor `pass`, signal rows `28`, ledger rows `0`, positions `0`, orders `0`
- cycle `10`: status `pass`, monitor `pass`, signal rows `28`, ledger rows `0`, positions `0`, orders `0`
- cycle `11`: status `pass`, monitor `pass`, signal rows `28`, ledger rows `0`, positions `0`, orders `0`
- cycle `12`: status `pass`, monitor `pass`, signal rows `29`, ledger rows `0`, positions `0`, orders `0`

## Failed Checks

- None.
