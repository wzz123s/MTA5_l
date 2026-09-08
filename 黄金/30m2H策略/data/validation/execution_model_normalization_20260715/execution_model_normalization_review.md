# Python-MT5 execution-model normalization prototype

## Scope

- Non-destructive prototype; no EA change and no signal-set change.
- Recalculates Python dynamic risk using MT5-compatible value and EA StageLots parity.
- MT5 tick value per 1.00 lot: `0.1`.
- MT5 price-point value per 1.00 lot: `100.0`.

## Decision

- Execution-model prototype gate pass: `True`.
- Interpretation: pass requires full-sample absolute direct-gap and matched-profit improvement without reducing matched/reliable coverage.
- This is not a final merge approval; residual full-sample PnL gap must still be decomposed.

## Decision Matrix

| scenario         | model      |   python_mt5_trades |   python_mt5_final_balance |   mt5_final_balance |   direct_gap |   abs_direct_gap |   matched_unique |   reliable_tier_matched |   relaxed_tier_matched |   python_unmatched |   mt5_unmatched |   matched_python_profit |   matched_mt5_profit |   matched_profit_diff |   abs_matched_profit_diff |   invalid_spec_rows | dynamic_dir                                                                                                  | mapping_dir                                                                                                  |   direct_gap_delta_vs_baseline |   abs_direct_gap_delta_vs_baseline |   matched_profit_diff_delta_vs_baseline |   abs_matched_profit_diff_delta_vs_baseline |   matched_unique_delta_vs_baseline |   reliable_tier_delta_vs_baseline |   relaxed_tier_delta_vs_baseline |
|:-----------------|:-----------|--------------------:|---------------------------:|--------------------:|-------------:|-----------------:|-----------------:|------------------------:|-----------------------:|-------------------:|----------------:|------------------------:|---------------------:|----------------------:|--------------------------:|--------------------:|:-------------------------------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------------|-------------------------------:|-----------------------------------:|----------------------------------------:|--------------------------------------------:|-----------------------------------:|----------------------------------:|---------------------------------:|
| metadatafix      | baseline   |                  98 |                    1969.91 |             3811.35 |    -1841.44  |         1841.44  |               57 |                      29 |                     28 |                 41 |              21 |                 543.301 |              2631.43 |              -2088.13 |                   2088.13 |                   2 | F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\dynamic_risk_alignment_shift90_metadatafix_close_retry_20260714 | F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\mapped_trade_alignment_shift90_metadatafix_close_retry_20260714 |                         nan    |                             nan    |                                  nan    |                                      nan    |                                nan |                               nan |                              nan |
| metadatafix      | exec_model |                  98 |                    4039.57 |             3811.35 |      228.222 |          228.222 |               57 |                      29 |                     28 |                 41 |              21 |                1348.56  |              2631.43 |              -1282.87 |                   1282.87 |                   2 | F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\dynamic_risk_alignment_exec_model_metadatafix_20260715          | F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\mapped_trade_alignment_exec_model_metadatafix_20260715          |                        2069.66 |                           -1613.21 |                                  805.26 |                                     -805.26 |                                  0 |                                 0 |                                0 |
| p0_subset_bridge | baseline   |                 100 |                    2077.66 |             3811.35 |    -1733.69  |         1733.69  |               59 |                      31 |                     28 |                 41 |              19 |                 601.391 |              2921.37 |              -2319.98 |                   2319.98 |                   2 | F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\dynamic_risk_alignment_p0_subset_bridge_20260715                | F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\mapped_trade_alignment_p0_subset_bridge_20260715                |                         nan    |                             nan    |                                  nan    |                                      nan    |                                nan |                               nan |                              nan |
| p0_subset_bridge | exec_model |                 100 |                    4433.96 |             3811.35 |      622.614 |          622.614 |               59 |                      31 |                     28 |                 41 |              19 |                1634.53  |              2921.37 |              -1286.84 |                   1286.84 |                   2 | F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\dynamic_risk_alignment_exec_model_p0_subset_bridge_20260715     | F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\mapped_trade_alignment_exec_model_p0_subset_bridge_20260715     |                        2356.3  |                           -1111.07 |                                 1033.13 |                                    -1033.13 |                                  0 |                                 0 |                                0 |

## P0 Target Rows

| model         | mt5_trade_id   | matched   | match_tier        | py_trade_id     |   py_profit |   mt5_profit |   profit_diff_py_minus_mt5 |   abs_profit_diff | py_stage_lots   |   abs_profit_diff_delta_vs_p0_baseline |
|:--------------|:---------------|:----------|:------------------|:----------------|------------:|-------------:|---------------------------:|------------------:|:----------------|---------------------------------------:|
| p0_baseline   | mt5_0005       | True      | exact_align90_all | python_mt5_0009 |     17.3329 |       161.09 |                 -143.757   |         143.757   | 0.01/0.01/0.02  |                                        |
| p0_baseline   | mt5_0019       | True      | exact_align90_all | python_mt5_0027 |     32.8569 |       128.85 |                  -95.9931  |          95.9931  | 0.01/0.02/0.04  |                                        |
| p0_exec_model | mt5_0005       | True      | exact_align90_all | python_mt5_0009 |    139.821  |       161.09 |                  -21.2692  |          21.2692  | 0.01/0.01/0.01  |                              -122.488  |
| p0_exec_model | mt5_0019       | True      | exact_align90_all | python_mt5_0027 |    127.628  |       128.85 |                   -1.22236 |           1.22236 | 0.01/0.01/0.01  |                               -94.7708 |

## Output Files

- `execution_model_decision_matrix.csv`
- `execution_model_p0_target_gap_summary.csv`
- `F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\dynamic_risk_alignment_exec_model_metadatafix_20260715`
- `F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\mapped_trade_alignment_exec_model_metadatafix_20260715`
- `F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\dynamic_risk_alignment_exec_model_p0_subset_bridge_20260715`
- `F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\mapped_trade_alignment_exec_model_p0_subset_bridge_20260715`
