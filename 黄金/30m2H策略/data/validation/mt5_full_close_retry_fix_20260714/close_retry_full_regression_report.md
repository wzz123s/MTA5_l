# ClosePos Retry Full Regression 20260714

## Scope

- Old snapshot: `mt5_ledger_deinitfix_full_20260713_v1`
- New snapshot: `mt5_full_close_retry_fix_20260714`
- Key: `signal_anchor_time + dir + stage`

## Summary

| snapshot                                  |   ledger_rows |   unique_signal_anchors |   ledger_net_profit |   deal_out_rows |   deal_out_net_profit |
|:------------------------------------------|--------------:|------------------------:|--------------------:|----------------:|----------------------:|
| old_mt5_ledger_deinitfix_full_20260713_v1 |           234 |                      78 |             3440.37 |             234 |               3440.37 |
| new_mt5_full_close_retry_fix_20260714     |           234 |                      78 |             3311.35 |             234 |               3311.35 |

- Net profit delta: `-129.02`.
- Changed rows: `10`.

## Changed Rows

| signal_anchor_time   | dir   |   stage | _merge   |   ticket_old |   position_id_old |   lots_old |   fill_price_old |   actual_stop_old | local_exit_reason_old   | deal_reason_old   | exit_time_old       |   exit_price_old |   net_profit_old |   ticket_new |   position_id_new |   lots_new |   fill_price_new |   actual_stop_new | local_exit_reason_new   | deal_reason_new   | exit_time_new       |   exit_price_new |   net_profit_new |   net_diff |
|:---------------------|:------|--------:|:---------|-------------:|------------------:|-----------:|-----------------:|------------------:|:------------------------|:------------------|:--------------------|-----------------:|-----------------:|-------------:|------------------:|-----------:|-----------------:|------------------:|:------------------------|:------------------|:--------------------|-----------------:|-----------------:|-----------:|
| 2020.03.20 02:00     | BUY   |       3 | both     |           57 |                57 |       0.01 |          1482.25 |           1474.17 | stage3_cross_exit       | EXPERT            | 2020.03.25 10:00:05 |          1622.28 |           138.59 |           57 |                57 |       0.01 |          1482.25 |           1474.17 | stage3_cross_exit       | EXPERT            | 2020.03.22 22:05:00 |          1503.1  |            20.37 |    -118.22 |
| 2024.03.07 15:00     | SELL  |       3 | both     |          213 |               213 |       0.02 |          2148.6  |           2154.7  | deal_exit               | SL                | 2024.03.07 14:51:40 |          2154.72 |           -12.23 |          213 |               213 |       0.01 |          2148.6  |           2154.7  | deal_exit               | SL                | 2024.03.07 14:51:40 |          2154.72 |            -6.12 |       6.11 |
| 2024.04.08 12:30     | SELL  |       3 | both     |          231 |               231 |       0.02 |          2327.53 |           2333.2  | deal_exit               | SL                | 2024.04.08 13:03:30 |          2333.2  |           -11.33 |          231 |               231 |       0.01 |          2327.53 |           2333.2  | deal_exit               | SL                | 2024.04.08 13:03:30 |          2333.2  |            -5.67 |       5.66 |
| 2025.10.14 18:30     | BUY   |       3 | both     |          315 |               315 |       0.02 |          4148.4  |           4134.07 | deal_exit               | SL                | 2025.10.21 14:29:38 |          4134.06 |           -35.39 |          315 |               315 |       0.01 |          4148.4  |           4134.07 | deal_exit               | SL                | 2025.10.21 14:29:38 |          4134.06 |           -17.7  |      17.69 |
| 2025.10.15 12:30     | SELL  |       3 | both     |          320 |               320 |       0.04 |          4180.52 |           4187.34 | deal_exit               | SL                | 2025.10.15 12:35:27 |          4187.35 |           -27.31 |          320 |               320 |       0.03 |          4180.52 |           4187.34 | deal_exit               | SL                | 2025.10.15 12:35:27 |          4187.35 |           -20.49 |       6.82 |
| 2025.10.17 13:00     | SELL  |       3 | both     |          332 |               332 |       0.02 |          4314.31 |           4327.96 | stage3_cross_exit       | EXPERT            | 2025.10.20 05:22:30 |          4252.64 |           123.34 |          332 |               332 |       0.01 |          4314.31 |           4327.96 | stage3_cross_exit       | EXPERT            | 2025.10.20 05:22:30 |          4252.64 |            61.67 |     -61.67 |
| 2026.01.26 19:00     | SELL  |       3 | both     |          363 |               363 |       0.02 |          5064.37 |           5079.19 | deal_exit               | SL                | 2026.01.26 18:50:19 |          5079.2  |           -29.66 |          363 |               363 |       0.01 |          5064.37 |           5079.19 | deal_exit               | SL                | 2026.01.26 18:50:19 |          5079.2  |           -14.83 |      14.83 |
| 2026.01.26 20:30     | SELL  |       1 | both     |          367 |               367 |       0.01 |          5049.98 |           5069.66 | stage1_tp               | SL                | 2026.01.27 01:14:45 |          5069.66 |           -19.67 |          367 |               367 |       0.01 |          5049.98 |           5069.66 | deal_exit               | SL                | 2026.01.27 01:14:45 |          5069.66 |           -19.67 |       0    |
| 2026.03.24 08:30     | BUY   |       3 | both     |          435 |               435 |       0.02 |          4396.75 |           4381.49 | deal_exit               | SL                | 2026.03.24 11:01:42 |          4381.47 |           -30.57 |          435 |               435 |       0.01 |          4396.75 |           4381.49 | deal_exit               | SL                | 2026.03.24 11:01:42 |          4381.47 |           -15.28 |      15.29 |
| 2026.06.08 11:30     | BUY   |       3 | both     |          447 |               447 |       0.05 |          4318.55 |           4312.25 | stage3_cross_exit       | EXPERT            | 2026.06.08 12:32:40 |          4334.08 |            77.68 |          447 |               447 |       0.04 |          4318.55 |           4312.25 | stage3_cross_exit       | EXPERT            | 2026.06.08 12:32:40 |          4334.08 |            62.15 |     -15.53 |

