# 三来源分层对比报告

## 输入范围

- Python基础版：`data/raw`、`data/processed/m30_standardized.csv`、`data/signals`
- Python调用MT5数据版：`data/raw/H2_XAUUSDm_mt5.csv`、`data/processed/m30_mt5.csv`、`data/signals_mt5`
- MT5-only：`mt5_only_bar_export_session5_20260712.csv` + 当前 M30-only strict-veto diff session_03

## 先看原始/计算数据

| dataset                   | role             |   rows | time_start          | time_end            |   duplicate_time_rows |
|:--------------------------|:-----------------|-------:|:--------------------|:--------------------|----------------------:|
| Python base raw M30       | python_base_raw  |  97640 | 2018-01-15 06:30:00 | 2026-07-03 16:30:00 |                     0 |
| Python base raw M15       | python_base_raw  |  98901 | 2022-04-08 12:30:00 | 2026-07-03 16:45:00 |                     0 |
| Python base raw H2        | python_base_raw  |  26080 | 2018-01-15 06:00:00 | 2026-07-03 16:00:00 |                     0 |
| Python base processed M30 | python_base_calc |  97627 | 2018-01-04 20:00:00 | 2026-06-25 03:00:00 |                     0 |
| Python base processed M15 | python_base_calc |  98900 | 2022-03-30 21:45:00 | 2026-06-25 03:00:00 |                     0 |
| Python base processed H2  | python_base_calc |  26079 | 2018-01-04 16:00:00 | 2026-06-25 04:00:00 |                     0 |
| Python MT5 raw H2         | python_mt5_raw   |  25558 | 2018-01-02 08:00:00 | 2026-07-03 18:00:00 |                     0 |
| Python MT5 processed M30  | python_mt5_calc  |  97640 | 2018-01-15 08:30:00 | 2026-07-03 18:30:00 |                     0 |
| MT5-only bar export       | mt5_only_calc    | 100459 | 2018-01-02 06:00:00 | 2026-07-06 23:30:00 |                     0 |

## M30计算差异摘要

|   common_bars | metric                   |   count |   max_abs |    mean_abs |   p95_abs |   nonzero_gt_1e-6 |
|--------------:|:-------------------------|--------:|----------:|------------:|----------:|------------------:|
|         91960 | py_vs_py_mt5_close_diff  |   91960 |    5.893  | 6.40822e-05 |   0       |                 1 |
|         91960 | py_vs_mt5_close_diff     |   91960 |  360.952  | 3.89776     |  13.5202  |             91942 |
|         91960 | py_vs_py_mt5_sma5_diff   |   91960 |   65.7693 | 0.746991    |   2.59399 |             91958 |
|         91960 | py_vs_py_mt5_sma13_diff  |   91960 |   25.485  | 0.436894    |   1.5206  |             91959 |
|         91960 | py_mt5_vs_mt5_close_diff |   91960 |  360.952  | 3.89769     |  13.5202  |             91942 |
|         91960 | py_mt5_vs_mt5_sma5_diff  |   91960 |  164.858  | 2.68781     |   9.25177 |             91959 |
|         91960 | py_mt5_vs_mt5_sma13_diff |   91960 |   75.6081 | 1.79203     |   6.14847 |             91960 |
|         91960 | py_vs_mt5_sma5_diff      |   91960 |  142.025  | 2.10298     |   7.2789  |             91960 |
|         91960 | py_vs_mt5_sma13_diff     |   91960 |   69.1025 | 1.43083     |   4.903   |             91960 |

## 信号层摘要

