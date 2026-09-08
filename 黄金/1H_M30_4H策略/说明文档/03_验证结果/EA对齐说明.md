# 1H_M30_4H EA 对齐说明

日期：2026-07-26

## 当前状态

| item | status |
| --- | --- |
| 当前候选 | `fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7` |
| Python 预期逐笔账本 | done |
| 当前候选专用 EA | done |
| MT5 Strategy Tester ledger | done |
| Python vs EA 逐笔对齐 | matched |

## 当前候选规则

```text
fixed_delay_1
+ H1 last6 structural stop
+ stop_distance 8-28pt
+ side-extreme pool
+ close_momentum_signed_pct >= -0.4
+ SHORT only: side_extreme_vol_way_s_way <= 0.7
```

关键口径：

- 入场：M30 SMA5/SMA13 穿越后第 1 根 M30 K 线开盘。
- 止损：H1 最近 6 根已收盘结构高低点。
- 做空机会：最近 4 根已收盘 H1 最高价 vs H4 SMA55 >= 2%。
- 做多机会：最近 4 根已收盘 H1 最低价 vs H4 SMA55 <= -2%。
- 通用动能：`side_extreme_close_momentum_signed_pct >= -0.4`。
- 空头专用：`side_extreme_vol_way_s_way <= 0.7`。

## 对齐窗口

MT5 Strategy Tester 使用与 Python 样本一致的窗口：

```text
Symbol=XAUUSDm
Period=M30
FromDate=2020.02.26
ToDate=2023.12.30
Deposit=500
Leverage=2000
InpSimMode=true
InpExportLedger=true
```

说明：

- Python 当前候选第一笔入场为 `2020-02-26 14:00:00`。
- Python 当前候选最后一笔出场为 `2023-12-29 07:00:00`。
- MT5 `ToDate=2023.12.29` 会漏掉最后一笔出场，所以对齐窗口使用 `2023.12.30`。

## 对齐结果

| expected_rows | actual_rows | matched_rows | missing_in_actual | extra_in_actual | max_abs_entry_diff | max_abs_stop_diff | max_abs_exit_diff | max_abs_pnl_points_diff |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 88 | 88 | 88 | 0 | 0 | 0.0 | 0.0 | 0.0 | 0.0 |

结论：Python 预期账本与 MT5 EA 导出账本逐笔完全一致。

## 收益口径

当前报告口径为 `0.01 lot`，`1.0 price point = $1.00`。

| metric | value |
| --- | ---: |
| trades | 88 |
| long | 38 |
| short | 50 |
| PF | 3.1901 |
| test PF | 2.2755 |
| net PnL, 0.01 lot | $670.33 |
| max drawdown, 0.01 lot | $47.45 |

## 输出文件

```text
F:\use_code\MTA5_l\黄金\1H_M30_4H策略\data\validation\ea_alignment_current_candidate\python_expected_trade_ledger.csv
F:\use_code\MTA5_l\黄金\1H_M30_4H策略\data\validation\ea_alignment_current_candidate\1H_M30_4H_current_candidate_trade_ledger.csv
F:\use_code\MTA5_l\黄金\1H_M30_4H策略\data\validation\ea_alignment_current_candidate\python_vs_ea_alignment_summary.csv
F:\use_code\MTA5_l\黄金\1H_M30_4H策略\data\validation\ea_alignment_current_candidate\python_vs_ea_alignment_detail.csv
F:\use_code\MTA5_l\黄金\1H_M30_4H策略\data\validation\ea_alignment_current_candidate\ea_alignment_current_candidate_report.md
```

## 部署前边界

当前 EA 默认 `InpSimMode=true`，用于导出虚拟 ledger，不会下真实订单。

如果进入 MT5 部署评审，必须单独确认：

- `InpSimMode=false`
- `InpLots`
- `InpMagic`
- 最大同时持仓
- 点差/滑点保护
- 账户最大风险
- MT5 重启后的状态恢复
- 是否允许真实下单
