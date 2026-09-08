# EA v3.26 修复方案 v3

> 日期: 2026-07-10
> 状态: 可落地方案。先锁定验收口径，再按小步实施和验证。
> 范围: 只修改 `auto_trade/30m2H_Strategy_EA.mq5`。不在 v3.26 中扩展 Python 策略逻辑。

---

## 0. 核心结论

v3.26 不应直接以单一的 "Python 101" 作为唯一验收目标。当前项目里至少有两个可用口径：

| 口径 | 含义 | M15 | Layer3 | 用途 |
|------|------|-----|--------|------|
| Baseline-A | 当前导出脚本 101 | `ea_executable_diag=True`，slot1 runtime replace/rescue，rescue 输入为全部 `spec_fail` | static `apply_layer3` | 研究口径参考 |
| Baseline-B | 纯 EA 可执行口径 | `ea_executable_diag=True`，slot1 runtime replace/rescue，rescue 输入为全部 `spec_fail` | rolling `apply_layer3_ea_executable` | v3.26 主验收 |
| Baseline-C | slot2 实验口径 | slot1 + slot2/choose_any 类行为 | 需单独生成 | slot2 开关开启后的实验验收 |

v3.26 的建议目标：

1. 默认对齐 Baseline-B。
2. M30 SMMA 主流程改为 Python-style SMMA。
3. M30 close 的 post_n SL 改为 Python-style SMA13。
4. M15 early-entry 修复已知时序/anchor/tag 问题。
5. slot2 支持加开关，默认关闭；核心修复验收通过后再开启并对比 Baseline-C。

这样做的原因：Baseline-A/B 当前都是 slot1 runtime 口径；如果直接启用 slot2，却用 A/B 验收，会把"修 bug"和"扩策略"混在一起。

---

## 1. Step 0: 先记录验收数字

### 1.1 Baseline-A

运行当前导出脚本，记录最终导出信号数、Layer3 入选数、MAX_POS 后信号数：

```powershell
cd F:\use_code\MTA5_l\黄金\30m2H策略\scripts\signals
python export_with_mt5_data.py
```

注意：该脚本当前调用：

```python
cb.build_final_accepted(ea_executable_diag=True)
cb.apply_layer3(final_acc, top_pct=TOP_PCT)
```

所以它是 `ea_executable_diag M15 + static Layer3` 的混合口径。

### 1.2 Baseline-B

运行纯 EA 可执行口径：

```powershell
cd F:\use_code\MTA5_l
python -c "from scripts._current_baseline import summarize_strategy, DEFAULT_TOP_PCT; r=summarize_strategy(ea_executable_diag=True, top_pct=DEFAULT_TOP_PCT); print('accepted=', len(r['accepted'])); print('picked=', len(r['picked'])); print('trades=', len(r['trades'])); print('threshold=', r['threshold'])"
```

验收时优先看 `picked` 和实际回测交易数的差异。

### 1.3 Baseline-C

slot2 开关开启前，不把 Baseline-C 作为阻塞项。开启 slot2 前再写一个 Python 分支：

```text
M15 chooser = choose_any 或等价 slot1+slot2
Layer3      = rolling EA 口径优先
rescue      = all spec_fail
```

---

## 2. F1: M30 主流程 SMMA 改为 Python-style 批量函数

### 2.1 当前问题

当前 `GetM30SMAArrays()` 使用 MT5 `CopyBuffer(MODE_SMMA)`，而 Python `calc_smma()` 的初始化是前 N 根均值。差异会影响：

- M30 cross / pre_cross。
- `FindStopSMA()`。
- M15 early-entry 的 M30 SMA 上下文。
- M30 close 的部分止损计算。

### 2.2 落地原则

新增 `GetM30SMAArrays_Python()`，不要循环调用 `PythonSMMA()`。

关键要求：

1. 内部按完整时间轴 `oldest -> newest` 递推。
2. `_full[period - 1]` 是第一根有效 SMMA。
3. 输出仍为 `oldest -> newest`，`out[n-1]` 是 current/forming bar。
4. 缓存按 `Bars()` 失效。
5. 如果输出包含 forming bar，必须在 current M30 close 变化时刷新最后一个值。

### 2.3 推荐实现骨架

