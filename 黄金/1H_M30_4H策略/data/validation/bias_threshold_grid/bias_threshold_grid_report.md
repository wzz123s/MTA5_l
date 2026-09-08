# 1H_M30_4H Bias 阈值网格测试

- 阈值：`3.0%` 到 `6.0%`，步长 `0.2%`。
- 字段：`bias5_signed_pct`、`bias13_signed_pct`、`bias55_signed_pct`。
- 两两组合：同一周期内两个 bias 字段同时大于等于同一阈值。
- 排名：优先 raw 测试 PF；同时保留当前 StopSpec 后 stage 估算收益。

## 单项 Top

| timeframe | bias_fields | threshold_pct | raw_n | raw_pf | raw_test_pf | raw_test_ev | stage_n_after_stop | stage_pnl_usd | stage_test_pf |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4h | bias55 | 3.2000 | 36 | 1.1433 | 0.2027 | -3.4815 | 21 | $13.69 | 0.0000 |
| 4h | bias55 | 3.0000 | 47 | 0.9610 | 0.1008 | -4.3081 | 30 | $12.69 | 0.0000 |

## 两两组合 Top

| timeframe | bias_fields | threshold_pct | raw_n | raw_pf | raw_test_pf | raw_test_ev | stage_n_after_stop | stage_pnl_usd | stage_test_pf |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4h | bias13+bias55 | 3.0000 | 1 | 0.0000 | 0.0000 | -18.6070 | 0 | $0.00 | 0.0000 |
| 30m | bias5+bias13 | 3.0000 | 0 | 0.0000 | 0.0000 | 0.0000 | 0 | $0.00 | 0.0000 |
| 30m | bias5+bias55 | 3.0000 | 0 | 0.0000 | 0.0000 | 0.0000 | 0 | $0.00 | 0.0000 |
| 30m | bias13+bias55 | 3.0000 | 0 | 0.0000 | 0.0000 | 0.0000 | 0 | $0.00 | 0.0000 |
| 30m | bias5+bias13 | 3.2000 | 0 | 0.0000 | 0.0000 | 0.0000 | 0 | $0.00 | 0.0000 |
| 30m | bias5+bias55 | 3.2000 | 0 | 0.0000 | 0.0000 | 0.0000 | 0 | $0.00 | 0.0000 |
| 30m | bias13+bias55 | 3.2000 | 0 | 0.0000 | 0.0000 | 0.0000 | 0 | $0.00 | 0.0000 |
| 30m | bias5+bias13 | 3.4000 | 0 | 0.0000 | 0.0000 | 0.0000 | 0 | $0.00 | 0.0000 |
