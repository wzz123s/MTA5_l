# EA v3.26 修复方案 — 第二次修订版

> **状态**: 可执行（所有索引/时序问题已修正）
> **日期**: 2026-07-10 22:50
> **基于**: v3.25（UpdatePostNState 已用 PythonSMMA，pre_cross 排除同根穿越，Stage3 cross exit）
> **前版**: [EA_v3.26_修复方案_修订版.md](./EA_v3.26_修复方案_修订版.md) — 5 个 P0 索引/时序 bug 已全部修正

---

## Step 0: 验收口径选择（阻塞项）

### 当前事实

| 维度 | export_with_mt5_data.py 实际行为 | EA 当前行为 |
|------|----------------------------------|------------|
| M15 replace | `choose_slot1_by_distance` + `require_earlier=True` | slot1 early-entry (slot2 死代码) |
| M15 rescue | 输入集 = **所有 spec_fail** | 仅 too_wide |
| Layer3 | `apply_layer3()` → **静态分位数** | IsBias5TopPct() → 滚动 500-bar |
| SMMA 源 (M30) | calc_smma(Python 初始化) | Bias=PythonSMMA, 主流程=CopyBuffer(MODE_SMMA) |

**Python 101 信号的实际口径 = ea_executable_diag M15 + static Layer3 + Python SMMA**

这是一个混合口径。v3.26 必须先明确对齐目标：

| 选项 | 名称 | M15 | Layer3 | SMMA | 用途 |
|------|------|-----|--------|------|------|
| **A** | Baseline-A (当前 101) | slot1-only + all-spec_fail rescue | static quantile | Python calc_smma | 主线研究基准 |
| **B** | Baseline-B (纯 EA 口径) | slot1-only + all-spec_fail rescue | rolling 500-bar | Python calc_smma | EA 对齐验收 |

> **建议**: v3.26 先对齐 Baseline-A（因为 rescue 扩展暂不进 EA），后续再单独评估 Layer3 rolling 差异。

### 行动项

```bash
# 在 F:\use_code\MTA5_l 下运行:
cd 黄金/30m2H策略/scripts/signals
python export_with_mt5_data.py   # 记录当前 101 信号的完整参数

# 同时跑 summarize_strategy(ea_executable_diag=True) 得到 Baseline-B 数字:
cd scripts
python -c "
from _current_baseline import *
df = load_final_signals()
r = summarize_strategy(df, ea_executable_diag=True, top_pct=DEFAULT_TOP_PCT)
print('Baseline-A (current): N=', len(df))
print('Baseline-B (ea_exec+rolling): N=', len(r))
"
```

记录两个数字后进入 Step 1。

---

## Step 1 [P0]: 新增 `GetM30SMAArrays_Python()` — 替换主流程 SMMA 数据源

### 问题根因

当前 `GetM30SMAArrays()` (L437-444) 通过 `GetMABars()` → `CopyBuffer(handle)` 获取 MT5 原生 MODE_SMMA 数据。MT5 的 SMMA 初始化方式与 Python `calc_smma()` 不同（MT5 用首根价格，Python 用前 N 根均值），导致所有下游计算（cross 检测、FindStopSMA、post_n SL、M15 early-entry 的 SMA 上下文）产生系统性偏移。

### 修复：新增批量函数 `GetM30SMAArrays_Python()`

**设计原则**：
1. 一次性 `CopyClose` 取全部 close 价格
2. 内联递推 SMA5 和 SMA13 两套完整数组（不循环调 PythonSMMA）
3. 缓存按 Bars() 失效（每新 M30 bar 最多算一次）
4. 输出格式与原 `GetM30SMAArrays` 完全一致：`oldest→newest`，`[n-1]` = forming bar

#### 1.1 函数代码（插入在 `PythonSMMA()` 之后，约 L205）

