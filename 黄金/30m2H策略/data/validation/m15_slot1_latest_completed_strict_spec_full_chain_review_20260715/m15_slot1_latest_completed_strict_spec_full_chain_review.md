# M15 SLOT1 latest-completed strict-spec full-chain review

## 结论

- 本版本在 latest-completed bar 语义后，强制重算 `sd/spec_pass/spec_reason`，并在 Layer3/max-pos 前过滤 actual `sd` 超出 `[5,35]` 的行。
- 该脚本不修改 EA，不覆盖 current metadatafix 或 broad latest-completed 快照。
- strict direct dynamic gap delta vs current = `-1162.651665`；负数表示 Python-MT5 相对 MT5 更低。
- 是否能进入主线，取决于 strict 版本是否同时满足：target 假阳性消失、invalid spec rows 不放大、mapping/gap 不显著恶化。

## Strict Prototype Metrics

| variant                                            | use_q2_early   |   mt5_time_shift_minutes |   m30_rows |   h2_rows |   m15_rows |   layer1_pass_bars |   early_bar_count |   raw_candidates |   accepted |   layer3_threshold |   picked_before_maxpos |   picked_after_maxpos |   m15_replace_changed |   m15_rescued_count | output_dir                                                                                                                                                        |   trade_rows |   unique_signal_rows |   wins |   losses |   win_rate_pct |   total_dollars |   final_balance_python_multiplier5 |   stage1_exit_sl_count |   stage2_exit_sl_count |   stage3_exit_sl_count |   any_stage_sl_count |   all_stage_sl_count | mode_counts                                                                      |
|:---------------------------------------------------|:---------------|-------------------------:|-----------:|----------:|-----------:|-------------------:|------------------:|-----------------:|-----------:|-------------------:|-----------------------:|----------------------:|----------------------:|--------------------:|:------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------:|---------------------:|-------:|---------:|---------------:|----------------:|-----------------------------------:|-----------------------:|-----------------------:|-----------------------:|---------------------:|---------------------:|:---------------------------------------------------------------------------------|
| python_h2_context_q2early_latest_slot1_strict_spec | True           |                       90 |      97640 |     26080 |      98901 |               5392 |               341 |              711 |        337 |           0.324227 |                    129 |                    95 |                     0 |                  28 | F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\m15_slot1_latest_completed_strict_spec_prototype_20260715\signals\python_h2_context_q2early_latest_slot1_strict_spec |           95 |                   95 |     45 |       50 |        47.3684 |         362.162 |                            2310.81 |                     50 |                     61 |                     45 |                   79 |                   35 | cross:12; post_n2:7; post_n3:14; post_n4:17; post_n5:12; post_n6:9; pre_cross:24 |

## Dynamic Risk Summary

| run                          | source     |   trade_count |   final_balance |   dynamic_total_profit |   win_rate_pct |   any_stage_sl_count |   all_stage_sl_count |   avg_stop_pts_spec |
|:-----------------------------|:-----------|--------------:|----------------:|-----------------------:|---------------:|---------------------:|---------------------:|--------------------:|
| current_metadatafix          | python_mt5 |            98 |        1969.91  |               1469.91  |        46.9388 |                   80 |                   33 |             15.1367 |
| current_metadatafix          | mt5_ledger |            78 |        3811.35  |               3311.35  |        42.3077 |                   72 |                   36 |             15.9843 |
| latest_completed_broad       | python_mt5 |           107 |         651.151 |                151.151 |        40.1869 |                   92 |                   41 |             17.3771 |
| latest_completed_broad       | mt5_ledger |            78 |        3811.35  |               3311.35  |        42.3077 |                   72 |                   36 |             15.9843 |
| latest_completed_strict_spec | python_mt5 |            95 |         807.262 |                307.262 |        41.0526 |                   79 |                   35 |             15.8794 |
| latest_completed_strict_spec | mt5_ledger |            78 |        3811.35  |               3311.35  |        42.3077 |                   72 |                   36 |             15.9843 |

## Mapping Summary

| run                          |   python_trades |   mt5_trades |   matched_unique |   reliable_tier_matched |   relaxed_tier_matched |   python_unmatched |   mt5_unmatched |   matched_python_profit |   matched_mt5_profit |   matched_profit_diff |
|:-----------------------------|----------------:|-------------:|-----------------:|------------------------:|-----------------------:|-------------------:|----------------:|------------------------:|---------------------:|----------------------:|
| current_metadatafix          |              98 |           78 |               57 |                      29 |                     28 |                 41 |              21 |                543.301  |              2631.43 |              -2088.13 |
| latest_completed_broad       |             107 |           78 |               63 |                      33 |                     30 |                 44 |              15 |                 53.7014 |              2980.34 |              -2926.64 |
| latest_completed_strict_spec |              95 |           78 |               59 |                      30 |                     29 |                 36 |              19 |                139.996  |              2758.43 |              -2618.43 |

