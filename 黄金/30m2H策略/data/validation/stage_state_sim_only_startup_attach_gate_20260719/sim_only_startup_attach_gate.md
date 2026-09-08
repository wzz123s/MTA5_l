# SIM_ONLY Startup Attach Gate

## Decision

- status: `pass_attach_pending_market_data`
- ready_to_runtime_forward_review_after_market_tick: `True`
- ready_to_sim_continuous_runner_execution: `False`
- ready_to_live_trade: `False`
- signal_csv_rows: `0`
- trade_ledger_rows: `0`
- latest_tick_time: `2026-07-18T04:57:58`
- latest_tick_age_minutes: `2107.27`

## Interpretation

- SIM_ONLY startup attach is confirmed by terminal log and target CSV creation.
- Runtime data review remains pending because the signal CSV has no data rows yet.
- The current blocker is stale/no market tick, not strategy logic or live-trade approval.

## Failed Checks

- `market_tick_recent_enough_for_forward_review`: 2107.27 (expected <= 90 minutes)
- `signal_csv_has_runtime_rows`: 0 (expected > 0)
