# Stage-State M15 SLOT1 Near-Trigger Family Drift Audit

## Final Decision

- Target count: `5`.
- MT5 net profit sum: `121.36000000000001`.
- Trigger-family label gap count: `4`.
- Raw sequence gap count: `1`.
- Slot1 anchor gap count: `0`.
- Mapping far-window artifact secondary count: `2`.
- Diagnostic trigger-family prototype gate: `False`.
- Main signal gate: `False`.
- EA behavior gate: `False`.
- Mapping gate: `False`.
- Merge gate: `False`.

## Classification Summary

| primary_classification   |   count |   mt5_net_profit_sum |   reliable_mapped_count | mt5_ids                             |
|:-------------------------|--------:|---------------------:|------------------------:|:------------------------------------|
| trigger_family_label_gap |       4 |               209.71 |                       1 | mt5_0052;mt5_0054;mt5_0068;mt5_0069 |
| raw_sequence_gap         |       1 |               -88.35 |                       0 | mt5_0067                            |

## Case Verdict

| mt5_trade_id   | signal_anchor_time   | dir_norm   | mt5_signal_src                      |   mt5_net_profit | mapping_match_tier     | primary_classification   | secondary_classifications                            | classification_reason                                                                                      |   layer12_near_same_dir_nonpostn_count |   layer12_near_same_dir_postn_count | layer12_nearest_near_nonpostn_time   | layer12_nearest_near_nonpostn_mode   | raw_nearest_day_postn_time   |   raw_nearest_day_postn_diff_minutes |   mapping_time_diff_minutes |
|:---------------|:---------------------|:-----------|:------------------------------------|-----------------:|:-----------------------|:-------------------------|:-----------------------------------------------------|:-----------------------------------------------------------------------------------------------------------|---------------------------------------:|------------------------------------:|:-------------------------------------|:-------------------------------------|:-----------------------------|-------------------------------------:|----------------------------:|
| mt5_0052       | 2025-10-07 14:30:00  | BUY        | post_n5_m15_slot1_replace_or_rescue |           -11.97 | nan                    | trigger_family_label_gap | trigger_family_label_gap                             | EA exact post_n exists, while Python Layer1/2 near window has same-direction cross/pre_cross but no post_n |                                      1 |                                   0 | 2025-10-07 13:30:00                  | cross                                |                              |                                      |                             |
| mt5_0054       | 2025-10-14 18:30:00  | BUY        | post_n5_m15_slot1_replace_or_rescue |           201.68 | nearby_7d_all          | trigger_family_label_gap | mapping_far_window_artifact;trigger_family_label_gap | EA exact post_n exists, while Python Layer1/2 near window has same-direction cross/pre_cross but no post_n |                                      1 |                                   0 | 2025-10-14 17:30:00                  | cross                                |                              |                                      |                        8370 |
| mt5_0067       | 2026-02-02 15:00:00  | BUY        | post_n4_m15_slot1_replace_or_rescue |           -88.35 | nan                    | raw_sequence_gap         | raw_sequence_gap                                     | EA exact post_n exists, while Python raw near window has same-direction non-post_n but no post_n           |                                      0 |                                   0 |                                      |                                      | 2026-02-03 02:00:00          |                                  660 |                             |
| mt5_0068       | 2026-02-02 16:30:00  | SELL       | post_n2_m15_slot1_replace_or_rescue |             2.03 | nearby_60_mode_relaxed | trigger_family_label_gap | trigger_family_label_gap                             | EA exact post_n exists, while Python Layer1/2 near window has same-direction cross/pre_cross but no post_n |                                      2 |                                   0 | 2026-02-02 17:00:00                  | cross                                |                              |                                      |                          30 |
| mt5_0069       | 2026-02-02 18:00:00  | SELL       | post_n5_m15_slot1_replace_or_rescue |            17.97 | nearby_7d_mode_relaxed | trigger_family_label_gap | mapping_far_window_artifact;trigger_family_label_gap | EA exact post_n exists, while Python Layer1/2 near window has same-direction cross/pre_cross but no post_n |                                      1 |                                   0 | 2026-02-02 17:00:00                  | cross                                |                              |                                      |                        9900 |

## Interpretation

- This audit confirms whether the previous no-candidate bucket is a local trigger-family mismatch or a far mapping artifact.
- The result remains diagnostic-only until a repeated trigger-family generation rule can be proven across the affected cohort.
- No main signal, EA behavior, mapping, dynamic-risk, or merge gate is opened here.
