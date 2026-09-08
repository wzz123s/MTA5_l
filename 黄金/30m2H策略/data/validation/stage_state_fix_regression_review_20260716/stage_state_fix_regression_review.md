# EA stage-state tracking fix regression review

## Scope

- Reviews the compiled EA after replacing single-slot stage management with active ledger-slot traversal.
- Smoke outputs are used to prove the `mt5_0031` unmanaged Stage1 bug is fixed.
- Full output is used as a merge gate; it is not accepted only because deinit rows disappeared.

## Summary

| snapshot                   |   ledger_rows |   unique_anchors |   deinit_rows |   ledger_net_sum |   deal_out_rows |   deal_out_net_sum |   ledger_vs_deal_net_gap |   final_balance |   final_net_profit |   ledger_vs_final_net_gap |
|:---------------------------|--------------:|-----------------:|--------------:|-----------------:|----------------:|-------------------:|-------------------------:|----------------:|-------------------:|--------------------------:|
| baseline_close_retry_full  |           234 |               78 |             1 |          3311.35 |             234 |            3311.35 |                        0 |         3811.35 |            3311.35 |                         0 |
| stage_state_smoke_short    |             9 |                3 |             1 |           213.96 |               9 |             213.96 |                        0 |          713.96 |             213.96 |                        -0 |
| stage_state_smoke_extended |            12 |                4 |             0 |           173.54 |              12 |             173.54 |                        0 |          673.54 |             173.54 |                         0 |
| stage_state_full           |           246 |               82 |             0 |          1149.84 |             246 |            1149.84 |                        0 |         1649.84 |            1149.84 |                         0 |

## Target mt5_0031 Before/After

| snapshot             | signal_anchor_time   | signal_src                          |   stage |   ticket |   position_id | open_time           | exit_time           | local_exit_reason   | deal_reason   |   profit |    swap |   net_profit | deal_comment   |
|:---------------------|:---------------------|:------------------------------------|--------:|---------:|--------------:|:--------------------|:--------------------|:--------------------|:--------------|---------:|--------:|-------------:|:---------------|
| baseline_close_retry | 2022.11.08 16:30     | post_n5_m15_slot1_replace_or_rescue |       3 |      184 |           184 | 2022.11.08 16:15:06 | 2022.11.10 03:44:24 | stage3_cross_exit   | EXPERT        |    -4.7  |   -1.92 |        -6.62 | nan            |
| baseline_close_retry | 2022.11.08 16:30     | post_n5_m15_slot1_replace_or_rescue |       2 |      183 |           183 | 2022.11.08 16:15:06 | 2022.11.13 23:06:00 | stage2_forced       | EXPERT        |    49.92 |   -2.88 |        47.04 | nan            |
| baseline_close_retry | 2022.11.08 16:30     | post_n5_m15_slot1_replace_or_rescue |       1 |      182 |           182 | 2022.11.08 16:15:06 | 2026.07.06 23:59:59 | deinit_history      | CLIENT        |  2443.64 | -641.28 |      1802.36 | end of test    |
| stage_state_full     | 2022.11.08 16:30     | post_n5_m15_slot1_replace_or_rescue |       3 |      184 |           184 | 2022.11.08 16:15:06 | 2022.11.10 03:44:24 | stage3_cross_exit   | EXPERT        |    -4.7  |   -1.92 |        -6.62 | nan            |
| stage_state_full     | 2022.11.08 16:30     | post_n5_m15_slot1_replace_or_rescue |       2 |      183 |           183 | 2022.11.08 16:15:06 | 2022.11.11 11:01:38 | deal_exit           | SL            |    42.56 |   -2.4  |        40.16 | sl 1756.309    |
| stage_state_full     | 2022.11.08 16:30     | post_n5_m15_slot1_replace_or_rescue |       1 |      182 |           182 | 2022.11.08 16:15:06 | 2022.11.15 07:40:45 | stage1_tp           | EXPERT        |    65.91 |   -3.36 |        62.55 | nan            |

## Full Regression Largest Negative Deltas

