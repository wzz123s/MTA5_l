# Stage-State M15 SLOT1 No-Candidate Source-Gap Audit

## Final Decision

- Target count: `7`.
- MT5 net profit sum: `211.14`.
- Positive MT5 count: `4`.
- Reliable mapped count: `2`.
- Primary class count: `4`.
- Diagnostic source prototype gate: `False`.
- Main signal gate: `False`.
- EA behavior gate: `False`.
- Mapping gate: `False`.
- Merge gate: `False`.

## Classification Summary

| primary_classification       |   count |   mt5_net_profit_sum |   positive_count |   negative_or_flat_count |   reliable_mapped_count | mt5_ids                             |
|:-----------------------------|--------:|---------------------:|-----------------:|-------------------------:|------------------------:|:------------------------------------|
| layer12_present_not_postn    |       4 |               209.71 |                3 |                        1 |                       1 | mt5_0052;mt5_0054;mt5_0068;mt5_0069 |
| time_axis_drift              |       1 |               159.92 |                1 |                        0 |                       1 | mt5_0050                            |
| raw_present_layer12_filtered |       1 |               -70.14 |                0 |                        1 |                       0 | mt5_0072                            |
| trigger_or_direction_drift   |       1 |               -88.35 |                0 |                        1 |                       0 | mt5_0067                            |

## Profit Summary

| profit_bucket    |   count |   mt5_net_profit_sum | primary_classes                                                                   | mt5_ids                             |
|:-----------------|--------:|---------------------:|:----------------------------------------------------------------------------------|:------------------------------------|
| negative_or_flat |       3 |              -170.46 | layer12_present_not_postn;trigger_or_direction_drift;raw_present_layer12_filtered | mt5_0052;mt5_0067;mt5_0072          |
| positive         |       4 |               381.6  | time_axis_drift;layer12_present_not_postn                                         | mt5_0050;mt5_0054;mt5_0068;mt5_0069 |

## Case Review

| mt5_trade_id   | signal_anchor_time   | dir_norm   | mt5_signal_src                      |   mt5_net_profit | mapping_match_tier     | primary_classification       | classification_reason                                                                   |   raw_actual_same_dir_postn_count |   raw_pm60_same_dir_any_count |   layer12_pm60_same_dir_any_count |   raw_pm7d_same_dir_postn_count |   layer12_pm7d_same_dir_postn_count | layer12_pm7d_nearest_postn_time   |   layer12_pm7d_nearest_postn_diff_minutes |   dynamic_pm7d_same_dir_postn_count |
|:---------------|:---------------------|:-----------|:------------------------------------|-----------------:|:-----------------------|:-----------------------------|:----------------------------------------------------------------------------------------|----------------------------------:|------------------------------:|----------------------------------:|--------------------------------:|------------------------------------:|:----------------------------------|------------------------------------------:|------------------------------------:|
| mt5_0050       | 2025-09-05 14:30:00  | BUY        | post_n5_m15_slot1_replace_or_rescue |           159.92 | nearby_7d_all          | time_axis_drift              | Layer1/2 same-direction post_n exists only outside +/-24h                               |                                 0 |                             0 |                                 0 |                               2 |                                   2 | 2025-09-02 18:00:00               |                                     -4110 |                                   1 |
| mt5_0052       | 2025-10-07 14:30:00  | BUY        | post_n5_m15_slot1_replace_or_rescue |           -11.97 | nan                    | layer12_present_not_postn    | Layer1/2 same-direction candidate exists within +/-60m, but it is not post_n            |                                 0 |                             1 |                                 1 |                               5 |                                   5 | 2025-10-09 10:30:00               |                                      2640 |                                   0 |
| mt5_0054       | 2025-10-14 18:30:00  | BUY        | post_n5_m15_slot1_replace_or_rescue |           201.68 | nearby_7d_all          | layer12_present_not_postn    | Layer1/2 same-direction candidate exists within +/-60m, but it is not post_n            |                                 0 |                             1 |                                 1 |                              10 |                                   9 | 2025-10-09 12:30:00               |                                     -7560 |                                   1 |
| mt5_0067       | 2026-02-02 15:00:00  | BUY        | post_n4_m15_slot1_replace_or_rescue |           -88.35 | nan                    | trigger_or_direction_drift   | raw same-direction candidate exists within +/-60m, but it is not post_n                 |                                 0 |                             1 |                                 0 |                               9 |                                   5 | 2026-01-27 08:00:00               |                                     -9060 |                                   0 |
| mt5_0068       | 2026-02-02 16:30:00  | SELL       | post_n2_m15_slot1_replace_or_rescue |             2.03 | nearby_60_mode_relaxed | layer12_present_not_postn    | Layer1/2 same-direction candidate exists within +/-60m, but it is not post_n            |                                 0 |                             2 |                                 2 |                              10 |                                   3 | 2026-01-26 23:00:00               |                                     -9690 |                                   1 |
| mt5_0069       | 2026-02-02 18:00:00  | SELL       | post_n5_m15_slot1_replace_or_rescue |            17.97 | nearby_7d_mode_relaxed | layer12_present_not_postn    | Layer1/2 same-direction candidate exists within +/-60m, but it is not post_n            |                                 0 |                             1 |                                 1 |                              10 |                                   3 | 2026-01-26 23:00:00               |                                     -9780 |                                   1 |
| mt5_0072       | 2026-03-23 16:00:00  | BUY        | post_n6_m15_slot1_replace_or_rescue |           -70.14 | nan                    | raw_present_layer12_filtered | raw same-direction post_n exists at actual anchor but no Layer1/2 post_n survives there |                                 1 |                             5 |                                 0 |                              20 |                                  12 | 2026-03-24 10:00:00               |                                      1080 |                                   0 |

## Interpretation

- This audit is diagnostic-only. It does not open the main signal, EA behavior, mapping, or merge gate.
- The no-candidate bucket is reviewed by raw presence, Layer1/2 survival, time-axis distance, mapping status, and MT5 profit sign.
- A source-gap prototype remains closed until one bucket shows a repeatable rule that is not merely a far-window mapping or profit-only selection.
