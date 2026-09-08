# 30m2H_Strategy_EA 全面 BUG 审查报告（2026-09-07）

> 审查对象：`黄金/30m2H策略/auto_trade/30m2H_Strategy_EA.mq5`（4,003 行，v3.31 头注 / 实含 v3.35-3.36 逻辑）  
> 方法：逐行通读 + 交叉引用 ABC_EA（已修 BUG-12/13/15）与 Python 参考实现  
> 分级：🔴 P0 高（影响对齐/正确性）｜🟠 P1 中（隐患/维护）｜🟡 P2 低（健壮性/整洁）

---

## 修复进度（2026-09-07 22:40 最终更新）

| Bug                                        | 状态    | 说明                                                         |
| ------------------------------------------ | ----- | ---------------------------------------------------------- |
| P0-1 merged stack 移植                       | ✅ 已修  | v3.37，替换近似吸收为 ABC 精确 stack，500 bar 中 27 个(5.4%)merged 方向修正 |
| P0-2 版本号统一                                 | ✅ 已修  | v3.37，property + OnInit 打印统一                               |
| P0-3 H2 口径 PythonSMMA                      | ✅ 已修  | v3.37，H2Filter 改用 PythonSMMA(mean-init)                    |
| P2-2 InpMagic 默认值                          | ✅ 已修  | 302025 → 302036（对齐实盘 .chr）                                 |
| P1-2 死代码                                    | ✅ 已删  | 删 6 个无调用函数 533 行（TryM15EarlyEntry/M15EntryDiagWrite/M30Cross/ShouldExit/HasPosDir/H2SegmentDir）|
| P1-1 去重失效                                  | ✅ 已修  | g_signal_fired 比较改为 iTime(M30,1) completed bar               |
| P1-3 h2_cross 参数                             | ✅ 已删  | CheckStageExit 删未用参数 + 2 处调用点                           |
| P2-3 FindStopSMA 刷屏                          | ✅ 已修  | RETURN Print 加 InpDebugStages 门控                            |
| P1-4 数据不足放行                               | ✅ 核对非bug | EA `valid<10 return true` 与 Python `len<10→NaN→PASS` 完全一致，无需修 |
| P2-1 &&/||                                    | ✅ 核对非bug | `&&` 合理：导出本品种全部成交供 Python 按 stage 列自行过滤          |
| P2-4 双计数器                                  | ✅ 已删  | 删 UpdatePostNState + g_post_n_counter + g_last_cross_dir（净减 60 行）|
| M15 孤儿参数/句柄                              | ✅ 已清  | 删 3 参数+InpExportM15EntryDiag+diag句柄+打印+打开/关闭块（净减 37 行）；InpM15Period/new_m15_bar 保留 |

**编译验证：0 errors, 0 warnings ✅（3993 → 3364 行，累计净减 629 行）**

---

## 🔴 P0 — 高优先级

### P0-1 主线 merged 段吸收仍是「近似实现」，未采用 ABC 的精确 stack（BUG-13 未完全落地）

- 位置：`M30MergedDirectionCodeLastCompleted()`（L1797，注释自认 "Approximation-port of ... filter_short_segments_causal"）
- 现状：主线用 `dir_codes + region_count 吸收` 的近似算法；ABC_EA 已把 BUG-13 修为「逐 bar + stack」精确等价 Python `filter_short_segments_causal`
- 后果：主线 merged 方向（决定 post_n 计数 + stage3 退出）与 Python 非严格一致，是主线 EA↔Python 信号分歧（早期 74 vs 118）的结构性根因之一
- 建议：把 ABC_EA 的 stack 实现移植到主线 `M30MergedDirectionCodeLastCompleted`，替换近似吸收

### P0-2 版本号与实际代码代际脱节

- `#property version "3.31"`（L30），但代码含 v3.32（M15 slot1 禁用）、v3.33（strict 移除）、v3.34（FindStopSMA 语义）、v3.35（M15 rescue 移除）、v3.36（CalcBias55EarlyQ 对齐）逻辑
- `OnInit` 硬编码打印 "v3.26 - Initializing"（L1116），与实际 v3.3x 不符
- 后果：无法靠版本号判断代码代际（今日已实证 5 份源都写 3.31）
- 建议：确立单一权威版本号（建议 v3.36），property + OnInit 打印 + 注释统一

### P0-3 H2 方向口径不一致（MODE_SMMA 句柄 vs PythonSMMA）