## Reason Diff

|   stage | local_exit_reason   | deal_reason   |   old_rows |   new_rows |   row_diff |
|--------:|:--------------------|:--------------|-----------:|-----------:|-----------:|
|       1 | deal_exit           | SL            |         43 |         44 |          1 |
|       1 | deinit_history      | CLIENT        |          1 |          1 |          0 |
|       1 | position_gone       | SL            |          1 |          1 |          0 |
|       1 | stage1_tp           | EXPERT        |         32 |         32 |          0 |
|       1 | stage1_tp           | SL            |          1 |          0 |         -1 |
|       2 | deal_exit           | SL            |         66 |         66 |          0 |
|       2 | position_gone       | SL            |          2 |          2 |          0 |
|       2 | stage2_forced       | EXPERT        |         10 |         10 |          0 |
|       3 | deal_exit           | SL            |         47 |         47 |          0 |
|       3 | position_gone       | SL            |          1 |          1 |          0 |
|       3 | stage3_cross_exit   | EXPERT        |         30 |         30 |          0 |

## Interpretation

- The new full ledger remains internally closed: ledger OUT net equals raw deal OUT net.
- Signal count and stage row count are unchanged: `78` anchors and `234` stage rows.
- The main behavioral change is the `2020.03.20 02:00` BUY Stage3 row: after a market-closed close failure, the fixed EA keeps Stage3 state and retries successfully on `2020.03.22 22:05:00` instead of losing state and leaving the position until `2020.03.25 10:00:05`.
- Later differences are mostly dynamic-lot cascade effects caused by the earlier balance path change.
- The `2026.01.26 20:30` Stage1 row now reports `deal_exit + SL` instead of the stale `stage1_tp + SL` intent, with no PnL change for that row.