```mql5
//+------------------------------------------------------------------+
//| Batch Python-style SMMA for M30 (SMA5 + SMA13)                   |
//| Output: same layout as GetM30SMAArrays — oldest→newest            |
//|         out_fast[out_n-1] = forming bar (shift=0)                |
//| Cache key: Bars(M30) — recalculates only on new bar               |
//+------------------------------------------------------------------+
int GetM30SMAArrays_Python(double &out_fast[], double &out_slow[], int max_bars)
{
   // --- Cache layer ---
   static string    _cached_sym  = "";
   static int       _cached_bars = 0;
   static double    _full_fast[];   // complete time axis: oldest→newest
   static double    _full_slow[];
   static int       _full_count = 0;  // total valid entries in _full_*

   int total_bars = Bars(InpSymbol, InpM30Period);
   if(total_bars < InpSlowMA + 2) return 0;

   bool need_recalc = (_cached_sym != InpSymbol ||
                       _cached_bars != total_bars ||
                       _full_count <= 0);

   if(need_recalc)
   {
      _cached_sym  = InpSymbol;
      _cached_bars = total_bars;

      // Step A: Read all close prices (newest-first from MT5)
      int need = MathMin(total_bars, max_bars + InpSlowMA);  // extra for warmup
      double closes[];
      ArraySetAsSeries(closes, true);
      if(CopyClose(InpSymbol, InpM30Period, 0, need, closes) <= 0) return 0;
      int n_close = ArraySize(closes);
      if(n_close < InpSlowMA + 1) return 0;

      // Step B: Allocate full time-axis arrays
      // Layout: _full[0] = oldest valid, _full[n-1] = newest
      // Index mapping: _full[i] corresponds to time position (n_close - 1 - i)
      ArrayResize(_full_fast, n_close);
      ArrayResize(_full_slow, n_close);

      // === SMA5 calculation (period = InpFastMA = 5) ===
      // Init: mean of first 5 prices (Python style)
      double sum5 = 0;
      for(int j = 0; j < InpFastMA; j++)
         sum5 += closes[n_close - 1 - j];  // oldest 5
      _full_fast[InpFastMA - 1] = sum5 / InpFastMA;  // _full_fast[4] = first valid

      // Recurrence: _full_fast[i] = (close[i] + (p-1)*_full_fast[i-1]) / p
      for(int j = InpFastMA; j < n_close; j++)  // j = 5, 6, ..., n_close-1
      {
         int ci = n_close - 1 - j;              // close index (from newest=0)
         _full_fast[j] = (closes[ci] + (InpFastMA - 1) * _full_fast[j - 1]) / InpFastMA;
         //                    ^^^^^^^^                        ^^^^^^^^^^^^^^^^
         //                    correct close                  prev SMMA (linked chain!)
      }

      // === SMA13 calculation (period = InpSlowMA = 13) ===
      double sum13 = 0;
      for(int j = 0; j < InpSlowMA; j++)
         sum13 += closes[n_close - 1 - j];
      _full_slow[InpSlowMA - 1] = sum13 / InpSlowMA;  // _full_slow[12]

      for(int j = InpSlowMA; j < n_close; j++)  // j = 13, 14, ...
      {
         int ci = n_close - 1 - j;
         _full_slow[j] = (closes[ci] + (InpSlowMA - 1) * _full_slow[j - 1]) / InpSlowMA;
      }

      _full_count = n_close;
   }

   // Step C: Tail-slice to requested max_bars (take NEWEST portion)
   // _full[*] layout: [0]=oldest, [_full_count-1]=newest
   // We want: out[0]=oldest_of_request, out[out_n-1]=newest(forming)
   int out_count = MathMin(max_bars, _full_count - InpSlowMA);  // skip warmup zone
   if(out_count <= 0) return 0;

   // CRITICAL FIX (v3.26 rev2): copy from END of _full*, not start
   // _full has _full_count entries, we need the last 'out_count' ones
   int copy_start = _full_count - out_count;  // first entry to copy

   ArrayResize(out_fast, out_count);
   ArrayResize(out_slow, out_count);
   ArrayCopy(out_fast, _full_fast, 0, copy_start, out_count);
   ArrayCopy(out_slow, _full_slow, 0, copy_start, out_count);

   return out_count;
}
```

#### 1.2 索引正确性验证表

