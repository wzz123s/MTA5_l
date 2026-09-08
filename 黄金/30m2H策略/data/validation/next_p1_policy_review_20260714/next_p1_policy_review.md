# Next P1 Policy Review 20260714

## Summary

| item                     | status                                            | decision                                                     | next_step                                                                                                                                                                           |
| ------------------------ | ------------------------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| mt5_0068                 | time_axis_gap_plus_mt5_runtime_slot1_entry        | fix_python_mt5_time_axis_or_slot1_bridge_before_signal_logic | Do not patch EA or Layer3. Add a Python-MT5 diagnostic bridge for M15 SLOT1 signals whose shifted anchor falls in a missing processed M30/M15 bar, then rerun mt5_0068.             |
| python_mt5_0061_mt5_0045 | selected_policy_nonreliable_trigger_relaxed_match | exclude_from_runtime_pnl_adjustment_keep_for_accounting_only | Do not use this pair to prove a Stage3 runtime bug. Keep it in accounting diff, or move it to signal-set drift, until tick/journal evidence validates the relaxed M15-vs-M30 match. |

## mt5_0068 StopSpec / Slot1

| item     | mt5_shifted_anchor  | mt5_raw_anchor      | mt5_log_time        | ledger_signal_entry | ledger_signal_stop | ledger_stop_pts_spec | processed_m30_has_shifted_anchor | processed_m30_prev  | processed_m30_next  | python_nearest_raw_time | python_nearest_raw_sd | python_nearest_raw_spec_reason | decision                                                     |
| -------- | ------------------- | ------------------- | ------------------- | ------------------- | ------------------ | -------------------- | -------------------------------- | ------------------- | ------------------- | ----------------------- | --------------------- | ------------------------------ | ------------------------------------------------------------ |
| mt5_0068 | 2026-02-03 01:00:00 | 2026-02-02 23:30:00 | 2026-02-02 23:15:00 | 4718.614            | 4683.84825         | 34.7657              | False                            | 2026-02-02 23:30:00 | 2026-02-03 01:30:00 | 2026-02-03 01:30:00     | 72.99674243706613     | too_wide                       | fix_python_mt5_time_axis_or_slot1_bridge_before_signal_logic |

## python_mt5_0061 Mapping Policy

| item                     | policy                            | effective_match_tier      | effective_is_reliable | trigger_same | py_trigger_family | mt5_trigger_family | abs_time_diff_minutes | profit_diff | decision                                                     |
| ------------------------ | --------------------------------- | ------------------------- | --------------------- | ------------ | ----------------- | ------------------ | --------------------- | ----------- | ------------------------------------------------------------ |
| python_mt5_0061_mt5_0045 | bidirectional_m30_m15_90_profit20 | nearby_60_trigger_relaxed | False                 | False        | M15 SLOT1         | M30 CLOSE          | 30.0                  | -55.8098    | exclude_from_runtime_pnl_adjustment_keep_for_accounting_only |

## Decision

- Keep the EA price-side repair gate closed.
- Treat `mt5_0068` as a Python-MT5 time-axis / M15 SLOT1 bridge issue before changing signal math.
- Treat `python_mt5_0061 / mt5_0045` as a non-reliable relaxed mapping for accounting only until direct EA evidence exists.
