# Live Trade Gate Checklist Draft

## Decision

- status: `draft_complete`
- checklist_item_count: `10`
- critical_item_count: `7`
- major_item_count: `3`
- ready_to_live_trade: `False`

## Boundary

- This is a checklist draft only.
- It does not enable live trading.
- It does not authorize `InpSimMode=false`.
- It does not authorize `auto_trade/auto_trader.py`.

## Checklist

### LIVE-GAP-001 - Live trading approval record

- priority: `P0`
- severity: `critical`
- closure condition: A signed and dated approval record exists and explicitly names account, symbol, max risk, allowed runner, and rollback owner.
- evidence required: live_trade_approval_record.md with approval_id, approver, date, account alias, symbol, max risk, and scope.
- script check: Verify approval file exists, required fields are non-empty, and approval_scope is live-trade-gate-only.
- manual confirmation: Human approver must confirm this is not inherited from SIM_ONLY readiness.
- fail closed: Keep ready_to_live_trade=false and keep InpSimMode=true.

### LIVE-GAP-002 - Independent live package audit

- priority: `P0`
- severity: `critical`
- closure condition: Live EX5, live set, startup config, deployment path, and SHA256 hashes are reviewed independently from SIM_ONLY artifacts.
- evidence required: live_package_manifest.json, live_package_hashes.csv, compile log, deployed path proof.
- script check: Verify live artifact paths exist, hashes match, compile log has 0 errors/warnings, and package is not SIM_ONLY.
- manual confirmation: Reviewer confirms the live package is intentionally separate from SIM_ONLY package.
- fail closed: Use only SIM_ONLY package; do not attach a live package.

### LIVE-GAP-003 - InpSimMode=false gate

- priority: `P0`
- severity: `critical`
- closure condition: A dedicated gate explicitly authorizes changing InpSimMode from true to false after all live package and risk gates pass.
- evidence required: sim_mode_transition_approval.md and parsed live set showing InpSimMode=false.
- script check: Verify all prior gate statuses pass before accepting InpSimMode=false.
- manual confirmation: Approver types exact phrase: APPROVE_INPSIMMODE_FALSE.
- fail closed: Abort live gate and continue with InpSimMode=true.

### LIVE-GAP-004 - Credential externalization

- priority: `P0`
- severity: `critical`
- closure condition: No source file contains live account/password values; live credentials are loaded from approved external secret storage.
- evidence required: secret_policy.md, .env.example without real values, credential_scan_report.csv.
- script check: Scan blocked source files for hardcoded account/password patterns and verify no real credential values are stored in repository files.
- manual confirmation: Operator confirms the live terminal/session does not expose credentials in logs or generated reports.
- fail closed: Do not run Python runner or any live startup using source-stored credentials.

### LIVE-GAP-005 - Approved production runner path

- priority: `P0`
- severity: `critical`
- closure condition: The live execution path is declared as EA-only or audited runner-only, with one source of orders and no stale Python runner.
- evidence required: production_runner_decision.md and runner_source_audit.csv.
- script check: Verify auto_trade/auto_trader.py remains blocked unless separately audited and approved.
- manual confirmation: Reviewer confirms exactly one live order path is enabled.
- fail closed: Keep auto_trade/auto_trader.py blocked and keep live trading disabled.

### LIVE-GAP-006 - Live risk policy

- priority: `P0`
- severity: `critical`
- closure condition: Live max daily loss, max drawdown, max orders, max spread, margin guard, lot caps, and balance cap are defined.
- evidence required: live_risk_policy.json with numeric limits and fail-closed thresholds.
- script check: Parse policy and verify every numeric limit is present, positive, and stricter than broad account defaults.
- manual confirmation: Operator confirms policy matches the intended account size and leverage.
- fail closed: Reject live start if any risk value is missing, zero where not allowed, or too broad.

### LIVE-GAP-007 - Emergency stop and rollback

- priority: `P0`
- severity: `critical`
- closure condition: Emergency disable and emergency close-position procedure is documented and tested outside real-money mode.
- evidence required: emergency_runbook.md and emergency_rehearsal_report.csv.
- script check: Verify runbook and rehearsal report exist, and rehearsal status is pass.
- manual confirmation: Operator confirms who can stop the system and how positions are handled.
- fail closed: Reject live start; RUNNER_STOP.flag alone is insufficient for real positions.

### LIVE-GAP-008 - Live monitoring, alerts, and reconciliation

- priority: `P1`
- severity: `major`
- closure condition: Alerts and reconciliation are defined for order, position, P/L, margin, disconnect, stale tick, and ledger mismatch.
- evidence required: live_monitoring_policy.json and reconciliation_checklist.csv.
- script check: Verify every alert type has channel, threshold, owner, and fail-closed action.
- manual confirmation: Operator confirms alert channel is watched during live window.
- fail closed: Do not start live without watched alerts.

### LIVE-GAP-009 - Broker/account/spec confirmation

- priority: `P1`
- severity: `major`
- closure condition: Allowed account, leverage, symbol spec, contract size, margin, min lot, step lot, spread policy, and balance cap are recorded.
- evidence required: live_account_spec_snapshot.json and broker_symbol_spec.csv.
- script check: Verify account/spec files exist and symbol is XAUUSDm with expected lot and margin fields.
- manual confirmation: Operator confirms this is the intended account and not a different terminal profile.
- fail closed: Reject live gate if account/spec is stale or missing.

### LIVE-GAP-010 - Non-production order-placement rehearsal

- priority: `P1`
- severity: `major`
- closure condition: A demo or tester order-placement rehearsal validates open/close, SL/TP, ledger, alerts, and emergency handling.
- evidence required: nonprod_order_rehearsal_report.md, rehearsal_ledger.csv, rehearsal_alert_log.csv.
- script check: Verify rehearsal report status is pass and all expected order lifecycle events are present.
- manual confirmation: Reviewer confirms rehearsal did not use real money.
- fail closed: Do not enable real-money order placement.
