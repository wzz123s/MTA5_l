# 1H_M30_4H delayed entry + M30 SMA13 stop test

Date: 2026-07-25

## Rules

- Opportunity layer is rechecked at entry time: short when `H1roll4 high vs H4 SMA55 >= 2%`, long when `<= -2%`.
- `fixed_delay_1` is the current next-M30-open baseline after the cross close.
- `fixed_delay_2..12` enters at the open of the k-th M30 bar after the cross bar.
- `window_2_to_n_first_valid` enters on the first bar in `2..n` whose entry price is on the valid side of the SMA13 stop.
- Stop price uses the last closed M30 SMA13 at entry open: `m30_entry_prev_closed_sma13`.
- Exit remains opposite M30 cross next open, unless the SMA13 stop is hit first.
- USD PnL is `pnl_points * 100 * 0.01 lot`; spread, slippage, and commission are not deducted.

## Fixed Delay Summary

| entry_rule | third_filter | stop_range | n | long_n | short_n | pf | test_pf | pnl_usd_001 | stop_hits | stop_hit_rate_pct | avg_entry_delay_bars | avg_stop_distance | positive_years | total_years | sample_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fixed_delay_12 | none | all | 95 | 27 | 68 | 1.1505 | 4.8653 | $44.64 | 68 | 71.5789 | 12.0000 | 4.8066 | 3 | 4 | ok |
| fixed_delay_10 | none | all | 105 | 30 | 75 | 1.3713 | 2.4187 | $129.21 | 74 | 70.4762 | 10.0000 | 4.9850 | 3 | 4 | ok |
| fixed_delay_8 | none | all | 124 | 34 | 90 | 1.4194 | 2.2416 | $166.34 | 89 | 71.7742 | 8.0000 | 5.3727 | 3 | 4 | ok |
| fixed_delay_7 | none | all | 141 | 37 | 104 | 1.2870 | 2.0798 | $131.56 | 100 | 70.9220 | 7.0000 | 5.5632 | 3 | 4 | ok |
| fixed_delay_9 | none | all | 115 | 31 | 84 | 1.3165 | 1.8365 | $116.59 | 85 | 73.9130 | 9.0000 | 4.6836 | 3 | 4 | ok |
| fixed_delay_3 | none | all | 199 | 51 | 148 | 1.3688 | 1.1987 | $211.21 | 144 | 72.3618 | 3.0000 | 5.0869 | 3 | 4 | ok |
| fixed_delay_6 | none | all | 162 | 39 | 123 | 1.2470 | 1.4591 | $122.15 | 119 | 73.4568 | 6.0000 | 5.1406 | 3 | 4 | ok |
| fixed_delay_5 | none | all | 172 | 43 | 129 | 1.1171 | 1.5648 | $66.99 | 126 | 73.2558 | 5.0000 | 5.4884 | 3 | 4 | ok |
| fixed_delay_4 | none | all | 185 | 48 | 137 | 1.2697 | 1.2482 | $153.69 | 135 | 72.9730 | 4.0000 | 5.1743 | 3 | 4 | ok |
| fixed_delay_2 | none | all | 236 | 64 | 172 | 1.2261 | 1.2275 | $158.15 | 178 | 75.4237 | 2.0000 | 4.7218 | 3 | 4 | ok |
| fixed_delay_1 | none | all | 266 | 77 | 189 | 1.0521 | 1.0392 | $44.35 | 204 | 76.6917 | 1.0000 | 4.6701 | 2 | 4 | ok |
| fixed_delay_11 | none | all | 97 | 30 | 67 | 0.8419 | 3.3970 | $-53.59 | 70 | 72.1649 | 11.0000 | 5.1933 | 2 | 4 | ok |

## Window 2..n Summary

