# 1H_M30_4H 4H高价bias机会池测试

日期：2026-07-25

## 口径

- 机会池先保留样本，不再设置 6% 上限。
- 做空：`H1roll4最高价 vs H4 SMA55 >= bias55阈值`，且只接 M30 空信号。
- 做多：`H1roll4最高价 vs H4 SMA55 <= -bias55阈值`，且只接 M30 多信号。
- 第一层默认观察阈值：`bias55 >= 2.0%` 或 `bias55 <= -2.0%`。
- 组合测试：`bias55` 与 `bias13` 使用不同阈值，二者同时满足才进入机会池。
- 止损：1H 结构止损候选。
- 收益：`pnl_points * 100 * 0.01 lot`，未扣点差、滑点、手续费。

## bias55=2.0% 机会池

| stop_variant | name | bias55_threshold | bias13_threshold | n | long_n | short_n | pf | test_pf | pnl_usd_001 | stop_hits | positive_years | total_years | sample_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| h1_dir_segment_hilo | bias55_abs_ge_2.0 | 2.0000 | nan | 266 | 77 | 189 | 1.1853 | 0.9444 | $213.70 | 18 | 2 | 4 | ok |
| h1_last3_hilo | bias55_abs_ge_2.0 | 2.0000 | nan | 266 | 77 | 189 | 1.1506 | 0.9199 | $173.98 | 66 | 2 | 4 | ok |
| h1_last6_hilo | bias55_abs_ge_2.0 | 2.0000 | nan | 266 | 77 | 189 | 1.1674 | 0.8815 | $194.72 | 37 | 2 | 4 | ok |

## bias55 阈值扫描 Top

| stop_variant | name | bias55_threshold | bias13_threshold | n | long_n | short_n | pf | test_pf | pnl_usd_001 | stop_hits | positive_years | total_years | sample_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| h1_last3_hilo | bias55_abs_ge_4.0 | 4.0000 | nan | 38 | 7 | 31 | 2.1090 | 2.2303 | $208.34 | 7 | 3 | 4 | ok |
| h1_last3_hilo | bias55_abs_ge_3.8 | 3.8000 | nan | 39 | 8 | 31 | 2.0125 | 2.2303 | $199.33 | 7 | 3 | 4 | ok |
| h1_last6_hilo | bias55_abs_ge_4.0 | 4.0000 | nan | 38 | 7 | 31 | 2.0989 | 2.1583 | $207.43 | 2 | 3 | 4 | ok |
| h1_last6_hilo | bias55_abs_ge_3.8 | 3.8000 | nan | 39 | 8 | 31 | 2.0033 | 2.1583 | $198.42 | 2 | 3 | 4 | ok |
| h1_dir_segment_hilo | bias55_abs_ge_4.0 | 4.0000 | nan | 38 | 7 | 31 | 2.0739 | 2.0552 | $205.16 | 1 | 3 | 4 | ok |
| h1_dir_segment_hilo | bias55_abs_ge_3.8 | 3.8000 | nan | 39 | 8 | 31 | 1.9805 | 2.0552 | $196.15 | 1 | 3 | 4 | ok |
| h1_last3_hilo | bias55_abs_ge_3.6 | 3.6000 | nan | 49 | 12 | 37 | 1.8551 | 1.6892 | $209.79 | 9 | 3 | 4 | ok |
| h1_last6_hilo | bias55_abs_ge_3.6 | 3.6000 | nan | 49 | 12 | 37 | 1.8385 | 1.6476 | $207.58 | 3 | 3 | 4 | ok |
| h1_dir_segment_hilo | bias55_abs_ge_3.6 | 3.6000 | nan | 49 | 12 | 37 | 1.8218 | 1.5868 | $205.31 | 2 | 3 | 4 | ok |
| h1_last6_hilo | bias55_abs_ge_2.4 | 2.4000 | nan | 210 | 55 | 155 | 1.2828 | 1.0644 | $256.59 | 24 | 3 | 4 | ok |
| h1_last3_hilo | bias55_abs_ge_2.4 | 2.4000 | nan | 210 | 55 | 155 | 1.2378 | 1.0944 | $218.08 | 47 | 3 | 4 | ok |
| h1_dir_segment_hilo | bias55_abs_ge_2.4 | 2.4000 | nan | 210 | 55 | 155 | 1.2857 | 1.0369 | $258.63 | 10 | 3 | 4 | ok |
| h1_last3_hilo | bias55_abs_ge_2.2 | 2.2000 | nan | 237 | 67 | 170 | 1.1988 | 1.0696 | $203.28 | 55 | 3 | 4 | ok |
| h1_dir_segment_hilo | bias55_abs_ge_2.2 | 2.2000 | nan | 237 | 67 | 170 | 1.2625 | 1.1013 | $265.27 | 14 | 2 | 4 | ok |
| h1_dir_segment_hilo | bias55_abs_ge_1.6 | 1.6000 | nan | 369 | 111 | 258 | 1.1743 | 0.8665 | $260.25 | 23 | 3 | 4 | ok |

