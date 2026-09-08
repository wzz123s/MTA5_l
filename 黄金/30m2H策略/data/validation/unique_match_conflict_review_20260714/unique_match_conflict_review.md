# Unique Match Conflict Review 20260714

## Summary

| review_classification                                 | rows | gap_sum_usd        | abs_gap_sum_usd    |
| ----------------------------------------------------- | ---- | ------------------ | ------------------ |
| stale_spec_metadata_plus_low_confidence_far_candidate | 2    | 391.47246          | 391.47246          |
| duplicate_python_continuation_after_exact_mt5_match   | 7    | 147.90771900000001 | 221.35270300000005 |
| low_confidence_far_candidate_conflict                 | 7    | 100.37292599999999 | 134.699204         |
| occupied_mt5_candidate_mapping_conflict               | 1    | -3.732822          | 3.732822           |

## Top Focus Cases

| trade_id        | target_time         | mode_or_signal_src | gap_effect_$ | spec_pass | spec_reason | sd                 | actual_spec_pass | spec_flag_stale | best_candidate_mt5 | best_candidate_tier | best_candidate_abs_minutes | selected_owner_py | selected_owner_tier | review_classification                                 |
| --------------- | ------------------- | ------------------ | ------------ | --------- | ----------- | ------------------ | ---------------- | --------------- | ------------------ | ------------------- | -------------------------- | ----------------- | ------------------- | ----------------------------------------------------- |
| python_mt5_0079 | 2025-10-21 10:00:00 | post_n6            | 201.85136    | False     | too_wide    | 32.32603000000017  | True             | True            | mt5_0056           | nearby_7d_all       | 5490.0                     | python_mt5_0074   | exact_align90_all   | stale_spec_metadata_plus_low_confidence_far_candidate |
| python_mt5_0073 | 2025-10-17 11:00:00 | pre_cross          | 189.6211     | False     | too_tight   | 10.36772000000019  | True             | True            | mt5_0055           | nearby_7d_all       | 1650.0                     | python_mt5_0072   | exact_align90_all   | stale_spec_metadata_plus_low_confidence_far_candidate |
| python_mt5_0075 | 2025-10-17 15:00:00 | post_n4            | 150.91695    | True      | ok          | 12.636389999999665 | True             | False           | mt5_0056           | nearby_60_all       | 30.0                       | python_mt5_0074   | exact_align90_all   | duplicate_python_continuation_after_exact_mt5_match   |

## Decision

- These cases are not evidence for reopening the EA price-side repair gate.
- Current top `spec_pass=False` labels are stale metadata after rescue/reanchor; their current `sd` is inside the 5-35 StopSpec range.
- Recompute rescue metadata before using `spec_pass/spec_reason` as a gating or diagnostic field.
- `nearby_60_all` cases whose MT5 target is already occupied by an exact match should be reviewed as duplicate continuation/cluster policy.

## Output Files

- `unique_match_conflict_case_summary.csv`
- `unique_match_conflict_candidate_occupancy.csv`
- `unique_match_conflict_signal_chain_window.csv`
- `unique_match_conflict_classification_summary.csv`
