# 1H_M30_4H 空头分侧优化

日期：2026-07-26

## 口径

- 多头保留当前主候选规则，不参与本轮优化。
- 空头基线：`fixed_delay_1 + H1 last6 stop + stop_distance 8-28pt + side-extreme pool + close_momentum_signed_pct >= -0.4`。
- 本轮只对空头增加过滤条件，再把“原多头 + 过滤后空头”合成总策略评估。
- 最小样本约束：空头不少于 40 笔，总交易不少于 75 笔。

## 空头基线

| filter_name | family | short_n | removed_short_n | short_pf | short_pnl_usd_001 | total_n | total_pf | total_test_pf | total_pnl_usd_001 | cost_1_test_pf | cost_1_pnl_usd_001 | roll12_positive_rate_pct | roll12_min_pnl_points | quality_ok |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | baseline | 70 | 0 | 1.9107 | $270.69 | 108 | 2.4334 | 1.9237 | $585.95 | 1.5893 | $477.95 | 93.6170 | -39.2460 | True |

## 按评分排序

| filter_name | family | short_n | removed_short_n | short_pf | short_pnl_usd_001 | total_n | total_pf | total_test_pf | total_pnl_usd_001 | cost_1_test_pf | cost_1_pnl_usd_001 | roll12_positive_rate_pct | roll12_min_pnl_points | quality_ok |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1h_bias55_signed_pct_le_-0.5 | h1_bias55 | 42 | 28 | 2.5984 | $219.85 | 80 | 3.1482 | 3.3855 | $535.11 | 2.7598 | $455.11 | 97.8261 | -16.3280 | True |
| side_extreme_vol_way_s_way_le_0.7 | way_volume | 50 | 20 | 2.8253 | $355.07 | 88 | 3.1901 | 2.2755 | $670.33 | 1.8975 | $582.33 | 97.8723 | -28.4610 | True |
| side_extreme_way_s_way_ge_0.3 | way | 59 | 11 | 2.5390 | $329.81 | 97 | 2.9797 | 2.2431 | $645.06 | 1.8372 | $548.06 | 97.8723 | -16.9950 | True |
| extreme_h1_direction_up | h1_way_state | 54 | 16 | 1.9780 | $195.62 | 92 | 2.6397 | 2.6964 | $510.88 | 2.2076 | $418.88 | 97.8723 | -16.8370 | True |
| 1h_bias55_signed_pct_le_0.1 | h1_bias55 | 62 | 8 | 2.2438 | $278.99 | 100 | 2.7693 | 2.2846 | $594.25 | 1.8829 | $494.25 | 97.8723 | -15.3770 | True |
| 1h_bias55_signed_pct_le_-0.3 | h1_bias55 | 52 | 18 | 1.9318 | $172.98 | 90 | 2.6428 | 2.6666 | $488.24 | 2.1642 | $398.24 | 97.8261 | -20.6490 | True |
| side_extreme_bias55_h4sma_pct_ge_2.4 | extreme_bias55 | 59 | 11 | 2.1511 | $268.91 | 97 | 2.6924 | 2.2846 | $584.17 | 1.8829 | $487.17 | 97.8723 | -14.9390 | True |
| 1h_bias55_signed_pct_le_-0.1 | h1_bias55 | 60 | 10 | 2.1389 | $246.53 | 98 | 2.7127 | 2.2846 | $561.79 | 1.8829 | $463.79 | 97.8261 | -15.3770 | True |
| side_extreme_vol_way_s_way_le_0.8 | way_volume | 60 | 10 | 2.3117 | $318.69 | 98 | 2.7882 | 2.2553 | $633.95 | 1.8620 | $535.95 | 95.7447 | -34.2110 | True |
| 1h_bias55_signed_pct_le_0.3 | h1_bias55 | 64 | 6 | 2.0856 | $261.98 | 102 | 2.6358 | 2.1485 | $577.24 | 1.7725 | $475.24 | 97.8723 | -15.3770 | True |
| 1h_bias55_signed_pct_le_0.5 | h1_bias55 | 68 | 2 | 2.0912 | $296.35 | 106 | 2.5963 | 2.0242 | $611.60 | 1.6719 | $505.61 | 97.8723 | -22.0300 | True |
| side_extreme_body_momentum_signed_le_0.3 | momentum_body | 40 | 30 | 1.9970 | $179.79 | 78 | 2.6960 | 2.4763 | $495.05 | 2.0336 | $417.05 | 95.7447 | -29.5040 | True |
| side_extreme_bias55_h4sma_pct_ge_2.2 | extreme_bias55 | 61 | 9 | 2.0066 | $252.48 | 99 | 2.5667 | 2.2846 | $567.74 | 1.8829 | $468.74 | 95.7447 | -31.3700 | True |
| side_extreme_body_momentum_signed_le_0.4 | momentum_body | 46 | 24 | 1.9322 | $178.02 | 84 | 2.6305 | 2.4165 | $493.28 | 1.9753 | $409.28 | 95.7447 | -28.0050 | True |
| side_extreme_vol_way_s_way_le_0.9 | way_volume | 65 | 5 | 2.1396 | $302.49 | 103 | 2.6386 | 2.1226 | $617.75 | 1.7540 | $514.75 | 95.7447 | -34.2110 | True |

