# Stage-State Layer3 Displacement Source Audit: mt5_0076

## Scope

- Diagnostic-only audit for `mt5_0076`.
- Reviews Python raw, Layer1/2, Layer3, dynamic execution, MT5 unique ledger, and MT5 stage-state ledger.
- Does not change Python signals, EA behavior, dynamic risk, or mapping.

## Decision

- Source bucket: `maxpos_lifecycle_gap`.
- Secondary bucket: `layer3_selection_policy_gap`.
- Raw exact equivalent count: `1`.
- Layer1/2 exact same-family count: `1`.
- Layer3 exact same-family count: `0`.
- Dynamic exact same-family count: `0`.
- MT5 exact same-family count: `1`.
- Add target without removing opposite accepted: `False`.
- Add target after removing nearest opposite accepted: `True`.
- Current 24h max-pos blockers before target: `2026-03-24 02:00:00 SELL M30 CLOSE/pre_cross;2026-03-24 04:30:00 SELL M30 CLOSE/post_n;2026-03-24 05:00:00 SELL M15 SLOT1/post_n`.
- Target-only exact prototype pass: `True`.
- MT5 target closed before aligned target time: `True`.

Interpretation: Python has a valid raw and Layer1/2 candidate at the aligned target time, but the current Layer3/max-pos path keeps earlier accepted signals under a fixed 24-hour occupancy model. MT5 records the aligned target as an actual same-family ledger signal and its position lifecycle is not represented by that fixed Python occupancy model.

## Max-Pos Summary

| scenario                           | target_candidate_present   | target_accepted_by_current_24h_maxpos   |   target_active_count_before | target_active_blockers_before                                                                                                    | removed_opposite_present   | removed_opposite_accepted   |
|:-----------------------------------|:---------------------------|:----------------------------------------|-----------------------------:|:---------------------------------------------------------------------------------------------------------------------------------|:---------------------------|:----------------------------|
| add_target_no_removal              | True                       | False                                   |                            3 | 2026-03-24 02:00:00 SELL M30 CLOSE/pre_cross;2026-03-24 04:30:00 SELL M30 CLOSE/post_n;2026-03-24 05:00:00 SELL M15 SLOT1/post_n | True                       | True                        |
| add_target_remove_nearest_opposite | True                       | True                                    |                            2 | 2026-03-24 02:00:00 SELL M30 CLOSE/pre_cross;2026-03-24 04:30:00 SELL M30 CLOSE/post_n                                           | False                      | False                       |
| baseline_current_layer3_reapply    | False                      | False                                   |                           -1 |                                                                                                                                  | True                       | True                        |

## Added Target vs Removed Opposite

| field                        | added_target_2026_03_24_1200_buy   | removed_opposite_2026_03_24_0500_sell   |
|:-----------------------------|:-----------------------------------|:----------------------------------------|
| time                         | 2026-03-24 12:00:00                | 2026-03-24 05:00:00                     |
| direction                    | BUY                                | SELL                                    |
| trigger_family               | M15 SLOT1                          | M15 SLOT1                               |
| mode                         | post_n6                            | post_n5                                 |
| variant                      | ea_slot1_replace                   | ea_slot1_replace                        |
| entry                        | 4422.228                           | 4366.186                                |
| stop                         | 4391.32398                         | 4385.57752                              |
| sd                           | 30.904019999999942                 | 19.391520000000128                      |
| source_profit_or_pnl         | -30.904019999999942                | -19.391520000000128                     |
| Bias_5                       | 0.8001778851182048                 | 1.5231475599015465                      |
| Bias_13                      | 0.5211691316700139                 | 3.373790142476365                       |
| Bias_55                      | 7.112104891341796                  | 9.847775757637782                       |
| Bias_5_ea                    | 0.8001778851182048                 | 1.5231475599015465                      |
| layer3_threshold_ea          |                                    | 0.7439216347923595                      |
| layer3_pass_ea               |                                    | True                                    |
| spec_pass                    | True                               | True                                    |
| spec_reason                  | ok                                 | ok                                      |
| nearest_opposite_time        | 2026-03-24 05:00:00                |                                         |
| nearest_opposite_abs_minutes | 420.0                              |                                         |
| cluster_rows                 | 5                                  |                                         |
| cluster_all_negative         | True                               |                                         |
| is_cluster_latest_time       | True                               |                                         |
| is_cluster_max_mode          | True                               |                                         |

