# 千问工作助理 · MTA5_l 项目总索引

> 本文件是进项目的**第一份读物**（人 AI 皆同）。只指向权威文件、不复述内容（复述即漂移）。
> 建立：2026-09-08（目录整理 Phase 1）｜维护规则见 00_项目规则.md R7
> 数据截至：2026-09-08 21:30（本地）

## 1. 一句话工程定义

黄金/原油多策略量化研究工程：Python 研究管线 + MQL5 EA 模拟盘 + 自动监控告警；账户为 **Exness DEMO（277752085）**，全链路只读监控不下单（唯一例外：1H_M30_4H 实盘部署图表 SimMode=false，见 §5）。

## 2. 策略状态总表

> 权威明细以 `00_文档中心\策略审查状态.md` 为准，本表是其快照，每次大轮收口刷新。

| 策略 | 正式口径 | 审查 | 对齐 | 监控 | 状态 |
|---|---|---|---|---|---|
| 黄金 30m2H 策略 | Strategy_EA v3.37（主线）＋ABC（对齐参照） | ✅修12项 | ⚠️验收口径待定（见 §6-T1） | 是（DEMO 实挂） | 主线验证中 |
| 黄金 1H_M30_4H 策略 | ABC_EA | ✅全修 | 94.6%（A2） | 是 | DEMO 运行；另有实盘部署图 SimMode=false |
| 黄金 2H_M30_6H 策略 | ABC_EA＋V4 带通 | ✅全修 | 96.5%／V4 88.6% | 是 | 运行；TODO-8 missing 40 排查中 |
| 黄金乖离反转策略 | BiasReversal_Combo_EA v8 | ✅已审 | 100%（351/351 多头默认路径） | 是 | 运行；做空分支门禁关闭 |
| 原油 2H 策略 | USOIL2H_CrossConfirm（因果口径） | ✅修8处 | 53/53 冒烟 | 面板监控（**EA 已摘除**） | 待调整（09-07 决策） |
| 原油 4H 门策略 | USOIL4H_Gate_On2H | ✅修BUG-6 | 72/72 | 面板监控（**EA 已摘除**） | 待调整 |
| 原油黄金数据行情策略（金） | Gold_DataEvent_EA | ✅修BUG-7 | ⏳Tester 未跑 | 是（SimMode） | 运行观察 |
| 原油黄金数据行情策略（油） | Oil_DataEvent_EA | ✅修BUG-7 | ledger 无成交（EA 已摘除） | 面板监控 | 待调整 |
| 大周期拐点策略 | MCT_EA 阶段5 | ✅无新P0/P1 | 26/26 | 是（SimMode） | 观察期自 09-06，等首笔信号 |
| V 型反转策略 | 纯研究 | ✅定论 | — | 否 | 降级观察（优势消失） |
| 黄金 H1_M30_H4 / 2H_1H_6H、原油 USOIL_1H/2H/30m | 文档型研究线 | 已盘点/立项 | — | 否 | 另立项，无 EA |

## 3. 目录地图（一级）

| 路径 | 是什么 | 能动吗 |
|---|---|---|
| `00_文档中心\` | 跨策略文档唯一入口（状态表/问题记录/公共方法论/监控运维/归档） | 按 R5/R7 进出 |
| `黄金\ 原油\ 原油黄金数据行情策略\ 大周期拐点\ V型反转策略\ 宏观日历研究\` | 策略与共享研究域 | 按策略骨架规范；冻结区禁 |
| `scripts\` | 跨策略工具与监控脚本 | 共享库钉死；一次性脚本走 _archive |
| `observation_dashboard\ ea_alignment_logs\` | 运行时产物 / Tester 对齐工作区 | **禁动** |
| `backup_20260907\` | 一次性归档（后续备份进 `archive\`） | 只进不出 |
| `项目文档\` | 已退役（内容进 00_文档中心） | — |
| 冻结区全表 | 见整理方案 §六 | **禁动** |

## 4. 共享层（挪走即断链，全清单见整理方案 §五）

- 监控五件套：`scripts\{monitor_all_strategies, monitor_cycle, qq_snapshot, watch_signal_alerts, qq_digest_push}.py`
- 公共库：`scripts\{strategy_research_common, replay_raw_signals_with_stops}.py`
- 跨策略引擎与认证基准：`黄金\30m2H策略\参考实现工程\`（multi_tf_matrix + base_data + position_sizing_strict_certify_20260627）
- 监控适配器：MCT / DataEvent 两 adapter（留在各自策略目录）
- 事件日历：`宏观日历研究\data\calendar_export.csv`
- 骨架母本：`00_文档中心\公共方法论\其他策略复用流程.md`
- 公共方法论索引：`00_文档中心\公共方法论\README.md`

## 5. 运行链路（监控是怎么活的）

```
MT5 终端(DAD3B8) 挂 8 EA ──Files导出──> signals/ledger/gate CSV
      │                                      │
      └──── MetaTrader5 python API ──────────┤
                                             ▼
   DSH harness tool-jobs 每30分钟 → scripts\monitor_cycle.py → 监测报告 + dashboard
                                             │
   DSH 网关(profile qqbot) ← qq_snapshot ────┴─ QQ 推送（2min 事件 / 30min 总览）
