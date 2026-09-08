# Two-sided correction accounting prototype

## Scope

- Diagnostic accounting bridge only; not a mergeable signal implementation.
- Removes P0 Python false positives backed by EA M15 diagnostics.
- Injects selected MT5-only rows using MT5 ledger net profit to test whether paired recovery improves the signal-set gap.

## Removed Python Rows
| run                           |   removed_count |   removed_profit_sum | removed_dates                           |
|:------------------------------|----------------:|---------------------:|:----------------------------------------|
| remove_p0_python_only         |               2 |              391.472 | 2025-10-17 11:00:00;2025-10-21 10:00:00 |
| remove_p0_add_p0_mt5_bridge   |               2 |              391.472 | 2025-10-17 11:00:00;2025-10-21 10:00:00 |
| remove_p0_add_p0p1_mt5_bridge |               2 |              391.472 | 2025-10-17 11:00:00;2025-10-21 10:00:00 |

## Bridge MT5 Rows
| run                           |   bridge_count |   bridge_profit_sum | bridge_mt5_trade_ids                         |
|:------------------------------|---------------:|--------------------:|:---------------------------------------------|
| remove_p0_python_only         |              0 |                0    |                                              |
| remove_p0_add_p0_mt5_bridge   |              3 |              520.57 | mt5_0068;mt5_0005;mt5_0019                   |
| remove_p0_add_p0p1_mt5_bridge |              5 |              742.87 | mt5_0068;mt5_0005;mt5_0019;mt5_0074;mt5_0069 |

## Gap Components
| run                           |   python_mt5_total_profit |   mt5_total_profit |   direct_dynamic_gap_python_minus_mt5 |   matched_profit_diff |   python_unmatched_gap_effect |   mt5_unmatched_gap_effect |   signal_set_gap_effect |   reconstructed_dynamic_gap |
|:------------------------------|--------------------------:|-------------------:|--------------------------------------:|----------------------:|------------------------------:|---------------------------:|------------------------:|----------------------------:|
| current_metadatafix           |                   1469.91 |            3311.35 |                              -1841.44 |              -2088.13 |                       926.613 |                    -679.92 |                 246.693 |                    -1841.44 |
| remove_p0_python_only         |                   1078.44 |            3311.35 |                              -2232.91 |              -2088.13 |                       535.14  |                    -679.92 |                -144.78  |                    -2232.91 |
| remove_p0_add_p0_mt5_bridge   |                   1599.01 |            3311.35 |                              -1712.34 |              -2088.13 |                       535.14  |                    -159.35 |                 375.79  |                    -1712.34 |
| remove_p0_add_p0p1_mt5_bridge |                   1821.31 |            3311.35 |                              -1490.04 |              -2088.13 |                       535.14  |                      62.95 |                 598.09  |                    -1490.04 |

## Mapping Summary
| run                           | source     |   python_trades |   mt5_trades |   matched_unique |   reliable_tier_matched |   relaxed_tier_matched |   python_unmatched |   mt5_unmatched |   matched_profit_diff |
|:------------------------------|:-----------|----------------:|-------------:|-----------------:|------------------------:|-----------------------:|-------------------:|----------------:|----------------------:|
| current_metadatafix           | python_mt5 |              98 |           78 |               57 |                      29 |                     28 |                 41 |              21 |              -2088.13 |
| remove_p0_python_only         | python_mt5 |              96 |           78 |               57 |                      29 |                     28 |                 39 |              21 |              -2088.13 |
| remove_p0_add_p0_mt5_bridge   | python_mt5 |              99 |           78 |               60 |                      32 |                     28 |                 39 |              18 |              -2088.13 |
| remove_p0_add_p0p1_mt5_bridge | python_mt5 |             101 |           78 |               62 |                      34 |                     28 |                 39 |              16 |              -2088.13 |

## Decision Matrix
| run                           |   direct_gap |   direct_gap_delta_vs_current |   matched_unique |   matched_unique_delta |   python_unmatched |   python_unmatched_delta |   mt5_unmatched |   mt5_unmatched_delta |   matched_profit_diff |   signal_set_gap_effect |
|:------------------------------|-------------:|------------------------------:|-----------------:|-----------------------:|-------------------:|-------------------------:|----------------:|----------------------:|----------------------:|------------------------:|
| remove_p0_python_only         |     -2232.91 |                      -391.472 |               57 |                      0 |                 39 |                       -2 |              21 |                     0 |              -2088.13 |                 -144.78 |
| remove_p0_add_p0_mt5_bridge   |     -1712.34 |                       129.098 |               60 |                      3 |                 39 |                       -2 |              18 |                    -3 |              -2088.13 |                  375.79 |
| remove_p0_add_p0p1_mt5_bridge |     -1490.04 |                       351.398 |               62 |                      5 |                 39 |                       -2 |              16 |                    -5 |              -2088.13 |                  598.09 |

## Interpretation

- `remove_p0_python_only` measures the cost of removing only the two confirmed false positives.
- `remove_p0_add_p0_mt5_bridge` tests the first paired correction using only P0 time-axis MT5-only candidates.
- `remove_p0_add_p0p1_mt5_bridge` adds P1 MT5-only candidates as a broader accounting stress test.
- A variant can justify deeper signal-code work only if it improves direct gap and mapping coverage without reintroducing the two false positives.
