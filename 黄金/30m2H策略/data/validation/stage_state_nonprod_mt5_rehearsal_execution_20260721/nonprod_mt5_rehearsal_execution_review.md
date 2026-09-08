# Non-production MT5 Rehearsal Execution Review

## Decision

- status: `nonprod_mt5_rehearsal_passed`
- nonprod_rehearsal_passed: `True`
- initial_deposit: `2000`
- final_balance: `2043.70`
- profit: `43.7`
- signal_rows: `1180`
- trade_ledger_rows: `15`
- deal_history_rows: `30`
- sl_rows: `10`
- expert_exit_rows: `5`
- min_lot: `0.01`
- max_lot: `0.05`
- ready_to_live_trade: `False`

## Boundary

- MT5 Strategy Tester executed the EA in a non-production rehearsal window.
- Logs were copied in redacted form.
- The Python runner was not executed.
- This does not approve real-money live trading.

## Lifecycle Metrics

- `final_balance`: `2043.70`
- `initial_deposit`: `2000`
- `net_profit_sum_from_ledger`: `43.7`
- `signal_rows`: `1180`
- `trade_ledger_rows`: `15`
- `deal_history_rows`: `30`
- `min_lot`: `0.01`
- `max_lot`: `0.05`
- `sl_rows`: `10`
- `expert_exit_rows`: `5`
- `deal_entry_in_rows`: `15`
- `deal_entry_out_rows`: `15`
- `local_exit_reason_deal_exit`: `10`
- `local_exit_reason_stage1_tp`: `2`
- `local_exit_reason_stage2_forced`: `1`
- `local_exit_reason_stage3_cross_exit`: `2`
- `stage_1`: `5`
- `stage_2`: `5`
- `stage_3`: `5`
- `deal_reason_EXPERT`: `5`
- `deal_reason_SL`: `10`

## Checks

- `package_ready`: `True` - actual `True`, expected `True`
- `demo_ready_not_live`: `True` - actual `nonprod=True live=False`, expected `nonprod true, live false`
- `terminal_loaded_expected_ini`: `True` - actual `seen`, expected `seen`
- `terminal_tester_started`: `True` - actual `seen`, expected `seen`
- `terminal_tester_finished_success`: `True` - actual `seen`, expected `seen`
- `terminal_shutdown_code_0`: `True` - actual `seen`, expected `seen`
- `agent_test_passed`: `True` - actual `seen`, expected `seen`
- `final_balance_2043_70`: `True` - actual `2043.70`, expected `2043.70`
- `signals_export_rows_1180`: `True` - actual `1180`, expected `1180`
- `trade_ledger_has_rows`: `True` - actual `15`, expected `> 0`
- `deal_history_has_rows`: `True` - actual `30`, expected `> 0`
- `deal_history_has_in_and_out`: `True` - actual `IN=15 OUT=15`, expected `IN>0 and OUT>0`
- `sl_and_expert_exits_present`: `True` - actual `SL=10 EXPERT=5`, expected `SL>0 and EXPERT>0`
- `stages_1_2_3_present`: `True` - actual `stage_counts={'1': 5, '3': 5, '2': 5}`, expected `1/2/3 present`
- `lots_within_strategy_cap`: `True` - actual `min=0.01 max=0.05`, expected `0.01 <= lots <= 10.0`
- `net_profit_matches_balance_delta`: `True` - actual `43.7`, expected `43.7`
- `no_python_runner_invocation`: `True` - actual `not found`, expected `not found`
- `report_xml_optional`: `False` - actual `missing`, expected `exists`
- `redacted_logs_no_full_account`: `True` - actual `False`, expected `False`
