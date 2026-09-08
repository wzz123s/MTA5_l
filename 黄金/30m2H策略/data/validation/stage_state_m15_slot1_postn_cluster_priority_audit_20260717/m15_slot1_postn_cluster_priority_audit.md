# Stage-State M15 SLOT1 post_n Cluster Priority / Ranking Audit

## Scope

- Diagnostic-only audit for same-family M15 SLOT1/post_n rescue clusters.
- Compares earliest/latest/max-mode/min-profit/MT5-proximity choices.
- Uses lifecycle trace from the prior non-destructive probe.
- Does not modify baseline signals, EA behavior, dynamic risk, or mapping.

## Final Decision

- Same-family cluster count: `2`.
- MT5 exact-supported cluster count: `1`.
- Ranking rules tested: `8`.
- Rules selecting `mt5_0076` target: `6`.
- Ranking rule gate pass count: `0`.
- Decision: `ranking_rule_not_proven_single_mt5_supported_cluster`.
- Recommended next action: `audit_mt5_0076_postn_counter_anchor_before_ranking_prototype`.
- `main_signal_change_gate_open = False`.
- `ea_behavior_gate_open = False`.
- `mapping_change_gate_open = False`.
- `merge_gate_pass = False`.

## Cluster Summary

| candidate_cluster_key                     |   cluster_rows | dir_norm   | cluster_min_time    | cluster_max_time    | mode_list                               |   mode_n_min |   mode_n_max |   source_profit_min |   source_profit_max |   negative_rows | all_negative   |   exact_same_family_mt5_candidate_count | exact_same_family_mt5_ids   |   min_same_family_mt5_abs_minutes | contains_mt5_0076_target_time   |
|:------------------------------------------|---------------:|:-----------|:--------------------|:--------------------|:----------------------------------------|-------------:|-------------:|--------------------:|--------------------:|----------------:|:---------------|----------------------------------------:|:----------------------------|----------------------------------:|:--------------------------------|
| 2025-10-20 14:00:00|M15 SLOT1|post_n|SELL |              3 | SELL       | 2025-10-21 08:00:00 | 2025-10-21 09:30:00 | post_n2;post_n4;post_n5                 |            2 |            5 |             -16.846 |            222.464  |               1 | False          |                                       0 |                             |                              5370 | False                           |
| 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  |              5 | BUY        | 2026-03-24 10:00:00 | 2026-03-24 12:00:00 | post_n2;post_n3;post_n4;post_n5;post_n6 |            2 |            6 |             -30.904 |            -12.5458 |               5 | True           |                                       1 | mt5_0076                    |                                 0 | True                            |

## Rule Summary

| rule                    |   clusters_considered |   clusters_with_choice |   mt5_supported_clusters_total |   choices_with_exact_same_family_mt5 |   choices_with_exact_supported_cluster |   choices_within_60m_same_family_mt5 | selects_mt5_0076_target_time   | ranking_rule_gate_pass   | decision                                |
|:------------------------|----------------------:|-----------------------:|-------------------------------:|-------------------------------------:|---------------------------------------:|-------------------------------------:|:-------------------------------|:-------------------------|:----------------------------------------|
| latest                  |                     2 |                      2 |                              1 |                                    1 |                                      1 |                                    1 | True                           | False                    | single_mt5_supported_cluster_not_proven |
| latest_negative         |                     2 |                      2 |                              1 |                                    1 |                                      1 |                                    1 | True                           | False                    | single_mt5_supported_cluster_not_proven |
| max_mode_n              |                     2 |                      2 |                              1 |                                    1 |                                      1 |                                    1 | True                           | False                    | single_mt5_supported_cluster_not_proven |
| max_mode_negative       |                     2 |                      2 |                              1 |                                    1 |                                      1 |                                    1 | True                           | False                    | single_mt5_supported_cluster_not_proven |
| min_source_profit       |                     2 |                      2 |                              1 |                                    1 |                                      1 |                                    1 | True                           | False                    | single_mt5_supported_cluster_not_proven |
| nearest_same_family_mt5 |                     2 |                      2 |                              1 |                                    1 |                                      1 |                                    1 | True                           | False                    | single_mt5_supported_cluster_not_proven |
| earliest                |                     2 |                      2 |                              1 |                                    0 |                                      0 |                                    0 | False                          | False                    | no_exact_mt5_support                    |
| max_source_profit       |                     2 |                      2 |                              1 |                                    0 |                                      0 |                                    0 | False                          | False                    | no_exact_mt5_support                    |

