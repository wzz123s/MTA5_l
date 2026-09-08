# MT5 EA v3.25 vs Python 策略 — 完整差异分析与修复方案 v2

> **生成时间**: 2026-07-10 21:02
> **分析对象**: EA v3.25 (UpdatePostNState 已改回 PythonSMMA) vs Python export (ea_executable_diag=True + 静态 Layer3)
> **预期**: EA ~90-95 信号 vs Python ~101 信号，差距 ~6-11 个

---

## 一、已修复项（v3.25 已完成）

| # | 模块 | 差异内容 | 状态 |
|---|------|---------|------|
| F0 | UpdatePostNState SMMA源 | 已从 CopyBuffer(MODE_SMMA) 改回 PythonSMMA | ✅ 已修 |
| F0 | post_n 重置条件 | 已添加 direction mismatch 时 reset=0 | ✅ 已修 |

---

## 二、剩余差异清单（按影响程度排序）

### 🔴 P0-A: OnTick 主流程 M30 Cross/Stop 数据源不一致（预计影响 2-4 个信号）

#### 问题详解

EA 在以下关键路径仍使用 **MT5 内置 MODE_SMMA**（首值=第一个价格），而非 PythonSMMA：

| 位置 | 行号(约) | 用途 | 当前数据源 |
|------|---------|------|-----------|
| `GetM30SMAArrays()` → OnTick | L437-444 → L1781 | cross检测 / post_n判断 / FindStopSMA输入 | `CopyBuffer(g_ma_fast_m30)` MODE_SMMA ❌ |
| `M30Cross()` | L418-419 | 独立 cross 检测函数 | `GetMALastN(g_ma_fast_m30)` ❌ |
| `FindStopSMA()` 输入 | L439 (via caller) | 止损极值搜索的 SMA 数组 | `GetM30SMAArrays()` → MODE_SMMA ❌ |
| Stage3 Exit | L1947 | SMA5/13 金叉/死叉平仓 | `GetMALastN(g_ma_fast_m30)` ❌ |
| post_n SL | L2061 | post_n 模式止损 = 当前SMA13 | `GetMALastN(g_ma_slow_m30)` ❌ |
| ShouldExit | L1012-1013 | Legacy 反向 cross 平仓 | `GetMABars(g_ma_fast_m30)` ❌ |
| TrailStage2 SL | L894 | Stage2 移动止损追踪 | `GetMALastN(g_ma_slow_m30)` ❌ |
| H2 CSV输出 | L1856-1864 | CSV 写入 H2 SMA 值 | `GetMALastN(g_h2_smaX)` ❌ (H2也用MT5 SMMA) |

#### 为什么这很重要

SMMA 初始化差异导致：
- **cross 发生时机偏移 ±1-2 bars** → post_n 计数器起始点错位
- **FindStopSMA segment 起点不同** → 止损极值不同 → spec check 通过/失败翻转
- **Stage3 平仓时机偏移** → MAX_POS=3 并发数不同 → 后续信号被拦或放行

#### 修复方案

**核心思路**: 将 OnTick 主流程中的 M30 SMA5/13 数据获取改为 PythonSMMA 批量计算。

```mql5
// ===== 新增函数: GetM30SMAArrays_Python() =====
// 替代 GetM30SMAArrays(), 使用 PythonSMMA 获取 M30 SMA 数据
int GetM30SMAArrays_Python(double &fast[], double &slow[], int max_bars)
{
   ArrayResize(fast, max_bars);
   ArrayResize(slow, max_bars);
   int valid = 0;
   for(int i = 0; i < max_bars; i++)
   {
      // shift=1 是最近完成的 bar, shift=max_bars 是最老的
      double f = PythonSMMA(InpSymbol, InpM30Period, 5, i + 1);
      double s = PythonSMMA(InpSymbol, InpM30Period, 13, i + 1);
      if(f == 0 || s == 0) continue;
      fast[valid] = f;
      slow[valid] = s;
      valid++;
   }
   // 反转使 [0]=oldest, [valid-1]=newest (与 GetMABars 输出一致)
   ArrayReverse(fast, 0, valid);
   ArrayReverse(slow, 0, valid);
   return valid;
}
```

**需要修改的调用点**:
1. **OnTick L1781**: `GetM30SMAArrays(fast_ma, slow_ma, n_sma)` → `GetM30SMAArrays_Python(fast_ma, slow_ma, n_sma)`
2. **FindStopSMA 调用**: 自动继承（因为输入数组变了）
3. **Stage3 L1947**: 改为 PythonSMMA 单值调用
4. **post_n SL L2061**: 改为 PythonSMMA 单值调用
5. **TrailStage2 L894**: 改为 PythonSMMA
6. **ShouldExit L1012**: 改为 PythonSMMA