| entry_rule | third_filter | stop_range | n | long_n | short_n | pf | test_pf | pnl_usd_001 | stop_hits | stop_hit_rate_pct | avg_entry_delay_bars | avg_stop_distance | positive_years | total_years | sample_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| window_2_to_2_first_valid | none | all | 236 | 64 | 172 | 1.2261 | 1.2275 | $158.15 | 178 | 75.4237 | 2.0000 | 4.7218 | 3 | 4 | ok |
| window_2_to_10_first_valid | none | all | 237 | 64 | 173 | 1.2245 | 1.2198 | $157.23 | 179 | 75.5274 | 2.0042 | 4.7058 | 3 | 4 | ok |
| window_2_to_11_first_valid | none | all | 237 | 64 | 173 | 1.2245 | 1.2198 | $157.23 | 179 | 75.5274 | 2.0042 | 4.7058 | 3 | 4 | ok |
| window_2_to_12_first_valid | none | all | 237 | 64 | 173 | 1.2245 | 1.2198 | $157.23 | 179 | 75.5274 | 2.0042 | 4.7058 | 3 | 4 | ok |
| window_2_to_3_first_valid | none | all | 237 | 64 | 173 | 1.2245 | 1.2198 | $157.23 | 179 | 75.5274 | 2.0042 | 4.7058 | 3 | 4 | ok |
| window_2_to_4_first_valid | none | all | 237 | 64 | 173 | 1.2245 | 1.2198 | $157.23 | 179 | 75.5274 | 2.0042 | 4.7058 | 3 | 4 | ok |
| window_2_to_5_first_valid | none | all | 237 | 64 | 173 | 1.2245 | 1.2198 | $157.23 | 179 | 75.5274 | 2.0042 | 4.7058 | 3 | 4 | ok |
| window_2_to_6_first_valid | none | all | 237 | 64 | 173 | 1.2245 | 1.2198 | $157.23 | 179 | 75.5274 | 2.0042 | 4.7058 | 3 | 4 | ok |
| window_2_to_7_first_valid | none | all | 237 | 64 | 173 | 1.2245 | 1.2198 | $157.23 | 179 | 75.5274 | 2.0042 | 4.7058 | 3 | 4 | ok |
| window_2_to_8_first_valid | none | all | 237 | 64 | 173 | 1.2245 | 1.2198 | $157.23 | 179 | 75.5274 | 2.0042 | 4.7058 | 3 | 4 | ok |
| window_2_to_9_first_valid | none | all | 237 | 64 | 173 | 1.2245 | 1.2198 | $157.23 | 179 | 75.5274 | 2.0042 | 4.7058 | 3 | 4 | ok |

## Delayed Entry + 1H bias5&bias13

