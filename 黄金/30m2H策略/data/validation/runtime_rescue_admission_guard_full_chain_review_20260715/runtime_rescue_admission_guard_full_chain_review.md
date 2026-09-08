# Runtime Rescue Admission Guard Prototype

## Decision

- No variant passes the merge gate. Best local diagnostic candidate: `python_h2_context_q2early_require_selected_m15_mode`.
- Merge gate used here requires both target false positives removed, no new invalid spec rows, matched_unique not lower, direct gap delta >= -50, and matched_profit_diff delta >= -50.
- This review changes only Python-MT5 signal generation prototypes; EA behavior and current metadatafix snapshots are not overwritten.
- A candidate still needs manual review before merging into the mainline because runtime_rescue also affects Layer3 ranking and max-pos.

## Decision Matrix

| run                                                 | target_20251017_removed   | target_20251021_removed   |   trade_count_delta |   final_balance_delta |   matched_unique_delta |   python_unmatched_delta |   mt5_unmatched_delta |   direct_gap_delta |   matched_profit_diff_delta |   dynamic_invalid_spec_delta |
|:----------------------------------------------------|:--------------------------|:--------------------------|--------------------:|----------------------:|-----------------------:|-------------------------:|----------------------:|-------------------:|----------------------------:|-----------------------------:|
| python_h2_context_q2early_runtime_rescue_wide_only  | True                      | False                     |                  -4 |              -94.2342 |                     -1 |                       -3 |                     1 |           -94.2342 |                    -21.3889 |                            0 |
| python_h2_context_q2early_no_stop_side_mirror       | True                      | False                     |                  -1 |             -157.154  |                      0 |                       -1 |                     0 |          -157.154  |                    -28.1872 |                            0 |
| python_h2_context_q2early_require_selected_m15_mode | True                      | False                     |                  -1 |             -155.875  |                      0 |                       -1 |                     0 |          -155.875  |                    -26.9082 |                            0 |
| python_h2_context_q2early_combined_runtime_guard    | True                      | False                     |                  -4 |              -99.5407 |                     -1 |                       -3 |                     1 |           -99.5407 |                    -26.6953 |                            0 |

## Signal Metrics

| variant                                             | use_q2_early   |   mt5_time_shift_minutes |   m30_rows |   h2_rows |   m15_rows |   layer1_pass_bars |   early_bar_count |   raw_candidates |   accepted |   layer3_threshold |   picked_before_maxpos |   picked_after_maxpos |   m15_replace_changed |   m15_rescued_count | output_dir                                                                                                                                                         |   trade_rows |   unique_signal_rows |   wins |   losses |   win_rate_pct |   total_dollars |   final_balance_python_multiplier5 |   stage1_exit_sl_count |   stage2_exit_sl_count |   stage3_exit_sl_count |   any_stage_sl_count |   all_stage_sl_count | mode_counts                                                                       |
|:----------------------------------------------------|:---------------|-------------------------:|-----------:|----------:|-----------:|-------------------:|------------------:|-----------------:|-----------:|-------------------:|-----------------------:|----------------------:|----------------------:|--------------------:|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------:|---------------------:|-------:|---------:|---------------:|----------------:|-----------------------------------:|-----------------------:|-----------------------:|-----------------------:|---------------------:|---------------------:|:----------------------------------------------------------------------------------|
| python_h2_context_q2early_runtime_rescue_wide_only  | True           |                       90 |      97640 |     26080 |      98901 |               5392 |               341 |              711 |        361 |           0.339134 |                    130 |                    94 |                   150 |                  22 | F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\runtime_rescue_admission_guard_full_chain_review_20260715\signals\python_h2_context_q2early_runtime_rescue_wide_only  |           94 |                   94 |     49 |       45 |        52.1277 |         527.79  |                            3138.95 |                     45 |                     60 |                     41 |                   77 |                   31 | cross:17; post_n2:7; post_n3:10; post_n4:13; post_n5:13; post_n6:9; pre_cross:25  |
| python_h2_context_q2early_no_stop_side_mirror       | True           |                       90 |      97640 |     26080 |      98901 |               5392 |               341 |              711 |        375 |           0.339134 |                    133 |                    97 |                   150 |                  36 | F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\runtime_rescue_admission_guard_full_chain_review_20260715\signals\python_h2_context_q2early_no_stop_side_mirror       |           97 |                   97 |     49 |       48 |        50.5155 |         517.128 |                            3085.64 |                     48 |                     63 |                     43 |                   80 |                   33 | cross:17; post_n2:7; post_n3:10; post_n4:13; post_n5:14; post_n6:11; pre_cross:25 |
| python_h2_context_q2early_require_selected_m15_mode | True           |                       90 |      97640 |     26080 |      98901 |               5392 |               341 |              711 |        368 |           0.332351 |                    132 |                    97 |                   150 |                  29 | F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\runtime_rescue_admission_guard_full_chain_review_20260715\signals\python_h2_context_q2early_require_selected_m15_mode |           97 |                   97 |     49 |       48 |        50.5155 |         519.226 |                            3096.13 |                     48 |                     63 |                     43 |                   80 |                   33 | cross:16; post_n2:7; post_n3:10; post_n4:14; post_n5:14; post_n6:11; pre_cross:25 |
| python_h2_context_q2early_combined_runtime_guard    | True           |                       90 |      97640 |     26080 |      98901 |               5392 |               341 |              711 |        356 |           0.335742 |                    129 |                    94 |                   150 |                  17 | F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\runtime_rescue_admission_guard_full_chain_review_20260715\signals\python_h2_context_q2early_combined_runtime_guard    |           94 |                   94 |     49 |       45 |        52.1277 |         529.888 |                            3149.44 |                     45 |                     60 |                     41 |                   77 |                   31 | cross:16; post_n2:7; post_n3:10; post_n4:14; post_n5:13; post_n6:9; pre_cross:25  |

