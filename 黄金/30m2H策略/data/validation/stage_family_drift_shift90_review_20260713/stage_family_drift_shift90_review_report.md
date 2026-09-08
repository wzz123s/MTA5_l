# Stage / Trigger Family Drift Shift90 Review

## Trigger/Mode Cause Summary

| trigger_family   | mode_family   | cause_bucket                         |   rows |
|:-----------------|:--------------|:-------------------------------------|-------:|
| M15 SLOT1        | post_n        | stage_execution_diff_or_family_drift |      3 |
| M15 SLOT1        | post_n        | trigger_family_drift                 |      1 |
| M30 CLOSE        | cross         | stage_execution_diff_or_family_drift |      1 |
| M30 CLOSE        | post_n        | stage_execution_diff_or_family_drift |      7 |
| M30 CLOSE        | post_n        | trigger_family_drift                 |      4 |
| M30 CLOSE        | pre_cross     | stage_execution_diff_or_family_drift |      3 |
| M30 CLOSE        | pre_cross     | trigger_family_drift                 |      1 |

## Drift Pattern Summary

| drift_pattern                        | cause_bucket                         |   rows |
|:-------------------------------------|:-------------------------------------|-------:|
| mt5_m15_python_m30_far_parent        | stage_execution_diff_or_family_drift |      1 |
| mt5_m15_python_m30_far_parent        | trigger_family_drift                 |      1 |
| mt5_m15_python_m30_near_parent       | stage_execution_diff_or_family_drift |      2 |
| mt5_m30_python_m15_far               | trigger_family_drift                 |      1 |
| mt5_m30_python_m15_same_or_next_slot | stage_execution_diff_or_family_drift |     11 |
| mt5_m30_python_m15_same_or_next_slot | trigger_family_drift                 |      4 |

## Review Action Summary

| review_action                               |   rows |
|:--------------------------------------------|-------:|
| review_m15_replace_trigger_family_semantics |     17 |
| review_time_window_or_one_to_one_conflict   |      3 |

## Details