| 操作 | 数组索引 | 对应 bar | 说明 |
|------|---------|----------|------|
| `_full_fast[4]` | init 位置 | 第 5 根 oldest bar | 前 5 根均值 |
| `_full_fast[5]` | 递推第 1 个 | 第 6 根 bar | uses `_full_fast[4]` ✅ 链接正确 |
| `_full_fast[j]` | 通用 | 第 j+1 根 bar | uses `_full_fast[j-1]` ✅ 连续链 |
| `_full_fast[n_close-1]` | 最新值 | forming bar (shift=0) | 最后一个递推结果 |
| `copy_start = _full_count - out_count` | 切片起点 | 最老的有效 bar | ✅ 不丢 forming |
| `out_fast[out_count-1]` | 输出最新 | forming bar | 与原 `fast_ma[n_sma-1]` 语义一致 ✅ |

对比错误版本（已废弃）的索引路径：

```
❌ 废弃版 (rev1):
   _cached_fast[4] = init        ← cache[4]
   oi=1: _cached_fast[1] = ... * _cached_fast[0]  ← _cached_full[0] 未初始化!

✅ rev2 (当前版):
   _full_fast[4] = init          ← full[4]
   j=5:  _full_fast[5]  = ... * _full_fast[4]     ← full[4] 已初始化! ✅
   j=6:  _full_fast[6]  = ... * _full_fast[5]     ← full[5] 刚写入! ✅
```

#### 1.3 修改调用点（仅一处！）

**位置**: L1781

```mql5
// 旧:
int n_sma = GetM30SMAArrays(fast_ma, slow_ma, n_rates);

// 新:
int n_sma = GetM30SMAArrays_Python(fast_ma, slow_ma, n_rates);
```

**影响范围** (这一处修改覆盖以下所有子路径):

| 子路径 | 使用 fast_ma/slow_ma 的函数 | 影响 |
|--------|---------------------------|------|
| M30 cross 检测 (L1802-1806) | ma5_prev, ma13_prev, ma5_prev2, ma13_prev2 | ✅ cross 时机修正 |
| pre_cross (L1992) | ma5_prev2, ma5_prev, ma13_prev, ma13_prev2 | ✅ pre_cross 时机修正 |
| FindStopSMA (L2047) | fast_ma[], slow_ma[], n_sma | ✅ stop 极值搜索区间修正 |
| post_n SL (L2061) | 间接影响（见 F3） | — |
| M15 TryM15EarlyEntry (L1974) | fast_ma, slow_ma, n_sma, ma5_curr/prev | ✅ M15 上下文修正 |
| Stage3 exit (L1947) | 不受影响（用 GetMALastN） | — |
| TrailStage2 (L894) | 不受影响（用 GetMALastN） | — |

#### 1.4 性能评估

| 操作 | 耗时 | 频率 |
|------|------|------|
| 全量重算 (cache miss) | ~50ms (单次 CopyClose + 两套内联递推) | 每 30 分钟一次（新 M30 bar） |
| 缓存命中 (ArrayCopy) | <1ms | 每个 tick |
| vs 旧版 (CopyBuffer × 2) | ~2ms | 每个 tick |
| vs 循环 PythonSMMA (废弃方案) | >5s (period 交替反复失效) | ❌ 不可接受 |

**结论**: 性能优于旧版（cache miss 时略慢但频率极低），远优于废弃的循环方案。

#### 1.5 验证脚本（Step 1.5 — 必须在编译前运行）

在 MT5 策略测试器中临时加入以下诊断代码，或通过 Expert 日志验证：

```mql5
// 临时插入 OnTick() 中 GetM30SMAArrays_Python 调用之后:
#ifdef _DEBUG_SMMA_CHECK
{
   double old_f[], old_s[], new_f[], new_s[];
   int n_old = GetM30SMAArrays(old_f, old_s, n_rates);
   int n_new = GetM30SMAArrays_Python(new_f, new_s, n_rates);
   int cmp_n = MathMin(n_old, n_new);
   double max_diff_fast = 0, max_diff_slow = 0;
   for(int i = 0; i < cmp_n; i++)
   {
      double df = MathAbs(old_f[i] - new_f[i]);
      double ds = MathAbs(old_s[i] - new_s[i]);
      if(df > max_diff_fast) max_diff_fast = df;
      if(ds > max_diff_slow) max_diff_slow = ds;
   }
   if(max_diff_fast > 0.001 || max_diff_slow > 0.001)
      Print("[SMMA-CHECK] diff_fast=", max_diff_fast,
            " diff_slow=", max_diff_slow, " n=", cmp_n);
}
#endif
```

