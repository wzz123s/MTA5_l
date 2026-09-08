# MT5 策略收益与部署评估

日期：2026-07-25

## 2026-07-25 新验证口径重建结果

本节覆盖旧研究结果。新口径为：

- `bias5/bias13/bias55` 使用带方向偏离。
- StopSpec source 统一为结构止损 `stop_distance`。
- `recent2_any` 和 ATR 不进入核心信号框架。

| 策略 | Python 主推荐门 | 交易数 | PF | 测试 PF | Stage+仓位 PnL | StopSpec | StopSpec source | StopSpec profit | 当前判断 |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |
| `1H_M30_4H` | `1H_M30_4H__1h_dir_align` | 648 | 1.3834 | 1.2865 | `$88.98` | `2-8pt` | `stop_distance` | `$58.97` | 正但偏弱，暂不进 EA |
| `2H_M30_6H` | `2H_M30_6H__6h_bias5_13_55_signed_pos` | 286 | 2.0399 | 2.1045 | `$690.17` | `2-10pt` | `stop_distance` | `$531.82` | 优先进入下一轮稳健性验证 |

详细记录见：`策略验证重建执行记录.md`。

## 2026-07-25 EA 逐笔对齐结果

已完成 EA 编译、MT5 Strategy Tester 回测、EA ledger 导出、Python vs EA 逐笔对齐。结果不是通过，而是两套策略均 `mismatch`。

| 策略 | 对齐状态 | Python expected | EA rows | matched | Python only | EA only | EA 实际净收益 | EA 实际收益率 | 部署决定 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `1H_M30_4H` | `mismatch` | 294 | 1,177 | 147 | 147 | 1,030 | `$-321.65` | `-64.33%` | 禁止实盘 |
| `2H_M30_6H` | `mismatch` | 453 | 54 | 9 | 444 | 45 | `$-500.18` | `-100.04%` | 禁止实盘 |

杠杆：账户快照为 `1:2000`，EA 参数 `InpLeverageOverride=0`，即沿用账户杠杆。上述收益按参数包 `start_capital = 500.0` 和 EA ledger 净收益统计。

关键原因：Python 研究版是 `mt5_basic_cross_v1` 基础 M30 cross 加专用高周期门；当前 EA 仍保留旧 `30m2H` 的 Layer2 `pre_cross/cross/post_n` 扩展交易路径，实际交易笔数和退出路径与 Python expected 不一致。

详细执行记录见：`EA逐笔对齐执行记录.md`。

## 数据状态

| 策略 | MT5 历史 source id | 周期 | M30 行数 | 其他周期行数 | bundle hash |
| --- | --- | --- | ---: | ---: | --- |
| `1H_M30_4H` | `1h_m30_4h_mt5_gen_20200101_20240101` | `M30,H1,H4` | 47,325 | H1 23,715 / H4 6,477 | `3affbf6e...3b37db70` |
| `2H_M30_6H` | `2h_m30_6h_mt5_gen_20240101_20260725` | `M30,H2,H6` | 30,306 | H2 7,913 / H6 2,783 | `a8902d29...7926bc4e` |

两套策略使用不同时间窗口，manifest 独立性校验已通过。它们不是同一测试窗口上的横向排名，收益只能作为各自数据源上的研究结果。

## 收益结果

| 策略 | 选中变体 | 交易数 | 候选 PF | 候选 EV | 测试 PF | 测试 EV | Stage+仓位 PF | Stage+仓位 EV | 估算收益 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `1H_M30_4H` | `1H_M30_4H__1h_bias5_top30` | 118 | 1.1718 | 0.9167 | 2.4496 | 4.9907 | 1.0776 | 1.2414 | `$29.30` |
| `2H_M30_6H` | `2H_M30_6H__2h_dir_align` | 219 | 1.4335 | 4.5759 | 1.3483 | 6.0306 | 1.1390 | 4.4028 | `$192.84` |

## StopSpec

| 策略 | primary | secondary | acceptable | 结论 |
| --- | --- | --- | --- | --- |
| `1H_M30_4H` | `6-20pt` | `8-20pt` | `2-46pt` | 当前数据下不支持继续使用旧的 `14-70pt` 作为主档 |
| `2H_M30_6H` | `12-34pt` | `14-34pt` | `4-238pt` | 主档较克制；尾部极宽值暂不进入部署参数 |

## 是否最佳

不是最终最佳策略，只是“MT5 raw 可运行研究版”。

已经完成：

- 直接 MT5 历史数据导出。
- 直接 MT5 实时数据冒烟。
- 策略 raw manifest 独立性校验。
- 基础交叉信号、候选门、基础验证、高级验证。
- 研究 `.set` 输出。

仍未完成：

- EA 源码完全适配各策略真实多周期门。
- MT5 Strategy Tester 回测。
- Python vs EA 逐笔对齐。
- Stage 的 EA 路径级复刻。
- 模拟盘连续观察。

## MT5 部署判断

当前只能部署到 MT5 做回测诊断，不能进入模拟盘或实盘部署。

使用文件：

- `黄金/1H_M30_4H策略/auto_trade/1H_M30_4H_Strategy_EA.mq5`
- `黄金/1H_M30_4H策略/auto_trade/1H_M30_4H_Strategy_EA.mt5_raw_research_20260725.set`
- `黄金/2H_M30_6H策略/auto_trade/2H_M30_6H_Strategy_EA.mq5`
- `黄金/2H_M30_6H策略/auto_trade/2H_M30_6H_Strategy_EA.mt5_raw_research_20260725.set`

上线前必须重写专用 EA，使其复刻 Python 最终信号和 stage 路径，并让 `ea_alignment` 从 `mismatch` 变成逐笔匹配通过。
