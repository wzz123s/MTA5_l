# Stage-State Targeted Raw Signal Replay

## Scope

- Reviews only `mt5_0076`, `mt5_0067`, `mt5_0044`, and `mt5_0026`.
- Links MT5-only targets to Python raw, Layer1/2, Layer3, stage export, and dynamic executed records.
- Does not change Python signals, mapping rules, dynamic risk, or EA behavior.

## Summary

- Reviewed rows: `4`.
- Reviewed abs gap: `349.200000`.
- Raw-absent abs gap: `163.540000`.
- Layer1/2 abs gap: `80.960000`.
- Layer3 abs gap: `104.700000`.
- Execution abs gap: `0.000000`.

## Loss Point Summary

| raw_chain_loss_point                          |   rows |   abs_gap_effect_sum | targets   | recommended_next_action          |
|:----------------------------------------------|-------:|---------------------:|:----------|:---------------------------------|
| layer3_displaced_by_nearby_opposite_selection |      1 |               104.7  | mt5_0076  | layer3_gate_raw_replay           |
| raw_absent_nearby_opposite_selected           |      1 |                88.35 | mt5_0067  | raw_signal_replay_no_main_change |
| layer12_trigger_family_drift_after_raw_parent |      1 |                80.96 | mt5_0044  | trigger_family_transform_audit   |
| raw_absent_for_mt5_signal                     |      1 |                75.19 | mt5_0026  | python_raw_generation_audit      |

## Case Review

| trade_id   | target_time         | dir_norm   | trigger_family   | mode_family   |   abs_gap_effect_$ |   raw_exact_equivalent_count |   layer12_exact_same_family_count |   layer3_exact_same_family_count |   dynamic_exact_same_family_count | raw_chain_loss_point                          | recommended_next_action          |
|:-----------|:--------------------|:-----------|:-----------------|:--------------|-------------------:|-----------------------------:|----------------------------------:|---------------------------------:|----------------------------------:|:----------------------------------------------|:---------------------------------|
| mt5_0076   | 2026-03-24 12:00:00 | BUY        | M15 SLOT1        | post_n        |             104.7  |                            1 |                                 1 |                                0 |                                 0 | layer3_displaced_by_nearby_opposite_selection | layer3_gate_raw_replay           |
| mt5_0067   | 2026-02-02 16:30:00 | BUY        | M15 SLOT1        | post_n        |              88.35 |                            0 |                                 0 |                                0 |                                 0 | raw_absent_nearby_opposite_selected           | raw_signal_replay_no_main_change |
| mt5_0044   | 2024-11-13 19:30:00 | SELL       | M30 CLOSE        | post_n        |              80.96 |                            1 |                                 0 |                                0 |                                 0 | layer12_trigger_family_drift_after_raw_parent | trigger_family_transform_audit   |
| mt5_0026   | 2021-11-10 16:30:00 | BUY        | M30 CLOSE        | post_n        |              75.19 |                            0 |                                 0 |                                0 |                                 0 | raw_absent_for_mt5_signal                     | python_raw_generation_audit      |

## Decision

- `main_signal_change_gate_open`: `False`.
- `ea_behavior_gate_open`: `False`.
- `targeted_signal_prototype_required`: `True`.
- `merge_gate_pass`: `False`.
- Recommended next action: `audit_python_raw_generation_vs_mt5_signal_source`.

The raw replay identifies where each target drops from the Python chain, but it is not a merge signal. A prototype must be run before main logic changes.

## Output Files

- `targeted_raw_signal_replay_case_review.csv`
- `targeted_raw_signal_replay_window_counts.csv`
- `targeted_raw_signal_replay_context_rows.csv`
- `targeted_raw_signal_replay_summary.csv`
- `targeted_raw_signal_replay_decision.csv`