**性能注意**: PythonSMMA 有内部缓存（key=Bars()+period），同一 bar 的重复调用命中缓存。批量加载 N 个 values 需要 N 次缓存查找+数组索引，比 CopyBuffer 慢但可接受（每根 M30 bar 调用一次）。

**H2 SMA 句柄**: Bias_55/Bias_5/EarlyQ 已改用 PythonSMMA。但 CSV 输出和 H2CrossDetector 的 H2 SMA5/SMA13 仍用 CopyBuffer — 这些只影响日志不影响信号，可暂不修改。

---

### 🔴 P0-B: Layer3 过滤方法根本性不同（预计影响 3-5 个信号）

#### 问题详解

这是**架构级差异**，是信号差距的最大来源之一：

| 维度 | EA v3.25 | Python (export_with_mt5_data.py) |
|------|----------|--------------------------------|
| **函数** | `IsBias5TopPct()` | `cb.apply_layer3()` |
| **方法** | 滚动窗口 500 bars | **静态分位数**（在候选集上一次性计算）|
| **计算范围** | 回看 500 根 H2 bar 的历史偏差 | 所有通过 Layer1+Layer2 的候选信号 |
| **阈值特点** | 每个信号评估时动态变化（随时间窗口滑动）| 固定阈值（由候选集整体分布决定）|
| **代码位置** | EA L1220-1251 | `_current_baseline.py` L106-109 |

**Python 实现** (L106-109):
```python
def apply_layer3(final_acc, top_pct=DEFAULT_TOP_PCT):  # top_pct=34
    threshold = float(final_acc["Bias_5"].quantile(1 - top_pct / 100.0))
    picked = final_acc[final_acc["Bias_5"] >= threshold].reset_index(drop=True)
    return threshold, picked
```

**EA 实现** (L1220-1251):
```mql5
bool IsBias5TopPct(double current_bias5)
{
    // 加载最近 500 根 H2 bar 的 close 和 SMA5
    // 计算 500 个 Bias_5 值
    // 取 (1-34%) = 66% 分位作为阈值
    // 比较 current_bias5 >= threshold
}
```

**为什么差异大**:
- 静态分位数: 如果候选集中有 100 个信号，始终取第 67 名最大的 Bias_5 作为门槛 → 相对宽松
- 滚动窗口: 在某些历史时段（如低波动期），500-bar 窗口内的 Bias_5 整体偏低 → 阈值偏低 → 更多通过；在高波动期则相反
- 关键区别: 静态方法保证恰好 34% 的**候选**信号通过；滚动方法通过的信号比例随市场状态波动

#### 修复方案（两个选择）

**选项 A: 修改 EA → 静态量化方法（推荐，完全对齐 Python）**

问题: EA 是实时系统，无法预知所有"候选信号"。但可以近似:
- 方案 A1: 收集一整段回测期的 Bias_5 快照，预先算好全局阈值硬编码
- 方案 A2: 改用更大的滚动窗口（如 5000 bars ≈ 全部数据）来逼近全局分布
- 方案 A3: 在回测中两遍扫描——第一遍收集所有 candidate bias5，第二遍用静态阈值

**选项 B: 修改 Python → 滚动窗口方法（对齐 EA）**

修改 `export_with_mt5_data.py` L91:
```python
# 原来:
threshold, picked = cb.apply_layer3(final_acc, top_pct=TOP_PCT)

# 改为:
threshold, picked = cb.apply_layer3_ea_executable(
    final_acc, h2, top_pct=TOP_PCT, lookback=500)
```
这样 Python 会模拟 EA 的滚动 500-bar 行为。

**推荐选项 B**（改动最小，立竿见影）: 先在 Python 端对齐验证信号差距缩小幅度，再决定是否需要在 EA 端做等价修改。

---

### 🟡 P1-A: M15 Slot 选择策略差异（预计影响 1-3 个信号）

#### 差异对比

| 维度 | EA v3.25 | Python (ea_executable_diag=True) |
|------|----------|----------------------------------|
| Slot 范围 | slot1 **+ slot2** (L1607 允许 1 或 2) | **仅 slot1** |
| 选择函数 | 取最近的已完成 M15 bar | `choose_slot1_by_distance` + `require_earlier=True` |
| require_earlier | ❌ 无此检查 | ✅ M15 入场必须早于 M30 close |

#### EA 代码 (L1605-1608):
```mql5
int slot_in_m30 = ...;
// v3.25: Check both slot1 and slot2
if(slot_in_m30 < 1 || slot_in_m30 > 2) return false;  // ← 允许 slot1 和 slot2
```

#### Python 代码 (`_current_baseline.py` L67-74):
```python
cov_mod, _ = m15t.apply_replace_variant(
    cov, m15,
    m15t.choose_slot1_by_distance,  # ← 仅 slot1
    "ea_slot1_replace",
    require_earlier=True,           # ← 必须更早
    reanchor_stop_by_distance=True,
)
```

