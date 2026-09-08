# Stage Exit Rule Alignment Review - shift90

## Scope

- 输入样本：`matched_profit_exit_diff_shift90_20260713/matched_profit_exit_diff_details.csv` 中 `primary_diff_class = stage_exit_detail_diff` 的 18 笔。
- 展开口径：每笔拆成 Stage1/Stage2/Stage3，共 54 行 stage 明细。
- 回补字段：Python stage exit/profit/lot，MT5 local_exit_reason/deal_reason/net_profit/lot/exit_price。

## Exit Relation Summary

|   stage | exit_relation                      |   rows |
|--------:|:-----------------------------------|-------:|
|       1 | both_initial_sl                    |      3 |
|       1 | mt5_expert_close_other             |      2 |
|       1 | py_tp_mt5_expert_close             |      6 |
|       1 | py_tp_mt5_sl                       |      7 |
|       2 | both_stop_or_trail                 |     10 |
|       2 | mt5_expert_close_other             |      1 |
|       2 | py_cross_mt5_sl                    |      2 |
|       2 | py_forced_mt5_sl                   |      5 |
|       3 | both_cross_but_price_time_may_diff |      6 |
|       3 | both_initial_sl                    |      8 |
|       3 | mt5_expert_close_other             |      1 |
|       3 | py_cross_mt5_sl                    |      3 |

## Direction Summary

| dir_norm   |   rows |
|:-----------|-------:|
| SELL       |     18 |

## Stage / Python Exit / MT5 Deal Summary

|   stage | py_exit          | mt5_deal_reason   | mt5_local_exit_reason   |   rows |
|--------:|:-----------------|:------------------|:------------------------|-------:|
|       1 | 2.0R TP          | EXPERT            | stage1_tp               |      6 |
|       1 | 2.0R TP          | SL                | deal_exit               |      6 |
|       1 | 2.0R TP          | SL                | stage1_tp               |      1 |
|       1 | SL hit           | EXPERT            | stage1_tp               |      2 |
|       1 | SL hit           | SL                | deal_exit               |      3 |
|       2 | 4.0R forced      | SL                | deal_exit               |      5 |
|       2 | M30 merged cross | SL                | deal_exit               |      2 |
|       2 | trail/SL hit     | EXPERT            | stage2_forced           |      1 |
|       2 | trail/SL hit     | SL                | deal_exit               |     10 |
|       3 | M30 merged cross | EXPERT            | stage3_cross_exit       |      6 |
|       3 | M30 merged cross | SL                | deal_exit               |      3 |
|       3 | SL hit           | EXPERT            | stage3_cross_exit       |      1 |
|       3 | SL hit           | SL                | deal_exit               |      8 |

## Sign Pair Summary

|   stage | sign_pair   | exit_relation                      |   rows |
|--------:|:------------|:-----------------------------------|-------:|
|       1 | loss->loss  | both_initial_sl                    |      3 |
|       1 | loss->win   | mt5_expert_close_other             |      2 |
|       1 | win->loss   | py_tp_mt5_sl                       |      7 |
|       1 | win->win    | py_tp_mt5_expert_close             |      6 |
|       2 | loss->loss  | both_stop_or_trail                 |      4 |
|       2 | loss->loss  | py_cross_mt5_sl                    |      1 |
|       2 | loss->win   | py_cross_mt5_sl                    |      1 |
|       2 | win->loss   | both_stop_or_trail                 |      3 |
|       2 | win->loss   | py_forced_mt5_sl                   |      5 |
|       2 | win->win    | both_stop_or_trail                 |      3 |
|       2 | win->win    | mt5_expert_close_other             |      1 |
|       3 | loss->loss  | both_cross_but_price_time_may_diff |      1 |
|       3 | loss->loss  | both_initial_sl                    |      8 |
|       3 | loss->win   | both_cross_but_price_time_may_diff |      1 |
|       3 | loss->win   | mt5_expert_close_other             |      1 |
|       3 | win->loss   | both_cross_but_price_time_may_diff |      1 |
|       3 | win->loss   | py_cross_mt5_sl                    |      3 |
|       3 | win->win    | both_cross_but_price_time_may_diff |      3 |

## Lot Ratio Summary