| signal_anchor_time   | trigger_tag   | signal_src                            | dir   |   stage |   old_rows |   old_net |   new_rows |   new_net |   net_delta_new_minus_old |   row_delta_new_minus_old |
|:---------------------|:--------------|:--------------------------------------|:------|--------:|-----------:|----------:|-----------:|----------:|--------------------------:|--------------------------:|
| 2022.11.08 16:30     | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue   | BUY   |       1 |          1 |   1802.36 |          1 |     62.55 |                  -1739.81 |                         0 |
| 2025.09.05 14:30     | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue   | BUY   |       3 |          1 |    429.02 |          1 |     47.79 |                   -381.23 |                         0 |
| 2026.03.24 10:30     | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue   | BUY   |       1 |          0 |      0    |          1 |    -34.9  |                    -34.9  |                         1 |
| 2026.03.24 10:30     | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue   | BUY   |       3 |          0 |      0    |          1 |    -34.9  |                    -34.9  |                         1 |
| 2026.03.24 10:30     | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue   | BUY   |       2 |          0 |      0    |          1 |    -34.9  |                    -34.9  |                         1 |
| 2026.06.30 07:30     | [M30 CLOSE]   | cross                                 | BUY   |       2 |          0 |      0    |          1 |    -30.05 |                    -30.05 |                         1 |
| 2026.06.30 07:30     | [M30 CLOSE]   | cross                                 | BUY   |       3 |          0 |      0    |          1 |    -30.05 |                    -30.05 |                         1 |
| 2026.06.30 07:30     | [M30 CLOSE]   | cross                                 | BUY   |       1 |          0 |      0    |          1 |    -30.05 |                    -30.05 |                         1 |
| 2020.03.13 14:30     | [M30 CLOSE]   | cross                                 | SELL  |       2 |          1 |     69.1  |          1 |     41.81 |                    -27.29 |                         0 |
| 2026.06.08 11:30     | [M15 SLOT1]   | pre_cross_m15_slot1_replace_or_rescue | BUY   |       2 |          1 |     79.15 |          1 |     52.76 |                    -26.39 |                         0 |
| 2026.06.30 06:30     | [M30 CLOSE]   | pre_cross                             | BUY   |       3 |          1 |     35.53 |          1 |     17.77 |                    -17.76 |                         0 |
| 2025.10.20 01:30     | [M30 CLOSE]   | pre_cross                             | BUY   |       3 |          0 |      0    |          1 |    -15.88 |                    -15.88 |                         1 |
| 2025.10.20 01:30     | [M30 CLOSE]   | pre_cross                             | BUY   |       2 |          0 |      0    |          1 |     -7.94 |                     -7.94 |                         1 |
| 2025.10.20 01:30     | [M30 CLOSE]   | pre_cross                             | BUY   |       1 |          0 |      0    |          1 |     -7.94 |                     -7.94 |                         1 |
| 2025.10.07 14:30     | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue   | BUY   |       3 |          1 |    -14.51 |          1 |    -21.77 |                     -7.26 |                         0 |
| 2022.11.08 16:30     | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue   | BUY   |       2 |          1 |     47.04 |          1 |     40.16 |                     -6.88 |                         0 |
| 2022.11.16 10:00     | [M30 CLOSE]   | post_n4                               | BUY   |       1 |          0 |      0    |          1 |     -6.87 |                     -6.87 |                         1 |
| 2022.11.16 10:00     | [M30 CLOSE]   | post_n4                               | BUY   |       3 |          0 |      0    |          1 |     -6.87 |                     -6.87 |                         1 |
| 2022.11.16 10:00     | [M30 CLOSE]   | post_n4                               | BUY   |       2 |          0 |      0    |          1 |     -6.87 |                     -6.87 |                         1 |
| 2024.03.07 15:00     | [M15 SLOT1]   | pre_cross_m15_slot1_replace_or_rescue | SELL  |       3 |          1 |     -6.12 |          1 |    -12.23 |                     -6.11 |                         0 |
| 2024.04.08 12:30     | [M30 CLOSE]   | pre_cross                             | SELL  |       3 |          1 |     -5.67 |          1 |    -11.33 |                     -5.66 |                         0 |
| 2025.10.07 14:30     | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue   | BUY   |       2 |          1 |     -2.42 |          1 |     -4.83 |                     -2.41 |                         0 |
| 2022.11.10 14:00     | [M30 CLOSE]   | post_n2                               | BUY   |       1 |          1 |     47.99 |          1 |     46.59 |                     -1.4  |                         0 |
| 2020.03.16 23:00     | [M30 CLOSE]   | cross                                 | BUY   |       3 |          1 |     -5.56 |          1 |     -5.56 |                      0    |                         0 |
| 2020.03.18 08:00     | [M30 CLOSE]   | post_n4                               | SELL  |       1 |          1 |    -23.92 |          1 |    -23.92 |                      0    |                         0 |

## Full Regression Largest Positive Deltas

