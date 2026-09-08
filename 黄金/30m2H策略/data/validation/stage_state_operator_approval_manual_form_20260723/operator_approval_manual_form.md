# Operator Approval Manual Form

Generated: 2026-07-23T20:54:38

## Current Gate State

- Latest final gate status: `final_live_gate_approval_preconditions_satisfied_loading_package_pending`
- Operator alias ready: `True`
- Approval booleans: `10 / 10`
- Ready to live trade: `false`

## How To Use

This form is only for non-secret operator approval. Do not write full account numbers, passwords, investor passwords, API tokens, or secret keys.

The next gate can only be rerun after:

1. `operator_alias` is changed from `manual_pending` to a non-secret alias.
2. Each genuinely approved item below is set to `true`.
3. The final live gate review is rerun.

## Approval Items

- [ ] `LIVE-GAP-001_live_trading_approval`: 当前 `True`，批准后应为 `true`
- [ ] `LIVE-GAP-002_live_package_manifest_release_approval`: 当前 `True`，批准后应为 `true`
- [ ] `LIVE-GAP-003_InpSimMode_false_loading_approval`: 当前 `True`，批准后应为 `true`
- [ ] `LIVE-GAP-004_secret_externalization_approval`: 当前 `True`，批准后应为 `true`
- [ ] `LIVE-GAP-005_MT5_EA_only_order_path_approval`: 当前 `True`，批准后应为 `true`
- [ ] `LIVE-GAP-006_live_risk_policy_approval`: 当前 `True`，批准后应为 `true`
- [ ] `LIVE-GAP-008_watched_alert_channel_confirmed`: 当前 `True`，批准后应为 `true`
- [ ] `LIVE-GAP-008_operator_reconciliation_confirmed`: 当前 `True`，批准后应为 `true`
- [ ] `LIVE-GAP-009_account_spec_intended_context_confirmed`: 当前 `True`，批准后应为 `true`
- [ ] `LIVE-GAP-010_nonprod_rehearsal_alert_emergency_acceptance`: 当前 `True`，批准后应为 `true`

## Signoff Requirements

- `SIGN-001` / `LIVE-GAP-001`: explicitly approve demo/live execution scope；最低证据：operator approval record with account alias, symbol, balance cap, leverage, and execution mode
- `SIGN-002` / `LIVE-GAP-002`: approve exact EA package and deployment manifest；最低证据：EX5/MQ5 path, compile log, set file/inputs, manifest, and release timestamp
- `SIGN-003` / `LIVE-GAP-003`: approve InpSimMode=false loading；最低证据：operator confirms live set transition from SIM_ONLY to execution mode
- `SIGN-004` / `LIVE-GAP-004`: approve credential externalization；最低证据：no credentials in repo outputs; any required login handled outside tracked files
- `SIGN-005` / `LIVE-GAP-005`: approve MT5 EA-only production order path；最低证据：operator confirms no Python runner order placement and no external order source
- `SIGN-006` / `LIVE-GAP-006`: approve live numeric risk policy；最低证据：operator accepts risk guard limits, max lot behavior, balance cap, and fail-closed rules
- `SIGN-007` / `LIVE-GAP-008`: sign watched alert and reconciliation confirmation；最低证据：watched alert channel confirmed and operator reconciliation confirmed
- `SIGN-008` / `LIVE-GAP-009`: confirm account/spec snapshot is intended execution context；最低证据：operator confirms account alias, server, symbol, balance cap, leverage, and no unexpected exposure
- `SIGN-009` / `LIVE-GAP-010`: accept non-production rehearsal alert/emergency evidence；最低证据：operator accepts guard rehearsal, alert handling, emergency stop behavior, and ledger/deal reconciliation

## Safe Reply Shape

You can reply with a short non-secret confirmation, for example:

```text
operator_alias: owner_local
批准以上 10 个 approval boolean，继续 rerun final live gate review。
```

This does not authorize removing stop flags or loading the EA. Those remain separate steps after the gate review.