```mql5
int GetM30SMAArrays_Python(double &out_fast[], double &out_slow[], int max_bars)
{
   static string _cached_sym = "";
   static int    _cached_bars = 0;
   static double _cached_close0 = 0.0;
   static double _full_fast[];
   static double _full_slow[];
   static int    _full_count = 0;

   int total_bars = Bars(InpSymbol, InpM30Period);
   if(total_bars < InpSlowMA + 2 || max_bars <= 0) return 0;

   double close0 = iClose(InpSymbol, InpM30Period, 0);
   bool need_recalc = (_cached_sym != InpSymbol ||
                       _cached_bars != total_bars ||
                       _full_count != total_bars ||
                       _full_count <= 0);

   if(need_recalc)
   {
      double closes[];
      ArraySetAsSeries(closes, true);
      int n_close = CopyClose(InpSymbol, InpM30Period, 0, total_bars, closes);
      if(n_close != total_bars) return 0;

      ArrayResize(_full_fast, total_bars);
      ArrayResize(_full_slow, total_bars);
      ArrayInitialize(_full_fast, 0.0);
      ArrayInitialize(_full_slow, 0.0);

      double sum5 = 0.0;
      for(int j = 0; j < InpFastMA; j++)
         sum5 += closes[total_bars - 1 - j];
      _full_fast[InpFastMA - 1] = sum5 / InpFastMA;
      for(int j = InpFastMA; j < total_bars; j++)
      {
         int ci = total_bars - 1 - j;
         _full_fast[j] = (closes[ci] + (InpFastMA - 1) * _full_fast[j - 1]) / InpFastMA;
      }

      double sum13 = 0.0;
      for(int j = 0; j < InpSlowMA; j++)
         sum13 += closes[total_bars - 1 - j];
      _full_slow[InpSlowMA - 1] = sum13 / InpSlowMA;
      for(int j = InpSlowMA; j < total_bars; j++)
      {
         int ci = total_bars - 1 - j;
         _full_slow[j] = (closes[ci] + (InpSlowMA - 1) * _full_slow[j - 1]) / InpSlowMA;
      }

      _cached_sym = InpSymbol;
      _cached_bars = total_bars;
      _full_count = total_bars;
   }
   else if(close0 != _cached_close0)
   {
      int last = _full_count - 1;
      if(last > InpSlowMA)
      {
         _full_fast[last] = (close0 + (InpFastMA - 1) * _full_fast[last - 1]) / InpFastMA;
         _full_slow[last] = (close0 + (InpSlowMA - 1) * _full_slow[last - 1]) / InpSlowMA;
      }
   }

   _cached_close0 = close0;

   int valid_count = _full_count - InpSlowMA + 1;
   int out_count = MathMin(max_bars, valid_count);
   if(out_count <= 0) return 0;

   int copy_start = _full_count - out_count;
   ArrayResize(out_fast, out_count);
   ArrayResize(out_slow, out_count);
   ArrayCopy(out_fast, _full_fast, 0, copy_start, out_count);
   ArrayCopy(out_slow, _full_slow, 0, copy_start, out_count);
   return out_count;
}
```

### 2.4 调用点

只替换主流程一处：

```mql5
int n_sma = GetM30SMAArrays_Python(fast_ma, slow_ma, n_rates);
```

不要删除旧 `GetM30SMAArrays()`，保留作诊断对比。

### 2.5 验证

不要只和旧 `MODE_SMMA` 比。必须和现有 `PythonSMMA()` 单值比：

```mql5
for(int sh = 0; sh <= 300; sh++)
{
   int idx = n_sma - 1 - sh;
   if(idx < 0) break;
   double f1 = fast_ma[idx];
   double f2 = PythonSMMA(InpSymbol, InpM30Period, InpFastMA, sh);
   double s1 = slow_ma[idx];
   double s2 = PythonSMMA(InpSymbol, InpM30Period, InpSlowMA, sh);
   // abs diff should be near zero, allowing floating precision only.
}
```

---

## 3. F2: M15 early-entry 修复，slot2 用开关隔离

### 3.1 新增输入参数

新增一个开关，默认关闭：

```mql5
input bool InpEnableM15Slot2 = false;  // Enable M15 slot2 early-entry experiment
```

默认关闭时，v3.26 仍对齐 Baseline-B。开启后再对比 Baseline-C。

### 3.2 必修问题

无论 slot2 是否开启，都要修：

