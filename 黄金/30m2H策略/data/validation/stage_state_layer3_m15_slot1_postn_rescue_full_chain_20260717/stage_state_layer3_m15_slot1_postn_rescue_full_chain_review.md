# Stage-State Layer3 M15 SLOT1 post_n Rescue Full-Chain Prototype

## Scope

- Non-destructive prototype only.
- Builds versioned signal snapshots and reruns Stage, dynamic risk, and mapping.
- Does not modify baseline Python signals, EA behavior, or mapping rules.

## Signal Variants

| variant                                  | description                                                                                            |   base_layer3_rows |   available_rescue_candidates |   before_maxpos_rows |   after_maxpos_rows |   candidate_rows_before_maxpos |   candidate_rows_after_maxpos |   removed_nearest_opposite_rows |   target_candidate_after_maxpos |   target_candidate_after_maxpos_profit_sum |
|:-----------------------------------------|:-------------------------------------------------------------------------------------------------------|-------------------:|------------------------------:|---------------------:|--------------------:|-------------------------------:|------------------------------:|--------------------------------:|--------------------------------:|-------------------------------------------:|
| add_then_maxpos_all29                    | append all 29 rescue candidates, then apply current max-pos-3 gate                                     |                 98 |                            29 |                  127 |                 102 |                             29 |                             9 |                               0 |                               0 |                                      0     |
| replace_nearest_opposite_all29           | remove nearest opposite Layer3 rows for all 29 candidates, append all candidates, then apply max-pos-3 |                 98 |                            29 |                  120 |                 101 |                             29 |                            12 |                               7 |                               0 |                                      0     |
| target_mt5_0076_replace_nearest_opposite | only add the exact mt5_0076 target candidate and remove its nearest opposite Layer3 row                |                 98 |                            29 |                   98 |                  98 |                              1 |                             1 |                               1 |                               1 |                                    -30.904 |

## Before / After

| scenario                                 |   python_trade_count |   mt5_trade_count |   python_final_balance |   mt5_final_balance |   direct_gap_py_minus_mt5 |   matched_unique |   reliable_tier_matched |   relaxed_tier_matched |   python_unmatched |   mt5_unmatched |   matched_profit_diff_py_minus_mt5 |   signal_set_gap_py_minus_mt5 | note                                                                                                   |
|:-----------------------------------------|---------------------:|------------------:|-----------------------:|--------------------:|--------------------------:|-----------------:|------------------------:|-----------------------:|-------------------:|----------------:|-----------------------------------:|------------------------------:|:-------------------------------------------------------------------------------------------------------|
| current_stage_state_metadatafix          |                   98 |                82 |                4039.57 |             1649.84 |                   2389.73 |               60 |                      29 |                     31 |                 38 |              22 |                            654.895 |                       1734.84 | current accepted stage-state metadatafix baseline                                                      |
| add_then_maxpos_all29                    |                  102 |                82 |                4495.88 |             1649.84 |                   2846.04 |               63 |                      30 |                     33 |                 39 |              19 |                            819.268 |                       2026.77 | append all 29 rescue candidates, then apply current max-pos-3 gate                                     |
| replace_nearest_opposite_all29           |                  101 |                82 |                4310.27 |             1649.84 |                   2660.43 |               63 |                      31 |                     32 |                 38 |              19 |                           1074.16  |                       1586.27 | remove nearest opposite Layer3 rows for all 29 candidates, append all candidates, then apply max-pos-3 |
| target_mt5_0076_replace_nearest_opposite |                   98 |                82 |                3953.33 |             1649.84 |                   2303.49 |               61 |                      30 |                     31 |                 37 |              21 |                            666.883 |                       1636.61 | only add the exact mt5_0076 target candidate and remove its nearest opposite Layer3 row                |

## Target mt5_0076

