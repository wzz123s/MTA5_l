# 1H_M30_4H extreme way_s_way and momentum filter scan

Date: 2026-07-25

## Rules

- Rebuild `way_s_way` from this strategy's own MT5 H1 bars.
- Short side uses the H1 bar with the highest high in the last four closed H1 bars.
- Long side uses the H1 bar with the lowest low in the last four closed H1 bars.
- `side_extreme_way_s_way` is taken from that exact high/low bar.
- Momentum controls: signed candle body, signed close-to-close momentum, and signed SMA13-gap momentum.
- Report PnL uses `pnl_points * 100 * 0.01 lot`; spread, slippage, and commission are not deducted.

## Candidate Baselines

| candidate | pool | filter_name | n | long_n | short_n | pf | test_pf | pnl_usd_001 | avg_way_s_way | avg_body_momentum_signed | positive_years | total_years | sample_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fd3_m30sma13_6_28 | side_extreme_pool | baseline | 67 | 28 | 39 | 2.8759 | 2.6092 | $439.74 | 0.4440 | 0.2215 | 4 | 4 | ok |
| fd3_m30sma13_6_28 | legacy_high_pool | baseline | 50 | 11 | 39 | 3.1162 | 2.4490 | $404.75 | 0.4494 | 0.2590 | 3 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | baseline | 112 | 41 | 71 | 2.2954 | 1.8391 | $561.37 | 0.4398 | 0.1344 | 4 | 4 | ok |
| fd1_h1last6_6_28 | side_extreme_pool | baseline | 144 | 53 | 91 | 1.9439 | 1.3945 | $508.99 | 0.4389 | 0.1631 | 4 | 4 | ok |
| fd1_h1last6_8_28 | legacy_high_pool | baseline | 90 | 19 | 71 | 2.3045 | 1.8937 | $481.25 | 0.4284 | 0.1356 | 2 | 4 | ok |
| fd1_h1last6_6_28 | legacy_high_pool | baseline | 118 | 27 | 91 | 1.9512 | 1.5206 | $440.56 | 0.4255 | 0.1661 | 3 | 4 | ok |

## Filter Top By Score