1. `m15_shift` 不能再根据 slot 写成 slot2=0。
2. `signal_src` 和 `DiagLog` tag 动态化。
3. `ExecuteSignalByMarket()` 必须传 `anchor_time`。
4. 必须返回 `ExecuteSignalByMarket()` 的真实结果。

### 3.3 时间索引规则

以 `completed_m15_open = iTime(M15, 1)` 为唯一事实源：

```mql5
int m15_shift = iBarShift(InpSymbol, InpM15Period, completed_m15_open, true);
if(m15_shift < 0) return false;

int m30_shift = iBarShift(InpSymbol, InpM30Period, completed_m15_open, false);
if(m30_shift < 0) return false;

datetime slot_m30_open = iTime(InpSymbol, InpM30Period, m30_shift);
int slot_in_m30 = (int)((completed_m15_open - slot_m30_open) / PeriodSeconds(InpM15Period)) + 1;

bool is_slot1 = (m30_shift == 0 && slot_in_m30 == 1 && slot_m30_open == cur_bar);
bool is_slot2 = (m30_shift == 1 && slot_in_m30 == 2);

if(is_slot2 && !InpEnableM15Slot2) return false;
if(!is_slot1 && !is_slot2) return false;
```

不要使用 `m30_shift >= 1`，避免 EA 启动、跳 tick 或测试器跳时把更早的 M15 误当 slot2。

### 3.4 anchor 规则

```mql5
datetime anchor_time = slot_m30_open + PeriodSeconds(InpM30Period);
if(g_signal_anchor_time == anchor_time) return false;
```

执行交易时必须使用：

```mql5
return ExecuteSignalByMarket(signal_dir, signal_src, stop_price, anchor_time, log_tag);
```

不能传 `slot_m30_open`，也不能忽略返回值。

### 3.5 slot1 上下文

slot1 使用 OnTick 传入的当前 M30 forming 上下文：

```mql5
ctx_ma5_curr = ma5_curr;
ctx_ma13_curr = ma13_curr;
ctx_ma5_prev = ma5_prev;
ctx_ma13_prev = ma13_prev;
ctx_close_curr = rates[n_rates - 1].close;
ctx_close_prev = rates[n_rates - 2].close;
```

### 3.6 slot2 上下文

slot2 只允许 `m30_shift == 1`，因此父 M30 bar 一定是数组中的最近已完成 bar。

```mql5
MqlRates ctx_rates[];
int ctx_nrates = GetM30Rates(ctx_rates, n_rates);
if(ctx_nrates < InpSlowMA + 5) return false;

double ctx_fast[], ctx_slow[];
int ctx_nsma = GetM30SMAArrays_Python(ctx_fast, ctx_slow, ctx_nrates);
if(ctx_nsma < InpSlowMA + 5) return false;
if(ctx_nsma != ctx_nrates) return false;

int parent_idx = ctx_nsma - 1 - m30_shift;  // m30_shift == 1, so parent_idx == n-2
if(parent_idx < 1 || parent_idx >= ctx_nsma - 1) return false;

ctx_ma5_curr = ctx_fast[parent_idx];
ctx_ma13_curr = ctx_slow[parent_idx];
ctx_ma5_prev = ctx_fast[parent_idx - 1];
ctx_ma13_prev = ctx_slow[parent_idx - 1];
ctx_close_curr = ctx_rates[parent_idx].close;
ctx_close_prev = ctx_rates[parent_idx - 1].close;
```

`FindStopSMA()` 可直接使用 `ctx_fast, ctx_slow, ctx_nsma`，因为 `parent_idx == ctx_nsma - 2`，符合当前函数假设。

### 3.7 signal_src 和 log tag

```mql5
string slot_suffix = is_slot2 ? "slot2" : "slot1";
string log_tag = is_slot2 ? "[M15 SLOT2]" : "[M15 SLOT1]";

signal_src = "pre_cross_m15_" + slot_suffix;
signal_src = "cross_m15_" + slot_suffix;
signal_src = "post_n" + IntegerToString(MathAbs(g_post_n_counter)) + "_m15_" + slot_suffix;
```

所有 `DiagLog()`、`Print()`、`PassLayer1Gate()`、`PassLayer3Gate()`、`ExecuteSignalByMarket()` 使用 `log_tag`。

---

## 4. F3: M30 close post_n SL 改为 PythonSMMA

