# Far Candidate Runtime Rescue Review 20260714

## Summary

| stable_case                          | target_time         | mode      |   filtered_trade_profit |   python_picked_rows_within_240m |   mt5_same_trigger_mode_rows_within_240m |   mt5_active_stage_rows_at_raw_time | classification                   |
|:-------------------------------------|:--------------------|:----------|------------------------:|---------------------------------:|-----------------------------------------:|------------------------------------:|:---------------------------------|
| far_runtime_rescue_20251021_postn6   | 2025-10-21 10:00:00 | post_n6   |                 201.851 |                                1 |                                        0 |                                   2 | mt5_position_occupancy_candidate |
| far_runtime_rescue_20251017_precross | 2025-10-17 11:00:00 | pre_cross |                 189.621 |                                3 |                                        0 |                                   2 | mt5_position_occupancy_candidate |

## Active MT5 Positions

| stable_case                          | raw_target_time     | signal_anchor_time   |   stage | dir   | trigger_tag   | signal_src                          | open_time           | exit_time           |   net_profit |
|:-------------------------------------|:--------------------|:---------------------|--------:|:------|:--------------|:------------------------------------|:--------------------|:--------------------|-------------:|
| far_runtime_rescue_20251021_postn6   | 2025-10-21 08:30:00 | 2025.10.14 18:30     |       3 | BUY   | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue | 2025.10.14 18:15:00 | 2025.10.21 14:29:38 |       -17.7  |
| far_runtime_rescue_20251021_postn6   | 2025-10-21 08:30:00 | 2022.11.08 16:30     |       1 | BUY   | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue | 2022.11.08 16:15:06 | 2026.07.06 23:59:59 |      1802.36 |
| far_runtime_rescue_20251017_precross | 2025-10-17 09:30:00 | 2025.10.14 18:30     |       3 | BUY   | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue | 2025.10.14 18:15:00 | 2025.10.21 14:29:38 |       -17.7  |
| far_runtime_rescue_20251017_precross | 2025-10-17 09:30:00 | 2022.11.08 16:30     |       1 | BUY   | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue | 2022.11.08 16:15:06 | 2026.07.06 23:59:59 |      1802.36 |

## Decision

- These rows are no longer ordinary unique-match conflicts; they are far-candidate Python runtime_rescue admissions.
- If MT5 had active positions at the raw target time, the next repair candidate is Python lifecycle/max-position simulation, not EA price-side behavior.
- If no MT5 position or signal evidence exists, keep the row in Python-only signal review before changing strategy generation.