|   stage | stage_lot_ratio_bucket   |   rows |
|--------:|:-------------------------|-------:|
|       1 | <=1.5x                   |      6 |
|       1 | <=10x                    |      3 |
|       1 | <=3x                     |      5 |
|       1 | <=5x                     |      3 |
|       1 | >10x                     |      1 |
|       2 | <=10x                    |      5 |
|       2 | <=3x                     |      6 |
|       2 | <=5x                     |      4 |
|       2 | >10x                     |      3 |
|       3 | <=10x                    |      5 |
|       3 | <=3x                     |      5 |
|       3 | <=5x                     |      2 |
|       3 | >10x                     |      6 |

## Numeric Summary

|   stage | py_exit          | mt5_deal_reason   |   rows |   avg_stage_profit_diff |   max_abs_stage_profit_diff |   avg_py_lot |   avg_mt5_lot |   avg_lot_ratio |
|--------:|:-----------------|:------------------|-------:|------------------------:|----------------------------:|-------------:|--------------:|----------------:|
|       1 | 2.0R TP          | SL                |      7 |                23.642   |                     36.4821 |    0.0614286 |     0.01      |         6.14286 |
|       1 | 2.0R TP          | EXPERT            |      6 |               -42.0734  |                     74.671  |    0.0283333 |     0.01      |         2.83333 |
|       1 | SL hit           | SL                |      3 |                20.4522  |                     22.1169 |    0.0133333 |     0.01      |         1.33333 |
|       1 | SL hit           | EXPERT            |      2 |               -45.4407  |                     55.6834 |    0.02      |     0.01      |         2       |
|       2 | trail/SL hit     | SL                |     10 |                 3.81386 |                     29.5266 |    0.055     |     0.011     |         4.6     |
|       2 | 4.0R forced      | SL                |      5 |                63.6065  |                     80.7123 |    0.146     |     0.01      |        14.6     |
|       2 | M30 merged cross | SL                |      2 |                -7.4848  |                     34.01   |    0.045     |     0.01      |         4.5     |
|       2 | trail/SL hit     | EXPERT            |      1 |               -44.2377  |                     44.2377 |    0.03      |     0.01      |         3       |
|       3 | SL hit           | SL                |      8 |                 5.5584  |                     20.9198 |    0.13125   |     0.01375   |        10.5     |
|       3 | M30 merged cross | EXPERT            |      6 |               -37.0608  |                    104.624  |    0.045     |     0.0116667 |         4.08333 |
|       3 | M30 merged cross | SL                |      3 |               100.395   |                    208.681  |    0.233333  |     0.0133333 |        15.8333  |
|       3 | SL hit           | EXPERT            |      1 |               -65.1094  |                     65.1094 |    0.08      |     0.01      |         8       |

## Top Stage Profit Differences