| entry_rule | third_filter | stop_range | n | long_n | short_n | pf | test_pf | pnl_usd_001 | stop_hits | stop_hit_rate_pct | avg_entry_delay_bars | avg_stop_distance | positive_years | total_years | sample_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fixed_delay_12 | 1h_bias5_13_pos | all | 79 | 22 | 57 | 1.2107 | 4.8779 | $59.17 | 53 | 67.0886 | 12.0000 | 5.5687 | 3 | 4 | ok |
| fixed_delay_7 | 1h_bias5_13_pos | all | 110 | 30 | 80 | 1.4740 | 2.3203 | $189.71 | 69 | 62.7273 | 7.0000 | 6.6024 | 3 | 4 | ok |
| fixed_delay_6 | 1h_bias5_13_pos | all | 121 | 31 | 90 | 1.4111 | 2.0681 | $174.15 | 80 | 66.1157 | 6.0000 | 6.2598 | 3 | 4 | ok |
| fixed_delay_1 | 1h_bias5_13_pos | all | 135 | 31 | 104 | 1.5138 | 1.9248 | $233.35 | 97 | 71.8519 | 1.0000 | 5.2592 | 2 | 4 | ok |
| fixed_delay_8 | 1h_bias5_13_pos | all | 93 | 29 | 64 | 1.3958 | 1.7191 | $138.50 | 60 | 64.5161 | 8.0000 | 6.6213 | 3 | 4 | ok |
| fixed_delay_10 | 1h_bias5_13_pos | all | 83 | 22 | 61 | 1.2297 | 1.8781 | $73.48 | 55 | 66.2651 | 10.0000 | 5.8869 | 3 | 4 | ok |
| fixed_delay_2 | 1h_bias5_13_pos | all | 172 | 45 | 127 | 1.3813 | 1.1889 | $213.00 | 122 | 70.9302 | 2.0000 | 5.5192 | 3 | 4 | ok |
| window_2_to_10_first_valid | 1h_bias5_13_pos | all | 172 | 45 | 127 | 1.3813 | 1.1889 | $213.00 | 122 | 70.9302 | 2.0000 | 5.5192 | 3 | 4 | ok |
| window_2_to_11_first_valid | 1h_bias5_13_pos | all | 172 | 45 | 127 | 1.3813 | 1.1889 | $213.00 | 122 | 70.9302 | 2.0000 | 5.5192 | 3 | 4 | ok |
| window_2_to_12_first_valid | 1h_bias5_13_pos | all | 172 | 45 | 127 | 1.3813 | 1.1889 | $213.00 | 122 | 70.9302 | 2.0000 | 5.5192 | 3 | 4 | ok |
| window_2_to_2_first_valid | 1h_bias5_13_pos | all | 172 | 45 | 127 | 1.3813 | 1.1889 | $213.00 | 122 | 70.9302 | 2.0000 | 5.5192 | 3 | 4 | ok |
| window_2_to_3_first_valid | 1h_bias5_13_pos | all | 172 | 45 | 127 | 1.3813 | 1.1889 | $213.00 | 122 | 70.9302 | 2.0000 | 5.5192 | 3 | 4 | ok |
| window_2_to_4_first_valid | 1h_bias5_13_pos | all | 172 | 45 | 127 | 1.3813 | 1.1889 | $213.00 | 122 | 70.9302 | 2.0000 | 5.5192 | 3 | 4 | ok |
| window_2_to_5_first_valid | 1h_bias5_13_pos | all | 172 | 45 | 127 | 1.3813 | 1.1889 | $213.00 | 122 | 70.9302 | 2.0000 | 5.5192 | 3 | 4 | ok |
| window_2_to_6_first_valid | 1h_bias5_13_pos | all | 172 | 45 | 127 | 1.3813 | 1.1889 | $213.00 | 122 | 70.9302 | 2.0000 | 5.5192 | 3 | 4 | ok |
| window_2_to_7_first_valid | 1h_bias5_13_pos | all | 172 | 45 | 127 | 1.3813 | 1.1889 | $213.00 | 122 | 70.9302 | 2.0000 | 5.5192 | 3 | 4 | ok |
| window_2_to_8_first_valid | 1h_bias5_13_pos | all | 172 | 45 | 127 | 1.3813 | 1.1889 | $213.00 | 122 | 70.9302 | 2.0000 | 5.5192 | 3 | 4 | ok |
| window_2_to_9_first_valid | 1h_bias5_13_pos | all | 172 | 45 | 127 | 1.3813 | 1.1889 | $213.00 | 122 | 70.9302 | 2.0000 | 5.5192 | 3 | 4 | ok |
| fixed_delay_5 | 1h_bias5_13_pos | all | 130 | 30 | 100 | 1.1482 | 1.4933 | $74.16 | 87 | 66.9231 | 5.0000 | 6.6165 | 3 | 4 | ok |
| fixed_delay_3 | 1h_bias5_13_pos | all | 155 | 37 | 118 | 1.4208 | 1.0511 | $207.59 | 104 | 67.0968 | 3.0000 | 5.9695 | 3 | 4 | ok |

## Delayed Entry + 1H bias5&bias13 + Stop Distance Top

