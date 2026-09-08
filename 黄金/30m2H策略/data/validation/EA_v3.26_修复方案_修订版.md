# EA v3.26 修复方案 — 修订版（基于 P0 审核修正）

> **版本**: 2026-07-10 22:37 修订 | **前置**: EA v3.25 (UpdatePostNState 已改 PythonSMMA)
> **状态**: ✅ 可执行（已修正原版 4 个 P0 缺陷）
> **工作区**: `F:\use_code\MTA5_l\` (DAD3 Terminal mq5 == MTA5_l ✅)

---

## 零、验收口径选择（必须先决定）

### 问题：Python "101 信号" 是混合口径

`export_with_mt5_data.py` 的实际调用路径：

```
build_final_accepted(ea_executable_diag=True)
  ├─ M15 replace → choose_slot1_by_distance + require_earlier=True  [EA诊断口径]
  ├─ M15 rescue → 输入集 = 所有 spec_fail                        [EA诊断口径]
  └─ return final_acc

apply_layer3(final_acc)          ← 静态全局分位数! [主线研究口径]
  └─ NOT apply_layer3_ea_executable()  ← 没用 rolling!
```

**结论**: Python 101 信号的口径 = `ea_executable_diag 的 M15 + 主线的 Layer3`。这是**有意或无意形成的混合口径**。

### 方案 A：对齐"Python 混合 101"

| 维度 | 值 | 说明 |
|------|-----|------|
| M15 replace | slot1-only, require_earlier=True | 与 export 一致 |
| M15 rescue | **先只救 too_wide** (EA 当前行为) | 不改，保持与 export rescue 输入的差异作为已知残差 |
| Layer3 | **EA 保持 rolling 500-bar** | 接受 static vs rolling 差异为已知残差 |
| SMMA 数据源 | 全路统一 PythonSMMA | 本方案核心修复 |
| slot2 | 修时序+父上下文 | 对齐 Python mainline choose_any |

**验收目标**: EA 总信号接近 90-95，与 Python 101 的差距 ≤ 12 个。
**已知残差**: Layer3 方法差异(±3-5)、rescue 覆盖差异(±1-2)。

### 方案 B：对齐"EA 可执行诊断口径"

在 `summarize_strategy(ea_executable_diag=True)` 路径下跑一次 Python，得到纯 EA 口径信号数，以此为准。

需要做的事：
1. 在 `_current_baseline.py` 或新建脚本中调 `summarize_strategy(ea_executable_diag=True)`
2. 确认该路径使用 `apply_layer3_ea_executable` (rolling)
3. 以输出信号数为 EA 验收基准

**推荐**: 先跑一次方案 B 得到基准数字，再以方案 A 作为 v3.26 代码修改目标。两者差值就是 Layer3 方法差异的量化。

### ⚡ 决策要求

在执行任何代码修改前，必须：
1. 运行 `summarize_strategy(ea_executable_diag=True)` 得到**纯 EA 口径信号数**
2. 记录该数字作为 **Baseline-B**
3. 将 Python 101 (混合) 记录为 **Baseline-A**
4. v3.26 回测后同时对比 A 和 B

---

## 一、修复清单总览

| ID | 优先级 | 模块 | 修改内容 | 预计影响 | 风险 |
|----|--------|------|---------|---------|------|
| **F1** | **P0** | M30 SMMA 批量源 | 新增真正的批量 SMMA 函数（不循环调 PythonSMMA）| +2~6 | 中 |
| **F2** | **P0** | slot2 时序+上下文 | 允许 slot2 + **重建父 M30 bar 的完整交易上下文** | +0~3 | 中 |
| **F3** | **P0** | post_n SL | CopyBuffer → PythonSMMA 单次调用 | +0~1 | 极低 |
| **F4** | **P1** | signal_src 命名 | 区分 _slot1 / _slot2 / _rescue，局部变量 tag | 0 | 无 |
| **F5** | **P1** | rescue 扩展 | **不改 EA**，先做 Python 分支回测 | 待定 | 需数据 |
| **F6** | **P2** | Stage3/Trail/Merged SMMA | F1-F4 验收后仍有 >5 残差时才做 | +0~2 | 低 |

---

## 二、逐项精确修复方案

---

### F1 [P0] M30 主流程 SMMA 批量源对齐（修订版）

#### 1.1 问题

OnTick 主流程中 `GetM30SMAArrays(fast_ma, slow_ma, n_rates)` (L1781) 使用 `CopyBuffer(MODE_SMMA)` 获取 M30 SMA5/13 数组。这些数组被 cross 检测/FindStopSMA/pre_cross/M15 early-entry 共享使用。

MT5 MODE_SMMA 初始化 = 第一根 bar 价格；Python calc_smma() 初始化 = 前 N 根均值 → 下游全部偏移。

#### 1.2 修订版设计：真正的批量函数

**核心原则**: 一次性 `CopyClose`，内部分别计算 period=5 和 period=13 两套完整数组，不循环调用现有 `PythonSMMA()`。

```mql5
//+------------------------------------------------------------------+
//| Batch compute Python-style SMMA for M30 period=5 and period=13    |
//| Output: fast[] = SMA5[], slow[] = SMA13[]                         |
//| Convention: oldest→newest, index[n-1] = forming bar (shift=0)     |
//| Cache: recomputed only when total_bars changes (new M30 bar)      |
//+------------------------------------------------------------------+
int GetM30SMAArrays_Python(double &fast_out[], double &slow_out[], int max_bars)
{
   // === Static cache (per new M30 bar) ===
   static int    _last_total_bars = -1;
   static double _cached_fast[];
   static double _cached_slow[];
   static int    _cached_total = 0;   // actual number of valid entries in cache
   static int    _cached_capacity = 0;

   int total_bars = Bars(InpSymbol, InpM30Period);
   if(total_bars <= InpSlowMA + 1) return 0;

   // === Cache invalidation: only on new M30 bar ===
   bool need_recompute = (total_bars != _last_total_bars)
                      || (_cached_capacity < max_bars);

   if(need_recompute)
   {
      _last_total_bars = total_bars;
      int available = total_bars - InpSlowMA;   // skip warmup bars where SMMA not stable
      if(available <= 0) return 0;

      int need = MathMin(available, max_bars);
      if(need <= 0) return 0;

      // Grow cache if needed
      if(_cached_capacity < need)
      {
         ArrayResize(_cached_fast, need);
         ArrayResize(_cached_slow, need);
         _cached_capacity = need;
      }
      _cached_total = need;

      // === Single CopyClose for both periods ===
      // Read ALL close prices from oldest warmup bar to current
      double closes[];
      ArraySetAsSeries(closes, true);
      int n_close = CopyClose(InpSymbol, InpM30Period, 0, total_bars, closes);
      if(n_close < InpSlowMA + 1) { _cached_total = 0; return 0; }

      // closes[0] = newest (forming), closes[n_close-1] = oldest
      // We'll fill cache from oldest→newest:
      // cache[0] corresponds to shift = need - 1 (oldest valid entry)
      // cache[need-1] corresponds to shift = 0 (newest / forming)

      // --- Compute SMA5 array ---
      // Init: average of first 5 prices (matching Python calc_smma)
      double sum5 = 0;
      for(int j = 0; j < InpFastMA && j < n_close; j++)
         sum5 += closes[n_close - 1 - j];   // from oldest
      _cached_fast[InpFastMA - 1] = sum5 / InpFastMA;

      // Recurrence: (close + 4*prev) / 5
      for(int j = InpFastMA; j < need + InpFastMA - 1; j++)
      {
         int ci = n_close - 1 - j;           // close price index (from newest)
         int oi = j - InpFastMA + 1;         // output cache index
         if(oi >= need) break;
         if(ci >= 0 && oi > 0)
            _cached_fast[oi] = (closes[ci] + (InpFastMA - 1) * _cached_fast[oi - 1]) / InpFastMA;
      }

      // --- Compute SMA13 array ---
      double sum13 = 0;
      for(int j = 0; j < InpSlowMA && j < n_close; j++)
         sum13 += closes[n_close - 1 - j];
      _cached_slow[InpSlowMA - 1] = sum13 / InpSlowMA;

      for(int j = InpSlowMA; j < need + InpSlowMA - 1; j++)
      {
         int ci = n_close - 1 - j;
         int oi = j - InpSlowMA + 1;
         if(oi >= need) break;
         if(ci >= 0 && oi > 0)
            _cached_slow[oi] = (closes[ci] + (InpSlowMA - 1) * _cached_slow[oi - 1]) / InpSlowMA;
      }
   }

   // === Copy to output: take the NEWEST 'max_bars' entries ===
   // CRITICAL FIX (v3.26 rev): copy from tail of cache, not head!
   // _cached_fast[0] = oldest, _cached[_cached_total-1] = newest (forming)
   // Caller needs newest entries, so we copy from the end.
   int out_count = MathMin(_cached_total, max_bars);
   if(out_count <= 0) return 0;

   int copy_start = _cached_total - out_count;  // starting index in cache
   if(copy_start < 0) copy_start = 0;

   ArrayResize(fast_out, out_count);
   ArrayResize(slow_out, out_count);
   ArrayCopy(fast_out, _cached_fast, 0, copy_start, out_count);
   ArrayCopy(slow_out, _cached_slow, 0, copy_start, out_count);

   return out_count;
}
```

#### 1.3 设计决策对比表（vs 原版 F1）

| 维度 | 原版 F1（有缺陷）| 修订版 F1 |
|------|-----------------|----------|
| 计算方式 | 循环调 `PythonSMMA(period=5/13)` | 内联批量递推，**单次 CopyClose** |
| 缓存失效 | period 变化导致每次循环都全量重算 | **只在 Bars() 变化时重算一次** |
| per-new-bar 开销 | ~2×need 次 full recalc ≈ 10-15s | **1次 CopyClose + 2×need 递推 ≈ 50ms** |
| ArrayCopy 起点 | `copy_start=0`（取最老段）❌ | `copy_start=_cached_total-out_count`（取最新段）✅ |
| forming bar 包含? | 是但值可能错 | **保证正确** |

#### 1.4 性能评估（修订版）

| 场景 | 操作 | 开销 |
|------|------|------|
| 正常 tick（无新 bar）| 缓存命中 + ArrayCopy | < 1ms |
| 新 M30 bar 形成 | 1× CopyClose(~6000 bars) + 2× 递推 | ~50-100ms |
| 对比 v3.24 per-tick 4× PythonSMMA | — | **减少 99%+** |

**回测时间预估**: 从当前 ~1h 增加到 ~1h05m（每 30 分钟额外 50ms × 7200 bars/h = 6min/h，但实际 tester 加速远快于实时）。

#### 1.5 调用点修改

**唯一修改点 — OnTick L1781**:

```mql5
// 旧:
int n_sma = GetM30SMAArrays(fast_ma, slow_ma, n_rates);

