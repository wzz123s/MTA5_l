# MT5 直接数据接入执行记录

日期：2026-07-25

## 当前结论

正在执行“直接用 MT5 调用历史数据和实时数据”的落地方案。已先补基础设施与规则文件，实际历史数据导出需要本机 MT5 终端可初始化、品种可见，并且终端有对应日期范围历史数据。

补充结论：2026-07-25 已完成 EA 编译、MT5 Strategy Tester 回测、EA ledger 导出、Python vs EA 逐笔对齐。两套策略均为 `mismatch`，不能部署实盘。详见 `EA逐笔对齐执行记录.md`。

## 执行流水

| 时间 | 步骤 | 结果 |
| --- | --- | --- |
| 2026-07-25 | 检查旧 `build_from_mt5.py`、`mt5_data_source.py`、`export_with_mt5_data.py` | 确认旧脚本读取的是 EA/CSV 导出，不是 Python 直接调用 MT5 API |
| 2026-07-25 | 新增共享 MT5 连接层 | 已新增 `scripts/mt5/mt5_connection.py` |
| 2026-07-25 | 新增 MT5 历史导出层 | 已新增 `scripts/mt5/mt5_history.py` |
| 2026-07-25 | 新增 MT5 实时采集层 | 已新增 `scripts/mt5/mt5_live.py` |
| 2026-07-25 | 新增 `1H_M30_4H` 专用 MT5 raw 同步入口 | 已新增 `黄金/1H_M30_4H策略/scripts/data_source/sync_raw_data_from_mt5.py` |
| 2026-07-25 | 新增 `2H_M30_6H` 专用 MT5 raw 同步入口 | 已新增 `黄金/2H_M30_6H策略/scripts/data_source/sync_raw_data_from_mt5.py` |
| 2026-07-25 | 扩展 raw manifest 同源检查 | 已支持 MT5 bundle manifest 与逐文件 hash 检查 |
| 2026-07-25 | Python 语法检查 | 通过：MT5 工具、策略 raw 同步、prepare、signals、validation 相关脚本均通过 `py_compile` |
| 2026-07-25 | MT5 Python 包检查 | 通过：`MetaTrader5` version `5.0.5735` 可 import |
| 2026-07-25 | 默认 MT5 初始化 | 失败：`IPC initialize failed, MetaTrader 5 x64 not found` |
| 2026-07-25 | 显式 EXNESS 终端初始化 | 成功：`F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe`，MT5 version `(500, 5833, 25 Apr 2026)`，server `Exness-MT5Trial5` |
| 2026-07-25 | `1H_M30_4H` 实时冒烟 | 成功：`data/live/1h_m30_4h_live_smoke` |
| 2026-07-25 | `2H_M30_6H` 实时冒烟 | 成功：`data/live/2h_m30_6h_live_smoke` |
| 2026-07-25 | `1H_M30_4H` 历史数据导出 | 成功：`M30=47325`、`H1=23715`、`H4=6477`，source id `1h_m30_4h_mt5_gen_20200101_20240101` |
| 2026-07-25 | `2H_M30_6H` 历史数据导出 | 成功：`M30=30306`、`H2=7913`、`H6=2783`，source id `2h_m30_6h_mt5_gen_20240101_20260725` |
| 2026-07-25 | raw manifest 独立性检查 | 通过：两套策略 bundle hash 不同，且未发现相同组件 hash |
| 2026-07-25 | 解耦旧参考 signal bundle | 已完成：`prepare` 改为读取当前策略 MT5 raw，并生成 `mt5_basic_cross_signals.csv` |
| 2026-07-25 | 动态 train/test 切分 | 已完成：不再固定 `2023-01-01`，改为每个候选按时间顺序 70/30 切分 |
| 2026-07-25 | `1H_M30_4H` 一键 bundle | 成功：baseline signals `393` |
| 2026-07-25 | `2H_M30_6H` 一键 bundle | 成功：baseline signals `604` |
| 2026-07-25 | MT5 raw 研究 `.set` | 已新增两套 `*.mt5_raw_research_20260725.set`，仅供回测/对齐前研究 |
| 2026-07-25 | EA 编译 | 两套 EA 编译日志均为 `0 errors, 0 warnings`，`.ex5` 已生成 |
| 2026-07-25 | MT5 Strategy Tester | 两套策略 terminal log 均显示 successfully finished；XML 报告未生成，但 EA CSV ledger 已从 Tester agent 回收 |
| 2026-07-25 | Python vs EA 逐笔对齐 | 已执行但未通过：`1H_M30_4H` matched `147/294`，`2H_M30_6H` matched `9/453` |
| 2026-07-25 | EA 实际收益统计 | `1H_M30_4H` 净收益 `$-321.65`，`2H_M30_6H` 净收益 `$-500.18`，禁止部署实盘 |

