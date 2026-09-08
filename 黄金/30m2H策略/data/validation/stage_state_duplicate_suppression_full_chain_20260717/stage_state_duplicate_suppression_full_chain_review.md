# Stage-State Duplicate Suppression Filtered Mapping Rerun

## Scope

- Non-destructive validation only.
- Filters the 8 duplicate-continuation candidates from the Python-MT5 dynamic trade list.
- Recalculates the visible balance path and reruns the existing unique mapper.
- Does not rerun signal generation or dynamic lot sizing from a changed signal stream.

## Key Numbers

- Removed rows: `8`.
- Filtered Python-MT5 rows: `90`.
- Current direct gap: `+2389.732270`.
- First-order direct gap: `+2018.655810`.
- Filtered mapping rerun direct gap: `+2018.655810`.
- Current signal-set gap: `+1734.837492`.
- Filtered mapping rerun signal-set gap: `+1363.761032`.
- Matched unique: `60 -> 60`.
- Reliable tier matched: `29 -> 29`.
- Python unmatched: `38 -> 30`.
- MT5 unmatched: `22 -> 22`.

## Decision

- `direct_gap_improved`: `True`.
- `signal_set_gap_improved`: `True`.
- `unmatched_count_reduced`: `True`.
- `mapping_quality_improved`: `False`.
- `merge_gate_pass`: `False`.
- Decision: `diagnostic_improvement_only`.

The result remains diagnostic. A main signal change still requires a signal-level suppression prototype, not only a filtered trade-list rerun.

## Output Files

- `filtered_dynamic/python_mt5_dynamic_risk_trades.csv`
- `filtered_mapping/unique_match_summary.csv`
- `filtered_duplicate_suppression_removed_rows.csv`
- `stage_state_duplicate_suppression_full_chain_before_after.csv`
- `stage_state_duplicate_suppression_full_chain_decision.csv`
