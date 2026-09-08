# P1 Signal Drift Topcase Review 20260714

## Key Finding

- `map_python_mt5_ledger_trades.py` previously normalized `B/BUY/1` as BUY but missed Python `L`.
- After adding `L/LONG` to BUY normalization and rerunning close-retry mapping, Python-MT5 matched trades increased from `34` to `57`, and MT5-unmatched fell from `44` to `21`.
- The previous largest MT5-only cases `mt5_0031` and `mt5_0049` are no longer signal-set drift; both are now matched Stage-exit/PnL cases.

## Watchlist Status

| watch_id        | case_status                           | py_trade_id     | mt5_trade_id | target_time         | trigger_family | mode_family | match_tier        | py_profit | mt5_profit | runtime_adjusted_profit | gap_or_residual | next_step                                                                 |
| --------------- | ------------------------------------- | --------------- | ------------ | ------------------- | -------------- | ----------- | ----------------- | --------- | ---------- | ----------------------- | --------------- | ------------------------------------------------------------------------- |
| mt5_0031        | resolved_by_buy_direction_mapping_fix | python_mt5_0039 | mt5_0031     | 2022-11-08 18:00:00 | M15 SLOT1      | post_n      | exact_align90_all | 4.203474  | 1842.78    | 1842.78                 | 0.0             | No longer a signal-set drift case; keep under matched runtime PnL review. |
| mt5_0049        | resolved_by_buy_direction_mapping_fix | python_mt5_0067 | mt5_0049     | 2025-09-05 16:00:00 | M15 SLOT1      | post_n      | nearby_7d_all     | 29.66803  | 541.15     | 541.15                  | 0.0             | No longer a signal-set drift case; keep under matched runtime PnL review. |
| mt5_0068        | remaining_signal_drift                |                 | mt5_0068     | 2026-02-03 01:00:00 | M15 SLOT1      | pre_cross   |                   |           | 230.63     |                         | -230.63         | review_python_layer3_acceptance_mismatch                                  |
| python_mt5_0079 | remaining_signal_drift                | python_mt5_0079 |              | 2025-10-21 10:00:00 | M15 SLOT1      | post_n      |                   | 201.85136 |            | 201.85136               | 201.85136       | resolve_unique_match_conflict_after_runtime                               |
| python_mt5_0073 | remaining_signal_drift                | python_mt5_0073 |              | 2025-10-17 11:00:00 | M15 SLOT1      | pre_cross   |                   | 189.6211  |            | 189.6211                | 189.6211        | resolve_unique_match_conflict_after_runtime                               |
| python_mt5_0075 | remaining_signal_drift                | python_mt5_0075 |              | 2025-10-17 15:00:00 | M15 SLOT1      | post_n      |                   | 150.91695 |            | 150.91695               | 150.91695       | resolve_unique_match_conflict_after_runtime                               |
| python_mt5_0092 | matched_after_policy_refresh          | python_mt5_0092 | mt5_0075     | 2026-06-08 13:00:00 | M15 SLOT1      | pre_cross   | exact_align90_all | 145.2975  | 155.12     | 145.2975                | -9.8225         | No longer Python-unmatched under selected policy.                         |

## Current Top Work Items

