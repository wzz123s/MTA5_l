# LIVE-GAP-007 P0 Manual Evidence Dry Run

- dry_run_status: `redacted_placeholder_only`
- priority: `P0`
- source_file: `emergency_runbook.md`
- gate_status: `open`
- ready_to_live_trade: `false`
- contains_real_credentials: `false`
- generated_at: `2026-07-21T12:21:13`

## Required Fields

- `disable_auto_trading_steps`: `PENDING_DISABLE_AUTO_TRADING_STEPS`
- `close_position_steps`: `PENDING_CLOSE_POSITION_STEPS`
- `rollback_steps`: `PENDING_ROLLBACK_STEPS`
- `owner`: `PENDING_OWNER`
- `backup_owner`: `PENDING_BACKUP_OWNER`

## Evidence

PENDING_MANUAL_EVIDENCE_REDACTED_DRY_RUN_ONLY

## Confirmation Boundary

- confirmer: `user plus operator`
- prerequisite_source: `documented emergency runbook`
- next_allowed_action: `fill the template with redacted/manual confirmation data only`

## Forbidden Content

do not rely only on RUNNER_STOP.flag; real-money order placement, live chart attachment, or live set switching

## Fail Closed

Keep all live gates open and keep ready_to_live_trade=false.