#### 修复方案

**EA 端修改**:
```mql5
// L1607: 只允许 slot1
if(slot_in_m30 != 1) return false;  // 原: slot_in_m30 < 1 || > 2

// 新增 require_earlier 检查
datetime m30_close_time = slot_m30_open + PeriodSeconds(InpM30Period);
datetime m15_entry_time = completed_m15_open + PeriodSeconds(InpM15Period);
if(m15_entry_time >= m30_close_time) return false;  // 必须 M15 先于 M30 关闭
```

---

### 🟡 P1-B: Rescue 路径覆盖范围差异（预计影响 1-2 个信号）

#### 差异对比

| 维度 | EA v3.25 | Python (ea_executable_diag) |
|------|----------|---------------------------|
| 触发条件 | `m30_sd > InpStopHi` (仅 too_wide) | `~raw_df["spec_pass"]` (所有 spec_fail) |
| rescue 入场价 | M15 close (slot1) | M15 close (choose_slot1_by_distance) |
| rescue 止损 | 复用原 M30 止损 | reanchor_stop_by_distance |

#### EA 代码 (L2076-2079):
```mql5
double m30_sd = MathAbs(C - stop_price) / exec_point;
if(m30_sd > InpStopHi && InpUseM15EarlyEntry)  // ← 仅 too_wide
{
    // ... try M15 rescue
}
```

#### Python 代码 (`_current_baseline.py` L75-85):
```python
# ea_executable_diag: 救援 ALL spec_fail (不只是 too_wide)
rejected_runtime = raw_df[
    (~raw_df["spec_pass"])
    & m15t.coverage_mask(raw_df, m15_start)  # ← 所有未通过 spec 的
].copy()
rescued, _ = m15t.build_rescued_trades(
    rejected_runtime, m15,
    m15t.choose_slot1_by_distance,
    variant_name="ea_slot1_runtime_rescue",
    reanchor_stop_by_distance=True,
)
```

#### 修复方案

**EA 端扩展 rescue 条件**:
将 `m30_sd > InpStopHi` 改为 `m30_sd > InpStopHi \|\| m30_sd < InpStopLo`（覆盖 too_wide + too_tight），或者更进一步在 SPEC_FAIL 后统一尝试 rescue。

⚠️ 注意: Python 端 rescue 还做了 `reanchor_stop_by_distance`（基于 M15 入场价重新算止损），EA 当前复用原 M30 止损。这也是一个差异点。

---

### 🟡 P1-C: post_n 止损 SMMA 源（预计影响 0-1 个信号，影响止损质量）

#### EA 代码 (L2059-2063):
```mql5
// v3.25: post_n SL = current SMA13 using CopyBuffer (fast path)
double sma13_buf[];
if(GetMALastN(g_ma_slow_m30, 1, sma13_buf) && ArraySize(sma13_buf) > 0)
{
    stop_price = NormalizeDouble(sma13_buf[0],  // ← MODE_SMMA
}
```

应改为:
```mql5
double sma13_p = PythonSMMA(InpSymbol, InpM30Period, 13, 1);
if(sma13_p > 0)
    stop_price = NormalizeDouble(sma13_p, 5);
```

---

### 🟢 P2-A: Stage3 Exit Cross 检测 SMMA 源（预计影响 0-1 个信号，通过 MAX_POS 间接影响）

#### EA 代码 (L1946-1950):
```mql5
double stage3_fast[], stage3_slow[];
if(GetMALastN(g_ma_fast_m30, 2, stage3_fast) && GetMALastN(g_ma_slow_m30, 2, stage3_slow))
{
    bool prev_above = (stage3_fast[1] > stage3_slow[1]);  // ← MODE_SMMA
    bool curr_above = (stage3_fast[0] > stage3_slow[0]);
```

应改为 PythonSMMA(shift=1) 和 PythonSMMA(shift=0)。

---

### 🟢 P2-B: FindStopSMA 搜索边界（预计影响 0-1 个信号）

EA 的 FindStopSMA (L482-492):
```mql5
for(int i = n - 2; i >= 1; i--)  // 从倒数第2根 bar 往回找
{
    bool curr_above = sma_f[i] > sma_s[i];
    bool prev_above = sma_f[i+1] > sma_s[i+1];
```

Python 端可能使用略有不同的搜索范围。由于输入数据本身会因 P0-A 修复而改变，此差异会在修复 P0-A 后自动对齐大部分。

---

### 🟢 P2-C: M30Cross() 独立函数（仅在调试/H2 场景使用）

L418-419 使用 `GetMALastN(g_ma_fast_m30, 3, fast_buf)` — 这个函数在当前主流程中未被直接调用（OnTick 自己做 cross 检测），优先级最低。

