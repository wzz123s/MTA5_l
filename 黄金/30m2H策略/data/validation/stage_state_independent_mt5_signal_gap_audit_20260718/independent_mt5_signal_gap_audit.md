# Stage-state independent MT5 signal gap audit

## Decision

- MT5-unmatched rows reviewed: `22`
- True independent signal candidate rows: `2`
- True independent signal candidate abs gap: `135.1`
- Candidate ids: `mt5_0026;mt5_0061`
- Recommended next task: `Stage-state M30 CLOSE post_n true no-candidate source audit`
- Main signal / EA behavior / mapping / dynamic-risk / merge gates all remain `False`.

## True Candidate Rows

- `mt5_0026` `2021-11-10 16:30:00` `M30 CLOSE/post_n` abs gap `75.19`, class `m30_close_postn_true_no_candidate_candidate`, next `python_raw_generation_audit`
- `mt5_0061` `2026-01-13 17:30:00` `M30 CLOSE/post_n` abs gap `59.91`, class `m30_close_postn_true_no_candidate_candidate`, next `python_raw_generation_audit`

## Bucket Summary

- candidate `True` `m30_close_postn_true_no_candidate_candidate`: rows `2`, abs `135.1`, ids `mt5_0026;mt5_0061`
- candidate `False` `time_axis_diagnostic_only`: rows `5`, abs `574.05`, ids `mt5_0070;mt5_0005;mt5_0019;mt5_0021;mt5_0037`
- candidate `False` `mapping_policy_unique_conflict_accounting`: rows `4`, abs `308.7`, ids `mt5_0049;mt5_0059;mt5_0079;mt5_0011`
- candidate `False` `outside_7d_mapping_window_accounting`: rows `3`, abs `276.63`, ids `mt5_0077;mt5_0051;mt5_0071`
- candidate `False` `nearby_opposite_direction_divergence_defer`: rows `3`, abs `107.04`, ids `mt5_0065;mt5_0017;mt5_0075`
- candidate `False` `layer3_displacement_prototype_not_mergeable`: rows `1`, abs `104.7`, ids `mt5_0076`
- candidate `False` `base_sequence_reset_gap_defer`: rows `1`, abs `88.35`, ids `mt5_0067`
- candidate `False` `layer12_trigger_family_drift_high_blast_defer`: rows `1`, abs `80.96`, ids `mt5_0044`
- candidate `False` `raw_present_layer12_filtered_defer`: rows `1`, abs `70.14`, ids `mt5_0072`
- candidate `False` `runtime_label_layer3_threshold_closed`: rows `1`, abs `11.97`, ids `mt5_0052`

## Interpretation

- Mapping-policy, time-axis, outside-7d, runtime-label threshold, and high-blast trigger-family buckets remain diagnostic/accounting only.
- The only narrow remaining independent-signal candidate cohort is `M30 CLOSE/post_n` true no-candidate, currently `mt5_0026` and `mt5_0061`.
- This does not open a signal-change gate; it only selects the next source audit.
