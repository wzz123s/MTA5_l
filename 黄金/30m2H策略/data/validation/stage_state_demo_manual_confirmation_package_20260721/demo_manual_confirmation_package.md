# Demo Manual Confirmation Package

## Decision

- status: `demo_manual_confirmation_collected_nonprod_rehearsal_pending`
- account_alias: `MT5_DEMO_***085`
- account_type: `demo_nonproduction`
- symbol: `XAUUSDm`
- starting_balance_cap: `2000`
- leverage: `1:2000`
- risk_mode: `strategy_defined`
- allowed_runner: `MT5_EA_ONLY`
- emergency_stop: `disable_mt5_auto_trading`
- position_close_rule: `strategy_defined`
- ready_to_nonprod_rehearsal: `True`
- ready_to_live_trade: `False`

## Boundary

- This package records approval for MT5 demo/non-production rehearsal only.
- It does not approve real-money live trading.
- The full demo account id is not written into repo artifacts.
- The next required evidence is an actual MT5 tester/demo rehearsal report and ledger.

## Evidence Matrix

- `LIVE-GAP-001`: `collected_for_demo_nonprod_only`, nonprod ready `True`, live ready `False`
- `LIVE-GAP-005`: `collected_for_demo_nonprod_only`, nonprod ready `True`, live ready `False`
- `LIVE-GAP-006`: `collected_for_demo_nonprod_only`, nonprod ready `True`, live ready `False`
- `LIVE-GAP-007`: `collected_for_demo_nonprod_only`, nonprod ready `True`, live ready `False`
- `LIVE-GAP-009`: `collected_for_demo_nonprod_only`, nonprod ready `True`, live ready `False`
- `LIVE-GAP-010`: `planned_not_executed`, nonprod ready `True`, live ready `False`

## Checks

- `approval_scope_nonprod_demo_only`: `True` - actual `nonprod_demo_rehearsal_only`, expected `nonprod_demo_rehearsal_only`
- `account_alias_redacted`: `True` - actual `MT5_DEMO_***085`, expected `MT5_DEMO_***085`
- `full_account_id_not_written`: `True` - actual `False`, expected `False`
- `symbol_xauusdm`: `True` - actual `XAUUSDm; set=XAUUSDm`, expected `XAUUSDm`
- `balance_cap_2000`: `True` - actual `2000`, expected `2000`
- `leverage_2000`: `True` - actual `2000`, expected `2000`
- `risk_strategy_defined`: `True` - actual `3.0`, expected `present`
- `max_lot_strategy_defined`: `True` - actual `10.0`, expected `present`
- `runner_mt5_ea_only`: `True` - actual `MT5_EA_ONLY`, expected `MT5_EA_ONLY`
- `emergency_stop_present`: `True` - actual `disable_mt5_auto_trading`, expected `disable_mt5_auto_trading`
- `nonprod_rehearsal_not_yet_executed`: `True` - actual `pending`, expected `pending`
- `ready_to_nonprod_rehearsal_true`: `True` - actual `True`, expected `True`
- `ready_to_live_trade_false`: `True` - actual `False`, expected `False`
