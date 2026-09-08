# M15 SLOT1 post_n Shift90 Review

## Cause Summary

| cause_bucket                         |   rows |
|:-------------------------------------|-------:|
| layer3_reject                        |      3 |
| mapping_conflict_or_profit_diff      |      3 |
| missing_raw_parent                   |      1 |
| stage_execution_diff_or_family_drift |      3 |
| trigger_family_drift                 |      1 |

## Parent Summary

| parent_status         | parent_time_bucket   | parent_mode_family   |   rows |
|:----------------------|:---------------------|:---------------------|-------:|
| has_nearby_m30_parent | <=30                 | post_n               |      1 |
| has_nearby_m30_parent | <=90                 | post_n               |      1 |
| missing_raw_parent    | none                 | nan                  |      9 |

## Action Summary

| action_class                             | cause_bucket                         |   rows |
|:-----------------------------------------|:-------------------------------------|-------:|
| diagnostic_candidate_family_drift        | stage_execution_diff_or_family_drift |      1 |
| diagnostic_candidate_family_drift        | trigger_family_drift                 |      1 |
| diagnostic_candidate_true_missing_parent | missing_raw_parent                   |      1 |
| keep_for_layer3_review                   | layer3_reject                        |      3 |
| keep_for_mapping_or_profit_review        | mapping_conflict_or_profit_diff      |      3 |
| keep_parent_exists_trigger_family_drift  | stage_execution_diff_or_family_drift |      2 |

## EA Action Summary

| ea_action                                 |   rows |
|:------------------------------------------|-------:|
| diagnostic_only                           |      2 |
| diagnostic_only_possible_filter_candidate |      1 |
| do_not_filter                             |      8 |

## Case Details

| trade_id   | target_time         | dir_norm   |   profit | cause_bucket                         | parent_status         | parent_time_bucket   | accepted_status   | accepted_time_bucket   | accepted_trigger_family   | accepted_mode_family   | accepted_mode   | accepted_variant   | action_class                             | ea_action                                 |
|:-----------|:--------------------|:-----------|---------:|:-------------------------------------|:----------------------|:---------------------|:------------------|:-----------------------|:--------------------------|:-----------------------|:----------------|:-------------------|:-----------------------------------------|:------------------------------------------|
| mt5_0003   | 2020-03-13 11:00:00 | BUY        |   -16.89 | stage_execution_diff_or_family_drift | has_nearby_m30_parent | <=90                 | trigger_drift     | <=90                   | M30 CLOSE                 | post_n                 | post_n2         | m30_base           | keep_parent_exists_trigger_family_drift  | do_not_filter                             |
| mt5_0005   | 2020-03-13 17:30:00 | SELL       |   161.09 | stage_execution_diff_or_family_drift | has_nearby_m30_parent | <=30                 | trigger_drift     | <=30                   | M30 CLOSE                 | post_n                 | post_n3         | m30_base           | keep_parent_exists_trigger_family_drift  | do_not_filter                             |
| mt5_0019   | 2020-08-04 19:00:00 | BUY        |   128.85 | trigger_family_drift                 | missing_raw_parent    | none                 | trigger_drift     | <=7d                   | M30 CLOSE                 | post_n                 | post_n6         | m30_base           | diagnostic_candidate_family_drift        | diagnostic_only                           |
| mt5_0021   | 2021-01-11 16:00:00 | SELL       |   -29.01 | missing_raw_parent                   | missing_raw_parent    | none                 | none              | none                   | nan                       | nan                    | nan             | nan                | diagnostic_candidate_true_missing_parent | diagnostic_only_possible_filter_candidate |
| mt5_0029   | 2022-03-08 10:00:00 | BUY        |    27.99 | stage_execution_diff_or_family_drift | missing_raw_parent    | none                 | trigger_drift     | <=1d                   | M30 CLOSE                 | post_n                 | post_n6         | m30_base           | diagnostic_candidate_family_drift        | diagnostic_only                           |
| mt5_0031   | 2022-11-08 18:00:00 | BUY        |  1842.78 | mapping_conflict_or_profit_diff      | missing_raw_parent    | none                 | same_trigger_mode | 0                      | M15 SLOT1                 | post_n                 | post_n6         | ea_slot1_replace   | keep_for_mapping_or_profit_review        | do_not_filter                             |
| mt5_0049   | 2025-09-05 16:00:00 | BUY        |   541.15 | mapping_conflict_or_profit_diff      | missing_raw_parent    | none                 | same_trigger_mode | <=7d                   | M15 SLOT1                 | post_n                 | post_n6         | ea_slot1_replace   | keep_for_mapping_or_profit_review        | do_not_filter                             |
| mt5_0051   | 2025-10-07 16:00:00 | BUY        |    -2.3  | layer3_reject                        | missing_raw_parent    | none                 | same_trigger_mode | <=7d                   | M15 SLOT1                 | post_n                 | post_n2         | ea_slot1_replace   | keep_for_layer3_review                   | do_not_filter                             |
| mt5_0053   | 2025-10-14 20:00:00 | BUY        |    50.71 | mapping_conflict_or_profit_diff      | missing_raw_parent    | none                 | same_trigger_mode | <=7d                   | M15 SLOT1                 | post_n                 | post_n6         | ea_slot1_replace   | keep_for_mapping_or_profit_review        | do_not_filter                             |
| mt5_0065   | 2026-02-02 16:30:00 | BUY        |   -88.35 | layer3_reject                        | missing_raw_parent    | none                 | same_trigger_mode | <=7d                   | M15 SLOT1                 | post_n                 | post_n6         | ea_slot1_replace   | keep_for_layer3_review                   | do_not_filter                             |
| mt5_0070   | 2026-03-23 17:30:00 | BUY        |   -70.14 | layer3_reject                        | missing_raw_parent    | none                 | same_trigger_mode | <=1d                   | M15 SLOT1                 | post_n                 | post_n2         | ea_slot1_replace   | keep_for_layer3_review                   | do_not_filter                             |

## Interpretation

- The remaining `M15 SLOT1 / post_n` MT5-only set is mixed; it is not a pure missing-parent set.
- Parent-only filtering remains unsafe because several rows without a nearby M30 parent still have Python same-trigger candidates or Layer3 candidates.
- The only behaviorally plausible EA work here is diagnostic enrichment first; filtering needs a local, testable condition that does not depend on offline match labels.

## Output Files

- `m15_slot1_postn_shift90_review_details.csv`
- `m15_slot1_postn_shift90_cause_summary.csv`
- `m15_slot1_postn_shift90_parent_summary.csv`
- `m15_slot1_postn_shift90_action_summary.csv`
- `m15_slot1_postn_shift90_ea_action_summary.csv`
