# Manual Evidence Prerequisite Plan Review

## Decision

- status: `pass_manual_prerequisites_live_blocked`
- remaining_prerequisite_items: `20`
- blocker_failure_count: `0`
- ready_to_live_trade: `False`

## Checks

- `decision_status_live_blocked`: `True` - manual_prerequisites_drafted_live_blocked
- `remaining_count_is_20`: `True` - rows=20 decision=20
- `expected_remaining_keys_match`: `True` - missing=[] extra=[]
- `manual_count_is_13`: `True` - manual rows
- `rehearsal_count_is_4`: `True` - rehearsal rows
- `pending_auto_count_is_3`: `True` - pending auto rows
- `all_completion_states_open`: `True` - completion states
- `all_gate_status_open`: `True` - gate statuses
- `all_ready_false`: `True` - ready flags
- `no_collected_auto_reincluded`: `True` - collected auto keys excluded
- `forbidden_content_present`: `True` - forbidden content fields
- `next_allowed_action_present`: `True` - next allowed action fields
- `confirmer_present`: `True` - confirmer fields
- `no_secret_assignments_in_outputs`: `True` - secret assignment scan
