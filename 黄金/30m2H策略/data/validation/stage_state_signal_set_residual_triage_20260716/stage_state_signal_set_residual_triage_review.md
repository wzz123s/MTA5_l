# Stage-state signal-set residual triage

## Scope

- Baseline: accepted stage-state MT5 full tester ledger.
- Primary scenario: `stage_state_metadatafix_exec_model`.
- This is read-only and does not modify EA, Python signals, mapping scripts, or fund-curve calculations.

## Decision

- Recomputed signal-set gap: `1734.837492`.
- Expected signal-set gap: `1734.837492`.
- Recompute error: `-0.0`.
- EA price-side gate open: `False`.
- Decision: `do_not_change_ea_behavior_from_current_evidence`.
- Next action: `mapping_policy_and_unique_conflict_review_before_signal_or_ea_changes`.

## Current Gap Context

|   current_mt5_final_balance |   metadatafix_direct_gap_py_minus_mt5 |   metadatafix_matched_profit_diff_py_minus_mt5 |   metadatafix_signal_set_gap_py_minus_mt5 |   metadatafix_matched_unique |   metadatafix_reliable_tier_matched |   metadatafix_relaxed_tier_matched |   metadatafix_python_unmatched |   metadatafix_mt5_unmatched |
|----------------------------:|--------------------------------------:|-----------------------------------------------:|------------------------------------------:|-----------------------------:|------------------------------------:|-----------------------------------:|-------------------------------:|----------------------------:|
|                     1649.84 |                               2389.73 |                                        654.895 |                                   1734.84 |                           60 |                                  29 |                                 31 |                             38 |                          22 |

## Signal-Set Bucket Summary

| action_bucket                           | side             |   rows |   gap_effect_sum |   abs_gap_effect_sum |   max_abs_gap_effect |
|:----------------------------------------|:-----------------|-------:|-----------------:|---------------------:|---------------------:|
| mapping_policy_first_unique_conflict    | python_unmatched |     28 |         1615.61  |              2492.47 |              389.955 |
| python_only_signal_gap_no_mt5_candidate | python_unmatched |     10 |          686.567 |              1042.66 |              346.215 |
| mt5_only_signal_gap_no_python_candidate | mt5_unmatched    |     12 |           -9.43  |               804.75 |              171.9   |
| time_axis_diagnostic_only               | mt5_unmatched    |      6 |         -396.95  |               644.19 |              230.63  |
| mapping_policy_first_unique_conflict    | mt5_unmatched    |      4 |         -160.96  |               308.7  |              123.92  |

## Top Signal-Set Cases

