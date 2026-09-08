# LIVE-GAP-005 P0 Manual Evidence Dry Run

- dry_run_status: `redacted_placeholder_only`
- priority: `P0`
- source_file: `production_runner_decision.md`
- gate_status: `open`
- ready_to_live_trade: `false`
- contains_real_credentials: `false`
- generated_at: `2026-07-21T12:21:13`

## Required Fields

- `runner_mode`: `PENDING_RUNNER_MODE`
- `order_source_count`: `PENDING_ORDER_SOURCE_COUNT`
- `blocked_runner_files`: `PENDING_BLOCKED_RUNNER_FILES`
- `approver`: `PENDING_APPROVER`

## Evidence

PENDING_MANUAL_EVIDENCE_REDACTED_DRY_RUN_ONLY

## Confirmation Boundary

- confirmer: `user plus reviewer`
- prerequisite_source: `runner architecture decision`
- next_allowed_action: `fill the template with redacted/manual confirmation data only`

## Forbidden Content

do not approve auto_trade/auto_trader.py by default; real-money order placement, live chart attachment, or live set switching

## Fail Closed

Keep all live gates open and keep ready_to_live_trade=false.
