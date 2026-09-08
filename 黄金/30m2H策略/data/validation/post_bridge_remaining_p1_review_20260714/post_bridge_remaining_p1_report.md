# Post-Bridge Remaining P1 Review 20260714

## Summary

| metric                                      | value                                    | note                                                                       |
| ------------------------------------------- | ---------------------------------------- | -------------------------------------------------------------------------- |
| signal_set_gap_effect_sum_no_fund_change    | 434.415919                               | Bridge reclassifies cause only; gap effect is unchanged.                   |
| time_axis_bridge_candidate_rows             | 6                                        | These are data/time-axis classification items, not direct Layer3/EA fixes. |
| time_axis_bridge_candidate_gap_sum          | -403.06                                  | Signed gap now isolated under bridge cause.                                |
| p1_signal_cases_after_excluding_bridge      | 49                                       | Remaining P1 signal-set cases that still need mapping/signal review.       |
| p1_matched_behavior_candidates_after_policy | 2                                        | python_mt5_0061/mt5_0045 is excluded from runtime behavior blockers.       |
| ea_price_side_repair_gate                   | closed                                   | No current post-bridge evidence requires EA Stage1/2 price-side change.    |
| largest_effective_signal_cause_by_abs_gap   | python_unmatched / unique_match_conflict | abs_gap_sum=751.257189                                                     |

## Signal Cause Summary

| side             | effective_cause_bucket               | rows | gap_sum_usd         | abs_gap_sum_usd |
| ---------------- | ------------------------------------ | ---- | ------------------- | --------------- |
| python_unmatched | unique_match_conflict                | 17   | 636.0202830000001   | 751.257189      |
| mt5_unmatched    | time_axis_bridge_candidate           | 6    | -403.06             | 638.08          |
| python_unmatched | mt5_family_or_time_drift             | 14   | 6.606995000000008   | 471.997677      |
| python_unmatched | python_signal_not_in_mt5_ledger      | 10   | 300.978641          | 433.584523      |
| mt5_unmatched    | layer3_reject                        | 4    | -112.96000000000001 | 294.26          |
| mt5_unmatched    | trigger_family_drift                 | 5    | -35.629999999999995 | 270.53          |
| mt5_unmatched    | mapping_conflict_or_profit_diff      | 3    | 141.59              | 141.59          |
| mt5_unmatched    | stage_execution_diff_or_family_drift | 1    | -123.92             | 123.92          |
| mt5_unmatched    | missing_python_candidate             | 1    | 75.19               | 75.19           |
| mt5_unmatched    | missing_raw_parent                   | 1    | -50.4               | 50.4            |

## Next Work Items

| work_type        | id                       | priority | side             | target_time         | effective_cause                      | gap_or_residual_$ | abs_$      | next_action                                    |
| ---------------- | ------------------------ | -------- | ---------------- | ------------------- | ------------------------------------ | ----------------- | ---------- | ---------------------------------------------- |
| signal_set       | python_mt5_0079          | P1       | python_unmatched | 2025-10-21 10:00:00 | unique_match_conflict                | 201.85136         | 201.85136  | resolve_unique_match_or_mapping_conflict       |
| signal_set       | python_mt5_0073          | P1       | python_unmatched | 2025-10-17 11:00:00 | unique_match_conflict                | 189.6211          | 189.6211   | resolve_unique_match_or_mapping_conflict       |
| signal_set       | mt5_0074                 | P1       | mt5_unmatched    | 2026-04-02 03:00:00 | layer3_reject                        | -171.9            | 171.9      | review_python_layer3_or_time_axis_after_bridge |
| signal_set       | python_mt5_0075          | P1       | python_unmatched | 2025-10-17 15:00:00 | unique_match_conflict                | 150.91695         | 150.91695  | resolve_unique_match_or_mapping_conflict       |
| signal_set       | python_mt5_0091          | P1       | python_unmatched | 2026-05-28 15:30:00 | python_signal_not_in_mt5_ledger      | 135.186066        | 135.186066 | review_python_only_signal_or_time_drift        |
| signal_set       | mt5_0048                 | P1       | mt5_unmatched    | 2025-09-02 17:30:00 | stage_execution_diff_or_family_drift | -123.92           | 123.92     | review_trigger_family_or_execution_boundary    |
| signal_set       | python_mt5_0065          | P1       | python_unmatched | 2025-04-22 16:30:00 | mt5_family_or_time_drift             | 115.714136        | 115.714136 | review_python_only_signal_or_time_drift        |
| signal_set       | python_mt5_0090          | P1       | python_unmatched | 2026-05-28 14:30:00 | python_signal_not_in_mt5_ledger      | 114.292288        | 114.292288 | review_python_only_signal_or_time_drift        |
| matched_residual | python_mt5_0009/mt5_0007 | P1       | matched          | 2020-03-17 04:00:00 | stop_distance_diff                   | 15.877926         | 15.877926  | review_stop_distance_or_fill_price             |
| matched_residual | python_mt5_0008/mt5_0004 | P1       | matched          | 2020-03-13 16:00:00 | exit_reason_diff                     | -14.81836         | 14.81836   | review_exit_reason_runtime_ordering            |

## Accounting-Only Matched Case

| py_trade_id     | mt5_trade_id | primary_diff_class     | runtime_residual_$ | runtime_abs_residual_$ | post_bridge_status                          | post_bridge_action_bucket             |
| --------------- | ------------ | ---------------------- | ------------------ | ---------------------- | ------------------------------------------- | ------------------------------------- |
| python_mt5_0061 | mt5_0045     | stage_exit_detail_diff | -55.8098           | 55.8098                | accounting_only_nonreliable_relaxed_mapping | exclude_from_runtime_behavior_blocker |

## Decision

- Bridge reclassification does not change the fund curve.
- `python_mt5_0061 / mt5_0045` is excluded from runtime behavior blockers because its selected match is non-reliable trigger-relaxed.
- The next code-facing work is mapping/signal review for remaining non-bridge P1 cases, not EA price-side behavior changes.
