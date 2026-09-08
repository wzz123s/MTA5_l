# Stage-State Targeted Signal-Level Replay

## Scope

- Reviews all outside-7d cases plus no-candidate P1/P2 moments.
- Uses the current Python-MT5 dynamic trades, MT5 stage-state ledger, and the closest available Python signal-chain export.
- Does not rerun the strategy, change signal logic, change mapping rules, or modify EA behavior.

## Coverage

- Reviewed rows: `13`.
- P1/P2 rows: `9`.
- Reviewed abs gap: `1516.631802`.
- Accounting-only abs gap: `1090.172912`.
- Lifecycle candidate abs gap: `0.000000`.
- True-signal candidate abs gap: `75.190000`.
- Directional divergence abs gap: `274.010000`.

## Classification Summary

| replay_classification                          | side             |   rows |   gap_effect_sum |   abs_gap_effect_sum |   p1_rows |   counterpart_active_rows |
|:-----------------------------------------------|:-----------------|-------:|-----------------:|---------------------:|----------:|--------------------------:|
| accounting_only_occupied_outside_candidate     | python_unmatched |      4 |         710.724  |             801.573  |         3 |                         0 |
| directional_signal_divergence_needs_raw_replay | mt5_unmatched    |      3 |         112.09   |             274.01   |         0 |                         0 |
| accounting_only_occupied_outside_candidate     | mt5_unmatched    |      3 |        -210.33   |             234.27   |         1 |                         0 |
| boundary_window_gap                            | python_unmatched |      1 |         -77.2589 |              77.2589 |         0 |                         0 |
| mt5_only_true_signal_needs_python_replay       | mt5_unmatched    |      1 |          75.19   |              75.19   |         0 |                         0 |
| accounting_only_relaxed_window_risk            | mt5_unmatched    |      1 |         -54.33   |              54.33   |         0 |                         0 |

## Top Cases

| target_case_id   | side             | trade_id        | target_time         | dir_norm   | trigger_family   | mode_family   |   abs_gap_effect_$ |   counterpart_active_count |   python_layer3_exact_same_family |   python_dynamic_exact_same_family |   mt5_unique_exact_same_family | replay_classification                          | recommended_next_action       |
|:-----------------|:-----------------|:----------------|:--------------------|:-----------|:-----------------|:--------------|-------------------:|---------------------------:|----------------------------------:|-----------------------------------:|-------------------------------:|:-----------------------------------------------|:------------------------------|
| target_001       | python_unmatched | python_mt5_0091 | 2026-05-28 15:30:00 | BUY        | M15 SLOT1        | cross         |           346.215  |                          0 |                                 1 |                                  1 |                              0 | accounting_only_occupied_outside_candidate     | keep_accounting_only          |
| target_002       | python_unmatched | python_mt5_0090 | 2026-05-28 14:30:00 | BUY        | M15 SLOT1        | pre_cross     |           246.083  |                          0 |                                 0 |                                  1 |                              0 | accounting_only_occupied_outside_candidate     | keep_accounting_only          |
| target_003       | mt5_unmatched    | mt5_0077        | 2026-04-02 03:00:00 | SELL       | M15 SLOT1        | pre_cross     |           171.9    |                          0 |                                 0 |                                  0 |                              1 | accounting_only_occupied_outside_candidate     | keep_accounting_only          |
| target_004       | python_unmatched | python_mt5_0068 | 2025-09-30 09:30:00 | SELL       | M15 SLOT1        | pre_cross     |           163.85   |                          0 |                                 1 |                                  1 |                              0 | accounting_only_occupied_outside_candidate     | keep_accounting_only          |
| target_005       | mt5_unmatched    | mt5_0076        | 2026-03-24 12:00:00 | BUY        | M15 SLOT1        | post_n        |           104.7    |                          0 |                                 0 |                                  0 |                              1 | directional_signal_divergence_needs_raw_replay | targeted_signal_raw_replay    |
| target_006       | mt5_unmatched    | mt5_0067        | 2026-02-02 16:30:00 | BUY        | M15 SLOT1        | post_n        |            88.35   |                          0 |                                 0 |                                  0 |                              1 | directional_signal_divergence_needs_raw_replay | targeted_signal_raw_replay    |
| target_007       | mt5_unmatched    | mt5_0044        | 2024-11-13 19:30:00 | SELL       | M30 CLOSE        | post_n        |            80.96   |                          0 |                                 0 |                                  0 |                              1 | directional_signal_divergence_needs_raw_replay | targeted_signal_raw_replay    |
| target_008       | python_unmatched | python_mt5_0001 | 2019-08-13 15:30:00 | SELL       | M30 CLOSE        | cross         |            77.2589 |                          0 |                                 1 |                                  1 |                              0 | boundary_window_gap                            | audit_data_window_or_warmup   |
| target_009       | mt5_unmatched    | mt5_0026        | 2021-11-10 16:30:00 | BUY        | M30 CLOSE        | post_n        |            75.19   |                          0 |                                 0 |                                  0 |                              1 | mt5_only_true_signal_needs_python_replay       | targeted_python_signal_replay |
| target_010       | mt5_unmatched    | mt5_0051        | 2025-09-09 16:30:00 | SELL       | M30 CLOSE        | pre_cross     |            54.33   |                          0 |                                 0 |                                  0 |                              1 | accounting_only_relaxed_window_risk            | keep_accounting_only          |
| target_011       | mt5_unmatched    | mt5_0071        | 2026-02-24 03:00:00 | SELL       | M15 SLOT1        | pre_cross     |            50.4    |                          0 |                                 0 |                                  0 |                              1 | accounting_only_occupied_outside_candidate     | keep_accounting_only          |
| target_012       | python_unmatched | python_mt5_0066 | 2025-05-07 00:30:00 | SELL       | M15 SLOT1        | pre_cross     |            45.4243 |                          0 |                                 1 |                                  1 |                              0 | accounting_only_occupied_outside_candidate     | keep_accounting_only          |

## Decision

- `main_signal_change_gate_open`: `False`.
- `ea_behavior_gate_open`: `False`.
- `lifecycle_prototype_required`: `False`.
- `raw_signal_replay_required`: `True`.
- `merge_gate_pass`: `False`.
- Recommended next action: `targeted_raw_signal_replay_before_main_logic_change`.

The replay evidence keeps the current main logic closed. Any behavior change still needs a targeted non-destructive prototype and full-chain rerun.

## Output Files

- `targeted_signal_replay_case_review.csv`
- `targeted_signal_replay_context_rows.csv`
- `targeted_signal_replay_classification_summary.csv`
- `targeted_signal_replay_decision.csv`
