# M15 SLOT1 latest-completed full-chain review

## 结论

- 本报告把 latest-completed prototype 接入 dynamic risk、MT5 ledger mapping 和 gap components；没有修改 EA，也没有覆盖当前主线快照。
- `2025-10-21 10:00` 目标假阳性在 prototype dynamic/mapping 中消失。
- direct dynamic gap delta = `-1318.763390`，signal-set gap delta = `-480.253527`；正数表示 Python-MT5 相对 MT5 更高，负数表示更低。
- 本报告未重跑 runtime-style Stage-exit adjustment；若 mapping/gap 明显收敛，再进入更重的 runtime-style rerun。

## Dynamic Risk Before/After

| run                    | source     |   trade_count |   final_balance |   dynamic_total_profit |   win_rate_pct |   any_stage_sl_count |   all_stage_sl_count |   avg_stop_pts_spec |
|:-----------------------|:-----------|--------------:|----------------:|-----------------------:|---------------:|---------------------:|---------------------:|--------------------:|
| current_metadatafix    | python_mt5 |            98 |        1969.91  |               1469.91  |        46.9388 |                   80 |                   33 |             15.1367 |
| current_metadatafix    | mt5_ledger |            78 |        3811.35  |               3311.35  |        42.3077 |                   72 |                   36 |             15.9843 |
| latest_completed_proto | python_mt5 |           107 |         651.151 |                151.151 |        40.1869 |                   92 |                   41 |             17.3771 |
| latest_completed_proto | mt5_ledger |            78 |        3811.35  |               3311.35  |        42.3077 |                   72 |                   36 |             15.9843 |

## Mapping Before/After

| run                    |   python_trades |   mt5_trades |   matched_unique |   reliable_tier_matched |   relaxed_tier_matched |   python_unmatched |   mt5_unmatched |   matched_python_profit |   matched_mt5_profit |   matched_profit_diff |
|:-----------------------|----------------:|-------------:|-----------------:|------------------------:|-----------------------:|-------------------:|----------------:|------------------------:|---------------------:|----------------------:|
| current_metadatafix    |              98 |           78 |               57 |                      29 |                     28 |                 41 |              21 |                543.301  |              2631.43 |              -2088.13 |
| latest_completed_proto |             107 |           78 |               63 |                      33 |                     30 |                 44 |              15 |                 53.7014 |              2980.34 |              -2926.64 |

## Gap Components

| run                    |   python_mt5_total_profit |   mt5_total_profit |   direct_dynamic_gap_python_minus_mt5 |   matched_profit_diff |   python_unmatched_gap_effect |   mt5_unmatched_gap_effect |   signal_set_gap_effect |   reconstructed_dynamic_gap |
|:-----------------------|--------------------------:|-------------------:|--------------------------------------:|----------------------:|------------------------------:|---------------------------:|------------------------:|----------------------------:|
| current_metadatafix    |                  1469.91  |            3311.35 |                              -1841.44 |              -2088.13 |                      926.613  |                    -679.92 |                 246.693 |                    -1841.44 |
| latest_completed_proto |                   151.151 |            3311.35 |                              -3160.2  |              -2926.64 |                       97.4493 |                    -331.01 |                -233.561 |                    -3160.2  |

## Target Case Before/After

| run                    |   target_dynamic_trade_rows |   target_mapping_rows | target_modes   | target_variants         |   target_dynamic_total_sum | target_match_tiers   |
|:-----------------------|----------------------------:|----------------------:|:---------------|:------------------------|---------------------------:|:---------------------|
| current_metadatafix    |                           1 |                     0 | post_n6        | ea_slot1_runtime_rescue |                    201.851 |                      |
| latest_completed_proto |                           0 |                     0 |                |                         |                      0     |                      |

## Top Prototype Python-Unmatched

| side             | py_trade_id     | date                | dir_norm   | trigger_family   | mode_family   | mode      | variant                 |   dynamic_total_$ |   effect |   abs_effect |
|:-----------------|:----------------|:--------------------|:-----------|:-----------------|:--------------|:----------|:------------------------|------------------:|---------:|-------------:|
| python_unmatched | python_mt5_0072 | 2025-04-22 16:00:00 | SELL       | M15 SLOT1        | post_n        | post_n4   | ea_slot1_replace        |           72.8408 |  72.8408 |      72.8408 |
| python_unmatched | python_mt5_0007 | 2020-03-13 15:30:00 | SELL       | M30 CLOSE        | pre_cross     | pre_cross | m30_base                |           64.2283 |  64.2283 |      64.2283 |
| python_unmatched | python_mt5_0054 | 2023-03-21 09:30:00 | SELL       | M15 SLOT1        | post_n        | post_n3   | ea_slot1_replace        |           42.6724 |  42.6724 |      42.6724 |
| python_unmatched | python_mt5_0100 | 2026-05-28 14:30:00 | BUY        | M15 SLOT1        | pre_cross     | pre_cross | ea_slot1_replace        |           42.6086 |  42.6086 |      42.6086 |
| python_unmatched | python_mt5_0069 | 2025-04-21 02:00:00 | BUY        | M15 SLOT1        | post_n        | post_n5   | ea_slot1_replace        |           33.0231 |  33.0231 |      33.0231 |
| python_unmatched | python_mt5_0083 | 2025-10-20 03:00:00 | BUY        | M15 SLOT1        | pre_cross     | pre_cross | ea_slot1_replace        |          -20.824  | -20.824  |      20.824  |
| python_unmatched | python_mt5_0045 | 2022-11-14 18:00:00 | BUY        | M15 SLOT1        | post_n        | post_n5   | ea_slot1_runtime_rescue |           19.4505 |  19.4505 |      19.4505 |
| python_unmatched | python_mt5_0023 | 2020-07-28 08:00:00 | SELL       | M30 CLOSE        | post_n        | post_n2   | m30_base                |           19.344  |  19.344  |      19.344  |
| python_unmatched | python_mt5_0081 | 2025-10-17 14:00:00 | SELL       | M15 SLOT1        | post_n        | post_n2   | ea_slot1_runtime_rescue |           18.4722 |  18.4722 |      18.4722 |
| python_unmatched | python_mt5_0087 | 2025-12-26 19:00:00 | SELL       | M15 SLOT1        | pre_cross     | pre_cross | ea_slot1_runtime_rescue |          -18.3871 | -18.3871 |      18.3871 |
| python_unmatched | python_mt5_0048 | 2022-11-16 12:00:00 | BUY        | M15 SLOT1        | post_n        | post_n5   | ea_slot1_replace        |          -17.8958 | -17.8958 |      17.8958 |
| python_unmatched | python_mt5_0049 | 2022-11-16 12:30:00 | BUY        | M15 SLOT1        | post_n        | post_n6   | ea_slot1_runtime_rescue |          -17.7255 | -17.7255 |      17.7255 |