## Dynamic Risk

| run                                                 | source     |   trade_count |   final_balance |   dynamic_total_profit |   win_rate_pct |   any_stage_sl_count |   all_stage_sl_count |   avg_stop_pts_spec |
|:----------------------------------------------------|:-----------|--------------:|----------------:|-----------------------:|---------------:|---------------------:|---------------------:|--------------------:|
| current_metadatafix                                 | python_mt5 |            98 |         1969.91 |                1469.91 |        46.9388 |                   80 |                   33 |             15.1367 |
| current_metadatafix                                 | mt5_ledger |            78 |         3811.35 |                3311.35 |        42.3077 |                   72 |                   36 |             15.9843 |
| python_h2_context_q2early_runtime_rescue_wide_only  | python_mt5 |            94 |         1875.68 |                1375.68 |        46.8085 |                   77 |                   31 |             15.4267 |
| python_h2_context_q2early_runtime_rescue_wide_only  | mt5_ledger |            78 |         3811.35 |                3311.35 |        42.3077 |                   72 |                   36 |             15.9843 |
| python_h2_context_q2early_no_stop_side_mirror       | python_mt5 |            97 |         1812.76 |                1312.76 |        46.3918 |                   80 |                   33 |             15.2004 |
| python_h2_context_q2early_no_stop_side_mirror       | mt5_ledger |            78 |         3811.35 |                3311.35 |        42.3077 |                   72 |                   36 |             15.9843 |
| python_h2_context_q2early_require_selected_m15_mode | python_mt5 |            97 |         1814.04 |                1314.04 |        46.3918 |                   80 |                   33 |             15.2221 |
| python_h2_context_q2early_require_selected_m15_mode | mt5_ledger |            78 |         3811.35 |                3311.35 |        42.3077 |                   72 |                   36 |             15.9843 |
| python_h2_context_q2early_combined_runtime_guard    | python_mt5 |            94 |         1870.37 |                1370.37 |        46.8085 |                   77 |                   31 |             15.449  |
| python_h2_context_q2early_combined_runtime_guard    | mt5_ledger |            78 |         3811.35 |                3311.35 |        42.3077 |                   72 |                   36 |             15.9843 |

## Mapping

| run                                                 |   python_trades |   mt5_trades |   matched_unique |   reliable_tier_matched |   relaxed_tier_matched |   python_unmatched |   mt5_unmatched |   matched_python_profit |   matched_mt5_profit |   matched_profit_diff |
|:----------------------------------------------------|----------------:|-------------:|-----------------:|------------------------:|-----------------------:|-------------------:|----------------:|------------------------:|---------------------:|----------------------:|
| current_metadatafix                                 |              98 |           78 |               57 |                      29 |                     28 |                 41 |              21 |                 543.301 |              2631.43 |              -2088.13 |
| python_h2_context_q2early_runtime_rescue_wide_only  |              94 |           78 |               56 |                      29 |                     27 |                 38 |              22 |                 562.272 |              2671.79 |              -2109.52 |
| python_h2_context_q2early_no_stop_side_mirror       |              97 |           78 |               57 |                      29 |                     28 |                 40 |              21 |                 515.114 |              2631.43 |              -2116.32 |
| python_h2_context_q2early_require_selected_m15_mode |              97 |           78 |               57 |                      30 |                     27 |                 40 |              21 |                 516.393 |              2631.43 |              -2115.04 |
| python_h2_context_q2early_combined_runtime_guard    |              94 |           78 |               56 |                      30 |                     26 |                 38 |              22 |                 556.966 |              2671.79 |              -2114.82 |

## Gap Components

