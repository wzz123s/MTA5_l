# Broker Symbol Spec Read-only Review

## Decision

- status: `pass_broker_symbol_spec_read_only_live_blocked`
- symbol: `XAUUSDm`
- broker_symbol_spec_rows: `1`
- blocker_failure_count: `0`
- ready_to_live_trade: `False`

## Checks

- `decision_status_collected`: `True` - broker_symbol_spec_collected_read_only_live_blocked
- `row_count_is_1`: `True` - rows=1
- `symbol_is_expected`: `True` - symbol=XAUUSDm
- `required_fields_present`: `True` - required=['symbol', 'contract_size', 'min_lot', 'lot_step', 'margin_initial', 'digits', 'spread_policy']
- `approval_phrase_present`: `True` - approval phrase
- `read_only_collection_mode`: `True` - read_only_symbol_info
- `mt5_initialized_only_for_read`: `True` - mt5 initialized flag
- `terminal_process_not_spawned`: `True` - before=1 after=1
- `no_runner_order_live_set_actions`: `True` - action flags
- `no_secret_assignments_in_outputs`: `True` - secret assignment scan
- `gate_status_open`: `True` - gate status
- `ready_to_live_trade_false`: `True` - ready flags