## Top Prototype MT5-Unmatched

| side          | mt5_trade_id   | signal_anchor_time   | aligned_time        | dir_norm   | trigger_family   | mode_family   | signal_src                            |   net_profit |   effect |   abs_effect |
|:--------------|:---------------|:---------------------|:--------------------|:-----------|:-----------------|:--------------|:--------------------------------------|-------------:|---------:|-------------:|
| mt5_unmatched | mt5_0068       | 2026-02-02 23:30:00  | 2026-02-03 01:00:00 | BUY        | M15 SLOT1        | pre_cross     | pre_cross_m15_slot1_replace_or_rescue |       230.63 |  -230.63 |       230.63 |
| mt5_unmatched | mt5_0005       | 2020-03-13 16:00:00  | 2020-03-13 17:30:00 | SELL       | M15 SLOT1        | post_n        | post_n3_m15_slot1_replace_or_rescue   |       161.09 |  -161.09 |       161.09 |
| mt5_unmatched | mt5_0019       | 2020-08-04 17:30:00  | 2020-08-04 19:00:00 | BUY        | M15 SLOT1        | post_n        | post_n6_m15_slot1_replace_or_rescue   |       128.85 |  -128.85 |       128.85 |
| mt5_unmatched | mt5_0057       | 2025-10-20 12:00:00  | 2025-10-20 13:30:00 | BUY        | M30 CLOSE        | post_n        | post_n4                               |       110.91 |  -110.91 |       110.91 |
| mt5_unmatched | mt5_0065       | 2026-02-02 15:00:00  | 2026-02-02 16:30:00 | BUY        | M15 SLOT1        | post_n        | post_n4_m15_slot1_replace_or_rescue   |       -88.35 |    88.35 |        88.35 |
| mt5_unmatched | mt5_0026       | 2021-11-10 15:00:00  | 2021-11-10 16:30:00 | BUY        | M30 CLOSE        | post_n        | post_n3                               |       -75.19 |    75.19 |        75.19 |
| mt5_unmatched | mt5_0070       | 2026-03-23 16:00:00  | 2026-03-23 17:30:00 | BUY        | M15 SLOT1        | post_n        | post_n6_m15_slot1_replace_or_rescue   |       -70.14 |    70.14 |        70.14 |
| mt5_unmatched | mt5_0063       | 2026-01-27 06:00:00  | 2026-01-27 07:30:00 | BUY        | M30 CLOSE        | post_n        | post_n5                               |       -57.54 |    57.54 |        57.54 |
| mt5_unmatched | mt5_0076       | 2026-06-11 06:00:00  | 2026-06-11 07:30:00 | BUY        | M15 SLOT1        | pre_cross     | pre_cross_m15_slot1_replace_or_rescue |       -55.28 |    55.28 |        55.28 |
| mt5_unmatched | mt5_0050       | 2025-09-09 15:00:00  | 2025-09-09 16:30:00 | SELL       | M30 CLOSE        | pre_cross     | pre_cross                             |        54.33 |   -54.33 |        54.33 |
| mt5_unmatched | mt5_0017       | 2020-07-28 16:00:00  | 2020-07-28 17:30:00 | BUY        | M30 CLOSE        | post_n        | post_n3                               |        31.71 |   -31.71 |        31.71 |
| mt5_unmatched | mt5_0021       | 2021-01-11 14:30:00  | 2021-01-11 16:00:00 | SELL       | M15 SLOT1        | post_n        | post_n2_m15_slot1_replace_or_rescue   |       -29.01 |    29.01 |        29.01 |

## Output Snapshots

- `validation\dynamic_risk_inputs_m15_slot1_latest_completed_20260715`
- `validation\dynamic_risk_alignment_m15_slot1_latest_completed_close_retry_20260715`
- `validation\mapped_trade_alignment_m15_slot1_latest_completed_close_retry_20260715`
