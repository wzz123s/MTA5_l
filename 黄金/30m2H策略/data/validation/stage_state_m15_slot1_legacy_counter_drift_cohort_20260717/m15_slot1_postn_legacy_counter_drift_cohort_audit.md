# Stage-State M15 SLOT1 post_n Legacy Counter Drift Cohort Audit

## Final Decision

- Cohort total: `19`.
- Comparable after Python M15 start: `12`.
- Pre Python M15 coverage: `7`.
- Log candidate covered: `19`.
- Actual-anchor exact counter match: `0`.
- Actual-anchor counter offset: `1`.
- Mapped count: `12`.
- Reliable mapped count: `6`.
- Low-blast prototype gate: `False`.
- Main signal gate: `False`.
- EA behavior gate: `False`.
- Mapping gate: `False`.
- Merge gate: `False`.

## Classification Summary

| cohort_classification            |   count |   mt5_net_profit_sum |   matched_count |   reliable_count |
|:---------------------------------|--------:|---------------------:|----------------:|-----------------:|
| pre_python_m15_coverage          |       7 |               324.24 |               4 |                0 |
| python_no_postn_candidate_nearby |       7 |               211.14 |               4 |                2 |
| aligned_plus90_counter_offset    |       4 |               221.55 |               4 |                4 |
| actual_anchor_counter_offset     |       1 |              -104.7  |               0 |                0 |

## Counter Diff Summary

| within_python_m15_coverage   |   mt5_mode_n |   log_post_n_counter_abs |   log_merged_post_n_counter_abs |   layer12_actual_first_mode_n_diff |   count |   mt5_net_profit_sum |
|:-----------------------------|-------------:|-------------------------:|--------------------------------:|-----------------------------------:|--------:|---------------------:|
| True                         |            5 |                        5 |                               5 |                                    |       5 |               463.69 |
| True                         |            2 |                        2 |                               2 |                                    |       3 |               108.15 |
| True                         |            3 |                        3 |                               3 |                                    |       1 |                19.34 |
| True                         |            4 |                        4 |                               4 |                                    |       1 |               -88.35 |
| True                         |            5 |                        5 |                               5 |                                 -2 |       1 |              -104.7  |
| True                         |            6 |                        6 |                               6 |                                    |       1 |               -70.14 |
| False                        |            4 |                        4 |                               4 |                                 -2 |       2 |              -104.13 |
| False                        |            6 |                        6 |                               6 |                                    |       2 |               268.3  |
| False                        |            2 |                        2 |                               2 |                                    |       1 |               -29.01 |
| False                        |            3 |                        3 |                               3 |                                    |       1 |               161.09 |
| False                        |            5 |                        5 |                               5 |                                    |       1 |                27.99 |

## Mapping Summary

| mapping_mapping_status   | mapping_match_tier        |   count |   reliable_count |   mt5_net_profit_sum |   profit_diff_sum |
|:-------------------------|:--------------------------|--------:|-----------------:|---------------------:|------------------:|
| matched                  | exact_align90_all         |       4 |                4 |               221.55 |           50.4966 |
| matched                  | nearby_7d_trigger_relaxed |       3 |                0 |               150.55 |         -272.915  |
| matched                  | nearby_7d_all             |       2 |                2 |               361.6  |          -41.8589 |
| matched                  | nearby_60_mode_relaxed    |       1 |                0 |                 2.03 |         -114.553  |
| matched                  | nearby_60_trigger_relaxed |       1 |                0 |               -87.24 |          124.332  |
| matched                  | nearby_7d_mode_relaxed    |       1 |                0 |                17.97 |           78.8769 |
| unmatched                | nan                       |       7 |                0 |               -14.23 |            0      |

## Cohort Rows