```
**单点**：DSH Web 进程关闭 = 30 分钟监测循环停。注意 1H_M30_4H_CurrentCandidate 挂图 SimMode=false 且 AllowRealTrading=true（DEMO 账户），与"只读监控"表述有出入——保持关注，变更需走人工决策。

## 6. 当前开放事项（权威登记处见括注）

| # | 事项 | 出处 |
|---|---|---|
| T1 | **30m2H v3.37 对齐验收口径未定**：全窗重跑完成（67 信号 vs 认证 102），信号级对齐仅 13.7%（±60min）；根因=认证管线默认 `ea_executable_diag=False`（含 M15 replace/rescue + 静态 Layer3），≠ EA 可执行口径；**下一步=用 ea_executable_diag=True 重生成认证基线后公平复比**，暂勿据此判定 EA 缺陷 | 黄金\30m2H策略\data\validation\mainline_v337_tester_20260907\30m2H_v337_对齐报告_20260908_v2_m15fixed.md |
| T2 | TODO-8：2H V4 missing 40 笔排查（H6 bar 边界/band 时序） | 00_文档中心\策略审查状态.md §S2-3 |
| T3 | 原油三策略（2H/4H门/数据行情油）待调整：归因→编译→SimMode 恢复挂载 | 各策略 待调整记录_*20260907.md |
| T4 | Gold_DataEvent Tester 未跑（工具链就绪）；MCT 观察期等首笔平仓 | 策略审查状态.md |
| T5 | 乖离反转/1H·2H 旧版 CurrentCandidate BUG 审查（低优先级）；H1_M30_H4 研究线微钻 | 策略审查状态.md §S2 |
| T6 | 目录整理 Phase 2-4（validation 沉底/大对象瘦身/git 重建）| 目录整理方案_20260908.md |
| T7 | 2H_1H_6H 七个空骨架目录去留、P9 三版规范文档权威裁决 | 整理方案（待用户确认） |

## 7. 最近变更日志（滚动 10 条，R7）

- 2026-09-08 21:30 **目录整理 Phase 0/1 完成**：根级 24 散文件收口入 00_文档中心/各策略；12 空目录+56 pycache 清出；母本《其他策略复用流程》提级；新建 00_README/00_项目规则/AGENTS.md；monitor_cycle 频率文案改"DSH tool-jobs 30 分钟"并核实 v3.37 验收已落盘（→T1）
- 2026-09-08 21:07 30m2H M15 孤儿句柄修复重编译部署，Tester 全窗重跑成功（零行为回归）
- 2026-09-08 20:24-20:42 Tester 面板 UI 驱动重跑尝试（ea_alignment_logs\_scratch）
- 2026-09-07 22:45 30m2H 主线 Strategy_EA v3.37 修 8 项+同步终端
- 2026-09-07 20:42 原油三 EA 从 MT5 摘除（用户决策，登记待调整）
- 2026-09-07 19:55 backup_20260907 归档 533 文件；策略审查状态 09-07 快照建立
- 2026-09-06 22:xx 乖离反转 351/351=100% 闭环；2H V4 带通落地
- 2026-09-05 QQ 推送链路上线（后 09-07 体检发现一度停摆，详见监控运维文档）
- 2026-09-06 14:40 MCT 阶段5 模拟盘挂载，观察期起点
- 2026-09-04 问题记录基线建立（BUG-1~15 系列）
