# Python-MT5 +90/+120 time-axis normalization gate (stage-state baseline)

## Scope

- Baseline: accepted stage-state MT5 full tester ledger.
- Candidate source: prior M15 SLOT1 time-axis bridge view, rechecked against current stage-state ledger anchors.
- This is a diagnostic gate only; it does not change signal generation, Stage execution, dynamic risk, or EA code.

## Decision

- Global +120/date+30 merge gate pass: `False`.
- Stable subset rule proven: `False`.
- `mt5_0068` status: `accounting_only_time_axis_diagnostic`.
- Decision: `do_not_merge_time_axis_rule`.
- Reason: +120/date+30 changes Layer3 outcomes, but it is not data-available for all gap candidates and no stage-state full-chain shared/only/fund-curve rerun exists.

## Current Stage-State Baseline

| current_mt5_baseline_id                 |   current_mt5_final_balance |   current_mt5_trade_count |   metadatafix_direct_gap_vs_current_mt5 |   stage_state_metadatafix_matched_unique |   stage_state_metadatafix_python_unmatched |   stage_state_metadatafix_mt5_unmatched |   stage_state_metadatafix_signal_set_gap |
|:----------------------------------------|----------------------------:|--------------------------:|----------------------------------------:|-----------------------------------------:|-------------------------------------------:|----------------------------------------:|-----------------------------------------:|
| stage_state_full_2018_20260707_20260716 |                     1649.84 |                        82 |                                 2389.73 |                                       60 |                                         38 |                                      22 |                                  1734.84 |

## Candidate Summary

| metric                                                   |   value |
|:---------------------------------------------------------|--------:|
| stage_state_m15_slot1_candidates_reused_from_bridge_view |   29    |
| bridge_summary_m15_slot1_signals                         |   29    |
| bridge_summary_any_time_axis_gap                         |   16    |
| bridge_summary_current_remaining_m15_slot1_with_gap      |    6    |
| bridge_summary_reclass_changed_cases                     |    6    |
| stage_state_ledger_same_anchor_matches                   |   29    |
| plus90_available_all_candidates                          |   13    |
| plus120_available_all_candidates                         |   15    |
| plus120_available_among_time_axis_gaps                   |    2    |
| plus120_available_among_remaining_bridge_candidates      |    1    |
| current_plus90_layer3_pass_all_candidates                |    8    |
| raw_plus120_layer3_pass_all_candidates                   |   14    |
| date_plus30_layer3_pass_all_candidates                   |   14    |
| plus120_fail_to_pass_flips_all_candidates                |    7    |
| plus120_pass_to_fail_flips_all_candidates                |    1    |
| changed_cases_gap_effect_sum_old_bridge_view             | -403.06 |

## Rechecked Bridge-Changed Cases

| trade_id   | target_time         | dir_norm   | mode_family   |   gap_effect_$ | current_plus90_available_metadatafix   | plus120_available_metadatafix   | stage_state_ledger_has_same_anchor   |   stage_state_ledger_net_profit | current_raw_plus90_layer3_pass   | raw_plus120_layer3_pass   | date_plus30_layer3_pass   | plus120_flips_current_layer3_fail_to_pass   |
|:-----------|:--------------------|:-----------|:--------------|---------------:|:---------------------------------------|:--------------------------------|:-------------------------------------|--------------------------------:|:---------------------------------|:--------------------------|:--------------------------|:--------------------------------------------|
| mt5_0068   | 2026-02-03 01:00:00 | BUY        | pre_cross     |        -230.63 | False                                  | True                            | True                                 |                          230.63 | False                            | True                      | True                      | True                                        |
| mt5_0005   | 2020-03-13 17:30:00 | SELL       | post_n        |        -161.09 | False                                  | False                           | True                                 |                          161.09 | True                             | True                      | True                      | False                                       |
| mt5_0019   | 2020-08-04 19:00:00 | BUY        | post_n        |        -128.85 | False                                  | False                           | True                                 |                          128.85 | True                             | True                      | True                      | False                                       |
| mt5_0070   | 2026-03-23 17:30:00 | BUY        | post_n        |          70.14 | False                                  | False                           | True                                 |                          -70.14 | False                            | True                      | True                      | True                                        |
| mt5_0021   | 2021-01-11 16:00:00 | SELL       | post_n        |          29.01 | False                                  | False                           | True                                 |                          -29.01 | True                             | False                     | False                     | False                                       |
| mt5_0036   | 2024-03-07 16:30:00 | SELL       | pre_cross     |          18.36 | False                                  | False                           | True                                 |                          -24.47 | False                            | False                     | False                     | False                                       |

## mt5_0068 Prior Boundary Decision

| item     | current_plus90_layer3_pass   |   current_plus90_bias5 |   current_plus90_threshold | plus120_layer3_pass   |   plus120_bias5 |   plus120_threshold | plus90_m30_exists   | plus90_m15_exists   | plus120_m30_exists   | plus120_m15_exists   |   ledger_entry |   ledger_stop | decision                                    | reason                                                                                                        | next_step                                                                                                                                     |
|:---------|:-----------------------------|-----------------------:|---------------------------:|:----------------------|----------------:|--------------------:|:--------------------|:--------------------|:---------------------|:---------------------|---------------:|--------------:|:--------------------------------------------|:--------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------|
| mt5_0068 | False                        |               0.712056 |                   0.916843 | True                  |         1.05559 |            0.916843 | False               | False               | True                 | True                 |        4718.61 |       4683.85 | do_not_include_in_current_plus90_full_chain | Current +90 M15 SLOT1 Layer3 fails; +120 can pass but that is a time-axis semantics change, not a Layer3 fix. | Run a Python-MT5 +90/+120 time-axis normalization gate before any merge involving mt5_0068; P0 subset can only use mt5_0005/mt5_0019 for now. |

## Interpretation

- `+120` and `date+30min` are equivalent for the raw-anchor candidates where `shifted_anchor = raw_anchor + 90min`, but this equivalence is not enough for a merge.
- Some candidates improve Layer3 under `+120`, while some currently passing `+90` candidates can fail under `+120`; therefore it is not a safe global replacement.
- The old bridge changed cases remain useful as time-axis diagnostics, but after the stage-state baseline reset their old trade IDs and unmatched status must not be copied into current funding tables without a full-chain rerun.
- The current action is to keep the time-axis rule read-only and continue with stage-state signal-set residual triage, or explicitly run a separate full-chain prototype before any merge.

## Output Files

- `time_axis_candidate_recheck_stage_state.csv`
- `time_axis_layer3_eval_matrix_stage_state.csv`
- `time_axis_changed_case_review_stage_state.csv`
- `time_axis_normalization_summary_stage_state.csv`
- `time_axis_normalization_gate_decision_stage_state.csv`
- `mt5_0068_prior_boundary_layer3_compact.csv`
