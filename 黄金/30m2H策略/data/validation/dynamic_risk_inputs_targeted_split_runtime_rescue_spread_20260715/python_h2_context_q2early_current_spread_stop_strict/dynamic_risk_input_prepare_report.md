# Dynamic Risk Input Preparation - shift90

## Summary

| source      | source_variant                    |   layer3_rows |   stage_rows |   merged_rows |   signal_only_rows |   stage_only_rows |   matched_rows |   layer3_dupe_keys |   stage_dupe_keys |   min_stop_pts_spec |   max_stop_pts_spec |   m30_postn_signals |   postn_counter_t_abs_matches |   postn_counter_t_signed_matches |
|:------------|:----------------------------------|--------------:|-------------:|--------------:|-------------------:|------------------:|---------------:|-------------------:|------------------:|--------------------:|--------------------:|--------------------:|------------------------------:|---------------------------------:|
| python_only | baseline                          |           118 |          118 |           118 |                  0 |                 0 |            118 |                  0 |                 0 |             5.04179 |             34.9591 |                     |                               |                                  |
| python_mt5  | shift90_python_h2_context_q2early |            96 |           96 |            96 |                  0 |                 0 |             96 |                  0 |                 0 |             5.48895 |             34.757  |                  54 |                            54 |                               54 |

## Notes
- Python-only remains the baseline `data/signals` source.
- Python-MT5 now uses `signals_mt5_shift90_20260712/python_h2_context_q2early`.
- This output intentionally does not overwrite `dynamic_risk_inputs_20260712`.
