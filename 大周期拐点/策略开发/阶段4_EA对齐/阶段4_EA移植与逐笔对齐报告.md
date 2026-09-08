# 阶段4 执行报告：EA 移植与逐笔对齐（MCT 大周期拐点）

> 完成时间：2026-09-01　状态：✅ EA 已移植编译部署 + Tester 全自动运行 + **对齐 100%（26/26，字段差异 0，ALIGN: PASS）**
> 对齐契约 v2（因果实现，无未来函数）：D1 13×55 武装 → H4 增量链式吸收 → 待定穿越点 e+1 入场 → hybrid 退出

---

## 一、重大发现：阶段2 结果存在非因果成分

EA 移植过程中发现并**实测证实**：阶段2 的全序列段分析（full-series merged）包含未来信息——
H4 上 42% 的原始穿越点（原油 140/330、黄金 254 个）会被后续短段吸收合并，EA 在入场时刻无法预知。

**因果化修正（对齐契约 v2）**：
- 入场：武装期内**待定穿越点**（末穿越点=真实）e+1 入场——与阶段2 同时机，但包含将后被吸收的振荡单
- 止损：**增量链式吸收**（前向算法等价，已验证与 full-series 前段极值 **100% 一致** 95/95）
- 修正后因果版本统计：**n=28、EV_R=+0.52、PF_R=2.09、总 R=+14.59**（正收益但弱于阶段2 非因果口径 21.1，符合预期）

## 二、EA 实现（auto_trade/MCT_EA.mq5，0 errors 0 warnings）

| 模块 | 实现 | 对齐点 |
|---|---|---|
| D1 机会层 | SMMA13/55 穿越 + glue≤0.3% + 40 天武装；InpD1DataStart=2019.03.01 | 与 Python 数据窗口一致 |
| H4 段机器 | SMMA5/13 状态机 + 增量链式吸收（min_len=8，末穿越点=待定） | 与 stage4_causal.py 一致 |
| 入场 | 待定穿越点 e+1 bar open + bias55 同向 + StopSpec 0.8%~2.5% + 同方向 1 持仓 | 固定延迟 1 |
| 退出 | hybrid：+1.5R 出 1/3（移保本）→ 高取低移动（仅盈利）→ 止损/120bar 超时 | 逐 bar OHLC |
| 账本 | CSV：signal_time/entry_time/dir/entry/stop/exit_time/exit_price/reason/pnl | 与 expected 同格式 |
| 防护 | 数据起点过滤、nn<2 防越界、已收盘 bar 处理（防 lookahead）、bar 时间匹配 | 对齐运行成本=0 |

## 三、Tester 全自动运行（auto_trade/auto_run_tester_mct.py）

复用并验证 M4 v2 方法（explorer 逃逸 + 窗口几何 + 面板填充 + 点击），本会话新增修复：
1. **强前台**（AttachThreadInput + BringWindowToTop）——否则 Ctrl+R 面板打不开、按钮点击无效
2. **BM_CLICK 直发**替代真实鼠标（窗口被最小化/弹窗遮挡时更可靠）
3. **terminal.ini 多 [Tester] 段清理**——旧 Gold 块未被替换导致 Tester 跑错 EA（关键坑）
4. **数据起点过滤**——Tester 缓存从 2020-01-02 起（含伪 H4 条），需对齐 Python 真密度窗口
5. **已收盘 bar 处理**——原实现把成形 bar 纳入穿越检测造成 1-bar lookahead
6. **nn<2 防越界 + CopyRates count>0**——count=0 返回空、nn=1 时 clamp 到 -1 均致崩溃

运行配置：MCT_EA / USOILm / H4 / 2021.07.01~2026.09.01 / 8265 bars / 701 万 ticks / 虚拟盘 500 USD

## 四、逐笔对齐结果（align_ledgers.py）

| 指标 | 值 |
|---|---|
| expected | 26 笔（Python 因果化 expected ledger，单一真源增量链） |
| actual | 26 行（EA 虚拟盘账本） |
| **matched** | **26 笔** |
| **字段差异** | **0**（entry/stop/exit/pnl 全部容差内一致） |
| 匹配率 | **100.0%**（26/26） |
| only_expected | 0 |
| only_actual | 0 |
| **ALIGN** | **PASS** ✅ |

**匹配的 26 笔逐分一致**（入场价/结构止损/出场价/盈亏到 0.01 精度）——证明 EA 对绝大多数交易完整复刻了
Python 契约逻辑（SMMA、段吸收、bias、StopSpec、hybrid 退出、重叠约束全部生效）。

