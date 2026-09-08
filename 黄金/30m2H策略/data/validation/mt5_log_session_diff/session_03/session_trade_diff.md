# MT5 会话逐笔差异对比

- 会话编号：`3`
- 回测区间：`2018-01-01 00:00:00` 到 `2026-07-04 00:00:00`
- 参数摘要：`top34% + Stage 2.0/1.5/4.0 + stop [5,35]`
- 是否当前主线参数：`是`
- Python 复算模式：`EA可执行诊断口径`
- 输出目录：`F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\mt5_log_session_diff\session_03`

## 汇总

- MT5 信号数：`74`
- Python 执行信号数：`60`
- 共同信号数：`20`
- 共同但字段不一致：`20`
- MT5 独有：`54`
- Python 独有：`40`

## 共同但不一致

| anchor_time_mt5     | dir_mt5   | trigger_mt5   | trigger_python   | mode_raw_mt5                          | mode_raw_python   |   mt5_stop_dist |   python_stop_dist_1dp | 差异说明                     |
|:--------------------|:----------|:--------------|:-----------------|:--------------------------------------|:------------------|----------------:|-----------------------:|:-----------------------------|
| 2020-03-06 21:30:00 | L         | M30 CLOSE     | M30 CLOSE        | cross                                 | cross             |            13.7 |                   13.9 | 止损: MT5=13.7 / Python=13.9 |
| 2020-03-20 03:30:00 | L         | M30 CLOSE     | M30 CLOSE        | cross                                 | cross             |             8.1 |                    7.8 | 止损: MT5=8.1 / Python=7.8   |
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
| 2026-03-24 02:00:00 | S         | M30 CLOSE     | M30 CLOSE        | pre_cross                             | pre_cross         |            28.9 |                   28.2 | 止损: MT5=28.9 / Python=28.2 |
| 2026-06-08 13:00:00 | L         | M15 SLOT1     | M15 SLOT1        | pre_cross_m15_slot1_replace_or_rescue | pre_cross         |             6.3 |                   10.1 | 止损: MT5=6.3 / Python=10.1  |
| 2026-06-19 14:30:00 | L         | M30 CLOSE     | M30 CLOSE        | pre_cross                             | pre_cross         |            13.7 |                   12.7 | 止损: MT5=13.7 / Python=12.7 |
| 2026-06-30 08:00:00 | L         | M30 CLOSE     | M30 CLOSE        | pre_cross                             | pre_cross         |            16.3 |                   16   | 止损: MT5=16.3 / Python=16.0 |

## MT5 独有样本

| mt5_raw_anchor_time   | anchor_time         | dir   | trigger   | mode_raw   |   mt5_stop_dist |
|:----------------------|:--------------------|:------|:----------|:-----------|----------------:|
| 2018-05-24 14:00:00   | 2018-05-24 15:30:00 | S     | M30 CLOSE | post_n3    |             8.8 |
| 2018-05-24 14:30:00   | 2018-05-24 16:00:00 | S     | M30 CLOSE | post_n3    |             8.9 |
| 2019-05-29 03:00:00   | 2019-05-29 04:30:00 | S     | M30 CLOSE | post_n5    |             5.7 |
| 2019-06-28 12:30:00   | 2019-06-28 14:00:00 | L     | M30 CLOSE | post_n4    |             8.8 |
| 2020-03-13 14:30:00   | 2020-03-13 16:00:00 | S     | M30 CLOSE | cross      |            10.4 |
| 2020-03-16 23:00:00   | 2020-03-17 00:30:00 | L     | M30 CLOSE | cross      |             5.1 |
| 2020-03-17 02:30:00   | 2020-03-17 04:00:00 | S     | M30 CLOSE | cross      |            15.1 |
| 2020-04-26 00:00:00   | 2020-04-26 01:30:00 | S     | M30 CLOSE | post_n2    |             6.4 |
| 2020-04-26 22:00:00   | 2020-04-26 23:30:00 | S     | M30 CLOSE | post_n6    |             7.2 |
| 2020-06-22 12:00:00   | 2020-06-22 13:30:00 | L     | M30 CLOSE | post_n5    |            24.1 |
| 2021-01-06 04:00:00   | 2021-01-06 05:30:00 | L     | M30 CLOSE | post_n3    |             6.2 |
| 2021-03-26 10:30:00   | 2021-03-26 12:00:00 | S     | M30 CLOSE | post_n6    |             5.9 |
| 2021-07-21 07:30:00   | 2021-07-21 09:00:00 | S     | M30 CLOSE | post_n6    |             7.6 |
| 2021-10-19 16:30:00   | 2021-10-19 18:00:00 | L     | M30 CLOSE | post_n4    |             7.7 |
| 2021-10-19 17:00:00   | 2021-10-19 18:30:00 | L     | M30 CLOSE | post_n4    |             5.5 |
| 2021-11-05 12:30:00   | 2021-11-05 14:00:00 | L     | M30 CLOSE | post_n6    |            21.4 |
| 2022-03-08 01:30:00   | 2022-03-08 03:00:00 | S     | M30 CLOSE | pre_cross  |             9.7 |
| 2022-07-01 15:30:00   | 2022-07-01 17:00:00 | L     | M30 CLOSE | cross      |            10.6 |
| 2022-08-09 08:30:00   | 2022-08-09 10:00:00 | S     | M30 CLOSE | post_n4    |             5.6 |
| 2022-08-09 13:00:00   | 2022-08-09 14:30:00 | S     | M30 CLOSE | post_n4    |             5.3 |

## Python 独有样本

| anchor_time         | dir   | trigger   | mode_raw   |   python_stop_dist_1dp | variant                 |
|:--------------------|:------|:----------|:-----------|-----------------------:|:------------------------|
| 2019-08-13 15:30:00 | S     | M30 CLOSE | cross      |                   35.2 | m30_base                |
| 2020-01-06 17:30:00 | S     | M30 CLOSE | cross      |                    9   | m30_base                |
| 2020-02-24 21:00:00 | S     | M30 CLOSE | cross      |                   16.1 | m30_base                |
| 2020-03-13 09:30:00 | L     | M30 CLOSE | cross      |                   13.8 | m30_base                |
| 2020-03-13 15:30:00 | S     | M30 CLOSE | pre_cross  |                    9.7 | m30_base                |
| 2020-03-17 17:30:00 | L     | M30 CLOSE | post_n4    |                   34.2 | m30_base                |
| 2020-03-18 09:30:00 | S     | M30 CLOSE | post_n4    |                   23   | m30_base                |
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

## 输出文件

- `mt5_signals.csv`
- `python_executed_signals.csv`
- `shared_signals.csv`
- `shared_mismatch.csv`
- `mt5_only_signals.csv`
- `python_only_signals.csv`
