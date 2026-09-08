# Stage-State Lifecycle-Aware Max-Pos Probe

## Scope

- Non-destructive prototype only.
- Tests Stage-derived `stage3_time` as active-until instead of fixed 24-hour max-pos occupancy.
- Rebuilds signal snapshots and reruns Stage, dynamic risk, and mapping for lifecycle variants.
- Does not modify baseline Python signals, EA behavior, dynamic-risk code, or mapping rules.

## Final Decision

- Variants tested: `3`.
- Target exact variants: `0`.
- Lifecycle probe gate pass count: `0`.
- Decision: `lifecycle_probe_not_mergeable`.
- Recommended next action: `review_lifecycle_probe_failures_before_any_signal_change`.
- `main_signal_change_gate_open = False`.
- `ea_behavior_gate_open = False`.
- `mapping_change_gate_open = False`.
- `merge_gate_pass = False`.

## Signal Admission Summary

| variant                                    | description                                                                                                                      | selector             | remove_nearest_opposite   |   selected_candidates |   selected_same_family_opposite |   removed_nearest_opposite_rows |   before_maxpos_rows |   fixed24_after_rows |   fixed24_candidate_rows_after |   fixed24_target_candidate_after |   lifecycle_after_rows |   lifecycle_candidate_rows_after |   lifecycle_target_candidate_after | lifecycle_target_accepted   |   lifecycle_target_active_count_before | lifecycle_target_blockers_before                                                                                           |   lifecycle_minus_fixed_candidate_rows |
|:-------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------|:---------------------|:--------------------------|----------------------:|--------------------------------:|--------------------------------:|---------------------:|---------------------:|-------------------------------:|---------------------------------:|-----------------------:|---------------------------------:|-----------------------------------:|:----------------------------|---------------------------------------:|:---------------------------------------------------------------------------------------------------------------------------|---------------------------------------:|
| lifecycle_add_all29_stage3time             | Append all 29 rescue candidates and use Stage-derived stage3_time as active-until.                                               | all29                | False                     |                    29 |                               8 |                               0 |                  127 |                  102 |                              9 |                                0 |                    117 |                               22 |                                  0 | False                       |                                      3 | 2026-03-24 10:00:00 BUY M15 SLOT1/post_n;2026-03-24 10:30:00 BUY M15 SLOT1/post_n;2026-03-24 11:00:00 BUY M15 SLOT1/post_n |                                     13 |
| lifecycle_replace_nearest_all29_stage3time | Remove nearest opposite rows for all 29 rescue candidates, then use Stage-derived stage3_time as active-until.                   | all29                | True                      |                    29 |                               8 |                               7 |                  120 |                  101 |                             12 |                                0 |                    112 |                               23 |                                  0 | False                       |                                      3 | 2026-03-24 10:00:00 BUY M15 SLOT1/post_n;2026-03-24 10:30:00 BUY M15 SLOT1/post_n;2026-03-24 11:00:00 BUY M15 SLOT1/post_n |                                     11 |
| lifecycle_replace_same_family8_stage3time  | Remove nearest opposite rows only for the 8 same-family-opposite candidates, then use Stage-derived stage3_time as active-until. | same_family_opposite | True                      |                     8 |                               8 |                               2 |                  104 |                   99 |                              4 |                                0 |                    100 |                                6 |                                  0 | False                       |                                      3 | 2026-03-24 10:00:00 BUY M15 SLOT1/post_n;2026-03-24 10:30:00 BUY M15 SLOT1/post_n;2026-03-24 11:00:00 BUY M15 SLOT1/post_n |                                      2 |

## Full-Chain Before / After

| scenario                                   |   python_trade_count |   mt5_trade_count |   python_final_balance |   mt5_final_balance |   direct_gap_py_minus_mt5 |   matched_unique |   reliable_tier_matched |   relaxed_tier_matched |   python_unmatched |   mt5_unmatched |   matched_profit_diff_py_minus_mt5 |   signal_set_gap_py_minus_mt5 | note                                                                                                                             |
|:-------------------------------------------|---------------------:|------------------:|-----------------------:|--------------------:|--------------------------:|-----------------:|------------------------:|-----------------------:|-------------------:|----------------:|-----------------------------------:|------------------------------:|:---------------------------------------------------------------------------------------------------------------------------------|
| current_stage_state_metadatafix            |                   98 |                82 |                4039.57 |             1649.84 |                   2389.73 |               60 |                      29 |                     31 |                 38 |              22 |                            654.895 |                       1734.84 | current accepted stage-state metadatafix baseline                                                                                |
| lifecycle_add_all29_stage3time             |                  117 |                82 |                7523.08 |             1649.84 |                   5873.24 |               67 |                      33 |                     34 |                 50 |              15 |                            411.688 |                       5461.55 | Append all 29 rescue candidates and use Stage-derived stage3_time as active-until.                                               |
| lifecycle_replace_nearest_all29_stage3time |                  112 |                82 |                7077.71 |             1649.84 |                   5427.87 |               65 |                      32 |                     33 |                 47 |              17 |                            382.181 |                       5045.69 | Remove nearest opposite rows for all 29 rescue candidates, then use Stage-derived stage3_time as active-until.                   |
| lifecycle_replace_same_family8_stage3time  |                  100 |                82 |                6213.05 |             1649.84 |                   4563.21 |               61 |                      30 |                     31 |                 39 |              21 |                            699.36  |                       3863.85 | Remove nearest opposite rows only for the 8 same-family-opposite candidates, then use Stage-derived stage3_time as active-until. |

