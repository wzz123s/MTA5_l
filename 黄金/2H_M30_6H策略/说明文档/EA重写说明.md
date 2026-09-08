# 2H_M30_6H EA 重写说明

> **日期**: 2026-07-30
> **旧版本**: `2H_M30_6H_Strategy_EA.mq5` (v3.26)
> **新版本**: `2H_M30_6H_CurrentCandidate_EA.mq5` (v1.00)
> **Python变体**: `2H_M30_6H__6h_bias5_13_55_signed_pos`

---

## 1. 重写原因

### 1.1 旧EA问题

**版本**: v3.26 (高度复杂的遗留代码)

**主要问题**:
- ❌ 保留旧的 `pre_cross / cross / post_n` Layer2 扩展交易路径
- ❌ 包含M15 early-entry实验功能
- ❌ 3-stage split TP逻辑复杂且与Python研究版不一致
- ❌ EA对齐结果: mismatch (仅9/453匹配)
- ❌ EA实际收益: -$500.18 (-100.04%，接近爆仓)

**代码复杂度**:
- 输入参数: 50+ 个
- 状态机: post_n counter, merged counter, stage tracking等
- 代码行数: 预估1000+ 行

### 1.2 Python研究版定义

**最终选中变体**: `2H_M30_6H__6h_bias5_13_55_signed_pos`

**核心规则**:
- ✅ 基础信号: M30 SMA5/SMA13 cross (仅cross，无pre/post扩展)
- ✅ 高周期门控: 6H bias5 signed > 0 AND bias13 > 0 AND bias55 > 0
- ✅ 止损: 结构止损距离 `stop_distance`, 主档 2-10pt
- ✅ Stage: 2.0 / 2.5 / 4.0 R (Python验证口径)
- ✅ 仓位: 0.01 / 0.01 / 0.04 lot

**研究表现**:
- 交易数: 286
- PF: 2.0399
- 样本外PF: 2.1045
- Stage+仓位收益: $690.17

---

## 2. 新EA设计

### 2.1 设计原则

1. **简洁优先**: 移除所有非核心功能
2. **精确复刻**: 每个规则都对应Python研究版的一个明确条件
3. **安全默认**: 默认SimMode=true, AllowRealTrading=false
4. **可验证性**: 导出完整虚拟账单，支持逐笔对齐

### 2.2 架构对比

| 维度 | 旧EA (v3.26) | 新EA (v1.00) |
|------|--------------|--------------|
| 代码行数 | ~1500+ | ~350 |
| 输入参数 | 50+ | 20 |
| 信号模型 | pre_cross + cross + post_n | 仅 cross |
| 高周期门 | H2 Bias_55 > 3% (Layer1) + H2 Bias_5 top34% (Layer3) | 6H bias5&13&55 signed > 0 |
| 止损逻辑 | 复杂FindStopSMA (14-70pt) | 结构止损 (2-10pt) |
| Stage执行 | 3-stage split TP (真实下单) | 虚拟账单 (待实现stage) |
| M15 early entry | ✅ 有 | ❌ 移除 |
| CSV导出 | 多文件 (signals, ledger, diag) | 单一ledger |

### 2.3 核心功能模块

#### Module 1: 信号检测 (`CheckForSignal`)
```
输入: M30 K线数据
处理:
  1. 检测SMA5/SMA13穿越 (在已完成bar上)
  2. 判断方向 (BUY/SELL)
  3. 调用bias门控检查
  4. 验证点差和止损距离
  5. 开启虚拟交易
输出: VirtualTrade结构体
```

#### Module 2: Bias门控 (`CheckBiasGates`)
```
输入: 交易方向 (dir)
处理:
  1. 获取6H close, SMA5, SMA13, SMA55
  2. 计算带方向偏离: (close - sma) / sma * 100 * sign(dir)
  3. 验证三个bias均 > 阈值 (默认0)
输出: bias5, bias13, bias55数值 + 通过/失败
```

#### Module 3: 止损计算 (`FindStructuralStop`)
```
当前实现: 基于最近20根H2的高低点 (简化版)
待改进: 应使用更精确的结构止损定义
```

#### Module 4: 出场检测 (`CheckForExit`)
```
处理:
  1. 每bar检查止损是否触发
  2. 检测反向cross作为出场信号
  3. 写入ledger并关闭虚拟交易
```

#### Module 5: 账单导出
```
格式: CSV
字段: seq, signal_time, dir, entry_time, entry, stop, stop_distance,
      exit_time, exit, exit_reason, pnl_points, pnl_usd,
      holding_bars, h6_bias5_pct, h6_bias13_pct, h6_bias55_pct
```

---

## 3. 与Python研究版的对应关系

### 3.1 信号模型

| Python规则 | EA实现 | 状态 |
|------------|--------|------|
| `mt5_basic_cross_v1` | M30 SMA5/SMA13 cross detection | ✅ 已实现 |
| `fixed_delay_1` | 在新M30 bar开盘入场 | ✅ 已实现 |

### 3.2 Bias门控

