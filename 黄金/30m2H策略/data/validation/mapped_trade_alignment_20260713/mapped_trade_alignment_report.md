# Python vs MT5 Ledger Mapped Trade Alignment

- EA anchor offset: MT5 `signal_anchor_time + 90 min`.
- Final unique matching excludes `same_dir_7d_unclassified`; those rows remain only as candidate diagnostics.
- Reliable tiers require direction + trigger family + mode family. Relaxed tiers are diagnostic, not final evidence of strategy parity.

## Unique Match Summary
| source      |   python_trades |   mt5_trades |   matched_unique |   reliable_tier_matched |   relaxed_tier_matched |   python_unmatched |   mt5_unmatched |   matched_python_profit |   matched_mt5_profit |   matched_profit_diff |   any_sl_same_count |   all_sl_same_count |
|:------------|----------------:|-------------:|-----------------:|------------------------:|-----------------------:|-------------------:|----------------:|------------------------:|---------------------:|----------------------:|--------------------:|--------------------:|
| python_only |             118 |           78 |               31 |                      23 |                      8 |                 87 |              47 |                 2651.1  |               467.11 |               2183.99 |                  26 |                  26 |
| python_mt5  |             101 |           78 |               30 |                      15 |                     15 |                 71 |              48 |                 9017.14 |               420.15 |               8596.99 |                  22 |                  23 |

## Candidate Tier Summary
| source      | match_tier                |   tier_rank |   candidate_pairs |   mt5_with_candidate |   python_with_candidate |
|:------------|:--------------------------|------------:|------------------:|---------------------:|------------------------:|
| python_mt5  | exact_align90_all         |           1 |                 7 |                    7 |                       7 |
| python_mt5  | nearby_60_all             |           2 |                12 |                    8 |                      12 |
| python_mt5  | nearby_180_all            |           3 |                 2 |                    2 |                       2 |
| python_mt5  | nearby_1d_all             |           4 |                 1 |                    1 |                       1 |
| python_mt5  | nearby_7d_all             |           5 |                20 |                   12 |                      16 |
| python_mt5  | nearby_60_trigger_relaxed |           6 |                12 |                    9 |                      12 |
| python_mt5  | nearby_60_mode_relaxed    |           7 |                 7 |                    5 |                       6 |
| python_mt5  | nearby_7d_trigger_relaxed |           8 |                12 |                    7 |                      11 |
| python_mt5  | nearby_7d_mode_relaxed    |           9 |                43 |                   14 |                      27 |
| python_mt5  | same_dir_7d_unclassified  |          99 |                23 |                    8 |                      21 |
| python_only | exact_align90_all         |           1 |                11 |                   11 |                      11 |
| python_only | nearby_60_all             |           2 |                16 |                   10 |                      16 |
| python_only | nearby_180_all            |           3 |                 4 |                    3 |                       4 |
| python_only | nearby_1d_all             |           4 |                 1 |                    1 |                       1 |
| python_only | nearby_7d_all             |           5 |                20 |                   12 |                      14 |
| python_only | nearby_60_trigger_relaxed |           6 |                12 |                    7 |                      12 |
| python_only | nearby_60_mode_relaxed    |           7 |                 6 |                    4 |                       5 |
| python_only | nearby_7d_trigger_relaxed |           8 |                16 |                    9 |                      14 |
| python_only | nearby_7d_mode_relaxed    |           9 |                54 |                   22 |                      41 |
| python_only | same_dir_7d_unclassified  |          99 |                31 |                   12 |                      22 |

## Unique Match Tier Counts
| source      | match_tier                |   unique_matches |
|:------------|:--------------------------|-----------------:|
| python_mt5  | exact_align90_all         |                7 |
| python_mt5  | nearby_60_all             |                6 |
| python_mt5  | nearby_60_mode_relaxed    |                2 |
| python_mt5  | nearby_60_trigger_relaxed |                8 |
| python_mt5  | nearby_7d_all             |                2 |
| python_mt5  | nearby_7d_mode_relaxed    |                3 |
| python_mt5  | nearby_7d_trigger_relaxed |                2 |
| python_only | exact_align90_all         |               11 |
| python_only | nearby_60_all             |               10 |
| python_only | nearby_60_mode_relaxed    |                1 |
| python_only | nearby_60_trigger_relaxed |                4 |
| python_only | nearby_7d_all             |                2 |
| python_only | nearby_7d_trigger_relaxed |                3 |

## Unmatched Trigger/Mode Summary
| source      | side             | trigger_family   | mode_family   |   rows |
|:------------|:-----------------|:-----------------|:--------------|-------:|
| python_only | python_unmatched | M30 CLOSE        | post_n        |     57 |
| python_only | python_unmatched | M30 CLOSE        | pre_cross     |     15 |
| python_only | python_unmatched | M30 CLOSE        | cross         |      7 |
| python_only | python_unmatched | M15 SLOT1        | cross         |      4 |
| python_only | python_unmatched | M15 SLOT1        | post_n        |      4 |
| python_only | mt5_unmatched    | M30 CLOSE        | post_n        |     18 |
| python_only | mt5_unmatched    | M15 SLOT1        | post_n        |     11 |
| python_only | mt5_unmatched    | M15 SLOT1        | pre_cross     |      6 |
| python_only | mt5_unmatched    | M30 CLOSE        | cross         |      6 |
| python_only | mt5_unmatched    | M30 CLOSE        | pre_cross     |      6 |
| python_mt5  | python_unmatched | M15 SLOT1        | post_n        |     26 |
| python_mt5  | python_unmatched | M15 SLOT1        | pre_cross     |     18 |
| python_mt5  | python_unmatched | M30 CLOSE        | post_n        |     16 |
| python_mt5  | python_unmatched | M15 SLOT1        | cross         |      6 |
| python_mt5  | python_unmatched | M30 CLOSE        | pre_cross     |      3 |
| python_mt5  | python_unmatched | M30 CLOSE        | cross         |      2 |
| python_mt5  | mt5_unmatched    | M30 CLOSE        | post_n        |     18 |
| python_mt5  | mt5_unmatched    | M15 SLOT1        | post_n        |     11 |
| python_mt5  | mt5_unmatched    | M30 CLOSE        | pre_cross     |      7 |
| python_mt5  | mt5_unmatched    | M15 SLOT1        | pre_cross     |      6 |
| python_mt5  | mt5_unmatched    | M30 CLOSE        | cross         |      6 |

## Key Interpretation
- Exact key overlap was zero before anchor correction. After `+90min`, strict exact matches reappear but remain limited.
- The remaining gap is not a ledger completeness issue: fixed MT5 ledger already reconciles to tester final balance.
- The next repair target is signal construction alignment, especially M15/M30 trigger-family drift and post_n raw-parent rules.

## Output Files
- `candidate_match_tier_summary.csv`
- `unique_match_summary.csv`
- `all_candidate_matches.csv`
- `all_unique_matches.csv`
- `unmatched_trigger_mode_summary.csv`
- `python_only_mt5_unique_matches.csv`
- `python_mt5_mt5_unique_matches.csv`
- `*_unmatched_python_trades.csv`
- `*_unmatched_mt5_trades.csv`
