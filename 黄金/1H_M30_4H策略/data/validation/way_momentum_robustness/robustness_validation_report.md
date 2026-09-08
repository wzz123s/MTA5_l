# 1H_M30_4H 稳健性验证

日期：2026-07-26

## 验证范围

- 输入：上一轮极值 way / 动能扫描生成的 `way_momentum_enriched_trades.csv`。
- 本步骤只做稳健性验证，不重建信号、不改止损。
- 成本压力测试为每笔交易扣除固定往返成本。按当前报告口径，0.01 lot 下 1.0 price point 约等于 $1.00。

## 总体结果

| candidate | n | long_n | short_n | pf | test_pf | pnl_usd_001 | test_pnl_usd_001 | positive_years | total_years | positive_months | total_months | max_drawdown_usd_001 | breakeven_cost_points_per_trade |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fd1_8_28_side_pool_base | 112 | 41 | 71 | 2.2954 | 1.8391 | $561.37 | $119.10 | 4 | 4 | 22 | 36 | $57.74 | 5.0123 |
| fd1_8_28_side_pool_close_mom_ge_-0.4 | 108 | 38 | 70 | 2.4334 | 1.9237 | $585.95 | $125.34 | 4 | 4 | 23 | 36 | $57.01 | 5.4255 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 88 | 38 | 50 | 3.1901 | 2.2755 | $670.33 | $139.56 | 4 | 4 | 23 | 34 | $47.45 | 7.6174 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_way_ge_0.3 | 97 | 38 | 59 | 2.9797 | 2.2431 | $645.06 | $140.57 | 4 | 4 | 23 | 36 | $56.63 | 6.6502 |
| fd1_8_28_side_pool_way_le_0.6 | 101 | 35 | 66 | 2.3408 | 2.0110 | $544.29 | $131.23 | 4 | 4 | 22 | 36 | $56.35 | 5.3890 |
| fd1_6_28_side_pool_base | 144 | 53 | 91 | 1.9439 | 1.3945 | $508.99 | $70.88 | 4 | 4 | 21 | 37 | $85.02 | 3.5346 |
| fd1_6_28_side_pool_close_mom_ge_-0.4 | 140 | 50 | 90 | 2.0367 | 1.5030 | $533.56 | $83.86 | 4 | 4 | 21 | 37 | $77.63 | 3.8112 |
| fd3_6_28_side_pool_base | 67 | 28 | 39 | 2.8759 | 2.6092 | $439.74 | $95.66 | 4 | 4 | 17 | 30 | $43.78 | 6.5633 |

## 年度拆分

| candidate | year | n | long_n | short_n | pf | pnl_usd_001 |
| --- | --- | --- | --- | --- | --- | --- |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 2020 | 20 | 5 | 15 | 9.3368 | $425.69 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 2021 | 17 | 10 | 7 | 3.3083 | $89.55 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 2022 | 29 | 17 | 12 | 1.1435 | $19.03 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 2023 | 22 | 6 | 16 | 2.6276 | $136.06 |
| fd1_6_28_side_pool_base | 2020 | 27 | 6 | 21 | 6.2107 | $421.33 |
| fd1_6_28_side_pool_base | 2021 | 37 | 16 | 21 | 1.0263 | $3.45 |
| fd1_6_28_side_pool_base | 2022 | 38 | 20 | 18 | 1.1161 | $18.70 |
| fd1_6_28_side_pool_base | 2023 | 42 | 11 | 31 | 1.3942 | $65.51 |

## 多空拆分

