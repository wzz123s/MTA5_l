# M15 SLOT1 Time-Axis Bridge Prototype 20260714

## Summary

| metric                               | value |
| ------------------------------------ | ----- |
| m15_slot1_signals                    | 29    |
| m30_shifted_anchor_gap               | 3     |
| m15_log_plus90_gap                   | 16    |
| any_time_axis_gap                    | 16    |
| current_remaining_m15_slot1_with_gap | 6     |
| remaining_reclass_changed_cases      | 6     |
| mt5_0068_reclassified                | 1     |

## Reclassified Remaining Cases

| trade_id | target_time         | dir_norm | mode_family | cause_bucket                         | bridge_cause_bucket        | gap_effect_$ | bridge_decision                   |
| -------- | ------------------- | -------- | ----------- | ------------------------------------ | -------------------------- | ------------ | --------------------------------- |
| mt5_0068 | 2026-02-03 01:00:00 | BUY      | pre_cross   | layer3_reject                        | time_axis_bridge_candidate | -230.63      | reclass_cause_only_no_fund_change |
| mt5_0005 | 2020-03-13 17:30:00 | SELL     | post_n      | stage_execution_diff_or_family_drift | time_axis_bridge_candidate | -161.09      | reclass_cause_only_no_fund_change |
| mt5_0019 | 2020-08-04 19:00:00 | BUY      | post_n      | trigger_family_drift                 | time_axis_bridge_candidate | -128.85      | reclass_cause_only_no_fund_change |
| mt5_0070 | 2026-03-23 17:30:00 | BUY      | post_n      | layer3_reject                        | time_axis_bridge_candidate | 70.14        | reclass_cause_only_no_fund_change |
| mt5_0021 | 2021-01-11 16:00:00 | SELL     | post_n      | missing_raw_parent                   | time_axis_bridge_candidate | 29.01        | reclass_cause_only_no_fund_change |
| mt5_0036 | 2024-03-07 16:30:00 | SELL     | pre_cross   | missing_raw_parent                   | time_axis_bridge_candidate | 18.36        | reclass_cause_only_no_fund_change |

## mt5_0068 Evidence

| remaining_trade_id | shifted_anchor      | raw_anchor          | log_time            | log_time_plus90     | ledger_signal_entry | ledger_signal_stop | ledger_stop_pts_spec | processed_m30_has_shifted_anchor | processed_m30_prev  | processed_m30_next  | processed_m15_has_log_plus90 | processed_m15_prev  | processed_m15_next  | nearest_raw_any_mode_time | nearest_raw_any_mode_mode | nearest_raw_any_mode_sd | nearest_raw_any_mode_spec_reason | nearest_raw_time    | nearest_raw_mode | nearest_raw_sd     | nearest_raw_spec_reason | bridge_class               |
| ------------------ | ------------------- | ------------------- | ------------------- | ------------------- | ------------------- | ------------------ | -------------------- | -------------------------------- | ------------------- | ------------------- | ---------------------------- | ------------------- | ------------------- | ------------------------- | ------------------------- | ----------------------- | -------------------------------- | ------------------- | ---------------- | ------------------ | ----------------------- | -------------------------- |
| mt5_0068           | 2026-02-03 01:00:00 | 2026-02-02 23:30:00 | 2026-02-02 23:15:00 | 2026-02-03 00:45:00 | 4718.614            | 4683.84825         | 34.765699999999995   | False                            | 2026-02-02 23:30:00 | 2026-02-03 01:30:00 | False                        | 2026-02-02 23:45:00 | 2026-02-03 01:15:00 | 2026-02-03 01:30:00       | cross                     | 72.99674243706613       | too_wide                         | 2026-01-30 01:30:00 | pre_cross        | 50.465830000000096 | too_wide                | time_axis_bridge_candidate |

## Decision

- This prototype changes classification only; it does not change signals, trades, or the fund curve.
- MT5 M15 SLOT1 samples with shifted anchors inside processed-data gaps should not be judged by the nearest later Python raw candidate.
- Keep the EA price-side repair gate closed.
