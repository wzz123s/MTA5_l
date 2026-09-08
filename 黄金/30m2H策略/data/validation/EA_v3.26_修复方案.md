# EA v3.26 修复方案 — 精确可执行版

> **基于**: 独立审核 + 逐行代码对比（2026-07-10 22:29）
> **基准**: EA v3.25 (UpdatePostNState 已改 PythonSMMA) vs Python 101 信号
> **目标**: EA 信号数从 ~37 → 接近 90-95，残差 < 10 个进入工程误差范围
> **前置确认**: 工作区 = `F:\use_code\MTA5_l\`, DAD3 Terminal mq5 == MTA5_l ✅

---

## 零、关键事实基线（修复前必须理解）

### 0.1 Python 101 信号的真实口径

| 维度 | 值 | 来源 |
|------|-----|------|
| M30 SMA 数据源 | **Python calc_smma()** | export_with_mt5_data.py L75 |
| Layer3 方法 | **静态全局分位数** `apply_layer3()` | L91（注意：**不是** `apply_layer3_ea_executable`！）|
| M15 replace | `choose_slot1_by_distance` + require_earlier=True | _current_baseline.py L67-73 |
| M15 rescue 输入集 | **所有 spec_fail**（不只是 too_wide）| _current_baseline.py L75-78 |
| M15 rescue chooser | `choose_slot1_by_distance` | _current_baseline.py L82 |
| post_n SL | `sma13[i]` 同 bar 的 Python calc_smma(13) | collect_post_candidates L211 |

### 0.2 EA 当前状态（v3.25）

| 路径 | 数据源 | 影响 |
|------|--------|------|
| UpdatePostNState | ✅ PythonSMMA | 已修 |
| CalcBias55/5/IsBias5TopPct | ✅ PythonSMMA | 已修 |
| OnTick cross 检测 | ❌ CopyBuffer(MODE_SMMA) via GetM30SMAArrays | **待修** |
| FindStopSMA 输入 | ❌ 继承上面的 MODE_SMMA 数组 | **待修** |
| post_n SL (L2061) | ❌ CopyBuffer(MODE_SMMA) g_ma_slow_m30 | **待修** |
| Stage3 exit (L1947) | ❌ CopyBuffer(MODE_SMMA) | 低优先 |
| TrailStage2 SL (L894) | ❌ CopyBuffer(MODE_SMMA) | 低优先 |
| ShouldExit (L1012) | ❌ CopyBuffer(MODE_SMMA) | 低优先 |
| M30MergedDirectionLastCompleted | ❌ CopyBuffer(MODE_SMMA) | 影响方向判断 |
| TryM15EarlyEntry slot2 | ⚠️ 代码允许但时序 bug 导致不可达 | **待修** |
| rescue 条件 | ⚠️ 只救 too_wide，Python 救所有 spec_fail | 待诊断 |
| signal_src 命名 | ⚠️ 全部硬编码 `_slot1` | **待修** |
| Layer3 过滤 | ⚠️ EA 用 rolling 500-bar, Python 用静态 | **已确认差异** |

---

## 一、修复清单总览

| ID | 优先级 | 模块 | 修改内容 | 预计信号影响 | 风险 |
|----|--------|------|---------|-------------|------|
| F1 | **P0** | M30 SMMA 批量源 | 新增 `GetM30SMAArrays_Python()` 替换主路径 | +2~6 | 中（需验证性能） |
| F2 | **P0** | slot2 时序 | 允许 slot2 在新 M30 处理上一根 anchor | +0~3 | 低 |
| F3 | **P0** | post_n SL | 改为 `PythonSMMA(M30,13,1)` | +0~1 | 极低 |
| F4 | **P1** | signal_src 命名 | 区分 slot1/slot2/rescue | 0（诊断用）| 无 |
| F5 | **P1** | rescue 扩展 | 先做 Python 分支回测：too_wide only vs all spec_fail | 待定 | 需数据 |
| F6 | **P2** | Stage3/Trail SMMA | 逐步替换为 PythonSMMA | +0~1 | 低 |

---

## 二、逐项精确修复方案

---

### F1 [P0] M30 主流程 SMMA 批量源对齐

#### 问题

OnTick 主流程中 `GetM30SMAArrays(fast_ma, slow_ma, n_sma)` (L1781) 使用 `CopyBuffer(MODE_SMMA)` 获取 M30 SMA5/13 数组。这些数组被用于：

1. **cross 检测** (L1802-1806): `ma5_prev > ma13_prev` 判断金叉/死叉
2. **pre_cross 传入参数** (L1626-1627): DetectPreCross 的 ma5_curr/ma13_curr 等
3. **FindStopSMA 输入** (L1676, L2047): 止损极值搜索
4. **M15 early-entry 传入** (L1974): TryM15EarlyEntry 的 fast_ma/slow_ma/n_sma

MT5 MODE_SMMA 与 Python calc_smma() 初始化不同 → cross 点可能偏移 ±1~2 bars。

#### 修复：新增 `GetM30SMAArrays_Python()` 函数

**位置**: 在 `GetM30SMAArrays()` (L437) 之后插入

```mql5
//+------------------------------------------------------------------+
//| Get M30 SMA values using PythonSMMA (matches Python calc_smma())   |
//| Output: arrays oldest->newest (same as GetMABars convention)       |
//| shift=0 = forming bar, shift=1 = last completed, ...             |
//+------------------------------------------------------------------+
int GetM30SMAArrays_Python(double &fast[], double &slow[], int max_bars)
{
   // Performance guard: only recalculate when new M30 bar forms
   static int _last_total_bars = -1;
   static double _cached_fast[], _cached_slow[];
   static int _cached_count = 0;

   int total_bars = Bars(InpSymbol, InpM30Period);
   if(total_bars <= InpSlowMA + 1) return 0;

   // Cache invalidation: only recompute on new bar
   if(total_bars != _last_total_bars || ArraySize(_cached_fast) < max_bars)
   {
      _last_total_bars = total_bars;
      int need = MathMin(total_bars - InpSlowMA, max_bars);  // skip warmup bars
      if(need <= 0) return 0;

      ArrayResize(_cached_fast, need);
      ArrayResize(_cached_slow, need);
      _cached_count = 0;

      // Build array: index 0 = oldest valid, index need-1 = newest (= forming bar at shift 0)
      for(int i = 0; i < need; i++)
      {
         // i=0 → oldest (shift = total_bars - 1 - InpSlowMa - (need-1-i))
         // i=need-1 → newest forming (shift = 0)
         int shift = (need - 1 - i);
         double f = PythonSMMA(InpSymbol, InpM30Period, InpFastMA, shift);
         double s = PythonSMMA(InpSymbol, InpM30Period, InpSlowMA, shift);
         if(f == 0 || s == 0) continue;  // should not happen after warmup
         _cached_fast[_cached_count] = f;
         _cached_slow[_cached_count] = s;
         _cached_count++;
      }
   }

   // Copy cached data to output (limit to requested count)
   int out_count = MathMin(_cached_count, max_bars);
   ArrayResize(fast, out_count);
   ArrayResize(slow, out_count);
   ArrayCopy(fast, _cached_fast, 0, 0, out_count);
   ArrayCopy(slow, _cached_slow, 0, 0, out_count);
   return out_count;
}
```

**关键设计决策说明**:

| 决策 | 理由 |
|------|------|
| 按 bar 缓存（ Bars() 变化才重算）| 避免 per-tick 重算 N 个 PythonSMMA |
| 输出格式与 GetMABars 一致（oldest→newest）| 最小化调用方改动 |
| 包含 forming bar (shift=0) | 保持 `fast_ma[n_sma-1] = current` 语义不变 |
| 跳过 warmup bars | 前 InpSlowMA 根 SMMA 未稳定，不需要 |
| 静态变量缓存 | 跨 tick 保持，只在 new_m30_bar 时失效 |

#### 调用点修改

**修改 1 — OnTick 主流程 (L1781)**:

```mql5
// 旧:
int n_sma = GetM30SMAArrays(fast_ma, slow_ma, n_rates);

