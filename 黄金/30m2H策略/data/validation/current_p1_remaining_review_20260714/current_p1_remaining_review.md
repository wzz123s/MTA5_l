# Current P1 Remaining Review 20260714

## Summary

| item                     | status                                           | impact                                         | recommended_next_step                                                                                                                                                                             |
| ------------------------ | ------------------------------------------------ | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| python_mt5_0061_mt5_0045 | mapping_policy_risk_plus_unresolved_stage3_cross | -55.809800 matched residual if left unadjusted | First verify whether this relaxed M15-vs-M30 match should drive runtime adjustment; if yes, add EA Stage3 cross diagnostics/tick evidence around the first M30 cross before changing EA behavior. |
| mt5_0068                 | target_window_raw_candidates_all_spec_reject     | -230.63 signal-set gap                         | Review Python StopSpec/M15 SLOT1 rescue rules around 2026-02-03; current evidence points to target-window raw spec rejection rather than a true Layer3-only reject.                               |

## Stage-Exit Blocker

| case_id                | py_trade_id     | mt5_trade_id | match_tier                | trigger_pair           | mode_pair        | first_m30_cross_time | mt5_sl_time         | minutes_cross_before_sl | journal_class              | review_conclusion                                |
| ---------------------- | --------------- | ------------ | ------------------------- | ---------------------- | ---------------- | -------------------- | ------------------- | ----------------------- | -------------------------- | ------------------------------------------------ |
| runtime_stage_case_014 | python_mt5_0061 | mt5_0045     | nearby_60_trigger_relaxed | M15 SLOT1 -> M30 CLOSE | post_n -> post_n | 2025-04-22 15:00:00  | 2025.04.22 22:04:38 | 424.633333              | unresolved_by_journal_scan | mapping_policy_risk_plus_unresolved_stage3_cross |

## Layer3 Reject Review

| mt5_trade_id | target_time         | dir_norm | trigger_family | mode_family | mt5_profit | raw_same_dir_rows_within_180m | raw_spec_pass_rows_within_180m | raw_nearest_time    | raw_nearest_mode | raw_nearest_spec_reason | accepted_same_trigger_mode_within_180m | picked_same_trigger_mode_within_180m | executed_same_trigger_mode_within_180m | review_subcause                              |
| ------------ | ------------------- | -------- | -------------- | ----------- | ---------- | ----------------------------- | ------------------------------ | ------------------- | ---------------- | ----------------------- | -------------------------------------- | ------------------------------------ | -------------------------------------- | -------------------------------------------- |
| mt5_0068     | 2026-02-03 01:00:00 | BUY      | M15 SLOT1      | pre_cross   | 230.63     | 5                             | 0                              | 2026-02-03 01:30:00 | cross            | too_wide                | 0                                      | 0                                    | 0                                      | target_window_raw_candidates_all_spec_reject |

## Raw Candidates Near mt5_0068

| date                | minutes_from_target | dir | mode    | entry             | stop              | sd                 | spec_pass | spec_reason | pnl                |
| ------------------- | ------------------- | --- | ------- | ----------------- | ----------------- | ------------------ | --------- | ----------- | ------------------ |
| 2026-02-03 01:30:00 | 30.0                | L   | cross   | 4755.390333333334 | 4682.393590896268 | 72.99674243706613  | False     | too_wide    | 230.8846666666659  |
| 2026-02-03 02:00:00 | 60.0                | L   | post_n2 | 4819.798          | 4702.71867        | 117.07932999999956 | False     | too_wide    | 166.47699999999986 |
| 2026-02-03 02:30:00 | 90.0                | L   | post_n3 | 4780.421          | 4708.69577        | 71.72523000000001  | False     | too_wide    | 205.85399999999936 |
| 2026-02-03 03:00:00 | 120.0               | L   | post_n4 | 4853.518          | 4719.83594        | 133.6820600000001  | False     | too_wide    | 132.7569999999996  |
| 2026-02-03 03:30:00 | 150.0               | L   | post_n5 | 4841.551          | 4729.19864        | 112.35236000000076 | False     | too_wide    | 144.72399999999925 |

## Decision

- Do not open the EA price-side repair gate from these two cases.
- `python_mt5_0061 / mt5_0045` is a relaxed M15-vs-M30 mapping plus unresolved Stage3 cross-vs-SL chronology issue.
- `mt5_0068` should be reclassified from generic `layer3_reject` to target-window raw StopSpec rejection / missing accepted parent.