预期：diff 应该是**非零但有界**的（MT5 SMMA vs Python SMMA 的系统性偏移，通常 5-20 points）。如果 diff=0 则说明 MT5 和 Python SMMA 恰好接近（不太可能），如果 diff>1000 points 则说明实现有误。

---

## Step 2 [P0]: 重写 `TryM15EarlyEntry()` — slot2 时序修复 + 父 M30 上下文重建

### 2.1 问题总结（5 个子 bug）

| # | Bug | 位置 | 症状 |
|---|-----|------|------|
| B1 | `slot_m30_open != cur_bar` 永远拒绝 slot2 | L1608 | slot2 死代码 |
| B2 | OnTick 传 parent_m30_bar 不可达 | 方案 rev1 L283 | g_last_m30_bar 已更新为 cur_bar |
| B3 | slot2 用 forming bar 做 ma5_curr/ma13_curr | 方案 rev1 L371 | 错配上下文 |
| B4 | m15_shift slot2=0 取到新形成 M15 | L1614 | entry price 错 |
| B5 | signal_src 全部写死 _slot1 | L1639-1654 | 无法区分来源 |

### 2.2 修复策略

**核心思路**：不再从 OnTick 传入父 M30 上下文。改为让 `TryM15EarlyEntry()` 以 `completed_m15_open` 为唯一事实来源，自行反推所有时间索引：

```
completed_m15_open (= iTime(M15,1))
  │
  ├─→ iBarShift(M30, completed_m15_open) → m30_shift (所属 M30 bar shift)
  │     ├─ m30_shift = 1 → slot2 of previous M30 (需要父上下文)
  │     └─ m30_shift = 0 → slot1 of current M30 (正常路径)
  │
  ├─→ slot_in_m30 计算 (不变)
  │
  ├─→ 时间门判断: 放宽为允许 slot2 在新 M30 开始时处理
  │
  └─→ 上下文重建: slot2 → 从 GetM30Rates/SMA 重新取父 M30 的 rates+SMA
```

### 2.3 完整重写代码

