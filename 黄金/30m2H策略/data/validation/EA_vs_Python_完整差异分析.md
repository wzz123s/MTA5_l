# MT5 EA vs Python 策略完整差异分析报告

**生成时间**: 2026-07-10
**分析对象**:
- EA: auto_trade/30m2H_Strategy_EA.mq5 (v3.25)
- Python: scripts/_current_baseline.py + _pre_cross_range_test.py + _m15_early_entry_test.py + _h2_early_gate_test.py
- **预期信号数**: EA ~90-95, Python ~101 (差距 ~6-11个信号)

---

## 差异 #1: [SMMA计算] - M30 SMA5/13 的 SMMA 实现差异

### EA 实现
EA 在 cross 检测和止损计算时使用 MT5 内置 CopyBuffer (MODE_SMMA)，与 Python 的 calc_smma() 初始化方式不同。
- MT5 内置 MODE_SMMA: 第一个值 = 第一个 close 价格
- Python calc_smma(): 初始化值 = 前 N 个 close 的均值

### Python 实现
全部使用 calc_smma() 函数，初始化值为前 N 个 close 的均值。

### 影响: **高**
导致早期 SMMA 值不同，影响:
1. cross 检测的 bar index 可能偏移 ±1-2 bars
2. FindStopSMA() 找到的 segment 起点不同
3. post_n counter 的计数时机可能错位

### 修复方案
将 OnTick() 中的 M30 SMA 数据获取统一改为 PythonSMMA()，移除 g_ma_fast_m30 和 g_ma_slow_m30 句柄的使用。

---

## 差异 #2: [Cross检测] - Bar index 和时机的差异

### 影响: **高**
Python 的 cross 检测在当前遍历的 bar i 上，而 EA 是在 last completed bar (bar[1]) 上。当 SMMA 数据源不一致时，cross 发生的 bar index 会偏移。

### 修复方案
确保两端 SMMA 数据完全一致后（修复差异#1），cross 检测的 bar index 应该对齐。

---

## 差异 #3: [Pre_Cross检测] - 遍历范围差异

### 影响: **中**
- Python: range(1, len(df)-1) 排除首尾bar
- EA: 不排除（依赖外部调用时的数组边界）
可能导致 Python 丢失最后一个 bar 上的 pre_cross 信号。

---

## 差异 #4: [Post_N计数器] - 更新逻辑和重置条件差异

### 影响: **高**
1. EA 使用 raw direction (未合并), Python 使用 merged direction (短 segment <8 bars 被吸收)
2. EA 的重置条件过于激进：趋势翻转但不是cross时就立即重置为0
预期 EA 的 post_n 信号比 Python 少 3-5 个。

### 修复方案
让 EA 的 post_n 计数也基于 merged direction，或调整重置逻辑使其更宽松。

---

## 差异 #5: [M15 Early-Entry] - Slot选择逻辑和触发时机差异

### 影响: **中-高**
1. EA 支持 slot1+slot2, Python 只用 slot1
2. EA 缺少 require_earlier 显式检查
3. Rescue 路径覆盖范围不同

### 修复方案
统一下Slot选择（只保留slot1），添加 require_earlier 检查，统一 rescue 条件。

---

## 差异 #6: [H2 Early-Gate Q2] - 估算Bias55计算

### 影响: **低**
数学公式完全等价，唯一微小差异来自浮点精度（可忽略）。

---

## 差异 #7: [Layer3过滤] - Bias_5 Top% 计算的滚动窗口差异

### 影响: **高**

1. **计算窗口语义完全不同**:
   - EA: 固定回看 500 根 H2 bar 的全局滚动阈值
   - Python: 只在候选信号集上计算的静态阈值
   
2. EA 的方法更保守，可能比 Python 多过滤掉 3-5 个信号。

### 修复方案
将 EA 改为 Python 的静态 quantile 方法（需要重构信号生成流程）。

---

## 差异 #8: [StopLoss计算] - FindStopSMA 的搜索范围差异

### 影响: **中**
Segment 区间边界和极值查找范围可能有 ±1 bar 的偏差。

### 修复方案
调整 EA 的循环边界使其与 Python 一致（跳过 seg_start 点）。

---

## 差异 #9: [并发限制 MAX_POS=3] - 实现逻辑差异

### 影响: **中**
EA 基于实际 Stage exit 逻辑，Python 基于 24 小时简化持有模型。这是架构级差异。

### 修复方案
改进 Python 端的持仓模拟逻辑，使用与 EA 一致的 Stage exit 规则。

---

## 差异 #10: [Spec Check] - Stop distance validation 时机差异

### 影响: **低-中**
EA 用真实 ASK/BID 检查，Python 用历史 OHLC proxy。可能差 1-2 个信号。

---

## 差异 #11: [Entry Price] - 入场价格取值方式

### 影响: **低**
各 mode 下 entry price 取值方式一致（close/typical）。最终执行价格差异只影响 PnL 不影响信号计数。

---

## 差异 #12: [Time Filtering] - 时间对齐差异

### 影响: **中**
EA 使用 MT5 服务器时间，Python 对 H2 数据应用了多级时间偏移。如果偏移参数配置不当会导致 H2 bar align 错误。

### 修复方案
确认 Python 的时间偏移常量与 MT5 服务器的实际时区一致。

---

## 总结: 影响程度排序和预期信号差距来源

| 优先级 | 差异项 | 影响程度 | 预期信号差距 |
|--------|--------|----------|-------------|
| P0 | #1 SMMA计算不一致 | 高 | 2-4 个 |
| P0 | #4 Post_N重置策略过激 | 高 | 3-5 个 |
| P0 | #7 Layer3滚动窗口vs静态 | 高 | 3-5 个 |
| P1 | #2 Cross检测bar偏移 | 高 | 2-4 个 |
| P1 | #5 M15 slot选择和rescue | 中-高 | 1-3 个 |
| P2 | #3 Pre_Cross遍历范围 | 中 | 0-1 个 |
| P2 | #8 StopLoss搜索边界 | 中 | 0-1 个 |
| P2 | #9 MAX_POS实现差异 | 中 | ±2 个 |
| P3 | #10 Spec check时机 | 低-中 | 0-1 个 |
| P3 | #12 Time filtering | 中 | 1-2 个 |
| P4 | #6 H2 early-gate公式 | 低 | 0 个 |
| P4 | #11 Entry price | 低 | 0 个 |

**总预期差距**: 6-11 个信号（与观察到的 ~90-95 vs ~101 基本吻合）

### 推荐修复顺序
1. **第一步**: 统一 SMMA 计算（#1）→ 解决 cross/post_n/stop 计算的基础数据一致性
2. **第二步**: 调整 Post_N 重置策略（#4）或迁移到 merged direction → 恢复 3-5 个 post_n 信号
3. **第三步**: 对齐 Layer3 过滤方式（#7）→ 恢复 3-5 个被过度过滤的信号
4. **第四步**: 统一 M15 slot 选择和 rescue 路径（#5）→ 恢复 1-3 个 M15 信号
5. **第五步**: 微调其余边界条件（#2, #3, #8, #9, #10, #12）→ 收尾剩余差距

完成前 3 步后，预期信号差距应缩小到 2-4 个（进入可接受的工程误差范围）。
