# Runtime Stage Exit Integrated Alignment

## Scope

- Base cases: `python_runtime_stage_exit_prototype_20260714\runtime_stage_input_cases.csv`
- Enhanced ledger: `ea_stage2_trail_ledger_full_20260714\30m2H_strategy_trade_ledger.csv`
- Evidence layers: M30 replay, M15 refine, Stage2 trail refine, remaining Stage2 trail ledger evidence.

## Key Counts

- Stage exit detail trades before runtime integration: `18`
- Priority 1 stage rows before runtime integration: `25`
- Remaining Priority 1 blockers after runtime integration: `3`
- Priority 1 rows still requiring strict tick/journal replay: `16`

## Trade Status

| trade_runtime_status                          | trades |
| --------------------------------------------- | ------ |
| has_priority1_blocker                         | 3      |
| no_priority1_stage                            | 16     |
| priority1_explained_but_strict_replay_pending | 6      |
| priority1_resolved                            | 4      |

## Stage Summary

| runtime_priority | stage | runtime_resolution_level            | runtime_residual_class                                      | remaining_priority1_blocker | requires_strict_tick_replay | rows |
| ---------------- | ----- | ----------------------------------- | ----------------------------------------------------------- | --------------------------- | --------------------------- | ---- |
| 1                | 1     | confirmed_m15_bar                   | m15_mt5_sl_before_python_event                              | False                       | False                       | 1    |
| 1                | 1     | confirmed_m30_bar                   | m30_broker_sl_first                                         | False                       | False                       | 1    |
| 1                | 1     | plausible_needs_tick                | m15_mt5_sl_before_python_event                              | False                       | True                        | 3    |
| 1                | 1     | plausible_needs_tick                | m30_broker_sl_first                                         | False                       | True                        | 1    |
| 1                | 1     | unresolved                          | python_event_before_mt5_sl_session_or_close_retry_candidate | True                        | False                       | 1    |
| 1                | 2     | confirmed_ledger                    | confirmed_initial_sl_after_open_by_deal_ledger              | False                       | True                        | 6    |
| 1                | 2     | confirmed_ledger                    | enhanced_stage2_ledger_initial_sl                           | False                       | False                       | 2    |
| 1                | 2     | confirmed_ledger                    | enhanced_stage2_ledger_trail_sl                             | False                       | False                       | 2    |
| 1                | 2     | confirmed_ledger                    | resolved_as_trail_sl_by_ea_ledger                           | False                       | False                       | 2    |
| 1                | 3     | plausible_needs_stage3_cross_replay | stage3_broker_sl_seen_cross_chronology_pending              | False                       | True                        | 3    |
| 1                | 3     | plausible_needs_tick                | m30_broker_sl_first                                         | False                       | True                        | 1    |
| 1                | 3     | unresolved                          | expert_close_after_broker_sl_candidate_needs_journal        | True                        | True                        | 1    |
| 1                | 3     | unresolved                          | runtime_model_contradicts_mt5_sl                            | True                        | True                        | 1    |
| 2                | 1     | out_of_scope                        | not_priority1_reprocessed                                   | False                       | False                       | 3    |
| 2                | 2     | out_of_scope                        | not_priority1_reprocessed                                   | False                       | False                       | 3    |
| 2                | 3     | out_of_scope                        | not_priority1_reprocessed                                   | False                       | False                       | 12   |
| 3                | 1     | out_of_scope                        | not_priority1_reprocessed                                   | False                       | False                       | 19   |
| 3                | 2     | out_of_scope                        | not_priority1_reprocessed                                   | False                       | False                       | 14   |
| 3                | 3     | out_of_scope                        | not_priority1_reprocessed                                   | False                       | False                       | 11   |

## Priority 1 Case View

