# Stage-state new MT5 baseline decision

## Scope

- This gate decides the MT5 reference baseline only.
- It does not mark Python-MT5 strategy alignment as complete.
- It does not change EA or Python strategy logic.

## Decision

| gate                                  | accept_stage_state_as_current_mt5_baseline   | alignment_merge_gate_pass   | current_mt5_baseline_id                 |   current_mt5_final_balance |   current_mt5_trade_count |   current_mt5_stage_rows |   current_mt5_deinit_rows |   metadatafix_direct_gap_vs_current_mt5 | deprecated_close_retry_allowed_for_future_direct_gap   | next_action                                                          |
|:--------------------------------------|:---------------------------------------------|:----------------------------|:----------------------------------------|----------------------------:|--------------------------:|-------------------------:|--------------------------:|----------------------------------------:|:-------------------------------------------------------|:---------------------------------------------------------------------|
| stage_state_new_mt5_baseline_decision | True                                         | False                       | stage_state_full_2018_20260707_20260716 |                     1649.84 |                        82 |                      246 |                         0 |                                 2389.73 | False                                                  | resume_python_mt5_time_axis_normalization_using_stage_state_baseline |

## Current Baseline Manifest

| baseline_status                | baseline_id                             | ledger_dir                                                                               | configured_test_from   | configured_test_to   | first_trade_anchor   | last_trade_anchor   |   initial_deposit | leverage   |   final_balance |   net_profit |   trade_count_unique_anchors |   stage_rows |   win_count |   win_rate_pct |   any_stage_sl_count |   all_stage_sl_count |   deinit_rows |   ledger_vs_deal_net_gap |   ledger_vs_final_net_gap |
|:-------------------------------|:----------------------------------------|:-----------------------------------------------------------------------------------------|:-----------------------|:---------------------|:---------------------|:--------------------|------------------:|:-----------|----------------:|-------------:|-----------------------------:|-------------:|------------:|---------------:|---------------------:|---------------------:|--------------:|-------------------------:|--------------------------:|
| accepted_current_mt5_reference | stage_state_full_2018_20260707_20260716 | F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\mt5_stage_state_full_2018_20260707_20260716 | 2018-01-01             | 2026-07-07           | 2020-03-06 20:00:00  | 2026-06-30 07:30:00 |               500 | 1:100      |         1649.84 |      1149.84 |                           82 |          246 |          33 |        40.2439 |                   75 |                   40 |             0 |                        0 |                         0 |

## Deprecated vs Accepted Baseline

| item                             | baseline_id                             |   final_balance |   net_profit |   trade_count_unique_anchors |   stage_rows |   deinit_rows | valid_for_future_direct_gap   | reason                                                                                                  |
|:---------------------------------|:----------------------------------------|----------------:|-------------:|-----------------------------:|-------------:|--------------:|:------------------------------|:--------------------------------------------------------------------------------------------------------|
| deprecated_close_retry_reference | mt5_full_close_retry_fix_20260714       |         3811.35 |      3311.35 |                           78 |          234 |             1 | False                         | contains invalid unmanaged deinit/long-hold lifecycle profit                                            |
| accepted_stage_state_reference   | stage_state_full_2018_20260707_20260716 |         1649.84 |      1149.84 |                           82 |          246 |             0 | True                          | multi-slot lifecycle ledger closes to deal/final net and removes invalid long-held profits              |
| delta_new_minus_deprecated       |                                         |        -2161.51 |     -2161.51 |                            4 |           12 |            -1 |                               | target_deinit_stage1=-1739.81; target_20250905_stage3=-381.23; new_anchors=-247.22; shared_other=-167.6 |

## Acceptance Evidence

| evidence                                  | pass   | value                                                    |
|:------------------------------------------|:-------|:---------------------------------------------------------|
| ledger_deal_final_closure                 | True   | ledger/deal/final net gap = 0                            |
| deinit_rows_removed                       | True   | deinit_rows=0                                            |
| mt5_0031_lifecycle_corrected              | True   | mt5_0031 Stage1 closes as stage1_tp / EXPERT             |
| target_20250905_old_profit_invalidated    | True   | old_stage3_likely_unmanaged_after_stage3_state_overwrite |
| new_anchors_explained_by_capacity_release | True   | 4/4                                                      |
| lifecycle_delta_closed                    | True   | total delta -2161.51 is bucketed                         |

## Python-MT5 Gap Rebase

| scenario         |   python_mt5_final_balance |   deprecated_close_retry_mt5_final |   accepted_stage_state_mt5_final |   direct_gap_vs_deprecated_close_retry |   direct_gap_vs_accepted_stage_state |   gap_rebase_delta | future_reference               |
|:-----------------|---------------------------:|-----------------------------------:|---------------------------------:|---------------------------------------:|-------------------------------------:|-------------------:|:-------------------------------|
| metadatafix      |                    4039.57 |                            3811.35 |                          1649.84 |                                228.222 |                              2389.73 |            2161.51 | accepted_stage_state_mt5_final |
| p0_subset_bridge |                    4433.96 |                            3811.35 |                          1649.84 |                                622.614 |                              2784.12 |            2161.51 | accepted_stage_state_mt5_final |

## Interpretation

- Accept `mt5_stage_state_full_2018_20260707_20260716` as the current MT5 reference baseline.
- Do not use `mt5_full_close_retry_fix_20260714` for future direct-gap conclusions; it remains historical evidence only.
- The accepted MT5 baseline is final balance `$1649.84`, unique anchor trades `82`, stage rows `246`, deinit rows `0`.
- Python-MT5 alignment is still not complete: metadatafix direct gap against the accepted MT5 baseline is `+$2389.732270`.
- Future work resumes at the Python-MT5 +90/+120 time-axis normalization gate using this stage-state baseline.

## Output Files

- `stage_state_new_baseline_decision.csv`
- `current_mt5_baseline_manifest.csv`
- `deprecated_vs_accepted_baseline_summary.csv`
- `stage_state_baseline_acceptance_evidence.csv`
- `python_mt5_gap_rebase_after_stage_state.csv`
- `current_mt5_baseline_README.md`