## bias55=2.0 后续过滤 Top

| stop_variant | name | bias55_threshold | bias13_threshold | n | long_n | short_n | pf | test_pf | pnl_usd_001 | stop_hits | positive_years | total_years | sample_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| h1_last3_hilo | 1h_bias5_13_pos | 2.0000 | nan | 135 | 31 | 104 | 1.6663 | 1.5369 | $366.53 | 24 | 3 | 4 | ok |
| h1_last6_hilo | 1h_bias5_13_pos | 2.0000 | nan | 135 | 31 | 104 | 1.6348 | 1.5033 | $355.93 | 17 | 3 | 4 | ok |
| h1_last3_hilo | 1h_close_side | 2.0000 | nan | 137 | 32 | 105 | 1.6462 | 1.4877 | $359.82 | 25 | 3 | 4 | ok |
| h1_last3_hilo | 1h_bias13_pos | 2.0000 | nan | 137 | 32 | 105 | 1.6462 | 1.4877 | $359.82 | 25 | 3 | 4 | ok |
| h1_last6_hilo | 1h_close_side | 2.0000 | nan | 137 | 32 | 105 | 1.6075 | 1.4327 | $346.40 | 18 | 3 | 4 | ok |
| h1_last6_hilo | 1h_bias13_pos | 2.0000 | nan | 137 | 32 | 105 | 1.6075 | 1.4327 | $346.40 | 18 | 3 | 4 | ok |
| h1_dir_segment_hilo | 1h_bias5_13_pos | 2.0000 | nan | 135 | 31 | 104 | 1.5973 | 1.4439 | $338.38 | 12 | 2 | 4 | ok |
| h1_dir_segment_hilo | 1h_close_side | 2.0000 | nan | 137 | 32 | 105 | 1.5728 | 1.3840 | $329.55 | 12 | 2 | 4 | ok |
| h1_dir_segment_hilo | 1h_bias13_pos | 2.0000 | nan | 137 | 32 | 105 | 1.5728 | 1.3840 | $329.55 | 12 | 2 | 4 | ok |
| h1_last3_hilo | 1h_dir_align | 2.0000 | nan | 31 | 7 | 24 | 2.9930 | 0.8082 | $225.90 | 8 | 2 | 4 | ok |
| h1_dir_segment_hilo | 1h_dir_align | 2.0000 | nan | 31 | 7 | 24 | 2.7950 | 0.7906 | $210.35 | 7 | 2 | 4 | ok |
| h1_last6_hilo | 1h_dir_align | 2.0000 | nan | 31 | 7 | 24 | 2.8503 | 0.7468 | $220.23 | 6 | 2 | 4 | ok |
| h1_last6_hilo | buy_only | 2.0000 | nan | 77 | 77 | 0 | 1.4263 | 0.8558 | $128.71 | 11 | 3 | 4 | ok |
| h1_dir_segment_hilo | base | 2.0000 | nan | 266 | 77 | 189 | 1.1853 | 0.9444 | $213.70 | 18 | 2 | 4 | ok |
| h1_dir_segment_hilo | m30_close_side | 2.0000 | nan | 266 | 77 | 189 | 1.1853 | 0.9444 | $213.70 | 18 | 2 | 4 | ok |
| h1_dir_segment_hilo | m30_bias5_pos | 2.0000 | nan | 266 | 77 | 189 | 1.1853 | 0.9444 | $213.70 | 18 | 2 | 4 | ok |
| h1_dir_segment_hilo | m30_bias13_pos | 2.0000 | nan | 266 | 77 | 189 | 1.1853 | 0.9444 | $213.70 | 18 | 2 | 4 | ok |
| h1_dir_segment_hilo | m30_bias5_13_pos | 2.0000 | nan | 266 | 77 | 189 | 1.1853 | 0.9444 | $213.70 | 18 | 2 | 4 | ok |
| h1_last3_hilo | 1h_bias5_pos | 2.0000 | nan | 244 | 70 | 174 | 1.2116 | 1.0431 | $221.76 | 62 | 1 | 4 | ok |
| h1_last3_hilo | base | 2.0000 | nan | 266 | 77 | 189 | 1.1506 | 0.9199 | $173.98 | 66 | 2 | 4 | ok |

## bias55 + bias13 不同阈值组合 Top

