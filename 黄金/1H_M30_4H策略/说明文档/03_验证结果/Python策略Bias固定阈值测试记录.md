# Python Bias 固定阈值网格测试记录

日期：2026-07-25

## 口径

- 阈值范围：`3.0%` 到 `6.0%`，每 `0.2%` 一档。
- 单项过滤：`bias5`、`bias13`、`bias55` 分别测试。
- 两两组合：`bias5+bias13`、`bias5+bias55`、`bias13+bias55`，同周期、同阈值同时满足。
- 过滤字段全部使用 `*_signed_pct`，不是 top30%，不是 abs。

## 最优摘要

| strategy | best_scope | timeframe | bias_fields | threshold_pct | raw_n | raw_pf | raw_test_pf | raw_test_ev | stage_n_after_stop | stage_pnl_usd | stage_test_pf | sample_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1H_M30_4H | single | 4h | bias55 | 3.2000 | 36 | 1.1433 | 0.2027 | -3.4815 | 21 | $13.69 | 0.0000 | ok |
| 1H_M30_4H | pair | 4h | bias13+bias55 | 3.0000 | 1 | 0.0000 | 0.0000 | -18.6070 | 0 | $0.00 | 0.0000 | insufficient |
| 2H_M30_6H | single | 6h | bias55 | 3.6000 | 115 | 1.9314 | 1.7904 | 15.1895 | 60 | $225.13 | 2.1311 | ok |
| 2H_M30_6H | pair | 6h | bias13+bias55 | 3.0000 | 6 | 3.0673 | 0.0000 | -50.6760 | 2 | $87.20 | 999.0000 | insufficient |

## 输出文件

- `1H_M30_4H`: `黄金/1H_M30_4H策略/data/validation/bias_threshold_grid/bias_threshold_grid_summary.csv`
- `1H_M30_4H`: `黄金/1H_M30_4H策略/data/validation/bias_threshold_grid/bias_threshold_grid_report.md`
- `2H_M30_6H`: `黄金/2H_M30_6H策略/data/validation/bias_threshold_grid/bias_threshold_grid_summary.csv`
- `2H_M30_6H`: `黄金/2H_M30_6H策略/data/validation/bias_threshold_grid/bias_threshold_grid_report.md`
