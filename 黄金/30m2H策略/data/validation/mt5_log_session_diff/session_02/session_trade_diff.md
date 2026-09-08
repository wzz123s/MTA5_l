# MT5 缓存信号逐笔差异对比

- 回测区间：`2018-01-01 00:00:00` 到 `2026-07-04 00:00:00`
- 参数摘要：`top30% + Stage 1.2/2.0/3.0 + stop [5,35]`
- Python 复算模式：`EA可执行诊断口径`
- 输出目录：`F:\use_code\MTA5\黄金/30m2H策略\data\validation\mt5_log_session_diff\session_02`

## 汇总

- MT5 信号数：`32`
- Python 执行信号数：`55`
- 共同信号数：`18`
- 共同但字段不一致：`18`
- MT5 独有：`14`
- Python 独有：`37`

## 共同但不一致

| anchor_time_mt5     | dir_mt5   | trigger_mt5   | trigger_python   | mode_raw_mt5                          | mode_raw_python   |   mt5_stop_dist |   python_stop_dist_1dp | 差异说明                     |
|:--------------------|:----------|:--------------|:-----------------|:--------------------------------------|:------------------|----------------:|-----------------------:|:-----------------------------|
| 2020-03-06 21:30:00 | L         | M30 CLOSE     | M30 CLOSE        | cross                                 | cross             |            13.7 |                   13.9 | 止损: MT5=13.7 / Python=13.9 |
| 2020-03-25 12:00:00 | L         | M30 CLOSE     | M30 CLOSE        | cross                                 | cross             |             8.7 |                    9.6 | 止损: MT5=8.7 / Python=9.6   |
| 2020-07-28 07:30:00 | S         | M30 CLOSE     | M30 CLOSE        | cross                                 | cross             |             8.9 |                   12.2 | 止损: MT5=8.9 / Python=12.2  |
| 2020-07-31 15:00:00 | S         | M30 CLOSE     | M30 CLOSE        | pre_cross                             | pre_cross         |             6.7 |                    7.1 | 止损: MT5=6.7 / Python=7.1   |
| 2020-08-12 21:30:00 | S         | M30 CLOSE     | M30 CLOSE        | cross                                 | cross             |            24.7 |                   25.6 | 止损: MT5=24.7 / Python=25.6 |
| 2024-04-03 09:00:00 | S         | M30 CLOSE     | M30 CLOSE        | pre_cross                             | pre_cross         |             6.4 |                    5.9 | 止损: MT5=6.4 / Python=5.9   |
| 2024-04-08 14:00:00 | S         | M30 CLOSE     | M30 CLOSE        | pre_cross                             | pre_cross         |             5.7 |                    6.5 | 止损: MT5=5.7 / Python=6.5   |
| 2024-04-08 19:30:00 | L         | M30 CLOSE     | M30 CLOSE        | cross                                 | cross             |             7.3 |                    7.2 | 止损: MT5=7.3 / Python=7.2   |
| 2024-11-12 15:00:00 | L         | M30 CLOSE     | M30 CLOSE        | pre_cross                             | pre_cross         |             7.6 |                    7.1 | 止损: MT5=7.6 / Python=7.1   |
| 2025-10-15 14:00:00 | S         | M30 CLOSE     | M30 CLOSE        | pre_cross                             | pre_cross         |             6.8 |                    5.8 | 止损: MT5=6.8 / Python=5.8   |
| 2025-10-16 07:30:00 | S         | M15 SLOT1     | M15 SLOT1        | pre_cross_m15_slot1_replace_or_rescue | pre_cross         |             6.4 |                    6   | 止损: MT5=6.4 / Python=6.0   |
| 2025-12-24 04:30:00 | S         | M30 CLOSE     | M30 CLOSE        | pre_cross                             | pre_cross         |            15.5 |                   14.9 | 止损: MT5=15.5 / Python=14.9 |
| 2026-01-21 17:00:00 | S         | M30 CLOSE     | M30 CLOSE        | pre_cross                             | pre_cross         |            18.8 |                   18.6 | 止损: MT5=18.8 / Python=18.6 |
| 2026-01-26 20:30:00 | S         | M15 SLOT1     | M15 SLOT1        | pre_cross_m15_slot1_replace_or_rescue | pre_cross         |            14.8 |                    5.6 | 止损: MT5=14.8 / Python=5.6  |
| 2026-02-02 15:30:00 | S         | M30 CLOSE     | M30 CLOSE        | pre_cross                             | pre_cross         |            17.7 |                   19.8 | 止损: MT5=17.7 / Python=19.8 |
| 2026-06-08 13:00:00 | L         | M15 SLOT1     | M15 SLOT1        | pre_cross_m15_slot1_replace_or_rescue | pre_cross         |             6.3 |                   10.1 | 止损: MT5=6.3 / Python=10.1  |
| 2026-06-19 14:30:00 | L         | M30 CLOSE     | M30 CLOSE        | pre_cross                             | pre_cross         |            13.7 |                   12.7 | 止损: MT5=13.7 / Python=12.7 |
| 2026-06-30 08:00:00 | L         | M30 CLOSE     | M30 CLOSE        | pre_cross                             | pre_cross         |            16.3 |                   16   | 止损: MT5=16.3 / Python=16.0 |

## MT5 独有样本