| signal_anchor_time   | trigger_tag   | signal_src                            | dir   |   stage |   old_rows |   old_net |   new_rows |   new_net |   net_delta_new_minus_old |   row_delta_new_minus_old |
|:---------------------|:--------------|:--------------------------------------|:------|--------:|-----------:|----------:|-----------:|----------:|--------------------------:|--------------------------:|
| 2025.10.14 18:30     | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue   | BUY   |       3 |          1 |    -17.7  |          1 |    115.58 |                    133.28 |                         0 |
| 2020.03.13 14:30     | [M30 CLOSE]   | cross                                 | SELL  |       3 |          1 |    -10.4  |          1 |     82.41 |                     92.81 |                         0 |
| 2024.04.08 18:00     | [M30 CLOSE]   | cross                                 | BUY   |       3 |          1 |     -8.26 |          1 |     12.87 |                     21.13 |                         0 |
| 2025.12.24 03:00     | [M30 CLOSE]   | pre_cross                             | SELL  |       3 |          1 |    -31.01 |          1 |    -15.51 |                     15.5  |                         0 |
| 2021.06.16 22:30     | [M15 SLOT1]   | post_n6_m15_slot1_replace_or_rescue   | SELL  |       1 |          1 |     53.57 |          1 |     67.13 |                     13.56 |                         0 |
| 2026.06.11 06:00     | [M15 SLOT1]   | pre_cross_m15_slot1_replace_or_rescue | BUY   |       3 |          1 |    -31.59 |          1 |    -23.69 |                      7.9  |                         0 |
| 2020.07.28 06:00     | [M30 CLOSE]   | cross                                 | SELL  |       2 |          1 |     -3.26 |          1 |      3.87 |                      7.13 |                         0 |
| 2021.06.16 22:30     | [M15 SLOT1]   | post_n6_m15_slot1_replace_or_rescue   | SELL  |       2 |          1 |     32.31 |          1 |     38.91 |                      6.6  |                         0 |
| 2025.10.16 06:00     | [M15 SLOT1]   | pre_cross_m15_slot1_replace_or_rescue | SELL  |       3 |          1 |    -25.52 |          1 |    -19.14 |                      6.38 |                         0 |
| 2026.03.24 00:30     | [M30 CLOSE]   | pre_cross                             | SELL  |       2 |          1 |      5.56 |          1 |      9.18 |                      3.62 |                         0 |
| 2020.03.25 08:00     | [M30 CLOSE]   | post_n6                               | SELL  |       1 |          1 |     -7.97 |          1 |     -7.97 |                      0    |                         0 |
| 2020.08.04 17:30     | [M15 SLOT1]   | post_n6_m15_slot1_replace_or_rescue   | BUY   |       3 |          1 |     57.55 |          1 |     57.55 |                      0    |                         0 |
| 2020.03.25 08:00     | [M30 CLOSE]   | post_n6                               | SELL  |       3 |          1 |     -7.97 |          1 |     -7.97 |                      0    |                         0 |
| 2020.03.25 10:30     | [M30 CLOSE]   | cross                                 | BUY   |       1 |          1 |     -8.8  |          1 |     -8.8  |                      0    |                         0 |
| 2020.03.25 10:30     | [M30 CLOSE]   | cross                                 | BUY   |       3 |          1 |     -8.8  |          1 |     -8.8  |                      0    |                         0 |

## Exit Reason Delta

| local_exit_reason   | deal_reason   |   old_rows |   old_net |   new_rows |   new_net |   net_delta_new_minus_old |   row_delta_new_minus_old |
|:--------------------|:--------------|-----------:|----------:|-----------:|----------:|--------------------------:|--------------------------:|
| deinit_history      | CLIENT        |          1 |   1802.36 |          0 |      0    |                  -1802.36 |                        -1 |
| stage3_cross_exit   | EXPERT        |         30 |   1187.3  |         33 |    999.17 |                   -188.13 |                         3 |
| deal_exit           | SL            |        157 |  -1593.47 |        167 |  -1738.48 |                   -145.01 |                        10 |
| stage2_forced       | EXPERT        |         10 |    702.7  |          9 |    601.98 |                   -100.72 |                        -1 |
| position_gone       | SL            |          4 |    -13.2  |          4 |    -13.2  |                      0    |                         0 |
| stage1_tp           | EXPERT        |         32 |   1225.66 |         33 |   1300.37 |                     74.71 |                         1 |

## New Full Deinit Rows

_No rows._

## Decision

- Smoke gate passes: the original `2022.11.08 16:30` Stage1 no longer survives to deinit and now closes as `stage1_tp / EXPERT`.
- Extended smoke gate passes: deinit rows are zero after extending the window to remove test-end truncation.
- Full deinit gate passes: full-run deinit rows are zero and ledger net equals deal OUT net.
- Merge gate fails for now: full final balance is materially lower than the close-retry baseline, so this EA behavior change requires a dedicated regression decision before it can replace the baseline.
- The largest expected drop is removal of the invalid `mt5_0031` deinit profit; the remaining drop must be reviewed as normal lifecycle changes from managing previously overwritten positions.

## Output Files

- `stage_state_fix_summary.csv`
- `stage_state_full_vs_baseline_anchor_stage_delta.csv`
- `stage_state_full_exit_reason_delta.csv`
- `stage_state_target_mt5_0031_before_after.csv`
- `stage_state_full_deinit_rows.csv`
