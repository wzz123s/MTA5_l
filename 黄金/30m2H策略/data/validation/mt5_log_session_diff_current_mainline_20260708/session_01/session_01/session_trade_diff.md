# MT5 会话逐笔差异对比

- 会话编号：`1`
- 回测区间：`2026-01-01 00:00:00` 到 `2026-07-07 00:00:00`
- 参数摘要：`top34% + Stage 2.0/1.5/4.0 + stop [5,35]`
- 是否当前主线参数：`是`
- Python 复算模式：`EA可执行诊断口径`
- 输出目录：`F:\use_code\MTA5\黄金/30m2H策略\data\validation\mt5_log_session_diff_current_mainline_20260708\session_01\session_01`

## 汇总

- MT5 信号数：`12`
- Python 执行信号数：`12`
- 共同信号数：`7`
- 共同但字段不一致：`7`
- MT5 独有：`5`
- Python 独有：`5`

## 共同但不一致

| anchor_time_mt5     | dir_mt5   | trigger_mt5   | trigger_python   | mode_raw_mt5                          | mode_raw_python   |   mt5_stop_dist |   python_stop_dist_1dp | 差异说明                     |
|:--------------------|:----------|:--------------|:-----------------|:--------------------------------------|:------------------|----------------:|-----------------------:|:-----------------------------|
| 2026-01-21 17:00:00 | S         | M30 CLOSE     | M30 CLOSE        | pre_cross                             | pre_cross         |            18.8 |                   18.6 | 止损: MT5=18.8 / Python=18.6 |
| 2026-01-26 20:30:00 | S         | M15 SLOT1     | M15 SLOT1        | pre_cross_m15_slot1_replace_or_rescue | pre_cross         |            14.8 |                    5.6 | 止损: MT5=14.8 / Python=5.6  |
| 2026-02-02 15:30:00 | S         | M30 CLOSE     | M30 CLOSE        | pre_cross                             | pre_cross         |            17.7 |                   19.8 | 止损: MT5=17.7 / Python=19.8 |
| 2026-03-24 02:00:00 | S         | M30 CLOSE     | M30 CLOSE        | pre_cross                             | pre_cross         |            28.9 |                   28.2 | 止损: MT5=28.9 / Python=28.2 |
| 2026-06-08 13:00:00 | L         | M15 SLOT1     | M15 SLOT1        | pre_cross_m15_slot1_replace_or_rescue | pre_cross         |             6.3 |                   10.1 | 止损: MT5=6.3 / Python=10.1  |
| 2026-06-19 14:30:00 | L         | M30 CLOSE     | M30 CLOSE        | pre_cross                             | pre_cross         |            13.7 |                   12.7 | 止损: MT5=13.7 / Python=12.7 |
| 2026-06-30 08:00:00 | L         | M30 CLOSE     | M30 CLOSE        | pre_cross                             | pre_cross         |            16.3 |                   16   | 止损: MT5=16.3 / Python=16.0 |

## MT5 独有样本

| mt5_raw_anchor_time   | anchor_time         | dir   | trigger   | mode_raw                              |   mt5_stop_dist |
|:----------------------|:--------------------|:------|:----------|:--------------------------------------|----------------:|
| 2026-02-02 23:30:00   | 2026-02-03 01:00:00 | L     | M15 SLOT1 | pre_cross_m15_slot1_replace_or_rescue |            34.8 |
| 2026-02-24 01:30:00   | 2026-02-24 03:00:00 | S     | M15 SLOT1 | pre_cross_m15_slot1_replace_or_rescue |            17.4 |
| 2026-04-02 01:30:00   | 2026-04-02 03:00:00 | S     | M15 SLOT1 | pre_cross_m15_slot1_replace_or_rescue |            10.2 |
| 2026-06-11 06:00:00   | 2026-06-11 07:30:00 | L     | M15 SLOT1 | pre_cross_m15_slot1_replace_or_rescue |             7.9 |
| 2026-06-30 07:30:00   | 2026-06-30 09:00:00 | L     | M30 CLOSE | cross                                 |            29.6 |

## Python 独有样本

| anchor_time         | dir   | trigger   | mode_raw   |   python_stop_dist_1dp | variant          |
|:--------------------|:------|:----------|:-----------|-----------------------:|:-----------------|
| 2026-01-27 07:30:00 | L     | M30 CLOSE | post_n5    |                   18.7 | ea_slot1_replace |
| 2026-02-02 17:00:00 | S     | M15 SLOT1 | cross      |                    6.5 | ea_slot1_replace |
| 2026-03-24 10:00:00 | L     | M30 CLOSE | post_n2    |                   15.1 | ea_slot1_replace |
| 2026-05-28 14:30:00 | L     | M30 CLOSE | pre_cross  |                   33.1 | ea_slot1_replace |
| 2026-06-22 03:30:00 | L     | M30 CLOSE | post_n3    |                   23.5 | ea_slot1_replace |

## 输出文件

- `mt5_signals.csv`
- `python_executed_signals.csv`
- `shared_signals.csv`
- `shared_mismatch.csv`
- `mt5_only_signals.csv`
- `python_only_signals.csv`
