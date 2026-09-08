# PostN Counter Anchor Replay

## Summary

| source      | scope                   | metric                           |   value |
|:------------|:------------------------|:---------------------------------|--------:|
| python_mt5  | all_mt5_m30_postn       | rows                             |      26 |
| python_mt5  | all_mt5_m30_postn       | counter_t_matches_mt5_abs        |      24 |
| python_mt5  | all_mt5_m30_postn       | counter_t_plus_30_matches_py_abs |       1 |
| python_mt5  | observed_30min_n_plus_1 | rows                             |       1 |
| python_mt5  | observed_30min_n_plus_1 | counter_t_matches_mt5_abs        |       1 |
| python_mt5  | observed_30min_n_plus_1 | counter_t_plus_30_matches_py_abs |       1 |
| python_mt5  | observed_30min_n_plus_1 | next_bar_explains_numbering      |       1 |
| python_mt5  | unmatched               | rows                             |      18 |
| python_mt5  | unmatched               | observed_30min_n_plus_1          |       0 |
| python_mt5  | reliable_matched        | rows                             |       6 |
| python_mt5  | reliable_matched        | observed_30min_n_plus_1          |       1 |
| python_only | all_mt5_m30_postn       | rows                             |      26 |
| python_only | all_mt5_m30_postn       | counter_t_matches_mt5_abs        |      22 |
| python_only | all_mt5_m30_postn       | counter_t_plus_30_matches_py_abs |      15 |
| python_only | observed_30min_n_plus_1 | rows                             |      14 |
| python_only | observed_30min_n_plus_1 | counter_t_matches_mt5_abs        |      14 |
| python_only | observed_30min_n_plus_1 | counter_t_plus_30_matches_py_abs |      14 |
| python_only | observed_30min_n_plus_1 | next_bar_explains_numbering      |      14 |
| python_only | unmatched               | rows                             |      18 |
| python_only | unmatched               | observed_30min_n_plus_1          |       8 |
| python_only | reliable_matched        | rows                             |       8 |
| python_only | reliable_matched        | observed_30min_n_plus_1          |       6 |

## Cause/Status Breakdown

| source      | match_status     | cause_bucket                         | layer_hint                  | observed_30min_n_plus_1   |   rows |   counter_t_matches_mt5_abs |   counter_t_plus_30_matches_py_abs |   next_bar_explains_numbering |
|:------------|:-----------------|:-------------------------------------|:----------------------------|:--------------------------|-------:|----------------------------:|-----------------------------------:|------------------------------:|
| python_mt5  | relaxed_matched  | nan                                  | nan                         | False                     |      2 |                           2 |                                  0 |                             0 |
| python_mt5  | reliable_matched | nan                                  | nan                         | False                     |      5 |                           5 |                                  0 |                             0 |
| python_mt5  | reliable_matched | nan                                  | nan                         | True                      |      1 |                           1 |                                  1 |                             1 |
| python_mt5  | unmatched        | stage_execution_diff_or_family_drift | family_drift                | False                     |      7 |                           6 |                                  0 |                             0 |
| python_mt5  | unmatched        | mapping_conflict_or_profit_diff      | executed_nearby             | False                     |      5 |                           4 |                                  0 |                             0 |
| python_mt5  | unmatched        | trigger_family_drift                 | family_drift                | False                     |      4 |                           4 |                                  0 |                             0 |
| python_mt5  | unmatched        | layer3_reject                        | accepted_only_layer3_reject | False                     |      1 |                           1 |                                  0 |                             0 |
| python_mt5  | unmatched        | missing_python_candidate             | missing_python_candidate    | False                     |      1 |                           1 |                                  0 |                             0 |
| python_only | reliable_matched | nan                                  | nan                         | True                      |      6 |                           6 |                                  6 |                             6 |
| python_only | reliable_matched | nan                                  | nan                         | False                     |      2 |                           1 |                                  0 |                             0 |
| python_only | unmatched        | mapping_conflict_or_profit_diff      | executed_nearby             | True                      |      8 |                           8 |                                  8 |                             8 |
| python_only | unmatched        | mapping_conflict_or_profit_diff      | executed_nearby             | False                     |      5 |                           4 |                                  1 |                             0 |
| python_only | unmatched        | layer3_reject                        | accepted_only_layer3_reject | False                     |      4 |                           2 |                                  0 |                             0 |
| python_only | unmatched        | missing_python_candidate             | missing_python_candidate    | False                     |      1 |                           1 |                                  0 |                             0 |

