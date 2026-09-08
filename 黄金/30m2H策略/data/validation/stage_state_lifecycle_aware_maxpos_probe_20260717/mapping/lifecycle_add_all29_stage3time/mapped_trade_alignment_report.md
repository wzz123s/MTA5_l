# Python vs MT5 Ledger Mapped Trade Alignment

- EA anchor offset: MT5 `signal_anchor_time + 90 min`.
- Final unique matching excludes `same_dir_7d_unclassified`; those rows remain only as candidate diagnostics.
- Reliable tiers require direction + trigger family + mode family. Relaxed tiers are diagnostic, not final evidence of strategy parity.

## Unique Match Summary
| source      |   python_trades |   mt5_trades |   matched_unique |   reliable_tier_matched |   relaxed_tier_matched |   python_unmatched |   mt5_unmatched |   matched_python_profit |   matched_mt5_profit |   matched_profit_diff |   any_sl_same_count |   all_sl_same_count |
|:------------|----------------:|-------------:|-----------------:|------------------------:|-----------------------:|-------------------:|----------------:|------------------------:|---------------------:|----------------------:|--------------------:|--------------------:|
| python_only |             118 |           82 |               61 |                      43 |                     18 |                 57 |              21 |                 5486.13 |               983.63 |              4502.5   |                  49 |                  48 |
| python_mt5  |             117 |           82 |               67 |                      33 |                     34 |                 50 |              15 |                 1052.58 |               640.89 |               411.688 |                  57 |                  51 |

## Candidate Tier Summary
| source      | match_tier                |   tier_rank |   candidate_pairs |   mt5_with_candidate |   python_with_candidate |
|:------------|:--------------------------|------------:|------------------:|---------------------:|------------------------:|
| python_mt5  | exact_align90_all         |           1 |                24 |                   24 |                      24 |
| python_mt5  | nearby_60_all             |           2 |                15 |                   10 |                      15 |
| python_mt5  | nearby_180_all            |           3 |                 2 |                    1 |                       2 |
| python_mt5  | nearby_1d_all             |           4 |                 4 |                    2 |                       4 |
| python_mt5  | nearby_7d_all             |           5 |                49 |                   23 |                      39 |
| python_mt5  | nearby_60_trigger_relaxed |           6 |                43 |                   26 |                      43 |
| python_mt5  | nearby_60_mode_relaxed    |           7 |                 9 |                    7 |                       8 |
| python_mt5  | nearby_7d_trigger_relaxed |           8 |                47 |                   14 |                      35 |
| python_mt5  | nearby_7d_mode_relaxed    |           9 |                66 |                   23 |                      45 |
| python_mt5  | same_dir_7d_unclassified  |          99 |                38 |                   16 |                      35 |
| python_only | exact_align90_all         |           1 |                18 |                   18 |                      18 |
| python_only | nearby_60_all             |           2 |                38 |                   23 |                      38 |
| python_only | nearby_180_all            |           3 |                11 |                    9 |                      11 |
| python_only | nearby_1d_all             |           4 |                 2 |                    2 |                       2 |
| python_only | nearby_7d_all             |           5 |                39 |                   19 |                      27 |
| python_only | nearby_60_trigger_relaxed |           6 |                18 |                   12 |                      18 |
| python_only | nearby_60_mode_relaxed    |           7 |                 7 |                    5 |                       6 |
| python_only | nearby_7d_trigger_relaxed |           8 |                48 |                   19 |                      40 |
| python_only | nearby_7d_mode_relaxed    |           9 |                76 |                   32 |                      56 |
| python_only | same_dir_7d_unclassified  |          99 |                40 |                   18 |                      30 |

## Unique Match Tier Counts
| source      | match_tier                |   unique_matches |
|:------------|:--------------------------|-----------------:|
| python_mt5  | exact_align90_all         |               24 |
| python_mt5  | nearby_1d_all             |                1 |
| python_mt5  | nearby_60_all             |                3 |
| python_mt5  | nearby_60_mode_relaxed    |                1 |
| python_mt5  | nearby_60_trigger_relaxed |               25 |
| python_mt5  | nearby_7d_all             |                5 |
| python_mt5  | nearby_7d_mode_relaxed    |                5 |
| python_mt5  | nearby_7d_trigger_relaxed |                3 |
| python_only | exact_align90_all         |               18 |
| python_only | nearby_60_all             |               21 |
| python_only | nearby_60_mode_relaxed    |                1 |
| python_only | nearby_60_trigger_relaxed |                6 |
| python_only | nearby_7d_all             |                4 |
| python_only | nearby_7d_mode_relaxed    |                3 |
| python_only | nearby_7d_trigger_relaxed |                8 |

## Unmatched Trigger/Mode Summary
| source      | side             | trigger_family   | mode_family   |   rows |
|:------------|:-----------------|:-----------------|:--------------|-------:|
| python_only | python_unmatched | M30 CLOSE        | post_n        |     36 |
| python_only | python_unmatched | M30 CLOSE        | pre_cross     |      9 |
| python_only | python_unmatched | M30 CLOSE        | cross         |      6 |
| python_only | python_unmatched | M15 SLOT1        | cross         |      4 |
| python_only | python_unmatched | M15 SLOT1        | post_n        |      2 |
| python_only | mt5_unmatched    | M15 SLOT1        | pre_cross     |      5 |
| python_only | mt5_unmatched    | M30 CLOSE        | post_n        |      5 |
| python_only | mt5_unmatched    | M15 SLOT1        | post_n        |      4 |
| python_only | mt5_unmatched    | M30 CLOSE        | pre_cross     |      4 |
| python_only | mt5_unmatched    | M30 CLOSE        | cross         |      3 |
| python_mt5  | python_unmatched | M15 SLOT1        | post_n        |     27 |
| python_mt5  | python_unmatched | M30 CLOSE        | post_n        |      9 |
| python_mt5  | python_unmatched | M15 SLOT1        | pre_cross     |      7 |
| python_mt5  | python_unmatched | M30 CLOSE        | cross         |      3 |
| python_mt5  | python_unmatched | M15 SLOT1        | cross         |      2 |
| python_mt5  | python_unmatched | M30 CLOSE        | pre_cross     |      2 |
| python_mt5  | mt5_unmatched    | M30 CLOSE        | post_n        |      6 |
| python_mt5  | mt5_unmatched    | M15 SLOT1        | pre_cross     |      4 |
| python_mt5  | mt5_unmatched    | M15 SLOT1        | post_n        |      3 |
| python_mt5  | mt5_unmatched    | M30 CLOSE        | pre_cross     |      2 |

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