| scenario                                 | target_time         |   target_dynamic_rows |   target_dynamic_profit_sum | target_dynamic_modes   | target_dynamic_variants   | mt5_0076_matched   | target_python_time_matched   | mt5_0076_match_tier   | mt5_0076_py_trade_id   | mt5_0076_py_date    | mt5_0076_py_trigger_family   | mt5_0076_py_mode_family   |   mt5_0076_py_profit |   mt5_0076_mt5_profit |   mt5_0076_profit_diff |
|:-----------------------------------------|:--------------------|----------------------:|----------------------------:|:-----------------------|:--------------------------|:-------------------|:-----------------------------|:----------------------|:-----------------------|:--------------------|:-----------------------------|:--------------------------|---------------------:|----------------------:|-----------------------:|
| current_stage_state_metadatafix          | 2026-03-24 12:00:00 |                     0 |                      0      |                        |                           | False              | False                        |                       |                        |                     |                              |                           |                      |                       |                        |
| add_then_maxpos_all29                    | 2026-03-24 12:00:00 |                     0 |                      0      |                        |                           | False              | False                        |                       |                        |                     |                              |                           |                      |                       |                        |
| replace_nearest_opposite_all29           | 2026-03-24 12:00:00 |                     0 |                      0      |                        |                           | True               | False                        | nearby_180_all        | python_mt5_0092        | 2026-03-24 10:00:00 | M15 SLOT1                    | post_n                    |             -32.5693 |                -104.7 |                72.1307 |
| target_mt5_0076_replace_nearest_opposite | 2026-03-24 12:00:00 |                     1 |                    -92.7121 | post_n6                | ea_slot1_replace          | True               | True                         | exact_align90_all     | python_mt5_0089        | 2026-03-24 12:00:00 | M15 SLOT1                    | post_n                    |             -92.7121 |                -104.7 |                11.9879 |

## Decision

| variant                                  |   candidate_rows_after_maxpos |   target_candidate_after_maxpos | mt5_0076_matched   | target_python_time_matched   |   matched_unique_delta |   reliable_tier_delta |   python_unmatched_delta |   mt5_unmatched_delta |   direct_gap_delta |   signal_set_gap_delta | matched_not_worse   | reliable_not_worse   | direct_gap_not_worse   | signal_gap_not_worse   | quality_improved   | target_improved   | main_signal_change_gate_open   | ea_behavior_gate_open   | mapping_change_gate_open   | merge_gate_pass   | decision                                |
|:-----------------------------------------|------------------------------:|--------------------------------:|:-------------------|:-----------------------------|-----------------------:|----------------------:|-------------------------:|----------------------:|-------------------:|-----------------------:|:--------------------|:---------------------|:-----------------------|:-----------------------|:-------------------|:------------------|:-------------------------------|:------------------------|:---------------------------|:------------------|:----------------------------------------|
| add_then_maxpos_all29                    |                             9 |                               0 | False              | False                        |                      3 |                     1 |                        1 |                    -3 |            456.305 |               291.932  | True                | True                 | False                  | False                  | True               | False             | False                          | False                   | False                      | False             | diagnostic_only                         |
| replace_nearest_opposite_all29           |                            12 |                               0 | True               | False                        |                      3 |                     2 |                        0 |                    -3 |            270.693 |              -148.569  | True                | True                 | False                  | True                   | True               | True              | False                          | False                   | False                      | False             | diagnostic_only                         |
| target_mt5_0076_replace_nearest_opposite |                             1 |                               1 | True               | True                         |                      1 |                     1 |                       -1 |                    -1 |            -86.243 |               -98.2309 | True                | True                 | True                   | True                   | True               | True              | False                          | False                   | False                      | True              | prototype_candidate_needs_manual_review |

## Interpretation

- `add_then_maxpos_all29` tests whether the current max-pos gate naturally admits the rescue candidates.
- `replace_nearest_opposite_all29` tests whether the nearby opposite Layer3 selections are blocking the same-family candidates.
- `target_mt5_0076_replace_nearest_opposite` is the narrowest target proof for the selected residual case.
- A merge candidate requires improved target matching plus no deterioration in matched/reliable counts and gap components.

## Output Files

- `prototype_signal_variant_summary.csv`
- `prototype_full_chain_before_after.csv`
- `prototype_target_mt5_0076_review.csv`
- `prototype_layer3_rescue_decision.csv`
- `signals/<variant>/`
- `dynamic_inputs/<variant>/`
- `dynamic_alignment/<variant>/`
- `mapping/<variant>/`