// 新:
int n_sma = GetM30SMAArrays_Python(fast_ma, slow_ma, n_rates);
```

此一处修改自动覆盖所有子路径：
- ✅ cross 检测 (L1802-1806)
- ✅ pre_cross 参数 (L1627)
- ✅ FindStopSMA (L1676, L2047)
- ✅ M15 early-entry (L1974) — 但注意 F2 会进一步处理 slot2 上下文
- ✅ post_n SL 间接（通过 ma13_curr 参数传递到 TryM15EarlyEntry）

**其他调用点（低频，可后续处理）**：

| 函数 | 行号 | 当前实现 | 修订建议 | 优先级 |
|------|------|---------|---------|--------|
| `M30Cross()` | L418-419 | GetMALastN(MODE_SMMA) | 改为 3× PythonSMMA 单值 | F6 |
| `ShouldExit()` | L1012-1013 | GetMABars(MODE_SMMA) | 改为 n× PythonSMMA 循环(n≈4) | F6 |
| `TrailStage2SL()` | L894 | GetMALastN(MODE_SMMA) | 改为 1× PythonSMMA 单值 | F6 |
| `M30MergedDirectionLastCompleted()` | L687-688 | GetMABars(MODE_SMMA) | **建议纳入 F1 或 F6** — 服务 merged post_n 路径 | F6 |
| `Stage3 exit` | L1947 | GetMALastN(MODE_SMMA) | 改为 2× PythonSMMA | F6 |

---

### F2 [P0] slot2 时序 + 父 M30 上下文重建（完全重写）

#### 2.1 问题（双层）

**Layer 1 — 时间门不可达** (已确认):
```
T+30: cur_bar 已更新为新 M30 → slot_m30_open(旧) != cur_bar(新) → reject
```

**Layer 2 — 上下文错配** (更严重):
即使时间门通过，TryM15EarlyEntry 收到的参数全是新 M30 bar 的数据：

| 参数 | 来源 | slot2 应该用的 |
|------|------|---------------|
| rates[] | L1777 GetM30Rates → 新 bar 的 OHLC | **父 M30 bar X 的 OHLC** |
| fast_ma/slow_ma | L1781 GetM30SMAArrays → 新 bar SMA 序列 | **父 M30 bar X 的 SMA** |
| ma5_curr/ma13_curr | L1788-1789 取自 fast_ma[n_sma-1] | **父 M30 bar X 的 curr** |
| ma5_prev/ma13_prev | L1792-1793 取自 fast_ma[n_sma-2] | **父 M30 bar X 的 prev** |
| cur_bar | L1739 iTime(M30,0) = 新 bar 时间 | **slot_m30_open (bar X)** |

#### 2.2 修复策略

将 `TryM15EarlyEntry` 拆分为两个阶段：

**Phase 1 — OnTick 中**：检测 slot1/slot2 是否符合时序条件，确定 `slot_m30_open`（父 anchor）
**Phase 2 — 函数内部**：如果 is_slot2，从 `slot_m30_open` 重建父 M30 的完整交易上下文

#### 2.3 代码修改

##### 修改 A：OnTick 调用点 (L1972-1977)

```mql5
// Real-time M15 early-entry.
if(new_m15_bar)
{
   // v3.26: Pass additional context for slot2 parent-M30 reconstruction
   datetime parent_m30_bar = cur_bar;       // default = current M30
   if(g_last_m30_bar != cur_bar)
   {
      // New M30 just formed: completed_m15 might be slot2 of PREVIOUS bar
      // Check if it belongs to g_last_m30_bar
      datetime completed_m15 = iTime(InpSymbol, InpM15Period, 1);
      int m30_shift_for_slot = iBarShift(InpSymbol, InpM30Period, completed_m15, false);
      if(m30_shift_for_slot >= 0)
      {
         datetime slot_anchor = iTime(InpSymbol, InpM30Period, m30_shift_for_slot);
         if(slot_anchor == g_last_m30_bar)
            parent_m30_bar = slot_anchor;  // this IS a slot2 of previous bar
      }
   }

   if(TryM15EarlyEntry(rates, n_rates,
                       fast_ma, slow_ma, n_sma,
                       ma5_curr, ma13_curr, ma5_prev, ma13_prev,
                       cur_bar, parent_m30_bar))  // ← 新增 parent_m30_bar 参数
      return;
}
```

##### 修改 B：TryM15EarlyEntry 签名 + slot2 上下文重建 (L1581-1611 替换)

```mql5
bool TryM15EarlyEntry(MqlRates &rates[], int n_rates,
                      double &fast_ma[], double &slow_ma[], int n_sma,
                      double ma5_curr, double ma13_curr,
                      double ma5_prev, double ma13_prev,
                      datetime cur_bar,              // current detecting M30 bar
                      datetime parent_m30_bar)        // v3.26: parent anchor for slot2
{
   if(!InpUseM15EarlyEntry) return false;
   if(OurStageCount() >= InpMaxPos)
   {
      string log_tag = "[M15 SLOT?]";  // will be resolved after slot detection
      DiagLog(log_tag, "Candidate",
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
   if(slot_in_m30 < 1 || slot_in_m30 > 2) return false;

   // v3.26 FIX: Time gate accepts both slot1 and slot2
   bool is_slot2 = (slot_in_m30 == 2);
   if(is_slot2)
   {
      // Slot2 may be processed when cur_bar has advanced to next M30.
      // Allow if slot belongs to previous completed bar OR current bar.
      datetime prev_completed_m30 = iTime(InpSymbol, InpM30Period, 1);  // last comp
      if(slot_m30_open != prev_completed_m30 && slot_m30_open != cur_bar)
         return false;
   }
   else
   {
      // Slot1 must be within current M30 bar
      if(slot_m30_open != cur_bar) return false;
   }

   // === v3.26: SLOT2 PARENT CONTEXT RECONSTRUCTION ===
   double ctx_ma5_curr, ctx_ma13_curr, ctx_ma5_prev, ctx_ma13_prev;
   double ctx_fast_ma[], ctx_slow_ma[];
   int    ctx_n_sma = 0;
   MqlRates ctx_rates[];
   int    ctx_n_rates = 0;

   if(is_slot2 && slot_m30_open != cur_bar)
   {
      // Slot2 belongs to parent M30 bar — rebuild its trading context
      const int CTX_SMA_WARMUP = InpSlowMA + 5;
      ctx_n_rates = GetM30Rates(ctx_rates, MathMax(CTX_SMA_WARMUP + 10, InpStopLookback));
      if(ctx_n_rates < CTX_SMA_WARMUP) return false;

      // Use same batch function for parent bar's SMA arrays
      ctx_n_sma = GetM30SMAArrays_Python(ctx_fast_ma, ctx_slow_ma, ctx_n_rates);
      if(ctx_n_sma < CTX_SMA_WARMUP) return false;

      ctx_ma5_curr  = ctx_fast_ma[ctx_n_sma - 1];
      ctx_ma13_curr = ctx_slow_ma[ctx_n_sma - 1];
      ctx_ma5_prev  = ctx_fast_ma[ctx_n_sma - 2];
      ctx_ma13_prev = ctx_slow_ma[ctx_n_sma - 2];

      if(ctx_ma5_prev == 0 || ctx_ma13_prev == 0) return false;
   }
   else
   {
      // Slot1 or slot2 within current bar: use passed-in context as-is
      ctx_ma5_curr = ma5_curr;  ctx_ma13_curr = ma13_curr;
      ctx_ma5_prev = ma5_prev;  ctx_ma13_prev = ma13_prev;
      // Shallow-copy references (safe: these are stack arrays from OnTick)
      ctx_n_sma = n_sma;
      // Note: ctx_fast_ma/slow_ma are NOT set here; caller's fast_ma/slow_ma used directly below
   }

   // ... rest of function uses ctx_* variables instead of original params ...
   // (见下面的 C/D/E/F 修改)
```

##### 修改 C：函数体中的变量替换

在上述 slot2 上下文重建之后，将函数体内所有引用原始参数的地方改为 `ctx_*`：

| 原始代码位置 | 原始用法 | 修改后 |
|-------------|---------|--------|
| L1626-1627 DetectPreCross | `ma5_prev, ma5_curr, ma13_curr, ma13_prev` | `ctx_ma5_prev, ctx_ma5_curr, ctx_ma13_curr, ctx_ma13_prev` |
| L1630-1631 curr_above/prev_above | `ma5_curr > ma13_curr`, `ma5_prev > ma13_prev` | `ctx_ma5_curr > ctx_ma13_curr`, `ctx_ma5_prev > ctx_ma13_prev` |
| L1676 FindStopSMA | `FindStopSMA(fast_ma, slow_ma, n_sma, seg_dir)` | slot2 用 `FindStopSMA(ctx_fast_ma, ctx_slow_ma, ctx_n_sma, seg_dir)`；slot1 保持原样 |
| L1689 sma13_now | `ma13_curr` | `ctx_ma13_curr` |
| L1658-1723 signal_src/DiagLog | 硬编码 `"[M15 SLOT1]"` | 见 F4 动态 tag |

##### 关键：FindStopSMA 的条件分支

```mql5
// Inside TryM15EarlyEntry, after stop calculation section:
double stop_sma;
if(is_slot2 && slot_m30_open != cur_bar)
{
   // Use parent bar's SMA sequence for segment search
   stop_sma = FindStopSMA(ctx_fast_ma, ctx_slow_ma, ctx_n_sma, seg_dir);
}
else
{
   // slot1 or slot2-within-current: use OnTick's arrays
   stop_sma = FindStopSMA(fast_ma, slow_ma, n_sma, seg_dir);
}
```

##### 修改 D：anchor_time 计算（不变）

```mql5
datetime anchor_time = slot_m30_open + PeriodSeconds(InpM30Period);
// anchor_time 始终基于 slot_m30_open（父 M30 bar），这是正确的
```

##### 修改 E：PassLayer1Gate / PassLayer3Gate

这两个门控函数内部会读取全局 SMA handle 的数据。对于 slot2，它们检查的是**当前 tick 的 Bias 值**（来自 H2），而不是 M30 SMA 序列。Bias 基于 H2 bar 的 PythonSMMA，不受 M30 bar 边界影响。所以**不需要额外修改**。

但需注意：如果未来 PassLayer3Gate 改为使用传入的 SMA 数组计算 Bias_5（而非 H2 全局数据），则需要同步传入 ctx_fast_ma/ctx_slow_ma。当前实现无此问题。

#### 2.4 时序验证表（完整版）

| 时刻 | 事件 | cur_bar | parent_m30_bar | slot_m30_open | slot | v3.25 | v3.26 |
|------|------|---------|---------------|---------------|------|-------|-------|
| T+00 | M30 bar X 开始 | T+00 | T+00 | T+00 | 1 | pass ✅ | pass ✅ |
| T+15 | M15 slot1 关闭 | T+00 | T+00 | T+00 | 1 | pass ✅ | pass ✅ |
| T+30 | M30 bar X+1 开始, slot2 同时关闭 | T+30 | **T+00** (检测!) | T+00 | 2 | ❌ reject | ✅ pass + 重建 ctx |
| T+45 | M15 slot1 (新bar) 关闭 | T+30 | T+30 | T+30 | 1 | pass ✅ | pass ✅ |

#### 2.5 风险和缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| slot2 重复信号（同 anchor 双入）| 低 | 资金管理异常 | ExecuteSignalByMarket 有 `g_signal_anchor_time` 去重 |
| slot2 上下文重建的 GetM30SMAArrays_Python 第二次调用 | 低 | 性能（多 50ms/次）| 仅 slot2 触发时调用；且缓存可能命中 |
| slot2 的 FindStopSMA 在父 bar 上搜索范围不足 | 低 | stop 极值找不到 | ctx_n_rates 与主路径相同（warmup+stoplookback）|

---

### F3 [P0] post_n SL 对齐

#### 问题和修复

L2059-2064（M30 CLOSE 路径的 post_n SL）:
```mql5
// 旧:
double sma13_buf[];
if(GetMALastN(g_ma_slow_m30, 1, sma13_buf) && ArraySize(sma13_buf) > 0)
    stop_price = NormalizeDouble(sma13_buf[0], 5);  // MT5 MODE_SMMA

// 新:
double sma13_for_sl = PythonSMMA(InpSymbol, InpM30Period, InpSlowMA, 1);
if(sma13_for_sl > 0)
    stop_price = NormalizeDouble(sma13_for_sl, 5);
else
{
    DiagLog("[M30 CLOSE]", "Stop", "mode=" + signal_src + " result=POSTN_STOP_INVALID");
    return;
}
```

**注意**: 这里的 `PythonSMMA` 是单值调用（shift=1 = last completed bar）。由于已有缓存，且 period=13 不变，缓存命中开销 ≈ 0。

同样需要修改 **TryM15EarlyEntry 内部的 post_n SL** (L1689):
```mql5
// 旧:
double sma13_now = ma13_curr;  // 来自 fast_ma/slow_ma 参数
// ...
stop_price = NormalizeDouble(sma13_now, 5);

// 新: 如果是 slot2 且用了 ctx_*，则 ctx_ma13_curr 已经是 PythonSMMA 值
// （通过 GetM30SMAArrays_Python 获取）
// 所以这里无需额外修改 — F1 已经覆盖了!
```

**结论**: F3 对于 M30 CLOSE 路径是独立的修改；对于 M15 路径，F1 的 GetM30SMAArrays_Python 已经覆盖。

---

### F4 [P1] signal_src 命名 + DiagLog tag

#### 修改

在 TryM15EarlyEntry 的 slot2 判断之后（is_slot2 已确定），定义局部变量：

```mql5
string slot_tag = is_slot2 ? "_slot2" : "_slot1";
string log_tag  = is_slot2 ? "[M15 SLOT2]" : "[M15 SLOT1]";
```

替换所有硬编码：

```mql5
// signal_src (原来全部 _slot1):
signal_src = "pre_cross_m15" + slot_tag;          // was: "pre_cross_m15_slot1"
signal_src = "cross_m15" + slot_tag;               // was: "cross_m15_slot1"
signal_src = "post_n" + IntegerToString(g_post_n_counter) + "_m15" + slot_tag;

// DiagLog tags:
DiagLog(log_tag, "Candidate", ...);                 // was: "[M15 SLOT1]"
DiagLog(log_tag, "Stop", ...);                       // was: "[M15 SLOT1]"
DiagLog(log_tag, "Layer1", ...);                     // was: "[M15 SLOT1]"
DiagLog(log_tag, "Layer3", ...);                     // was: "[M15 SLOT1]"
DiagLog(log_tag, "Spec", ...);                       // was: "[M15 SLOT1]"

// ExecuteSignalByMarket:
return ExecuteSignalByMarket(signal_dir, signal_src, stop_price, anchor_time, log_tag);
// was: "... , "[M15 SLOT1]");
```

rescue 路径 (L2104+) 的追加标签自动继承正确的 slot_tag：
```mql5
signal_src = signal_src + "_rescue";  // → "cross_m15_slot2_rescue" etc.
```

---

### F5 [P1] Rescue 条件扩展（先不做 EA 修改）

#### 背景

当前 EA rescue 只触发 `m30_sd > InpStopHi`（too_wide）。Python ea_executable_diag 救所有 spec_fail（含 too_tight）。

#### 建议：Python 分支实验

在 `export_with_mt5_data.py` 或新建脚本中新增对比：

```
Branch A (baseline): ea_executable_diag=True, rescue=too_wide only (当前行为)
Branch B:             ea_executable_diag=True, rescue=all spec_fail
Branch C (mainline):  ea_executable_diag=False, choose_any, rescue=too_wide only
```

**判定标准**:
- Branch B 新增 rescued trades 通过率 < 40% 或 PF < 1.0 → **不扩展 EA**
- Branch B 通过率 > 50% 且 PF ≥ 1.2 → **考虑扩展**

预期：most too_tight trades 被 Layer3 否决是有道理的（入场距止损太近），扩展收益有限。

---

### F6 [P2] 低优先级 SMMA 对齐（F1-F4 后再评估）

仅在以下条件满足时执行：
1. F1-F4 已编译通过并完成回测
2. EA vs Python 残差仍 > 5 个信号
3. 残差分析指向 Stage3 / Trail / Merged 方向判断

修改内容：

```mql5
// TrailStage2SL (L894):
// 旧: GetMALastN(g_ma_slow_m30, 1, sma13_now)
// 新: double trail_sma13 = PythonSMMA(InpSymbol, InpM30Period, InpSlowMA, 1);

// ShouldExit (L1012-1013):
// 旧: GetMABars(g_ma_fast_m30, n, fast) + GetMABars(g_ma_slow_m30, n, slow)
// 新: 循环 n(≈4) 次 PythonSMMA（n 很小，性能无影响）

// M30MergedDirectionLastCompleted (L687-688):
// 旧: GetMABars(g_ma_fast_m30, need, fast)
// 新: 使用 GetM30SMAArrays_Python 批量获取（复用 F1 的函数!）

// Stage3 exit (L1947):
// 旧: GetMALastN(g_ma_fast_m30, 2, stage3_fast)
// 新: 2× PythonSMMA (fast) + 2× PythonSMMA (slow)
```

---

## 三、不修改项（及理由）

| 项目 | 理由 |
|------|------|
| **Layer3 方法 (static vs rolling)** | Python 101 用 static（主线研究口径）；EA 用 rolling（实盘合理）。**作为已知残差接受**。v3.26 不修改 EA 的 Layer3 实现。如果要消除此差异，应在 Python 端改用 `apply_layer3_ea_executable` 重新生成 Baseline-B |
| **rescue chooser 升级到 choose_any** | Python ea_executable_diag 也只用 slot1_by_distance。升级到 mainline 的 choose_any 是另一个维度的对齐 |
| **H2 SMA 数据源** | CalcBias55/Bias5/Bias55EarlyQ 已用 PythonSMMA。H2 CSV 只用于日志，不影响交易逻辑 |
| **M30-close rescue 从 shift=1 改为扫描窗口** | Python choose_any 扫同一 anchor 窗口内的所有 M15。EA 当前只试最近 1 根。这属于 F5 范畴，需先看 Python 分支实验结果 |

---

## 四、执行顺序

### Step 0：建立验收基准（阻塞项！）

```
操作: 运行 summarize_strategy(ea_executable_diag=True) 得到 Baseline-B
      记录 Baseline-A = 101 (Python export_with_mt5_data.py 混合口径)
输出: 文档记录 A/B 两个基准数字
```

### Step 1：备份 + 应用 F1

```
操作: 备份 v3.25 mq5 → 插入 GetM30SMAArrays_Python() → 改 L1781 调用点
验证: 编译通过 + Strategy Tester 可视模式跑 2-3 天确认无 crash
```

### Step 2：应用 F2 + F4

```
操作: 重写 TryM15EarlyEntry 签名 + slot2 上下文重建 + 动态 tag
验证: 编译通过 + 可视模式确认 slot2 信号出现
```

### Step 3：应用 F3

```
操作: 替换 L2061 CopyBuffer 为 PythonSMMA
验证: 编译通过
```

### Step 4：编译部署回测

```
操作: F7 编译 → 复制 mq5 到 DAD3 Terminal Advisors → 编译 ex5
      Stop/Start 回测
验收指标:
  □ post_n 恢复到 50-55?
  □ 总信号数 vs Baseline-A 和 Baseline-B 各差多少?
  □ 日志中出现 _slot2 信号?
  □ M15 early-entry 总数是否增加?
  □ rescue 成功率是否 > 0?
```

### Step 5：逐笔 diff + 残差分析

```
操作: 导出 EA CSV → compare_mt5_log_sessions.py 对比
      逐笔 diff 定位剩余 mismatch
输出: 更新 task_plan.md / progress.md / findings.md
```

### Step 6：可选 F6 + F5

```
前提: Step 4 残差 > 5
操作: 按需应用 F6 (Stage3/Trail/Merged SMMA)
      跑 F5 Python 分支实验决定是否扩展 rescue
```

---

## 五、风险矩阵（修订版）

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| F1 批量 SMMA 数组边界错误 | 中 | 编译错误/运行崩溃 | 可视模式 2-3 天验证；ArrayCopy 前加 range check |
| F1 回测时间增加 > 20% | 低 | 工作流变慢 | 批量设计保证仅 new bar 计算；如超 1.5h 则降级回 CopyBuffer |
| F2 slot2 引入重复信号 | 低 | 双入场同 anchor | g_signal_anchor_time 去重机制已存在 |
| F2 上下文重建遗漏某个子路径 | 中 | slot2 信号参数部分错配 | 逐一审查函数体内所有对原始参数的引用 |
| F3 PythonSMMA 单值调用异常 | 极低 | post_n SL 失效 | 返回值 check (`sma13_for_sl > 0`) |
| PythonSMMA 与 MT5 SMMA 在早期 bar 差异大 | 中 | warmup 区间信号偏差 | 已跳过前 InpSlowMA 根 warmup bar |

---

## 六、版本线

| 版本 | 内容 | 基线 | 状态 |
|------|------|------|------|
| v3.23 | 基线版 | 旧 | 已替代 |
| v3.25 | UpdatePostNState 改 PythonSMMA + P0/P1 fixes | v3.23 | **当前** |
| **v3.26** | **F1(批量SMMA) + F2(slot2上下文) + F3(post_n SL) + F4(命名)** | v3.25 | **本方案目标** |
| v3.27 (预留) | F5(rescue扩展) + F6(Stage3/Trail/Merged) + Layer3 口径选择 | v3.26 | 待定 |