| side             | trade_id        | target_time         | dir_norm   | trigger_family   | mode_family   |   gap_effect_$ | action_priority   | action_bucket                           |   candidate_count |   reliable_candidate_count | best_candidate_tier       |   best_candidate_abs_minutes | best_candidate_unique_conflict   | best_candidate_unique_conflict_with   | time_axis_candidate   | time_axis_has_gap   |
|:-----------------|:----------------|:--------------------|:-----------|:-----------------|:--------------|---------------:|:------------------|:----------------------------------------|------------------:|---------------------------:|:--------------------------|-----------------------------:|:---------------------------------|:--------------------------------------|:----------------------|:--------------------|
| python_unmatched | python_mt5_0079 | 2025-10-21 10:00:00 | SELL       | M15 SLOT1        | post_n        |       389.955  | P1                | mapping_policy_first_unique_conflict    |                 3 |                          1 | nearby_7d_all             |                         5490 | True                             | python_mt5_0074                       | False                 | False               |
| python_unmatched | python_mt5_0073 | 2025-10-17 11:00:00 | SELL       | M15 SLOT1        | pre_cross     |       379.242  | P1                | mapping_policy_first_unique_conflict    |                 3 |                          1 | nearby_7d_all             |                         1650 | True                             | python_mt5_0072                       | False                 | False               |
| python_unmatched | python_mt5_0091 | 2026-05-28 15:30:00 | BUY        | M15 SLOT1        | cross         |       346.215  | P1                | python_only_signal_gap_no_mt5_candidate |                 0 |                          0 |                           |                          nan | False                            |                                       | False                 | False               |
| python_unmatched | python_mt5_0075 | 2025-10-17 15:00:00 | SELL       | M15 SLOT1        | post_n        |       301.834  | P1                | mapping_policy_first_unique_conflict    |                 3 |                          1 | nearby_60_all             |                           30 | True                             | python_mt5_0074                       | False                 | False               |
| python_unmatched | python_mt5_0090 | 2026-05-28 14:30:00 | BUY        | M15 SLOT1        | pre_cross     |       246.083  | P1                | python_only_signal_gap_no_mt5_candidate |                 0 |                          0 |                           |                          nan | False                            |                                       | False                 | False               |
| mt5_unmatched    | mt5_0070        | 2026-02-03 01:00:00 | BUY        | M15 SLOT1        | pre_cross     |      -230.63   | P1                | time_axis_diagnostic_only               |                 0 |                          0 |                           |                          nan | False                            |                                       | True                  | True                |
| python_unmatched | python_mt5_0065 | 2025-04-22 16:30:00 | SELL       | M15 SLOT1        | post_n        |       191.769  | P1                | mapping_policy_first_unique_conflict    |                 2 |                          0 | nearby_60_trigger_relaxed |                           60 | True                             | python_mt5_0064                       | False                 | False               |
| python_unmatched | python_mt5_0062 | 2025-04-21 02:30:00 | BUY        | M15 SLOT1        | post_n        |       185.728  | P1                | mapping_policy_first_unique_conflict    |                 1 |                          0 | nearby_60_trigger_relaxed |                           60 | True                             | python_mt5_0061                       | False                 | False               |
| mt5_unmatched    | mt5_0077        | 2026-04-02 03:00:00 | SELL       | M15 SLOT1        | pre_cross     |      -171.9    | P1                | mt5_only_signal_gap_no_python_candidate |                 0 |                          0 |                           |                          nan | False                            |                                       | True                  | False               |
| python_unmatched | python_mt5_0068 | 2025-09-30 09:30:00 | SELL       | M15 SLOT1        | pre_cross     |       163.85   | P1                | python_only_signal_gap_no_mt5_candidate |                 0 |                          0 |                           |                          nan | False                            |                                       | False                 | False               |
| mt5_unmatched    | mt5_0005        | 2020-03-13 17:30:00 | SELL       | M15 SLOT1        | post_n        |      -161.09   | P1                | time_axis_diagnostic_only               |                 4 |                          0 | nearby_7d_trigger_relaxed |                         6720 | True                             | mt5_0009                              | True                  | True                |
| mt5_unmatched    | mt5_0019        | 2020-08-04 19:00:00 | BUY        | M15 SLOT1        | post_n        |      -128.85   | P2                | time_axis_diagnostic_only               |                 0 |                          0 |                           |                          nan | False                            |                                       | True                  | True                |
| mt5_unmatched    | mt5_0049        | 2025-09-02 17:30:00 | BUY        | M30 CLOSE        | post_n        |      -123.92   | P2                | mapping_policy_first_unique_conflict    |                 1 |                          0 | nearby_60_trigger_relaxed |                           30 | True                             | mt5_0050                              | False                 | False               |
| python_unmatched | python_mt5_0007 | 2020-03-13 15:30:00 | SELL       | M30 CLOSE        | pre_cross     |       121.922  | P2                | mapping_policy_first_unique_conflict    |                 4 |                          0 | nearby_60_mode_relaxed    |                           30 | True                             | python_mt5_0008                       | False                 | False               |
| mt5_unmatched    | mt5_0059        | 2025-10-20 13:30:00 | BUY        | M30 CLOSE        | post_n        |      -110.91   | P2                | mapping_policy_first_unique_conflict    |                 2 |                          0 | nearby_60_trigger_relaxed |                           30 | True                             | mt5_0054                              | False                 | False               |
| mt5_unmatched    | mt5_0076        | 2026-03-24 12:00:00 | BUY        | M15 SLOT1        | post_n        |       104.7    | P2                | mt5_only_signal_gap_no_python_candidate |                 0 |                          0 |                           |                          nan | False                            |                                       | False                 | False               |
| python_unmatched | python_mt5_0041 | 2022-11-10 16:00:00 | BUY        | M15 SLOT1        | post_n        |        90.858  | P2                | mapping_policy_first_unique_conflict    |                 4 |                          1 | nearby_7d_all             |                         2760 | True                             | python_mt5_0039                       | False                 | False               |
| python_unmatched | python_mt5_0042 | 2022-11-10 16:30:00 | BUY        | M15 SLOT1        | post_n        |        90.1661 | P2                | mapping_policy_first_unique_conflict    |                 4 |                          1 | nearby_7d_all             |                         2790 | True                             | python_mt5_0039                       | False                 | False               |
| python_unmatched | python_mt5_0038 | 2022-03-09 12:30:00 | SELL       | M30 CLOSE        | post_n        |        89.2193 | P2                | mapping_policy_first_unique_conflict    |                 2 |                          1 | nearby_60_all             |                           60 | True                             | python_mt5_0036                       | False                 | False               |
| python_unmatched | python_mt5_0098 | 2026-06-30 09:30:00 | BUY        | M15 SLOT1        | post_n        |       -88.6497 | P2                | mapping_policy_first_unique_conflict    |                 2 |                          0 | same_dir_7d_unclassified  |                           30 | True                             | python_mt5_0097                       | False                 | False               |

