# LIVE-GAP-004 Evidence Template

- gate_item: `Credential externalization`
- priority: `P0`
- severity: `critical`
- template_status: `template_only`
- gate_status: `open`
- contains_real_credentials: `false`

## Required Fields

- `secret_source`: `TEMPLATE_PLACEHOLDER`
- `allowed_runtime`: `TEMPLATE_PLACEHOLDER`
- `forbidden_locations`: `TEMPLATE_PLACEHOLDER`
- `operator`: `TEMPLATE_PLACEHOLDER`

## Evidence

TEMPLATE_PLACEHOLDER

## Manual Confirmation

Operator confirms the live terminal/session does not expose credentials in logs or generated reports.

## Fail Closed

Do not run Python runner or any live startup using source-stored credentials.