| candidate | pool | filter_name | n | long_n | short_n | pf | test_pf | pnl_usd_001 | avg_way_s_way | avg_body_momentum_signed | positive_years | total_years | sample_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fd1_h1last6_8_28 | legacy_high_pool | way_ge_0.2__body_le_0.0 | 33 | 9 | 24 | 2.4309 | 6.0957 | $180.68 | 0.4476 | -0.3462 | 3 | 4 | ok |
| fd1_h1last6_6_28 | side_extreme_pool | way_ge_0.4__body_le_0.0 | 31 | 14 | 17 | 2.6864 | 5.7961 | $165.07 | 0.5284 | -0.3408 | 3 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | body_mom_le_0.4 | 35 | 17 | 18 | 5.4960 | 3.2027 | $384.48 | 0.4329 | -0.1252 | 4 | 4 | ok |
| fd3_m30sma13_6_28 | legacy_high_pool | gap_mom_le_0.2 | 33 | 6 | 27 | 4.5930 | 4.1140 | $357.24 | 0.4373 | 0.0709 | 3 | 4 | ok |
| fd3_m30sma13_6_28 | legacy_high_pool | close_mom_le_0.2 | 34 | 6 | 28 | 4.7399 | 3.6887 | $371.85 | 0.4444 | 0.0780 | 3 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | way_ge_0.2__body_le_0.4 | 34 | 16 | 18 | 4.4991 | 3.2027 | $299.23 | 0.4403 | -0.1383 | 4 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | close_mom_le_0.6 | 63 | 27 | 36 | 3.1853 | 3.2510 | $462.51 | 0.4449 | 0.1901 | 4 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | gap_mom_le_0.6 | 63 | 27 | 36 | 3.1853 | 3.2510 | $462.51 | 0.4449 | 0.1901 | 4 | 4 | ok |
| fd3_m30sma13_6_28 | legacy_high_pool | gap_mom_le_0.4 | 41 | 10 | 31 | 3.3396 | 3.5426 | $332.18 | 0.4449 | 0.1588 | 3 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | close_mom_le_0.2 | 47 | 19 | 28 | 3.4979 | 3.0158 | $356.13 | 0.4423 | 0.0540 | 4 | 4 | ok |
| fd1_h1last6_6_28 | side_extreme_pool | way_ge_0.2__body_le_0.0 | 49 | 21 | 28 | 2.0431 | 4.3975 | $188.48 | 0.4478 | -0.3675 | 3 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | gap_mom_le_0.2 | 45 | 18 | 27 | 3.3676 | 2.9168 | $337.56 | 0.4389 | 0.0350 | 4 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | close_mom_ge_-0.6 | 66 | 27 | 39 | 2.9874 | 2.8991 | $448.49 | 0.4444 | 0.2357 | 4 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | close_mom_ge_-0.4 | 66 | 27 | 39 | 2.9874 | 2.8991 | $448.49 | 0.4444 | 0.2357 | 4 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | gap_mom_ge_-0.6 | 66 | 27 | 39 | 2.9874 | 2.8991 | $448.49 | 0.4444 | 0.2357 | 4 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | gap_mom_ge_-0.4 | 66 | 27 | 39 | 2.9874 | 2.8991 | $448.49 | 0.4444 | 0.2357 | 4 | 4 | ok |
| fd3_m30sma13_6_28 | legacy_high_pool | close_mom_le_0.4 | 42 | 10 | 32 | 2.9560 | 3.5426 | $313.75 | 0.4448 | 0.1695 | 3 | 4 | ok |
| fd3_m30sma13_6_28 | legacy_high_pool | close_mom_le_0.6 | 46 | 10 | 36 | 3.5372 | 2.9239 | $427.51 | 0.4511 | 0.2192 | 3 | 4 | ok |
| fd3_m30sma13_6_28 | legacy_high_pool | gap_mom_le_0.6 | 46 | 10 | 36 | 3.5372 | 2.9239 | $427.51 | 0.4511 | 0.2192 | 3 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | way_le_0.7 | 66 | 28 | 38 | 2.7677 | 2.8991 | $414.36 | 0.4382 | 0.2253 | 4 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | way_le_0.8 | 66 | 28 | 38 | 2.7677 | 2.8991 | $414.36 | 0.4382 | 0.2253 | 4 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | way_ge_0.2__body_le_0.0 | 42 | 18 | 24 | 2.1391 | 4.0620 | $181.63 | 0.4500 | -0.3531 | 3 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | gap_mom_le_0.4 | 56 | 25 | 31 | 2.9093 | 2.8691 | $353.46 | 0.4402 | 0.1331 | 4 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | body_mom_ge_-0.6 | 63 | 26 | 37 | 2.6171 | 2.9649 | $354.77 | 0.4444 | 0.2820 | 4 | 4 | ok |
| fd3_m30sma13_6_28 | legacy_high_pool | body_mom_le_0.6 | 39 | 9 | 30 | 3.2556 | 2.9988 | $314.85 | 0.4438 | 0.1275 | 3 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | way_le_0.5 | 47 | 20 | 27 | 2.8199 | 2.8828 | $319.93 | 0.3798 | 0.2073 | 4 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | baseline | 67 | 28 | 39 | 2.8759 | 2.6092 | $439.74 | 0.4440 | 0.2215 | 4 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | way_ge_0.0 | 67 | 28 | 39 | 2.8759 | 2.6092 | $439.74 | 0.4440 | 0.2215 | 4 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | way_ge_0.1 | 67 | 28 | 39 | 2.8759 | 2.6092 | $439.74 | 0.4440 | 0.2215 | 4 | 4 | ok |
| fd3_m30sma13_6_28 | side_extreme_pool | way_le_0.9 | 67 | 28 | 39 | 2.8759 | 2.6092 | $439.74 | 0.4440 | 0.2215 | 4 | 4 | ok |

## Filter Top By Actual PnL

