# Dynamic Risk Alignment - P0 subset bridge

## Summary

| source      |   trade_count |   final_balance |   dynamic_total_profit |   win_count |   win_rate_pct |   any_stage_sl_count |   all_stage_sl_count |   avg_stop_pts_spec |   avg_total_lot | source_variant                                |
|:------------|--------------:|----------------:|-----------------------:|------------:|---------------:|---------------------:|---------------------:|--------------------:|----------------:|:----------------------------------------------|
| python_only |           118 |         9585.57 |                9085.57 |          51 |        43.2203 |                   95 |                   44 |             15.6285 |        0.503475 | baseline                                      |
| python_mt5  |           100 |         2077.66 |                1577.66 |          47 |        47      |                   82 |                   33 |             15.3645 |        0.2372   | p0_subset_m15_slot1_data_axis_bridge_20260715 |
| mt5_ledger  |            78 |         3811.35 |                3311.35 |          33 |        42.3077 |                   72 |                   36 |             15.9843 |                 | mt5_full_close_retry_fix_20260714             |

## Exact Key Overlap

| source      |   shared |   python_only |   mt5_only |
|:------------|---------:|--------------:|-----------:|
| python_only |        0 |           118 |         78 |
| python_mt5  |        0 |           100 |         78 |
