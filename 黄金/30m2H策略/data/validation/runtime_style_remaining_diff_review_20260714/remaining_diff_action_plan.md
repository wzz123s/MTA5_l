# Runtime Style Remaining Diff Review 20260714

## Scope

- Starts after `runtime_style_dynamic_risk_alignment_20260714`.
- Separates residual into matched non-Stage-exit PnL residual and signal-set drift.
- Uses the same `bidirectional_m30_m15_90_profit20` selected-match policy as matched profit/exit diff.
- Runtime-adjusted Python PnL is used for Python-unmatched impact.

## Overall Components

| metric                              | value       | note                                                                                 |
| ----------------------------------- | ----------- | ------------------------------------------------------------------------------------ |
| runtime_python_mt5_total_profit     | 3788.503976 | Sum of runtime_adjusted_total_$ over all Python-MT5 trades.                          |
| mt5_reference_profit_from_mapping   | 3311.35     | Selected-policy matched MT5 profit plus selected-policy MT5-unmatched ledger profit. |
| selected_policy_matched_mt5_profit  | 2802.16     | MT5 profit over bidirectional_m30_m15_90_profit20 selected matches.                  |
| direct_runtime_gap_python_minus_mt5 | 477.153976  | Runtime Python-MT5 total profit minus reconstructed MT5 reference profit.            |
| remaining_matched_residual_sum      | 42.738057   | Runtime adjusted matched PnL minus matched MT5 PnL for non-zero residual cases.      |
| python_unmatched_gap_effect         | 943.605919  | Python-MT5 unmatched profit included only on Python side.                            |
| mt5_unmatched_gap_effect            | -509.19     | Negative of MT5-only ledger profit.                                                  |
| signal_set_gap_effect_sum           | 434.415919  | Python unmatched plus MT5 unmatched gap effect.                                      |
| reconstructed_gap_from_components   | 477.153976  | Matched residual plus signal-set gap effect.                                         |

## Runtime Primary Diff Summary

| primary_diff_class     | rows | adjusted_rows | runtime_residual_sum | runtime_abs_residual_sum | runtime_abs_residual_mean |
| ---------------------- | ---- | ------------- | -------------------- | ------------------------ | ------------------------- |
| exit_reason_diff       | 5    | 0             | -26.890608           | 35.273736                | 7.054747                  |
| minor_or_mixed_diff    | 12   | 0             | 103.665597           | 117.002675               | 9.750223                  |
| pnl_aligned            | 6    | 0             | 9.672263             | 11.158377                | 1.859729                  |
| stage_exit_detail_diff | 29   | 28            | -55.8098             | 55.8098                  | 1.924476                  |
| stop_distance_diff     | 5    | 0             | 12.100605            | 50.270289                | 10.054058                 |

## Remaining Matched Residual Summary

| primary_diff_class     | action_priority | action_bucket                        | rows | residual_sum | abs_residual_sum | max_abs_residual |
| ---------------------- | --------------- | ------------------------------------ | ---- | ------------ | ---------------- | ---------------- |
| stage_exit_detail_diff | P1              | resolve_remaining_stage_exit_blocker | 1    | -55.8098     | 55.8098          | 55.8098          |
| stop_distance_diff     | P1              | review_stop_distance_or_fill_price   | 1    | 15.877926    | 15.877926        | 15.877926        |
| exit_reason_diff       | P1              | review_exit_reason_runtime_ordering  | 1    | -14.81836    | 14.81836         | 14.81836         |
| minor_or_mixed_diff    | P2              | defer_after_p1_or_split_minor_mixed  | 12   | 103.665597   | 117.002675       | 16.725488        |
| stop_distance_diff     | P2              | review_stop_distance_or_fill_price   | 4    | -3.777321    | 34.392363        | 9.8225           |
| exit_reason_diff       | P2              | review_exit_reason_runtime_ordering  | 4    | -12.072248   | 20.455376        | 8.83341          |
| pnl_aligned            | P3              | accept_or_rounding_audit             | 6    | 9.672263     | 11.158377        | 4.33998          |

## Signal-Set Drift Summary

