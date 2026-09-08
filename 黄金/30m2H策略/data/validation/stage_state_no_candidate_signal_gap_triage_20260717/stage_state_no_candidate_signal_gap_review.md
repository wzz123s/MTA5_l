# Stage-State No-Candidate Signal Gap Triage

## Scope

- Reviews only rows classified as `python_only_signal_gap_no_mt5_candidate` or `mt5_only_signal_gap_no_python_candidate`.
- Widens candidate context to 30/90 days for diagnostic classification.
- Does not change mapping, Python signals, dynamic risk, or EA behavior.

## Closure

- Reviewed rows: `22`.
- Python-only rows: `10`.
- MT5-only rows: `12`.
- Recomputed gap effect: `+677.136628`.
- Expected gap effect: `+677.136628`.
- Recompute error: `+0.000000000`.
- Recomputed abs gap: `1847.409952`.

## Action Bucket Summary

| no_candidate_action_bucket                      | side             |   rows |   gap_effect_sum |   abs_gap_effect_sum |   max_abs_gap_effect |   p1_rows |
|:------------------------------------------------|:-----------------|-------:|-----------------:|---------------------:|---------------------:|----------:|
| outside_7d_same_family_mapping_window_review    | python_unmatched |      3 |        364.509   |             455.358  |             246.083  |         2 |
| nearby_opposite_direction_signal_divergence     | mt5_unmatched    |      6 |        120.13    |             381.05   |             104.7    |         0 |
| outside_7d_same_direction_mapping_window_review | python_unmatched |      1 |        346.215   |             346.215  |             346.215  |         1 |
| outside_7d_same_family_mapping_window_review    | mt5_unmatched    |      3 |       -210.33    |             234.27   |             171.9    |         1 |
| python_before_first_mt5_trade_gap               | python_unmatched |      4 |          3.06397 |             198.203  |              77.2589 |         0 |
| m30_post_n_true_no_candidate_signal_gap         | mt5_unmatched    |      2 |        135.1     |             135.1    |              75.19   |         0 |
| outside_7d_same_direction_mapping_window_review | mt5_unmatched    |      1 |        -54.33    |              54.33   |              54.33   |         0 |
| nearby_opposite_direction_signal_divergence     | python_unmatched |      1 |        -35.0527  |              35.0527 |              35.0527 |         0 |
| m15_slot1_true_no_candidate_signal_gap          | python_unmatched |      1 |          7.831   |               7.831  |               7.831  |         0 |

## Trigger/Mode Summary

| side             | trigger_family   | mode_family   |   rows |   gap_effect_sum |   abs_gap_effect_sum | top_trade_id    |
|:-----------------|:-----------------|:--------------|-------:|-----------------:|---------------------:|:----------------|
| python_unmatched | M15 SLOT1        | pre_cross     |      4 |         329.456  |              490.41  | python_mt5_0090 |
| python_unmatched | M15 SLOT1        | cross         |      2 |         354.046  |              354.046 | python_mt5_0091 |
| mt5_unmatched    | M30 CLOSE        | post_n        |      6 |          62.18   |              323.1   | mt5_0044        |
| mt5_unmatched    | M15 SLOT1        | pre_cross     |      2 |        -222.3    |              222.3   | mt5_0077        |
| mt5_unmatched    | M15 SLOT1        | post_n        |      3 |         205.02   |              205.02  | mt5_0076        |
| python_unmatched | M30 CLOSE        | cross         |      3 |         -50.3971 |              144.742 | python_mt5_0001 |
| mt5_unmatched    | M30 CLOSE        | pre_cross     |      1 |         -54.33   |               54.33  | mt5_0051        |
| python_unmatched | M30 CLOSE        | post_n        |      1 |          53.461  |               53.461 | python_mt5_0004 |

## Top Cases

| side             | trade_id        | target_time         | dir_norm   | trigger_family   | mode_family   |   gap_effect_$ |   abs_gap_effect_$ | no_candidate_action_bucket                      |   nearest_same_dir_minutes |   opposite_dir_7d_count |
|:-----------------|:----------------|:--------------------|:-----------|:-----------------|:--------------|---------------:|-------------------:|:------------------------------------------------|---------------------------:|------------------------:|
| python_unmatched | python_mt5_0091 | 2026-05-28 15:30:00 | BUY        | M15 SLOT1        | cross         |       346.215  |           346.215  | outside_7d_same_direction_mapping_window_review |                      15690 |                       0 |
| python_unmatched | python_mt5_0090 | 2026-05-28 14:30:00 | BUY        | M15 SLOT1        | pre_cross     |       246.083  |           246.083  | outside_7d_same_family_mapping_window_review    |                      15750 |                       0 |
| mt5_unmatched    | mt5_0077        | 2026-04-02 03:00:00 | SELL       | M15 SLOT1        | pre_cross     |      -171.9    |           171.9    | outside_7d_same_family_mapping_window_review    |                      12840 |                       0 |
| python_unmatched | python_mt5_0068 | 2025-09-30 09:30:00 | SELL       | M15 SLOT1        | pre_cross     |       163.85   |           163.85   | outside_7d_same_family_mapping_window_review    |                      12540 |                       0 |
| mt5_unmatched    | mt5_0076        | 2026-03-24 12:00:00 | BUY        | M15 SLOT1        | post_n        |       104.7    |           104.7    | nearby_opposite_direction_signal_divergence     |                      93750 |                       3 |
| mt5_unmatched    | mt5_0067        | 2026-02-02 16:30:00 | BUY        | M15 SLOT1        | post_n        |        88.35   |            88.35   | nearby_opposite_direction_signal_divergence     |                     151350 |                       5 |
| mt5_unmatched    | mt5_0044        | 2024-11-13 19:30:00 | SELL       | M30 CLOSE        | post_n        |       -80.96   |            80.96   | nearby_opposite_direction_signal_divergence     |                     171480 |                       1 |
| python_unmatched | python_mt5_0001 | 2019-08-13 15:30:00 | SELL       | M30 CLOSE        | cross         |       -77.2589 |            77.2589 | python_before_first_mt5_trade_gap               |                     306750 |                       0 |
| mt5_unmatched    | mt5_0026        | 2021-11-10 16:30:00 | BUY        | M30 CLOSE        | post_n        |        75.19   |            75.19   | m30_post_n_true_no_candidate_signal_gap         |                     168780 |                       0 |
| mt5_unmatched    | mt5_0061        | 2026-01-13 17:30:00 | BUY        | M30 CLOSE        | post_n        |        59.91   |            59.91   | m30_post_n_true_no_candidate_signal_gap         |                     122610 |                       0 |

## Decision

- `ea_behavior_gate_open`: `False`.
- `main_signal_change_gate_open`: `False`.
- `signal_level_prototype_required`: `True`.
- `merge_gate_pass`: `False`.
- Recommended next action: `audit_mapping_window_accounting_then_signal_replay`.

No-candidate rows are now separated from mapping unique-conflict and duplicate-continuation diagnostics. The next executable step should replay these raw signal moments at signal level before modifying main strategy logic.

## Output Files

- `stage_state_no_candidate_signal_gap_cases.csv`
- `stage_state_no_candidate_signal_gap_bucket_summary.csv`
- `stage_state_no_candidate_trigger_mode_summary.csv`
- `stage_state_no_candidate_signal_gap_decision.csv`
