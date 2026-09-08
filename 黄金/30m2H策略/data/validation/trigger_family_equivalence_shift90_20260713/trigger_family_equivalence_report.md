# Trigger Family Equivalence Shift90 Prototype

## Policy Summary

| policy                            |   python_trades |   mt5_trades |   matched_unique |   reliable_tier_matched |   relaxed_tier_matched |   equivalence_matches |   python_unmatched |   mt5_unmatched |   matched_python_profit |   matched_mt5_profit |   matched_profit_diff |
|:----------------------------------|----------------:|-------------:|-----------------:|------------------------:|-----------------------:|----------------------:|-------------------:|----------------:|------------------------:|---------------------:|----------------------:|
| baseline                          |              98 |           78 |               34 |                      18 |                     16 |                     0 |                 64 |              44 |                 244.764 |               -56.77 |               301.534 |
| m30_to_m15_replace_30             |              98 |           78 |               34 |                      27 |                      7 |                     9 |                 64 |              44 |                 244.764 |               -56.77 |               301.534 |
| m30_to_m15_replace_30_profit20    |              98 |           78 |               34 |                      24 |                     10 |                     6 |                 64 |              44 |                 244.764 |               -56.77 |               301.534 |
| bidirectional_m30_m15_30          |              98 |           78 |               34 |                      27 |                      7 |                     9 |                 64 |              44 |                 244.764 |               -56.77 |               301.534 |
| bidirectional_m30_m15_90          |              98 |           78 |               34 |                      28 |                      6 |                    10 |                 64 |              44 |                 244.764 |               -56.77 |               301.534 |
| bidirectional_m30_m15_90_profit20 |              98 |           78 |               34 |                      24 |                     10 |                     6 |                 64 |              44 |                 244.764 |               -56.77 |               301.534 |

## Tier Counts

| policy                            | effective_match_tier                 |   rows |
|:----------------------------------|:-------------------------------------|-------:|
| baseline                          | exact_align90_all                    |     16 |
| baseline                          | nearby_60_all                        |      2 |
| baseline                          | nearby_60_mode_relaxed               |      1 |
| baseline                          | nearby_60_trigger_relaxed            |     11 |
| baseline                          | nearby_7d_mode_relaxed               |      3 |
| baseline                          | nearby_7d_trigger_relaxed            |      1 |
| bidirectional_m30_m15_30          | equiv_m30_to_m15_replace_30          |      9 |
| bidirectional_m30_m15_30          | exact_align90_all                    |     16 |
| bidirectional_m30_m15_30          | nearby_60_all                        |      2 |
| bidirectional_m30_m15_30          | nearby_60_mode_relaxed               |      1 |
| bidirectional_m30_m15_30          | nearby_60_trigger_relaxed            |      2 |
| bidirectional_m30_m15_30          | nearby_7d_mode_relaxed               |      3 |
| bidirectional_m30_m15_30          | nearby_7d_trigger_relaxed            |      1 |
| bidirectional_m30_m15_90          | equiv_bidirectional_m30_m15_90       |      1 |
| bidirectional_m30_m15_90          | equiv_m30_to_m15_replace_30          |      9 |
| bidirectional_m30_m15_90          | exact_align90_all                    |     16 |
| bidirectional_m30_m15_90          | nearby_60_all                        |      2 |
| bidirectional_m30_m15_90          | nearby_60_mode_relaxed               |      1 |
| bidirectional_m30_m15_90          | nearby_60_trigger_relaxed            |      1 |
| bidirectional_m30_m15_90          | nearby_7d_mode_relaxed               |      3 |
| bidirectional_m30_m15_90          | nearby_7d_trigger_relaxed            |      1 |
| bidirectional_m30_m15_90_profit20 | equiv_m30_to_m15_replace_30_profit20 |      6 |
| bidirectional_m30_m15_90_profit20 | exact_align90_all                    |     16 |
| bidirectional_m30_m15_90_profit20 | nearby_60_all                        |      2 |
| bidirectional_m30_m15_90_profit20 | nearby_60_mode_relaxed               |      1 |
| bidirectional_m30_m15_90_profit20 | nearby_60_trigger_relaxed            |      5 |
| bidirectional_m30_m15_90_profit20 | nearby_7d_mode_relaxed               |      3 |
| bidirectional_m30_m15_90_profit20 | nearby_7d_trigger_relaxed            |      1 |
| m30_to_m15_replace_30             | equiv_m30_to_m15_replace_30          |      9 |
| m30_to_m15_replace_30             | exact_align90_all                    |     16 |
| m30_to_m15_replace_30             | nearby_60_all                        |      2 |
| m30_to_m15_replace_30             | nearby_60_mode_relaxed               |      1 |
| m30_to_m15_replace_30             | nearby_60_trigger_relaxed            |      2 |
| m30_to_m15_replace_30             | nearby_7d_mode_relaxed               |      3 |
| m30_to_m15_replace_30             | nearby_7d_trigger_relaxed            |      1 |
| m30_to_m15_replace_30_profit20    | equiv_m30_to_m15_replace_30_profit20 |      6 |
| m30_to_m15_replace_30_profit20    | exact_align90_all                    |     16 |
| m30_to_m15_replace_30_profit20    | nearby_60_all                        |      2 |
| m30_to_m15_replace_30_profit20    | nearby_60_mode_relaxed               |      1 |
| m30_to_m15_replace_30_profit20    | nearby_60_trigger_relaxed            |      5 |
| m30_to_m15_replace_30_profit20    | nearby_7d_mode_relaxed               |      3 |
| m30_to_m15_replace_30_profit20    | nearby_7d_trigger_relaxed            |      1 |