| side             | cause_bucket                         | action_priority | action_bucket                                 | rows | gap_effect_sum | abs_gap_effect_sum | max_abs_gap_effect |
| ---------------- | ------------------------------------ | --------------- | --------------------------------------------- | ---- | -------------- | ------------------ | ------------------ |
| python_unmatched | unique_match_conflict                | P1              | resolve_unique_match_conflict_after_runtime   | 17   | 636.020283     | 751.257189         | 201.85136          |
| mt5_unmatched    | layer3_reject                        | P1              | review_python_layer3_acceptance_mismatch      | 6    | -273.45        | 595.03             | 230.63             |
| python_unmatched | mt5_family_or_time_drift             | P1              | review_family_or_time_drift                   | 14   | 6.606995       | 471.997677         | 115.714136         |
| mt5_unmatched    | trigger_family_drift                 | P1              | review_trigger_family_equivalence_or_anchor   | 6    | -164.48        | 399.38             | 128.85             |
| python_unmatched | python_signal_not_in_mt5_ledger      | P1              | review_python_extra_signal_lifecycle          | 3    | 347.416104     | 347.416104         | 135.186066         |
| mt5_unmatched    | stage_execution_diff_or_family_drift | P1              | split_family_drift_vs_execution_after_runtime | 2    | -285.01        | 285.01             | 161.09             |
| mt5_unmatched    | mapping_conflict_or_profit_diff      | P1              | recheck_mapping_with_runtime_pnl              | 3    | 141.59         | 141.59             | 59.82              |
| mt5_unmatched    | missing_python_candidate             | P1              | review_missing_python_candidate               | 1    | 75.19          | 75.19              | 75.19              |
| mt5_unmatched    | missing_raw_parent                   | P1              | review_m15_raw_parent_or_rescue_gap           | 1    | -50.4          | 50.4               | 50.4               |
| python_unmatched | python_signal_not_in_mt5_ledger      | P2              | review_python_extra_signal_lifecycle          | 7    | -46.437463     | 86.168419          | 28.390183          |
| mt5_unmatched    | missing_raw_parent                   | P2              | review_m15_raw_parent_or_rescue_gap           | 2    | 47.37          | 47.37              | 29.01              |

## Trigger/Mode Impact

| side             | trigger_family | mode_family | rows | gap_effect_sum | abs_gap_effect_sum |
| ---------------- | -------------- | ----------- | ---- | -------------- | ------------------ |
| python_unmatched | M15 SLOT1      | post_n      | 15   | 398.255272     | 715.61286          |
| mt5_unmatched    | M30 CLOSE      | post_n      | 9    | 24.57          | 533.33             |
| mt5_unmatched    | M15 SLOT1      | pre_cross   | 5    | -379.29        | 526.57             |
| python_unmatched | M15 SLOT1      | pre_cross   | 7    | 368.838609     | 500.333667         |
| mt5_unmatched    | M15 SLOT1      | post_n      | 6    | -100.14        | 479.74             |
| python_unmatched | M15 SLOT1      | cross       | 4    | 62.591571      | 211.625753         |
| python_unmatched | M30 CLOSE      | post_n      | 10   | 73.592479      | 123.467261         |
| python_unmatched | M30 CLOSE      | pre_cross   | 2    | 49.210961      | 79.245719          |
| mt5_unmatched    | M30 CLOSE      | pre_cross   | 1    | -54.33         | 54.33              |
| python_unmatched | M30 CLOSE      | cross       | 3    | -8.882973      | 26.554129          |

## Top Matched Residual Cases

| action_priority | action_bucket                        | py_trade_id     | mt5_trade_id | date                | primary_diff_class     | runtime_residual_$ | runtime_abs_residual_$ |
| --------------- | ------------------------------------ | --------------- | ------------ | ------------------- | ---------------------- | ------------------ | ---------------------- |
| P1              | resolve_remaining_stage_exit_blocker | python_mt5_0061 | mt5_0045     | 2025-04-21 02:00:00 | stage_exit_detail_diff | -55.8098           | 55.8098                |
| P1              | review_stop_distance_or_fill_price   | python_mt5_0009 | mt5_0007     | 2020-03-17 04:00:00 | stop_distance_diff     | 15.877926          | 15.877926              |
| P1              | review_exit_reason_runtime_ordering  | python_mt5_0008 | mt5_0004     | 2020-03-13 16:00:00 | exit_reason_diff       | -14.81836          | 14.81836               |
| P2              | defer_after_p1_or_split_minor_mixed  | python_mt5_0029 | mt5_0024     | 2021-06-18 15:30:00 | minor_or_mixed_diff    | 16.725488          | 16.725488              |
| P2              | defer_after_p1_or_split_minor_mixed  | python_mt5_0033 | mt5_0027     | 2022-03-07 21:30:00 | minor_or_mixed_diff    | 16.26939           | 16.26939               |
| P2              | defer_after_p1_or_split_minor_mixed  | python_mt5_0080 | mt5_0058     | 2025-12-24 04:30:00 | minor_or_mixed_diff    | 13.816847          | 13.816847              |
| P2              | defer_after_p1_or_split_minor_mixed  | python_mt5_0018 | mt5_0013     | 2020-03-25 12:00:00 | minor_or_mixed_diff    | 12.325755          | 12.325755              |
| P2              | review_stop_distance_or_fill_price   | python_mt5_0092 | mt5_0075     | 2026-06-08 13:00:00 | stop_distance_diff     | -9.8225            | 9.8225                 |
| P2              | defer_after_p1_or_split_minor_mixed  | python_mt5_0069 | mt5_0052     | 2025-10-09 03:00:00 | minor_or_mixed_diff    | 9.532856           | 9.532856               |
| P2              | review_stop_distance_or_fill_price   | python_mt5_0022 | mt5_0015     | 2020-07-28 07:30:00 | stop_distance_diff     | -9.262342          | 9.262342               |
| P2              | defer_after_p1_or_split_minor_mixed  | python_mt5_0071 | mt5_0054     | 2025-10-15 14:00:00 | minor_or_mixed_diff    | 8.895566           | 8.895566               |
| P2              | review_exit_reason_runtime_ordering  | python_mt5_0057 | mt5_0041     | 2024-04-09 17:00:00 | exit_reason_diff       | -8.83341           | 8.83341                |