// 新:
int n_sma = GetM30SMAArrays_Python(fast_ma, slow_ma, n_rates);
```

此一处修改自动覆盖以下所有子路径（因为它们都使用 fast_ma/slow_ma）:
- ✅ cross 检测 (L1802-1806)
- ✅ pre_cross 参数 (L1626-1627)
- ✅ FindStopSMA (L1676, L2047)
- ✅ M15 early-entry (L1974)

**修改 2 — M30Cross() (L418-419)**:

```mql5
// 旧:
if(!GetMALastN(g_ma_fast_m30, BARS, fast_buf)) return 0;
if(!GetMALastN(g_ma_slow_m30, BARS, slow_buf)) return 0;

// 新: 直接用 PythonSMMA 单值调用（只有 3 个值）
fast_buf[0] = PythonSMMA(InpSymbol, InpM30Period, InpFastMA, 0);  // forming
fast_buf[1] = PythonSMMA(InpSymbol, InpM30Period, InpFastMA, 1);  // last comp
fast_buf[2] = PythonSMMA(InpSymbol, InpM30Period, InpFastMA, 2);  // prev comp
slow_buf[0] = PythonSMMA(InpSymbol, InpM30Period, InpSlowMA, 0);
slow_buf[1] = PythonSMMA(InpSymbol, InpM30Period, InpSlowMA, 1);
slow_buf[2] = PythonSMMA(InpSymbol, InpM30Period, InpSlowMA, 2);
if(fast_buf[1]==0 || slow_buf[1]==0 || fast_buf[2]==0 || slow_buf[2]==0) return 0;
```

注意: GetMALastN 返回 `[0]=newest, [1]=last_comp, [2]=prev_comp`，所以上面映射正确。

**修改 3 — ShouldExit (L1012-1013)**:

```mql5
// 旧:
if(!GetMABars(g_ma_fast_m30, n, fast)) return false;
if(!GetMABars(g_ma_slow_m30, n, slow)) return false;

