# LIVE-GAP-007 Emergency Stop And Rollback Runbook

Generated: 2026-07-23T08:40:20

## Scope

This runbook is for the MT5 EA-only path on `XAUUSDm`. It is a non-production rehearsal artifact and does not approve real-money live trading.

## Immediate Stop Order

1. Create or confirm `auto_trade/EMERGENCY_STOP.flag`.
2. Create or confirm `auto_trade/RUNNER_STOP.flag`.
3. In MT5, turn off Algo Trading / AutoTrading.
4. Remove the EA from any `XAUUSDm` chart or close the terminal if this is a tester/demo rehearsal.
5. Confirm positions and orders. If positions exist, follow strategy-defined close rules unless a separate emergency manual-close approval is recorded.
6. Freeze deployments: do not replace `.ex5` or `.set` until a post-incident review is complete.

## Verification

- Check no unauthorized Python runner is active.
- Check MT5 terminal state and process state.
- Check positions, orders, ledger, and deal history.
- Save journal/expert logs, screenshots if a GUI action was performed, and the final gate decision.

## Rollback

- Keep the last reviewed EX5/set package.
- Keep both stop flags in place until a deliberate resume decision removes them.
- Require a final live gate review before any real-money operation.