## Top Signal-Set Drift Cases

| action_priority | action_bucket                                 | side             | trade_id        | target_time         | trigger_family | mode_family | cause_bucket                         | source_profit_$ | gap_effect_$ | abs_gap_effect_$ |
| --------------- | --------------------------------------------- | ---------------- | --------------- | ------------------- | -------------- | ----------- | ------------------------------------ | --------------- | ------------ | ---------------- |
| P1              | review_python_layer3_acceptance_mismatch      | mt5_unmatched    | mt5_0068        | 2026-02-03 01:00:00 | M15 SLOT1      | pre_cross   | layer3_reject                        | 230.63          | -230.63      | 230.63           |
| P1              | resolve_unique_match_conflict_after_runtime   | python_unmatched | python_mt5_0079 | 2025-10-21 10:00:00 | M15 SLOT1      | post_n      | unique_match_conflict                | 201.85136       | 201.85136    | 201.85136        |
| P1              | resolve_unique_match_conflict_after_runtime   | python_unmatched | python_mt5_0073 | 2025-10-17 11:00:00 | M15 SLOT1      | pre_cross   | unique_match_conflict                | 189.6211        | 189.6211     | 189.6211         |
| P1              | review_python_layer3_acceptance_mismatch      | mt5_unmatched    | mt5_0074        | 2026-04-02 03:00:00 | M15 SLOT1      | pre_cross   | layer3_reject                        | 171.9           | -171.9       | 171.9            |
| P1              | split_family_drift_vs_execution_after_runtime | mt5_unmatched    | mt5_0005        | 2020-03-13 17:30:00 | M15 SLOT1      | post_n      | stage_execution_diff_or_family_drift | 161.09          | -161.09      | 161.09           |
| P1              | resolve_unique_match_conflict_after_runtime   | python_unmatched | python_mt5_0075 | 2025-10-17 15:00:00 | M15 SLOT1      | post_n      | unique_match_conflict                | 150.91695       | 150.91695    | 150.91695        |
| P1              | review_python_extra_signal_lifecycle          | python_unmatched | python_mt5_0091 | 2026-05-28 15:30:00 | M15 SLOT1      | cross       | python_signal_not_in_mt5_ledger      | 135.186066      | 135.186066   | 135.186066       |
| P1              | review_trigger_family_equivalence_or_anchor   | mt5_unmatched    | mt5_0019        | 2020-08-04 19:00:00 | M15 SLOT1      | post_n      | trigger_family_drift                 | 128.85          | -128.85      | 128.85           |
| P1              | split_family_drift_vs_execution_after_runtime | mt5_unmatched    | mt5_0048        | 2025-09-02 17:30:00 | M30 CLOSE      | post_n      | stage_execution_diff_or_family_drift | 123.92          | -123.92      | 123.92           |
| P1              | review_family_or_time_drift                   | python_unmatched | python_mt5_0065 | 2025-04-22 16:30:00 | M15 SLOT1      | post_n      | mt5_family_or_time_drift             | 115.714136      | 115.714136   | 115.714136       |
| P1              | review_python_extra_signal_lifecycle          | python_unmatched | python_mt5_0090 | 2026-05-28 14:30:00 | M15 SLOT1      | pre_cross   | python_signal_not_in_mt5_ledger      | 114.292288      | 114.292288   | 114.292288       |
| P1              | review_python_extra_signal_lifecycle          | python_unmatched | python_mt5_0068 | 2025-09-30 09:30:00 | M15 SLOT1      | pre_cross   | python_signal_not_in_mt5_ledger      | 97.93775        | 97.93775     | 97.93775         |
| P1              | review_python_layer3_acceptance_mismatch      | mt5_unmatched    | mt5_0065        | 2026-02-02 16:30:00 | M15 SLOT1      | post_n      | layer3_reject                        | -88.35          | 88.35        | 88.35            |
| P1              | review_trigger_family_equivalence_or_anchor   | mt5_unmatched    | mt5_0043        | 2024-11-13 19:30:00 | M30 CLOSE      | post_n      | trigger_family_drift                 | 80.96           | -80.96       | 80.96            |
| P1              | review_missing_python_candidate               | mt5_unmatched    | mt5_0026        | 2021-11-10 16:30:00 | M30 CLOSE      | post_n      | missing_python_candidate             | -75.19          | 75.19        | 75.19            |

## Action Plan

1. Treat the remaining matched residual as small but actionable diagnostics: review `exit_reason_diff` and `stop_distance_diff` first, then split `minor_or_mixed_diff`; keep `pnl_aligned` as tolerance unless later reruns expand it.
2. For signal-set drift, prioritize high-impact MT5-only positive-profit misses and Python-only high-impact extra signals; these dominate the post-runtime global gap.
3. The cause labels in this report are regenerated from the close-retry mapping snapshot; rerun this review after any mapping-policy change.
4. Keep EA price-side behavior unchanged until a new smoke directly proves a Stage1/2 price-side error.
