# LIVE-GAP-006 Evidence Template

- gate_item: `Live risk policy`
- priority: `P0`
- severity: `critical`
- template_status: `template_only`
- gate_status: `open`
- contains_real_credentials: `false`

## Required Fields

- `account_size`: `TEMPLATE_PLACEHOLDER`
- `leverage`: `TEMPLATE_PLACEHOLDER`
- `operator`: `TEMPLATE_PLACEHOLDER`
- `confirmed_at`: `TEMPLATE_PLACEHOLDER`

## Evidence

TEMPLATE_PLACEHOLDER

## Manual Confirmation

Operator confirms policy matches the intended account size and leverage.

## Fail Closed

Reject live start if any risk value is missing, zero where not allowed, or too broad.