## Gap Components

| run                          |   python_mt5_total_profit |   mt5_total_profit |   direct_dynamic_gap_python_minus_mt5 |   matched_profit_diff |   python_unmatched_gap_effect |   mt5_unmatched_gap_effect |   signal_set_gap_effect |   reconstructed_dynamic_gap |
|:-----------------------------|--------------------------:|-------------------:|--------------------------------------:|----------------------:|------------------------------:|---------------------------:|------------------------:|----------------------------:|
| current_metadatafix          |                  1469.91  |            3311.35 |                              -1841.44 |              -2088.13 |                      926.613  |                    -679.92 |                 246.693 |                    -1841.44 |
| latest_completed_broad       |                   151.151 |            3311.35 |                              -3160.2  |              -2926.64 |                       97.4493 |                    -331.01 |                -233.561 |                    -3160.2  |
| latest_completed_strict_spec |                   307.262 |            3311.35 |                              -3004.09 |              -2618.43 |                      167.266  |                    -552.92 |                -385.654 |                    -3004.09 |

## Invalid Spec Counts

| run                          | layer          |   rows |   invalid_spec_rows |   min_dist |   max_dist |
|:-----------------------------|:---------------|-------:|--------------------:|-----------:|-----------:|
| current_metadatafix          | accepted       |    379 |                   3 |    3.93366 |    42.6899 |
| current_metadatafix          | picked         |     98 |                   2 |    5.31557 |    42.6899 |
| current_metadatafix          | dynamic_inputs |     98 |                   2 |    5.31557 |    42.6899 |
| latest_completed_broad       | accepted       |    367 |                  30 |    0.57656 |    65.6957 |
| latest_completed_broad       | picked         |    107 |                  14 |    0.75003 |    65.6957 |
| latest_completed_broad       | dynamic_inputs |    107 |                  14 |    0.75003 |    65.6957 |
| latest_completed_strict_spec | accepted       |    337 |                   0 |    5.0177  |    34.9668 |
| latest_completed_strict_spec | picked         |     95 |                   0 |    5.17256 |    34.9668 |
| latest_completed_strict_spec | dynamic_inputs |     95 |                   0 |    5.17256 |    34.9668 |

## Target Case

| run                          |   target_dynamic_trade_rows |   target_mapping_rows | target_modes   | target_variants         |   target_dynamic_total_sum |
|:-----------------------------|----------------------------:|----------------------:|:---------------|:------------------------|---------------------------:|
| current_metadatafix          |                           1 |                     0 | post_n6        | ea_slot1_runtime_rescue |                    201.851 |
| latest_completed_broad       |                           0 |                     0 |                |                         |                      0     |
| latest_completed_strict_spec |                           0 |                     0 |                |                         |                      0     |

## Strict Top Python-Unmatched

| side             | py_trade_id     | date                | dir_norm   | trigger_family   | mode_family   | mode      | variant                 |   dynamic_total_$ |   effect |   abs_effect |
|:-----------------|:----------------|:--------------------|:-----------|:-----------------|:--------------|:----------|:------------------------|------------------:|---------:|-------------:|
| python_unmatched | python_mt5_0074 | 2025-10-17 15:00:00 | SELL       | M15 SLOT1        | post_n        | post_n4   | ea_slot1_replace        |           92.7892 |  92.7892 |      92.7892 |
| python_unmatched | python_mt5_0066 | 2025-04-22 16:00:00 | SELL       | M15 SLOT1        | post_n        | post_n4   | ea_slot1_replace        |           72.8408 |  72.8408 |      72.8408 |
| python_unmatched | python_mt5_0006 | 2020-03-13 15:30:00 | SELL       | M30 CLOSE        | pre_cross     | pre_cross | m30_base                |           64.2283 |  64.2283 |      64.2283 |
| python_unmatched | python_mt5_0089 | 2026-05-28 14:30:00 | BUY        | M15 SLOT1        | pre_cross     | pre_cross | ea_slot1_replace        |           52.3003 |  52.3003 |      52.3003 |
| python_unmatched | python_mt5_0063 | 2025-04-21 02:00:00 | BUY        | M15 SLOT1        | post_n        | post_n5   | ea_slot1_replace        |           33.0231 |  33.0231 |      33.0231 |
| python_unmatched | python_mt5_0075 | 2025-10-20 03:00:00 | BUY        | M15 SLOT1        | pre_cross     | pre_cross | ea_slot1_replace        |          -25.4515 | -25.4515 |      25.4515 |
| python_unmatched | python_mt5_0076 | 2025-10-20 07:30:00 | SELL       | M15 SLOT1        | cross         | cross     | ea_slot1_replace        |          -22.251  | -22.251  |      22.251  |
| python_unmatched | python_mt5_0079 | 2025-12-26 19:00:00 | SELL       | M15 SLOT1        | pre_cross     | pre_cross | ea_slot1_runtime_rescue |          -21.2159 | -21.2159 |      21.2159 |
| python_unmatched | python_mt5_0022 | 2020-07-28 08:00:00 | SELL       | M30 CLOSE        | post_n        | post_n2   | m30_base                |           19.344  |  19.344  |      19.344  |
| python_unmatched | python_mt5_0095 | 2026-06-30 09:30:00 | BUY        | M15 SLOT1        | post_n        | post_n2   | ea_slot1_replace        |          -17.8187 | -17.8187 |      17.8187 |
| python_unmatched | python_mt5_0045 | 2022-11-16 11:30:00 | BUY        | M15 SLOT1        | post_n        | post_n4   | ea_slot1_replace        |          -17.5835 | -17.5835 |      17.5835 |
| python_unmatched | python_mt5_0016 | 2020-03-25 11:30:00 | BUY        | M30 CLOSE        | pre_cross     | pre_cross | m30_base                |          -17.3277 | -17.3277 |      17.3277 |

