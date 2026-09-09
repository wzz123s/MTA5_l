# 千问工作助理 · MTA5_l 项目总索引

> 本文件是进项目的**第一份读物**（人 AI 皆同）。只指向权威文件、不复述内容（复述即漂移）。
> 建立：2026-09-08（目录整理 Phase 1）｜维护规则见 00_项目规则.md R7
> 数据截至：2026-09-09（本地，变更明细见 §7 最新条目）

## 1. 一句话工程定义

黄金/原油多策略量化研究工程：Python 研究管线 + MQL5 EA 模拟盘 + 自动监控告警；账户为 Exness DEMO（277752085）。

**交易口径（2026-09-09 实测纠偏）**：终端 `trade_expert=True`，9 个挂载实例中 6 个在 DEMO 真下单；窗口 2025-01-01~2026-09-09 共 121 笔成交／59 个持仓，balance 2667.61 = 入金 2089.46 + 交易净盈利 578.15。`.set` 非真相源，真相源是 `chart*.chr` 终端实参（T12）。证据与逐笔还原见 `00_文档中心\问题记录.md` §二十三。

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
| 大周期拐点策略 | MCT_EA 阶段5 | ✅无新P0/P1 | 26/26 | diag 在写、台账仅表头 | ⚠️**观察期空转**：EA 自认末根 bar 停在 2026.08.30 20:00，每根新 bar 判 `entry_skip_not_last` → 永远等不到首笔信号；**根因在 EA 侧 bar 序列读取，非行情源**（实测 USOILm H4 末根 = 09-08 16:00、D1 = 09-08 00:00，数据新鲜）。挂 chart12(USOILm,H4)、SimMode=true 不下单（T15／§二十三⑦） |
| V 型反转策略 | 纯研究 | ✅定论 | — | 否 | 降级观察（优势消失） |
| 黄金 H1_M30_H4 / 2H_1H_6H、原油 USOIL_1H/2H/30m | 文档型研究线 | 已盘点/立项 | — | 否 | 另立项，无 EA |

> **2026-09-09 注（§二十三⑥）**：本表"监控=是"仅指 signals/gate 导出链路活着（实测 0.1h 前仍在更新）；**成交台账链路是断的**——4 个 `*_trade_ledger.csv` 因 MQL5 未加 `FILE_SHARE_READ` 被 EA 独占句柄，Python 侧 `PermissionError` 读不到；`30m2H_abc_trade_ledger.csv`／`MCT_trade_ledger.csv`／`30m2H_strategy_deal_history.csv` 仅有表头。故"监控中"≠"成交可见"，监测报告与 dashboard 里没有真实成交数据（T14）。各 EA 真下单状态见 §1 与 §二十三①。

## 3. 目录地图（一级）

