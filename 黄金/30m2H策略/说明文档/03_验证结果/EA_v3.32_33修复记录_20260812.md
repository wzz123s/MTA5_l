# 30m2H 对齐迭代记录 — 2026-08-12（第 8 轮：post_n 滚动合并 + M15 分发重构）

> 收尾时间：2026-08-12 20:30（进行中）

---

## 一、本轮发现的根因（3 个）

### 1. post_n 全量合并含 look-ahead（Python 侧）

**现象**：expected post_n 94 笔 vs EA post_n 48 笔，交集仅 19 笔。

**根因**：Python `processing/segment_filter.py filter_short_segments_v2()` 对**整个历史**一次合并（吸收链用到未来穿越点）；EA 的 `M30MergedDirectionCodeLastCompleted()` 是滚动语义（实时末段穿越点永远保留）。两者 merged 方向 26.8% bar 不一致（645 段）。

**修复**：`_current_baseline.py` 新增 `rolling_merged_postn(df, window=500)`（复刻 EA 算法），`build_final_accepted(rolling_merged=True)` 覆盖 `merged_post_cross_n` + `方向_合并后`。expected 137 → **156 笔**，对齐容差匹配 150 → **177**。

### 2. strict_post_n 双检 bug（EA 侧）

**现象**：SKIP_STRICT_MERGED_POSTN 日志 9807 次 — EA 大量 post_n 信号被拒。

**根因**：`g_merged_strict_post_n_counter` 一旦因"方向不匹配"被清零（strict_last=0），后续 merged 翻转（发生在吸收后的 state bar，merged_code=±1 非 ±2）不会重置它 → **永久死亡**。Python 无 strict 概念。

**修复**：v3.33 删除 M30 close 路径的 strict_post_n_ok 检查块。

### 3. M15 slot1 独立触发（EA 侧，信号异源）

**现象**：EA M15 44 笔 vs Python M15 48 笔，精确匹配仅 5 笔（entry_diff 0.1-6 点）。

**根因**：EA slot1 在 M30 bar 进行中（15min 时点）用**实时数据**独立判定信号 + 用 15min 时点价入场；Python M15 replace = M30 收盘信号 + 信号 bar close 价入场。两边信号判定输入和入场价格都不同。

**修复**：v3.32 `InpUseM15EarlyEntry = false` 默认（slot1 独立触发禁用）→ 所有信号统一走 M30 close 路径（信号同源、entry = close 价）。

## 二、时间语义验证结论（本轮确认）

- 两侧 `signal_anchor_time` = 信号 M30 bar 的 **open 时间**（96/96 matched 零差异）
- Python entry = 信号 bar **close 价**（信号确定时刻市价）
- EA entry = 信号 bar 收盘后 1 tick 的 market fill（≈ close 价 + 0.3 点滑点）
- M15 SLOT1 入场价 = M30 close 入场价（144/144 零差异验证）→ 对齐脚本不比较 open_time/trigger_tag，M15/M30 标签不影响匹配

## 三、v3.33-3.36 修改清单

| 版本 | 改动 | 状态 |
|------|------|------|
| v3.32 | `InpUseM15EarlyEntry = false` 默认（slot1 禁用） | 编译 ✓ |
| v3.33 | 删除 strict_post_n_ok 检查（3807-3825 行） | 编译 ✓ 0 errors |
| v3.34 | **FindStopSMA → Python prior_segment_stop 语义**（当前段：最近穿越点起 SMA13 极值；v3.28 上一段是 0/43 错配） | 编译 ✓ |
| v3.35 | **硬移除 M15 slot1 触发调用 + M30 close 路径 M15 rescue 块**（面板缓存 InpUseM15EarlyEntry=true 会覆盖默认值 → 直接删调用点最可靠） | 编译 ✓ 0 errors |
| v3.36 | **CalcBias55EarlyQ 对齐 Python**：prev_sma55 shift 2→1（刚收盘 H2）+ elapsed_q 语义（距上一根 H2 的 M30 数，无 +1） | 编译 ✓ 0 errors |

### Python 侧 v3.36 配套修改（模式判定层对齐）

1. **移除三个 collect 的"出场搜索失败丢弃"过滤**（pre_cross/cross/post_n）— 这是 look-ahead（用未来 merged 方向判断信号有效性），EA 实时无法复刻 → 改为数据末尾兜底
2. **cross 信号 entry：典型价 → close**（EA 可执行口径，`ea_mode` 参数）— Python 用 (high+low+close)/3 与 EA 市价相差大 → spec 边界翻转（例：22:30 cross Python sd=4.26 too_tight vs EA 6.5 合规）
3. **Layer3 阈值样本不含当前 H2 bar**（EA IsBias5TopPct 用 CopyClose(H2,1,n)）

### 归因结论（模式判定层深挖）

- **Layer3**：交集 338 信号判定 100% 一致 ✓（bias5 值也完全一致，0.32241 实证）
- **Layer1**：722 中 674 PASS 一致（93%），48 个差异 → early gate 修复（v3.36）
- **spec 层**：117 SPEC_FAIL 仅 4 个对应 expected → stop 已对齐；354 个 too_tight/wide 是两边一致拒绝（非差异）
- **MAXPOS**：EA InpMaxPos=3 持仓限制（Python 无）→ expected 加模拟（156→81 笔）；剩余 15 笔差异 = stage 平仓 tick 级时序（固有误差）
- **周界数据**：2020-03-08 等休市后信号（EA 判定时刻 H2 数据 vs Python 休市前）→ 1-2 笔固有差异

编译产物：`30m2H_Strategy_EA.ex5`（156,428 bytes, 2026-08-12 21:42）