| candidate | dir | n | pf | pnl_usd_001 | positive_years | total_years | positive_months | total_months |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fd1_8_28_side_pool_base | L | 41 | 3.3076 | $297.77 | 3 | 4 | 13 | 19 |
| fd1_8_28_side_pool_base | S | 71 | 1.8662 | $263.60 | 3 | 4 | 14 | 25 |
| fd1_8_28_side_pool_close_mom_ge_-0.4 | L | 38 | 3.8262 | $315.26 | 3 | 4 | 14 | 19 |
| fd1_8_28_side_pool_close_mom_ge_-0.4 | S | 70 | 1.9107 | $270.69 | 3 | 4 | 14 | 25 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | L | 38 | 3.8262 | $315.26 | 3 | 4 | 14 | 19 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | S | 50 | 2.8253 | $355.07 | 3 | 4 | 13 | 22 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_way_ge_0.3 | L | 38 | 3.8262 | $315.26 | 3 | 4 | 14 | 19 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_way_ge_0.3 | S | 59 | 2.5390 | $329.81 | 3 | 4 | 14 | 25 |
| fd1_8_28_side_pool_way_le_0.6 | L | 35 | 3.6862 | $297.96 | 3 | 4 | 13 | 19 |
| fd1_8_28_side_pool_way_le_0.6 | S | 66 | 1.8349 | $246.33 | 3 | 4 | 13 | 24 |
| fd1_6_28_side_pool_base | L | 53 | 2.5560 | $266.95 | 3 | 4 | 12 | 20 |
| fd1_6_28_side_pool_base | S | 91 | 1.6582 | $242.03 | 3 | 4 | 14 | 25 |
| fd1_6_28_side_pool_close_mom_ge_-0.4 | L | 50 | 2.8462 | $284.44 | 3 | 4 | 13 | 20 |
| fd1_6_28_side_pool_close_mom_ge_-0.4 | S | 90 | 1.6908 | $249.12 | 3 | 4 | 14 | 25 |
| fd3_6_28_side_pool_base | L | 28 | 2.4369 | $130.35 | 3 | 4 | 10 | 17 |
| fd3_6_28_side_pool_base | S | 39 | 3.1531 | $309.39 | 3 | 4 | 12 | 21 |

## 成本压力测试

| candidate | round_trip_cost_points | pf | test_pf | pnl_usd_001 | test_pnl_usd_001 | positive_years | total_years |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 0.5000 | 2.9033 | 2.0737 | $626.33 | $126.06 | 4 | 4 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 1.0000 | 2.6516 | 1.8975 | $582.33 | $112.56 | 3 | 4 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 1.5000 | 2.4295 | 1.7425 | $538.33 | $99.06 | 3 | 4 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 2.0000 | 2.2334 | 1.6051 | $494.33 | $85.56 | 3 | 4 |
| fd1_6_28_side_pool_base | 0.5000 | 1.7441 | 1.2492 | $436.99 | $48.88 | 2 | 4 |
| fd1_6_28_side_pool_base | 1.0000 | 1.5737 | 1.1264 | $364.99 | $26.88 | 2 | 4 |
| fd1_6_28_side_pool_base | 1.5000 | 1.4273 | 1.0213 | $292.99 | $4.88 | 2 | 4 |
| fd1_6_28_side_pool_base | 2.0000 | 1.3005 | 0.9303 | $220.99 | $-17.12 | 1 | 4 |

## 成本后的年度拆分