| stop_variant | name | bias55_threshold | bias13_threshold | n | long_n | short_n | pf | test_pf | pnl_usd_001 | stop_hits | positive_years | total_years | sample_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| h1_last6_hilo | bias55_2.4_bias13_1.0 | 2.4000 | 1.0000 | 130 | 24 | 106 | 1.0480 | 1.3458 | $29.77 | 14 | 3 | 4 | ok |
| h1_dir_segment_hilo | bias55_2.4_bias13_1.0 | 2.4000 | 1.0000 | 130 | 24 | 106 | 1.0545 | 1.3220 | $33.60 | 4 | 3 | 4 | ok |
| h1_last3_hilo | bias55_2.4_bias13_1.0 | 2.4000 | 1.0000 | 130 | 24 | 106 | 0.9899 | 1.3558 | $-6.35 | 29 | 3 | 4 | ok |
| h1_last6_hilo | bias55_2.0_bias13_1.0 | 2.0000 | 1.0000 | 143 | 27 | 116 | 1.0430 | 1.1947 | $28.78 | 17 | 2 | 4 | ok |
| h1_last3_hilo | bias55_2.0_bias13_1.0 | 2.0000 | 1.0000 | 143 | 27 | 116 | 0.9930 | 1.2035 | $-4.73 | 33 | 2 | 4 | ok |
| h1_last3_hilo | bias55_1.5_bias13_1.0 | 1.5000 | 1.0000 | 174 | 38 | 136 | 0.9802 | 1.0434 | $-15.71 | 41 | 3 | 4 | ok |
| h1_last6_hilo | bias55_1.5_bias13_1.0 | 1.5000 | 1.0000 | 174 | 38 | 136 | 1.0086 | 1.0174 | $6.84 | 19 | 3 | 4 | ok |
| h1_dir_segment_hilo | bias55_2.0_bias13_1.0 | 2.0000 | 1.0000 | 143 | 27 | 116 | 1.0421 | 1.1560 | $28.19 | 4 | 2 | 4 | ok |
| h1_dir_segment_hilo | bias55_1.5_bias13_1.0 | 1.5000 | 1.0000 | 174 | 38 | 136 | 1.0124 | 0.9933 | $9.79 | 4 | 3 | 4 | ok |
| h1_dir_segment_hilo | bias55_2.0_bias13_0.5 | 2.0000 | 0.5000 | 226 | 53 | 173 | 1.1401 | 0.9157 | $135.93 | 12 | 2 | 4 | ok |
| h1_last6_hilo | bias55_2.4_bias13_0.5 | 2.4000 | 0.5000 | 191 | 43 | 148 | 1.1088 | 0.9603 | $91.29 | 23 | 2 | 4 | ok |
| h1_last3_hilo | bias55_2.4_bias13_0.5 | 2.4000 | 0.5000 | 191 | 43 | 148 | 1.0636 | 0.9888 | $53.95 | 44 | 2 | 4 | ok |
| h1_dir_segment_hilo | bias55_2.4_bias13_0.5 | 2.4000 | 0.5000 | 191 | 43 | 148 | 1.1126 | 0.9341 | $94.18 | 10 | 2 | 4 | ok |
| h1_last3_hilo | bias55_2.0_bias13_0.5 | 2.0000 | 0.5000 | 226 | 53 | 173 | 1.0810 | 0.8812 | $79.18 | 55 | 1 | 4 | ok |
| h1_dir_segment_hilo | bias55_1.5_bias13_0.5 | 1.5000 | 0.5000 | 303 | 77 | 226 | 1.0687 | 0.8351 | $84.34 | 15 | 1 | 4 | ok |
| h1_last6_hilo | bias55_2.0_bias13_0.5 | 2.0000 | 0.5000 | 226 | 53 | 173 | 1.1077 | 0.8417 | $105.51 | 31 | 1 | 4 | ok |
| h1_last6_hilo | bias55_1.5_bias13_0.5 | 1.5000 | 0.5000 | 303 | 77 | 226 | 1.0450 | 0.7784 | $55.60 | 38 | 1 | 4 | ok |
| h1_last3_hilo | bias55_1.5_bias13_0.5 | 1.5000 | 0.5000 | 303 | 77 | 226 | 1.0157 | 0.7527 | $19.17 | 75 | 1 | 4 | ok |
| h1_last6_hilo | bias55_3.0_bias13_1.5 | 3.0000 | 1.5000 | 52 | 8 | 44 | 0.5752 | 1.1127 | $-131.99 | 4 | 1 | 4 | ok |
| h1_last3_hilo | bias55_3.0_bias13_1.5 | 3.0000 | 1.5000 | 52 | 8 | 44 | 0.5727 | 1.1069 | $-133.36 | 10 | 1 | 4 | ok |

## 输出文件

- `h4_bias_opportunity_pool_trades.csv`
- `h4_bias55_pool_threshold_scan.csv`
- `h4_bias55_pool_second_filter_summary.csv`
- `h4_bias55_bias13_combo_scan.csv`