## Lifecycle Trace For Same-Family8

| candidate_cluster_key                     | row_time            | active_until        | dir_norm   | mode    |   mode_n | is_target_candidate   |   active_count_before | active_blockers_before                                                                                                     | accepted   | stage1_exit   | stage2_exit   | stage3_exit      |   stage_total_$ |
|:------------------------------------------|:--------------------|:--------------------|:-----------|:--------|---------:|:----------------------|----------------------:|:---------------------------------------------------------------------------------------------------------------------------|:-----------|:--------------|:--------------|:-----------------|----------------:|
| 2025-10-20 14:00:00|M15 SLOT1|post_n|SELL | 2025-10-21 08:00:00 | 2025-10-21 08:30:00 | SELL       | post_n2 |        2 | False                 |                     0 | nan                                                                                                                        | True       | SL hit        | trail/SL hit  | SL hit           |       -10.1076  |
| 2025-10-20 14:00:00|M15 SLOT1|post_n|SELL | 2025-10-21 09:00:00 | 2025-10-22 21:30:00 | SELL       | post_n4 |        4 | False                 |                     0 | nan                                                                                                                        | True       | 2.0R TP       | 4.0R forced   | M30 merged cross |        61.641   |
| 2025-10-20 14:00:00|M15 SLOT1|post_n|SELL | 2025-10-21 09:30:00 | 2025-10-22 21:30:00 | SELL       | post_n5 |        5 | False                 |                     1 | 2025-10-21 09:00:00 SELL M15 SLOT1/post_n                                                                                  | True       | 2.0R TP       | 4.0R forced   | M30 merged cross |        57.8789  |
| 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  | 2026-03-24 10:00:00 | 2026-03-24 13:00:00 | BUY        | post_n2 |        2 | False                 |                     0 | nan                                                                                                                        | True       | 2.0R TP       | trail/SL hit  | SL hit           |         2.69237 |
| 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  | 2026-03-24 10:30:00 | 2026-03-24 13:00:00 | BUY        | post_n3 |        3 | False                 |                     1 | 2026-03-24 10:00:00 BUY M15 SLOT1/post_n                                                                                   | True       | 2.0R TP       | trail/SL hit  | SL hit           |         2.22687 |
| 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  | 2026-03-24 11:00:00 | 2026-03-24 13:00:00 | BUY        | post_n4 |        4 | False                 |                     2 | 2026-03-24 10:00:00 BUY M15 SLOT1/post_n;2026-03-24 10:30:00 BUY M15 SLOT1/post_n                                          | True       | SL hit        | trail/SL hit  | SL hit           |       -15.6825  |
| 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  | 2026-03-24 11:30:00 | 2026-03-24 13:00:00 | BUY        | post_n5 |        5 | False                 |                     3 | 2026-03-24 10:00:00 BUY M15 SLOT1/post_n;2026-03-24 10:30:00 BUY M15 SLOT1/post_n;2026-03-24 11:00:00 BUY M15 SLOT1/post_n | False      | SL hit        | trail/SL hit  | SL hit           |        -9.77822 |
| 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  | 2026-03-24 12:00:00 | 2026-03-24 13:00:00 | BUY        | post_n6 |        6 | True                  |                     3 | 2026-03-24 10:00:00 BUY M15 SLOT1/post_n;2026-03-24 10:30:00 BUY M15 SLOT1/post_n;2026-03-24 11:00:00 BUY M15 SLOT1/post_n | False      | SL hit        | trail/SL hit  | SL hit           |       -18.5424  |

