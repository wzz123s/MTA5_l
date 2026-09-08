# Dynamic Risk Alignment - shift90 + ClosePos Retry

## Summary

| source      |   trade_count |   final_balance |   dynamic_total_profit |   win_count |   win_rate_pct |   any_stage_sl_count |   all_stage_sl_count |   avg_stop_pts_spec |   avg_total_lot | source_variant                    |
|:------------|--------------:|----------------:|-----------------------:|------------:|---------------:|---------------------:|---------------------:|--------------------:|----------------:|:----------------------------------|
| python_only |           118 |         9585.57 |               9085.57  |          51 |        43.2203 |                   95 |                   44 |             15.6285 |        0.503475 | baseline                          |
| python_mt5  |            90 |         1328.15 |                828.149 |          41 |        45.5556 |                   75 |                   31 |             14.7615 |        0.194111 | shift90_python_h2_context_q2early |
| mt5_ledger  |            78 |         3811.35 |               3311.35  |          33 |        42.3077 |                   72 |                   36 |             15.9843 |                 | mt5_full_close_retry_fix_20260714 |

## Exact Key Overlap

| source      |   shared |   python_only |   mt5_only |
|:------------|---------:|--------------:|-----------:|
| python_only |        0 |           118 |         78 |
| python_mt5  |        0 |            90 |         78 |

## Notes
- Python-MT5 uses `dynamic_risk_inputs_shift90_20260713`.
- MT5 ledger uses `mt5_full_close_retry_fix_20260714`.
- This output intentionally does not overwrite prior shift90 alignment snapshots.