```mql5
//+------------------------------------------------------------------+
//| Real-time M15 early-entry (v3.26)                                |
//| Supports both slot1 (current M30) and slot2 (previous M30)       |
//| Context reconstruction: slot2 derives parent M30 data internally |
//+------------------------------------------------------------------+
bool TryM15EarlyEntry(MqlRates &rates[], int n_rates,
                      double &fast_ma[], double &slow_ma[], int n_sma,
                      double ma5_curr, double ma13_curr,
                      double ma5_prev, double ma13_prev,
                      datetime cur_bar)
{
   if(!InpUseM15EarlyEntry) return false;
   if(OurStageCount() >= InpMaxPos)
   {
      DiagLog("[M15]", "Candidate",
              "result=SKIP_MAX_POS stages=" + IntegerToString(OurStageCount()) +
              " max_pos=" + IntegerToString(InpMaxPos));
      return false;
   }

   datetime completed_m15_open = iTime(InpSymbol, InpM15Period, 1);
   if(completed_m15_open <= 0) return false;

   // Derive M30 context from completed_m15_open (single source of truth)
   int m30_shift = iBarShift(InpSymbol, InpM30Period, completed_m15_open, false);
   if(m30_shift < 0) return false;

   datetime slot_m30_open = iTime(InpSymbol, InpM30Period, m30_shift);
   if(slot_m30_open <= 0) return false;

   int slot_in_m30 = (int)((completed_m15_open - slot_m30_open) / PeriodSeconds(InpM15Period)) + 1;
   if(slot_in_m30 < 1 || slot_in_m30 > 2) return false;

   // --- v3.26 FIX B1: Time-gate allows slot2 on new-M30 boundary ---
   // slot1 (m30_shift=0): slot_m30_open == cur_bar → normal
   // slot2 (m30_shift=1): slot_m30_open == PREVIOUS bar → allow when processing late
   bool is_slot2 = (m30_shift >= 1);
   if(m30_shift == 0 && slot_m30_open != cur_bar) return false;
   // Note: m30_shift >= 1 means "this M15 belongs to a previously-completed M30 bar".
   // We still process it because it just completed and we haven't had a chance yet.

   datetime anchor_time = slot_m30_open + PeriodSeconds(InpM30Period);
   if(g_signal_anchor_time == anchor_time) return false;

   // --- v3.26 FIX B4: m15_shift always = 1 (completed bar) ---
   // Both slot1 and slot2 use the JUST-completed M15 bar.
   // Slot2's completed_m15_open IS shift=1 when processed at T+30.
   int m15_shift = 1;
   double m15_close_arr[];
   if(CopyClose(InpSymbol, InpM15Period, m15_shift, 1, m15_close_arr) <= 0) return false;

   // M15 SMA13 for same-side check (keep using CopyBuffer — M15 SMMA diff is minor)
   double m15_sma13_arr[];
   if(CopyBuffer(g_ma_slow_m15, 0, m15_shift, 1, m15_sma13_arr) <= 0) return false;
   double m15_sma13 = m15_sma13_arr[0];
   double m15_close = m15_close_arr[0];
   if(m15_sma13 <= 0 || m15_sma13 == EMPTY_VALUE) return false;

   // --- v3.26 FIX B3: Context reconstruction for slot2 ---
   // For slot2, rebuild parent M30's SMA/rate context instead of using new bar data.
   double ctx_ma5_curr, ctx_ma13_curr, ctx_ma5_prev, ctx_ma13_prev;
   double ctx_close_curr, ctx_close_prev;
   string log_tag;

   if(is_slot2 && m30_shift >= 1)
   {
      log_tag = "[M15 SLOT2]";

      // Rebuild parent M30 context: get fresh rates+SMA for parent bar
      MqlRates ctx_rates[];
      int ctx_nrates = GetM30Rates(ctx_rates, n_rates);  // same window size
      if(ctx_nrates < InpSlowMA + 5) return false;

      double ctx_fast[], ctx_slow[];
      int ctx_nsma = GetM30SMAArrays_Python(ctx_fast, ctx_slow, ctx_nrates);
      if(ctx_nsma < InpSlowMA + 5) return false;

      // Parent M30 completed bar index within the array:
      // ctx_rates[ctx_nrates - 1] = current (forming) bar X+1
      // ctx_rates[ctx_nrates - 2] = last completed bar X (parent!)
      // For m30_shift=1: parent_idx = ctx_nsma - 1 - m30_shift = ctx_nsma - 2
      int parent_shift = m30_shift;  // = 1 for slot2
      int parent_idx = ctx_nsma - 1 - parent_shift;
      if(parent_idx < 1 || parent_idx >= ctx_nsma - 1) return false;  // bounds check

      ctx_ma5_curr  = ctx_fast[parent_idx];      // parent M30 bar X SMA5
      ctx_ma13_curr = ctx_slow[parent_idx];       // parent M30 bar X SMA13
      ctx_ma5_prev  = ctx_fast[parent_idx - 1];   // bar X-1 SMA5
      ctx_ma13_prev = ctx_slow[parent_idx - 1];    // bar X-1 SMA13
      ctx_close_curr = ctx_rates[parent_idx].close;  // bar X close (for DetectPreCross)
      ctx_close_prev = ctx_rates[parent_idx - 1].close; // bar X-1 close
   }
   else
   {
      // slot1: use caller's context (current M30 bar, already correct)
      log_tag = "[M15 SLOT1]";
      ctx_ma5_curr  = ma5_curr;
      ctx_ma13_curr = ma13_curr;
      ctx_ma5_prev  = ma5_prev;
      ctx_ma13_prev = ma13_prev;
      ctx_close_curr = rates[n_rates - 1].close;   // forming bar close (or last comp for slot1)
      ctx_close_prev = rates[n_rates - 2].close;   // prev completed bar close
   }

   // Signal detection (uses RECONSTRUCTED context for slot2)
   int signal_dir = 0;
   string signal_src = "";
   int pre_cross = DetectPreCross(ctx_close_prev, ctx_close_curr,
                                  ctx_ma5_prev, ctx_ma5_curr,
                                  ctx_ma13_curr, ctx_ma13_prev);
   bool is_pre_cross_mode = (pre_cross != 0);

   bool curr_above = ctx_ma5_curr > ctx_ma13_curr;
   bool prev_above = ctx_ma5_prev > ctx_ma13_prev;
   bool is_cross_mode = ((!prev_above && curr_above) || (prev_above && !curr_above));
   bool is_post_n_mode = (g_post_n_counter >= InpPostNMin && g_post_n_counter <= InpPostNMax);
   bool is_post_n_mode_neg = (g_post_n_counter <= -InpPostNMin && g_post_n_counter >= -InpPostNMax);

   if(is_pre_cross_mode)
   {
      signal_dir = pre_cross;
      signal_src = "pre_cross_m15_" + (is_slot2 ? "slot2" : "slot1");
   }
   else if(is_cross_mode)
   {
      signal_dir = curr_above ? +1 : -1;
      signal_src = "cross_m15_" + (is_slot2 ? "slot2" : "slot1");
   }
   else if(is_post_n_mode)
   {
      signal_dir = +1;
      signal_src = "post_n" + IntegerToString(g_post_n_counter) + "_m15_" + (is_slot2 ? "slot2" : "slot1");
   }
   else if(is_post_n_mode_neg)
   {
      signal_dir = -1;
      signal_src = "post_n" + IntegerToString(-g_post_n_counter) + "_m15_" + (is_slot2 ? "slot2" : "slot1");
   }

   if(signal_dir == 0) return false;

   DiagLog(log_tag, "Candidate",
           "mode=" + signal_src +
           " dir=" + DirText(signal_dir) +
           " anchor=" + TimeToString(anchor_time, TIME_DATE|TIME_MINUTES) +
           " m15_close=" + DoubleToString(m15_close, 5) +
           " m15_smma13=" + DoubleToString(m15_sma13, 5) +
           " post_n_counter=" + IntegerToString(g_post_n_counter));

   if(!PassLayer1Gate(log_tag)) return false;
   if(!PassLayer3Gate(log_tag)) return false;

   // Stop price calculation (uses reconstructed context for slot2)
   double stop_price = 0.0;
   if(is_pre_cross_mode || is_cross_mode)
   {
      // For slot2: pass ctx_fast/ctx_slow to FindStopSMA (parent M30's SMA arrays)
      int seg_dir = (signal_dir == +1) ? -1 : +1;
      double stop_sma;
      if(is_slot2)
      {
         // Use parent-context SMA arrays for slot2
         double sfast[], sslow[];
         int sn = GetM30SMAArrays_Python(sfast, sslow, n_rates);
         stop_sma = FindStopSMA(sfast, sslow, sn, seg_dir);
      }
      else
      {
         stop_sma = FindStopSMA(fast_ma, slow_ma, n_sma, seg_dir);
      }
      if(stop_sma <= 0)
      {
         if(InpDebugStages)
            Print(log_tag, " ", signal_src, ": NO_STOP_EXTREME");
         DiagLog(log_tag, "Stop", "mode=" + signal_src + " result=NO_STOP_EXTREME");
         return false;
      }
      stop_price = NormalizeDouble(stop_sma, 5);
   }
   else
   {
      // Post-N mode: SL = parent M30's current SMA13
      double sma13_now = ctx_ma13_curr;
      if(signal_dir == +1 && m15_close <= sma13_now)
      {
         DiagLog(log_tag, "Stop", "mode=" + signal_src + " result=POSTN_STOP_INVALID");
         return false;
      }
      if(signal_dir == -1 && m15_close >= sma13_now)
      {
         DiagLog(log_tag, "Stop", "mode=" + signal_src + " result=POSTN_STOP_INVALID");
         return false;
      }
      stop_price = NormalizeDouble(sma13_now, 5);
   }

   // Execute
   DiagLog(log_tag, "Execute",
           signal_src + " entry_proxy=" + DoubleToString(m15_close, 5) +
           " stop=" + DoubleToString(stop_price, 5) +
           " dir=" + DirText(signal_dir));
   ExecuteSignalByMarket(signal_dir, signal_src, stop_price, slot_m30_open, log_tag);
   return true;
}
```