- `H2Filter()`（L1417）读 `g_ma_fast_h2/g_ma_slow_h2`（OnInit `iMA(..., MODE_SMMA)`，MT5 内建 SMMA init=首值）
- 而 Layer1/3 的 Bias_55/Bias_5 用 `PythonSMMA()`（init=均值，与 Python calc_smma 对齐）
- 后果：H2 方向在早期/边界 bar 可能与 Python mark_direction 不一致。当前 h2_dir 仅用于 CSV/STATUS（不进入开仓决策），故暂不影响交易，但会使 CSV 与 Python 的对齐诊断失真
- 建议：H2Filter 改用 PythonSMMA 读 H2 SMA5/13，彻底统一口径

---

## 🟠 P1 — 中优先级

### P1-1 `g_signal_fired` 去重失效（语义错误，靠兜底防重）

- L3866 `signal_bar = rates[n-2].time`（completed bar），L3033 存入 `g_signal_anchor_time`
- L3448/3467 `g_signal_fired = (g_signal_anchor_time == cur_bar)`，而 `cur_bar = iTime(M30,0)`（forming bar）
- 二者永远不等 → `g_signal_fired` 恒 false；实际防重靠 `new_m30_bar`（每 bar 一次）+ `OurStageCount()>=InpMaxPos`
- 建议：改为与 completed bar 比较，或直接删除该变量

### P1-2 死代码约 450+ 行（grep 证实无调用）

| 函数                | 行号         | 说明                                  |
| ----------------- | ---------- | ----------------------------------- |
| TryM15EarlyEntry  | L3044-3429 | v3.35 已移除 M15 slot1，全函数无调用（P3-3 已知） |
| M15EntryDiagWrite | L768-819   | 仅被 TryM15EarlyEntry 调用，随之死          |
| M30Cross          | L1443-1463 | 无调用（OnTick 内联 cross）                |
| ShouldExit        | L2308-2335 | 无调用                                 |
| HasPosDir         | L2044-2054 | 无调用                                 |
| H2SegmentDir      | L1396-1412 | 无调用（且有内部 fast/slow 覆盖 bug）          |

- 建议：删除上述函数 + `InpUseM15EarlyEntry/InpEnableM15Slot2/InpUseM15RescueTag` 参数组 + M15 diag CSV 导出（OnInit/OnDeinit 句柄），可净减约 500 行维护噪音

### P1-3 `CheckStageExit` 的 `h2_cross` 参数未被使用

- L1982 签名含 `int h2_cross`，函数体未引用；调用方（L3638）传入 h2_x 属无效传参
- 建议：删除该参数

### P1-4 `IsBias5TopPct` 数据不足直接放行

- L2578 `if(valid < 10) return true;` —— 历史不足 10 根 H2 时 Layer3 直接放行
- 需与 Python 数据不足时的行为对齐确认，避免冷启动/短历史过放

---

## 🟡 P2 — 低优先级

### P2-1 `DumpRawDealHistory` 过滤逻辑疑误

- L373 `if(symbol != InpSymbol && stage == 0) continue;` 用 `&&`，会导出「非本 symbol 但 stage>0」的脏行；意图应为 `||`
- 影响：仅原始成交导出 CSV 完整性，不影响交易

### P2-2 InpMagic 默认值 302025 与实盘 .chr 的 302036 不一致

- 重新从导航器拖入用默认参数时，magic 与 ledger/重启恢复错位
- 建议：默认值统一为 302036

### P2-3 FindStopSMA 无条件 Print 刷屏

- L1549 每次调用必打印，回测/信号密集时会刷日志
- 建议：改为 InpDebugStages 门控

### P2-4 g_post_n_counter 与 g_merged_post_n_counter 双计数器冗余

- 决策只用 merged（L3874），g_post_n_counter 仅诊断显示
- 建议：保留 merged，精简 raw 计数器
- **P1 四项**（去重失效、450 行死代码、参数未用、数据不足放行）+ **P2-1/P2-3/P2-4** 待修/待确认——这些不影响对齐和正确性（死代码不执行、去重有兜底），属于下一轮清理。

## 修复建议优先级总结

1. **先做 P0-1**（移植 ABC 的 merged stack）→ 直接提升主线对齐度，收益最大
2. P0-3（H2 口径统一）→ 让 CSV 诊断可与 Python 直接对表
3. P0-2（版本号规范）+ P1-1/P1-2/P1-3（去重语义 + 删 450 行死代码）→ 一次性清理
4. P2 项随手修

> 关联：ABC_EA 已修 BUG-12/13/15/P2-5（`30m2H_ABC_Tester对齐报告_20260906.md`，对齐 226/240=94.2%），主线可对照移植。