| 路径 | 是什么 | 能动吗 |
|---|---|---|
| `00_文档中心\` | 跨策略文档唯一入口（状态表/问题记录/公共方法论/监控运维/归档） | 按 R5/R7 进出 |
| `黄金\ 原油\ 原油黄金数据行情策略\ 大周期拐点\ V型反转策略\ 宏观日历研究\` | 策略与共享研究域 | 按策略骨架规范；冻结区禁 |
| `scripts\` | 跨策略工具与监控脚本 | 共享库钉死；一次性脚本走 _archive |
| `observation_dashboard\ ea_alignment_logs\` | 运行时产物 / Tester 对齐工作区 | **禁动** |
| `archive\` | 统一归档层，现存 `backup_20260907\`、`AI数据中心资本开支研报\`、`插件调研\` | 只进不出 |
| 冻结区全表 | 见整理方案 §六 | **禁动** |

## 4. 共享层（挪走即断链，全清单见整理方案 §五）

- 监控五件套：`scripts\{monitor_all_strategies, monitor_cycle, qq_snapshot, watch_signal_alerts, qq_digest_push}.py`
- 公共库：`scripts\{strategy_research_common, replay_raw_signals_with_stops, live_attribution}.py`（`live_attribution.py` = 2026-09-09 新增：DEMO 实挂成交的 **position_id 血缘归因** + `chart*.chr` 终端实参/下单闸读取 + 台账可读性体检，被 `monitor_all_strategies.py` 与 `monitor_cycle.py` 调用；口径依据 `00_文档中心\问题记录.md` §二十三——盈亏记到开仓方 magic，禁用平仓侧 `deal.magic` 与 `deal.reason`）
- 部署工具：`scripts\deploy_ex5_by_chr.py`（2026-09-09 新增，治 T22）——按 `.chr` 的 `path=` 精确投递 `.ex5`，**不硬编码 `Experts\` 或 `Experts\Advisors\`**；默认 dry-run、`--apply` 才写、投递前备份、投递后 sha256 校验、生成 R8 清单；不启动/不重启终端（新版需人工逐图表刷新才生效）。**此后任何 .ex5 更新都应走它**
- 跨策略引擎与认证基准：`黄金\30m2H策略\参考实现工程\`（multi_tf_matrix + base_data + position_sizing_strict_certify_20260627）；⚠️ 其 `auto_trade\auto_trader.py` 具备**独立实盘下单能力**（两处 `mt5.order_send`，magic=302025），窗口内无 302025 成交、启用状态无文档登记（§二十三⑪）
- 监控适配器：MCT / DataEvent 两 adapter（留在各自策略目录）
- 多机协作须知：`00_文档中心\监控运维\多机协作初始化与同步须知.md`（路径硬约束：各机 clone 到 `F:\use_code\MTA5_l`；密钥/归档目录不进库）
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
**单点**：DSH Web 进程关闭 = 30 分钟监测循环停。

**盲区（2026-09-09 实测）**：Files 导出链路只对 signals/gate 成立；成交台账 4 个文件被 EA 独占句柄、3 个仅表头 → 监测报告与 dashboard 无真实成交。修复状态与细节见 §6-T14 与 `00_文档中心\问题记录.md` §二十三⑥。
## 6. 当前开放事项（权威登记处见括注）

> **收口快照（2026-09-09 21:10 更新）**：T12/T17/T18/T19①③/T20 已收口；**T11/T14 已部署生效（09-09 21:10 全图刷新）；T13 已收口（chart14 摘除）；T22 已收口（chart06 加载 09-08 M15 修复版）**；T15/T16 未动等拍板；T1/T2/T3/T4/T5/T7 继续开放。逐项完整证据一律以括注出处为准。

| # | 事项 | 出处 |
|---|---|---|
| T1 | **30m2H v3.37 对齐验收口径未定**：全窗重跑完成（67 信号 vs 认证 102），信号级对齐仅 13.7%（±60min）；根因=认证管线默认 `ea_executable_diag=False`（含 M15 replace/rescue + 静态 Layer3），≠ EA 可执行口径；**下一步=用 ea_executable_diag=True 重生成认证基线后公平复比**，暂勿据此判定 EA 缺陷 | 黄金\30m2H策略\data\validation\mainline_v337_tester_20260907\30m2H_v337_对齐报告_20260908_v2_m15fixed.md |
| T2 | TODO-8：2H V4 missing 40 笔排查（H6 bar 边界/band 时序） | 00_文档中心\策略审查状态.md §S2-3 |
| T3 | 原油三策略（2H/4H门/数据行情油）待调整：归因→编译→SimMode 恢复挂载 | 各策略 待调整记录_*20260907.md |
| T4 | Gold_DataEvent Tester 未跑（工具链就绪）；~~MCT 观察期等首笔平仓~~ → **MCT 部分已失效，转 T15**（数据源滞后 9 天，观察期空转） | 策略审查状态.md ／ §二十三⑦ |
| T5 | 乖离反转/1H·2H 旧版 CurrentCandidate BUG 审查（低优先级）；H1_M30_H4 研究线微钻 | 策略审查状态.md §S2 |
| T6 | ✅ **已执行（09-08）**：Phase 2 一次性脚本与 validation 沉底 + Phase 3 大对象压缩 + Phase 4 git 重建（首提交 2657 文件、.gitignore 扩排除）；**残留 D5**：`ea_alignment_logs\_scratch`（100 个 Tester UI 驱动脚本）收口待 30m2H 主线验收闭环后做 | 00_README §7（09-08 23:15 条）＋整理方案 §七 D5 |
| T7 | 2H_1H_6H 七个空骨架目录去留、P9 三版规范文档权威裁决 | 整理方案（待用户确认） |
| T8 | ✅ **已按中间方案执行（09-08）**：全树扫描 1430 个现役文本 → 零引用 6 目录归档 _archive、被引用 230 个不动；validation 根生成 **目录索引.md**（230 行：修改日/文件数/体积/保留原因）；"≤20"仅约束新增实验（R6）| 黄金\30m2H策略\data\validation\目录索引.md |
| T9 | ✅ **已执行（09-08）**：base_data_backup(60MB) 与 V反 features×4 逐文件 sha256 校验全过 → 原件送回收站（共回收 ~99MB，zip 副本在位）；**tester_agent 原件按决定保留至 T1 收口** | 00_文档中心\归档\整理清单\t9_verify_report_20260908.txt |
| T10 | D4 裁决收口：原油 6H/8H 门与金叉实验被原油 2H 现役管线脚本引用 → **原地保留不归档**（用户 09-08 确认）| 00_README（本条即登记） |
| T11 | **P0 归因 BUG｜🔧 代码已修 + 编译 0 errors，待部署**（09-09 09:13）：`2H_M30_6H_ABC_EA` / `30m2H_ABC_EA` 已补 `g_trade.SetExpertMagicNumber(InpMagic)`（照抄 1H ABC L719-723 已验证范式，注释内写明实测证据）；原缺陷致平仓 deal 落 magic=0、**15/59 持仓开平错配**，按 magic 统计使 2H ABC 显示 −279.62（真实 **+68.17**）、1H ABC −68.82（真实 **+161.76**）、主线 S3 0.00（真实 **+177.87**）。**A3（主线 stage 级平仓 magic）按裁决暂缓**：血缘归因已覆盖其后果，且主线 v3.37 正在 T1 验收中 | 问题记录 §二十三③④⑤ + A/D 阶段一 |
| T12 | **P0 配置漂移**：工作区全部 `*SimDeployment*.set` 写 SimMode=true/AllowReal=false，终端实参为 false/true → `.set` 非真相源、R1④ 失效、事故无法复现参数；需终端实参反向导出为权威 `.set` 入库 | §二十三① |
| T13 | **P0 双挂**：`30m2H_ABC_EA` 两实例同 magic 352036、同图表周期（**chart07** SimMode=false/AllowReal=true 与 **chart14** SimMode=true/AllowReal=false，终端日志 09-08 00:21:30.935 与 00:21:31.093 各一条 loaded successfully），共写一份台账 → sim 实例 init 把 `30m2H_abc_trade_ledger.csv` 清成仅表头，352036 的 6 笔成交在台账中消失；signals_export 亦互相覆盖 | §二十三⑧＋补充取证1 |
| T14 | **P1 台账断链｜🔧 代码已修 + 编译 0 errors，待部署**（09-09 09:13）：**9 个 EA / 26 处 `FileOpen` 已补 `FILE_SHARE_READ`**（照抄主线 Strategy_EA 既有范式——它本来就带，故其台账实测可读；不带的正是 4 个 `PermissionError` 的来源）。幂等脚本先 dry-run 逐行核对再 apply，保持各文件原编码（1H CurrentCandidate 是 utf-8-sig）。残留：`monitor_magic_302025.py`/`scan_magic_302025.py` 仍指向已废弃 magic 302025；adapter 内部台账读取的异常处理**未核实** | §二十三⑥⑫ + A/D 阶段一 |
| T15 | **P1 MCT 空转**：EA 自认末根 bar 停在 2026.08.30 20:00，每根新 bar 判 `entry_skip_not_last` → 观察期（09-06 起）实际无任何入场评估。**根因更正：不是行情源滞后**——实测 USOILm H4 末根 09-08 16:00、D1 末根 09-08 00:00（数据新鲜），是 **EA 侧 bar 序列读取/缓存停在 8 天前**；挂载已确证 chart12(USOILm,H4)、OnInit 无 Print 故 Experts 日志查不到。修好后观察期起点重算 | §二十三⑦＋补充取证 |
| T16 | **P1 人工干预未留档**：08-29 00:49 乖离空头 372037 被人工平仓（comment `manual close (TP overdue)`，+177.05），`00_文档中心\` 全目录 grep 命中 0 条；且该空单浮盈 177 点期间 EA 退出逻辑始终未触发（退出逻辑缺陷线索）。做空门禁判定：**非门禁失效**（两笔开空 08-22/08-24 早于 09-04 停用结论） | §二十三⑨ |
| T17 | **口径**：盈亏归因须用 position_id 血缘而非 deal magic；台账/EA 日志用服务器时间而 `deal.time` 转本地 **+8h**，T1 逐笔对齐若不统一会系统性错配；magic→EA 映射表（此前无任何文档登记）已建于 §二十三② | §二十三②③⑩ |
| T18 | **P1 监控读错图表**：`monitor_all_strategies.py` L214 `read_ea_input()` 硬编码 `chart10.chr`、唯一调用点 L537 不传 chart_file → 恒读 chart10=**Gold_DataEvent_EA**，而 `ea_inputs` 只给 BiasReversal 配了 `InpLongMode` → **在 Gold_DataEvent 图表里找乖离反转参数**，必然返回 None → dashboard/报告「EA模式」列**从来没有内容**；且解析只支持数字（bool 读不出）、chart 编号会随增删重排（chart05/08/11 已空）→ 应按 EA 名扫描全部 `.chr` | §二十三 补充取证3 |
| T19 | **P1 归因配置缺口**：`STRATEGY_CONFIGS.magics` ①缺历史 magic 302025/302026/302027/302028 → 6 月 9 个持仓（合计 −137.50）监控完全看不到；②粒度过粗：`30m2H`=[302036~302039,**352036**] 把主线与 ABC 合并一行、`1H_M30_4H`=[**312026**,312036] 把 CurrentCandidate 与 ABC 合并、`BiasReversal`=[372036,372037] 多空合并；③`read_real_positions()` 只读 `positions_get()` 不读 `history_deals_get()` → 监控设计上**没有"已实现盈亏"这个量**，只有浮盈。另 L621 报告脚注写死"只读监控不下单"= §1 错话源头 | §二十三 补充取证4·5 |
| T20 | ✅ **已修（09-09 02:42）**：原 P1 隐患——`rebuild_and_attach_mct.py`/`attach_mct_ea_to_chart.py` 认 chart12=Oil_DataEvent、chart13=MCT；`deploy_combo_ea.py` 认 TARGET=chart10。实测 chart12=**MCT_EA**、chart13=空、chart10=**Gold_DataEvent_EA** → 重跑会顶掉 Gold_DataEvent、造成 MCT/乖离双挂并重启（`deploy_combo_ea.py` 更是 `taskkill /F` 强杀终端 + 备份两行是死代码）。**修法**：三个脚本植入前置守卫 `live_attribution.guard_deploy()`，按 EA 名动态读实际盘面，命中「目标 EA 已挂载／目标 chart 被别的 EA 占用／模板 chart 已漂移」任一条即中止，需 `--force` 才放行。**验证**：三脚本实跑均 exit 1 安全中止，`chart10.chr`/`chart13.chr`/`order.wnd` mtime 仍为 09-08 21:29（未改任何终端文件） | §二十三 补充取证二4 |
| T21 | **口径（重要）**：MT5 `DEAL_REASON` 字段**不可靠**——`comment='[sl 4670.599]'` 的亏损平仓被记 `reason=TP`、`comment='manual close (TP overdue)'` 的人工平仓被记 `reason=SL`；全窗口 `EXPERT` 0 笔而 magic=0 的 13 笔被记 12×SL+1×CLIENT。故归因**只用 position_id 血缘 + 开仓 magic**，禁用 `deal.magic`（平仓侧）与 `deal.reason`；平仓类型以 `comment` 前缀 + EA 台账 `local_exit_reason` 交叉判定。另 `signals_export.csv` 是**滚动窗口**（实测仅 47 行≈24h）不含历史 → 历史信号↔成交比对只能走台账 | §二十三 补充取证二1·2·6 |
| T22 | **P1 新发现（09-09 09:20 部署前置核对）：终端两个 Experts 目录致 `.ex5` 双副本版本漂移，且已造成一次"假部署"**——`MQL5\Experts\`（根）与 `MQL5\Experts\Advisors\` 各存一份同名 `.ex5`，而 `chart06`（主线）与 `chart02`（CurrentCandidate）的 `.chr` `path=` 指向**根目录**那份。主线：根目录 = 09-07 22:36/150,280B（**实盘在跑**），Advisors = 09-08 20:23/150,354B 且与工程内 `auto_trade\` 产物**时间与字节数完全一致** → §7「09-08 21:07 M15 孤儿句柄修复重编译**部署**」实际投递到了不被加载的目录，**该修复从未在实盘图表生效**（虽记载为"零行为回归"）。CurrentCandidate 同样双副本（根 08-11 19:38/63,020B ← chart02 在用；Advisors 08-21 21:46/64,712B 未使用）。**处置原则：部署必须按 `.chr` 的 `path=` 精确投递**，否则＝假部署；并应清理冗余副本、在部署脚本里加"目标路径来自 .chr"的校验 | 本轮 dir 终端两处 Experts + `.chr` path 交叉核对 |
| T23 | **版本号对齐（2026-09-09 登记）**：乖离反转口径代号 v8 与 EA `#property version` 1.00 未对齐；机制已生效，推荐在下次发布/认证基线统一并打 tag（当前不立即改源码） | 黄金\乖离反转策略\版本记录.md |