## 按实际收益排序

| filter_name | family | short_n | removed_short_n | short_pf | short_pnl_usd_001 | total_n | total_pf | total_test_pf | total_pnl_usd_001 | cost_1_test_pf | cost_1_pnl_usd_001 | roll12_positive_rate_pct | roll12_min_pnl_points | quality_ok |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| side_extreme_vol_way_s_way_le_0.7 | way_volume | 50 | 20 | 2.8253 | $355.07 | 88 | 3.1901 | 2.2755 | $670.33 | 1.8975 | $582.33 | 97.8723 | -28.4610 | True |
| side_extreme_way_s_way_ge_0.3 | way | 59 | 11 | 2.5390 | $329.81 | 97 | 2.9797 | 2.2431 | $645.06 | 1.8372 | $548.06 | 97.8723 | -16.9950 | True |
| side_extreme_vol_way_s_way_le_0.8 | way_volume | 60 | 10 | 2.3117 | $318.69 | 98 | 2.7882 | 2.2553 | $633.95 | 1.8620 | $535.95 | 95.7447 | -34.2110 | True |
| side_extreme_vol_way_s_way_le_0.9 | way_volume | 65 | 5 | 2.1396 | $302.49 | 103 | 2.6386 | 2.1226 | $617.75 | 1.7540 | $514.75 | 95.7447 | -34.2110 | True |
| 1h_bias55_signed_pct_le_0.5 | h1_bias55 | 68 | 2 | 2.0912 | $296.35 | 106 | 2.5963 | 2.0242 | $611.60 | 1.6719 | $505.61 | 97.8723 | -22.0300 | True |
| side_extreme_way_s_way_ge_0.2 | way | 66 | 4 | 2.0739 | $291.10 | 104 | 2.5848 | 2.2068 | $606.36 | 1.8009 | $502.36 | 93.6170 | -34.2110 | True |
| stop_9_26 | stop_distance | 64 | 6 | 2.0402 | $283.42 | 102 | 2.5590 | 1.9311 | $598.68 | 1.5979 | $496.68 | 95.7447 | -35.8810 | True |
| stop_9_28 | stop_distance | 64 | 6 | 2.0402 | $283.42 | 102 | 2.5590 | 1.9311 | $598.68 | 1.5979 | $496.68 | 95.7447 | -35.8810 | True |
| side_extreme_sma13_gap_momentum_signed_pct_ge_-0.2 | momentum_gap | 68 | 2 | 1.9784 | $280.86 | 106 | 2.4955 | 2.0016 | $596.12 | 1.6557 | $490.12 | 93.6170 | -39.2460 | True |
| 1h_bias55_signed_pct_le_0.7 | h1_bias55 | 69 | 1 | 1.9665 | $279.13 | 107 | 2.4847 | 1.9237 | $594.39 | 1.5893 | $487.39 | 93.6170 | -39.2460 | True |
| 1h_bias55_signed_pct_le_0.9 | h1_bias55 | 69 | 1 | 1.9665 | $279.13 | 107 | 2.4847 | 1.9237 | $594.39 | 1.5893 | $487.39 | 93.6170 | -39.2460 | True |
| 1h_bias55_signed_pct_le_0.1 | h1_bias55 | 62 | 8 | 2.2438 | $278.99 | 100 | 2.7693 | 2.2846 | $594.25 | 1.8829 | $494.25 | 97.8723 | -15.3770 | True |
| side_extreme_way_s_way_le_0.9 | way | 69 | 1 | 1.9537 | $277.23 | 107 | 2.4730 | 1.9645 | $592.49 | 1.6184 | $485.49 | 93.6170 | -39.2460 | True |
| side_extreme_close_momentum_signed_pct_le_0.6 | momentum_close | 68 | 2 | 1.9502 | $274.97 | 106 | 2.4721 | 2.0242 | $590.23 | 1.6719 | $484.23 | 95.7447 | -39.2460 | True |
| side_extreme_sma13_gap_momentum_signed_pct_le_0.6 | momentum_gap | 68 | 2 | 1.9502 | $274.97 | 106 | 2.4721 | 2.0242 | $590.23 | 1.6719 | $484.23 | 95.7447 | -39.2460 | True |

