# Live Trade Readiness Gap Audit

## Decision

- status: `blocked`
- audit_completed: `True`
- ready_to_continue_sim_only_monitoring: `True`
- ready_to_live_trade: `False`
- open_gap_count: `10`
- critical_gap_count: `7`
- current_positions_count: `0`
- current_orders_count: `0`

## Summary

- SIM_ONLY monitoring is ready to continue.
- Live trading is blocked by design in this audit.
- The existing Python auto trader remains blocked and must not be used as the live runner.
- A separate live package, live risk policy, credential policy, emergency handling, and manual approval are still required.

## Open Gaps

- `LIVE-GAP-001` [critical] Explicit human approval for live trading | current: No live approval record; latest gates keep ready_to_live_trade=false | action: Create a signed/dated approval gate before any live enablement.
- `LIVE-GAP-002` [critical] Separate live package with reviewed EX5, set file, hashes, and deployment path | current: Current approved package is SIM_ONLY; live config is absent | action: Build a live package audit that does not reuse SIM_ONLY approval as live approval.
- `LIVE-GAP-003` [critical] Independent gate before `InpSimMode=false` | current: SIM_ONLY set has InpSimMode=true; main frozen set has InpSimMode=false | action: Require a dedicated live gate and manual confirmation before changing sim mode.
- `LIVE-GAP-004` [critical] Externalized credential and secret handling | current: Hardcoded credential pattern files detected: 3 | action: Move credentials out of source and verify no live runner prints or stores secrets.
- `LIVE-GAP-005` [critical] Approved production runner path | current: Current approved runner is SIM_ONLY monitor; `auto_trade/auto_trader.py` remains blocked | action: Define whether live execution is EA-only or a new audited runner; do not use stale Python runner.
- `LIVE-GAP-006` [critical] Live risk limits and account guardrails | current: Current config sets max real positions/orders/loss to 0 | action: Define max daily loss, max drawdown, max orders, max spread, margin guard, and lot caps.
- `LIVE-GAP-007` [critical] Emergency stop and rollback plan | current: RUNNER_STOP.flag stops bounded monitor; it is not an emergency close-position mechanism | action: Create and test an emergency close/disable procedure on a non-live environment.
- `LIVE-GAP-008` [major] Live monitoring, alerts, and reconciliation | current: SIM_ONLY observation exists; live alerting/reconciliation is not defined | action: Define alerts for order, position, P/L, margin, disconnect, stale tick, and ledger mismatch.
- `LIVE-GAP-009` [major] Broker/account/spec confirmation | current: Current audit does not validate live account type, leverage, contract size, margin, or balance limit | action: Record allowed account, leverage, symbol spec, balance cap, and market-hours policy.
- `LIVE-GAP-010` [major] Non-production order-placement rehearsal | current: Only SIM_ONLY ledger-zero runs have passed; no demo/live-like tiny-order rehearsal is approved | action: Run a separate demo or tester order-placement gate before any real-money enablement.

## Not Approved

- Do not run `auto_trade/auto_trader.py`.
- Do not set `InpSimMode=false`.
- Do not enable live trading.
- Do not treat SIM_ONLY observation pass as live approval.
