# Unmatched Signal Cause Diagnosis

## Summary
| source      | side             | cause_bucket                         |   rows |
|:------------|:-----------------|:-------------------------------------|-------:|
| python_mt5  | mt5_unmatched    | stage_execution_diff_or_family_drift |     18 |
| python_mt5  | mt5_unmatched    | mapping_conflict_or_profit_diff      |     11 |
| python_mt5  | mt5_unmatched    | layer3_reject                        |     10 |
| python_mt5  | mt5_unmatched    | trigger_family_drift                 |      5 |
| python_mt5  | mt5_unmatched    | missing_raw_parent                   |      3 |
| python_mt5  | mt5_unmatched    | missing_python_candidate             |      1 |
| python_mt5  | python_unmatched | unique_match_conflict                |     34 |
| python_mt5  | python_unmatched | mt5_family_or_time_drift             |     26 |
| python_mt5  | python_unmatched | python_signal_not_in_mt5_ledger      |     11 |
| python_only | mt5_unmatched    | mapping_conflict_or_profit_diff      |     20 |
| python_only | mt5_unmatched    | stage_execution_diff_or_family_drift |     11 |
| python_only | mt5_unmatched    | layer3_reject                        |      8 |
| python_only | mt5_unmatched    | trigger_family_drift                 |      4 |
| python_only | mt5_unmatched    | missing_python_candidate             |      2 |
| python_only | mt5_unmatched    | missing_raw_parent                   |      2 |
| python_only | python_unmatched | unique_match_conflict                |     53 |
| python_only | python_unmatched | mt5_family_or_time_drift             |     25 |
| python_only | python_unmatched | python_signal_not_in_mt5_ledger      |      9 |

