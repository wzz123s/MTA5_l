# P0 Manual Template Fill Dry Run Review

## Decision

- status: `pass_p0_manual_dry_run_live_blocked`
- p0_manual_items: `10`
- dry_run_files_reviewed: `10`
- blocker_failure_count: `0`
- ready_to_live_trade: `False`

## Checks

- `decision_status_live_blocked`: `True` - p0_manual_dry_run_generated_live_blocked
- `expected_p0_manual_count_is_10`: `True` - expected=10
- `manifest_count_matches_expected`: `True` - manifest=10 expected=10
- `expected_keys_match_manifest`: `True` - missing=[] extra=[]
- `dry_run_files_exist`: `True` - missing=[]
- `dry_run_outputs_inside_dir`: `True` - outside=[]
- `all_required_fields_placeholder_filled`: `True` - field_failures=[]
- `source_templates_not_overwritten`: `True` - overwrite flags
- `no_secret_assignments_in_outputs`: `True` - secret assignment scan
- `all_gate_status_open`: `True` - gate statuses
- `all_ready_false`: `True` - ready flags
- `no_runner_mt5_live_set_actions`: `True` - action flags