| candidate | round_trip_cost_points | year | n | pf | pnl_usd_001 |
| --- | --- | --- | --- | --- | --- |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 0.5000 | 2020 | 20 | 8.6187 | $415.69 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 0.5000 | 2021 | 17 | 2.9163 | $81.05 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 0.5000 | 2022 | 29 | 1.0319 | $4.53 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 0.5000 | 2023 | 22 | 2.3881 | $125.06 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 1.0000 | 2020 | 20 | 7.9872 | $405.69 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 1.0000 | 2021 | 17 | 2.5744 | $72.55 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 1.0000 | 2022 | 29 | 0.9343 | $-9.97 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 1.0000 | 2023 | 22 | 2.1808 | $114.06 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 2.0000 | 2020 | 20 | 6.9090 | $385.69 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 2.0000 | 2021 | 17 | 2.0272 | $55.55 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 2.0000 | 2022 | 29 | 0.7732 | $-38.97 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 2.0000 | 2023 | 22 | 1.8400 | $92.06 |
| fd1_6_28_side_pool_base | 0.5000 | 2020 | 27 | 5.6685 | $407.83 |
| fd1_6_28_side_pool_base | 0.5000 | 2021 | 37 | 0.8953 | $-15.05 |
| fd1_6_28_side_pool_base | 0.5000 | 2022 | 38 | 0.9983 | $-0.30 |
| fd1_6_28_side_pool_base | 0.5000 | 2023 | 42 | 1.2443 | $44.51 |
| fd1_6_28_side_pool_base | 1.0000 | 2020 | 27 | 5.2013 | $394.33 |
| fd1_6_28_side_pool_base | 1.0000 | 2021 | 37 | 0.7862 | $-33.55 |
| fd1_6_28_side_pool_base | 1.0000 | 2022 | 38 | 0.8969 | $-19.30 |
| fd1_6_28_side_pool_base | 1.0000 | 2023 | 42 | 1.1186 | $23.51 |
| fd1_6_28_side_pool_base | 2.0000 | 2020 | 27 | 4.4308 | $367.33 |
| fd1_6_28_side_pool_base | 2.0000 | 2021 | 37 | 0.6165 | $-70.55 |
| fd1_6_28_side_pool_base | 2.0000 | 2022 | 38 | 0.7326 | $-57.30 |
| fd1_6_28_side_pool_base | 2.0000 | 2023 | 42 | 0.9197 | $-18.49 |

## 滚动窗口汇总

| candidate | window_months | windows | positive_windows | positive_window_rate_pct | min_pnl_points | median_pnl_points | worst_window_start | worst_window_end | worst_window_pnl_usd_001 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fd1_8_28_side_pool_base | 3 | 46 | 33 | 71.7391 | -52.3580 | 19.2705 | 2021-04 | 2021-06 | $-52.36 |
| fd1_8_28_side_pool_base | 6 | 47 | 36 | 76.5957 | -43.3490 | 51.0880 | 2022-01 | 2022-06 | $-43.35 |
| fd1_8_28_side_pool_base | 12 | 47 | 44 | 93.6170 | -39.2460 | 114.5760 | 2021-10 | 2022-09 | $-39.25 |
| fd1_8_28_side_pool_close_mom_ge_-0.4 | 3 | 46 | 33 | 71.7391 | -44.9720 | 19.2705 | 2021-04 | 2021-06 | $-44.97 |
| fd1_8_28_side_pool_close_mom_ge_-0.4 | 6 | 47 | 36 | 76.5957 | -43.3490 | 51.5940 | 2022-01 | 2022-06 | $-43.35 |
| fd1_8_28_side_pool_close_mom_ge_-0.4 | 12 | 47 | 44 | 93.6170 | -39.2460 | 127.5550 | 2021-10 | 2022-09 | $-39.25 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 3 | 46 | 35 | 76.0870 | -18.2210 | 22.3665 | 2022-01 | 2022-03 | $-18.22 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 6 | 47 | 41 | 87.2340 | -33.7870 | 58.6930 | 2022-01 | 2022-06 | $-33.79 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 12 | 47 | 46 | 97.8723 | -28.4610 | 136.0600 | 2021-10 | 2022-09 | $-28.46 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_way_ge_0.3 | 3 | 46 | 34 | 73.9130 | -50.7300 | 25.3585 | 2021-04 | 2021-06 | $-50.73 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_way_ge_0.3 | 6 | 47 | 39 | 82.9787 | -29.2390 | 51.5940 | 2020-12 | 2021-05 | $-29.24 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_way_ge_0.3 | 12 | 47 | 46 | 97.8723 | -16.9950 | 131.3760 | 2021-10 | 2022-09 | $-16.99 |
| fd1_8_28_side_pool_way_le_0.6 | 3 | 46 | 34 | 73.9130 | -50.9640 | 13.8595 | 2021-04 | 2021-06 | $-50.96 |
| fd1_8_28_side_pool_way_le_0.6 | 6 | 47 | 37 | 78.7234 | -35.0810 | 49.3820 | 2022-01 | 2022-06 | $-35.08 |
| fd1_8_28_side_pool_way_le_0.6 | 12 | 47 | 44 | 93.6170 | -33.1900 | 120.5820 | 2021-10 | 2022-09 | $-33.19 |
| fd1_6_28_side_pool_base | 3 | 47 | 31 | 65.9574 | -79.6310 | 14.3990 | 2021-04 | 2021-06 | $-79.63 |
| fd1_6_28_side_pool_base | 6 | 47 | 31 | 65.9574 | -52.2370 | 51.7730 | 2021-01 | 2021-06 | $-52.24 |
| fd1_6_28_side_pool_base | 12 | 47 | 39 | 82.9787 | -58.0090 | 99.2990 | 2021-04 | 2022-03 | $-58.01 |
| fd1_6_28_side_pool_close_mom_ge_-0.4 | 3 | 47 | 31 | 65.9574 | -72.2450 | 14.9980 | 2021-04 | 2021-06 | $-72.25 |
| fd1_6_28_side_pool_close_mom_ge_-0.4 | 6 | 47 | 31 | 65.9574 | -44.8510 | 55.6900 | 2021-01 | 2021-06 | $-44.85 |
| fd1_6_28_side_pool_close_mom_ge_-0.4 | 12 | 47 | 40 | 85.1064 | -51.6830 | 106.6850 | 2021-10 | 2022-09 | $-51.68 |
| fd3_6_28_side_pool_base | 3 | 43 | 26 | 60.4651 | -30.0340 | 4.7530 | 2022-11 | 2023-01 | $-30.03 |
| fd3_6_28_side_pool_base | 6 | 45 | 31 | 68.8889 | -41.5450 | 52.3320 | 2022-08 | 2023-01 | $-41.55 |
| fd3_6_28_side_pool_base | 12 | 45 | 40 | 88.8889 | -24.7550 | 102.2530 | 2020-09 | 2021-08 | $-24.75 |