## Observed 30min N+1 Samples

| source      | mt5_trade_id   | match_status     | aligned_time        | nearest_py_date     | dir_norm   | mt5_signal_src   | nearest_py_mode   |   counter_t |   counter_t_plus_30 | next_bar_explains_numbering   |
|:------------|:---------------|:-----------------|:--------------------|:--------------------|:-----------|:-----------------|:------------------|------------:|--------------------:|:------------------------------|
| python_only | mt5_0008       | unmatched        | 2020-03-17 17:30:00 | 2020-03-17 18:00:00 | BUY        | post_n4          | post_n5           |           4 |                   5 | True                          |
| python_only | mt5_0009       | reliable_matched | 2020-03-18 09:30:00 | 2020-03-18 10:00:00 | SELL       | post_n4          | post_n5           |          -4 |                  -5 | True                          |
| python_only | mt5_0011       | reliable_matched | 2020-03-20 19:30:00 | 2020-03-20 20:00:00 | SELL       | post_n4          | post_n5           |          -4 |                  -5 | True                          |
| python_only | mt5_0014       | unmatched        | 2020-03-26 13:30:00 | 2020-03-26 14:00:00 | BUY        | post_n4          | post_n5           |           4 |                   5 | True                          |
| python_only | mt5_0017       | unmatched        | 2020-07-28 17:30:00 | 2020-07-28 18:00:00 | BUY        | post_n3          | post_n4           |           3 |                   4 | True                          |
| python_only | mt5_0022       | reliable_matched | 2021-03-04 20:30:00 | 2021-03-04 21:00:00 | SELL       | post_n4          | post_n5           |          -4 |                  -5 | True                          |
| python_only | mt5_0024       | reliable_matched | 2021-06-18 15:30:00 | 2021-06-18 16:00:00 | SELL       | post_n3          | post_n4           |          -3 |                  -4 | True                          |
| python_only | mt5_0027       | unmatched        | 2022-03-07 21:30:00 | 2022-03-07 22:00:00 | BUY        | post_n3          | post_n4           |           3 |                   4 | True                          |
| python_only | mt5_0030       | reliable_matched | 2022-03-09 11:30:00 | 2022-03-09 12:00:00 | SELL       | post_n2          | post_n3           |          -2 |                  -3 | True                          |
| python_only | mt5_0032       | unmatched        | 2022-11-10 15:30:00 | 2022-11-10 16:00:00 | BUY        | post_n2          | post_n3           |           2 |                   3 | True                          |
| python_only | mt5_0034       | unmatched        | 2023-03-15 14:30:00 | 2023-03-15 15:00:00 | BUY        | post_n4          | post_n5           |           4 |                   5 | True                          |
| python_only | mt5_0038       | unmatched        | 2024-04-03 17:30:00 | 2024-04-03 18:00:00 | BUY        | post_n3          | post_n4           |           3 |                   4 | True                          |
| python_only | mt5_0047       | reliable_matched | 2025-04-22 15:30:00 | 2025-04-22 16:00:00 | SELL       | post_n3          | post_n4           |          -3 |                  -4 | True                          |
| python_only | mt5_0057       | unmatched        | 2025-10-20 13:30:00 | 2025-10-20 14:00:00 | BUY        | post_n4          | post_n5           |           4 |                   5 | True                          |
| python_mt5  | mt5_0022       | reliable_matched | 2021-03-04 20:30:00 | 2021-03-04 21:00:00 | SELL       | post_n4          | post_n5           |          -4 |                  -5 | True                          |

## Interpretation

- `counter_t` is the processed M30 `merged_post_cross_n` at the MT5 aligned signal time.
- `counter_t_plus_30` is the next M30 bar counter.
- `observed_30min_n_plus_1` means the nearest Python M30 post_n trade is 30 minutes after MT5 and has post_n one larger.
- If `counter_t` matches MT5 and `counter_t_plus_30` matches Python, the discrepancy is explained by anchor/counter semantics rather than a missing raw signal.
- In this run, Python-only follows that pattern, while Python-MT5 does not because the currently used `data/signals_mt5` files are not counter-aligned with `data/processed/m30_mt5.csv`; see `python_mt5_signal_source_audit_20260713`.

## Output Files

- `postn_counter_anchor_case_details.csv`
- `postn_counter_anchor_summary.csv`
- `postn_counter_anchor_policy_summary.csv`
