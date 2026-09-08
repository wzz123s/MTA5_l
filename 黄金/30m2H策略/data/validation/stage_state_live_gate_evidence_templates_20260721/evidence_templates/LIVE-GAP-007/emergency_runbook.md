# LIVE-GAP-007 Evidence Template

- gate_item: `Emergency stop and rollback`
- priority: `P0`
- severity: `critical`
- template_status: `template_only`
- gate_status: `open`
- contains_real_credentials: `false`

## Required Fields

- `disable_auto_trading_steps`: `TEMPLATE_PLACEHOLDER`
- `close_position_steps`: `TEMPLATE_PLACEHOLDER`
- `rollback_steps`: `TEMPLATE_PLACEHOLDER`
- `owner`: `TEMPLATE_PLACEHOLDER`
- `backup_owner`: `TEMPLATE_PLACEHOLDER`

## Evidence

TEMPLATE_PLACEHOLDER

## Manual Confirmation

Operator confirms who can stop the system and how positions are handled.

## Fail Closed

Reject live start; RUNNER_STOP.flag alone is insufficient for real positions.