| mt5_raw_anchor_time   | anchor_time         | dir   | trigger   | mode_raw                              |   mt5_stop_dist |
|:----------------------|:--------------------|:------|:----------|:--------------------------------------|----------------:|
| 2020-03-13 14:30:00   | 2020-03-13 16:00:00 | S     | M30 CLOSE | cross                                 |            10.4 |
| 2020-03-17 02:30:00   | 2020-03-17 04:00:00 | S     | M30 CLOSE | cross                                 |            15.1 |
| 2022-03-08 01:30:00   | 2022-03-08 03:00:00 | S     | M30 CLOSE | pre_cross                             |             9.7 |
| 2023-03-15 19:00:00   | 2023-03-15 20:30:00 | S     | M15 SLOT1 | pre_cross_m15_slot1_replace_or_rescue |             7.7 |
| 2023-03-20 11:00:00   | 2023-03-20 12:30:00 | S     | M15 SLOT1 | pre_cross_m15_slot1_replace_or_rescue |             6.5 |
| 2024-03-07 15:00:00   | 2024-03-07 16:30:00 | S     | M15 SLOT1 | pre_cross_m15_slot1_replace_or_rescue |             6.1 |
| 2025-04-13 22:30:00   | 2025-04-14 00:00:00 | S     | M15 SLOT1 | pre_cross_m15_slot1_replace_or_rescue |             5.3 |
| 2025-04-22 09:00:00   | 2025-04-22 10:30:00 | S     | M30 CLOSE | pre_cross                             |            14.2 |
| 2025-09-09 15:00:00   | 2025-09-09 16:30:00 | S     | M30 CLOSE | pre_cross                             |             5.4 |
| 2025-10-20 01:30:00   | 2025-10-20 03:00:00 | L     | M30 CLOSE | pre_cross                             |             7.9 |
| 2026-02-02 23:30:00   | 2026-02-03 01:00:00 | L     | M15 SLOT1 | pre_cross_m15_slot1_replace_or_rescue |            34.8 |
| 2026-02-24 01:30:00   | 2026-02-24 03:00:00 | S     | M15 SLOT1 | pre_cross_m15_slot1_replace_or_rescue |            17.4 |
| 2026-06-11 06:00:00   | 2026-06-11 07:30:00 | L     | M15 SLOT1 | pre_cross_m15_slot1_replace_or_rescue |             7.9 |
| 2026-06-30 07:30:00   | 2026-06-30 09:00:00 | L     | M30 CLOSE | cross                                 |            29.6 |

## Python 独有样本

| anchor_time         | dir   | trigger   | mode_raw   |   python_stop_dist_1dp | variant                 |
|:--------------------|:------|:----------|:-----------|-----------------------:|:------------------------|
| 2019-08-13 15:30:00 | S     | M30 CLOSE | cross      |                   35.2 | m30_base                |
| 2020-01-06 17:30:00 | S     | M30 CLOSE | cross      |                    9   | m30_base                |
| 2020-02-24 21:30:00 | S     | M30 CLOSE | post_n2    |                   17.2 | m30_base                |
| 2020-03-13 09:30:00 | L     | M30 CLOSE | cross      |                   13.8 | m30_base                |
| 2020-03-13 15:30:00 | S     | M30 CLOSE | pre_cross  |                    9.7 | m30_base                |
| 2020-03-17 17:30:00 | L     | M30 CLOSE | post_n4    |                   34.2 | m30_base                |
| 2020-03-18 09:30:00 | S     | M30 CLOSE | post_n4    |                   23   | m30_base                |
| 2020-03-20 05:30:00 | L     | M30 CLOSE | post_n5    |                    6.4 | m30_base                |
| 2020-03-20 19:30:00 | S     | M30 CLOSE | post_n4    |                    8.7 | m30_base                |
| 2020-03-25 09:30:00 | S     | M30 CLOSE | post_n6    |                    8.3 | m30_base                |
| 2020-03-26 13:30:00 | L     | M30 CLOSE | post_n4    |                   11.4 | m30_base                |
| 2020-07-28 17:30:00 | L     | M30 CLOSE | post_n3    |                   12.8 | m30_base                |
| 2021-03-04 21:00:00 | S     | M30 CLOSE | post_n5    |                   13.3 | m30_base                |
| 2021-06-18 09:30:00 | L     | M30 CLOSE | post_n5    |                    8.3 | m30_base                |
| 2021-06-18 15:30:00 | S     | M30 CLOSE | post_n3    |                   12   | m30_base                |
| 2021-08-10 12:00:00 | S     | M30 CLOSE | post_n4    |                    5.4 | m30_base                |
| 2022-03-07 21:30:00 | L     | M30 CLOSE | post_n3    |                    9.7 | m30_base                |
| 2022-03-09 11:30:00 | S     | M30 CLOSE | post_n2    |                   23.2 | m30_base                |
| 2022-11-08 18:00:00 | L     | M15 SLOT1 | post_n6    |                   32.1 | ea_slot1_replace        |
| 2022-11-10 15:30:00 | L     | M30 CLOSE | post_n2    |                   23   | ea_slot1_replace        |
| 2022-11-14 18:00:00 | L     | M15 SLOT1 | post_n5    |                    8.2 | ea_slot1_runtime_rescue |
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
| 2025-10-17 11:00:00 | S     | M15 SLOT1 | pre_cross  |                   12.3 | ea_slot1_runtime_rescue |
| 2025-10-21 10:00:00 | S     | M15 SLOT1 | post_n5    |                   31.6 | ea_slot1_runtime_rescue |
| 2026-02-02 17:00:00 | S     | M15 SLOT1 | cross      |                    6.5 | ea_slot1_replace        |
| 2026-03-24 04:30:00 | S     | M30 CLOSE | post_n4    |                   20.6 | ea_slot1_replace        |
| 2026-06-22 03:30:00 | L     | M30 CLOSE | post_n3    |                   23.5 | ea_slot1_replace        |