## MT5 Lifecycle Context

| signal_anchor_time   | aligned_target_time   | trigger_family   | signal_src                          | mode_family   | dir_norm   |   stage_rows | open_min            | exit_max            |   net_profit | local_exit_reasons                    | deal_reasons   | is_mt5_0076_aligned_target   | open_before_aligned_target   | closed_before_aligned_target   |
|:---------------------|:----------------------|:-----------------|:------------------------------------|:--------------|:-----------|-------------:|:--------------------|:--------------------|-------------:|:--------------------------------------|:---------------|:-----------------------------|:-----------------------------|:-------------------------------|
| 2026.03.24 00:30     | 2026-03-24 02:00:00   | M30 CLOSE        | pre_cross                           | pre_cross     | SELL       |            3 | 2026-03-24 00:30:00 | 2026-03-24 05:41:27 |       108.59 | deal_exit;stage1_tp;stage3_cross_exit | EXPERT;SL      | False                        | True                         | True                           |
| 2026.03.24 03:00     | 2026-03-24 04:30:00   | M15 SLOT1        | post_n3_m15_slot1_replace_or_rescue | post_n        | SELL       |            3 | 2026-03-24 02:45:00 | 2026-03-24 06:22:29 |        19.34 | deal_exit;stage1_tp                   | EXPERT;SL      | False                        | True                         | True                           |
| 2026.03.24 08:30     | 2026-03-24 10:00:00   | M30 CLOSE        | post_n2                             | post_n        | BUY        |            3 | 2026-03-24 08:30:00 | 2026-03-24 11:01:42 |        17.79 | deal_exit;stage1_tp                   | EXPERT;SL      | False                        | True                         | True                           |
| 2026.03.24 10:30     | 2026-03-24 12:00:00   | M15 SLOT1        | post_n5_m15_slot1_replace_or_rescue | post_n        | BUY        |            3 | 2026-03-24 10:15:00 | 2026-03-24 11:01:39 |      -104.7  | deal_exit                             | SL             | True                         | True                         | True                           |

## Compact Timeline