## Matched Residual Bucket Summary

| action_bucket                         | primary_residual_driver   | is_reliable_tier   |   rows |   profit_diff_py_minus_mt5_sum |   abs_profit_diff_sum |   max_abs_profit_diff |   lot_sizing_effect_sum |   stage_exit_points_effect_sum |   swap_commission_effect_sum |
|:--------------------------------------|:--------------------------|:-------------------|-------:|-------------------------------:|----------------------:|----------------------:|------------------------:|-------------------------------:|-----------------------------:|
| mapping_policy_first_relaxed_match    | stage_exit_points         | False              |     19 |                     -116.539   |            1215.28    |             156.817   |                 38.6127 |                       95.2648  |                       -17.28 |
| mapping_policy_first_relaxed_match    | lot_sizing                | False              |     11 |                      265.329   |             809.251   |             458.413   |                -14.8625 |                     -249.051   |                        -1.44 |
| execution_lot_sizing_or_balance_path  | lot_sizing                | True               |      3 |                      415.24    |             466.858   |             279.184   |               -301.93   |                     -113.315   |                         0    |
| execution_stage_exit_or_tick_ordering | stage_exit_points         | True               |     25 |                       87.9603  |             447.699   |             131.26    |                -66.4215 |                       -2.76179 |                       -18.72 |
| execution_cost_or_rounding            | swap_commission           | True               |      1 |                        1.81878 |               1.81878 |               1.81878 |                  0      |                       -0.36978 |                        -1.44 |
| mapping_policy_first_relaxed_match    | swap_commission           | False              |      1 |                        1.08634 |               1.08634 |               1.08634 |                  0      |                        2.27966 |                        -3.36 |

## Top Matched Residual Cases