## 当前最佳候选的最差月份

| candidate | month | n | long_n | short_n | pf | pnl_usd_001 |
| --- | --- | --- | --- | --- | --- | --- |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 2022-02 | 3 | 0 | 3 | 0.0000 | $-24.72 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 2022-09 | 6 | 6 | 0 | 0.2528 | $-21.62 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 2022-05 | 5 | 5 | 0 | 0.4011 | $-20.40 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 2023-01 | 3 | 0 | 3 | 0.0000 | $-17.00 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 2021-04 | 2 | 0 | 2 | 0.0000 | $-9.86 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 2023-06 | 1 | 1 | 0 | 0.0000 | $-6.52 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 2021-01 | 3 | 1 | 2 | 0.5739 | $-5.79 |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 2022-11 | 4 | 0 | 4 | 0.6515 | $-5.59 |

## 当前判断

- 当前最高实际收益候选：`fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7`。
- 当前最大样本候选：`fd1_6_28_side_pool_base`。
- `8-28pt + close_momentum >= -0.4` 是当前主候选；`6-28pt + close_momentum >= -0.4` 更适合作为样本对照。
- 多头 PF 明显高于空头，空头交易数更多但效率偏低；下一轮优化应优先做多空分侧，尤其先压缩空头弱月份。
- 2021/2022 的边际仍薄，加入成本后年度正收益数会下降；因此还不能直接进入实盘，只能进入 EA 逐笔对齐/模拟验证阶段。

## 输出文件

- `robustness_overall_summary.csv`
- `robustness_yearly_summary.csv`
- `robustness_monthly_summary.csv`
- `robustness_side_summary.csv`
- `robustness_cost_sensitivity.csv`
- `robustness_cost_yearly_summary.csv`
- `robustness_rolling_windows.csv`
- `robustness_rolling_summary.csv`