| py_trade_id     | mt5_trade_id   | py_date             | dir_norm   |   stage | py_exit          | mt5_local_exit_reason   | mt5_deal_reason   |   py_stage_profit |   mt5_stage_profit |   stage_profit_diff |   py_stage_lot |   mt5_stage_lot |   stage_lot_ratio_py_over_mt5 |   mt5_exit_price | deal_comment   | exit_relation                      |
|:----------------|:---------------|:--------------------|:-----------|--------:|:-----------------|:------------------------|:------------------|------------------:|-------------------:|--------------------:|---------------:|----------------:|------------------------------:|-----------------:|:---------------|:-----------------------------------|
| python_mt5_0063 | mt5_0046       | 2025-04-22 10:30:00 | SELL       |       3 | M30 merged cross | deal_exit               | SL                |         194.511   |             -14.17 |            208.681  |           0.15 |            0.01 |                          15   |          3458.2  | sl 3458.183    | py_cross_mt5_sl                    |
| python_mt5_0074 | mt5_0056       | 2025-10-17 14:30:00 | SELL       |       3 | M30 merged cross | stage3_cross_exit       | EXPERT            |          18.716   |             123.34 |           -104.624  |           0.05 |            0.02 |                           2.5 |          4252.64 | nan            | both_cross_but_price_time_may_diff |
| python_mt5_0084 | mt5_0062       | 2026-01-26 22:00:00 | SELL       |       2 | 4.0R forced      | deal_exit               | SL                |          72.8523  |              -7.86 |             80.7123 |           0.13 |            0.01 |                          13   |          5057.85 | sl 5057.824    | py_forced_mt5_sl                   |
| python_mt5_0082 | mt5_0061       | 2026-01-26 20:30:00 | SELL       |       2 | 4.0R forced      | deal_exit               | SL                |          64.5628  |             -14.83 |             79.3928 |           0.3  |            0.01 |                          30   |          5079.2  | sl 5079.185    | py_forced_mt5_sl                   |
| python_mt5_0083 | mt5_0067       | 2026-01-26 21:00:00 | SELL       |       2 | 4.0R forced      | deal_exit               | SL                |          68.8689  |              -9.82 |             78.6889 |           0.16 |            0.01 |                          16   |          4684.47 | sl 4684.454    | py_forced_mt5_sl                   |
| python_mt5_0064 | mt5_0047       | 2025-04-22 16:00:00 | SELL       |       1 | 2.0R TP          | stage1_tp               | EXPERT            |           6.12899 |              80.8  |            -74.671  |           0.01 |            0.01 |                           1   |          3337.73 | nan            | py_tp_mt5_expert_close             |
| python_mt5_0064 | mt5_0047       | 2025-04-22 16:00:00 | SELL       |       3 | M30 merged cross | stage3_cross_exit       | EXPERT            |          33.6292  |             103.12 |            -69.4908 |           0.04 |            0.01 |                           4   |          3315.41 | nan            | both_cross_but_price_time_may_diff |
| python_mt5_0082 | mt5_0061       | 2026-01-26 20:30:00 | SELL       |       3 | M30 merged cross | deal_exit               | SL                |          36.6435  |             -29.66 |             66.3035 |           0.45 |            0.02 |                          22.5 |          5079.2  | sl 5079.185    | py_cross_mt5_sl                    |
| python_mt5_0087 | mt5_0071       | 2026-03-24 02:00:00 | SELL       |       3 | SL hit           | stage3_cross_exit       | EXPERT            |         -23.2994  |              41.81 |            -65.1094 |           0.08 |            0.01 |                           8   |          4336.2  | nan            | mt5_expert_close_other             |
| python_mt5_0030 | mt5_0023       | 2021-06-18 16:00:00 | SELL       |       1 | SL hit           | stage1_tp               | EXPERT            |          -2.1134  |              53.57 |            -55.6834 |           0.02 |            0.01 |                           2   |          1757.78 | nan            | mt5_expert_close_other             |
| python_mt5_0024 | mt5_0016       | 2020-07-28 08:30:00 | SELL       |       2 | 4.0R forced      | deal_exit               | SL                |          23.7388  |             -29.08 |             52.8188 |           0.08 |            0.01 |                           8   |          1943.37 | sl 1943.356    | py_forced_mt5_sl                   |
| python_mt5_0087 | mt5_0071       | 2026-03-24 02:00:00 | SELL       |       1 | 2.0R TP          | stage1_tp               | EXPERT            |          11.6497  |              57.6  |            -45.9503 |           0.02 |            0.01 |                           2   |          4320.41 | nan            | py_tp_mt5_expert_close             |
| python_mt5_0074 | mt5_0056       | 2025-10-17 14:30:00 | SELL       |       2 | trail/SL hit     | stage2_forced           | EXPERT            |          11.5223  |              55.76 |            -44.2377 |           0.03 |            0.01 |                           3   |          4258.55 | nan            | mt5_expert_close_other             |
| python_mt5_0036 | mt5_0030       | 2022-03-09 11:30:00 | SELL       |       1 | 2.0R TP          | stage1_tp               | EXPERT            |           4.68717 |              46.31 |            -41.6228 |           0.01 |            0.01 |                           1   |          1971.66 | nan            | py_tp_mt5_expert_close             |
| python_mt5_0084 | mt5_0062       | 2026-01-26 22:00:00 | SELL       |       1 | 2.0R TP          | stage1_tp               | SL                |          16.8121  |             -19.67 |             36.4821 |           0.06 |            0.01 |                           6   |          5069.66 | sl 5069.662    | py_tp_mt5_sl                       |
| python_mt5_0030 | mt5_0023       | 2021-06-18 16:00:00 | SELL       |       3 | M30 merged cross | stage3_cross_exit       | EXPERT            |          -2.72    |              33.41 |            -36.13   |           0.08 |            0.01 |                           8   |          1777.93 | nan            | both_cross_but_price_time_may_diff |
| python_mt5_0083 | mt5_0067       | 2026-01-26 21:00:00 | SELL       |       1 | 2.0R TP          | stage1_tp               | EXPERT            |          17.2172  |              53.31 |            -36.0928 |           0.08 |            0.01 |                           8   |          4621.34 | nan            | py_tp_mt5_expert_close             |
| python_mt5_0086 | mt5_0066       | 2026-02-02 17:00:00 | SELL       |       1 | SL hit           | stage1_tp               | EXPERT            |          -8.53799 |              26.66 |            -35.198  |           0.02 |            0.01 |                           2   |          4670.59 | nan            | mt5_expert_close_other             |
| python_mt5_0024 | mt5_0016       | 2020-07-28 08:30:00 | SELL       |       1 | 2.0R TP          | deal_exit               | SL                |           5.9347  |             -29.08 |             35.0147 |           0.04 |            0.01 |                           4   |          1943.37 | sl 1943.356    | py_tp_mt5_sl                       |
| python_mt5_0030 | mt5_0023       | 2021-06-18 16:00:00 | SELL       |       2 | M30 merged cross | deal_exit               | SL                |          -1.7     |              32.31 |            -34.01   |           0.05 |            0.01 |                           5   |          1779.04 | sl 1779.020    | py_cross_mt5_sl                    |

