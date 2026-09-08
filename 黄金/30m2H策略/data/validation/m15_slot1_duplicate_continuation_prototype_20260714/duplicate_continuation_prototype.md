# M15 SLOT1 Duplicate Continuation Prototype 20260714

## Candidate Summary

| candidate_py_trade_id   | candidate_date      | candidate_mode   | candidate_variant   |   candidate_dynamic_$ |   candidate_stop_pts_spec | candidate_best_mt5   | candidate_match_tier   |   candidate_abs_minutes_to_mt5 | owner_py_trade_id   | owner_date          | owner_mode   |   owner_dynamic_$ | owner_match_tier   |   minutes_after_owner | prototype_duplicate_flag   | prototype_action                |
|:------------------------|:--------------------|:-----------------|:--------------------|----------------------:|--------------------------:|:---------------------|:-----------------------|-------------------------------:|:--------------------|:--------------------|:-------------|------------------:|:-------------------|----------------------:|:---------------------------|:--------------------------------|
| python_mt5_0075         | 2025-10-17 15:00:00 | post_n4          | ea_slot1_replace    |              150.917  |                   12.6364 | mt5_0056             | nearby_60_all          |                             30 | python_mt5_0074     | 2025-10-17 14:30:00 | post_n3      |           37.1577 | exact_align90_all  |                    30 | True                       | suppress_continuation_candidate |
| python_mt5_0089         | 2026-03-24 05:00:00 | post_n5          | ea_slot1_replace    |              -15.5179 |                   19.3915 | mt5_0072             | nearby_60_all          |                             30 | python_mt5_0088     | 2026-03-24 04:30:00 | post_n4      |          -13.6289 | exact_align90_all  |                    30 | True                       | suppress_continuation_candidate |

## Fund Prototype

| scenario                                  |   trade_count |   final_balance |   dynamic_total_profit |   delta_vs_current_final_balance |   delta_vs_current_profit |
|:------------------------------------------|--------------:|----------------:|-----------------------:|---------------------------------:|--------------------------:|
| metadatafix_current                       |            98 |         1969.91 |                1469.91 |                            0     |                     0     |
| suppress_duplicate_continuation_prototype |            96 |         1784.71 |                1284.71 |                         -185.206 |                  -185.206 |

## Signal Gap Effect

| metric                           |    value | note                                                                                            |
|:---------------------------------|---------:|:------------------------------------------------------------------------------------------------|
| suppressed_duplicate_rows        |    2     | Rows flagged by the non-destructive duplicate continuation prototype.                           |
| suppressed_signal_gap_effect_sum |  135.399 | Approximate post-bridge signal-set gap reduction if these Python-unmatched rows are suppressed. |
| raw_dynamic_final_balance_delta  | -185.206 | Raw dynamic-risk replay delta; not the runtime-style adjusted gap metric.                       |

## Decision

- This is a non-destructive prototype; it does not change the official signal snapshot.
- Suppression candidates require a nearby MT5 target already occupied by an exact Python match and a following same-family M15 SLOT1 post_n continuation.
- If accepted, the next step is to rerun mapping/remaining P1 on the filtered prototype output before changing signal generation.