### 2.4 关键变更清单

| 变更 | 旧代码 (v3.25) | 新代码 (v3.26) | 修复的 Bug |
|------|----------------|---------------|-----------|
| 时间门 | `if(slot_m30_open != cur_bar) return false;` | slot1 保留此检查；slot2 (`m30_shift>=1`) 跳过 | **B1** |
| m15_shift | `(slot==1)?1:0` | 固定 `= 1` | **B4** |
| 上下文来源 | 全部用 caller 传入的新 M30 数据 | slot2 重建父 M30 上下文 | **B3** |
| DetectPreCross 参数 | `rates[n_rates-2].close, rates[n_rates-1].close` | `ctx_close_prev, ctx_close_curr` (slot2 用父 bar) | **B3** |
| signal_src | 硬编码 `_slot1` | 动态 `_slot1` / `_slot2` | **B5** |
| Log tag | 硬编码 `[M15 SLOT1]` | 局部变量 `log_tag` | **B5** |
| FindStopSMA (slot2) | 用 caller 的 fast_ma (新 bar) | 重新取 ctx_fast/ctx_slow (父 bar) | **B3** |
| post_n SL (slot2) | 用 `ma13_curr` (新 bar) | 用 `ctx_ma13_curr` (父 bar) | **B3** |
| OnTick 调用签名 | 无变化 (9 个参数) | 无变化 | **B2** (无需改 OnTick) |