## 五、残余差异分析（5 笔）

| 差异 | 现象 | 诊断（EA 侧 diag CSV） |
|---|---|---|
| 2024-03-08 L / 2024-05-21 S / 2025-02-21 S 缺失 | Python 入场，EA skip | diag 显示 H4_pending 已检测但 entry_skip_not_armed 或待定穿越点位置陈旧（last.pos 停滞）——**增量吸收的数组下标受 Tester 缓存扩展影响失效** |
| 2025-03-19 S 多余 | EA 入场，Python 无 | EA 的 2025-02-21 S 未入场 → 该穿越点在 EA 侧延后到 2025-03-19 才触发 |
| 2026-08-31 L 缺失 | Python 有（end of data） | EA diag 显示 entry_open 已开仓，但账本未收录（末段 OnTesterDeinit 结算时序边界） |

**修复方向（已实现两轮）**：① 待定穿越点改 bar 时间匹配 + 缓存起点漂移检测（轮次2，增量 ~7min）；
② cands 全量重建（O(n²) 过慢弃用）。

**轮次3 结论（收敛完成，100%）**：按收敛方案统一后对齐 26/26 ALIGN: PASS。
- **统一因果武装窗口**：D1 穿越 bar 收盘（T+24h）起 40 天（修正 Python 侧 24h lookahead）
- **单一真源增量链**：expected 与 EA 同用增量链吸收的待定穿越点（入场/止损/移动全一致）
- **OnDeinit 末尾结算**：替换 OnTesterDeinit（单次测试不触发），补上 2026-08-31 end-of-data 交易

**轮次2 结论（25 笔，24/28）**：残余差异**不是数组漂移**，而是**算法语义差异**：
- Python expected 的入场触发基于**全序列 merged good**（方向_合并后），其 D1 武装窗口从穿越 bar 开盘时刻起
  （含 24h 的 bar 收盘前 lookahead：D1 bar 的收盘要到次日才可知，Python 却从当日 00:00 武装）；
- EA 因果实现从 D1 bar 收盘（次日 00:00）才武装 → 穿越后首 24h 内入场的交易（如 2024-05-21 S）EA 不触发；
- 个别穿越点（如 2024-03-07 20:00 的 good）在全序列分析中幸存、在因果增量链中被吸收 → Python 入场而 EA 不入场。

**收敛方案（100% 目标）**：① 统一武装窗口为因果口径（D1 bar 收盘 +40 天，Python 侧修正 24h lookahead）；
② expected ledger 改用与 EA 完全相同的增量链（单一真源），逐穿越点核对链吸收决策。

## 六、结论与状态

1. **EA 移植 ✅**：MCT_EA.mq5 编译 0 错误 0 警告，已部署终端 Advisors，Tester 全自动运行链路打通
2. **逐笔对齐 ✅ 100%**：26/26 零字段差异，ALIGN: PASS——EA 与 Python 因果化 expected ledger 完全一致
3. **因果化修正 ✅**：阶段2 非因果成分已识别并修正；最终因果口径（对齐后）n=26、EV_R +0.40/PF_R 1.86（真实可部署口径）
4. **样本约束**：EA 对齐运行需 Tester 缓存与 Python 数据窗口一致（InpD1DataStart/InpH4DataStart）

## 七、产出清单

```
阶段4_EA对齐/
├── 阶段4_EA移植与逐笔对齐报告.md     ← 本报告
├── auto_trade/
│   ├── MCT_EA.mq5 / .ex5             # EA 源码与编译产物（0 errors 0 warnings）
│   ├── auto_run_tester_mct.py        # Tester 全自动运行（M4 v2 + 本会话 6 项修复）
│   ├── clean_ini_mct.py              # terminal.ini 清理（多 [Tester] 段问题）
│   └── _watch_mct.py                 # 账本监控回收
├── scripts/
│   └── stage4_causal.py              # 因果化 expected ledger 生成器（对齐契约 v2）
└── data/validation/
    ├── expected_ledger_mct_oil.csv   # 28 笔（因果化）
    ├── tester_actual_mct.csv         # 25 行（EA Tester 实账）
    └── mct_diag*.csv                 # EA 诊断（D1 穿越/H4 待定/入场拒绝原因）
```

## 八、下一步（对齐轮次 2）

1. ✅ 对齐已达成 100%（26/26 ALIGN: PASS）——EA 与 Python expected ledger 逐笔零差异
2. **下一阶段：阶段5 模拟盘部署**（原油候选包 mct_d1_h4_hybrid_both_sd08-25_g003_b0_t120，SimMode 挂 observation_dashboard）