// 新: 改为循环 PythonSMMA（n 通常 = 4，开销极小）
ArrayResize(fast, n); ArrayResize(slow, n);
for(int i = 0; i < n; i++)
{
   fast[i] = PythonSMMA(InpSymbol, InpM30Period, InpFastMA, n - 1 - i);
   slow[i] = PythonSMMA(InpSymbol, InpM30Period, InpSlowMA, n - 1 - i);
}
// GetMABars 返回 oldest→newest, 所以 i=0→shift=n-1(最老), i=n-1→shift=0(最新)
```

**不修改的路径（低优先级，F6 处理）**:
- TrailStage2SL (L894): 只在 trail-on 时调用，SMMA 小偏差只影响 ratchet 精度
- Stage3 exit (L1947): cross 方向通常不受 SMMA 微小偏移影响
- M30MergedDirectionLastCompleted (L687-688): 500 根 bar 的方向统计，个别 bar 的 SMA 差异不影响整体

#### 性能评估

| 场景 | PythonSMMA 调用次数/bar | 开销 |
|------|------------------------|------|
| 正常（无新 bar）| 0（缓存命中）| ~0ms |
| 新 M30 bar 形成 | ~2×max_bars 次（计算+缓存填充）| ~50-100ms（一次性） |
| 对比 v3.24 的 per-tick 4 次 | **大幅减少** | — |

**回测时间预估**: 从当前 ~1h 增加到 ~1h10min（仅在 new M30 bar 时有额外计算）。

---

### F2 [P0] M15 slot2 时序修复

#### 问题

TryM15EarlyEntry (L1608):
```mql5
if(slot_m30_open != cur_bar) return false;
```

当 slot2 的 M15 bar 关闭时，OnTick 已经把 `cur_bar` 更新为新 M30 bar 了，导致 `slot_m30_open(旧) != cur_bar(新)` 永远为 true → slot2 永远被拒绝。

#### 修复

**修改 TryM15EarlyEntry (L1596-1611)**:

```mql5
bool TryM15EarlyEntry(MqlRates &rates[], int n_rates,
                      double &fast_ma[], double &slow_ma[], int n_sma,
                      double ma5_curr, double ma13_curr,
                      double ma5_prev, double ma13_prev,
                      datetime cur_bar)        // ← 参数含义改为 "当前检测到的 M30 bar"
{
   if(!InpUseM15EarlyEntry) return false;
   if(OurStageCount() >= InpMaxPos)
   {
      DiagLog("[M15 SLOT1/SLOT2]", "Candidate",
              "result=SKIP_MAX_POS stages=" + IntegerToString(OurStageCount()) +
              " max_pos=" + IntegerToString(InpMaxPos));
      return false;
   }

   datetime completed_m15_open = iTime(InpSymbol, InpM15Period, 1);
   if(completed_m15_open <= 0) return false;

   int m30_shift = iBarShift(InpSymbol, InpM30Period, completed_m15_open, false);
   if(m30_shift < 0) return false;

   datetime slot_m30_open = iTime(InpSymbol, InpM30Period, m30_shift);
   if(slot_m30_open <= 0) return false;

   int slot_in_m30 = (int)((completed_m15_open - slot_m30_open) / PeriodSeconds(InpM15Period)) + 1;
   // v3.26: Accept both slot1 and slot2
   if(slot_in_m30 < 1 || slot_in_m30 > 2) return false;

   // v3.26 FIX: For slot2, allow processing when we're in the NEXT M30 bar
   // but the slot still belongs to the previous M30 anchor window.
   // slot1: completed_m15_open is within cur_bar → normal check
   // slot2: completed_m15_open may be in PREVIOUS bar when new bar just formed
   bool is_slot2 = (slot_in_m30 == 2);
   if(is_slot2)
   {
      // Slot2 closes exactly when its parent M30 bar closes.
      // If cur_bar has advanced, slot_m30_open is the PREVIOUS M30 bar.
      // We still accept it because the signal belongs to that anchor.
      datetime prev_bar = iTime(InpSymbol, InpM30Period, 1);  // last completed M30
      if(slot_m30_open != prev_bar && slot_m30_open != cur_bar)
         return false;
   }
   else
   {
      // Slot1: must be within current M30 bar (unchanged logic)
      if(slot_m30_open != cur_bar) return false;
   }

   // ... rest of function unchanged until signal_src naming (see F4) ...
```

#### 时序验证表

| 时刻 | 事件 | cur_bar | slot_m30_open | slot_in_m30 | v3.25 结果 | v3.26 结果 |
|------|------|---------|---------------|-------------|-----------|-----------|
| T+00 | M30 bar X 开始 | T+00 | T+00 | 1 | ✅ pass | ✅ pass |
| T+15 | M15 slot1 关闭 | T+00 | T+00 | 1 | ✅ pass | ✅ pass |
| T+30 | M30 bar X+1 开始, M15 slot2 同时关闭 | T+30 | T+00 | 2 | ❌ reject (T≠T+30) | ✅ pass (T==prev_bar) |
| T+45 | M15 slot1 (新bar) 关闭 | T+30 | T+30 | 1 | ✅ pass | ✅ pass |

---

### F3 [P0] post_n SL 对齐

#### 问题

L2059-2064:
```mql5
double sma13_buf[];
if(GetMALastN(g_ma_slow_m30, 1, sma13_buf) && ArraySize(sma13_buf) > 0)
    stop_price = NormalizeDouble(sma13_buf[0], 5);  // ← MT5 MODE_SMMA
```

Python `collect_post_candidates` L211: `stop = sma13[i]` — 使用 Python calc_smma(13)

#### 修复

```mql5
// 旧:
if(GetMALastN(g_ma_slow_m30, 1, sma13_buf) && ArraySize(sma13_buf) > 0)
{
    stop_price = NormalizeDouble(sma13_buf[0], 5);
}

// 新:
double sma13_for_sl = PythonSMMA(InpSymbol, InpM30Period, 13, 1);
if(sma13_for_sl > 0)
{
    stop_price = NormalizeDouble(sma13_for_sl, 5);
}
```

**风险**: 极低。单次 PythonSMMA 调用（缓存命中的情况下 ≈ 0ms）。只影响 post_n 模式的 SL 价格精度。

---

### F4 [P1] signal_src 命名修正

#### 问题

L1639, 1644, 1649, 1654 全部硬编码 `_slot1`：
```mql5
signal_src = "pre_cross_m15_slot1";   // 即使是 slot2 也写 slot1
signal_src = "cross_m15_slot1";
signal_src = "post_n..._m15_slot1";
```

#### 修复

在 F2 的 slot2 判断之后，根据 `is_slot2` 变量设置命名：

```mql5
string slot_tag = is_slot2 ? "_slot2" : "_slot1";

if(is_pre_cross_mode)
{
   signal_dir = pre_cross;
   signal_src = "pre_cross_m15" + slot_tag;
}
else if(is_cross_mode)
{
   signal_dir = curr_above ? +1 : -1;
   signal_src = "cross_m15" + slot_tag;
}
else if(is_post_n_mode)
{
   signal_dir = +1;
   signal_src = "post_n" + IntegerToString(g_post_n_counter) + "_m15" + slot_tag;
}
else if(is_post_n_mode_neg)
{
   signal_dir = -1;
   signal_src = "post_n" + IntegerToString(-g_post_n_counter) + "_m15" + slot_tag;
}

// DiagLog tag also updated:
DiagLog("[M15 " + (is_slot2 ? "SLOT2" : "SLOT1") + "]", "Candidate", ...);
```

rescue 路径 (L2104) 已经用 `signal_src + "_rescue"` 追加标签，会自动继承正确的 slot 标签。

---

### F5 [P1] Rescue 条件扩展（先 Python 诊断）

#### 背景

当前状态:

| 维度 | EA | Python ea_executable_diag |
|------|-----|--------------------------|
| rescue 触发条件 | `m30_sd > InpStopHi` (仅 too_wide) | 所有 `spec_fail` (含 too_tight) |
| rescue 尝试次数 | 1 次 (shift=1 硬编码) | choose_slot1_by_distance 扫窗口 |
| same_side 检查 | ✅ 有 | ✅ 有 |
| entry>stop guard | 无 | 无（choose_slot1_by_distance 不检查）|

#### 建议：先不改 EA，跑 Python 分支回测

在 `inspect_accepted_missing_samples.py` 基础上新增一个分支对比实验：

```
分支 A: too_wide only (EA 当前行为)     → baseline
分支 B: all spec_fail (Python 行为)     → 看多救几个
分支 C: all spec_fail + choose_any      → Python mainline
```

如果分支 B/C 的新增 rescued trades 通过率 < 40% 或 PF < 1.0，则不扩展 EA 的 rescue 条件。
如果通过率 > 50% 且 PF >= 1.2，则将 EA 的 rescue 条件从 `m30_sd > InpStopHi` 改为包含 `m30_sd < InpStopLo`。

**预期结果**: most too_tight trades 被 Layer3 否决是有道理的（入场距离止损太近），扩展收益可能有限。

---

### F6 [P2] Stage3 / TrailStage SMMA 对齐（可选）

#### Stage3 Exit (L1947)

```mql5
// 旧:
if(GetMALastN(g_ma_fast_m30, 2, stage3_fast) && GetMALastN(g_ma_slow_m30, 2, stage3_slow))

// 新:
stage3_fast[0] = PythonSMMA(InpSymbol, InpM30Period, InpFastMA, 0);
stage3_fast[1] = PythonSMMA(InpSymbol, InpM30Period, InpFastMA, 1);
stage3_slow[0] = PythonSMMA(InpSymbol, InpM30Period, InpSlowMA, 0);
stage3_slow[1] = PythonSMMA(InpSymbol, InpM30Period, InpSlowMA, 1);
if(stage3_fast[0] > 0 && stage3_slow[0] > 0)
```

#### TrailStage2 SL (L894)

```mql5
// 旧:
if(GetMALastN(g_ma_slow_m30, 1, sma13_now) && ArraySize(sma13_now) > 0)
    TrailStage2SL(ticket, ..., sma13_now[0], ptype);

// 新:
double trail_sma13 = PythonSMMA(InpSymbol, InpM30Period, InpSlowMA, 1);
if(trail_sma13 > 0)
    TrailStage2SL(ticket, ..., trail_sma13, ptype);
```

**建议**: F1-F4 完成并验证后再决定是否执行 F6。这两个修改只影响退出时机精度，不影响信号数量。

---

## 三、不修改项（及理由）

| 项目 | 理由 |
|------|------|
| **Layer3 方法（static vs rolling）** | Python 101 信号用的是 **静态** Layer3（export_with_mt5_data.py L91），而 EA 用 rolling。但这是架构级差异，修改 EA 的 Layer3 为静态需要重构整个 PassLayer3Gate。而且 rolling 在理论上更合理（自适应阈值）。**暂不修改**，作为已知残差接受。 |
| **M30MergedDirectionLastCompleted SMMA** | 500 根 bar 的方向统计，个别 SMMA 差异不影响整体 merged direction。且 UpdateMergedPostNState 是独立的 post_n 计算路径，和主流程 post_n 不冲突。 |
| **H2 SMA 数据源** | H2 Bias_55/Bias_5 已经使用 PythonSMMA（通过 CalcBias55/CalcBias5）。H2 CSV 输出的 SMA 值只用于日志记录，不影响交易逻辑。 |
| **rescue chooser 升级到 choose_any** | Python ea_executable_diag 本身也只用 choose_slot1_by_distance。升级到 choose_any 是 mainline 对齐问题，不是 EA bug。 |

---

## 四、执行顺序和验收标准

### Step 1: 备份 + 应用 F1 (M30 SMMA 批量源)
```
操作: 备份 v3.25 → 新增 GetM30SMAArrays_Python() → 修改 L1781 调用点
编译: F7
部署: 复制 mq5 到 DAD3 Terminal → 编译 ex5
回测: Stop/Start
验收: post_n 恢复到 ~50-55? 总信号变化?
```

### Step 2: 应用 F2 (slot2 时序) + F4 (命名)
```
操作: 修改 TryM15EarlyEntry 的 slot2 判断逻辑
编译: F7
回测: Stop/Start
验收: 日志中出现 _slot2 信号? M15 early-entry 总数增加?
```

### Step 3: 应用 F3 (post_n SL)
```
操作: 替换 L2061 的 CopyBuffer 为 PythonSMMA
编译: F7
回测: Stop/Start
验收: post_n 模式信号的 SL 价格微调
```

### Step 4: 回测 + 逐笔 diff
```
操作: 导出 EA CSV → compare_mt5_log_sessions.py 对比
验收: 
  - 总信号数差距 < 10 (EA vs Python 101)
  - post_n 信号数接近
  - M15 early-entry 信号含 slot1 + slot2
  - rescue 成功率 > 0
```

### Step 5: 可选 F6 (Stage3/Trail)
```
前提: F1-F4 验收后仍有 > 5 个未解释的差异
操作: 替换 Stage3 和 TrailStage2 的 SMMA 源
```

### Step 6: 更新项目记录
```
文件: progress.md, task_plan.md, findings.md
内容: v3.26 变更记录、剩余残差分析
```

---

## 五、风险和缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| F1 缓存逻辑 bug 导致数组越界 | 低 | 编译错误/崩溃 | 先在 Strategy Tester 可视模式跑 1-2 天验证 |
| F1 回测时间增加 > 20% | 中 | 工作流变慢 | 缓存设计保证只在 new M30 bar 计算；如超 1.5h 则降级 |
| F2 slot2 引入重复信号（同 anchor 双入） | 低 | 资金管理异常 | ExecuteSignalByMarket 有 `g_signal_anchor_time` 去重 |
| PythonSMMA 与 MT5 SMMA 在早期 bar 差异大 | 中 | warmup 期间信号偏差 | 已跳过前 InpSlowMA 根 warmup bar |

---

## 六、版本号规则

| 版本 | 内容 | 基线 |
|------|------|------|
| v3.25 | UpdatePostNState 改 PythonSMMA + P0/P1 fixes | 当前 |
| v3.26 | F1+F2+F3+F4 (本方案全部 P0/P1) | **目标版本** |
| v3.27 (预留) | F5 (rescue扩展) + F6 (Stage3/Trail) + Layer3 方法选择 | 待定 |
