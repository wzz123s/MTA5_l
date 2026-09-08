# MT5 会话逐笔差异对比

- 会话编号：`3`
- 回测区间：`2018-01-01 00:00:00` 到 `2026-07-07 00:00:00`
- 参数摘要：`top34% + Stage 2.0/1.5/4.0 + stop [5,35]`
- 是否当前主线参数：`是`
- Python 复算模式：`EA可执行诊断口径`
- 输出目录：`黄金/30m2H策略\data\validation\mt5_log_session_diff_v326_full_20260712_m30postn_strict_veto_initfix_ea_diag\session_03`

## 汇总

- MT5 信号数：`78`
- Python 执行信号数：`60`
- 共同信号数：`34`
- 共同但字段不一致：`33`
- MT5 独有：`44`
- Python 独有：`26`

## 共同但不一致

| anchor_time_mt5     | dir_mt5   | trigger_mt5   | trigger_python   | mode_raw_mt5                        | mode_raw_python   |   mt5_stop_dist |   python_stop_dist_1dp | 差异说明                                                                                     |
|:--------------------|:----------|:--------------|:-----------------|:------------------------------------|:------------------|----------------:|-----------------------:|:---------------------------------------------------------------------------------------------|
| 2020-03-06 21:30:00 | L         | M30 CLOSE     | M30 CLOSE        | cross                               | cross             |            13.7 |                   13.9 | 止损: MT5=13.7 / Python=13.9                                                                 |
| 2020-03-17 17:30:00 | L         | M30 CLOSE     | M30 CLOSE        | post_n4                             | post_n4           |            35   |                   34.2 | 止损: MT5=35.0 / Python=34.2                                                                 |
| 2020-03-18 09:30:00 | S         | M30 CLOSE     | M30 CLOSE        | post_n4                             | post_n4           |            23.9 |                   23   | 止损: MT5=23.9 / Python=23.0                                                                 |
| 2020-03-20 03:30:00 | L         | M30 CLOSE     | M30 CLOSE        | cross                               | cross             |             8.1 |                    7.8 | 止损: MT5=8.1 / Python=7.8                                                                   |
| 2020-03-20 19:30:00 | S         | M30 CLOSE     | M30 CLOSE        | post_n4                             | post_n4           |             8.8 |                    8.7 | 止损: MT5=8.8 / Python=8.7                                                                   |
| 2020-03-25 09:30:00 | S         | M30 CLOSE     | M30 CLOSE        | post_n6                             | post_n6           |             7.9 |                    8.3 | 止损: MT5=7.9 / Python=8.3                                                                   |
| 2020-03-25 12:00:00 | L         | M30 CLOSE     | M30 CLOSE        | cross                               | cross             |             8.7 |                    9.6 | 止损: MT5=8.7 / Python=9.6                                                                   |
| 2020-03-26 13:30:00 | L         | M30 CLOSE     | M30 CLOSE        | post_n4                             | post_n4           |            11.5 |                   11.4 | 止损: MT5=11.5 / Python=11.4                                                                 |
| 2020-07-28 07:30:00 | S         | M30 CLOSE     | M30 CLOSE        | cross                               | cross             |             8.9 |                   12.2 | 止损: MT5=8.9 / Python=12.2                                                                  |
| 2020-07-31 15:00:00 | S         | M30 CLOSE     | M30 CLOSE        | pre_cross                           | pre_cross         |             6.7 |                    7.1 | 止损: MT5=6.7 / Python=7.1                                                                   |
| 2020-08-12 21:30:00 | S         | M30 CLOSE     | M30 CLOSE        | cross                               | cross             |            24.7 |                   25.6 | 止损: MT5=24.7 / Python=25.6                                                                 |
| 2021-06-18 15:30:00 | S         | M30 CLOSE     | M30 CLOSE        | post_n3                             | post_n3           |            11.9 |                   12   | 止损: MT5=11.9 / Python=12.0                                                                 |
| 2021-08-10 12:00:00 | S         | M30 CLOSE     | M30 CLOSE        | post_n4                             | post_n4           |             5.3 |                    5.4 | 止损: MT5=5.3 / Python=5.4                                                                   |
| 2022-03-07 21:30:00 | L         | M30 CLOSE     | M30 CLOSE        | post_n3                             | post_n3           |             9.8 |                    9.7 | 止损: MT5=9.8 / Python=9.7                                                                   |
| 2022-03-09 11:30:00 | S         | M30 CLOSE     | M30 CLOSE        | post_n2                             | post_n2           |            23.3 |                   23.2 | 止损: MT5=23.3 / Python=23.2                                                                 |
| 2022-11-08 18:00:00 | L         | M15 SLOT1     | M15 SLOT1        | post_n5_m15_slot1_replace_or_rescue | post_n6           |            32.9 |                   32.1 | 模式: MT5=post_n5_m15_slot1_replace_or_rescue / Python=post_n6；止损: MT5=32.9 / Python=32.1 |
| 2022-11-10 15:30:00 | L         | M30 CLOSE     | M30 CLOSE        | post_n2                             | post_n2           |            24   |                   23   | 止损: MT5=24.0 / Python=23.0                                                                 |
| 2024-04-03 09:00:00 | S         | M30 CLOSE     | M30 CLOSE        | pre_cross                           | pre_cross         |             6.4 |                    5.9 | 止损: MT5=6.4 / Python=5.9                                                                   |
| 2024-04-08 14:00:00 | S         | M30 CLOSE     | M30 CLOSE        | pre_cross                           | pre_cross         |             5.7 |                    6.5 | 止损: MT5=5.7 / Python=6.5                                                                   |
| 2024-04-08 19:30:00 | L         | M30 CLOSE     | M30 CLOSE        | cross                               | cross             |             7.3 |                    7.2 | 止损: MT5=7.3 / Python=7.2                                                                   |