## Trigger/Mode Cause Summary
| source      | side             | trigger_family   | mode_family   | cause_bucket                         |   rows |
|:------------|:-----------------|:-----------------|:--------------|:-------------------------------------|-------:|
| python_mt5  | mt5_unmatched    | M15 SLOT1        | post_n        | layer3_reject                        |      3 |
| python_mt5  | mt5_unmatched    | M15 SLOT1        | post_n        | mapping_conflict_or_profit_diff      |      3 |
| python_mt5  | mt5_unmatched    | M15 SLOT1        | post_n        | stage_execution_diff_or_family_drift |      3 |
| python_mt5  | mt5_unmatched    | M15 SLOT1        | post_n        | missing_raw_parent                   |      1 |
| python_mt5  | mt5_unmatched    | M15 SLOT1        | post_n        | trigger_family_drift                 |      1 |
| python_mt5  | mt5_unmatched    | M15 SLOT1        | pre_cross     | layer3_reject                        |      2 |
| python_mt5  | mt5_unmatched    | M15 SLOT1        | pre_cross     | mapping_conflict_or_profit_diff      |      2 |
| python_mt5  | mt5_unmatched    | M15 SLOT1        | pre_cross     | missing_raw_parent                   |      2 |
| python_mt5  | mt5_unmatched    | M30 CLOSE        | cross         | layer3_reject                        |      2 |
| python_mt5  | mt5_unmatched    | M30 CLOSE        | cross         | mapping_conflict_or_profit_diff      |      2 |
| python_mt5  | mt5_unmatched    | M30 CLOSE        | cross         | stage_execution_diff_or_family_drift |      2 |
| python_mt5  | mt5_unmatched    | M30 CLOSE        | post_n        | stage_execution_diff_or_family_drift |      8 |
| python_mt5  | mt5_unmatched    | M30 CLOSE        | post_n        | mapping_conflict_or_profit_diff      |      4 |
| python_mt5  | mt5_unmatched    | M30 CLOSE        | post_n        | trigger_family_drift                 |      3 |
| python_mt5  | mt5_unmatched    | M30 CLOSE        | post_n        | layer3_reject                        |      2 |
| python_mt5  | mt5_unmatched    | M30 CLOSE        | post_n        | missing_python_candidate             |      1 |
| python_mt5  | mt5_unmatched    | M30 CLOSE        | pre_cross     | stage_execution_diff_or_family_drift |      5 |
| python_mt5  | mt5_unmatched    | M30 CLOSE        | pre_cross     | layer3_reject                        |      1 |
| python_mt5  | mt5_unmatched    | M30 CLOSE        | pre_cross     | trigger_family_drift                 |      1 |
| python_mt5  | python_unmatched | M15 SLOT1        | cross         | mt5_family_or_time_drift             |      3 |
| python_mt5  | python_unmatched | M15 SLOT1        | cross         | python_signal_not_in_mt5_ledger      |      3 |
| python_mt5  | python_unmatched | M15 SLOT1        | post_n        | unique_match_conflict                |     15 |
| python_mt5  | python_unmatched | M15 SLOT1        | post_n        | mt5_family_or_time_drift             |     11 |
| python_mt5  | python_unmatched | M15 SLOT1        | pre_cross     | mt5_family_or_time_drift             |      7 |
| python_mt5  | python_unmatched | M15 SLOT1        | pre_cross     | python_signal_not_in_mt5_ledger      |      7 |
| python_mt5  | python_unmatched | M15 SLOT1        | pre_cross     | unique_match_conflict                |      4 |
| python_mt5  | python_unmatched | M30 CLOSE        | cross         | python_signal_not_in_mt5_ledger      |      1 |
| python_mt5  | python_unmatched | M30 CLOSE        | cross         | unique_match_conflict                |      1 |
| python_mt5  | python_unmatched | M30 CLOSE        | post_n        | unique_match_conflict                |     14 |
| python_mt5  | python_unmatched | M30 CLOSE        | post_n        | mt5_family_or_time_drift             |      2 |
| python_mt5  | python_unmatched | M30 CLOSE        | pre_cross     | mt5_family_or_time_drift             |      3 |
| python_only | mt5_unmatched    | M15 SLOT1        | post_n        | stage_execution_diff_or_family_drift |      5 |
| python_only | mt5_unmatched    | M15 SLOT1        | post_n        | trigger_family_drift                 |      3 |
| python_only | mt5_unmatched    | M15 SLOT1        | post_n        | mapping_conflict_or_profit_diff      |      2 |
| python_only | mt5_unmatched    | M15 SLOT1        | post_n        | missing_raw_parent                   |      1 |
| python_only | mt5_unmatched    | M15 SLOT1        | pre_cross     | stage_execution_diff_or_family_drift |      4 |
| python_only | mt5_unmatched    | M15 SLOT1        | pre_cross     | missing_raw_parent                   |      1 |
| python_only | mt5_unmatched    | M15 SLOT1        | pre_cross     | trigger_family_drift                 |      1 |
| python_only | mt5_unmatched    | M30 CLOSE        | cross         | layer3_reject                        |      2 |
| python_only | mt5_unmatched    | M30 CLOSE        | cross         | mapping_conflict_or_profit_diff      |      2 |
| python_only | mt5_unmatched    | M30 CLOSE        | cross         | stage_execution_diff_or_family_drift |      2 |
| python_only | mt5_unmatched    | M30 CLOSE        | post_n        | mapping_conflict_or_profit_diff      |     13 |
| python_only | mt5_unmatched    | M30 CLOSE        | post_n        | layer3_reject                        |      4 |
| python_only | mt5_unmatched    | M30 CLOSE        | post_n        | missing_python_candidate             |      1 |
| python_only | mt5_unmatched    | M30 CLOSE        | pre_cross     | mapping_conflict_or_profit_diff      |      3 |
| python_only | mt5_unmatched    | M30 CLOSE        | pre_cross     | layer3_reject                        |      2 |
| python_only | mt5_unmatched    | M30 CLOSE        | pre_cross     | missing_python_candidate             |      1 |
| python_only | python_unmatched | M15 SLOT1        | cross         | mt5_family_or_time_drift             |      4 |
| python_only | python_unmatched | M15 SLOT1        | post_n        | unique_match_conflict                |      3 |
| python_only | python_unmatched | M15 SLOT1        | post_n        | mt5_family_or_time_drift             |      1 |
| python_only | python_unmatched | M30 CLOSE        | cross         | python_signal_not_in_mt5_ledger      |      4 |
| python_only | python_unmatched | M30 CLOSE        | cross         | mt5_family_or_time_drift             |      2 |
| python_only | python_unmatched | M30 CLOSE        | cross         | unique_match_conflict                |      1 |
| python_only | python_unmatched | M30 CLOSE        | post_n        | unique_match_conflict                |     45 |
| python_only | python_unmatched | M30 CLOSE        | post_n        | mt5_family_or_time_drift             |     12 |
| python_only | python_unmatched | M30 CLOSE        | pre_cross     | mt5_family_or_time_drift             |      6 |
| python_only | python_unmatched | M30 CLOSE        | pre_cross     | python_signal_not_in_mt5_ledger      |      5 |
| python_only | python_unmatched | M30 CLOSE        | pre_cross     | unique_match_conflict                |      4 |

## Interpretation
- This is a first-pass attribution table. It classifies unmatched trades by nearest accepted/picked/executed candidates.
- `missing_raw_parent` is only assigned when an unmatched MT5 `M15 SLOT1` signal lacks a nearby Python `M30 CLOSE` accepted parent.
- `family_drift` buckets mean a nearby same-direction candidate exists but trigger family or mode family differs.

## Output Files
- `all_unmatched_signal_causes.csv`
- `unmatched_signal_cause_summary.csv`
- `unmatched_trigger_mode_cause_summary.csv`
- `m30_postn_unmatched_cause.csv`
- `m15_slot1_postn_raw_parent_cause.csv`
- `python_only_mt5_unmatched_cause.csv`
- `python_only_python_unmatched_cause.csv`
- `python_mt5_mt5_unmatched_cause.csv`
- `python_mt5_python_unmatched_cause.csv`
