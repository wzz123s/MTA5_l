# 30m2H EA v3.21 → v3.26 修复与对齐历史（2026-07-09 ~ 07-10）

> 来源：`.workbuddy/memory/2026-07-09.md`、`2026-07-10.md` 工作日志归档
> 性质：历史开发档案。当前 EA 已迭代至 v3.36 / 30m2H_ABC_EA，本记录仅用于回溯 v3.21→v3.26 期间的修复链与决策。

---

## 1. 背景：MT5 vs Python 盈利差异（2026-07-09 定位）

### 1.1 20260709.log 分析

- 63.7 万行，UTF-16 LE，两次完整回测 pass。
- Pass 1: final balance **$7.82（破产）**；Pass 2: final balance **$895.86**。
- 根本问题：$500 初始资金 + 0.06 lot 总仓位（InpRiskPct=3%，3-stage 平衡 0.01/0.02/0.03），单笔风险约 18%。
- Execute 返回 0 全部由 `retcode=10019 (No money)` 引起，发生在 Pass 1。
- 6 个任务关键窗口的 EA 行为与 task_plan.md 预期完全吻合。
- 信号转化率仅 0.05%（72,542 候选 → 38 执行），Layer1 和 MAX_POS 吃掉 97%。

### 1.2 同窗对比（2026H1，同参数）

| 类别 | 数量 |
| --- | --- |
| MT5 信号 / Python 信号 | 12 / 12 |
| 共同信号 | 7 |
| 共同但止损不一致 | 7（100%） |
| MT5 独有 | 5（全是 M15 SLOT1，Python 时间轴缺口无法表达） |
| Python 独有 | 5（MT5 未执行：Layer3/MAX_POS/资金不足） |

### 1.3 差异根因

1. 7 笔共享信号止损距离全部不同 → 直接导致 P&L 不同：
   - 5 笔 M30 CLOSE：差异 <2.1pt（实时报价 vs K线价，可接受）；
   - 2 笔 M15 SLOT1：差异 3.8–9.2pt（slot1_close vs slot1_low vs 实时 tick）。
2. stop-distance 代理最优：`long=slot1_low / short=slot1_low`（mean_abs_error=1.49），仅用于诊断，不改执行分支。

## 2. EA v3.22：动态仓位修复（2026-07-09）

修改 `auto_trade/30m2H_Strategy_EA.mq5`：

1. 新增 `InpUseDynamicLots` 参数（默认 true）。
2. `StageLots()` 支持动态计算：balance × InpRiskPct% ÷ stop_distance，按 0.5:1.0:1.5 分配。
3. `ExecuteSignalByMarket()` 增加开仓前保证金预检（打印 Balance/Equity/Margin/FreeMargin）。
4. 保证金不足时输出 `LOW_MARGIN` 警告。
5. 固定 lot 模式保留（InpUseDynamicLots=false），向后兼容。

配置文件同步更新：v3.22_dynamic_lots_top34 set（新建）、v3.21_top34 set、current_mainline_full_2018 ini、AppData Tester 默认 set。

### v3.22 $2000 回测验证

- Deposit $2000，全区间 2018–2026：Final $1983.77（PnL -$16.23，-0.8%），37 unique signals。
- **0 次 No money** — 动态仓位修复生效。
- Lots：0.01×59、0.02×20、0.03×13、other×19。

## 3. EA v3.23：post_n 全部被误杀修复（2026-07-09）

- 根因：EA 第 1554 行旧 M15 close-side 过滤器（`CLOSE_SIDE_FAIL`）。
- 265 个 post_n 候选全被拒 → Python 102 笔 vs MT5 37 笔的根因。
- Python 主策略已废弃此过滤（M15 replace_any + rescue 替代），EA 未同步。
- v3.23 已移除该过滤。

## 4. MT5 原生 SMMA 数据管道（2026-07-10 凌晨）

创建：

- `processing/mt5_data_source.py` — 从 EA CSV 读取 MT5 原生 SMMA；
- `黄金/30m2H策略/scripts/data_source/build_from_mt5.py` — 生成 MT5 原生 H2/M30；
- `processing/prepare.py` 修改 — mt5_smma 参数优先用 MT5 值；
- `黄金/30m2H策略/scripts/signals/export_with_mt5_data.py` — MT5 数据完整信号导出；
- 原始文件备份：`黄金/30m2H策略/scripts/_backup_20260710/`。

### 三种数据源 x 完整策略对比（最终汇总）

| 数据源 | SMMA 计算 | 策略 | 信号数 | vs EA(74) | 总 Pts | WR |
| --- | --- | --- | --- | --- | --- | --- |
| MT5 原生 | MT5 内置 | basic Layer1-3 | 113 | +39 | - | - |
| MT5 原生 | MT5 内置 | combo+MAX_POS | 89 | +15 | +2781 | 53% |
| Python 原生 | calc_smma() | combo+MAX_POS | 101 | +27 | +4902 | 59% |

### 结论（07-10 凌晨）

