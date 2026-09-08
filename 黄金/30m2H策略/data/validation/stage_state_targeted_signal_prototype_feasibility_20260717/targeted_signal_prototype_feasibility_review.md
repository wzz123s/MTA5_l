# Stage-State Targeted Signal Prototype Feasibility Audit

## Scope

- Reviews only the 4 targets from targeted raw signal replay.
- Ranks prototype surfaces by evidence and blast radius.
- Does not change Python signals, EA behavior, mapping, dynamic lots, or fund curves.

## Decision

- Reviewed targets: `4`.
- Reviewed abs gap: `349.200000`.
- Selected next prototype: `prototype_layer3_m15_slot1_postn_same_family_rescue`.
- Selected target: `mt5_0076`.
- Selected target abs gap: `104.700000` (29.98% of reviewed abs gap).
- Selected historical blast radius rows: `29`.
- `main_signal_change_gate_open`: `False`.
- `ea_behavior_gate_open`: `False`.
- `mapping_change_gate_open`: `False`.
- `merge_gate_pass`: `False`.

## Candidate Rule Ranking

|   prototype_rank | candidate_rule                            | targets   |   target_abs_gap_sum |   historical_blast_radius_rows | blast_risk_bucket   | prototype_decision                                |
|-----------------:|:------------------------------------------|:----------|---------------------:|-------------------------------:|:--------------------|:--------------------------------------------------|
|                1 | layer3_m15_slot1_postn_same_family_rescue | mt5_0076  |               104.7  |                             29 | medium              | select_first_non_destructive_full_chain_prototype |
|                2 | preserve_m30_parent_before_slot1_replace  | mt5_0044  |                80.96 |                            126 | high                | defer_high_blast_radius                           |
|                3 | audit_m15_slot1_postn_raw_absent          | mt5_0067  |                88.35 |                             10 | unknown             | source_audit_before_prototype                     |
|                4 | audit_m30_close_postn_raw_absent          | mt5_0026  |                75.19 |                              1 | unknown             | source_audit_before_prototype                     |

## Target Feasibility

| trade_id   | raw_chain_loss_point                          | candidate_rule                            |   abs_gap_effect_$ |   historical_blast_radius_rows | prototype_decision                                |
|:-----------|:----------------------------------------------|:------------------------------------------|-------------------:|-------------------------------:|:--------------------------------------------------|
| mt5_0076   | layer3_displaced_by_nearby_opposite_selection | layer3_m15_slot1_postn_same_family_rescue |             104.7  |                             29 | select_first_non_destructive_full_chain_prototype |
| mt5_0067   | raw_absent_nearby_opposite_selected           | audit_m15_slot1_postn_raw_absent          |              88.35 |                             10 | source_audit_before_prototype                     |
| mt5_0044   | layer12_trigger_family_drift_after_raw_parent | preserve_m30_parent_before_slot1_replace  |              80.96 |                            126 | defer_high_blast_radius                           |
| mt5_0026   | raw_absent_for_mt5_signal                     | audit_m30_close_postn_raw_absent          |              75.19 |                              1 | source_audit_before_prototype                     |

## Blast-Radius Checks

- Layer3 M15 SLOT1 post_n displacement rows: `29`.
- M30 parent transformed to M15 SLOT1 rows: `126`.
- MT5 unique rows without Python raw equivalent within 60 minutes: `12`.

## Interpretation

- The selected Layer3 prototype is the smallest data-backed candidate because Python already has exact raw and Layer1/2 evidence for `mt5_0076`.
- The M30 parent-preserve idea explains `mt5_0044`, but its current blast radius is high and should be narrowed before a full-chain test.
- The raw-absent cases (`mt5_0067`, `mt5_0026`) are not safe signal prototypes yet because Python has no raw row to mutate at the target time.

## Output Files

- `targeted_signal_prototype_feasibility_case_review.csv`
- `targeted_signal_prototype_candidate_summary.csv`
- `targeted_signal_prototype_blast_radius_details.csv`
- `targeted_signal_prototype_decision.csv`