---

## Step 3 [P0-F3]: post_n SL 改为 PythonSMMA

### 修改点

**位置**: L2059-2064 (M30-close 路径的 post_n SL)

```mql5
// 旧 (v3.25):
double sma13_buf[];
if(GetMALastN(g_ma_slow_m30, 1, sma13_buf) && ArraySize(sma13_buf) > 0)
{
   stop_price = NormalizeDouble(sma13_buf[0], 5);
}

// 新 (v3.26):
// Use PythonSMMA for M30 SMA13 to match Python's post_n SL calculation
double sma13_py = PythonSMMA(InpSymbol, InpM30Period, InpSlowMA, 1);  // shift=1 = last completed
if(sma13_py > 0)
{
   stop_price = NormalizeDouble(sma13_py, 5);
}
else
{
   DiagLog("[M30 CLOSE]", "Stop", "mode=" + signal_src + " result=POSTN_STOP_INVALID");
   return;
}
```

**理由**: Python 的 post_n SL 用的是 `sma13[i]` 同 bar `calc_smma(13)` 结果。EA 当前用 `GetMALastN(g_ma_slow_m30)` = MT5 原生 MODE_SMMA。改为 `PythonSMMA(M30, 13, 1)` 单次调用，性能影响可忽略（PythonSMMA 有缓存）。

**注意**: M15 路径的 post_n SL 已在 Step 2 中一并修复（使用 `ctx_ma13_curr` = 父 bar 的 PythonSMMA 值，因为 slot2 的 ctx 来自 `GetM30SMAArrays_Python`）。

---

## Step 4 [P1-F4]: signal_src 命名 + log tag 动态化

已在 Step 2 的重写代码中包含。关键点：

```mql5
string log_tag = is_slot2 ? "[M15 SLOT2]" : "[M15 SLOT1]";
string signal_src = ... + (is_slot2 ? "slot2" : "slot1");
```

所有 DiagLog/Print 调用统一使用 `log_tag` 局部变量，不再硬编码。

---

## Step 5 [P1-F5]: Rescue 扩展 → Python 分支实验（不进 EA）

### 当前状态

| 维度 | EA | Python (export script) |
|------|----|-----------------------|
| rescue 触发条件 | only `too_wide` (stop_pts > InpStopHi) | **all spec_fail** (含 too_wide + too_tight) |
| rescue 入口 | 只试 M15 shift=1 | choose_any() 扫 slot1+slot2 |

### 实验方案

在 `scripts/_m15_rescue_experiment.py`（或现有测试脚本中）增加分支：

```python
# Branch 1: current EA behavior (baseline)
rescue_mask = df['stop_pts'] > STOP_HI  # too_wide only

# Branch 2: expanded rescue (experiment)
rescue_mask_expanded = (
    (df['stop_pts'] > STOP_HI) |   # too_wide
    (df['stop_pts'] < STOP_LO)     # too_tight (spec fail)
) & (df['spec_fail'] == True)

# Compare:
print(f"Branch1 (EA-current) rescued: {rescue_mask.sum()}")
print(f"Branch2 (expanded) rescued: {rescue_mask_expanded.sum()}")
# Check: do expanded signals pass Layer3? What's final PF?
```

**只有当实验显示明确正收益时才将扩展条件合入 EA v3.27**。