| trade_id   | target_time         | dir_norm   | trigger_family   | mode_family   |   profit | cause_bucket                         | accepted_status   | accepted_time_bucket   | accepted_trigger_family   | accepted_mode_family   | accepted_mode   | accepted_variant   | picked_status   | picked_time_bucket   | executed_status   | executed_time_bucket   | drift_pattern                        | review_action                               |
|:-----------|:--------------------|:-----------|:-----------------|:--------------|---------:|:-------------------------------------|:------------------|:-----------------------|:--------------------------|:-----------------------|:----------------|:-------------------|:----------------|:---------------------|:------------------|:-----------------------|:-------------------------------------|:--------------------------------------------|
| mt5_0003   | 2020-03-13 11:00:00 | BUY        | M15 SLOT1        | post_n        |   -16.89 | stage_execution_diff_or_family_drift | trigger_drift     | <=90                   | M30 CLOSE                 | post_n                 | post_n2         | m30_base           | trigger_drift   | <=90                 | trigger_drift     | <=90                   | mt5_m15_python_m30_near_parent       | review_m15_replace_trigger_family_semantics |
| mt5_0005   | 2020-03-13 17:30:00 | SELL       | M15 SLOT1        | post_n        |   161.09 | stage_execution_diff_or_family_drift | trigger_drift     | <=30                   | M30 CLOSE                 | post_n                 | post_n3         | m30_base           | trigger_drift   | <=7d                 | trigger_drift     | <=7d                   | mt5_m15_python_m30_near_parent       | review_m15_replace_trigger_family_semantics |
| mt5_0019   | 2020-08-04 19:00:00 | BUY        | M15 SLOT1        | post_n        |   128.85 | trigger_family_drift                 | trigger_drift     | <=7d                   | M30 CLOSE                 | post_n                 | post_n6         | m30_base           | none            | none                 | none              | none                   | mt5_m15_python_m30_far_parent        | review_time_window_or_one_to_one_conflict   |
| mt5_0029   | 2022-03-08 10:00:00 | BUY        | M15 SLOT1        | post_n        |    27.99 | stage_execution_diff_or_family_drift | trigger_drift     | <=1d                   | M30 CLOSE                 | post_n                 | post_n6         | m30_base           | trigger_drift   | <=1d                 | trigger_drift     | <=1d                   | mt5_m15_python_m30_far_parent        | review_time_window_or_one_to_one_conflict   |
| mt5_0032   | 2022-11-10 15:30:00 | BUY        | M30 CLOSE        | post_n        |   105.37 | stage_execution_diff_or_family_drift | trigger_drift     | 0                      | M15 SLOT1                 | post_n                 | post_n2         | ea_slot1_replace   | trigger_drift   | 0                    | trigger_drift     | 0                      | mt5_m30_python_m15_same_or_next_slot | review_m15_replace_trigger_family_semantics |
| mt5_0033   | 2022-11-14 17:30:00 | BUY        | M30 CLOSE        | post_n        |    -5.91 | stage_execution_diff_or_family_drift | trigger_drift     | 0                      | M15 SLOT1                 | post_n                 | post_n4         | ea_slot1_replace   | trigger_drift   | <=30                 | trigger_drift     | <=30                   | mt5_m30_python_m15_same_or_next_slot | review_m15_replace_trigger_family_semantics |
| mt5_0034   | 2023-03-15 14:30:00 | BUY        | M30 CLOSE        | post_n        |    86.56 | stage_execution_diff_or_family_drift | trigger_drift     | <=30                   | M15 SLOT1                 | post_n                 | post_n5         | ea_slot1_replace   | trigger_drift   | <=30                 | trigger_drift     | <=30                   | mt5_m30_python_m15_same_or_next_slot | review_m15_replace_trigger_family_semantics |
| mt5_0038   | 2024-04-03 17:30:00 | BUY        | M30 CLOSE        | post_n        |     7.68 | stage_execution_diff_or_family_drift | trigger_drift     | 0                      | M15 SLOT1                 | post_n                 | post_n3         | ea_slot1_replace   | trigger_drift   | <=30                 | trigger_drift     | <=30                   | mt5_m30_python_m15_same_or_next_slot | review_m15_replace_trigger_family_semantics |
| mt5_0040   | 2024-04-08 19:30:00 | BUY        | M30 CLOSE        | cross         |    18    | stage_execution_diff_or_family_drift | trigger_drift     | 0                      | M15 SLOT1                 | cross                  | cross           | ea_slot1_replace   | trigger_drift   | 0                    | trigger_drift     | 0                      | mt5_m30_python_m15_same_or_next_slot | review_m15_replace_trigger_family_semantics |
| mt5_0042   | 2024-11-12 15:00:00 | BUY        | M30 CLOSE        | pre_cross     |   -22.71 | stage_execution_diff_or_family_drift | trigger_drift     | 0                      | M15 SLOT1                 | pre_cross              | pre_cross       | ea_slot1_replace   | trigger_drift   | 0                    | trigger_drift     | 0                      | mt5_m30_python_m15_same_or_next_slot | review_m15_replace_trigger_family_semantics |
| mt5_0043   | 2024-11-13 19:30:00 | SELL       | M30 CLOSE        | post_n        |    80.96 | trigger_family_drift                 | trigger_drift     | 0                      | M15 SLOT1                 | post_n                 | post_n6         | ea_slot1_replace   | none            | none                 | none              | none                   | mt5_m30_python_m15_same_or_next_slot | review_m15_replace_trigger_family_semantics |
| mt5_0045   | 2025-04-21 01:30:00 | BUY        | M30 CLOSE        | post_n        |   108.52 | stage_execution_diff_or_family_drift | trigger_drift     | 0                      | M15 SLOT1                 | post_n                 | post_n4         | ea_slot1_replace   | trigger_drift   | <=30                 | trigger_drift     | <=30                   | mt5_m30_python_m15_same_or_next_slot | review_m15_replace_trigger_family_semantics |
| mt5_0048   | 2025-09-02 17:30:00 | BUY        | M30 CLOSE        | post_n        |   123.92 | stage_execution_diff_or_family_drift | trigger_drift     | 0                      | M15 SLOT1                 | post_n                 | post_n5         | ea_slot1_replace   | trigger_drift   | <=30                 | trigger_drift     | <=30                   | mt5_m30_python_m15_same_or_next_slot | review_m15_replace_trigger_family_semantics |
| mt5_0050   | 2025-09-09 16:30:00 | SELL       | M30 CLOSE        | pre_cross     |    54.33 | trigger_family_drift                 | trigger_drift     | <=7d                   | M15 SLOT1                 | pre_cross              | pre_cross       | ea_slot1_replace   | none            | none                 | none              | none                   | mt5_m30_python_m15_far               | review_time_window_or_one_to_one_conflict   |
| mt5_0057   | 2025-10-20 13:30:00 | BUY        | M30 CLOSE        | post_n        |   110.91 | stage_execution_diff_or_family_drift | trigger_drift     | 0                      | M15 SLOT1                 | post_n                 | post_n4         | ea_slot1_replace   | trigger_drift   | <=30                 | trigger_drift     | <=30                   | mt5_m30_python_m15_same_or_next_slot | review_m15_replace_trigger_family_semantics |
| mt5_0059   | 2026-01-13 17:30:00 | BUY        | M30 CLOSE        | post_n        |   -59.91 | trigger_family_drift                 | trigger_drift     | 0                      | M15 SLOT1                 | post_n                 | post_n6         | ea_slot1_replace   | none            | none                 | none              | none                   | mt5_m30_python_m15_same_or_next_slot | review_m15_replace_trigger_family_semantics |
| mt5_0063   | 2026-01-27 07:30:00 | BUY        | M30 CLOSE        | post_n        |   -57.54 | trigger_family_drift                 | trigger_drift     | 0                      | M15 SLOT1                 | post_n                 | post_n5         | ea_slot1_replace   | none            | none                 | none              | none                   | mt5_m30_python_m15_same_or_next_slot | review_m15_replace_trigger_family_semantics |
| mt5_0073   | 2026-03-24 10:00:00 | BUY        | M30 CLOSE        | post_n        |     2.5  | trigger_family_drift                 | trigger_drift     | 0                      | M15 SLOT1                 | post_n                 | post_n2         | ea_slot1_replace   | none            | none                 | none              | none                   | mt5_m30_python_m15_same_or_next_slot | review_m15_replace_trigger_family_semantics |
| mt5_0077   | 2026-06-19 14:30:00 | BUY        | M30 CLOSE        | pre_cross     |   -54.64 | stage_execution_diff_or_family_drift | trigger_drift     | 0                      | M15 SLOT1                 | pre_cross              | pre_cross       | ea_slot1_replace   | trigger_drift   | 0                    | trigger_drift     | 0                      | mt5_m30_python_m15_same_or_next_slot | review_m15_replace_trigger_family_semantics |
| mt5_0078   | 2026-06-30 08:00:00 | BUY        | M30 CLOSE        | pre_cross     |    73.09 | stage_execution_diff_or_family_drift | trigger_drift     | 0                      | M15 SLOT1                 | pre_cross              | pre_cross       | ea_slot1_replace   | trigger_drift   | 0                    | trigger_drift     | 0                      | mt5_m30_python_m15_same_or_next_slot | review_m15_replace_trigger_family_semantics |

## Interpretation

- Most drift cases are not pure Stage exit differences; they are trigger-family replacement semantics around M15 SLOT1 versus M30 CLOSE.
- Same-time or near-time `M30 CLOSE <-> M15 SLOT1` drift should be reviewed before changing stops, funds, or post_n counters.
- The next executable step is to inspect the M15 replace/rescue decision path and decide whether mapping should treat same-time replacement as equivalent, or Python/EA trigger labels need to be normalized.

## Output Files

- `stage_family_drift_shift90_details.csv`
- `stage_family_drift_shift90_trigger_mode_summary.csv`
- `stage_family_drift_shift90_pattern_summary.csv`
- `stage_family_drift_shift90_action_summary.csv`