---

## 三、推荐修复顺序与预期效果

```
┌─────────────────────────────────────────────────────────────┐
│                    修复路线图                                 │
├───────────┬──────────────────┬──────────┬───────────────────┤
│  步骤     │ 修复项            │ 预计缩减 │ 累计预期差距       │
│           │                  │ 信号差距 │                   │
├───────────┼──────────────────┼──────────┼───────────────────┤
│ Step 1    │ P0-A: OnTick主流程 │ 2-4 个  │ 6-11 → 4-9       │
│           │ SMMA→PythonSMMA   │          │                   │
├───────────┼──────────────────┼──────────┼───────────────────┤
│ Step 2    │ P0-B: Layer3方法  │ 3-5 个  │ 4-9 → 2-6        │
│           │ 对齐(先改Python端) │          │                   │
├───────────┼──────────────────┼──────────┼───────────────────┤
│ Step 3    │ P1-A: M15仅slot1 │ 1-3 个  │ 2-6 → 1-5        │
│           │ +require_earlier │          │                   │
├───────────┼──────────────────┼──────────┼───────────────────┤
│ Step 4    │ P1-B: Rescue扩展  │ 1-2 个  │ 1-5 → 0-4        │
├───────────┼──────────────────┼──────────┼───────────────────┤
│ Step 5    │ P1-C/P2: SL/Stage3│ 0-2 个  │ 0-4 → 0-2        │
│           │ SMMA 对齐         │          │ (工程误差范围)    │
└───────────┴──────────────────┴──────────┴───────────────────┘
```

---

## 四、每个修复的具体代码位置索引

### Step 1: P0-A 修改清单

| # | 文件位置 | 当前代码 | 修改为 |
|---|---------|---------|--------|
| 1A | L1781 | `int n_sma = GetM30SMAArrays(fast_ma, slow_ma, n_rates);` | 新函数 `GetM30SMAArrays_Python()` |
| 1B | L1788-1797 | fast_ma/slow_ma 数组索引取 SMA 值 | 不变（数组内容变了） |
| 1C | L1947 | `GetMALastN(g_ma_fast_m30, 2, stage3_fast)` | PythonSMMA × 2 (shift 0,1) |
| 1D | L2061 | `GetMALastN(g_ma_slow_m30, 1, sma13_buf)` | `PythonSMMA(InpSymbol,InpM30Period,13,1)` |
| 1E | L894 | `GetMALastN(g_ma_slow_m30, 1, sma13_now)` | PythonSMMA |
| 1F | L1012-1013 | `GetMABars(g_ma_fast_m30, n, fast)` | PythonSMMA 循环 |
| 1G | L418-419 | M30Cross 内的 GetMALastN | PythonSMMA (低优先) |

### Step 2: P0-B 修改清单

| # | 文件 | 修改 |
|---|------|------|
| 2A | `export_with_mt5_data.py` L91 | `cb.apply_layer3(...)` → `cb.apply_layer3_ea_executable(final_acc, h2, top_pct=TOP_PCT, lookback=500)` |
| 2B | (可选) EA `IsBias5TopPct()` | 如果选选项 A 则重构为静态量化 |

### Step 3: P1-A 修改清单

| # | EA 行号 | 当前 | 修改 |
|---|--------|------|------|
| 3A | L1607 | `if(slot_in_m30 < 1 \|\| slot_in_m30 > 2)` | `if(slot_in_m30 != 1)` |
| 3B | L1610 后 | 无 | 插入 `require_earlier` 时间检查 |

### Step 4: P1-B 修改清单

| # | EA 行号 | 当前 | 修改 |
|---|--------|------|------|
| 4A | L2079 | `if(m30_sd > InpStopHi && ...)` | 扩展条件或移到 SPEC_FAIL 之后 |

### Step 5: P1-C/P2 修改清单

见上述 P1-C、P2-A 各节。

---

## 五、验证方法

每步修复后执行:
1. MetaEditor F7 编译 → 0 错误
2. MT5 Tester Stop + Start 重跑
3. 读取日志确认: 信号总数 / post_n 分布 / Mode 分布
4. 与 Python `ea_executable_diag=True` + rolling Layer3 输出逐信号对比

---

## 六、风险提示

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| PythonSMMA 批量调用增加回测时间 | 可能从 ~1h 增加到 ~2h | 内部缓存已优化；可接受 |
| 静态 Layer3 在实时 EA 中不可用 | 仅回测对齐有效 | 实盘时保留滚动窗口（更安全）|
| M15 slot2 移除可能减少 EA 独有信号 | 部分 EA-only 信号消失 | 这些信号本就不在 Python 基线中 |
| Rescue 扩展可能引入坏信号 | 止损过小的信号被救回 | 保持 spec [5,35] 硬约束不变 |
