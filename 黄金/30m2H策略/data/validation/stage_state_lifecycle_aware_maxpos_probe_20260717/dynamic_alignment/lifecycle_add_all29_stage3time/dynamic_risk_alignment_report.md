# Dynamic Risk Alignment - execution model normalization (lifecycle_add_all29_stage3time)

## Summary

| source      |   trade_count |   final_balance |   dynamic_total_profit |   win_count |   win_rate_pct |   any_stage_sl_count |   all_stage_sl_count |   avg_stop_pts_spec |   avg_total_lot | exec_model                  | source_variant                                               |
|:------------|--------------:|----------------:|-----------------------:|------------:|---------------:|---------------------:|---------------------:|--------------------:|----------------:|:----------------------------|:-------------------------------------------------------------|
| python_only |           118 |        23366.4  |               22866.4  |          54 |        45.7627 |                   95 |                   44 |             15.6285 |        0.114831 | mt5_value_stage_lots_parity | lifecycle_add_all29_stage3time_python_only_exec_model        |
| python_mt5  |           117 |         7523.08 |                7023.08 |          52 |        44.4444 |                   95 |                   43 |             14.7058 |        0.069658 | mt5_value_stage_lots_parity | layer3_m15_slot1_postn_rescue_lifecycle_add_all29_stage3time |
| mt5_ledger  |            82 |         1649.84 |                1149.84 |          33 |        40.2439 |                   75 |                   40 |             16.1702 |                 | mt5_ledger_reference        | mt5_full_close_retry_fix_20260714                            |

## Exact Key Overlap

| source      |   shared |   python_only |   mt5_only |
|:------------|---------:|--------------:|-----------:|
| python_only |        0 |           118 |         82 |
| python_mt5  |        0 |           117 |         82 |

## Notes

- This is a non-destructive prototype.
- MT5 tick value per 1.00 lot: `0.1`.
- MT5 price-point value per 1.00 lot: `100.0`.
- Stage lots follow EA CalcLot()/StageLots() approximation.