| entry_rule | third_filter | stop_range | n | long_n | short_n | pf | test_pf | pnl_usd_001 | stop_hits | stop_hit_rate_pct | avg_entry_delay_bars | avg_stop_distance | positive_years | total_years | sample_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fixed_delay_7 | 1h_bias5_13_pos | 6-28pt | 36 | 12 | 24 | 1.9226 | 5.3447 | $148.21 | 12 | 33.3333 | 7.0000 | 9.8921 | 3 | 4 | ok |
| fixed_delay_3 | 1h_bias5_13_pos | 8-24pt | 33 | 10 | 23 | 2.8494 | 4.3922 | $241.47 | 9 | 27.2727 | 3.0000 | 11.5665 | 3 | 4 | ok |
| fixed_delay_7 | 1h_bias5_13_pos | 4-8pt | 41 | 12 | 29 | 2.7951 | 4.2734 | $231.49 | 22 | 53.6585 | 7.0000 | 5.6189 | 3 | 4 | ok |
| fixed_delay_7 | 1h_bias5_13_pos | 6-24pt | 35 | 11 | 24 | 1.4478 | 5.3447 | $71.93 | 12 | 34.2857 | 7.0000 | 9.4760 | 3 | 4 | ok |
| fixed_delay_3 | 1h_bias5_13_pos | 8-28pt | 34 | 10 | 24 | 2.9610 | 3.9158 | $256.05 | 9 | 26.4706 | 3.0000 | 11.9616 | 3 | 4 | ok |
| fixed_delay_3 | 1h_bias5_13_pos | 8-32pt | 34 | 10 | 24 | 2.9610 | 3.9158 | $256.05 | 9 | 26.4706 | 3.0000 | 11.9616 | 3 | 4 | ok |
| fixed_delay_12 | 1h_bias5_13_pos | 2-22pt | 61 | 18 | 43 | 1.0064 | 5.8680 | $1.47 | 39 | 63.9344 | 12.0000 | 5.9794 | 2 | 4 | ok |
| fixed_delay_3 | 1h_bias5_13_pos | 8-40pt | 36 | 11 | 25 | 2.7101 | 3.9158 | $258.70 | 9 | 25.0000 | 3.0000 | 13.3286 | 3 | 4 | ok |
| fixed_delay_12 | 1h_bias5_13_pos | 0-22pt | 77 | 21 | 56 | 1.3904 | 4.8779 | $95.48 | 52 | 67.5325 | 12.0000 | 4.9784 | 3 | 4 | ok |
| fixed_delay_7 | 1h_bias5_13_pos | 4-28pt | 60 | 18 | 42 | 2.1970 | 3.9982 | $287.82 | 29 | 48.3333 | 7.0000 | 7.8590 | 3 | 4 | ok |
| fixed_delay_12 | 1h_bias5_13_pos | 2-16pt | 59 | 17 | 42 | 1.1871 | 5.4133 | $36.36 | 38 | 64.4068 | 12.0000 | 5.5381 | 2 | 4 | ok |
| fixed_delay_7 | 1h_bias5_13_pos | 6-32pt | 37 | 12 | 25 | 1.7455 | 4.5366 | $131.91 | 12 | 32.4324 | 7.0000 | 10.4498 | 3 | 4 | ok |
| fixed_delay_7 | 1h_bias5_13_pos | 6-40pt | 37 | 12 | 25 | 1.7455 | 4.5366 | $131.91 | 12 | 32.4324 | 7.0000 | 10.4498 | 3 | 4 | ok |
| fixed_delay_12 | 1h_bias5_13_pos | 0-24pt | 78 | 22 | 56 | 1.2692 | 4.8779 | $72.12 | 53 | 67.9487 | 12.0000 | 5.2140 | 3 | 4 | ok |
| fixed_delay_12 | 1h_bias5_13_pos | 0-28pt | 78 | 22 | 56 | 1.2692 | 4.8779 | $72.12 | 53 | 67.9487 | 12.0000 | 5.2140 | 3 | 4 | ok |
| fixed_delay_12 | 1h_bias5_13_pos | 0-32pt | 78 | 22 | 56 | 1.2692 | 4.8779 | $72.12 | 53 | 67.9487 | 12.0000 | 5.2140 | 3 | 4 | ok |
| fixed_delay_7 | 1h_bias5_13_pos | 4-10pt | 51 | 16 | 35 | 2.0632 | 4.1402 | $203.37 | 28 | 54.9020 | 7.0000 | 6.2796 | 3 | 4 | ok |
| fixed_delay_12 | 1h_bias5_13_pos | 2-18pt | 60 | 18 | 42 | 1.0959 | 5.4133 | $20.19 | 39 | 65.0000 | 12.0000 | 5.7154 | 2 | 4 | ok |
| fixed_delay_12 | 1h_bias5_13_pos | 2-20pt | 60 | 18 | 42 | 1.0959 | 5.4133 | $20.19 | 39 | 65.0000 | 12.0000 | 5.7154 | 2 | 4 | ok |
| fixed_delay_12 | 1h_bias5_13_pos | 0-16pt | 75 | 20 | 55 | 1.6219 | 4.5000 | $130.37 | 51 | 68.0000 | 12.0000 | 4.6045 | 3 | 4 | ok |
| fixed_delay_12 | 1h_bias5_13_pos | 0-40pt | 79 | 22 | 57 | 1.2107 | 4.8779 | $59.17 | 53 | 67.0886 | 12.0000 | 5.5687 | 3 | 4 | ok |
| fixed_delay_12 | 1h_bias5_13_pos | 0-18pt | 76 | 21 | 55 | 1.5057 | 4.5000 | $114.19 | 52 | 68.4211 | 12.0000 | 4.7567 | 3 | 4 | ok |
| fixed_delay_12 | 1h_bias5_13_pos | 0-20pt | 76 | 21 | 55 | 1.5057 | 4.5000 | $114.19 | 52 | 68.4211 | 12.0000 | 4.7567 | 3 | 4 | ok |
| fixed_delay_7 | 1h_bias5_13_pos | 6-12pt | 30 | 10 | 20 | 1.3723 | 4.7279 | $48.05 | 12 | 40.0000 | 7.0000 | 7.9127 | 3 | 4 | ok |
| fixed_delay_7 | 1h_bias5_13_pos | 6-14pt | 30 | 10 | 20 | 1.3723 | 4.7279 | $48.05 | 12 | 40.0000 | 7.0000 | 7.9127 | 3 | 4 | ok |

