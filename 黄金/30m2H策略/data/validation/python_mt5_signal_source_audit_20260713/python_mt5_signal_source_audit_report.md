# Python-MT5 Signal Source Audit

## Summary

| signal_source                        |   m30_postn_signals |   mode_matches_counter_t_signed |   mode_matches_counter_t_abs |   mode_matches_counter_t_plus_30_abs |
|:-------------------------------------|--------------------:|--------------------------------:|-----------------------------:|-------------------------------------:|
| old_signals_mt5_vs_processed_m30_mt5 |                  57 |                               2 |                            2 |                                   52 |
| shift90_mt5_h2_barlevel_direct       |                  54 |                              54 |                           54 |                                    0 |
| shift90_mt5_h2_barlevel_q2early      |                  54 |                              54 |                           54 |                                    0 |
| shift90_python_h2_context_q2early    |                  54 |                              54 |                           54 |                                    0 |

## Interpretation

- `old_signals_mt5_vs_processed_m30_mt5` is the currently used directory for dynamic-risk Python-MT5 runs.
- The shift90 variants are versioned diagnostic outputs and are not used by `prepare_dynamic_risk_inputs.py` yet.
- If a signal file's `post_nN` does not match its M30 `merged_post_cross_n`, downstream trade mapping mixes signal and market-counter semantics.

## Output Files

- `python_mt5_signal_source_audit_details.csv`
- `python_mt5_signal_source_audit_summary.csv`