## Selected Equivalence Matches

| policy                            | effective_match_tier                 | py_trade_id     | mt5_trade_id   | py_date             | mt5_aligned_time    |   abs_time_diff_minutes | dir_norm   | py_trigger_family   | mt5_trigger_family   | py_mode_family   | mt5_mode_family   | py_mode   | mt5_signal_src                      | py_variant       |   py_profit |   mt5_profit |   profit_diff |
|:----------------------------------|:-------------------------------------|:----------------|:---------------|:--------------------|:--------------------|------------------------:|:-----------|:--------------------|:---------------------|:-----------------|:------------------|:----------|:------------------------------------|:-----------------|------------:|-------------:|--------------:|
| m30_to_m15_replace_30             | equiv_m30_to_m15_replace_30          | python_mt5_0085 | mt5_0064       | 2026-02-02 15:30:00 | 2026-02-02 15:30:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -53.4448  |       -53.31 |      -0.13479 |
| m30_to_m15_replace_30             | equiv_m30_to_m15_replace_30          | python_mt5_0051 | mt5_0037       | 2024-04-03 09:00:00 | 2024-04-03 09:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -17.166   |       -11.36 |      -5.80601 |
| m30_to_m15_replace_30             | equiv_m30_to_m15_replace_30          | python_mt5_0055 | mt5_0039       | 2024-04-08 14:00:00 | 2024-04-08 14:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -16.8013  |       -22.67 |       5.86875 |
| m30_to_m15_replace_30             | equiv_m30_to_m15_replace_30          | python_mt5_0081 | mt5_0060       | 2026-01-21 17:00:00 | 2026-01-21 17:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -48.5197  |       -56.43 |       7.91031 |
| m30_to_m15_replace_30             | equiv_m30_to_m15_replace_30          | python_mt5_0080 | mt5_0058       | 2025-12-24 04:30:00 | 2025-12-24 04:30:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -48.2132  |       -62.03 |      13.8168  |
| m30_to_m15_replace_30             | equiv_m30_to_m15_replace_30          | python_mt5_0071 | mt5_0054       | 2025-10-15 14:00:00 | 2025-10-15 14:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -32.0744  |       -47.79 |      15.7156  |
| m30_to_m15_replace_30             | equiv_m30_to_m15_replace_30          | python_mt5_0087 | mt5_0071       | 2026-03-24 02:00:00 | 2026-03-24 02:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |    -9.07122 |       104.97 |    -114.041   |
| m30_to_m15_replace_30             | equiv_m30_to_m15_replace_30          | python_mt5_0063 | mt5_0046       | 2025-04-22 10:30:00 | 2025-04-22 10:30:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   207.952   |       -42.51 |     250.462   |
| m30_to_m15_replace_30             | equiv_m30_to_m15_replace_30          | python_mt5_0064 | mt5_0047       | 2025-04-22 16:00:00 | 2025-04-22 15:30:00 |                      30 | SELL       | M15 SLOT1           | M30 CLOSE            | post_n           | post_n            | post_n4   | post_n3                             | ea_slot1_replace |    46.7316  |       220.42 |    -173.688   |
| m30_to_m15_replace_30_profit20    | equiv_m30_to_m15_replace_30_profit20 | python_mt5_0085 | mt5_0064       | 2026-02-02 15:30:00 | 2026-02-02 15:30:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -53.4448  |       -53.31 |      -0.13479 |
| m30_to_m15_replace_30_profit20    | equiv_m30_to_m15_replace_30_profit20 | python_mt5_0051 | mt5_0037       | 2024-04-03 09:00:00 | 2024-04-03 09:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -17.166   |       -11.36 |      -5.80601 |
| m30_to_m15_replace_30_profit20    | equiv_m30_to_m15_replace_30_profit20 | python_mt5_0055 | mt5_0039       | 2024-04-08 14:00:00 | 2024-04-08 14:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -16.8013  |       -22.67 |       5.86875 |
| m30_to_m15_replace_30_profit20    | equiv_m30_to_m15_replace_30_profit20 | python_mt5_0081 | mt5_0060       | 2026-01-21 17:00:00 | 2026-01-21 17:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -48.5197  |       -56.43 |       7.91031 |
| m30_to_m15_replace_30_profit20    | equiv_m30_to_m15_replace_30_profit20 | python_mt5_0080 | mt5_0058       | 2025-12-24 04:30:00 | 2025-12-24 04:30:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -48.2132  |       -62.03 |      13.8168  |
| m30_to_m15_replace_30_profit20    | equiv_m30_to_m15_replace_30_profit20 | python_mt5_0071 | mt5_0054       | 2025-10-15 14:00:00 | 2025-10-15 14:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -32.0744  |       -47.79 |      15.7156  |
| bidirectional_m30_m15_30          | equiv_m30_to_m15_replace_30          | python_mt5_0085 | mt5_0064       | 2026-02-02 15:30:00 | 2026-02-02 15:30:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -53.4448  |       -53.31 |      -0.13479 |
| bidirectional_m30_m15_30          | equiv_m30_to_m15_replace_30          | python_mt5_0051 | mt5_0037       | 2024-04-03 09:00:00 | 2024-04-03 09:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -17.166   |       -11.36 |      -5.80601 |
| bidirectional_m30_m15_30          | equiv_m30_to_m15_replace_30          | python_mt5_0055 | mt5_0039       | 2024-04-08 14:00:00 | 2024-04-08 14:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -16.8013  |       -22.67 |       5.86875 |
| bidirectional_m30_m15_30          | equiv_m30_to_m15_replace_30          | python_mt5_0081 | mt5_0060       | 2026-01-21 17:00:00 | 2026-01-21 17:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -48.5197  |       -56.43 |       7.91031 |
| bidirectional_m30_m15_30          | equiv_m30_to_m15_replace_30          | python_mt5_0080 | mt5_0058       | 2025-12-24 04:30:00 | 2025-12-24 04:30:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -48.2132  |       -62.03 |      13.8168  |
| bidirectional_m30_m15_30          | equiv_m30_to_m15_replace_30          | python_mt5_0071 | mt5_0054       | 2025-10-15 14:00:00 | 2025-10-15 14:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -32.0744  |       -47.79 |      15.7156  |
| bidirectional_m30_m15_30          | equiv_m30_to_m15_replace_30          | python_mt5_0087 | mt5_0071       | 2026-03-24 02:00:00 | 2026-03-24 02:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |    -9.07122 |       104.97 |    -114.041   |
| bidirectional_m30_m15_30          | equiv_m30_to_m15_replace_30          | python_mt5_0063 | mt5_0046       | 2025-04-22 10:30:00 | 2025-04-22 10:30:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   207.952   |       -42.51 |     250.462   |
| bidirectional_m30_m15_30          | equiv_m30_to_m15_replace_30          | python_mt5_0064 | mt5_0047       | 2025-04-22 16:00:00 | 2025-04-22 15:30:00 |                      30 | SELL       | M15 SLOT1           | M30 CLOSE            | post_n           | post_n            | post_n4   | post_n3                             | ea_slot1_replace |    46.7316  |       220.42 |    -173.688   |
| bidirectional_m30_m15_90          | equiv_m30_to_m15_replace_30          | python_mt5_0085 | mt5_0064       | 2026-02-02 15:30:00 | 2026-02-02 15:30:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -53.4448  |       -53.31 |      -0.13479 |
| bidirectional_m30_m15_90          | equiv_m30_to_m15_replace_30          | python_mt5_0051 | mt5_0037       | 2024-04-03 09:00:00 | 2024-04-03 09:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -17.166   |       -11.36 |      -5.80601 |
| bidirectional_m30_m15_90          | equiv_m30_to_m15_replace_30          | python_mt5_0055 | mt5_0039       | 2024-04-08 14:00:00 | 2024-04-08 14:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -16.8013  |       -22.67 |       5.86875 |
| bidirectional_m30_m15_90          | equiv_m30_to_m15_replace_30          | python_mt5_0081 | mt5_0060       | 2026-01-21 17:00:00 | 2026-01-21 17:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -48.5197  |       -56.43 |       7.91031 |
| bidirectional_m30_m15_90          | equiv_m30_to_m15_replace_30          | python_mt5_0080 | mt5_0058       | 2025-12-24 04:30:00 | 2025-12-24 04:30:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -48.2132  |       -62.03 |      13.8168  |
| bidirectional_m30_m15_90          | equiv_m30_to_m15_replace_30          | python_mt5_0071 | mt5_0054       | 2025-10-15 14:00:00 | 2025-10-15 14:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -32.0744  |       -47.79 |      15.7156  |
| bidirectional_m30_m15_90          | equiv_m30_to_m15_replace_30          | python_mt5_0087 | mt5_0071       | 2026-03-24 02:00:00 | 2026-03-24 02:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |    -9.07122 |       104.97 |    -114.041   |
| bidirectional_m30_m15_90          | equiv_m30_to_m15_replace_30          | python_mt5_0063 | mt5_0046       | 2025-04-22 10:30:00 | 2025-04-22 10:30:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   207.952   |       -42.51 |     250.462   |
| bidirectional_m30_m15_90          | equiv_m30_to_m15_replace_30          | python_mt5_0064 | mt5_0047       | 2025-04-22 16:00:00 | 2025-04-22 15:30:00 |                      30 | SELL       | M15 SLOT1           | M30 CLOSE            | post_n           | post_n            | post_n4   | post_n3                             | ea_slot1_replace |    46.7316  |       220.42 |    -173.688   |
| bidirectional_m30_m15_90          | equiv_bidirectional_m30_m15_90       | python_mt5_0024 | mt5_0016       | 2020-07-28 08:30:00 | 2020-07-28 09:30:00 |                      60 | SELL       | M30 CLOSE           | M15 SLOT1            | post_n           | post_n            | post_n3   | post_n4_m15_slot1_replace_or_rescue | m30_base         |    21.5133  |       -87.24 |     108.753   |
| bidirectional_m30_m15_90_profit20 | equiv_m30_to_m15_replace_30_profit20 | python_mt5_0085 | mt5_0064       | 2026-02-02 15:30:00 | 2026-02-02 15:30:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -53.4448  |       -53.31 |      -0.13479 |
| bidirectional_m30_m15_90_profit20 | equiv_m30_to_m15_replace_30_profit20 | python_mt5_0051 | mt5_0037       | 2024-04-03 09:00:00 | 2024-04-03 09:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -17.166   |       -11.36 |      -5.80601 |
| bidirectional_m30_m15_90_profit20 | equiv_m30_to_m15_replace_30_profit20 | python_mt5_0055 | mt5_0039       | 2024-04-08 14:00:00 | 2024-04-08 14:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -16.8013  |       -22.67 |       5.86875 |
| bidirectional_m30_m15_90_profit20 | equiv_m30_to_m15_replace_30_profit20 | python_mt5_0081 | mt5_0060       | 2026-01-21 17:00:00 | 2026-01-21 17:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -48.5197  |       -56.43 |       7.91031 |
| bidirectional_m30_m15_90_profit20 | equiv_m30_to_m15_replace_30_profit20 | python_mt5_0080 | mt5_0058       | 2025-12-24 04:30:00 | 2025-12-24 04:30:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -48.2132  |       -62.03 |      13.8168  |
| bidirectional_m30_m15_90_profit20 | equiv_m30_to_m15_replace_30_profit20 | python_mt5_0071 | mt5_0054       | 2025-10-15 14:00:00 | 2025-10-15 14:00:00 |                       0 | SELL       | M15 SLOT1           | M30 CLOSE            | pre_cross        | pre_cross         | pre_cross | pre_cross                           | ea_slot1_replace |   -32.0744  |       -47.79 |      15.7156  |

## Interpretation

- `m30_to_m15_replace_30` only promotes Python `ea_slot1_replace` rows when MT5 is `M30 CLOSE`, direction and mode family match, and time distance is within 30 minutes.
- Bidirectional policies additionally allow MT5 `M15 SLOT1` to match Python `M30 CLOSE` parent rows within 30 or 90 minutes.
- This is a mapping prototype only; it does not change Python or EA trading behavior.

## Output Files

- `trigger_family_equivalence_policy_summary.csv`
- `trigger_family_equivalence_tier_counts.csv`
- `trigger_family_equivalence_all_selected_matches.csv`
- `trigger_family_equivalence_selected_equiv_matches.csv`