## Delayed Entry + 1H bias5&bias13 + Stop Distance Highest PnL

| entry_rule | third_filter | stop_range | n | long_n | short_n | pf | test_pf | pnl_usd_001 | stop_hits | stop_hit_rate_pct | avg_entry_delay_bars | avg_stop_distance | positive_years | total_years | sample_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fixed_delay_3 | 1h_bias5_13_pos | 6-40pt | 52 | 12 | 40 | 2.9219 | 2.3121 | $407.40 | 16 | 30.7692 | 3.0000 | 11.4109 | 3 | 4 | ok |
| fixed_delay_3 | 1h_bias5_13_pos | 6-28pt | 50 | 11 | 39 | 3.1162 | 2.4490 | $404.75 | 16 | 32.0000 | 3.0000 | 10.4047 | 3 | 4 | ok |
| fixed_delay_3 | 1h_bias5_13_pos | 6-32pt | 50 | 11 | 39 | 3.1162 | 2.4490 | $404.75 | 16 | 32.0000 | 3.0000 | 10.4047 | 3 | 4 | ok |
| fixed_delay_3 | 1h_bias5_13_pos | 6-24pt | 49 | 11 | 38 | 3.0399 | 2.4490 | $390.17 | 16 | 32.6531 | 3.0000 | 10.1068 | 3 | 4 | ok |
| fixed_delay_3 | 1h_bias5_13_pos | 4-40pt | 82 | 15 | 67 | 1.9686 | 1.5501 | $319.92 | 38 | 46.3415 | 3.0000 | 9.0696 | 3 | 4 | ok |
| fixed_delay_3 | 1h_bias5_13_pos | 4-28pt | 80 | 14 | 66 | 2.0248 | 1.6534 | $317.27 | 38 | 47.5000 | 3.0000 | 8.3821 | 3 | 4 | ok |
| fixed_delay_3 | 1h_bias5_13_pos | 4-32pt | 80 | 14 | 66 | 2.0248 | 1.6534 | $317.27 | 38 | 47.5000 | 3.0000 | 8.3821 | 3 | 4 | ok |
| fixed_delay_3 | 1h_bias5_13_pos | 4-24pt | 79 | 14 | 65 | 1.9777 | 1.6534 | $302.69 | 38 | 48.1013 | 3.0000 | 8.1718 | 3 | 4 | ok |
| fixed_delay_1 | 1h_bias5_13_pos | 2-20pt | 113 | 24 | 89 | 1.7524 | 2.1995 | $295.20 | 77 | 68.1416 | 1.0000 | 5.6469 | 2 | 4 | ok |
| fixed_delay_4 | 1h_bias5_13_pos | 6-24pt | 51 | 9 | 42 | 2.2552 | 1.9980 | $292.67 | 22 | 43.1373 | 4.0000 | 9.7679 | 3 | 4 | ok |
| fixed_delay_4 | 1h_bias5_13_pos | 6-28pt | 51 | 9 | 42 | 2.2552 | 1.9980 | $292.67 | 22 | 43.1373 | 4.0000 | 9.7679 | 3 | 4 | ok |
| fixed_delay_4 | 1h_bias5_13_pos | 6-32pt | 51 | 9 | 42 | 2.2552 | 1.9980 | $292.67 | 22 | 43.1373 | 4.0000 | 9.7679 | 3 | 4 | ok |
| fixed_delay_7 | 1h_bias5_13_pos | 4-28pt | 60 | 18 | 42 | 2.1970 | 3.9982 | $287.82 | 29 | 48.3333 | 7.0000 | 7.8590 | 3 | 4 | ok |
| fixed_delay_1 | 1h_bias5_13_pos | 2-18pt | 112 | 24 | 88 | 1.7195 | 2.1995 | $282.29 | 77 | 68.7500 | 1.0000 | 5.5302 | 2 | 4 | ok |
| fixed_delay_3 | 1h_bias5_13_pos | 6-16pt | 45 | 9 | 36 | 2.6183 | 1.5107 | $277.78 | 15 | 33.3333 | 3.0000 | 9.1880 | 3 | 4 | ok |
| fixed_delay_4 | 1h_bias5_13_pos | 6-20pt | 50 | 9 | 41 | 2.1903 | 2.1826 | $277.52 | 22 | 44.0000 | 4.0000 | 9.5122 | 3 | 4 | ok |
| fixed_delay_4 | 1h_bias5_13_pos | 6-22pt | 50 | 9 | 41 | 2.1903 | 2.1826 | $277.52 | 22 | 44.0000 | 4.0000 | 9.5122 | 3 | 4 | ok |
| fixed_delay_3 | 1h_bias5_13_pos | 6-18pt | 46 | 10 | 36 | 2.6003 | 1.5662 | $276.60 | 15 | 32.6087 | 3.0000 | 9.3710 | 3 | 4 | ok |
| fixed_delay_1 | 1h_bias5_13_pos | 2-22pt | 114 | 24 | 90 | 1.6614 | 1.9602 | $273.71 | 78 | 68.4211 | 1.0000 | 5.7858 | 2 | 4 | ok |
| fixed_delay_3 | 1h_bias5_13_pos | 6-14pt | 43 | 9 | 34 | 2.6888 | 1.6021 | $273.11 | 15 | 34.8837 | 3.0000 | 8.9196 | 3 | 4 | ok |

## Output Files

- `delayed_entry_all_trades.csv`
- `delayed_entry_delay_summary.csv`
- `delayed_entry_third_filter_summary.csv`
- `delayed_entry_stop_range_summary.csv`
