# EA Stage Price-Side Smoke Review 20260714

## Scope

- Snapshots reviewed:
  - `20260126_close_retry_fix`
  - `20250422_close_retry_fix`
  - `20260324_close_retry_fix`
- Source CSVs: `30m2H_strategy_trade_ledger.csv` and `30m2H_strategy_stage_price_diag.csv`.

## Summary

| snapshot                 |   ledger_rows |   unique_signal_anchors |   ledger_net_profit |   diag_rows |   sell_diag_rows |   sell_action_mismatch_rows |   negative_new_trigger_rows |   stage2_trail_on_events |   stage1_tp_expert_rows |   stage3_expert_rows |   stage3_deinit_client_rows |
|:-------------------------|--------------:|------------------------:|--------------------:|------------:|-----------------:|----------------------------:|----------------------------:|-------------------------:|------------------------:|---------------------:|----------------------------:|
| 20260126_close_retry_fix |             9 |                       3 |             -149.23 |        8189 |             2365 |                           4 |                           0 |                        1 |                       0 |                    0 |                           0 |
| 20250422_close_retry_fix |             6 |                       2 |              176.78 |        6543 |             6543 |                           0 |                           0 |                        1 |                       1 |                    0 |                           1 |
| 20260324_close_retry_fix |            15 |                       5 |              -39.29 |        4971 |             3162 |                           1 |                           0 |                        3 |                       3 |                    1 |                           0 |

## Conclusions

- Across the three smoke windows there are `12070` SELL diagnostic rows and `5` legacy/profit-side action mismatch rows.
- New Stage1 TP / Stage2 force / Stage2 trail-on triggers with negative close-side profit: `0`.
- All observed Stage2 trail-on events are profit-positive under both legacy and close-side calculations.
- The remaining price-side mismatches are threshold-edge cases, not broad false-profit triggers.
- The `2026-01-26` sample remains dominated by market-session behavior: close/modify attempts occur during market closed, so the ClosePos retry/state-retention fix is required for correct state and ledger reason.
- The `2025-04-22` smoke contains a Stage3 `deinit_history + CLIENT` row, so tester-window/deinit handling must be considered before treating it as a strategy exit mismatch.

## Stage2 Trail-On Events

| snapshot                 | time                | signal_anchor_time   | dir   |   stage |   ticket |   entry |   orig_sl |   current_sl |     bid |     ask |   legacy_abs_rr |   close_profit_rr | legacy_action_text   | profit_side_action_text   |
|:-------------------------|:--------------------|:---------------------|:------|--------:|---------:|--------:|----------:|-------------:|--------:|--------:|----------------:|------------------:|:---------------------|:--------------------------|
| 20260126_close_retry_fix | 2026.01.26 21:21:30 | 2026.01.26 20:30     | SELL  |       2 |        9 | 5049.98 |   5069.66 |      5069.66 | 5020.08 | 5020.24 |         1.51961 |           1.51147 | stage2_trail_on      | stage2_trail_on           |
| 20250422_close_retry_fix | 2025.04.22 19:32:32 | 2025.04.22 14:00     | SELL  |       2 |        9 | 3418.53 |   3450.8  |      3450.8  | 3369.89 | 3370.05 |         1.50706 |           1.50213 | stage2_trail_on      | stage2_trail_on           |
| 20260324_close_retry_fix | 2026.03.24 01:14:40 | 2026.03.24 00:30     | SELL  |       2 |        9 | 4378.01 |   4406.94 |      4406.94 | 4331.79 | 4332.15 |         1.59829 |           1.5857  | stage2_trail_on      | stage2_trail_on           |
| 20260324_close_retry_fix | 2026.03.24 04:19:30 | 2026.03.24 03:00     | SELL  |       2 |       14 | 4366.75 |   4387.36 |      4387.36 | 4335.06 | 4335.42 |         1.53762 |           1.51996 | stage2_trail_on      | stage2_trail_on           |
| 20260324_close_retry_fix | 2026.03.24 09:40:30 | 2026.03.24 08:30     | BUY   |       2 |       21 | 4396.75 |   4381.49 |      4381.49 | 4420.18 | 4420.54 |         1.53456 |           1.53456 | stage2_trail_on      | stage2_trail_on           |

## Action Mismatches

| snapshot                 | time                | signal_anchor_time   | dir   |   stage |   ticket |   entry |     bid |     ask |   legacy_abs_rr |   close_profit_rr | legacy_action_text   | profit_side_action_text   |
|:-------------------------|:--------------------|:---------------------|:------|--------:|---------:|--------:|--------:|--------:|----------------:|------------------:|:---------------------|:--------------------------|
| 20260126_close_retry_fix | 2026.01.26 21:32:00 | 2026.01.26 20:30     | SELL  |       1 |        8 | 5049.98 | 5010.53 | 5010.69 |         2.0052  |           1.99707 | stage1_tp            | hold                      |
| 20260126_close_retry_fix | 2026.01.26 21:32:10 | 2026.01.26 20:30     | SELL  |       1 |        8 | 5049.98 | 5010.54 | 5010.7  |         2.00444 |           1.99631 | stage1_tp            | hold                      |
| 20260126_close_retry_fix | 2026.01.26 21:41:00 | 2026.01.26 20:30     | SELL  |       1 |        8 | 5049.98 | 5010.53 | 5010.69 |         2.0053  |           1.99717 | stage1_tp            | hold                      |
| 20260126_close_retry_fix | 2026.01.26 21:41:10 | 2026.01.26 20:30     | SELL  |       1 |        8 | 5049.98 | 5010.5  | 5010.66 |         2.00662 |           1.99849 | stage1_tp            | hold                      |
| 20260324_close_retry_fix | 2026.03.24 01:45:10 | 2026.03.24 00:30     | SELL  |       1 |        8 | 4378.01 | 4320.05 | 4320.41 |         2.00417 |           1.99158 | stage1_tp            | hold                      |
