# EA 逐笔对齐执行记录

日期：2026-07-25  
执行时间：2026-07-25 14:10:09 +08:00  
范围：`1H_M30_4H`、`2H_M30_6H`

## 执行结论

本次已经完成 EA 编译、MT5 Strategy Tester 回测、EA 逐笔 ledger 导出、Python vs EA 对齐比较。

结论：两套策略均为 `mismatch`，不能部署实盘。

当前 EA 可以作为 MT5 回测诊断版本使用，但不是与 Python 研究结果逐笔一致的部署版本。EA 实际回测收益也明显偏离研究收益，其中 `2H_M30_6H` 在 Tester ledger 中已接近爆仓。

## MT5 环境

| 项目 | 值 |
| --- | --- |
| Terminal | `F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe` |
| Data path | `C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16` |
| Tester agent source | `C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\B695BCB6C1E6864B6D96307B87B29F16\Agent-*\MQL5\Files` |
| Account | `277752085` |
| Server | `Exness-MT5Trial5` |
| Account leverage | `1:2000` |
| Run前持仓/挂单 | positions `0` / orders `0` |

## 使用脚本

| 文件 | 用途 |
| --- | --- |
| `scripts/mt5/ea_alignment_runner.ps1` | 复制 EA 和 `.set` 到 MT5、编译、生成 Tester ini、运行 Tester、回收 EA 导出 CSV |
| `黄金/1H_M30_4H策略/auto_trade/compare_python_vs_ea.py` | 生成 Python 期望 stage ledger，并与 EA ledger 逐笔对齐 |
| `黄金/2H_M30_6H策略/auto_trade/compare_python_vs_ea.py` | 生成 Python 期望 stage ledger，并与 EA ledger 逐笔对齐 |

## 编译与 Tester

| 策略 | 编译 | Tester | XML 报告 | EA CSV ledger |
| --- | --- | --- | --- | --- |
| `1H_M30_4H` | `0 errors, 0 warnings`，`.ex5` 已生成 | terminal log 显示 successfully finished | 未生成 | 已导出并复制 |
| `2H_M30_6H` | `0 errors, 0 warnings`，`.ex5` 已生成 | terminal log 显示 successfully finished | 未生成 | 已导出并复制 |

备注：MetaEditor 进程返回码为 `1`，但编译日志明确显示 `0 errors, 0 warnings`，且 `.ex5` 文件存在。本次按日志和产物判断编译成功。

## 对齐结果

| 策略 | 状态 | Python expected | EA rows | matched | Python only | EA only | mode mismatch | lot mismatch | PnL sign mismatch |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `1H_M30_4H` | `mismatch` | 294 | 1,177 | 147 | 147 | 1,030 | 0 | 0 | 28 |
| `2H_M30_6H` | `mismatch` | 453 | 54 | 9 | 444 | 45 | 0 | 0 | 4 |

对齐脚本已做本次语义修正：

- Python `mt5_basic_cross_v1` 归一为 EA `cross`。
- Python 信号完成 bar 与 EA 下单 anchor 做 `+30 minutes` 对齐。
- stage lots 使用参数包 `0.01/0.01/0.04`。
- StopSpec 使用参数包当前主档：`1H_M30_4H = 6-20pt`，`2H_M30_6H = 12-34pt`。

## EA 实际收益

以下是 MT5 Strategy Tester 导出的 EA ledger 实际净收益，按 `start_capital = 500.0` 统计。

| 策略 | EA stage rows | 信号数 | 净收益 | 期末权益估算 | 收益率 | 最大权益 | 第一笔 | 最后一笔 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `1H_M30_4H` | 1,177 | 393 | `$-321.65` | `$178.35` | `-64.33%` | `$2,436.38` | 2020-01-02 14:00 | 2023-05-11 13:00 |
| `2H_M30_6H` | 54 | 18 | `$-500.18` | `$-0.18` | `-100.04%` | `$483.61` | 2024-01-05 15:30 | 2024-04-19 17:00 |

## 主要分歧诊断

Python 研究版当前选中的最终画像是：

| 策略 | Python 最终变体 | Python 信号模型 | 高周期门 | StopSpec |
| --- | --- | --- | --- | --- |
| `1H_M30_4H` | `1H_M30_4H__1h_bias5_top30` | `mt5_basic_cross_v1` 基础 M30 SMA5/SMA13 cross | `1h_bias5_top30` | `6-20pt` |
| `2H_M30_6H` | `2H_M30_6H__2h_dir_align` | `mt5_basic_cross_v1` 基础 M30 SMA5/SMA13 cross | `2h_dir_align` | `12-34pt` |

当前 EA 仍保留旧 `30m2H` 路径中的 Layer2 `pre_cross / cross / post_n` 交易逻辑与 stage 执行路径，未完整实现上述 Python 最终门控。因此 EA ledger 与 Python expected ledger 不可能视为同一策略结果。

本次实际 EA 回测结果不能用来证明 Python 研究收益，反而说明：如果直接把现有 EA 装到 MT5 跑，实际交易路径会严重偏离研究策略。

## 部署决定

| 策略 | 决定 | 原因 |
| --- | --- | --- |
| `1H_M30_4H` | `blocked` | 对齐不通过；EA 实际净收益 `-64.33%` |
| `2H_M30_6H` | `blocked` | 对齐不通过；EA 实际净收益约 `-100.04%`，接近爆仓 |

禁止实盘部署。可以继续在 MT5 Strategy Tester 中作为诊断版本运行。

## 下一步

推荐路线：重写专用 EA，使其精确复刻 Python 最终策略。

必须完成：

1. EA 信号模型改成基础 M30 SMA5/SMA13 cross，不再交易旧 `pre_cross/post_n` 扩展信号。
2. EA 加入各策略专用高周期门：`1h_bias5_top30`、`2h_dir_align`。
3. EA 时间轴统一：Python signal bar 与 EA anchor 固定 `+30 minutes` 对齐。
4. EA StopSpec、stage exit、仓位拆分逐条复刻参数包。
5. 重新运行 MT5 Strategy Tester。
6. 重新导出 ledger，并让 Python vs EA 对齐达到可接受阈值后，才允许进入模拟盘观察。

备选路线：反向把 Python 研究改成完整复刻当前 EA 的旧 Layer2 逻辑。该路线不推荐，因为会改变本次新策略的研究定义。
