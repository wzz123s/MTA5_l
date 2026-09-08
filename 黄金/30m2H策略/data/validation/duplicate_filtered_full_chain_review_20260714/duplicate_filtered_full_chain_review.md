# Duplicate Filtered Full-Chain Review 20260714

## Mapping Before/After

| source     |   current_python_trades |   filtered_python_trades |   current_matched_unique |   filtered_matched_unique |   current_python_unmatched |   filtered_python_unmatched |   current_mt5_unmatched |   filtered_mt5_unmatched |
|:-----------|------------------------:|-------------------------:|-------------------------:|--------------------------:|---------------------------:|----------------------------:|------------------------:|-------------------------:|
| python_mt5 |                      98 |                       96 |                       57 |                        57 |                         41 |                          39 |                      21 |                       21 |

## Runtime Gap Projection

| metric                       |   value | note                                                                      |
|:-----------------------------|--------:|:--------------------------------------------------------------------------|
| current_runtime_direct_gap   | 477.154 | Current runtime-style adjusted direct gap.                                |
| current_signal_set_gap       | 434.416 | Post-bridge signal-set gap before duplicate suppression.                  |
| suppressed_signal_gap_effect | 135.399 | Net Python-unmatched gap effect of the duplicate-continuation candidates. |
| projected_signal_set_gap     | 299.017 | Current signal gap minus suppressed duplicate continuation effect.        |
| projected_runtime_gap        | 341.755 | Matched residual sum plus projected signal-set gap.                       |

## Filtered Top Python-Unmatched

| py_trade_id     | date                | trigger_family   | mode_family   | mode      |   dynamic_total_$ |   abs_dynamic_total_$ |
|:----------------|:--------------------|:-----------------|:--------------|:----------|------------------:|----------------------:|
| python_mt5_0078 | 2025-10-21 10:00:00 | M15 SLOT1        | post_n        | post_n6   |          201.851  |              201.851  |
| python_mt5_0073 | 2025-10-17 11:00:00 | M15 SLOT1        | pre_cross     | pre_cross |          189.621  |              189.621  |
| python_mt5_0089 | 2026-05-28 15:30:00 | M15 SLOT1        | cross         | cross     |          135.186  |              135.186  |
| python_mt5_0065 | 2025-04-22 16:30:00 | M15 SLOT1        | post_n        | post_n5   |          115.714  |              115.714  |
| python_mt5_0088 | 2026-05-28 14:30:00 | M15 SLOT1        | pre_cross     | pre_cross |          114.292  |              114.292  |
| python_mt5_0068 | 2025-09-30 09:30:00 | M15 SLOT1        | pre_cross     | pre_cross |           97.9377 |               97.9377 |
| python_mt5_0007 | 2020-03-13 15:30:00 | M30 CLOSE        | pre_cross     | pre_cross |           64.2283 |               64.2283 |
| python_mt5_0096 | 2026-06-30 09:30:00 | M15 SLOT1        | post_n        | post_n2   |          -50.3853 |               50.3853 |
| python_mt5_0062 | 2025-04-21 02:30:00 | M15 SLOT1        | post_n        | post_n6   |           40.0159 |               40.0159 |
| python_mt5_0076 | 2025-10-20 07:30:00 | M15 SLOT1        | cross         | cross     |          -38.9392 |               38.9392 |

## Decision

- The filtered prototype removes two Python-MT5 trades and keeps matched_unique unchanged.
- The projected runtime gap improves only by the suppressed signal-set effect; this is a projection, not a full runtime re-simulation.
- Continue with the next largest non-bridge P1 after confirming whether this projection is worth turning into a signal-generation rule.
