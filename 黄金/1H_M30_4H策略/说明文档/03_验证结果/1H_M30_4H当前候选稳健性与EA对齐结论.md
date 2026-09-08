# 1H_M30_4H 当前候选稳健性与 EA 对齐结论

日期：2026-07-26

## 本轮执行内容

本轮按“把空头分侧优化候选加入完整稳健性验证和 EA 逐笔对齐”的方向执行。

已完成：

- 将主候选 `fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7` 加入完整稳健性验证脚本。
- 保留纯 `way_s_way` 对照候选 `fd1_8_28_side_pool_close_mom_ge_-0.4__short_way_ge_0.3`。
- 重新生成完整稳健性验证输出。
- 生成当前候选的 Python 预期逐笔账单，作为 EA 对齐基准。
- 生成当前候选 EA 参数包和对齐状态记录。

未完成：

- 当前迁移 EA 仍是旧 stage/H2 执行框架，尚未实现当前候选规则。
- 因未生成当前候选专用 EA ledger，本轮不能宣称 Python vs EA 已逐笔匹配。

## 当前主候选

```text
fixed_delay_1
+ H1 last6 structural stop
+ stop_distance 8-28pt
+ side-extreme pool
+ close_momentum_signed_pct >= -0.4
+ SHORT only: side_extreme_vol_way_s_way <= 0.7
```

含义：

- 入场：M30 SMA5/SMA13 穿越后第 1 根 M30 K 线开仓。
- 止损：第 1 根入场使用 H1 结构止损，当前为 `h1_last6_hilo`。
- 机会池：
  - 做空：最近 4 根已收盘 H1 的最高价 vs H4 SMA55 >= 2%。
  - 做多：最近 4 根已收盘 H1 的最低价 vs H4 SMA55 <= -2%。
- 通用动能过滤：极值 K 线 `close_momentum_signed_pct >= -0.4`。
- 空头专用过滤：极值 K 线 `vol_way_s_way <= 0.7`。

## 完整稳健性结果

| candidate | n | long_n | short_n | PF | test PF | 0.01 lot净收益 | 正收益年 | 正收益月 | 最大回撤 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 当前主候选 short_vol_way <= 0.7 | 88 | 38 | 50 | 3.1901 | 2.2755 | $670.33 | 4/4 | 23/34 | $47.45 |
| 原主候选 无空头分侧 | 108 | 38 | 70 | 2.4334 | 1.9237 | $585.95 | 4/4 | 23/36 | $57.01 |
| 纯 way 对照 short_way >= 0.3 | 97 | 38 | 59 | 2.9797 | 2.2431 | $645.06 | 4/4 | 23/36 | $56.63 |

结论：当前主候选比原主候选交易数更少，但收益、PF、测试段 PF、最大回撤均改善。

## 年度拆分

| year | n | long_n | short_n | PF | 0.01 lot净收益 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2020 | 20 | 5 | 15 | 9.3368 | $425.69 |
| 2021 | 17 | 10 | 7 | 3.3083 | $89.55 |
| 2022 | 29 | 17 | 12 | 1.1435 | $19.03 |
| 2023 | 22 | 6 | 16 | 2.6276 | $136.06 |

2022 仍然是最薄弱年份，但已经保持正收益。

## 成本压力

| 往返成本 | PF | test PF | 0.01 lot净收益 | 正收益年 | 正收益月 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.0pt | 3.1901 | 2.2755 | $670.33 | 4/4 | 23/34 |
| 0.5pt | 2.9033 | 2.0737 | $626.33 | 4/4 | 22/34 |
| 1.0pt | 2.6516 | 1.8975 | $582.33 | 3/4 | 22/34 |
| 2.0pt | 2.2334 | 1.6051 | $494.33 | 3/4 | 21/34 |
| 3.0pt | 1.9017 | 1.3701 | $406.33 | 3/4 | 19/34 |

结论：总收益抗成本明显好于原候选，但 1.0pt 以上成本会压缩年度稳定性，说明 2022 仍需要在 EA 模拟中重点观察。

## 滚动窗口

| 窗口 | 正窗口率 | 最差窗口 | 最差窗口收益 |
| --- | ---: | --- | ---: |
| 3个月 | 76.09% | 2022-01 到 2022-03 | -18.221pt |
| 6个月 | 87.23% | 2022-01 到 2022-06 | -33.787pt |
| 12个月 | 97.87% | 2021-10 到 2022-09 | -28.461pt |

相比原候选，12个月滚动最差窗口从 `-39.246pt` 改善到 `-28.461pt`。

## EA 对齐状态

已生成 Python 预期逐笔账单：

- `黄金/1H_M30_4H策略/data/validation/ea_alignment_current_candidate/python_expected_trade_ledger.csv`
- `黄金/1H_M30_4H策略/data/validation/ea_alignment_current_candidate/python_expected_trade_ledger_minimal.csv`

已生成 EA 对齐参数包：

- `黄金/1H_M30_4H策略/data/validation/ea_alignment_current_candidate/current_candidate_parameter_pack.json`

当前状态：

```text
python_expected_ledger: done
candidate_parameter_pack: done
ea_implementation: pending
ea_strategy_tester_run: pending
python_vs_ea_alignment: pending
```

原因：现有 `1H_M30_4H_Strategy_EA.mq5` 仍是旧 stage/H2 框架迁移版，不等同于当前候选规则。不能拿旧 EA ledger 宣称已经对齐。

## 下一步

1. 实现当前候选专用 EA 或改造现有 EA，使其按当前规则导出 ledger。
2. 用 MT5 Strategy Tester 跑同一历史区间。
3. 将 EA 导出的 ledger 传给 `scripts/export_1h_current_candidate_ea_alignment.py`。
4. 比对 `entry_time + dir`、入场价、止损价、出场价、出场原因、pnl_points。
5. 只有逐笔匹配通过后，才进入模拟盘部署。

## 本轮输出

- `scripts/validate_1h_way_momentum_candidates.py`
- `scripts/export_1h_current_candidate_ea_alignment.py`
- `黄金/1H_M30_4H策略/data/validation/way_momentum_robustness/robustness_validation_report.md`
- `黄金/1H_M30_4H策略/data/validation/ea_alignment_current_candidate/ea_alignment_current_candidate_report.md`
- `1H_M30_4H当前候选EA对齐记录.md`
