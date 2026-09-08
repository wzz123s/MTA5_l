# P1 Manual Template Fill Dry Run Review

## Decision

- status: `pass_p1_manual_dry_run_live_blocked`
- p1_manual_items: `3`
- dry_run_files_reviewed: `3`
- blocker_failure_count: `0`
- ready_to_live_trade: `False`

## Checks

- `decision_status_live_blocked`: `True` - p1_manual_dry_run_generated_live_blocked
- `expected_p1_manual_count_is_3`: `True` - expected=3
- `manifest_count_matches_expected`: `True` - manifest=3 expected=3
- `expected_keys_match_manifest`: `True` - missing=[] extra=[]
- `dry_run_files_exist`: `True` - missing=[]
- `dry_run_outputs_inside_dir`: `True` - outside=[]
- `all_required_fields_placeholder_filled`: `True` - field_failures=[]
- `file_type_counts`: `True` - json/csv counts
- `source_templates_not_overwritten`: `True` - overwrite flags
- `no_secret_assignments_in_outputs`: `True` - secret assignment scan
- `all_gate_status_open`: `True` - gate statuses
- `all_ready_false`: `True` - ready flags
- `no_runner_mt5_order_live_set_actions`: `True` - action flags
