# Python 策略方向测试记录

日期：2026-07-25

## 汇总

| strategy | primary_variant | best_filter | best_desc | stage_trades_after_stop | stage_pnl_usd | stage_pf | stage_test_pf | positive_years | total_years |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1H_M30_4H | 1H_M30_4H__1h_dir_align | 4h_dir_against | 4H 方向反向 | 79 | $28.84 | 2.1901 | 1.4688 | 3 | 4 |
| 2H_M30_6H | 2H_M30_6H__6h_bias5_13_55_signed_pos | buy_only | 只做 BUY/LONG | 135 | $128.12 | 2.7610 | 4.0985 | 3 | 3 |

## 输出文件

- `1H_M30_4H`: `黄金/1H_M30_4H策略/data/validation/direction_test/direction_filter_summary.csv`
- `1H_M30_4H`: `黄金/1H_M30_4H策略/data/validation/direction_test/direction_yearly_summary.csv`
- `1H_M30_4H`: `黄金/1H_M30_4H策略/data/validation/direction_test/direction_test_report.md`
- `2H_M30_6H`: `黄金/2H_M30_6H策略/data/validation/direction_test/direction_filter_summary.csv`
- `2H_M30_6H`: `黄金/2H_M30_6H策略/data/validation/direction_test/direction_yearly_summary.csv`
- `2H_M30_6H`: `黄金/2H_M30_6H策略/data/validation/direction_test/direction_test_report.md`

## 解释

本测试只使用 Python 研究数据，目的是先判断策略方向和高周期方向门是否有收益倾向。它不代表 EA 已经对齐或可以部署。