| source_table               | row_time            | mt5_signal_anchor_time   | row_id          | dir_norm   | trigger_family   | mode_family   | mode_or_signal_src                  | variant                 |     profit | stage1_exit   | stage2_exit   | stage3_exit   | stage3_time         |
|:---------------------------|:--------------------|:-------------------------|:----------------|:-----------|:-----------------|:--------------|:------------------------------------|:------------------------|-----------:|:--------------|:--------------|:--------------|:--------------------|
| python_raw_candidates      | 2026-03-24 02:00:00 |                          |                 | SELL       | M30 CLOSE        | pre_cross     | pre_cross                           | m30_base                |  -29.1242  |               |               |               |                     |
| python_layer12_pass        | 2026-03-24 02:00:00 |                          |                 | SELL       | M15 SLOT1        | pre_cross     | pre_cross                           | ea_slot1_replace        |  -29.1242  |               |               |               |                     |
| python_layer3_selected     | 2026-03-24 02:00:00 |                          |                 | SELL       | M30 CLOSE        | pre_cross     | pre_cross                           | ea_slot1_replace        |  -29.1242  |               |               |               |                     |
| python_dynamic_executed    | 2026-03-24 02:00:00 |                          | python_mt5_0087 | SELL       | M15 SLOT1        | pre_cross     | pre_cross                           | ea_slot1_replace        |    5.15693 | 2.0R TP       | trail/SL hit  | SL hit        | 2026-03-24 09:00:00 |
| mt5_unique_ledger          | 2026-03-24 02:00:00 | 2026-03-24 00:30:00      | mt5_0073        | SELL       | M30 CLOSE        | pre_cross     | pre_cross                           |                         |  108.59    |               |               |               |                     |
| python_raw_candidates      | 2026-03-24 03:00:00 |                          |                 | SELL       | M30 CLOSE        | cross         | cross                               | m30_base                |  -54.5842  |               |               |               |                     |
| python_raw_candidates      | 2026-03-24 03:30:00 |                          |                 | SELL       | M30 CLOSE        | post_n        | post_n2                             | m30_base                |  -69.981   |               |               |               |                     |
| python_raw_candidates      | 2026-03-24 04:00:00 |                          |                 | SELL       | M30 CLOSE        | post_n        | post_n3                             | m30_base                |  -37.3384  |               |               |               |                     |
| python_raw_candidates      | 2026-03-24 04:30:00 |                          |                 | SELL       | M30 CLOSE        | post_n        | post_n4                             | m30_base                |  -21.1342  |               |               |               |                     |
| python_layer12_pass        | 2026-03-24 04:30:00 |                          |                 | SELL       | M15 SLOT1        | post_n        | post_n4                             | ea_slot1_replace        |  -21.1342  |               |               |               |                     |
| python_layer3_selected     | 2026-03-24 04:30:00 |                          |                 | SELL       | M30 CLOSE        | post_n        | post_n4                             | ea_slot1_replace        |  -21.1342  |               |               |               |                     |
| python_dynamic_executed    | 2026-03-24 04:30:00 |                          | python_mt5_0088 | SELL       | M15 SLOT1        | post_n        | post_n4                             | ea_slot1_replace        |   -6.46907 | 2.0R TP       | trail/SL hit  | SL hit        | 2026-03-24 08:00:00 |
| mt5_unique_ledger          | 2026-03-24 04:30:00 | 2026-03-24 03:00:00      | mt5_0074        | SELL       | M15 SLOT1        | post_n        | post_n3_m15_slot1_replace_or_rescue |                         |   19.34    |               |               |               |                     |
| python_raw_candidates      | 2026-03-24 05:00:00 |                          |                 | SELL       | M30 CLOSE        | post_n        | post_n5                             | m30_base                |  -20.9125  |               |               |               |                     |
| python_layer12_pass        | 2026-03-24 05:00:00 |                          |                 | SELL       | M15 SLOT1        | post_n        | post_n5                             | ea_slot1_replace        |  -19.3915  |               |               |               |                     |
| python_layer3_selected     | 2026-03-24 05:00:00 |                          |                 | SELL       | M15 SLOT1        | post_n        | post_n5                             | ea_slot1_replace        |  -19.3915  |               |               |               |                     |
| python_stage_result_export | 2026-03-24 05:00:00 |                          |                 | SELL       | M15 SLOT1        | post_n        | post_n5                             | ea_slot1_replace        |    2.58449 | 2.0R TP       | trail/SL hit  | SL hit        | 2026-03-24 08:00:00 |
| python_dynamic_executed    | 2026-03-24 05:00:00 |                          | python_mt5_0089 | SELL       | M15 SLOT1        | post_n        | post_n5                             | ea_slot1_replace        |   -6.46907 | 2.0R TP       | trail/SL hit  | SL hit        | 2026-03-24 08:00:00 |
| python_raw_candidates      | 2026-03-24 05:30:00 |                          |                 | SELL       | M30 CLOSE        | post_n        | post_n6                             | m30_base                |  -35.5565  |               |               |               |                     |
| python_layer12_pass        | 2026-03-24 05:30:00 |                          |                 | SELL       | M15 SLOT1        | post_n        | post_n6                             | ea_slot1_runtime_rescue |  -17.9495  |               |               |               |                     |
| python_raw_candidates      | 2026-03-24 09:30:00 |                          |                 | BUY        | M30 CLOSE        | cross         | cross                               | m30_base                |  -45.7137  |               |               |               |                     |
| python_raw_candidates      | 2026-03-24 10:00:00 |                          |                 | BUY        | M30 CLOSE        | post_n        | post_n2                             | m30_base                |  -14.8732  |               |               |               |                     |
| python_layer12_pass        | 2026-03-24 10:00:00 |                          |                 | BUY        | M15 SLOT1        | post_n        | post_n2                             | ea_slot1_replace        |  -14.8732  |               |               |               |                     |
| mt5_unique_ledger          | 2026-03-24 10:00:00 | 2026-03-24 08:30:00      | mt5_0075        | BUY        | M30 CLOSE        | post_n        | post_n2                             |                         |   17.79    |               |               |               |                     |
| python_raw_candidates      | 2026-03-24 10:30:00 |                          |                 | BUY        | M30 CLOSE        | post_n        | post_n3                             | m30_base                |  -27.9298  |               |               |               |                     |
| python_layer12_pass        | 2026-03-24 10:30:00 |                          |                 | BUY        | M15 SLOT1        | post_n        | post_n3                             | ea_slot1_replace        |  -12.5458  |               |               |               |                     |
| python_raw_candidates      | 2026-03-24 11:00:00 |                          |                 | BUY        | M30 CLOSE        | post_n        | post_n4                             | m30_base                |  -21.5066  |               |               |               |                     |
| python_layer12_pass        | 2026-03-24 11:00:00 |                          |                 | BUY        | M15 SLOT1        | post_n        | post_n4                             | ea_slot1_replace        |  -26.1376  |               |               |               |                     |
| python_raw_candidates      | 2026-03-24 11:30:00 |                          |                 | BUY        | M30 CLOSE        | post_n        | post_n5                             | m30_base                |  -37.7184  |               |               |               |                     |
| python_layer12_pass        | 2026-03-24 11:30:00 |                          |                 | BUY        | M15 SLOT1        | post_n        | post_n5                             | ea_slot1_runtime_rescue |  -18.3634  |               |               |               |                     |
| python_raw_candidates      | 2026-03-24 12:00:00 |                          |                 | BUY        | M30 CLOSE        | post_n        | post_n6                             | m30_base                |  -30.904   |               |               |               |                     |
| python_layer12_pass        | 2026-03-24 12:00:00 |                          |                 | BUY        | M15 SLOT1        | post_n        | post_n6                             | ea_slot1_replace        |  -30.904   |               |               |               |                     |
| mt5_unique_ledger          | 2026-03-24 12:00:00 | 2026-03-24 10:30:00      | mt5_0076        | BUY        | M15 SLOT1        | post_n        | post_n5_m15_slot1_replace_or_rescue |                         | -104.7     |               |               |               |                     |
| python_raw_candidates      | 2026-03-24 14:30:00 |                          |                 | SELL       | M30 CLOSE        | pre_cross     | pre_cross                           | m30_base                |  -18.8457  |               |               |               |                     |
| python_layer12_pass        | 2026-03-24 14:30:00 |                          |                 | SELL       | M15 SLOT1        | pre_cross     | pre_cross                           | ea_slot1_replace        |  -18.8457  |               |               |               |                     |
| python_raw_candidates      | 2026-03-24 15:30:00 |                          |                 | SELL       | M30 CLOSE        | cross         | cross                               | m30_base                |  -25.38    |               |               |               |                     |
| python_layer12_pass        | 2026-03-24 15:30:00 |                          |                 | SELL       | M15 SLOT1        | cross         | cross                               | ea_slot1_replace        |  -25.38    |               |               |               |                     |
| python_raw_candidates      | 2026-03-24 16:00:00 |                          |                 | BUY        | M30 CLOSE        | cross         | cross                               | m30_base                |   -9.24896 |               |               |               |                     |
| python_layer12_pass        | 2026-03-24 16:00:00 |                          |                 | BUY        | M15 SLOT1        | cross         | cross                               | ea_slot1_replace        |   -9.24896 |               |               |               |                     |

## Gates

- `main_signal_change_gate_open = False`
- `ea_behavior_gate_open = False`
- `mapping_change_gate_open = False`
- `merge_gate_pass = False`
- Recommended next action: `prototype_lifecycle_aware_maxpos_probe_for_layer3_rescue_candidates`.

## Output Files

- `layer3_displacement_timeline_mt5_0076.csv`
- `layer3_displacement_added_vs_removed_fields.csv`
- `layer3_displacement_maxpos_probe.csv`
- `layer3_displacement_maxpos_summary.csv`
- `layer3_displacement_mt5_lifecycle.csv`
- `layer3_displacement_source_decision.csv`
