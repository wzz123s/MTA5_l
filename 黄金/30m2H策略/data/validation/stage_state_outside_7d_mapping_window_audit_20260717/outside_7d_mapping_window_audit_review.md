# Stage-State Outside-7d Mapping/Accounting Window Audit

## Scope

- Reviews only outside-7d no-candidate rows from the previous triage.
- Runs 7/10/14/30-day candidate-window sensitivity for diagnostic comparison.
- Does not change the current 7-day mapper, Python signals, dynamic risk, or EA behavior.

## Closure

- Reviewed rows: `8`.
- Outside gap effect sum: `+446.064328`.
- Outside abs gap effect sum: `1090.172912`.
- P1 rows: `4`.
- Missing P1 candidate context: `0`.

## Case Bucket Summary

| case_review_bucket                                 | side             |   rows |   gap_effect_sum |   abs_gap_effect_sum |   p1_rows |   occupied_candidate_rows |
|:---------------------------------------------------|:-----------------|-------:|-----------------:|---------------------:|----------:|--------------------------:|
| outside_candidate_already_occupied_accounting_only | python_unmatched |      4 |          710.724 |              801.573 |         3 |                         4 |
| outside_candidate_already_occupied_accounting_only | mt5_unmatched    |      3 |         -210.33  |              234.27  |         1 |                         3 |
| outside_relaxed_family_window_risk                 | mt5_unmatched    |      1 |          -54.33  |               54.33  |         0 |                         0 |

## Window Sensitivity

|   window_days | policy                        |   python_trades |   mt5_trades |   matched_unique |   matched_unique_delta_vs_current |   reliable_tier_matched |   reliable_delta_vs_current |   relaxed_or_diagnostic_matched |   python_unmatched |   mt5_unmatched |   matched_profit_diff |   matched_profit_diff_delta_vs_current |   outside_7d_unique_matches |   outside_7d_same_family_matches |   outside_7d_relaxed_matches |   outside_7d_profit_diff_sum |   outside_7d_max_abs_minutes |   outside_7d_avg_abs_minutes |   outside_case_rows_resolved |   outside_python_cases_resolved |   outside_mt5_cases_resolved |   risk_far_over_14d_matches |   risk_relaxed_outside_matches | merge_gate_pass   |
|--------------:|:------------------------------|----------------:|-------------:|-----------------:|----------------------------------:|------------------------:|----------------------------:|--------------------------------:|-------------------:|----------------:|----------------------:|---------------------------------------:|----------------------------:|---------------------------------:|-----------------------------:|-----------------------------:|-----------------------------:|-----------------------------:|-----------------------------:|--------------------------------:|-----------------------------:|----------------------------:|-------------------------------:|:------------------|
|             7 | same_family_extension         |              98 |           82 |               60 |                                 0 |                      29 |                           0 |                              31 |                 38 |              22 |               654.895 |                                  0     |                           0 |                                0 |                            0 |                        0     |                              |                              |                            0 |                               0 |                            0 |                           0 |                              0 | False             |
|             7 | family_plus_relaxed_extension |              98 |           82 |               60 |                                 0 |                      29 |                           0 |                              31 |                 38 |              22 |               654.895 |                                  0     |                           0 |                                0 |                            0 |                        0     |                              |                              |                            0 |                               0 |                            0 |                           0 |                              0 | False             |
|            10 | same_family_extension         |              98 |           82 |               60 |                                 0 |                      29 |                           0 |                              31 |                 38 |              22 |               654.895 |                                  0     |                           0 |                                0 |                            0 |                        0     |                              |                              |                            0 |                               0 |                            0 |                           0 |                              0 | False             |
|            10 | family_plus_relaxed_extension |              98 |           82 |               62 |                                 2 |                      29 |                           0 |                              33 |                 36 |              20 |               624.938 |                                -29.957 |                           2 |                                0 |                            2 |                      -29.957 |                        12840 |                        11580 |                            1 |                               0 |                            1 |                           0 |                              2 | False             |
|            14 | same_family_extension         |              98 |           82 |               61 |                                 1 |                      29 |                           0 |                              32 |                 37 |              21 |               948.358 |                                293.463 |                           1 |                                1 |                            0 |                      293.463 |                        19740 |                        19740 |                            1 |                               1 |                            0 |                           0 |                              0 | False             |
|            14 | family_plus_relaxed_extension |              98 |           82 |               63 |                                 3 |                      29 |                           0 |                              34 |                 35 |              19 |               918.401 |                                263.506 |                           3 |                                1 |                            2 |                      263.506 |                        19740 |                        14300 |                            2 |                               1 |                            1 |                           0 |                              2 | False             |
|            30 | same_family_extension         |              98 |           82 |               62 |                                 2 |                      29 |                           0 |                              33 |                 36 |              20 |              1028.31  |                                373.414 |                           2 |                                2 |                            0 |                      373.414 |                        35880 |                        27810 |                            1 |                               1 |                            0 |                           1 |                              0 | False             |
|            30 | family_plus_relaxed_extension |              98 |           82 |               64 |                                 4 |                      29 |                           0 |                              35 |                 34 |              18 |               959.46  |                                304.565 |                           4 |                                2 |                            2 |                      304.565 |                        35880 |                        24570 |                            4 |                               2 |                            2 |                           2 |                              2 | False             |

## Top Outside Cases

