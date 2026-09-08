# Pending Auto Evidence Prerequisite Plan

## Decision

- status: `pending_auto_prerequisites_drafted_live_blocked`
- pending_auto_items: `3`
- p0_items: `2`
- p1_items: `1`
- ready_to_live_trade: `False`

## Boundary

- This plan does not collect the pending auto evidence.
- No MT5 access, runner execution, order placement, active live set parsing, or live package hash is performed.
- Each item remains blocked until its approval phrase and manual prerequisite are provided.

## Pending Items

- `live_package_hashes.csv`: `offline_hash_after_live_package_approval`; prerequisite: approved live package manifest and release reviewer confirmation.
- `parsed_live_set_template.json`: `offline_set_parse_after_transition_approval`; prerequisite: explicit sim-mode transition approval and reviewed inactive set template.
- `broker_symbol_spec.csv`: `read_only_mt5_spec_after_user_approval`; prerequisite: explicit user approval for read-only MT5 symbol/account-spec query.

## Steps

- `live_package_hashes.csv` `APPROVE-001`: User/release reviewer approves the live package manifest paths.
- `live_package_hashes.csv` `VERIFY-001`: Verify only approved manifest paths are in scope.
- `live_package_hashes.csv` `COLLECT-001`: After approval only, calculate sha256 hashes offline.
- `live_package_hashes.csv` `REVIEW-001`: Review hash CSV and keep live gate open until all live gates close together.
- `parsed_live_set_template.json` `APPROVE-001`: User/release reviewer approves offline parsing of an inactive set template.
- `parsed_live_set_template.json` `VERIFY-001`: Verify the set template is not loaded into MT5 and not attached to a chart.
- `parsed_live_set_template.json` `COLLECT-001`: After approval only, parse requested fields from the template file offline.
- `parsed_live_set_template.json` `REVIEW-001`: Review parsed fields and keep live gate open until all live gates close together.
- `broker_symbol_spec.csv` `APPROVE-001`: User explicitly approves read-only MT5 symbol/spec query with no order actions.
- `broker_symbol_spec.csv` `VERIFY-001`: Verify runner is not executed and orders are disabled before any query.
- `broker_symbol_spec.csv` `COLLECT-001`: After approval only, collect read-only symbol/account spec fields.
- `broker_symbol_spec.csv` `REVIEW-001`: Review spec CSV and keep live gate open until all live gates close together.
