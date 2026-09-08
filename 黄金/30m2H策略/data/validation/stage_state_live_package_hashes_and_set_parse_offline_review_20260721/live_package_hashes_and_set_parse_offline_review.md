# Live Package Hashes And Set Parse Offline Review

## Decision

- status: `pass_live_package_hashes_and_set_parse_offline_live_blocked`
- hash_rows: `2`
- InpSimMode: `false`
- blocker_failure_count: `0`
- ready_to_live_trade: `False`

## Checks

- `decision_status_collected`: `True` - live_package_hashes_and_set_parse_collected_offline_live_blocked
- `hash_rows_are_2`: `True` - rows=2
- `hashes_match_files`: `True` - mismatches=[]
- `hash_approval_present`: `True` - hash approval phrase
- `parsed_set_required_fields_present`: `True` - parsed set fields
- `set_approval_present`: `True` - set approval phrase
- `set_parse_is_offline`: `True` - offline_set_text_parse
- `inp_sim_mode_false_captured`: `True` - InpSimMode=false
- `export_flags_true`: `True` - export flags
- `no_mt5_runner_order_live_set_actions`: `True` - action flags
- `ready_to_live_trade_false`: `True` - ready flags