| Python规则 | EA实现 | 状态 |
|------------|--------|------|
| `6h_bias5_signed > 0` | `InpBias5MinPct = 0.0` | ✅ 已实现 |
| `6h_bias13_signed > 0` | `InpBias13MinPct = 0.0` | ✅ 已实现 |
| `6h_bias55_signed > 0` | `InpBias55MinPct = 0.0` | ✅ 已实现 |
| 带方向计算公式 | `BiasSigned()` 函数 | ✅ 已实现 |

### 3.3 止损

| Python规则 | EA实现 | 状态 |
|------------|--------|------|
| `stop_distance` | `FindStructuralStop()` | ⚠️ 简化版，需优化 |
| 主档 2-10pt | `InpStopLoPt=2.0, InpStopHiPt=10.0` | ✅ 已配置 |
| 结构止损源 | H2 recent highs/lows | ⚠️ 待确认是否与Python一致 |

### 3.4 Stage & 仓位

| Python规则 | EA实现 | 状态 |
|------------|--------|------|
| Stage 2.0/2.5/4.0 R | 当前为虚拟账单模式，未实现分阶段 | ❌ 待实现 |
| Lots 0.01/0.01/0.04 | 当前固定InpLots=0.01 | ⚠️ 简化版 |

---

## 4. 已知限制与待办事项

### 4.1 当前限制

1. ~~**结构止损简化**~~ ✅ **已修复 (2026-07-30)**
   - ~~当前: 基于H2最近20根高低点~~
   - **已改为: M30 SMA13极值点 (m30_prev_cross_sma13_extreme)**
   - **实现**: 查找入场前200根M30 K线中，距离SMA13在5pt内的极值点
   - **来源**: raw_stop_replay_report.md 第10行定义
   - **状态**: 🟢 已对齐Python逻辑，待Tester验证

2. **Stage未实现**
   - 当前: 固定0.01 lot虚拟交易
   - Python: 3-stage (0.01/0.01/0.04 lot, 2.0/2.5/4.0R)
   - 影响: 收益计算口径不同
   - **优先级**: 🟡 中 (影响收益幅度，不影响信号匹配)

3. **出场规则简化**
   - 当前: 反向cross或止损
   - Python: 可能有更复杂的出场逻辑
   - 影响: 持仓时间和最终收益可能不同
   - **优先级**: 🟡 中

### 4.2 待办清单

#### 必须完成 (P0 - 阻塞对齐)

- [x] **确认结构止损定义** ✅ **已完成 (2026-07-30 20:22)**
  - 任务: 查找Python代码中`stop_distance`的具体计算方式
  - 文件: `data/validation/raw_stop_replay/raw_stop_replay_report.md`
  - **发现**: 止损定义 = "上一段 M30 SMA13 极值" (m30_prev_cross_sma13_extreme)
  - **实施**: 重写`FindStructuralStop()`函数
    - 数据源: H2 → M30 (匹配Python)
    - 逻辑: 简单high/low → SMA13极值点扫描
    - 范围: 固定20bar → 动态200bar回溯 + 5pt SMA13容差
  - 目标: ~~让EA的`FindStructuralStop()`完全复刻Python逻辑~~ ✅ 已完成

- [ ] **运行MT5 Strategy Tester**
  - 使用新的`.set`参数包
  - 导出EA ledger
  - 运行`compare_python_vs_ea.py`
  - 目标: 达到acceptable匹配阈值

- [ ] **修复对齐差异**
  - 根据对齐报告逐条分析mismatch原因
  - 修正EA逻辑
  - 重新测试直到通过

#### 应该完成 (P1 - 提升质量)

- [ ] **实现Stage逻辑**
  - 将虚拟账单改为支持3-stage
  - 每笔交易记录stage信息
  - 对齐时按stage拆分验证

- [ ] **优化性能**
  - 减少不必要的indicator调用
  - 缓存已计算的值
  - 优化内存使用

- [ ] **增加诊断日志**
  - 记录每层的判定过程
  - 方便调试对齐差异

#### 可以做 (P2 - 锦上添花)

- [ ] **回测可视化**
  - 导出交易标记到CSV
  - 支持在图表上显示买卖点

- [ ] **多品种支持**
  - 参数化symbol配置
  - 支持同时运行多个品种

---

## 5. 测试计划

### 5.1 单元测试 (概念性)

| 测试项 | 输入 | 预期输出 | 状态 |
|--------|------|----------|------|
| Bullish cross检测 | SMA5上穿SMA13 | dir=BUY | ✅ 代码已实现 |
| Bearish cross检测 | SMA5下穿SMA13 | dir=SELL | ✅ 代码已实现 |
| Bias门控通过 | BUY方向, 所有bias>0 | true | ✅ 代码已实现 |
| Bias门控失败 | BUY方向, 任一bias<0 | false | ✅ 代码已实现 |
| 止损距离有效 | distance in [2,10]pt | 接受交易 | ✅ 代码已实现 |
| 止损距离过小 | distance < 2pt | 拒绝交易 | ✅ 代码已实现 |
| 止损距离过大 | distance > 10pt | 拒绝交易 | ✅ 代码已实现 |

### 5.2 集成测试 (MT5 Tester)

