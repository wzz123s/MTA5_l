# M30 PostN Alignment Diagnosis

## Summary
| source      | side             | match_status     | time_bucket   |   postn_diff |   rows |
|:------------|:-----------------|:-----------------|:--------------|-------------:|-------:|
| python_mt5  | mt5_m30_postn    | relaxed_matched  | none          |              |      2 |
| python_mt5  | mt5_m30_postn    | reliable_matched | <=30          |           -1 |      5 |
| python_mt5  | mt5_m30_postn    | reliable_matched | none          |              |      1 |
| python_mt5  | mt5_m30_postn    | unmatched        | <=30          |           -1 |      4 |
| python_mt5  | mt5_m30_postn    | unmatched        | none          |              |     14 |
| python_mt5  | python_m30_postn | matched          | <=30          |            1 |      5 |
| python_mt5  | python_m30_postn | matched          | <=60          |            2 |      3 |
| python_mt5  | python_m30_postn | matched          | none          |              |      2 |
| python_mt5  | python_m30_postn | unmatched        | <=180         |            3 |      4 |
| python_mt5  | python_m30_postn | unmatched        | <=30          |            1 |      4 |
| python_mt5  | python_m30_postn | unmatched        | <=60          |            2 |      4 |
| python_mt5  | python_m30_postn | unmatched        | none          |              |      4 |
| python_only | mt5_m30_postn    | reliable_matched | <=30          |           -1 |      6 |
| python_only | mt5_m30_postn    | reliable_matched | <=60          |           -1 |      1 |
| python_only | mt5_m30_postn    | reliable_matched | none          |              |      1 |
| python_only | mt5_m30_postn    | unmatched        | 0             |            0 |      3 |
| python_only | mt5_m30_postn    | unmatched        | <=30          |           -1 |      8 |
| python_only | mt5_m30_postn    | unmatched        | <=30          |            0 |      1 |
| python_only | mt5_m30_postn    | unmatched        | <=60          |           -2 |      1 |
| python_only | mt5_m30_postn    | unmatched        | none          |              |      5 |
| python_only | python_m30_postn | matched          | <=30          |            1 |      6 |
| python_only | python_m30_postn | matched          | <=60          |            2 |      2 |
| python_only | python_m30_postn | matched          | <=60          |            1 |      1 |
| python_only | python_m30_postn | matched          | none          |              |      4 |
| python_only | python_m30_postn | unmatched        | 0             |            0 |      3 |
| python_only | python_m30_postn | unmatched        | <=180         |            3 |      7 |
| python_only | python_m30_postn | unmatched        | <=180         |            4 |      3 |
| python_only | python_m30_postn | unmatched        | <=180         |           -3 |      1 |
| python_only | python_m30_postn | unmatched        | <=30          |            1 |     10 |
| python_only | python_m30_postn | unmatched        | <=30          |            0 |      1 |
| python_only | python_m30_postn | unmatched        | <=60          |            2 |     13 |
| python_only | python_m30_postn | unmatched        | <=60          |           -2 |      1 |
| python_only | python_m30_postn | unmatched        | none          |              |     18 |

## MT5 Unmatched Focus
| source      | cause_bucket                         | layer_hint                  | time_bucket   |   postn_diff |   rows |
|:------------|:-------------------------------------|:----------------------------|:--------------|-------------:|-------:|
| python_mt5  | stage_execution_diff_or_family_drift | family_drift                | none          |              |      8 |
| python_mt5  | mapping_conflict_or_profit_diff      | executed_nearby             | <=30          |           -1 |      4 |
| python_mt5  | trigger_family_drift                 | family_drift                | none          |              |      3 |
| python_mt5  | layer3_reject                        | accepted_only_layer3_reject | none          |              |      2 |
| python_mt5  | missing_python_candidate             | missing_python_candidate    | none          |              |      1 |
| python_only | mapping_conflict_or_profit_diff      | executed_nearby             | <=30          |           -1 |      8 |
| python_only | layer3_reject                        | accepted_only_layer3_reject | none          |              |      4 |
| python_only | mapping_conflict_or_profit_diff      | executed_nearby             | 0             |            0 |      3 |
| python_only | mapping_conflict_or_profit_diff      | executed_nearby             | <=30          |            0 |      1 |
| python_only | mapping_conflict_or_profit_diff      | executed_nearby             | <=60          |           -2 |      1 |
| python_only | missing_python_candidate             | missing_python_candidate    | none          |              |      1 |

## Interpretation
- `time_bucket` is based on the nearest same-direction M30 CLOSE post_n candidate within one day.
- `postn_diff = mt5_post_n - python_post_n` for MT5-side rows and `py_post_n - mt5_post_n` for Python-side rows.
- Rows with `accepted_only_layer3_reject` reached Python accepted but did not survive Layer3.
- Rows with `executed_nearby` are not missing raw signals; they are timing or post_n numbering conflicts.

## Output Files
- `m30_postn_alignment_details.csv`
- `m30_postn_alignment_summary.csv`
- `m30_postn_mt5_unmatched_details.csv`
