# Live Gate Auto-safe Evidence Collection

## Decision

- status: `auto_safe_evidence_collected_live_blocked`
- auto_items_total: `5`
- auto_items_collected: `2`
- auto_items_pending: `3`
- ready_to_live_trade: `False`
- credential_values_output: `False`
- runner_executed: `False`

## Boundary

- Only credential scan and runner source audit were collected.
- Credential values are not output.
- Runner files are not executed.
- Live package, live set parsing, and broker spec collection remain pending.

## Auto Items

- `live_package_hashes.csv`: `pending_manual_prerequisite` - Skipped by auto-safe policy; requires live package/live set/broker-spec approval first.
- `parsed_live_set_template.json`: `pending_manual_prerequisite` - Skipped by auto-safe policy; requires live package/live set/broker-spec approval first.
- `credential_scan_report.csv`: `collected` - Static scan collected with values redacted.
- `runner_source_audit.csv`: `collected` - Static source audit collected; no runner executed.
- `broker_symbol_spec.csv`: `pending_manual_prerequisite` - Skipped by auto-safe policy; requires live package/live set/broker-spec approval first.