## 待验证项

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| Python 语法检查 | 完成 | 已通过 |
| MT5 Python 包 | 完成 | 已通过 |
| MT5 终端初始化 | 完成 | 显式 EXNESS 终端路径通过 |
| 历史数据导出 | 完成 | 两套策略均已生成 MT5 raw manifest |
| 实时数据冒烟 | 完成 | 两套策略均有 live smoke 输出 |
| 策略重建 | 完成 | 两套策略一键 bundle 跑通 |
| 专用 EA | 部分完成 | EA 源码已存在；但源码仍带 H2 主线遗留逻辑，未证明完全匹配新策略门 |
| Python vs EA 逐笔对齐 | 已执行但未通过 | 当前状态 `mismatch`；EA ledger 已生成，但与 Python expected 逐笔不一致 |

## 收益摘要

| 策略 | 生成窗口 | 最终研究变体 | 交易数 | 候选 PF / EV | 30% 测试 PF / EV | Stage+仓位 PF / EV | Stage+仓位测试 PF / EV | 估算收益 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `1H_M30_4H` | 2020-01-02 至 2023-12-29 | `1H_M30_4H__1h_bias5_top30` | 118 | 1.1718 / 0.9167 | 2.4496 / 4.9907 | 1.0776 / 1.2414 | 2.2146 / 12.5448 | `$29.30` |
| `2H_M30_6H` | 2024-01-01 至 2026-07-24 | `2H_M30_6H__2h_dir_align` | 219 | 1.4335 / 4.5759 | 1.3483 / 6.0306 | 1.1390 / 4.4028 | 1.0436 / 2.2659 | `$192.84` |

## StopSpec 摘要

| 策略 | 本次 primary StopSpec | 次选 StopSpec | 可接受扫描范围 | 备注 |
| --- | --- | --- | --- | --- |
| `1H_M30_4H` | `6-20pt` | `8-20pt` | `2-46pt` | 比早前 `14-70pt` 明显收窄 |
| `2H_M30_6H` | `12-34pt` | `14-34pt` | `4-238pt` | primary 已小于旧 `14-70pt` 上限，但扫描尾部仍有极宽值，需要 EA 逐笔确认 |

## 部署判断

可以继续进入 MT5 回测诊断，但不能进入模拟盘或实盘部署。

原因：

1. 本次 MT5 历史和实时数据链路已跑通。
2. 两套策略已有研究参数和研究 `.set`。
3. EA 源码文件存在并可编译，但仍保留旧 `30m2H` Layer2 `pre_cross/cross/post_n` 交易路径。
4. 当前 alignment 已从 `ledger_missing` 更新为 `mismatch`：有 EA ledger，但逐笔不一致。
5. Stage 扫描目前是 MT5 raw 候选交易上的研究代理，不等于当前 EA 逐笔路径复刻。

下一步必须是：重写专用 EA，使其精确复刻 Python 最终信号、高周期门、StopSpec、stage exit 和仓位路径，然后重新跑 MT5 Strategy Tester 与 Python vs EA 逐笔对齐。