| side             | trade_id        | target_time         | dir_norm   | trigger_family   | mode_family   |   gap_effect_$ | selected_candidate_trade_id   |   selected_candidate_abs_minutes | selected_candidate_same_family   | selected_candidate_currently_occupied   | case_review_bucket                                 |
|:-----------------|:----------------|:--------------------|:-----------|:-----------------|:--------------|---------------:|:------------------------------|---------------------------------:|:---------------------------------|:----------------------------------------|:---------------------------------------------------|
| python_unmatched | python_mt5_0091 | 2026-05-28 15:30:00 | BUY        | M15 SLOT1        | cross         |       346.215  | mt5_0078                      |                            15690 | False                            | True                                    | outside_candidate_already_occupied_accounting_only |
| python_unmatched | python_mt5_0090 | 2026-05-28 14:30:00 | BUY        | M15 SLOT1        | pre_cross     |       246.083  | mt5_0078                      |                            15750 | True                             | True                                    | outside_candidate_already_occupied_accounting_only |
| mt5_unmatched    | mt5_0077        | 2026-04-02 03:00:00 | SELL       | M15 SLOT1        | pre_cross     |      -171.9    | python_mt5_0087               |                            13020 | True                             | True                                    | outside_candidate_already_occupied_accounting_only |
| python_unmatched | python_mt5_0068 | 2025-09-30 09:30:00 | SELL       | M15 SLOT1        | pre_cross     |       163.85   | mt5_0056                      |                            22920 | True                             | True                                    | outside_candidate_already_occupied_accounting_only |
| mt5_unmatched    | mt5_0051        | 2025-09-09 16:30:00 | SELL       | M30 CLOSE        | pre_cross     |       -54.33   | python_mt5_0068               |                            29820 | False                            | False                                   | outside_relaxed_family_window_risk                 |
| mt5_unmatched    | mt5_0071        | 2026-02-24 03:00:00 | SELL       | M15 SLOT1        | pre_cross     |       -50.4    | python_mt5_0085               |                            30930 | True                             | True                                    | outside_candidate_already_occupied_accounting_only |
| python_unmatched | python_mt5_0066 | 2025-05-07 00:30:00 | SELL       | M15 SLOT1        | pre_cross     |       -45.4243 | mt5_0045                      |                            33150 | True                             | True                                    | outside_candidate_already_occupied_accounting_only |
| mt5_unmatched    | mt5_0052        | 2025-10-07 16:00:00 | BUY        | M15 SLOT1        | post_n        |        11.97   | python_mt5_0078               |                            18600 | True                             | True                                    | outside_candidate_already_occupied_accounting_only |

## Added Outside-Window Matches

|   window_days | policy                        | py_trade_id     | mt5_trade_id   | match_tier                     |   abs_time_diff_minutes | same_family   |   py_profit |   mt5_profit |   profit_diff |
|--------------:|:------------------------------|:----------------|:---------------|:-------------------------------|------------------------:|:--------------|------------:|-------------:|--------------:|
|            10 | family_plus_relaxed_extension | python_mt5_0007 | mt5_0011       | outside_window_mode_relaxed    |                   10320 | False         |   121.922   |       -26.49 |       148.412 |
|            10 | family_plus_relaxed_extension | python_mt5_0089 | mt5_0077       | outside_window_mode_relaxed    |                   12840 | False         |    -6.46907 |       171.9  |      -178.369 |
|            14 | family_plus_relaxed_extension | python_mt5_0007 | mt5_0011       | outside_window_mode_relaxed    |                   10320 | False         |   121.922   |       -26.49 |       148.412 |
|            14 | family_plus_relaxed_extension | python_mt5_0089 | mt5_0077       | outside_window_mode_relaxed    |                   12840 | False         |    -6.46907 |       171.9  |      -178.369 |
|            14 | family_plus_relaxed_extension | python_mt5_0090 | mt5_0079       | outside_window_all             |                   19740 | True          |   246.083   |       -47.38 |       293.463 |
|            14 | same_family_extension         | python_mt5_0090 | mt5_0079       | outside_window_all             |                   19740 | True          |   246.083   |       -47.38 |       293.463 |
|            30 | family_plus_relaxed_extension | python_mt5_0089 | mt5_0077       | outside_window_mode_relaxed    |                   12840 | False         |    -6.46907 |       171.9  |      -178.369 |
|            30 | family_plus_relaxed_extension | python_mt5_0090 | mt5_0079       | outside_window_all             |                   19740 | True          |   246.083   |       -47.38 |       293.463 |
|            30 | family_plus_relaxed_extension | python_mt5_0068 | mt5_0051       | outside_window_trigger_relaxed |                   29820 | False         |   163.85    |        54.33 |       109.52  |
|            30 | family_plus_relaxed_extension | python_mt5_0004 | mt5_0011       | outside_window_all             |                   35880 | True          |    53.461   |       -26.49 |        79.951 |
|            30 | same_family_extension         | python_mt5_0090 | mt5_0079       | outside_window_all             |                   19740 | True          |   246.083   |       -47.38 |       293.463 |
|            30 | same_family_extension         | python_mt5_0004 | mt5_0011       | outside_window_all             |                   35880 | True          |    53.461   |       -26.49 |        79.951 |

## Decision

- `mapping_window_rule_gate_pass`: `False`.
- `main_mapping_change_gate_open`: `False`.
- `ea_behavior_gate_open`: `False`.
- `signal_level_replay_required`: `True`.
- `merge_gate_pass`: `False`.
- Recommended next action: `do_not_expand_window_globally_review_targeted_signal_replay`.

The 7-day rule remains the accepted mapping rule. Outside-window pairs are accounting diagnostics until a targeted signal-level replay proves a real construction issue.

## Output Files

- `outside_7d_mapping_window_case_review.csv`
- `outside_7d_mapping_window_case_summary.csv`
- `outside_7d_window_candidate_summary.csv`
- `outside_7d_window_sensitivity_summary.csv`
- `outside_7d_window_added_matches.csv`
- `outside_7d_mapping_window_decision.csv`
