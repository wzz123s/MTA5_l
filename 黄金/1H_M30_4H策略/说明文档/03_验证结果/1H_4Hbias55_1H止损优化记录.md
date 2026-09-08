# 1H_M30_4H 4H bias55 base + 1H止损优化

日期：2026-07-25

## 口径

- 第一层固定条件：`4h_bias55_signed_pct >= 2.0`。
- 信号：M30 SMA5/SMA13 交叉，M30 收盘确认，下一根 M30 开盘入场。
- 止损：只使用入场前已收盘的 1H 数据，不再使用 M30 SMA13 止损。
- 回放：入场后逐根 M30 K 线检查止损，未止损则下一次反向 M30 交叉确认后的下一根 M30 开盘退出。
- 收益：`pnl_points * 100 * 0.01 lot`，未扣点差、滑点、手续费。

## 1H止损定义对比

| stop_variant | n | pf | test_pf | pnl_usd_001 | stop_hits | stop_hit_rate_pct | avg_stop_distance | median_stop_distance | positive_years | total_years |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| h1_dir_segment_hilo | 183 | 0.9196 | 1.1698 | $-69.61 | 18 | 9.8361 | 32.3731 | 19.4740 | 2 | 4 |
| h1_last6_hilo | 183 | 0.9612 | 1.1293 | $-32.31 | 33 | 18.0328 | 11.4889 | 9.8170 | 2 | 4 |
| h1_last3_hilo | 183 | 0.8706 | 0.7063 | $-107.06 | 54 | 29.5082 | 9.2671 | 7.8610 | 1 | 4 |
| h1_last1_hilo | 183 | 0.8062 | 0.7869 | $-142.79 | 104 | 56.8306 | 6.5099 | 5.3130 | 0 | 4 |
| h1_dir_segment_sma13 | 179 | 0.7469 | 0.7978 | $-185.43 | 67 | 37.4302 | 28.2311 | 11.8500 | 0 | 4 |

## 第二层过滤 Top

| stop_variant | filter | n | pf | test_pf | pnl_usd_001 | stop_hits | stop_hit_rate_pct | avg_stop_distance | positive_years | total_years | sample_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| h1_last6_hilo | base_1h_dir_against | 68 | 1.1732 | 1.4543 | $49.96 | 10 | 14.7059 | 12.2959 | 2 | 4 | ok |
| h1_dir_segment_hilo | base_1h_dir_against | 68 | 1.1385 | 1.4543 | $41.19 | 7 | 10.2941 | 14.4186 | 2 | 4 | ok |
| h1_dir_segment_hilo | base_1h_bias55_pos | 182 | 0.9333 | 1.1698 | $-56.85 | 18 | 9.8901 | 32.3962 | 2 | 4 | ok |
| h1_last6_hilo | base_1h_bias55_pos | 182 | 0.9762 | 1.1293 | $-19.54 | 33 | 18.1319 | 11.3973 | 2 | 4 | ok |
| h1_dir_segment_hilo | base | 183 | 0.9196 | 1.1698 | $-69.61 | 18 | 9.8361 | 32.3731 | 2 | 4 | ok |
| h1_last6_hilo | base | 183 | 0.9612 | 1.1293 | $-32.31 | 33 | 18.0328 | 11.4889 | 2 | 4 | ok |
| h1_last3_hilo | base_1h_dir_against | 68 | 1.0853 | 1.0485 | $23.90 | 23 | 33.8235 | 9.1017 | 2 | 4 | ok |
| h1_last6_hilo | base_1h_bias5_pos | 161 | 0.9615 | 1.0944 | $-29.79 | 27 | 16.7702 | 12.2259 | 2 | 4 | ok |
| h1_dir_segment_hilo | base_1h_bias5_pos | 161 | 0.9179 | 1.1290 | $-66.03 | 17 | 10.5590 | 32.0177 | 2 | 4 | ok |
| h1_last1_hilo | base_1h_dir_against | 68 | 0.8356 | 1.2675 | $-39.16 | 45 | 66.1765 | 5.7269 | 1 | 4 | ok |
| h1_last6_hilo | base_buy_only | 117 | 0.9863 | 1.0145 | $-7.61 | 21 | 17.9487 | 11.6980 | 2 | 4 | ok |
| h1_dir_segment_hilo | base_buy_only | 117 | 0.9455 | 1.0190 | $-31.64 | 9 | 7.6923 | 32.4461 | 2 | 4 | ok |

## 输出文件

- `h1_stop_all_replay_trades.csv`
- `h1_stop_base_summary.csv`
- `h1_stop_second_filter_summary.csv`