## Candidate Rows

| candidate_cluster_key                     | row_time            | dir_norm   | mode    |   source_profit_num | exact_same_family_mt5_id   | nearest_same_family_mt5_id   |   nearest_same_family_mt5_abs_minutes | target_like_strict   |
|:------------------------------------------|:--------------------|:-----------|:--------|--------------------:|:---------------------------|:-----------------------------|--------------------------------------:|:---------------------|
| 2025-10-20 14:00:00|M15 SLOT1|post_n|SELL | 2025-10-21 08:00:00 | SELL       | post_n2 |            -16.846  |                            | mt5_0057                     |                                  5370 | False                |
| 2025-10-20 14:00:00|M15 SLOT1|post_n|SELL | 2025-10-21 09:00:00 | SELL       | post_n4 |            222.464  |                            | mt5_0057                     |                                  5430 | False                |
| 2025-10-20 14:00:00|M15 SLOT1|post_n|SELL | 2025-10-21 09:30:00 | SELL       | post_n5 |            222.464  |                            | mt5_0057                     |                                  5460 | False                |
| 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  | 2026-03-24 10:00:00 | BUY        | post_n2 |            -14.8732 |                            | mt5_0076                     |                                   120 | False                |
| 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  | 2026-03-24 10:30:00 | BUY        | post_n3 |            -12.5458 |                            | mt5_0076                     |                                    90 | False                |
| 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  | 2026-03-24 11:00:00 | BUY        | post_n4 |            -26.1376 |                            | mt5_0076                     |                                    60 | False                |
| 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  | 2026-03-24 11:30:00 | BUY        | post_n5 |            -18.3633 |                            | mt5_0076                     |                                    30 | False                |
| 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  | 2026-03-24 12:00:00 | BUY        | post_n6 |            -30.904  | mt5_0076                   | mt5_0076                     |                                     0 | True                 |

## Rule Choices