| case_id                | stage | exit_relation                      | sign_pair  | runtime_resolution_level            | runtime_residual_class                                      | remaining_priority1_blocker | requires_strict_tick_replay |
| ---------------------- | ----- | ---------------------------------- | ---------- | ----------------------------------- | ----------------------------------------------------------- | --------------------------- | --------------------------- |
| runtime_stage_case_001 | 2     | py_cross_mt5_sl                    | loss->loss | confirmed_ledger                    | confirmed_initial_sl_after_open_by_deal_ledger              | False                       | True                        |
| runtime_stage_case_002 | 3     | py_cross_mt5_sl                    | loss->loss | plausible_needs_tick                | m30_broker_sl_first                                         | False                       | True                        |
| runtime_stage_case_003 | 1     | py_tp_mt5_sl                       | win->loss  | confirmed_m30_bar                   | m30_broker_sl_first                                         | False                       | False                       |
| runtime_stage_case_004 | 2     | py_forced_mt5_sl                   | win->loss  | confirmed_ledger                    | enhanced_stage2_ledger_initial_sl                           | False                       | False                       |
| runtime_stage_case_005 | 2     | py_cross_mt5_sl                    | loss->loss | confirmed_ledger                    | confirmed_initial_sl_after_open_by_deal_ledger              | False                       | True                        |
| runtime_stage_case_006 | 2     | py_cross_mt5_sl                    | loss->win  | confirmed_ledger                    | enhanced_stage2_ledger_trail_sl                             | False                       | False                       |
| runtime_stage_case_007 | 1     | py_tp_mt5_sl                       | win->loss  | plausible_needs_tick                | m30_broker_sl_first                                         | False                       | True                        |
| runtime_stage_case_008 | 2     | both_stop_or_trail                 | win->loss  | confirmed_ledger                    | confirmed_initial_sl_after_open_by_deal_ledger              | False                       | True                        |
| runtime_stage_case_009 | 3     | both_cross_but_price_time_may_diff | win->loss  | unresolved                          | expert_close_after_broker_sl_candidate_needs_journal        | True                        | True                        |
| runtime_stage_case_010 | 2     | py_cross_mt5_sl                    | loss->win  | confirmed_ledger                    | resolved_as_trail_sl_by_ea_ledger                           | False                       | False                       |
| runtime_stage_case_011 | 1     | py_tp_mt5_sl                       | win->loss  | plausible_needs_tick                | m15_mt5_sl_before_python_event                              | False                       | True                        |
| runtime_stage_case_012 | 2     | py_forced_mt5_sl                   | win->loss  | confirmed_ledger                    | confirmed_initial_sl_after_open_by_deal_ledger              | False                       | True                        |
| runtime_stage_case_013 | 3     | py_cross_mt5_sl                    | win->loss  | plausible_needs_stage3_cross_replay | stage3_broker_sl_seen_cross_chronology_pending              | False                       | True                        |
| runtime_stage_case_014 | 3     | py_cross_mt5_sl                    | win->loss  | unresolved                          | runtime_model_contradicts_mt5_sl                            | True                        | True                        |
| runtime_stage_case_015 | 1     | py_tp_mt5_sl                       | win->loss  | plausible_needs_tick                | m15_mt5_sl_before_python_event                              | False                       | True                        |
| runtime_stage_case_016 | 2     | both_stop_or_trail                 | win->loss  | confirmed_ledger                    | confirmed_initial_sl_after_open_by_deal_ledger              | False                       | True                        |
| runtime_stage_case_017 | 3     | py_cross_mt5_sl                    | win->loss  | plausible_needs_stage3_cross_replay | stage3_broker_sl_seen_cross_chronology_pending              | False                       | True                        |
| runtime_stage_case_018 | 1     | py_tp_mt5_sl                       | win->loss  | plausible_needs_tick                | m15_mt5_sl_before_python_event                              | False                       | True                        |
| runtime_stage_case_019 | 2     | both_stop_or_trail                 | win->loss  | confirmed_ledger                    | confirmed_initial_sl_after_open_by_deal_ledger              | False                       | True                        |
| runtime_stage_case_020 | 1     | py_tp_mt5_sl                       | win->loss  | confirmed_m15_bar                   | m15_mt5_sl_before_python_event                              | False                       | False                       |
| runtime_stage_case_021 | 2     | py_forced_mt5_sl                   | win->loss  | confirmed_ledger                    | enhanced_stage2_ledger_initial_sl                           | False                       | False                       |
| runtime_stage_case_022 | 3     | py_cross_mt5_sl                    | win->loss  | plausible_needs_stage3_cross_replay | stage3_broker_sl_seen_cross_chronology_pending              | False                       | True                        |
| runtime_stage_case_023 | 2     | py_forced_mt5_sl                   | win->loss  | confirmed_ledger                    | resolved_as_trail_sl_by_ea_ledger                           | False                       | False                       |
| runtime_stage_case_024 | 1     | py_tp_mt5_sl                       | win->loss  | unresolved                          | python_event_before_mt5_sl_session_or_close_retry_candidate | True                        | False                       |
| runtime_stage_case_025 | 2     | py_forced_mt5_sl                   | win->loss  | confirmed_ledger                    | enhanced_stage2_ledger_trail_sl                             | False                       | False                       |

## Interpretation

- `remaining_priority1_blocker=False` means the row no longer blocks current Stage exit/PnL alignment.
- `requires_strict_tick_replay=True` means the row is explained enough for current classification, but raw ticks or tester journal would still be needed for strict event-order replay.
- Stage2 rows are now primarily resolved by the enhanced EA ledger instead of M30/M15 approximation.
- Remaining blockers are reserved for session/journal style cases where broker SL evidence and MT5 deal reason/time still conflict.

## Output Files

- `runtime_stage_exit_integrated_alignment.csv`
- `runtime_stage_exit_integrated_stage_summary.csv`
- `runtime_stage_exit_integrated_trade_summary.csv`