## Strict Top MT5-Unmatched

| side          | mt5_trade_id   | signal_anchor_time   | aligned_time        | dir_norm   | trigger_family   | mode_family   | signal_src                            |   net_profit |   effect |   abs_effect |
|:--------------|:---------------|:---------------------|:--------------------|:-----------|:-----------------|:--------------|:--------------------------------------|-------------:|---------:|-------------:|
| mt5_unmatched | mt5_0068       | 2026-02-02 23:30:00  | 2026-02-03 01:00:00 | BUY        | M15 SLOT1        | pre_cross     | pre_cross_m15_slot1_replace_or_rescue |       230.63 |  -230.63 |       230.63 |
| mt5_unmatched | mt5_0074       | 2026-04-02 01:30:00  | 2026-04-02 03:00:00 | SELL       | M15 SLOT1        | pre_cross     | pre_cross_m15_slot1_replace_or_rescue |       171.9  |  -171.9  |       171.9  |
| mt5_unmatched | mt5_0005       | 2020-03-13 16:00:00  | 2020-03-13 17:30:00 | SELL       | M15 SLOT1        | post_n        | post_n3_m15_slot1_replace_or_rescue   |       161.09 |  -161.09 |       161.09 |
| mt5_unmatched | mt5_0019       | 2020-08-04 17:30:00  | 2020-08-04 19:00:00 | BUY        | M15 SLOT1        | post_n        | post_n6_m15_slot1_replace_or_rescue   |       128.85 |  -128.85 |       128.85 |
| mt5_unmatched | mt5_0057       | 2025-10-20 12:00:00  | 2025-10-20 13:30:00 | BUY        | M30 CLOSE        | post_n        | post_n4                               |       110.91 |  -110.91 |       110.91 |
| mt5_unmatched | mt5_0065       | 2026-02-02 15:00:00  | 2026-02-02 16:30:00 | BUY        | M15 SLOT1        | post_n        | post_n4_m15_slot1_replace_or_rescue   |       -88.35 |    88.35 |        88.35 |
| mt5_unmatched | mt5_0026       | 2021-11-10 15:00:00  | 2021-11-10 16:30:00 | BUY        | M30 CLOSE        | post_n        | post_n3                               |       -75.19 |    75.19 |        75.19 |
| mt5_unmatched | mt5_0070       | 2026-03-23 16:00:00  | 2026-03-23 17:30:00 | BUY        | M15 SLOT1        | post_n        | post_n6_m15_slot1_replace_or_rescue   |       -70.14 |    70.14 |        70.14 |
| mt5_unmatched | mt5_0063       | 2026-01-27 06:00:00  | 2026-01-27 07:30:00 | BUY        | M30 CLOSE        | post_n        | post_n5                               |       -57.54 |    57.54 |        57.54 |
| mt5_unmatched | mt5_0076       | 2026-06-11 06:00:00  | 2026-06-11 07:30:00 | BUY        | M15 SLOT1        | pre_cross     | pre_cross_m15_slot1_replace_or_rescue |       -55.28 |    55.28 |        55.28 |
| mt5_unmatched | mt5_0050       | 2025-09-09 15:00:00  | 2025-09-09 16:30:00 | SELL       | M30 CLOSE        | pre_cross     | pre_cross                             |        54.33 |   -54.33 |        54.33 |
| mt5_unmatched | mt5_0069       | 2026-02-24 01:30:00  | 2026-02-24 03:00:00 | SELL       | M15 SLOT1        | pre_cross     | pre_cross_m15_slot1_replace_or_rescue |        50.4  |   -50.4  |        50.4  |