## Source Rule Comparison

- Python `scripts/_stage12_combo_test.py:93-155`：Stage1/Stage2/Stage3 以 M30 bar 的 high/low/close 回放；Stage1 先判 SL 再判 2.0R TP；Stage2 先判 4.0R forced，再判 trail_sl 命中，再更新 SMA13 trail；Stage3 先判 SL，再在 M30 merged direction flip 的 close 出场。
- EA `auto_trade/30m2H_Strategy_EA.mq5:1389-1445`：Stage1/2 在 tick 上用 `rr` 管理；Stage1 到 2.0R 即 `ClosePos`；Stage2 到 4.0R 即 `ClosePos`，到 1.5R 后只修改 broker SL 到 SMA13，实际 trail exit 多数会表现为 deal reason `SL`。
- EA `auto_trade/30m2H_Strategy_EA.mq5:2540-2562`：Stage1/2 当前把 `SYMBOL_BID` 缓存为统一 `cur_price` 传入 `CheckStageExit`。SELL 持仓的平仓/盈利阈值通常应以 ASK 侧确认，这是下一步必须 smoke 验证的强嫌疑点。
- EA `auto_trade/30m2H_Strategy_EA.mq5:2577-2612`：Stage3 用 M30 SMA5/SMA13 buffer 在 tick 上检测 cross 后市价平仓；Python Stage3 是 M30 merged direction flip close 出场。两者同名但不是完全同一价格源/时点。
- EA `auto_trade/30m2H_Strategy_EA.mq5:1465-1540`：动态手数按真实账户余额、真实 stop_pts 和交易品种 tick value 计算；Python 动态风险按模拟资金曲线重算。只要前序 PnL 不同，后续 stage lots 会继续分叉。

## Current Decision

- 不建议继续扩大 signal mapping 或 M15 parent filter；Stage exit 明细已经成为当前 PnL 残差主线。
- 本次 `stage_exit_detail_diff` 的 18 笔全部是 SELL；下一步不应做全局 Stage 行为大改，应先验证 SELL 的 price-side 和出场时点。
- 下一步优先做 EA Stage1/2 price-side smoke：按 BUY/SELL 分别记录 `bid/ask/current_price/rr/action/local_exit_reason`，验证 SELL 使用 BID 是否导致提前 TP/forced/trail-on。
- Stage2 trailing 不宜直接按 Python `trail/SL hit` 等价 MT5 `SL`；需要补 ledger 字段记录 trail_on、SMA13 trail SL、修改时间，才能判断是规则差异还是记录口径差异。
- 资金曲线对齐前，应先把 Python runtime-style Stage exit 改成更接近 EA tick/broker SL 模型，或把 EA ledger 诊断字段补齐后再决定是否改 EA 行为。

## Output Files

- `stage_exit_rule_alignment_stage_rows.csv`
- `stage_exit_rule_alignment_exit_relation_summary.csv`
- `stage_exit_rule_alignment_stage_exit_deal_summary.csv`
- `stage_exit_rule_alignment_sign_pair_summary.csv`
- `stage_exit_rule_alignment_lot_ratio_summary.csv`
- `stage_exit_rule_alignment_numeric_summary.csv`
- `stage_exit_rule_alignment_top_stage_diffs.csv`
