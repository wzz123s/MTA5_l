# EA v3.23 → v3.25 修复方案
# 基于 Python 策略 vs EA 逐层对比分析 (2026-07-10)

## 修复优先级总览

| # | 优先级 | Gap | 类型 | 预期效果 |
|---|:--:|------|------|------|
| 1 | P0 | SMMA 初始化: MODE_SMMA → PythonSMMA | 数据 | 基础SMA值对齐, 所有下游信号同步 |
| 2 | P0 | post_n counter 不匹配时不重置 | 逻辑BUG | post_n计数从+28差异大幅缩小 |
| 3 | P0 | M15 只扫描 slot1, 不扫描 slot2 | 逻辑 | M15信号数对齐 Python choose_any |
| 4 | P0 | 段合并窗口 120→全历史 | 数据 | 合并方向一致, Stage3 退出对齐 |
| 5 | P1 | pre_cross 不排除 direction=good/bad K线 | 逻辑 | pre_cross 不抢 cross 的同根K线 |
| 6 | P1 | 缺 M15 rescue 独立路径 | 逻辑 | 救回 too_wide 被拒信号 |
| 7 | P1 | Stage3 退出时机: sign-change vs cross | 逻辑 | 退出K线更精确 |
| 8 | P1 | post_n SL: FindStopSMA → 当前SMA13 | 设计 | SMMA对齐后可用当前SMA13 |

## 详细修复步骤

### 1. [P0] SMMA 初始化 — 已有 PythonSMMA(), 接入所有 MA 句柄

位置: 约第228行, g_ma_fast_m30 等 iMA(MODE_SMMA) 创建处

方案: 不修改 iMA 句柄创建, 而是在所有读取 MA 值的地方, 
      用 PythonSMMA() 替代 CopyBuffer(ma_handle, ...)

具体替换点:
- 第1234行 CalcBias55: CopyBuffer(g_h2_sma55,...) → PythonSMMA(sym, H2, 55, 1)
- 第1200行 CalcBias5: CopyBuffer(g_h2_sma5,...) → PythonSMMA(sym, H2, 5, 1)  
- 第1218行 IsBias5TopPct: CopyBuffer(g_h2_sma5,...) → 循环PythonSMMA
- 第629行 CalcBias55EarlyQ: CopyBuffer(g_h2_sma55,...) → PythonSMMA
- 第1670行 M15 slot1 SMA5/13: CopyBuffer → PythonSMMA
- 第1907行 post_n SMA13: CopyBuffer → PythonSMMA
- 所有 STATUS 日志中的 SMA 值: 同步替换

注意: PythonSMMA 使用静态缓冲, 同一symbol/tf只计算一次, 性能可接受。

### 2. [P0] post_n counter 不匹配时重置

位置: 第1313-1315行

当前(错误):
```mql5
   // else: SMA5/SMA13 relationship doesn't match last cross direction, but
   // no new cross occurred — keep the counter, don't reset. Python does the same.
```

改为:
```mql5
   else
   {
      // v3.25: Python DOES reset when current-trend doesn't match last cross
      // direction.py line 141-146: counter=0, last_cross=None, post_n=0
      g_post_n_counter = 0;
      g_last_cross_dir = 0;
   }
```

### 3. [P0] M15 slot2 扫描

位置: TryM15EarlyEntry 第1592行

当前: if(slot_in_m30 != 1) return false;  // 只查slot1

改为: 先查 slot1, 若失败则查 slot2:
```mql5
// Try slot1 first (0-15 min of M30 bar)
if(slot_in_m30 == 1) {
    if(CheckM15Conditions(...)) return true;
}
// Try slot2 if slot1 failed (15-30 min)
if(slot_in_m30 <= 2) {
    if(CheckM15Conditions(...)) return true;
}
return false;
```

### 4. [P0] 段合并窗口

位置: M30MergedDirectionLastCompleted 第682行

当前: int need = 120;

改为: 动态取可用M30总根数:
```mql5
int need = Bars(InpSymbol, PERIOD_M30) - 1;
if(need > 500) need = 500;  // 上限防性能问题
```

### 5. [P1] pre_cross 排除 direction=good/bad

位置: DetectPreCross 第1266行附近

在 pre_cross 检测成功后, 增加交叉检查:
```mql5
// Also check this is NOT a cross bar (close crossed AND SMA crossed)
bool sma5_prev_above = (ma5_prev2 > ma13_prev2);
bool sma5_curr_above = (ma5_prev1 > ma13_prev1);
if(sma5_prev_above != sma5_curr_above) return 0;  // SMA也穿越了 → 这是cross, 不是pre_cross
```

### 6. [P1] M15 rescue 独立路径

在 M30 信号判定后发现 too_wide 时, 不直接 return,
而是尝试 M15 rescue:
```mql5
if(stop_pts > InpStopHi) {
    // Try M15 rescue for too_wide signals
    if(TryM15Rescue(...)) return;  // 救回成功
    DiagLog(..., "result=SPEC_FAIL");
    return;
}
```

### 7. [P1] Stage3 退出: 等 good/bad K线收完再判断

位置: 第1910-1934行

当前在 merged_sign 改变时立即退出。
改为在方向列标记为 good/bad 的 K线收完后判断。

### 8. [P1] post_n SL: 当前 SMA13

位置: 第2025-2038行

SMMA 对齐后(Fix #1), 当前 SMA13 值与 Python 一致,
可改回用当前 SMA13:
```mql5
// v3.25: after SMMA alignment with Python, use current SMA13 for post_n SL
stop_price = NormalizeDouble(ma13_prev, 5);
```

## 预期效果

| 指标 | v3.23 | v3.25 预期 |
|------|:--:|:--:|
| 信号数 | 74 | ~95-100 |
| post_n | 34 | ~50-55 |
| M15 SLOT1 | 12 | ~15-18 |
| Python匹配率 | 27% | ~40-50% |
| 与Python(101)差距 | -27 | ~-5 |

## 执行顺序

1. Fix #1 SMMA (影响所有下游, 先做)
2. Fix #2 post_n counter (修复后post_n大增)
3. Fix #4 段合并窗口
4. Fix #3 M15 slot2
5. Fix #5-8 依次实现
