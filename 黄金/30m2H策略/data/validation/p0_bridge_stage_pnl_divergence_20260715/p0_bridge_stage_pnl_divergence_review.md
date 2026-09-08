# P0 bridge Stage/PnL divergence audit

## Scope

- Targets: `mt5_0005`, `mt5_0019`.
- This audit compares Python Stage replay / dynamic-risk valuation with MT5 close-retry trade ledger.
- MT5 net profit is used only as comparison evidence; no Python PnL is overwritten by ledger profit.

## Decision

- Signal recovery remains valid, but merge remains blocked.
- Primary reason: PnL is not on the same execution model.
- Python dynamic uses `VALUE_PER_SPEC_PT_PER_LOT=10.0` and dynamic stage lots.
- The two MT5 rows infer about `100` value per 1.0 price point per 1.00 lot and both execute `0.01/0.01/0.01` lots.
- The bridge rows also preserve a +90 aligned signal date, while MT5 actual opens are 90 minutes earlier than the bridge entry_time.

## Trade-Level Attribution

| mt5_trade_id   |   python_dynamic_total_$ |   mt5_net_profit |   net_gap_mt5_minus_python_dynamic |   contract_value_effect |   lot_sizing_effect |   exit_price_effect |   cost_effect |   contract_value_factor_mt5_over_py | py_stage_lots   | mt5_stage_lots   |   stage3_exit_time_delta_min_mt5_minus_py |
|:---------------|-------------------------:|-----------------:|-----------------------------------:|------------------------:|--------------------:|--------------------:|--------------:|------------------------------------:|:----------------|:-----------------|------------------------------------------:|
| mt5_0005       |                  17.3329 |           161.09 |                           143.757  |                 155.997 |            -33.5082 |            21.2683  |          0    |                             10.0001 | 0.01/0.01/0.02  | 0.01/0.01/0.01   |                                 -841.283  |
| mt5_0019       |                  32.8569 |           128.85 |                            95.9931 |                 295.737 |           -200.956  |             4.57271 |         -3.36 |                             10.0008 | 0.01/0.02/0.04  | 0.01/0.01/0.01   |                                  -57.3333 |

## Stage-Level Comparison

| mt5_trade_id   |   stage |   py_points |   mt5_price_points |   points_diff_mt5_minus_py |   py_stage_lot |   mt5_lot |   py_dynamic_$ |   mt5_net_profit |   net_gap_mt5_minus_py_dynamic | py_exit_reason   | mt5_local_exit_reason   | mt5_deal_reason   |
|:---------------|--------:|------------:|-------------------:|---------------------------:|---------------:|----------:|---------------:|-----------------:|-------------------------------:|:-----------------|:------------------------|:------------------|
| mt5_0005       |       1 |     66.983  |             67.007 |                    0.02404 |           0.01 |      0.01 |        6.6983  |            67.01 |                        60.3117 | 2.0R TP          | stage1_tp               | EXPERT            |
| mt5_0005       |       2 |     39.3298 |             40.992 |                    1.66217 |           0.01 |      0.01 |        3.93298 |            40.99 |                        37.057  | trail/SL hit     | deal_exit               | SL                |
| mt5_0005       |       3 |     33.508  |             53.09  |                   19.582   |           0.02 |      0.01 |        6.7016  |            53.09 |                        46.3884 | M30 merged cross | stage3_cross_exit       | EXPERT            |
| mt5_0019       |       1 |     39.1326 |             39.255 |                    0.1224  |           0.01 |      0.01 |        3.91326 |            38.78 |                        34.8667 | 2.0R TP          | stage1_tp               | EXPERT            |
| mt5_0019       |       2 |     32.272  |             32.995 |                    0.72296 |           0.02 |      0.01 |        6.45441 |            32.52 |                        26.0656 | trail/SL hit     | deal_exit               | SL                |
| mt5_0019       |       3 |     56.223  |             59.95  |                    3.727   |           0.04 |      0.01 |       22.4892  |            57.55 |                        35.0608 | M30 merged cross | stage3_cross_exit       | EXPERT            |

## Time/Lot Model Summary

| mt5_trade_id   | mt5_signal_anchor_time   | mt5_first_open_time   | bridge_entry_time   | py_date             |   mt5_open_minus_anchor_min |   bridge_entry_time_minus_mt5_open_min |   py_aligned_date_minus_mt5_open_min |
|:---------------|:-------------------------|:----------------------|:--------------------|:--------------------|----------------------------:|---------------------------------------:|-------------------------------------:|
| mt5_0005       | 2020-03-13 16:00:00      | 2020-03-13 15:45:06   | 2020-03-13 17:15:06 | 2020-03-13 17:30:00 |                      -14.9  |                                     90 |                               104.9  |
| mt5_0019       | 2020-08-04 17:30:00      | 2020-08-04 17:15:09   | 2020-08-04 18:45:09 | 2020-08-04 19:00:00 |                      -14.85 |                                     90 |                               104.85 |

## Scenario Matrix

| mt5_trade_id   | scenario                         |   profit_$ |   delta_from_previous |   gap_to_mt5_net |
|:---------------|:---------------------------------|-----------:|----------------------:|-----------------:|
| mt5_0005       | current_python_dynamic           |    17.3329 |                       |        143.757   |
| mt5_0005       | py_points_py_lots_at_mt5_value   |   173.33   |             155.997   |        -12.2399  |
| mt5_0005       | py_points_mt5_lots_at_mt5_value  |   139.822  |             -33.5082  |         21.2683  |
| mt5_0005       | mt5_points_mt5_lots_at_mt5_value |   161.09   |              21.2683  |          0       |
| mt5_0005       | mt5_net_profit_after_costs       |   161.09   |               0       |          0       |
| mt5_0019       | current_python_dynamic           |    32.8569 |                       |         95.9931  |
| mt5_0019       | py_points_py_lots_at_mt5_value   |   328.594  |             295.737   |       -199.744   |
| mt5_0019       | py_points_mt5_lots_at_mt5_value  |   127.637  |            -200.956   |          1.21271 |
| mt5_0019       | mt5_points_mt5_lots_at_mt5_value |   132.21   |               4.57271 |         -3.36    |
| mt5_0019       | mt5_net_profit_after_costs       |   128.85   |              -3.36    |          0       |

## Interpretation

- `contract_value_effect` shows what happens if Python's stage points and Python lots are revalued using MT5-inferred value per lot.
- `lot_sizing_effect` then changes Python dynamic lots to MT5 actual lots while keeping Python exit points.
- `exit_price_effect` then changes Python exit points to MT5 actual exit points while keeping MT5 lots.
- `cost_effect` is the remaining swap/commission/net-vs-gross difference.
- Therefore the next executable repair should not be another signal filter. It should be an execution-model gate: either align Python-MT5 valuation to MT5 tick/contract/lots for EA equivalence, or keep this subset as signal-only diagnostic under Python dynamic risk.

## Output Files

- `p0_bridge_stage_pnl_divergence.csv`
- `p0_bridge_trade_pnl_gap_attribution.csv`
- `p0_bridge_execution_scenario_matrix.csv`
- `p0_bridge_stage_pnl_divergence_review.md`