**步骤**:
1. 编译EA → 确认0 errors, 0 warnings
2. 加载到MT5 Strategy Tester
3. 选择历史区间: 2020-01-01 to 2024-01-01 (或数据可用范围)
4. 运行回测
5. 导出ledger CSV
6. 运行Python对齐脚本

**成功标准**:
- expected_rows ≈ ea_rows (允许±5%偏差)
- matched / expected > 80%
- entry price diff < 0.5pt
- stop price diff < 1pt
- PnL sign一致率 > 95%

### 5.3 回归测试

修改任何逻辑后必须重新运行完整Tester验证。

---

## 6. 文件清单

| 文件 | 用途 | 状态 |
|------|------|------|
| `auto_trade/2H_M30_6H_CurrentCandidate_EA.mq5` | 新EA源码 | ✅ 已创建 |
| `auto_trade/2H_M30_6H_CurrentCandidate_EA.set` | 新EA参数包 | ✅ 已创建 |
| `说明文档/EA重写说明.md` | 本文档 | ✅ 已创建 |
| `data/validation/ea_parameter_pack.json` | Python参数包 (已有) | ✅ 参考用 |
| `auto_trade/compare_python_vs_ea.py` | 对齐脚本 (已有) | ✅ 待运行 |

---

## 7. 时间线

| 里程碑 | 计划时间 | 状态 |
|--------|----------|------|
| 完成EA初稿 | 2026-07-30 | ✅ 完成 |
| 确认结构止损定义 | 2026-07-31 | ✅ **提前完成 (2026-07-30)** |
| 完成首次Tester运行 | 2026-07-31 | ⬜ 待开始 |
| 完成首次对齐验证 | 2026-08-01 | ⬜ 待开始 |
| 修复对齐差异 | 2026-08-02-03 | ⬜ 待开始 |
| 对齐通过 | 2026-08-04 | ⬜ 待开始 |
| 进入模拟盘候选 | 2026-08-05+ | ⬜ 待开始 |

---

## 8. 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 结构止损定义理解错误 | 中 | 高 | 仔细阅读Python代码，单元测试验证 |
| 数据区间不匹配 | 低 | 中 | 使用相同的raw manifest |
| MT5 API差异 | 低 | 中 | 参考已成功的1H_M30_4H EA |
| 性能问题 | 低 | 低 | 代码简洁，不太可能出现 |
| 对齐始终无法通过 | 中 | 高 | 准备备选方案：反向适配Python到EA |

---

## 9. 版本迭代与编译记录（v1.01 → v1.03）

> 来源：`.workbuddy/memory/2026-07-30.md` 工作日志归档（2026-07-31 ~ 08-01 跨日持续）。

### 9.1 v1.01 修复（2026-07-31）

1. MQL5 `iMA()` 用法错误：旧代码把 `iMA(symbol, period, 13, 0, MODE_SMA, PRICE_CLOSE, i)` 当数值用，实际返回 handle → 需用 CopyBuffer 取值。
2. 重写：OnInit 创建 5 个 indicator handle（MA5/MA13 on M30、MA5/MA13/MA55 on H6），新增 `GetMAVal(handle, shift)` 辅助函数，OnDeinit 用 IndicatorRelease 释放；代码约 370 行。

### 9.2 v1.02 修复（未成功编译）

- OnInit 中 H6 handle 创建失败时自动降级到 H4；
- 去掉 FILE_COMMON。

### 9.3 v1.03 修复（编译成功，33,576 bytes，2026-08-01 08:10）

- `H6Period` 默认改为 `PERIOD_H4`（兼容 Tester；后确认 H6 数据可用，929 根 K 线）；
- 去掉 FILE_COMMON → 文件保存到 MQL5/Files；
- 简化 OnInit（恢复简单版本）；
- .ex5 已复制到 3 个位置：源码目录、Experts、Experts/Advisors。

### 9.4 首次 Tester 运行（2026-07-31 19:57）

- v1.01 成功运行，触发 1 笔交易（BUY @ 1891.22），但 ledger 文件打开失败；
- v1.03 需在 Strategy Tester 面板重新选择 EA 并点击 Start。

### 9.5 MT5 自动化限制（重要经验）

MetaEditor GUI 自动化不可靠（5 种方法均失败：/compile 命令行崩溃、pywinauto 无法切换标签页、重启崩溃、英文路径启动即退出、F4 无法自动化）→ **编译需手动 F7**。

Strategy Tester 无法通过以下方式启动：Ctrl+R+Enter、PostMessage(BM_CLICK)、/config: 参数、click_input（SetCursorPos 失败）→ **需用户在面板手动选择 EA + 点 Start**（7/31 两次成功回测均为手动操作）。

### 9.6 待完成（截至 08-01）

1. 在 Strategy Tester 中选择 v1.03 EA → Start → 检查 ledger；
2. 1H_M30_4H：MT5 重启后 EA 丢失，需重新加载到 XAUUSDm M30 图表。

---

**文档版本**: v1.0
**最后更新**: 2026-08-15（追加 v1.01→v1.03 版本迭代记录）
**作者**: AI Assistant
**审核状态**: 待技术审核