| rule                    | candidate_cluster_key                     | rule_applicable   | selected_time       | selected_dir   | selected_mode   |   selected_mode_n |   selected_source_profit | exact_same_family_mt5_id   | nearest_same_family_mt5_id   |   nearest_same_family_mt5_abs_minutes | nearest_same_family_mt5_signal_src   | selects_mt5_0076_target_time   |
|:------------------------|:------------------------------------------|:------------------|:--------------------|:---------------|:----------------|------------------:|-------------------------:|:---------------------------|:-----------------------------|--------------------------------------:|:-------------------------------------|:-------------------------------|
| earliest                | 2025-10-20 14:00:00|M15 SLOT1|post_n|SELL | True              | 2025-10-21 08:00:00 | SELL           | post_n2         |                 2 |                 -16.846  |                            | mt5_0057                     |                                  5370 | post_n2_m15_slot1_replace_or_rescue  | False                          |
| latest                  | 2025-10-20 14:00:00|M15 SLOT1|post_n|SELL | True              | 2025-10-21 09:30:00 | SELL           | post_n5         |                 5 |                 222.464  |                            | mt5_0057                     |                                  5460 | post_n2_m15_slot1_replace_or_rescue  | False                          |
| max_mode_n              | 2025-10-20 14:00:00|M15 SLOT1|post_n|SELL | True              | 2025-10-21 09:30:00 | SELL           | post_n5         |                 5 |                 222.464  |                            | mt5_0057                     |                                  5460 | post_n2_m15_slot1_replace_or_rescue  | False                          |
| min_source_profit       | 2025-10-20 14:00:00|M15 SLOT1|post_n|SELL | True              | 2025-10-21 08:00:00 | SELL           | post_n2         |                 2 |                 -16.846  |                            | mt5_0057                     |                                  5370 | post_n2_m15_slot1_replace_or_rescue  | False                          |
| max_source_profit       | 2025-10-20 14:00:00|M15 SLOT1|post_n|SELL | True              | 2025-10-21 09:00:00 | SELL           | post_n4         |                 4 |                 222.464  |                            | mt5_0057                     |                                  5430 | post_n2_m15_slot1_replace_or_rescue  | False                          |
| latest_negative         | 2025-10-20 14:00:00|M15 SLOT1|post_n|SELL | True              | 2025-10-21 08:00:00 | SELL           | post_n2         |                 2 |                 -16.846  |                            | mt5_0057                     |                                  5370 | post_n2_m15_slot1_replace_or_rescue  | False                          |
| max_mode_negative       | 2025-10-20 14:00:00|M15 SLOT1|post_n|SELL | True              | 2025-10-21 08:00:00 | SELL           | post_n2         |                 2 |                 -16.846  |                            | mt5_0057                     |                                  5370 | post_n2_m15_slot1_replace_or_rescue  | False                          |
| nearest_same_family_mt5 | 2025-10-20 14:00:00|M15 SLOT1|post_n|SELL | True              | 2025-10-21 08:00:00 | SELL           | post_n2         |                 2 |                 -16.846  |                            | mt5_0057                     |                                  5370 | post_n2_m15_slot1_replace_or_rescue  | False                          |
| earliest                | 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  | True              | 2026-03-24 10:00:00 | BUY            | post_n2         |                 2 |                 -14.8732 |                            | mt5_0076                     |                                   120 | post_n5_m15_slot1_replace_or_rescue  | False                          |
| latest                  | 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  | True              | 2026-03-24 12:00:00 | BUY            | post_n6         |                 6 |                 -30.904  | mt5_0076                   | mt5_0076                     |                                     0 | post_n5_m15_slot1_replace_or_rescue  | True                           |
| max_mode_n              | 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  | True              | 2026-03-24 12:00:00 | BUY            | post_n6         |                 6 |                 -30.904  | mt5_0076                   | mt5_0076                     |                                     0 | post_n5_m15_slot1_replace_or_rescue  | True                           |
| min_source_profit       | 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  | True              | 2026-03-24 12:00:00 | BUY            | post_n6         |                 6 |                 -30.904  | mt5_0076                   | mt5_0076                     |                                     0 | post_n5_m15_slot1_replace_or_rescue  | True                           |
| max_source_profit       | 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  | True              | 2026-03-24 10:30:00 | BUY            | post_n3         |                 3 |                 -12.5458 |                            | mt5_0076                     |                                    90 | post_n5_m15_slot1_replace_or_rescue  | False                          |
| latest_negative         | 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  | True              | 2026-03-24 12:00:00 | BUY            | post_n6         |                 6 |                 -30.904  | mt5_0076                   | mt5_0076                     |                                     0 | post_n5_m15_slot1_replace_or_rescue  | True                           |
| max_mode_negative       | 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  | True              | 2026-03-24 12:00:00 | BUY            | post_n6         |                 6 |                 -30.904  | mt5_0076                   | mt5_0076                     |                                     0 | post_n5_m15_slot1_replace_or_rescue  | True                           |
| nearest_same_family_mt5 | 2026-03-24 05:00:00|M15 SLOT1|post_n|BUY  | True              | 2026-03-24 12:00:00 | BUY            | post_n6         |                 6 |                 -30.904  | mt5_0076                   | mt5_0076                     |                                     0 | post_n5_m15_slot1_replace_or_rescue  | True                           |

## Interpretation

- Rules such as latest/max-mode/min-profit can select the `mt5_0076` target row.
- The support comes from only one MT5 exact-supported cluster; the 2025-10-21 SELL cluster has no same-family MT5 exact counterpart.
- Therefore cluster ranking is not proven enough for a main signal change or a merge gate.

## Output Files

- `cluster_priority_candidate_rows.csv`
- `cluster_priority_cluster_summary.csv`
- `cluster_priority_rule_choices.csv`
- `cluster_priority_rule_summary.csv`
- `cluster_priority_lifecycle_trace.csv`
- `cluster_priority_final_decision.csv`