## MT5 独有样本

| mt5_raw_anchor_time   | anchor_time         | dir   | trigger   | mode_raw                              |   mt5_stop_dist |
|:----------------------|:--------------------|:------|:----------|:--------------------------------------|----------------:|
| 2020-03-08 22:00:00   | 2020-03-08 23:30:00 | L     | M30 CLOSE | post_n6                               |            19.9 |
| 2020-03-13 09:30:00   | 2020-03-13 11:00:00 | L     | M15 SLOT1 | post_n4_m15_slot1_replace_or_rescue   |             5.6 |
| 2020-03-13 14:30:00   | 2020-03-13 16:00:00 | S     | M30 CLOSE | cross                                 |            10.4 |
| 2020-03-13 16:00:00   | 2020-03-13 17:30:00 | S     | M15 SLOT1 | post_n3_m15_slot1_replace_or_rescue   |            33.5 |
| 2020-03-16 23:00:00   | 2020-03-17 00:30:00 | L     | M30 CLOSE | cross                                 |             5.1 |
| 2020-03-17 02:30:00   | 2020-03-17 04:00:00 | S     | M30 CLOSE | cross                                 |            15.1 |
| 2020-07-28 08:00:00   | 2020-07-28 09:30:00 | S     | M15 SLOT1 | post_n4_m15_slot1_replace_or_rescue   |            29.1 |
| 2020-08-04 17:30:00   | 2020-08-04 19:00:00 | L     | M15 SLOT1 | post_n6_m15_slot1_replace_or_rescue   |            19.6 |
| 2021-01-11 14:30:00   | 2021-01-11 16:00:00 | S     | M15 SLOT1 | post_n2_m15_slot1_replace_or_rescue   |             9.7 |
| 2021-03-04 19:00:00   | 2021-03-04 20:30:00 | S     | M30 CLOSE | post_n4                               |            20.3 |
| 2021-06-16 22:30:00   | 2021-06-17 00:00:00 | S     | M15 SLOT1 | post_n6_m15_slot1_replace_or_rescue   |            33   |
| 2021-11-10 15:00:00   | 2021-11-10 16:30:00 | L     | M30 CLOSE | post_n3                               |            29.2 |
| 2022-03-08 01:30:00   | 2022-03-08 03:00:00 | S     | M30 CLOSE | pre_cross                             |             9.7 |
| 2022-03-08 08:30:00   | 2022-03-08 10:00:00 | L     | M15 SLOT1 | post_n5_m15_slot1_replace_or_rescue   |            15.1 |
| 2022-11-14 16:00:00   | 2022-11-14 17:30:00 | L     | M30 CLOSE | post_n4                               |             8.7 |
| 2023-03-15 13:00:00   | 2023-03-15 14:30:00 | L     | M30 CLOSE | post_n4                               |            22.1 |
| 2023-03-20 11:00:00   | 2023-03-20 12:30:00 | S     | M15 SLOT1 | pre_cross_m15_slot1_replace_or_rescue |             6.5 |
| 2024-03-07 15:00:00   | 2024-03-07 16:30:00 | S     | M15 SLOT1 | pre_cross_m15_slot1_replace_or_rescue |             6.1 |
| 2024-04-03 16:00:00   | 2024-04-03 17:30:00 | L     | M30 CLOSE | post_n3                               |             9.5 |
| 2024-04-09 15:30:00   | 2024-04-09 17:00:00 | S     | M15 SLOT1 | pre_cross_m15_slot1_replace_or_rescue |             6.9 |