当前位置使用：

```mql5
GetMALastN(g_ma_slow_m30, 1, sma13_buf)
```

替换为：

```mql5
double sma13_py = PythonSMMA(InpSymbol, InpM30Period, InpSlowMA, 1);
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

M15 post_n 路径使用 F2 的 `ctx_ma13_curr`。

---

## 5. 暂不纳入 v3.26 的内容

| 项目 | 处理 |
|------|------|
| Layer3 static/rolling 统一 | 不改 EA。用 Baseline-A/B 量化残差。 |
| Rescue 策略扩展 | 不改 EA。Python 侧先做分支实验。 |
| Stage3/Trail/Merged 的 SMMA | F1-F4 后仍有残差再处理。 |
| H2 SMMA | 暂不动，除非残差定位到 H2 gate。 |

---

## 6. 可落地修复流程

### 阶段 0: 备份和基线记录

1. 备份当前 `auto_trade/30m2H_Strategy_EA.mq5`。
2. 记录当前 `.ex5` 修改时间。
3. 运行 Baseline-A、Baseline-B 命令并写入验证日志。
4. 记录当前 EA 回测统计：总信号、post_n 数、M15 early-entry 数、rescue 数、回测耗时。

### 阶段 1: 实施 F1

1. 在 `PythonSMMA()` 后新增 `GetM30SMAArrays_Python()`。
2. 替换 OnTick 主流程的 `GetM30SMAArrays()` 调用。
3. 编译。
4. 开启临时 SMMA 对比日志，比较 `GetM30SMAArrays_Python()` 与 `PythonSMMA()` 的 shift 0..300。
5. 若误差不接近 0，停止，不进入下一阶段。
6. 跑 2-3 天可视回测，确认无数组越界、无明显性能异常。

### 阶段 2: 实施 F3

1. 替换 M30 close post_n SL 数据源。
2. 编译。
3. 短回测确认 post_n 信号仍能入场，且 stop 价格合理。

### 阶段 3: 实施 F2 的 slot1 安全修复

1. 新增 `InpEnableM15Slot2=false`。
2. 重写 `TryM15EarlyEntry()` 的时间索引、`m15_shift`、`anchor_time`、动态 tag。
3. 保持 slot2 默认关闭。
4. 编译。
5. 回测，对比 Baseline-B。

验收重点：

```text
slot2 日志应为 0，因为开关关闭。
slot1 日志仍正常。
M15 early-entry 不应因 return true 误跳过 M30 close。
同 anchor 不应重复入场。
```

### 阶段 4: 可选开启 slot2

1. 设置 `InpEnableM15Slot2=true`。
2. 生成 Baseline-C。
3. 短回测确认 `_slot2` 日志出现。
4. 检查 slot2 的 `anchor_time` 是否等于父 M30 的 close 时间。
5. 检查 slot2 触发后同 anchor 的 M30 close 是否被压制。
6. 全量回测，对比 Baseline-C，不再用 Baseline-A/B 判断 slot2 是否正确。

### 阶段 5: 残差分析

若 F1-F4 后与 Baseline-B 仍差异较大，按以下顺序定位：

1. Layer3 static vs rolling。
2. Python runtime rescue 与 EA rescue 的触发条件。
3. Stage3/Trail/Merged 的 `MODE_SMMA` 残留。
4. H2 gate 时间对齐。
5. MAX_POS 并发限制差异。

---

## 7. 最小验收标准

v3.26-core，slot2 关闭：

| 项目 | 标准 |
|------|------|
| 编译 | 0 error，0 critical warning |
| SMMA 验证 | batch Python SMMA vs `PythonSMMA()` shift 0..300 误差接近 0 |
| 回测稳定性 | 无数组越界，无异常停止 |
| post_n | 数量明显恢复，不再因 MT5 SMMA 系统偏移失真 |
| M15 slot1 | 可正常触发，anchor 去重正常 |
| slot2 | 默认关闭时无 `_slot2` 信号 |
| 主验收 | 对比 Baseline-B，而不是只看 Baseline-A |

slot2 开启后：

| 项目 | 标准 |
|------|------|
| `_slot2` 日志 | 出现且 anchor 正确 |
| 同 anchor 去重 | slot2 成交后 M30 close 不重复开仓 |
| 验收口径 | 对比 Baseline-C |

