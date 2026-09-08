# Metadatafix Chain Effect 20260714

## Signal Metadata

| snapshot           |   layer3_rows |   rescue_rows |   rescue_spec_false_labels |   rescue_stale_false_but_actual_ok |   rescue_actual_spec_fail |
|:-------------------|--------------:|--------------:|---------------------------:|-----------------------------------:|--------------------------:|
| before_metadatafix |            98 |             8 |                          8 |                                  8 |                         0 |
| after_metadatafix  |            98 |             8 |                          0 |                                  0 |                         0 |

## Dynamic Risk

| source     |   old_trade_count |   new_trade_count |   old_final_balance |   new_final_balance |   final_balance_delta |
|:-----------|------------------:|------------------:|--------------------:|--------------------:|----------------------:|
| python_mt5 |                98 |                98 |             1969.91 |             1969.91 |                     0 |
| mt5_ledger |                78 |                78 |             3811.35 |             3811.35 |                     0 |

## Mapping

| source     |   old_matched_unique |   new_matched_unique |   old_python_unmatched |   new_python_unmatched |   old_mt5_unmatched |   new_mt5_unmatched |
|:-----------|---------------------:|---------------------:|-----------------------:|-----------------------:|--------------------:|--------------------:|
| python_mt5 |                   57 |                   57 |                     41 |                     41 |                  21 |                  21 |

## Top Case Cause Shift

| trade_id        | target_time         |   profit | old_cause             | new_cause                             |   new_mt5_abs_minutes | new_mt5_date        |
|:----------------|:--------------------|---------:|:----------------------|:--------------------------------------|----------------------:|:--------------------|
| python_mt5_0079 | 2025-10-21 10:00:00 |  201.851 | unique_match_conflict | low_confidence_far_candidate_conflict |                  5490 | 2025-10-17 14:30:00 |
| python_mt5_0073 | 2025-10-17 11:00:00 |  189.621 | unique_match_conflict | low_confidence_far_candidate_conflict |                  1650 | 2025-10-16 07:30:00 |
| python_mt5_0075 | 2025-10-17 15:00:00 |  150.917 | unique_match_conflict | unique_match_conflict                 |                    30 | 2025-10-17 14:30:00 |

## Decision

- The rescue metadata fix removes stale `spec_pass=False` labels for M15 SLOT1 runtime rescue rows.
- Dynamic final balances and unique mapping counts are unchanged.
- `python_mt5_0073` and `python_mt5_0079` move from ordinary unique-match conflict to low-confidence far-candidate conflict.
- `python_mt5_0075` remains the next real nearby unique-match conflict / duplicate continuation case.