## 空头年度拆分

| filter_name | year | n | pf | pnl_usd_001 |
| --- | --- | --- | --- | --- |
| baseline | 2020 | 18 | 4.6632 | $231.36 |
| baseline | 2021 | 15 | 0.2074 | $-56.49 |
| baseline | 2022 | 15 | 1.2481 | $16.14 |
| baseline | 2023 | 22 | 1.8150 | $79.67 |
| 1h_bias55_signed_pct_le_-0.5 | 2020 | 11 | 4.2469 | $80.16 |
| 1h_bias55_signed_pct_le_-0.5 | 2021 | 8 | 0.1903 | $-33.15 |
| 1h_bias55_signed_pct_le_-0.5 | 2022 | 10 | 2.1390 | $39.77 |
| 1h_bias55_signed_pct_le_-0.5 | 2023 | 13 | 4.5973 | $133.07 |
| side_extreme_vol_way_s_way_le_0.7 | 2020 | 15 | 6.9503 | $252.15 |
| side_extreme_vol_way_s_way_le_0.7 | 2021 | 7 | 0.3221 | $-17.90 |
| side_extreme_vol_way_s_way_le_0.7 | 2022 | 12 | 1.4962 | $26.93 |
| side_extreme_vol_way_s_way_le_0.7 | 2023 | 16 | 2.3136 | $93.90 |
| side_extreme_way_s_way_ge_0.3 | 2020 | 14 | 9.8538 | $255.03 |
| side_extreme_way_s_way_ge_0.3 | 2021 | 14 | 0.1266 | $-62.24 |
| side_extreme_way_s_way_ge_0.3 | 2022 | 13 | 1.8971 | $38.39 |
| side_extreme_way_s_way_ge_0.3 | 2023 | 18 | 2.3809 | $98.63 |

## 收益候选的空头最差月份

| filter_name | month | n | pf | pnl_usd_001 |
| --- | --- | --- | --- | --- |
| side_extreme_vol_way_s_way_le_0.7 | 2022-02 | 3 | 0.0000 | $-24.72 |
| side_extreme_vol_way_s_way_le_0.7 | 2023-10 | 5 | 0.2937 | $-17.73 |
| side_extreme_vol_way_s_way_le_0.7 | 2023-01 | 3 | 0.0000 | $-17.00 |
| side_extreme_vol_way_s_way_le_0.7 | 2021-04 | 2 | 0.0000 | $-9.86 |
| side_extreme_vol_way_s_way_le_0.7 | 2022-11 | 4 | 0.6515 | $-5.59 |
| side_extreme_vol_way_s_way_le_0.7 | 2020-07 | 2 | 0.0000 | $-4.59 |
| side_extreme_vol_way_s_way_le_0.7 | 2021-01 | 2 | 0.6913 | $-3.48 |
| side_extreme_vol_way_s_way_le_0.7 | 2021-11 | 2 | 0.2122 | $-2.65 |
| side_extreme_vol_way_s_way_le_0.7 | 2021-05 | 1 | 0.0000 | $-1.91 |
| side_extreme_vol_way_s_way_le_0.7 | 2022-08 | 1 | 999.0000 | $0.79 |

## 当前判断

- 当前实际收益最高的空头过滤：`side_extreme_vol_way_s_way_le_0.7`，含义：side extreme vol_way_s_way <= 0.7。
- 当前稳健评分最高的空头过滤：`1h_bias55_signed_pct_le_-0.5`，含义：1H bias55 signed pct <= -0.5。
- 主推先看实际收益候选；若后续成本/EA 对齐发现滑点更高，再降级到稳健评分候选。
- 如果某个最优项样本刚好卡在 40 笔附近，需要把它视为研究候选，而不是正式参数。

## 输出文件

- `short_side_filter_summary.csv`
- `short_side_selected_trades_top.csv`
- `short_side_yearly.csv`
- `short_side_monthly.csv`
- `short_side_optimization_report.md`