## Target mt5_0076

| scenario                                   | target_time         |   target_dynamic_rows |   target_dynamic_profit_sum | target_dynamic_modes   | target_dynamic_variants   | mt5_0076_matched   | target_python_time_matched   | mt5_0076_match_tier   | mt5_0076_py_trade_id   | mt5_0076_py_date    | mt5_0076_py_trigger_family   | mt5_0076_py_mode_family   |   mt5_0076_py_profit |   mt5_0076_mt5_profit |   mt5_0076_profit_diff |
|:-------------------------------------------|:--------------------|----------------------:|----------------------------:|:-----------------------|:--------------------------|:-------------------|:-----------------------------|:----------------------|:-----------------------|:--------------------|:-----------------------------|:--------------------------|---------------------:|----------------------:|-----------------------:|
| current_stage_state_metadatafix            | 2026-03-24 12:00:00 |                     0 |                           0 |                        |                           | False              | False                        |                       |                        |                     |                              |                           |                      |                       |                        |
| lifecycle_add_all29_stage3time             | 2026-03-24 12:00:00 |                     0 |                           0 |                        |                           | True               | False                        | nearby_60_all         | python_mt5_0108        | 2026-03-24 11:00:00 | M15 SLOT1                    | post_n                    |             -182.963 |                -104.7 |               -78.2629 |
| lifecycle_replace_nearest_all29_stage3time | 2026-03-24 12:00:00 |                     0 |                           0 |                        |                           | True               | False                        | nearby_60_all         | python_mt5_0103        | 2026-03-24 11:00:00 | M15 SLOT1                    | post_n                    |             -156.825 |                -104.7 |               -52.1253 |
| lifecycle_replace_same_family8_stage3time  | 2026-03-24 12:00:00 |                     0 |                           0 |                        |                           | True               | False                        | nearby_60_all         | python_mt5_0091        | 2026-03-24 11:00:00 | M15 SLOT1                    | post_n                    |             -156.825 |                -104.7 |               -52.1253 |

## Variant Decisions

| variant                                    |   selected_candidates |   lifecycle_candidate_rows_after |   lifecycle_target_candidate_after | mt5_0076_match_tier   | target_python_time_matched   |   matched_unique_delta |   reliable_tier_delta |   python_unmatched_delta |   mt5_unmatched_delta |   direct_gap_delta |   signal_set_gap_delta | matched_not_worse   | reliable_not_worse   | direct_gap_not_worse   | signal_gap_not_worse   | multi_candidate_support   | quality_improved   | lifecycle_probe_gate_pass   | main_signal_change_gate_open   | ea_behavior_gate_open   | mapping_change_gate_open   | merge_gate_pass   | decision               |
|:-------------------------------------------|----------------------:|---------------------------------:|-----------------------------------:|:----------------------|:-----------------------------|-----------------------:|----------------------:|-------------------------:|----------------------:|-------------------:|-----------------------:|:--------------------|:---------------------|:-----------------------|:-----------------------|:--------------------------|:-------------------|:----------------------------|:-------------------------------|:------------------------|:---------------------------|:------------------|:-----------------------|
| lifecycle_add_all29_stage3time             |                    29 |                               22 |                                  0 | nearby_60_all         | False                        |                      7 |                     4 |                       12 |                    -7 |            3483.51 |                3726.71 | True                | True                 | False                  | False                  | True                      | True               | False                       | False                          | False                   | False                      | False             | diagnostic_only_reject |
| lifecycle_replace_nearest_all29_stage3time |                    29 |                               23 |                                  0 | nearby_60_all         | False                        |                      5 |                     3 |                        9 |                    -5 |            3038.14 |                3310.85 | True                | True                 | False                  | False                  | True                      | True               | False                       | False                          | False                   | False                      | False             | diagnostic_only_reject |
| lifecycle_replace_same_family8_stage3time  |                     8 |                                6 |                                  0 | nearby_60_all         | False                        |                      1 |                     1 |                        1 |                    -1 |            2173.48 |                2129.01 | True                | True                 | False                  | False                  | True                      | True               | False                       | False                          | False                   | False                      | False             | diagnostic_only_reject |

## Interpretation

- A lifecycle-aware max-pos candidate must improve target matching without reducing matched/reliable counts or worsening direct/signal-set gaps.
- A target-only improvement remains diagnostic-only.
- Any candidate that passes this probe still requires manual review before a main signal change.

## Output Files

- `lifecycle_maxpos_signal_summary.csv`
- `lifecycle_maxpos_full_chain_before_after.csv`
- `lifecycle_maxpos_target_mt5_0076_review.csv`
- `lifecycle_maxpos_variant_decisions.csv`
- `lifecycle_maxpos_final_decision.csv`
- `lifecycle_maxpos_trace.csv`
- `signals/<variant>/`
- `dynamic_inputs/<variant>/`
- `dynamic_alignment/<variant>/`
- `mapping/<variant>/`