| mt5_trade_id   | signal_anchor_time   | dir_norm   | mt5_signal_src                      |   mt5_net_profit | cohort_classification            |   log_post_n_counter |   log_merged_post_n_counter | layer12_actual_modes   |   layer12_actual_first_mode_n_diff | layer12_aligned_modes   | layer12_same_mode_nearby_first_time   | mapping_mapping_status   | mapping_match_tier        |   mapping_profit_diff |
|:---------------|:---------------------|:-----------|:------------------------------------|-----------------:|:---------------------------------|---------------------:|----------------------------:|:-----------------------|-----------------------------------:|:------------------------|:--------------------------------------|:-------------------------|:--------------------------|----------------------:|
| mt5_0003       | 2020-03-13 09:30:00  | BUY        | post_n4_m15_slot1_replace_or_rescue |           -16.89 | pre_python_m15_coverage          |                    4 |                           4 | post_n2                |                                 -2 |                         |                                       | matched                  | nearby_7d_trigger_relaxed |             -60.7404  |
| mt5_0005       | 2020-03-13 16:00:00  | SELL       | post_n3_m15_slot1_replace_or_rescue |           161.09 | pre_python_m15_coverage          |                   -3 |                          -3 |                        |                                    |                         | 2020-03-13 17:00:00                   | unmatched                | nan                       |             nan       |
| mt5_0016       | 2020-07-28 08:00:00  | SELL       | post_n4_m15_slot1_replace_or_rescue |           -87.24 | pre_python_m15_coverage          |                   -4 |                          -4 | post_n2                |                                 -2 | post_n5                 | 2020-07-28 09:00:00                   | matched                  | nearby_60_trigger_relaxed |             124.332   |
| mt5_0019       | 2020-08-04 17:30:00  | BUY        | post_n6_m15_slot1_replace_or_rescue |           128.85 | pre_python_m15_coverage          |                    6 |                           6 |                        |                                    |                         |                                       | unmatched                | nan                       |             nan       |
| mt5_0021       | 2021-01-11 14:30:00  | SELL       | post_n2_m15_slot1_replace_or_rescue |           -29.01 | pre_python_m15_coverage          |                   -2 |                          -2 |                        |                                    |                         |                                       | unmatched                | nan                       |             nan       |
| mt5_0023       | 2021-06-16 22:30:00  | SELL       | post_n6_m15_slot1_replace_or_rescue |           139.45 | pre_python_m15_coverage          |                   -6 |                          -6 |                        |                                    |                         |                                       | matched                  | nearby_7d_trigger_relaxed |            -156.817   |
| mt5_0029       | 2022-03-08 08:30:00  | BUY        | post_n5_m15_slot1_replace_or_rescue |            27.99 | pre_python_m15_coverage          |                    5 |                           5 |                        |                                    |                         |                                       | matched                  | nearby_7d_trigger_relaxed |             -55.3574  |
| mt5_0031       | 2022-11-08 16:30:00  | BUY        | post_n5_m15_slot1_replace_or_rescue |            96.09 | aligned_plus90_counter_offset    |                    5 |                           5 |                        |                                    | post_n6                 | 2022-11-08 17:30:00                   | matched                  | exact_align90_all         |             -46.6683  |
| mt5_0050       | 2025-09-05 14:30:00  | BUY        | post_n5_m15_slot1_replace_or_rescue |           159.92 | python_no_postn_candidate_nearby |                    5 |                           5 |                        |                                    |                         |                                       | matched                  | nearby_7d_all             |             -43.4013  |
| mt5_0052       | 2025-10-07 14:30:00  | BUY        | post_n5_m15_slot1_replace_or_rescue |           -11.97 | python_no_postn_candidate_nearby |                    5 |                           5 |                        |                                    |                         |                                       | unmatched                | nan                       |             nan       |
| mt5_0054       | 2025-10-14 18:30:00  | BUY        | post_n5_m15_slot1_replace_or_rescue |           201.68 | python_no_postn_candidate_nearby |                    5 |                           5 |                        |                                    |                         |                                       | matched                  | nearby_7d_all             |               1.54236 |
| mt5_0057       | 2025-10-17 13:00:00  | SELL       | post_n2_m15_slot1_replace_or_rescue |           153.32 | aligned_plus90_counter_offset    |                   -2 |                          -2 |                        |                                    | post_n3                 |                                       | matched                  | exact_align90_all         |              -8.28641 |
| mt5_0064       | 2026-01-26 20:30:00  | SELL       | post_n2_m15_slot1_replace_or_rescue |           -47.2  | aligned_plus90_counter_offset    |                   -2 |                          -2 |                        |                                    | post_n3                 |                                       | matched                  | exact_align90_all         |             131.26    |
| mt5_0067       | 2026-02-02 15:00:00  | BUY        | post_n4_m15_slot1_replace_or_rescue |           -88.35 | python_no_postn_candidate_nearby |                    4 |                           4 |                        |                                    |                         |                                       | unmatched                | nan                       |             nan       |
| mt5_0068       | 2026-02-02 16:30:00  | SELL       | post_n2_m15_slot1_replace_or_rescue |             2.03 | python_no_postn_candidate_nearby |                   -2 |                          -2 |                        |                                    |                         |                                       | matched                  | nearby_60_mode_relaxed    |            -114.553   |
| mt5_0069       | 2026-02-02 18:00:00  | SELL       | post_n5_m15_slot1_replace_or_rescue |            17.97 | python_no_postn_candidate_nearby |                   -5 |                          -5 |                        |                                    |                         |                                       | matched                  | nearby_7d_mode_relaxed    |              78.8769  |
| mt5_0072       | 2026-03-23 16:00:00  | BUY        | post_n6_m15_slot1_replace_or_rescue |           -70.14 | python_no_postn_candidate_nearby |                    6 |                           6 |                        |                                    |                         |                                       | unmatched                | nan                       |             nan       |
| mt5_0074       | 2026-03-24 03:00:00  | SELL       | post_n3_m15_slot1_replace_or_rescue |            19.34 | aligned_plus90_counter_offset    |                   -3 |                          -3 |                        |                                    | post_n4                 |                                       | matched                  | exact_align90_all         |             -25.8091  |
| mt5_0076       | 2026-03-24 10:30:00  | BUY        | post_n5_m15_slot1_replace_or_rescue |          -104.7  | actual_anchor_counter_offset     |                    5 |                           5 | post_n3                |                                 -2 | post_n6                 | 2026-03-24 11:30:00                   | unmatched                | nan                       |             nan       |

## Interpretation

- The cohort is not a single clean correction target: early rows are outside Python M15 comparable coverage, while comparable rows split across actual-anchor offsets, nearby-only cases, and no-nearby cases.
- The EA log counter evidence is complete enough for cohort accounting, but it does not by itself justify a main-logic counter change.
- Any next prototype should stay diagnostic-only until a variant proves signal-set and profit gaps do not deteriorate.