| case_type        | action_priority | next_step                                     | side             | case_id         | target_time         | trigger_family | mode_family | cause_bucket                         | impact     | abs_impact |
| ---------------- | --------------- | --------------------------------------------- | ---------------- | --------------- | ------------------- | -------------- | ----------- | ------------------------------------ | ---------- | ---------- |
| signal_drift     | P1              | review_python_layer3_acceptance_mismatch      | mt5_unmatched    | mt5_0068        | 2026-02-03 01:00:00 | M15 SLOT1      | pre_cross   | layer3_reject                        | -230.63    | 230.63     |
| signal_drift     | P1              | resolve_unique_match_conflict_after_runtime   | python_unmatched | python_mt5_0079 | 2025-10-21 10:00:00 | M15 SLOT1      | post_n      | unique_match_conflict                | 201.85136  | 201.85136  |
| signal_drift     | P1              | resolve_unique_match_conflict_after_runtime   | python_unmatched | python_mt5_0073 | 2025-10-17 11:00:00 | M15 SLOT1      | pre_cross   | unique_match_conflict                | 189.6211   | 189.6211   |
| signal_drift     | P1              | review_python_layer3_acceptance_mismatch      | mt5_unmatched    | mt5_0074        | 2026-04-02 03:00:00 | M15 SLOT1      | pre_cross   | layer3_reject                        | -171.9     | 171.9      |
| signal_drift     | P1              | split_family_drift_vs_execution_after_runtime | mt5_unmatched    | mt5_0005        | 2020-03-13 17:30:00 | M15 SLOT1      | post_n      | stage_execution_diff_or_family_drift | -161.09    | 161.09     |
| signal_drift     | P1              | resolve_unique_match_conflict_after_runtime   | python_unmatched | python_mt5_0075 | 2025-10-17 15:00:00 | M15 SLOT1      | post_n      | unique_match_conflict                | 150.91695  | 150.91695  |
| signal_drift     | P1              | review_python_extra_signal_lifecycle          | python_unmatched | python_mt5_0091 | 2026-05-28 15:30:00 | M15 SLOT1      | cross       | python_signal_not_in_mt5_ledger      | 135.186066 | 135.186066 |
| signal_drift     | P1              | review_trigger_family_equivalence_or_anchor   | mt5_unmatched    | mt5_0019        | 2020-08-04 19:00:00 | M15 SLOT1      | post_n      | trigger_family_drift                 | -128.85    | 128.85     |
| signal_drift     | P1              | split_family_drift_vs_execution_after_runtime | mt5_unmatched    | mt5_0048        | 2025-09-02 17:30:00 | M30 CLOSE      | post_n      | stage_execution_diff_or_family_drift | -123.92    | 123.92     |
| signal_drift     | P1              | review_family_or_time_drift                   | python_unmatched | python_mt5_0065 | 2025-04-22 16:30:00 | M15 SLOT1      | post_n      | mt5_family_or_time_drift             | 115.714136 | 115.714136 |
| signal_drift     | P1              | review_python_extra_signal_lifecycle          | python_unmatched | python_mt5_0090 | 2026-05-28 14:30:00 | M15 SLOT1      | pre_cross   | python_signal_not_in_mt5_ledger      | 114.292288 | 114.292288 |
| signal_drift     | P1              | review_python_extra_signal_lifecycle          | python_unmatched | python_mt5_0068 | 2025-09-30 09:30:00 | M15 SLOT1      | pre_cross   | python_signal_not_in_mt5_ledger      | 97.93775   | 97.93775   |
| signal_drift     | P1              | review_python_layer3_acceptance_mismatch      | mt5_unmatched    | mt5_0065        | 2026-02-02 16:30:00 | M15 SLOT1      | post_n      | layer3_reject                        | 88.35      | 88.35      |
| signal_drift     | P1              | review_trigger_family_equivalence_or_anchor   | mt5_unmatched    | mt5_0043        | 2024-11-13 19:30:00 | M30 CLOSE      | post_n      | trigger_family_drift                 | -80.96     | 80.96      |
| signal_drift     | P1              | review_missing_python_candidate               | mt5_unmatched    | mt5_0026        | 2021-11-10 16:30:00 | M30 CLOSE      | post_n      | missing_python_candidate             | 75.19      | 75.19      |
| matched_residual | P1              | resolve_remaining_stage_exit_blocker          | matched          | python_mt5_0061 | 2025-04-21 02:00:00 | M15 SLOT1      | post_n      | stage_exit_detail_diff               | -55.8098   | 55.8098    |
| matched_residual | P1              | review_stop_distance_or_fill_price            | matched          | python_mt5_0009 | 2020-03-17 04:00:00 | M30 CLOSE      | cross       | stop_distance_diff                   | 15.877926  | 15.877926  |
| matched_residual | P1              | review_exit_reason_runtime_ordering           | matched          | python_mt5_0008 | 2020-03-13 16:00:00 | M30 CLOSE      | cross       | exit_reason_diff                     | -14.81836  | 14.81836   |
| matched_residual | P2              | defer_after_p1_or_split_minor_mixed           | matched          | python_mt5_0029 | 2021-06-18 15:30:00 | M30 CLOSE      | post_n      | minor_or_mixed_diff                  | 16.725488  | 16.725488  |
| matched_residual | P2              | defer_after_p1_or_split_minor_mixed           | matched          | python_mt5_0033 | 2022-03-07 21:30:00 | M30 CLOSE      | post_n      | minor_or_mixed_diff                  | 16.26939   | 16.26939   |

## Next Actions

1. Resolve `python_mt5_0061 / mt5_0045`, the only remaining Stage-exit runtime blocker after the BUY mapping fix.
2. Review `mt5_0068`, the largest remaining MT5-unmatched case, currently classified as `layer3_reject`.
3. Then handle Python-unmatched unique-match conflicts around `2025-10-17` to `2025-10-21`.
4. Keep EA price-side behavior unchanged; the current blocking issues are mapping/runtime evidence and signal-set review items.