| run                                                 |   python_mt5_total_profit |   mt5_total_profit |   direct_dynamic_gap_python_minus_mt5 |   matched_profit_diff |   python_unmatched_gap_effect |   mt5_unmatched_gap_effect |   signal_set_gap_effect |   reconstructed_dynamic_gap |
|:----------------------------------------------------|--------------------------:|-------------------:|--------------------------------------:|----------------------:|------------------------------:|---------------------------:|------------------------:|----------------------------:|
| current_metadatafix                                 |                   1469.91 |            3311.35 |                              -1841.44 |              -2088.13 |                       926.613 |                    -679.92 |                 246.693 |                    -1841.44 |
| python_h2_context_q2early_runtime_rescue_wide_only  |                   1375.68 |            3311.35 |                              -1935.67 |              -2109.52 |                       813.407 |                    -639.56 |                 173.847 |                    -1935.67 |
| python_h2_context_q2early_no_stop_side_mirror       |                   1312.76 |            3311.35 |                              -1998.59 |              -2116.32 |                       797.646 |                    -679.92 |                 117.726 |                    -1998.59 |
| python_h2_context_q2early_require_selected_m15_mode |                   1314.04 |            3311.35 |                              -1997.31 |              -2115.04 |                       797.646 |                    -679.92 |                 117.726 |                    -1997.31 |
| python_h2_context_q2early_combined_runtime_guard    |                   1370.37 |            3311.35 |                              -1940.98 |              -2114.82 |                       813.407 |                    -639.56 |                 173.847 |                    -1940.98 |

## Target Cases

| run                                                 | target                        | target_time         |   dynamic_trade_rows |   mapping_rows | modes     | variants                |   dynamic_total_sum | match_tiers   |
|:----------------------------------------------------|:------------------------------|:--------------------|---------------------:|---------------:|:----------|:------------------------|--------------------:|:--------------|
| current_metadatafix                                 | target_20251017_no_signal_dir | 2025-10-17 11:00:00 |                    1 |              0 | pre_cross | ea_slot1_runtime_rescue |             189.621 |               |
| current_metadatafix                                 | target_20251021_spec_fail     | 2025-10-21 10:00:00 |                    1 |              0 | post_n6   | ea_slot1_runtime_rescue |             201.851 |               |
| python_h2_context_q2early_runtime_rescue_wide_only  | target_20251017_no_signal_dir | 2025-10-17 11:00:00 |                    0 |              0 |           |                         |               0     |               |
| python_h2_context_q2early_runtime_rescue_wide_only  | target_20251021_spec_fail     | 2025-10-21 10:00:00 |                    1 |              0 | post_n6   | ea_slot1_runtime_rescue |             182.251 |               |
| python_h2_context_q2early_no_stop_side_mirror       | target_20251017_no_signal_dir | 2025-10-17 11:00:00 |                    0 |              0 |           |                         |               0     |               |
| python_h2_context_q2early_no_stop_side_mirror       | target_20251021_spec_fail     | 2025-10-21 10:00:00 |                    1 |              0 | post_n6   | ea_slot1_runtime_rescue |             182.251 |               |
| python_h2_context_q2early_require_selected_m15_mode | target_20251017_no_signal_dir | 2025-10-17 11:00:00 |                    0 |              0 |           |                         |               0     |               |
| python_h2_context_q2early_require_selected_m15_mode | target_20251021_spec_fail     | 2025-10-21 10:00:00 |                    1 |              0 | post_n6   | ea_slot1_runtime_rescue |             182.251 |               |
| python_h2_context_q2early_combined_runtime_guard    | target_20251017_no_signal_dir | 2025-10-17 11:00:00 |                    0 |              0 |           |                         |               0     |               |
| python_h2_context_q2early_combined_runtime_guard    | target_20251021_spec_fail     | 2025-10-21 10:00:00 |                    1 |              0 | post_n6   | ea_slot1_runtime_rescue |             182.251 |               |

## Invalid Spec Counts

| run                                                 |   accepted_invalid_spec_rows |   picked_invalid_spec_rows |   dynamic_invalid_spec_rows |
|:----------------------------------------------------|-----------------------------:|---------------------------:|----------------------------:|
| current_metadatafix                                 |                            3 |                          2 |                           2 |
| python_h2_context_q2early_runtime_rescue_wide_only  |                            3 |                          2 |                           2 |
| python_h2_context_q2early_no_stop_side_mirror       |                            3 |                          2 |                           2 |
| python_h2_context_q2early_require_selected_m15_mode |                            3 |                          2 |                           2 |
| python_h2_context_q2early_combined_runtime_guard    |                            3 |                          2 |                           2 |

## Interpretation

- `runtime_rescue_wide_only` tests whether rejecting original `too_tight` rescues is enough to remove the `2025-10-17` false positive.
- `no_stop_side_mirror` tests whether rejecting selected M15 entries that put the old stop on the wrong side is enough.
- `require_selected_m15_mode` tests whether M15 pre_cross/cross rows must be true M15 signal rows instead of inheriting M30 mode.
- `combined_runtime_guard` applies all three guards and is expected to be conservative.