| source           | layer                |   rows | mode_counts                        | dir_counts   |
|:-----------------|:---------------------|-------:|:-----------------------------------|:-------------|
| Python base      | accepted_L1_L2       |    341 | cross:75; post_n:199; pre_cross:67 | L:163; S:178 |
| Python base      | picked_L3            |    118 | cross:13; post_n:77; pre_cross:28  | L:52; S:66   |
| Python base      | executed_stage       |    118 | cross:13; post_n:77; pre_cross:28  | L:52; S:66   |
| Python MT5 data  | accepted_L1_L2       |    373 | cross:80; post_n:216; pre_cross:77 | L:185; S:188 |
| Python MT5 data  | picked_L3            |    101 | cross:13; post_n:57; pre_cross:31  | L:45; S:56   |
| Python MT5 data  | executed_stage       |    101 | cross:13; post_n:57; pre_cross:31  | L:45; S:56   |
| MT5-only EA      | executed_log_signals |     78 | cross:9; post_n:44; pre_cross:25   | L:36; S:42   |
| MT5-only EA      | shared_with_python   |     34 |                                    |              |
| MT5-only EA      | mt5_only             |     44 | cross:3; post_n:30; pre_cross:11   | L:20; S:24   |
| Python EA-window | python_only          |     26 | cross:6; post_n:13; pre_cross:7    | L:10; S:16   |

## 交易/止损/资金摘要

| source                | path                                                                 |   trade_rows |   stage1_exit_sl_count |   stage2_exit_sl_count |   stage3_exit_sl_count |   any_stage_sl_count |   all_stage_sl_count |   wins |   losses |   win_rate_pct |   base_profit |   profit_times_5 |   final_times_5 |   last_equity_column |   max_equity_column |   min_equity_column |   initial_balance |   final_balance |   python_same_window_trades |   python_same_window_final | note                                                                                                   |
|:----------------------|:---------------------------------------------------------------------|-------------:|-----------------------:|-----------------------:|-----------------------:|---------------------:|---------------------:|-------:|---------:|---------------:|--------------:|-----------------:|----------------:|---------------------:|--------------------:|--------------------:|------------------:|----------------:|----------------------------:|---------------------------:|:-------------------------------------------------------------------------------------------------------|
| Python base           | F:\use_code\MTA5_l\黄金\30m2H策略\data\signals\执行交易_Stage结果.csv     |          118 |                     54 |                     78 |                     64 |                   95 |                   44 |     64 |       54 |        54.2373 |       935.724 |          4678.62 |         5178.62 |              10935.7 |             10949.8 |             9945.09 |                   |                 |                             |                            |                                                                                                        |
| Python MT5 data       | F:\use_code\MTA5_l\黄金\30m2H策略\data\signals_mt5\执行交易_Stage结果.csv |          101 |                     41 |                     66 |                     46 |                   81 |                   30 |     60 |       41 |        59.4059 |       980.397 |          4901.99 |         5401.99 |              10980.4 |             11011.4 |             9983.37 |                   |                 |                             |                            |                                                                                                        |
| MT5-only EA session 5 |                                                                      |           78 |                        |                        |                        |                      |                      |        |          |                |               |                  |                 |                      |                     |                     |               500 |         3940.37 |                          60 |                    1969.79 | MT5 win/stop/equity curve require trade ledger; only final balance and signal count are available now. |

## MT5 bar级决策分布

| decision   |   rows |
|:-----------|-------:|
| SKIP       |  94712 |
| HOLD       |   5718 |
| SIGNAL     |     29 |

## MT5 bar级跳过原因

| skip_reason        |   rows |
|:-------------------|-------:|
| no_cross_m30_or_h2 |  92362 |
| nan                |   5747 |
| no_trigger         |   2320 |
| max_pos            |     30 |

## 当前限制

- MT5-only 现在有 bar级计算导出和日志信号，但还没有交易级 ledger，因此 MT5 胜率、止损次数、逐笔资金曲线仍不能可靠对齐。
- `signals_mt5` 当前文件时间仍是 2026-07-10，且 `export_with_mt5_data.py` 之前指向旧 terminal；本报告先按现有文件比较，后续仍需重建。
- MT5 bar export 的 `SIGNAL` 只有 M30 close 路径，M15 SLOT1 信号主要来自 tester log；因此 MT5-only 信号计算和交易信号需要分开看。