- Python 原生 SMMA + 完整组合：101 信号、+4902pts、59% WR（最接近旧基线 118）。
- EA v3.23：74 信号（受 post_n counter 重置 + M15 入口差异影响）。
- 剩余差距来源：EA post_n counter 重置逻辑 + M15 SLOT1 实时 tick + Layer3 滚动 vs 全局。

## 5. EA v3.25：10 项对齐修复（2026-07-10）

### P0（4 项）

1. SMMA：关键读取点改用 `PythonSMMA()` 对齐初始化方式。
2. post_n counter：方向不匹配时重置（direction.py L141-146）。
3. M15 slot2：slot1 失败后扫描 slot2（Python choose_any）。
4. 段合并窗口：120 → 500（动态）。

### P1（4 项）

5. pre_cross：排除 SMA 同根穿越 K 线。
6. M15 rescue：M30 too_wide 时尝试 M15 更近入场。
7. Stage3：判断 good/bad 穿越事件而非 merged_sign 符号。
8. post_n SL：SMMA 对齐后恢复当前 SMA13。

### 性能优化

- PythonSMMA 初始版本 per-tick 高频调用 → 4 小时；
- 优化 1：缓存键从 iTime(shift) → Bars()，去掉 iBarShift；
- 优化 2：大部分 CopyBuffer 回退（UpdatePostNState、M30 信号路径、Stage3、M15）；
- 最终仅 CalcBias55 / CalcBias5 / IsBias5TopPct 使用 PythonSMMA。

### 编译错误清单（已修复）

UpdatePostNState 缺关闭 `}`、InpUseM15Early → InpUseM15EarlyEntry、sma13_now 残留死代码、sma5_arr 未使用变量、IsBias5TopPct 缺 biases 数组声明、Stage3 缺 `if(InpStage3On)` 关闭 `}`、MQL5 声明位置（biases 声明必须在可执行语句前）。

### v3.25 回测问题

- 信号数 37（测试进行中）；post_n = 0 → 根因：UpdatePostNState 用 CopyBuffer(MODE_SMMA) 导致方向检测与 Python 不一致、counter 失控；改回 PythonSMMA（4 calls/bar 可接受）。
- M15 rescue：7 次尝试 0 次成功（待继续调试）。

## 6. EA v3.26：两轮方案审核（2026-07-10 22:35–22:50）

### 第一轮 P0 审核（4 项全部确认）

- **P0-1**：Python "101 信号"是混合口径（ea_executable_diag=True + apply_layer3 静态分位数，非 rolling）→ 必须先选验收口径：A=对齐混合101 / B=对齐纯EA诊断口径。
- **P0-2**：F1 循环 PythonSMMA 性能隐患（缓存键含 period，5/13 交替调用反复全量重算）→ 正确做法：单次 CopyClose 内联计算两套 SMMA 数组。
- **P0-3**：ArrayCopy 取旧段（copy_start=0）会丢 forming bar → 修正 copy_start = _cached_count - out_count。
- **P0-4**：F2 只修时间门不够，slot2 缺父 M30 上下文 → 必须重建 ctx_fast_ma/slow_ma/ma5_curr/ma5_prev/ma13_curr/ma13_prev。

### 第二轮 5 个 P0 判断（全部确认）

1. Baseline 口径混合 → 方案 Step 0 正确处理。
2. F1 索引致命 bug：废弃版 `_cached_fast[4]`=init 但递推从 oi=1 用 `_cached_fast[0]`（未初始化）→ 正确做法：先算完整 full[] 时间轴（full[period-1]=init），再 tail-slice 到 cache[]。
3. OnTick parent_m30_bar 检测不可达（L1758 已把 g_last_m30_bar 更新为 cur_bar）→ TryM15EarlyEntry 内部用 completed_m15_open → iBarShift(M30) 自反推。
4. slot2 ctx_ma5_curr = ctx_fast_ma[n_sma-1] 取到 forming bar → 应为 parent_idx = ctx_n_sma - 1 - parent_m30_shift（slot2 时 = ctx_n_sma - 2）。
5. m15_shift slot2=0 取到正在形成的新 bar → 统一 m15_shift=1。

### 方案产出

- `黄金/30m2H策略/data/validation/EA_v3.26_修复方案_修订版.md`（Step 0 验收口径选择 + F1-F6）
- `黄金/30m2H策略/data/validation/EA_v3.26_修复方案_v2.md`（F1 full[] 时间轴重写、F2 内部反推 m30_shift、F3 post_n SL 单次 PythonSMMA、Step 1.5 验证脚本、编译检查清单 6 项 + 验收指标 7 项 + 文件修改清单 3 处 ~250 行）

## 7. 后续衔接（2026-07-30 补齐）

- 创建过渡版 `data/raw/raw_source_manifest.json`；
- 4 天执行计划：`说明文档/03_验证结果/最终验证补齐执行计划_20260730.md`；
- 状态码：`python_mainline_ready__ea_loaded_evidence_exists__final_trade_ledger_alignment_pending`；
- 基线选择待确认：两个 Python 快照不一致（102 笔 vs 121 笔，PF 11.54 vs 2.96）——顶层快照（推荐）或参考实现工程复跑。

---

*归档日期：2026-08-15 | 来源：.workbuddy/memory/2026-07-09.md、2026-07-10.md*