| py_trade_id     | mt5_trade_id   | match_tier                | is_reliable_tier   | py_trigger_family   | py_mode_family   | dir_norm   |   profit_diff_py_minus_mt5 |   abs_profit_diff | primary_residual_driver   | action_bucket                         |
|:----------------|:---------------|:--------------------------|:-------------------|:--------------------|:-----------------|:-----------|---------------------------:|------------------:|:--------------------------|:--------------------------------------|
| python_mt5_0063 | mt5_0047       | nearby_60_trigger_relaxed | False              | M15 SLOT1           | pre_cross        | SELL       |                   458.413  |          458.413  | lot_sizing                | mapping_policy_first_relaxed_match    |
| python_mt5_0082 | mt5_0063       | exact_align90_all         | True               | M15 SLOT1           | pre_cross        | SELL       |                   279.184  |          279.184  | lot_sizing                | execution_lot_sizing_or_balance_path  |
| python_mt5_0092 | mt5_0078       | exact_align90_all         | True               | M15 SLOT1           | pre_cross        | BUY        |                   161.865  |          161.865  | lot_sizing                | execution_lot_sizing_or_balance_path  |
| python_mt5_0030 | mt5_0023       | nearby_7d_trigger_relaxed | False              | M30 CLOSE           | post_n           | SELL       |                  -156.817  |          156.817  | stage_exit_points         | mapping_policy_first_relaxed_match    |
| python_mt5_0084 | mt5_0064       | exact_align90_all         | True               | M15 SLOT1           | post_n           | SELL       |                   131.26   |          131.26   | stage_exit_points         | execution_stage_exit_or_tick_ordering |
| python_mt5_0024 | mt5_0016       | nearby_60_trigger_relaxed | False              | M30 CLOSE           | post_n           | SELL       |                   124.332  |          124.332  | stage_exit_points         | mapping_policy_first_relaxed_match    |
| python_mt5_0037 | mt5_0028       | nearby_7d_mode_relaxed    | False              | M30 CLOSE           | post_n           | SELL       |                   117.381  |          117.381  | stage_exit_points         | mapping_policy_first_relaxed_match    |
| python_mt5_0086 | mt5_0068       | nearby_60_mode_relaxed    | False              | M15 SLOT1           | cross            | SELL       |                  -114.553  |          114.553  | stage_exit_points         | mapping_policy_first_relaxed_match    |
| python_mt5_0087 | mt5_0073       | nearby_60_trigger_relaxed | False              | M15 SLOT1           | pre_cross        | SELL       |                  -103.433  |          103.433  | stage_exit_points         | mapping_policy_first_relaxed_match    |
| python_mt5_0061 | mt5_0046       | nearby_60_trigger_relaxed | False              | M15 SLOT1           | post_n           | BUY        |                    90.8202 |           90.8202 | stage_exit_points         | mapping_policy_first_relaxed_match    |
| python_mt5_0050 | mt5_0036       | nearby_7d_mode_relaxed    | False              | M15 SLOT1           | post_n           | SELL       |                    89.0087 |           89.0087 | stage_exit_points         | mapping_policy_first_relaxed_match    |
| python_mt5_0083 | mt5_0069       | nearby_7d_mode_relaxed    | False              | M15 SLOT1           | cross            | SELL       |                    78.8769 |           78.8769 | lot_sizing                | mapping_policy_first_relaxed_match    |
| python_mt5_0048 | mt5_0035       | nearby_60_trigger_relaxed | False              | M15 SLOT1           | post_n           | BUY        |                   -78.351  |           78.351  | stage_exit_points         | mapping_policy_first_relaxed_match    |
| python_mt5_0094 | mt5_0080       | nearby_60_trigger_relaxed | False              | M15 SLOT1           | pre_cross        | BUY        |                   -62.7593 |           62.7593 | lot_sizing                | mapping_policy_first_relaxed_match    |
| python_mt5_0011 | mt5_0003       | nearby_7d_trigger_relaxed | False              | M30 CLOSE           | post_n           | BUY        |                   -60.7404 |           60.7404 | stage_exit_points         | mapping_policy_first_relaxed_match    |
| python_mt5_0014 | mt5_0006       | nearby_7d_mode_relaxed    | False              | M30 CLOSE           | post_n           | BUY        |                    56.722  |           56.722  | stage_exit_points         | mapping_policy_first_relaxed_match    |
| python_mt5_0081 | mt5_0062       | nearby_60_trigger_relaxed | False              | M15 SLOT1           | pre_cross        | SELL       |                   -55.5385 |           55.5385 | lot_sizing                | mapping_policy_first_relaxed_match    |
| python_mt5_0035 | mt5_0029       | nearby_7d_trigger_relaxed | False              | M30 CLOSE           | post_n           | BUY        |                   -55.3574 |           55.3574 | stage_exit_points         | mapping_policy_first_relaxed_match    |
| python_mt5_0085 | mt5_0066       | nearby_60_trigger_relaxed | False              | M15 SLOT1           | pre_cross        | SELL       |                   -53.5796 |           53.5796 | lot_sizing                | mapping_policy_first_relaxed_match    |
| python_mt5_0072 | mt5_0056       | exact_align90_all         | True               | M15 SLOT1           | pre_cross        | SELL       |                    51.5108 |           51.5108 | stage_exit_points         | execution_stage_exit_or_tick_ordering |

## Interpretation

- The signal-set gap closes exactly from unmatched Python minus unmatched MT5 profit, so this is now an attribution problem rather than a missing-ledger problem.
- `time_axis_diagnostic_only` rows are not mergeable because the prior +90/+120 gate failed.
- `mapping_policy_first_*` rows require unique-match/window/relaxed-tier review before any signal or EA behavior changes.
- Reliable matched residuals can later feed execution-model work, but relaxed matched residuals must remain mapping/accounting risk first.
- P0 subset bridge is not selected here because it worsens the current stage-state direct and signal-set gaps.

## Output Files

- `stage_state_signal_set_case_triage.csv`
- `stage_state_signal_set_bucket_summary.csv`
- `stage_state_matched_residual_action_triage.csv`
- `stage_state_matched_residual_bucket_summary.csv`
- `stage_state_signal_set_residual_triage_decision.csv`
- `mapping_policy_first_signal_cases.csv`
- `time_axis_diagnostic_signal_cases.csv`
- `reliable_execution_residual_cases.csv`
