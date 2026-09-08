# Dynamic Risk Alignment - execution model normalization (p0_subset_bridge)

## Summary

| source      |   trade_count |   final_balance |   dynamic_total_profit |   win_count |   win_rate_pct |   any_stage_sl_count |   all_stage_sl_count |   avg_stop_pts_spec |   avg_total_lot | exec_model                  | source_variant                          |
|:------------|--------------:|----------------:|-----------------------:|------------:|---------------:|---------------------:|---------------------:|--------------------:|----------------:|:----------------------------|:----------------------------------------|
| python_only |           118 |        23366.4  |               22866.4  |          54 |        45.7627 |                   95 |                   44 |             15.6285 |        0.114831 | mt5_value_stage_lots_parity | p0_subset_bridge_python_only_exec_model |
| python_mt5  |           100 |         4433.96 |                3933.96 |          50 |        50      |                   82 |                   33 |             15.3645 |        0.0438   | mt5_value_stage_lots_parity | exec_model_p0_subset_bridge_20260715    |
| mt5_ledger  |            78 |         3811.35 |                3311.35 |          33 |        42.3077 |                   72 |                   36 |             15.9843 |                 | mt5_ledger_reference        | mt5_full_close_retry_fix_20260714       |

## Exact Key Overlap

| source      |   shared |   python_only |   mt5_only |
|:------------|---------:|--------------:|-----------:|
| python_only |        0 |           118 |         78 |
| python_mt5  |        0 |           100 |         78 |

## Notes

- This is a non-destructive prototype.
- MT5 tick value per 1.00 lot: `0.1`.
- MT5 price-point value per 1.00 lot: `100.0`.
- Stage lots follow EA CalcLot()/StageLots() approximation.