## Python 独有样本

| anchor_time         | dir   | trigger   | mode_raw   |   python_stop_dist_1dp | variant                 |
|:--------------------|:------|:----------|:-----------|-----------------------:|:------------------------|
| 2019-08-13 15:30:00 | S     | M30 CLOSE | cross      |                   35.2 | m30_base                |
| 2020-01-06 17:30:00 | S     | M30 CLOSE | cross      |                    9   | m30_base                |
| 2020-02-24 21:00:00 | S     | M30 CLOSE | cross      |                   16.1 | m30_base                |
| 2020-03-13 09:30:00 | L     | M30 CLOSE | cross      |                   13.8 | m30_base                |
| 2020-03-13 15:30:00 | S     | M30 CLOSE | pre_cross  |                    9.7 | m30_base                |
| 2021-03-04 21:00:00 | S     | M30 CLOSE | post_n5    |                   13.3 | m30_base                |
| 2021-06-18 09:30:00 | L     | M30 CLOSE | post_n5    |                    8.3 | m30_base                |
| 2022-11-14 18:00:00 | L     | M15 SLOT1 | post_n5    |                    8.2 | ea_slot1_runtime_rescue |
| 2022-11-16 11:30:00 | L     | M30 CLOSE | post_n4    |                    6.6 | ea_slot1_replace        |
| 2023-03-15 15:00:00 | L     | M15 SLOT1 | post_n5    |                   20.8 | ea_slot1_replace        |
| 2023-03-21 09:30:00 | S     | M30 CLOSE | post_n3    |                    8.3 | ea_slot1_replace        |
| 2023-12-04 08:30:00 | S     | M15 SLOT1 | pre_cross  |                    5.6 | ea_slot1_runtime_rescue |
| 2024-04-03 18:00:00 | L     | M15 SLOT1 | post_n4    |                    8.3 | ea_slot1_replace        |
| 2024-07-17 17:30:00 | S     | M15 SLOT1 | cross      |                    6.3 | ea_slot1_replace        |
| 2025-04-14 00:30:00 | S     | M15 SLOT1 | pre_cross  |                    7.3 | ea_slot1_replace        |
| 2025-04-21 02:00:00 | L     | M15 SLOT1 | post_n5    |                   20.7 | ea_slot1_replace        |
| 2025-04-22 16:00:00 | S     | M15 SLOT1 | post_n4    |                   30.5 | ea_slot1_replace        |
| 2025-09-30 09:30:00 | S     | M15 SLOT1 | pre_cross  |                    5.4 | ea_slot1_runtime_rescue |
| 2025-10-09 03:00:00 | S     | M15 SLOT1 | post_n5    |                   10.6 | ea_slot1_runtime_rescue |
| 2025-10-09 15:30:00 | S     | M30 CLOSE | pre_cross  |                   21.2 | ea_slot1_replace        |

## 输出文件

- `mt5_signals.csv`
- `python_executed_signals.csv`
- `shared_signals.csv`
- `shared_mismatch.csv`
- `mt5_only_signals.csv`
- `python_only_signals.csv`