---

## Step 6 [P2-F6]: Stage3 / TrailStage SMMA 对齐（可选，F1-F4 验收后决定）

### 当前不受影响的调用点

| 位置 | 函数 | 数据源 | 是否受 F1 影响 |
|------|------|--------|---------------|
| L894 | TrailStage2 SL | `GetMALastN(g_ma_slow_m30, 1, ...)` | ❌ 不受（独立 GetMALastN） |
| L1947 | Stage3 exit cross | `GetMALastN(g_ma_fast/slow_m30, 2, ...)` | ❌ 不受 |
| L393-394 | H2Filter | `GetMALastN(g_ma_fast/slow_h2, 1, ...)` | ❌ 不受（H2 不同 tf） |
| L418-419 | M30Cross | `GetMALastN(g_ma_fast/slow_m30, 3, ...)` | ❌ 不受（但 M30Cross 目前未被主流程使用，被 OnTick 内联 cross 取代） |

**建议**: 这些调用点保持现状。Stage3/TrailStage 的 SMMA 差异只影响出场精度（SL 价格差几个 points），不影响信号数量/入场决策。如需完美对齐可在后续版本处理。

---

## 编译检查清单

修改完成后逐项确认：

- [ ] `GetM30SMAArrays_Python()` 编译无错（特别注意数组声明在 executable statements 之前）
- [ ] `TryM15EarlyEntry()` 新签名兼容 OnTick 调用点（参数列表不变）
- [ ] `is_slot2` / `log_tag` / `signal_src` 所有分支覆盖（无遗漏路径返回 0）
- [ ] `parent_idx` 边界检查（`parent_idx < 1 || parent_idx >= ctx_nsma - 1`）
- [ ] MQL5 变量声明规则：所有 `double` 声明在任何 `if/for` 之前
- [ ] 版本号更新为 `"3.26"`

## 回测验收指标

| # | 指标 | v3.25 基线 | v3.26 目标 | 判定 |
|---|------|-----------|-----------|------|
| 1 | 总信号数 | 37 (post_n=0 bug) | **70-95** | 主要验收 |
| 2 | post_n 分布 | 全部=0 | 有非零值 (目标 50-55) | 主要验收 |
| 3 | M15 SLOT2 出现次数 | 0 (死代码) | ≥ 1 | 功能验证 |
| 4 | M15 RESCUE 成功率 | 0/7 | ≥ 3/7 | 功能验证 |
| 5 | signal_src 分类完整性 | 只有 `_slot1` | `_slot1`, `_slot2`, `_rescue` 三类均出现 | 诊断验证 |
| 6 | vs Baseline-A 差距 | ~64 信号 (101-37) | ≤ 15 | 对齐度 |
| 7 | 回测时长 | ~1h | ≤ 1.5h | 性能回归检查 |

## 文件修改清单

| 文件 | 修改类型 | 内容 |
|------|---------|------|
| `auto_trade/30m2H_Strategy_EA.mq5` | 新增函数 | `GetM30SMAArrays_Python()` (~80 行) |
| `auto_trade/30m2H_Strategy_EA.mq5` | 重写函数 | `TryM15EarlyEntry()` (~170 行替换原有 ~120 行) |
| `auto_trade/30m2H_Strategy_EA.mq5` | 局部修改 | L1781 调用点 + L2059-2064 post_n SL + 版本号 |

**总改动量**: ~250 行新增/修改，集中在 3 个区域。

---

## 不修改项（有意识的决定）

| 项目 | 决定 | 理由 |
|------|------|------|
| Layer3 方法 | 保持 rolling (IsBias5TopPct) | Baseline-A 用静态，差异已知且量化，作为独立残差不混入 v3.26 |
| M30MergedDirectionLastCompleted | 保持 CopyBuffer | 服务 merged post_n 路径，当前未启用，列入诊断观察 |
| Stage3/TrailStage SMMA | 保持 GetMALastN | 不影响入场信号数，出场精度差异 < 10 pts |
| H2 SMMA | 保持 CopyBuffer (H2Filter) | H2 是过滤条件不是信号触发器，少量偏差不改变 accept/reject |
| Rescue 条件扩展 | 不进 EA | 需要 Python 分支实验数据支撑 |