| candidate | pool | filter_name | n | long_n | short_n | pf | test_pf | pnl_usd_001 | avg_way_s_way | avg_body_momentum_signed | positive_years | total_years | sample_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fd1_h1last6_8_28 | side_extreme_pool | close_mom_ge_-0.4 | 108 | 38 | 70 | 2.4334 | 1.9237 | $585.95 | 0.4439 | 0.1620 | 4 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | gap_mom_ge_-0.4 | 109 | 39 | 70 | 2.3902 | 1.9237 | $578.56 | 0.4428 | 0.1545 | 4 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | close_mom_ge_-0.6 | 111 | 41 | 70 | 2.3336 | 1.8436 | $568.46 | 0.4404 | 0.1416 | 4 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | gap_mom_ge_-0.6 | 111 | 41 | 70 | 2.3336 | 1.8436 | $568.46 | 0.4404 | 0.1416 | 4 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | way_le_0.9 | 111 | 41 | 70 | 2.3306 | 1.8365 | $567.91 | 0.4348 | 0.1356 | 4 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | close_mom_le_0.6 | 110 | 41 | 69 | 2.3294 | 1.9145 | $565.66 | 0.4403 | 0.1222 | 4 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | gap_mom_le_0.6 | 110 | 41 | 69 | 2.3294 | 1.9145 | $565.66 | 0.4403 | 0.1222 | 4 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | baseline | 112 | 41 | 71 | 2.2954 | 1.8391 | $561.37 | 0.4398 | 0.1344 | 4 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | way_ge_0.0 | 112 | 41 | 71 | 2.2954 | 1.8391 | $561.37 | 0.4398 | 0.1344 | 4 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | way_ge_0.1 | 112 | 41 | 71 | 2.2954 | 1.8391 | $561.37 | 0.4398 | 0.1344 | 4 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | way_le_1.0 | 112 | 41 | 71 | 2.2954 | 1.8391 | $561.37 | 0.4398 | 0.1344 | 4 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | way_le_0.6 | 101 | 35 | 66 | 2.3408 | 2.0110 | $544.29 | 0.4083 | 0.1528 | 4 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | way_le_0.8 | 110 | 41 | 69 | 2.2695 | 1.9279 | $541.86 | 0.4312 | 0.1370 | 4 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | body_mom_ge_-0.4 | 94 | 31 | 63 | 2.5342 | 1.8124 | $539.41 | 0.4449 | 0.2710 | 3 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | way_le_0.7 | 107 | 38 | 69 | 2.2745 | 1.8610 | $536.84 | 0.4223 | 0.1326 | 4 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | gap_mom_ge_-0.2 | 102 | 34 | 68 | 2.3439 | 1.6643 | $535.70 | 0.4460 | 0.1987 | 4 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | body_mom_ge_-0.6 | 104 | 37 | 67 | 2.3181 | 1.8725 | $534.37 | 0.4413 | 0.1991 | 3 | 4 | ok |
| fd1_h1last6_6_28 | side_extreme_pool | close_mom_ge_-0.4 | 140 | 50 | 90 | 2.0367 | 1.5030 | $533.56 | 0.4420 | 0.1852 | 4 | 4 | ok |
| fd1_h1last6_6_28 | side_extreme_pool | gap_mom_ge_-0.4 | 141 | 51 | 90 | 2.0079 | 1.6013 | $526.18 | 0.4412 | 0.1793 | 4 | 4 | ok |
| fd1_h1last6_6_28 | side_extreme_pool | way_le_0.9 | 142 | 52 | 90 | 1.9742 | 1.4471 | $517.27 | 0.4310 | 0.1613 | 4 | 4 | ok |
| fd1_h1last6_6_28 | side_extreme_pool | close_mom_ge_-0.6 | 143 | 53 | 90 | 1.9697 | 1.4517 | $516.07 | 0.4393 | 0.1689 | 4 | 4 | ok |
| fd1_h1last6_6_28 | side_extreme_pool | gap_mom_ge_-0.6 | 143 | 53 | 90 | 1.9697 | 1.4517 | $516.07 | 0.4393 | 0.1689 | 4 | 4 | ok |
| fd1_h1last6_6_28 | side_extreme_pool | close_mom_le_0.6 | 142 | 53 | 89 | 1.9659 | 1.5077 | $513.27 | 0.4392 | 0.1541 | 4 | 4 | ok |
| fd1_h1last6_6_28 | side_extreme_pool | gap_mom_le_0.6 | 142 | 53 | 89 | 1.9659 | 1.5077 | $513.27 | 0.4392 | 0.1541 | 4 | 4 | ok |
| fd1_h1last6_8_28 | side_extreme_pool | close_mom_ge_-0.2 | 99 | 33 | 66 | 2.3470 | 1.7118 | $510.64 | 0.4486 | 0.2218 | 3 | 4 | ok |

## Output Files

- `way_momentum_enriched_trades.csv`
- `way_momentum_baseline_summary.csv`
- `way_momentum_filter_summary.csv`