## 7. 最近变更日志（滚动 10 条，R7）

- 2026-09-09 **版本记录机制＋工程审查整改收口**：①版本机制——EA `#property version` 为机器可读发布版本、仅在发布/认证基线通过时递增，发布按 `策略名-EA名-vX.Y` 打 tag；8 策略新增 `版本记录.md`；R1/R9 写入规则；git 身份 wzz；origin=https://github.com/wzz123s/MTA5_l 已接入。②审查整改——README 复述收敛与状态行统一、R7 滚动裁法、R6 存量目录索引豁免（`check_project_rules.py` 实跑 0 违规）、T23 乖离版本号对齐登记、遗留工作区收口（多轮 commit 见 git log）。多机须知：`00_文档中心\监控运维\多机协作初始化与同步须知.md`
- 2026-09-09 21:10 **A/D 阶段二自动落地（用户授权"自动执行"，正常退出＋重启，未强杀）**：T11/T14 已投递新版 ex5 全 9 图载入生效（chart02/03/04/06/07/09/10/12）；**30m2H_ABC_EA chart14 双挂实例已摘除（T13 收口）**；终端 `Experts\Advisors\` 内 ABC 旧版 `.ex5/.mq5` 送回收站，仅存新版（SHA `0B28E6FB…`，09-09 09:09 编译 60,648B）；核验=Experts 日志 8 个 EA 各 loaded ×1、`chart_layout()` 8 实例无 ABC 双挂、台账 `PermissionError` 全消失、`30m2H_abc_trade_ledger.csv` 恢复可写（chart07 init 后仅表头，待新成交落行）；chart14.chr 已去 EA 块（备份 `scripts\_archive\2026-09\chart14_chr_pre_remove_20260909.chr`）。详见问题记录 §二十三「A/D 阶段二落地记录」
- 2026-09-09 21:2x **T1 公平基线第一轮重跑（ea_executable_diag=True + MAXPOS=3）**：Python expected（限定 Tester 窗口）75 信号 vs EA Tester 67 信号；对齐 matched **56/75=74.7%（±120min）**、missing 19、EA extra 11；旧基线 13.7%（±60）口径偏差已排除大半，但仍低于 ABC/1H/2H 的 94%+ 验收水平 → T1 未收口，进入逐笔差分（missing 19 中 14 笔 EA 同 bar `no_cross`、2 笔模式错位、2 笔方向门矛盾、1 笔窗口尾）。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-09 21:3x **T1 逐笔差分（missing 19 / extra 11）定族**：missing=EA 同 bar `no_cross` ×15、`HOLD` 错位 ×1、`no_trigger` ×1、121-150min 相位 ×1、窗口尾 ×1；extra 11 全部 `PY_NO_CANDIDATE`（EA 发的信号 Python 完整候选根本没有）→ **剩余缺口收敛到 EA merged/post_n 计数与 H2 方向判定，非 M15/MAXPOS/时间轴**。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-09 21:4x **T1 merged 逐 bar 对账**：同 base_data 重建两侧 merged/post_n——missing 18 笔锚点计数一致且在带内（计数非根因、EA 0–1 仓开放→也非 maxpos），extra 9 笔 EA 计数 2–6 在带而 Python 已漂出（EA 短段吸收/复位时点更早）；**修正差异族=①短段吸收时机 ②EA 入场门(H2/Layer3/stop) ③两套持仓轨迹差异**。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-09 21:5x **T1 ①causal吸收＋②门复现**：extra 9 用 Python causal 仍未解释（EA 500-window 滚动 vs Python 全样本 causal）；missing 18 的 Layer3 全过、Layer1(completed bias55) 7 笔失败、13 笔两层都过仍不发 → 需 EA 逐 tick 500-window 复刻 / q2 early 复算 / EA DiagLog 对照。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-09 22:0x **T1 收口步骤更正**：① extra 8 笔 EA win==full → 根因=计数语义（EA 方向符号复位 vs Python good/bad 起数），非 500-window；② canonical q2 early 复算 missing **19/19 全在 Layer1 放行集**（先前 7 笔 FAIL 作废）→ missing 非 Layer1/q2/Layer3；③ Tester DiagLog 未留存，需重跑取证。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-09 22:1x **T1 rolling_merged 修正复跑**：Python 候选 152→177（窗口内 expected 86），对齐 matched 56→64、**EA extra 11→3**（计数语义假设验证）；missing 19→22、对齐率 74.7%→74.4%（±120）→ extra 基本清零，主残差=missing 22（EA 该发未发，2025/2026 集中）。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-09 22:2x **T1 missing22 Diag 取证定因**：用 09-08 Tester 全窗日志（169MB）按 anchor 抽取实际拒门——Layer1 FAIL ×7（EA early elapsed_q=0 而 Python canonical 放行）、stop SPEC_FAIL ×8（3.8~74.9 vs spec 5–35 边界）、Candidate 通过未见拒行 ×3、日志无 anchor ×4 → 修复方向=Python 精确复刻 EA early-gate 与 stop 边界口径。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-09 22:3x **early-gate 修复试跑结果**：单点打 EA 边界补丁后对齐 ±120 64→61、extra 3→6、对齐率 74.4→73.5% → **单点修不改善**；EA/Python 差为 early-gate＋stop 边界＋MAXPOS 顺序复合效应，需用日志 stop_pts 校准后组合验证。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-09 22:4x-5x **组合验证＋逐指标第一批**：按 EA Diag 实拒 15 笔校准 Python expected → 对齐 64/71=**90.14%**（未达 94%）；逐指标比对 18 anchor 的 close/SMA5/SMA13 **完全一致（Δ≤5e-6）**→ 差异转向 H2 SMA55/bias55 与 stop 段极值/换算。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-09 23:0x **指标矩阵全量比对**：18 anchors 中 close/SMA5/13 全一致；H2 bias55 17/18 一致（2025-10-29 20:30 EA 3.354 vs PY 3.001 一处差异）；Layer3 阈值系统性微差（EA vs PY 差 0.0008~0.0047）；**stop_pts 差异最大**（如 34.97 vs 27.9、2.0 vs 10.4、37.6 vs 11.2）→ 根因指向 FindStopSMA 段极值与 stop 换算。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-09 23:1x **三处差异源码级定位**：①H2 bias55＝EA 按实际 tick shift1、Python 固定 date+30min → 差 1 根 H2；②Layer3 阈值＝EA 含当前 H2 样本、Python `start:idx` 排除 → 实测含当前即与 EA 完全一致；③stop 差＝ea_executable 下 Python 仍保留 **M15 SLOT1** 入场（EA v3.35 已移除）→ 修复顺序 A/B/C 见问题记录。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-09 23:2x **A+B 修复入库并复跑**：源码改 `_current_baseline.py`（Layer3 含当前样本＋ea 模式去 M15）；复跑对齐 **64/76=84.2%（±120）**、missing 22→12、expected 0 行 M15 SLOT1；C（H2 tick 索引）经实验证明全局改会劣化（right 17/18 vs left 11/18），唯一个例已被 A+B 消除，暂不实施。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-09 23:3x **missing12 Diag 取证**：残余 missing=EA Layer1 FAIL ×6（early elapsed_q=0）、NO_CANDIDATE ×3、GATE_PASS 未见 OPEN ×2、STOP_SPEC_FAIL ×1 → 主残余回到 EA early-gate 边界；下一步在 A+B 基础上复测 early-gate 补丁。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-09 23:4x **early-gate 复测＋deep trace**：early-gate 补丁在 A+B 后复测仍降（84.2→83.3%、extra 3→7）→不采纳；2 笔 GATE_PASS 真相=EA Execute 三档全返回 0（执行层被拒）；3 笔 NO_CANDIDATE=EA/Python post_n 差 1 bar 相位 → A+B 84.2% 为现行基线，残余=early×6+执行层×2+相位×3+stop×1。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-09 23:5x **全量指标比对**：74,071 EA bar 与 Python 按 30min 标签差对齐后 72,376 行，**M30 close/SMA5/SMA13 差异 0（max|Δ|=0）**；signals_export 的 H2 列为部分/滚动估计值、非 completed H2，不可全量直比 → H2 决策比对以 Candidate Diag/补导出为准。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-09 23:6x **#3–#13 全量/事件级**：#3 raw cross 72,376 行 0 差；#9 H2 方向全窗 0 差；#5 post_n 19,923/19,929（6 差=起点历史）；#10 bias55 19,742/19,929（187 差）；#12 bias5 643/651；#13 阈值 473/651（178 差，含当前样本后仍余窗口差）；#4/#6/#7/#8/#11 需 EA 补导出。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 00:0x **EA 导出改造＋Tester 重跑（Phase1–3）**：signals 增至 31 列（completed-H2/merged/pre_cross/q2 early），74,071 行全导出、ledger 67 信号与旧版零差异；全量比对=H2 close/sma5/13/55/bias55/bias5 与 merged_code **0 差**；残留：L3 阈值 22,568 差、pre_cross 6,188 差、post_n 31 差（起点边界）。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 00:2x **四类残余前置诊断**：post_n31=测试窗初始化历史深度差；pre_cross6188=Python 0.05% vs EA 0.3% 阈值＋锚定差；L3阈值22568=非含当前问题、历史窗口时序差；q2 early=Python canonical early 与 EA CalcBias55EarlyQ 边界/elapsed 不一致。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 00:3x **pre_cross 全量归零**：EA DetectPreCross 语义（0.3%＋两根 bar 锚定）重算 74,071 行，EA/Python 均 5,255、mismatch 0。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 00:4x **L3 阈值重建定位**：EA H2 历史=Python 子集（0 数据差）、失配遍布全窗口、窗口变体无法闭合 → 指向 EA IsBias5TopPct 样本窗/percentile/导出时序细节，需导出每 bar valid_count/样本窗边界后定死。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 00:1x **L3 再导出取证**：第二轮 Tester 产出 l3_valid_count=500、percentile_idx 恒 329，但 Python idx 329/330 均不闭合 → 差异在 500 样本历史时序细节，需 EA 直接导出样本向量。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 01:0x **L3 500 向量定因**：第三轮导出 107MB 样本；EA b1==Python current → **H2 Bias5 窗差 1 bar 是主因**；部分样本校正后仍余差 → 需统一 EA/Python H2 时间轴（date=bar close）后全量复算。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 01:2x **L3 全量校正复算**：19,391 H2 样本用 b5[j-500:j] 复算，阈值失配 11,432（idx329）→ −1 窗必要非充分；残余=历史 H2 值时序差，需 EA 时间轴逐 bar 重排或以 EA 向量替换计算。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 01:4x **Layer3 EA-baseline 试跑**：threshold 直接取 EA 500 样本后 matched 63/75=84.0%（未升、extra+1）→ L3 失配非验收阻塞项；残余主因=early×6/执行层×2/相位×3/stop×1。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 02:0x **执行层 Execute=0 定因**：源码确认 Tester 内 AllowReal=false 不挡单；日志实抓 retcode=10018 **Market closed** → 两笔为收盘不可成交伪差，应从 Python expected 剔除后重算对齐。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 02:1x **Market-closed 剔除重算**：expected 76→74、matched 64/74=**86.49%**、missing 12→10 → 残余=early×6+相位×3+stop×1。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 02:3x **early-gate EA 真值试跑**：Layer1 按 EA 导出真值过滤后 matched 64/70=**91.43%**、missing 6 → early ×6 已消除；离验收线差 2.6pt。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 02:4x **最终残差**：EA 真值＋market-closed 剔除后 matched **64/68=94.12%**，missing4（3 相位＋1 stop）/extra3 → 已达 94% 参照线。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 02:5x **相位/stop 专项**：missing3=EA post_n 内部跳段（n3/n4 不发 Candidate）、missing1=stop 执行边界（34.97 vs 35.2）、extra3=起点族/Python 缺链/pre_cross 覆盖 → 不影响主体一致性。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 03:0x **T1 最终验收报告**：[T1_最终验收报告_20260910.md](黄金/30m2H策略/data/validation/mainline_v337_tester_20260907/T1_最终验收报告_20260910.md)——正式验收口径（EA 真值 Layer1＋rolling＋MAXPOS3＋market-closed 剔除）对齐 **64/68=94.12%**；方法=原始行情→前置指标→Candidate Diag 逐层比对。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 03:1x **验收脚本固化**：[t1_acceptance_20260910.py](黄金/30m2H策略/scripts/validate/t1_acceptance_20260910.py)——可重复运行，复现 **PASS（64/68=94.12%）**；输出 `T1_验收报告_acceptance_run_20260910.md`。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 03:3x **EA CalcBias55EarlyQ Python 复刻试验**：[ea_earlygate_replica_test_20260910.py](黄金/30m2H策略/scripts/validate/ea_earlygate_replica_test_20260910.py)——H2 date=bar open 语义逐行模拟，与 EA q2_early_pass 全量匹配 **72,186/72,376（99.74%）**，190 差全为 sim=1/EA=0 且 est_bias≈3.00–3.05 临界；暂不足以替代 EA 导出真值，正式验收继续以 EA 真值为准。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 03:4x **190 临界差索引实验**：offset−1 最优仍 190；差异=EA prev_sma55 历史值比 Python 高 0.04–0.08 bias 单位且未导出 → 归零需 EA 补导出 prev_sma55/partial_close。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 02:0x **第 4 轮中间量取证（190 归零）**：EA 新增 q2_prev_sma55/q2_partial_close 后全窗复算，calc vs EA mismatch=0、maxΔ=5e-5 → 190 归零；残余差异=Python h2 SMA55 历史值校准问题。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 02:3x **h2 SMA 校准入库**：`_h2_context.py` 用 EA mean-init 重算全部 H2 SMA 列；early 复刻 72,376 行 mismatch=0，验收仍 PASS 94.12%。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 02:5x **验收脚本去 EA 依赖＋残余专项**：[t1_acceptance_20260910.py](黄金/30m2H策略/scripts/validate/t1_acceptance_20260910.py) 改用校准后 Python Layer1 复刻，仍 PASS 94.12%；[T1_postn相位_stop边界_专项_20260910.md](黄金/30m2H策略/data/validation/mainline_v337_tester_20260907/T1_postn相位_stop边界_专项_20260910.md) 给出处理方案。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 03:0x **持仓占用 diff**：2020-07-28=EA_open3 阻塞可解释；另 2 missing EA_open0 仍不发；extra 均非容量。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 03:1x **0仓不发候选深追**：两笔=EA counter 比 Python 慢 1 bar（13:00 -3 vs -4；12:00 4 vs 5），12:30 到 n5 时被 max_pos 拦 → post_n 相位族。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 03:3x **31 笔相位专项修正**：31 全在测试起点（非2025）；2025 两笔=Python expected 收盘取档差 1 bar，不是 counter 相位。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 03:5x **日期语义实证**：Python date=EA ledger anchor（bar open）、entry=bar close（EA signals bar_time）；日期语义定死，2025 两笔归 counter 相位已知族。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-10 04:0x **残余归属台账**：[T1_残余归属台账_20260910.md](黄金/30m2H策略/data/validation/mainline_v337_tester_20260907/T1_残余归属台账_20260910.md)——口径内 missing4/extra3 与口径外已解释差异全列明。详见问题记录 §二十三「T1 第一轮公平基线重跑」
- 2026-09-09 09:13 **A/D 阶段一：T11 与 T14 的代码修复已编译通过，`.ex5` 未部署（全程未启动/未打断终端）**：按用户裁决执行（A3 暂缓、D1 全 9 个 EA、部署方式＝我复制 ex5 + 用户逐图刷新、借窗口一并摘 chart14）。**A1/A2**：`2H_M30_6H_ABC_EA` 与 `30m2H_ABC_EA` 的 OnInit 补 `g_trade.SetExpertMagicNumber(InpMagic)`，照抄 1H ABC L719-723 已验证范式，注释内写明各自实测证据（2H ABC：3 笔平仓 magic 落 0 致按 deal.magic 统计 −279.62 而血缘还原为 +68.17；30m2H ABC：属**潜伏未爆发**，其 3 笔平仓全由服务器 SL 触发故 magic 得以保留）。**D1**：9 个 EA / **26 处** `FileOpen` 补 `FILE_SHARE_READ`（照抄主线 Strategy_EA 既有范式——它本来就带故台账实测可读，不带的那批正是 4 个 `PermissionError` 的来源，因果逐一对应）；用幂等脚本先 dry-run 逐行核对再 `--apply`，保持各文件原编码（1H CurrentCandidate 是 utf-8-sig）、正确识别 `FILE_CSV \| FILE_WRITE` 顺序变体、已含该 flag 的行跳过。**编译**：`MetaEditor64.exe /compile` 独立进程（不启动终端），**9/9 全 0 errors** 且 `.ex5` mtime 全部刷新（判据用日志 errors 数 + ex5 刷新，不以 exit code 为准）；warnings 全部落在**未改动行**（`warning 39 expression not boolean` 于 2H ABC L944/30m2H ABC L875/1H ABC L877/Gold_DE L869，`warning 43 long→double` 于 BiasReversal L169·173·254·258/Oil_DE L255）= 既有、非本次引入；9 份编译日志按 R1④ 留各 `auto_trade\`（**过程修正**：初版日志名不带 EA 名致同目录 ABC 与 CurrentCandidate 互相覆盖，改带 EA 名后重跑）。**复验**：`live_attribution.py` 10 项断言仍全 PASS、台账仍 4 个 `PermissionError` —— 均符合"未部署"预期（终端仍跑旧 `.ex5`）。**阶段二**（备份旧 ex5 → 复制到终端 → 用户逐图刷新 chart02/03/04/07/09/10/12 + 摘 chart14 → 我跑 4 项事后核验）等用户给打断窗口，步骤与回滚见 问题记录 §二十三「A/D 阶段一落地记录」第 5 条
- 2026-09-09 02:42 **T20 修复：三个部署脚本植入 chart 守卫，"重跑就炸"的地雷拆除（未动任何终端文件）**：三者的 chart 编号假设已全部失效——`deploy_combo_ea.py`（`taskkill /F` 强杀终端 + 把 chart10 的 Gold_DataEvent 换成 SimMode=false/AllowReal=true 的乖离反转 → 顶掉 + 双挂，且备份两行是死代码 `shutil.copy2(...) if False else None`）、`rebuild_and_attach_mct.py`（以 chart12 为结构模板，而 chart12 现已是 MCT_EA 自己 → 会造 MCT 双挂同 magic 411103）、`attach_mct_ea_to_chart.py`（假设 chart13 含 MCT expert 块，实测是 2122B 空图表 → 白重启一次终端打断 9 个实例）。**修法**：`live_attribution.py` 新增 `chart_layout()` + `guard_deploy()`，三脚本各植入前置守卫——按 EA 名动态读实际 chart→EA 盘面，命中「目标 EA 已挂载（双挂）／目标 chart 被别的 EA 占用（顶掉）／模板 chart 已漂移」任一条即 `SystemExit`，需显式 `--force` 才放行。**验证（执行级+端到端）**：单元三场景（A 中止报 2 项／B `Oil_DataEvent_EA`+`chart11.chr` **放行不误拦**／C 中止报 2 项）+ 三脚本本体实跑均 exit 1（`deploy_combo_ea.py` 输出无 `ex5 copied`，证明未进写入分支），`chart10.chr`(70,254B)/`chart13.chr`(2,122B)/`order.wnd`(548B) mtime 仍为 **09-08 21:29** = 未改任何终端文件。附带修掉守卫自身缺陷：初版 `reconfigure(utf-8)` 让人工在 GBK 控制台看到的中文提示全乱码 → 改为不动调用方编码、`⚠` 换 ASCII `!!`。下一步（用户已定顺序）：排 A/D 打断窗口修 T11（P0，越晚修越多成交被错误归因）→ G1 并入 T1
- 2026-09-09 02:34 **F 项落地：监控改用血缘归因，"看不见的成交"变可见（未动任何 EA/终端）**：新建公共库 `scripts\live_attribution.py`（R3 已登记本文件 §4 + `scripts\README.md`）——`position_id` 血缘归因 + `chart*.chr` 只解析 `<expert>` 块取终端实参/双闸 + 台账可读性体检 + `EA_MAGIC_MAP` 22 条（补历史 magic 302025~302028）；`monitor_all_strategies.py` 改 6 处（dashboard 增列 `realized_pnl_usd`/`live_positions`/`magic_mismatch`/`ea_gate`/`ledger_state`、`read_ea_input` 弃硬编码 chart10 改按 EA 名定位、台账/降级/双挂/闸开无成交全部写进 warnings、新增「真实成交归因」节、**L621 脚注"只读监控不下单"纠偏**）；`monitor_cycle.py` 改 3 处（总览表增列 + 账户级合计行 + `ea_load_state` 报"8 个 EA/9 次加载 ⚠30m2H_ABC_EA×2"）。**验证**：`live_attribution.py` 自校验 **10 项断言全 PASS**（578.15/2089.46/2667.61/错配15/9实例/6真下单/双挂/两层合计一致）；`--no-refresh` 全策略实跑各行已实现盈亏 161.76+281.68+68.17+66.54=**578.15**；端到端 `monitor_cycle.py` 生成 `监测报告_20260908_1814.md` 三列有值。**T18 修复生效**（BiasReversal 的 `ea_mode` 首次显示 `0-6H门+H1金叉`，此前恒空）。**T12 收口**：9 个 `.chr_export_<chart>_20260909.set` 终端实参快照按 R8 清单新增至各策略 `auto_trade\`（未覆盖任何既有 .set），并更正"`.chr` 只记被改动参数"的保守声明——实测 `<expert><inputs>` 是**完整参数集**（乖离源码 23 input = 导出 23 参数）。**G2 完成**：台账 7 行 vs deals 按 `deal_ticket` **7/7 匹配**、profit 一致、时间恒差 +8h → EA 台账内容准确，问题在 magic 落 0/base 与台账被清空/独占；**G2 原设想不可行**（`signals_export` 仅 24h 滚动窗，覆盖不到成交时段）；**G1 建议并入 T1**（认证窗口 2020-03-06~2026-06-11 与实挂窗口 06-23~09-02 零重叠，合流才能形成三口径对照）。过程中修掉自身两处缺陷（指标参数混入 EA 实参致 chart07 漏识别、per_ea 用首个 magic 冒充 EA 标签）并复验。**A/D 项（改 EA 代码）与 B/C/E 项（终端手工）未做，等拍板**。9 个 `_tmp_*_20260909` 取证文件按 R4 归档 `scripts\_archive\2026-09\`（清单 `tmp_scripts_archive_20260909.csv`，grep 确认无代码引用；既有 6 个旧 `_tmp_` 脚本未误动）
- 2026-09-09 01:20 **DEMO 实挂下单盘面只读取证 + 文档纠偏（未改任何 EA 代码/终端设置）**：应用户质疑「模拟账户就是要大胆下单找问题」，以 MetaTrader5 API 只读查询 + Experts 日志原文 + 源码同层读回 + position_id 血缘还原，证实 §1「全链路只读监控不下单」不成立（`trade_expert=True`、**9 实例中 6 个真下单**、121 笔成交、balance 2667.61=入金 2089.46+交易净利 **578.15**）。根因锁定 `CTrade` 未设 ExpertMagicNumber：2H ABC / 30m2H ABC **仍缺**（1H ABC 09-02 已修、主线 09-01 修而不彻=平仓恒 base magic）→ 15/59 持仓开平 magic 错配、三策略盈亏被误判为亏损/零收益。另查出：台账 4 处 `PermissionError`+3 处仅表头（=监控盲区与本文档误判的技术根源）、MCT 观察期空转、`30m2H_ABC_EA` 双挂同 magic 清空台账、08-29 人工平仓 `manual close (TP overdue)` 未留档、magic 312026 潜伏冲突、服务器/本地时间差 8h。产出 `问题记录.md` **§二十三**（含 magic→EA 权威映射表、血缘对照表、分级建议 P0×3/P1×4/P2×3）；本文件 §1/§2/§4/§5 按实测纠偏、§6 新增 T11~T21、T4 的 MCT 部分转 T15。**01:40 补充取证更正两处**：①实例 9 个（终端日志 9 条 loaded successfully）、真下单 **6** 个——CurrentCandidate 经 `chart02.chr` 读出 `InpAllowRealTrading=true` 确证在真下单（初判"8 个中 5 个、CurrentCandidate 未确证"作废）；②MCT 根因**不是数据源滞后**，实测 USOILm H4/D1 末根均为 09-08（数据新鲜），是 EA 侧 bar 序列停在 08-30 20:00。同轮确证 chart→EA 全映射（chart07/chart14 双挂同 magic 352036）、`read_ea_input` 恒读 chart10 致「EA模式」列恒空（T18）、`magics` 配置缺历史 magic 且粒度过粗（T19）、`.chr` 可解析 bool 故 T12 可全自动反向导出 `.set`。取证脚本 7 个 `scripts\_tmp_*_20260909.py` 待归档（R4）。**01:50 二次更正（自我纠错）**：以 `deal.reason` 复核后，§二十三④"13 笔 magic=0 全部是 EA 所为、非人工"的断言**作废**（实测 12×SL + 1×CLIENT、`EXPERT` 全窗口 0 笔），且 `DEAL_REASON` 字段本身不可靠（`comment='[sl 4670.599]'` 的亏损平仓被记 `reason=TP`、人工 `manual close (TP overdue)` 被记 `reason=SL`）→ 归因**禁用** `deal.reason`（T21）。magic=0 主因仍是 EA 主动退出路径（源码 BUGFIX 注释 + 台账 7 行按 `deal_ticket` 逐笔交叉验证支持；其中行6 stage2 trail 修改 182 次而 magic 保留，**推翻"改 SL 致 magic=0"假说**）。另查出 chart 编号漂移致三个部署脚本图表假设全部失效（T20：`deploy_combo_ea.py` 重跑会把乖离 EA 写进 chart10 **顶掉 Gold_DataEvent** 并重启终端）；并**撤回**"EA 每 30 分钟周期重载"推测（仅 09-07 晚 3 批呈 29~30 分钟间隔，09-08 00:21 后 25h 稳定，台账清空时刻与最后一批 init 吻合）。详见 §二十三 补充取证二
- 2026-09-09 00:45 **文档一致性修正 6 处（纯文档，无文件移动）**：①整理方案头部状态行由"方案待确认、未执行任何移动/删除"改为"D1~D5 已拍板、Phase 0~4 执行完毕"，并注明 §一/§二 为执行前快照；②整理方案 R3 登记位置 §5→§4（对齐 00_项目规则.md 与本文件实际编号）；③本文件 §6 T6 标 ✅已执行，残留 D5（`_scratch` 收口）显式留档不丢；④本文件 §3 目录地图同步盘面（`backup_20260907\` 已迁入 `archive\`、补 `archive\` 行、移除已不存在的 `项目文档\` 行）；⑤**R1~R9 去分叉（用户裁决 A）**：撤掉整理方案内的规则草案表，改为指向 `00_项目规则.md` §一 的单源指针，仅保留权威版未收录的"谁改谁记"原则，原表 git 可溯；⑥**填平 §五c 编号缺口**：整理方案 五b→五d 之间原无 §五c 标题，却有 4 处引用（含 00_项目规则.md 头部）全为死链 → 将"00_项目规则.md 内容规范"子标题提级为 `## 五c` 接通全部引用，并把 §五b 第 7 段的"见 §五c 规则第 4 条"改指 `00_项目规则.md` §三 收尾义务第 1 条。另按滚动 10 条裁掉最旧 2 条（09-04/09-05，git 可溯）
- 2026-09-08 23:15 **目录整理 Phase 2/3/4 执行完毕**：乖离反转根 21 脚本归位 scripts\（syspath 精确改写、编译 0 失败）+ 策略 README 建立；H1_M30_H4 根级 20 md 归位说明文档；30m2H validation 30 目录沉 _archive\2026-07（白名单 236 偏保守→T8）；auto_trade .bak 7 个归位；Phase3 三组 .zip 生成（原件保留→T9）；**git 重建**（首提交 2657 文件，.gitignore 扩数据/产物排除）；机检 scripts\check_project_rules.py 上线（首跑 17 违规=R4×4 已修+T8/T9 登记）
- 2026-09-08 21:30 **目录整理 Phase 0/1 完成**：根级 24 散文件收口入 00_文档中心/各策略；12 空目录+56 pycache 清出；母本《其他策略复用流程》提级；新建 00_README/00_项目规则/AGENTS.md；monitor_cycle 频率文案改"DSH tool-jobs 30 分钟"并核实 v3.37 验收已落盘（→T1）
- 2026-09-08 21:07 30m2H M15 孤儿句柄修复重编译部署，Tester 全窗重跑成功（零行为回归）
- 2026-09-08 20:24-20:42 Tester 面板 UI 驱动重跑尝试（ea_alignment_logs\_scratch）
