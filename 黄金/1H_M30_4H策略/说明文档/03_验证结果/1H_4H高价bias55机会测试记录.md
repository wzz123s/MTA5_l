# 1H_M30_4H 4H高价bias55反向机会测试

> 注意：本文件是固定区间 `2%-6%` 的对照测试。
> 当前主线已改为无上限机会池：`bias55>=2%` 做空、`bias55<=-2%` 做多，详见 `1H_4H高价bias机会池测试记录.md`。

日期：2026-07-25

## 口径

- 将 4H 拆成最近 4 根已收盘 H1 K 线。
- 取这 4 根 H1 的最高价，计算 high-price bias55。
- 做空机会：bias55 在 `+2%` 到 `+6%` 之间，只接 M30 空信号。
- 做多机会：bias55 在 `-6%` 到 `-2%` 之间，只接 M30 多信号。
- 入场：M30 SMA5/SMA13 交叉收盘确认，下一根 M30 开盘。
- 止损：仍使用 1H 结构止损候选。
- 收益：`pnl_points * 100 * 0.01 lot`，未扣点差、滑点、手续费。

## 固定 2%-6% 区间

| stop_variant | feature | lower_pct | upper_pct | n | long_n | short_n | pf | test_pf | pnl_usd_001 | stop_hits | stop_hit_rate_pct | avg_stop_distance | positive_years | total_years | sample_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| h1_dir_segment_hilo | h1roll4_high_bias55_h4sma_pct | 2.0000 | 6.0000 | 262 | 76 | 186 | 1.1607 | 0.8990 | $182.58 | 18 | 6.8702 | 15.8904 | 2 | 4 | ok |
| h1_last3_hilo | h1roll4_high_bias55_h4sma_pct | 2.0000 | 6.0000 | 262 | 76 | 186 | 1.1256 | 0.8728 | $142.86 | 66 | 25.1908 | 10.2576 | 1 | 4 | ok |
| h1_last6_hilo | h1roll4_high_bias55_h4sma_pct | 2.0000 | 6.0000 | 262 | 76 | 186 | 1.1428 | 0.8364 | $163.60 | 37 | 14.1221 | 12.1503 | 1 | 4 | ok |
| h1_last3_hilo | h1roll4_high_bias55_h1sma_pct | 2.0000 | 6.0000 | 55 | 12 | 43 | 0.4841 | 0.7599 | $-193.79 | 13 | 23.6364 | 16.1476 | 0 | 4 | ok |
| h1_last6_hilo | h1roll4_high_bias55_h1sma_pct | 2.0000 | 6.0000 | 55 | 12 | 43 | 0.4811 | 0.7403 | $-196.13 | 4 | 7.2727 | 19.9334 | 0 | 4 | ok |
| h1_dir_segment_hilo | h1roll4_high_bias55_h1sma_pct | 2.0000 | 6.0000 | 55 | 12 | 43 | 0.4909 | 0.7277 | $-188.56 | 0 | 0.0000 | 27.5960 | 0 | 4 | ok |

## Lower 阈值扫描 Top

| stop_variant | feature | lower_pct | upper_pct | n | long_n | short_n | pf | test_pf | pnl_usd_001 | stop_hits | stop_hit_rate_pct | avg_stop_distance | positive_years | total_years | sample_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| h1_last3_hilo | h1roll4_high_bias55_h4sma_pct | 4.0000 | 6.0000 | 34 | 6 | 28 | 2.0416 | 2.6357 | $177.22 | 7 | 20.5882 | 14.3205 | 2 | 4 | ok |
| h1_last3_hilo | h1roll4_high_bias55_h4sma_pct | 3.8000 | 6.0000 | 35 | 7 | 28 | 1.9389 | 2.6357 | $168.21 | 7 | 20.0000 | 14.3729 | 2 | 4 | ok |
| h1_last6_hilo | h1roll4_high_bias55_h4sma_pct | 4.0000 | 6.0000 | 34 | 6 | 28 | 2.0308 | 2.5357 | $176.31 | 2 | 5.8824 | 17.9582 | 2 | 4 | ok |
| h1_last6_hilo | h1roll4_high_bias55_h4sma_pct | 3.8000 | 6.0000 | 35 | 7 | 28 | 1.9292 | 2.5357 | $167.30 | 2 | 5.7143 | 17.9067 | 2 | 4 | ok |
| h1_dir_segment_hilo | h1roll4_high_bias55_h4sma_pct | 4.0000 | 6.0000 | 34 | 6 | 28 | 2.0042 | 2.3946 | $174.04 | 1 | 2.9412 | 24.7707 | 2 | 4 | ok |
| h1_dir_segment_hilo | h1roll4_high_bias55_h4sma_pct | 3.8000 | 6.0000 | 35 | 7 | 28 | 1.9052 | 2.3946 | $165.03 | 1 | 2.8571 | 24.5285 | 2 | 4 | ok |
| h1_last3_hilo | h1roll4_high_bias55_h4sma_pct | 3.6000 | 6.0000 | 45 | 11 | 34 | 1.7849 | 1.8269 | $178.67 | 9 | 20.0000 | 13.7624 | 2 | 4 | ok |
| h1_last6_hilo | h1roll4_high_bias55_h4sma_pct | 3.6000 | 6.0000 | 45 | 11 | 34 | 1.7678 | 1.7783 | $176.46 | 3 | 6.6667 | 17.5043 | 2 | 4 | ok |
| h1_dir_segment_hilo | h1roll4_high_bias55_h4sma_pct | 3.6000 | 6.0000 | 45 | 11 | 34 | 1.7505 | 1.7077 | $174.19 | 2 | 4.4444 | 23.0440 | 2 | 4 | ok |
| h1_last6_hilo | h1roll4_high_bias55_h4sma_pct | 2.4000 | 6.0000 | 206 | 54 | 152 | 1.2534 | 1.0812 | $225.47 | 24 | 11.6505 | 12.5722 | 3 | 4 | ok |
| h1_last3_hilo | h1roll4_high_bias55_h4sma_pct | 2.4000 | 6.0000 | 206 | 54 | 152 | 1.2079 | 1.1121 | $186.96 | 47 | 22.8155 | 10.6621 | 3 | 4 | ok |
| h1_dir_segment_hilo | h1roll4_high_bias55_h4sma_pct | 2.4000 | 6.0000 | 206 | 54 | 152 | 1.2563 | 1.0527 | $227.51 | 10 | 4.8544 | 16.7229 | 3 | 4 | ok |
| h1_dir_segment_hilo | h1roll4_high_bias55_h4sma_pct | 2.2000 | 6.0000 | 233 | 66 | 167 | 1.2358 | 1.0962 | $234.15 | 14 | 6.0086 | 16.2953 | 2 | 4 | ok |
| h1_last3_hilo | h1roll4_high_bias55_h4sma_pct | 3.4000 | 6.0000 | 67 | 18 | 49 | 1.4038 | 1.0064 | $127.11 | 14 | 20.8955 | 12.6027 | 2 | 4 | ok |
| h1_last6_hilo | h1roll4_high_bias55_h4sma_pct | 3.4000 | 6.0000 | 67 | 18 | 49 | 1.4002 | 1.0057 | $126.30 | 4 | 5.9701 | 15.7366 | 2 | 4 | ok |

## 输出文件

- `h4_high_bias55_opportunity_trades.csv`
- `h4_high_bias55_opportunity_summary.csv`
