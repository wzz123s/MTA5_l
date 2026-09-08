# 30m2H EA 修复记录（v3.28-v3.31）

> 修复时间：2026-08-11 23:38 ~ 2026-08-12 01:40
> 版本：v3.26 → v3.27（安全固化）→ v3.28（stop 段区间）→ v3.29（双闸 Tester）→ v3.30（stage2/3 merged direction）→ v3.31（信号 anchor bar）

---

## 问题

v3.27 Tester 全量回测（2018.01.01-2026.08.11, 每报价, 4分36秒）：

- SIGNAL 122 个（Layer1-3 全部通过，与 Python 128 笔接近）
- **但 trade ledger 0 行** — 所有 Execute 调用 `result=SPEC_FAIL`
- 日志：`real_entry=1395.575 stop_price=1393.143 stop_pts=2.432 result=SPEC_FAIL`

**根因**：EA 计算的结构止损距离仅 1-3 点，全部低于 spec 下限 [5, 35] 点。

## 根因分析

`FindStopSMA()`（v3.17 起）的段定义错误：

```
旧逻辑：seg_start = 最近一次 SMA5/SMA13 cross（当前形成中段的起点）
       极值 = [seg_start, 当前] 内 SMA13 极值
```

**问题**：信号在 cross 时刻触发 → 当前段刚形成（1-2 根 bar）→ 段内 SMA13 极值贴近现价 → stop 距离 1-3 点 → 全部 SPEC_FAIL。

**Python 正确逻辑**（extrema.py）：stop = **上一已完成段**的 SMA13 极值：
- `long_stop = prev_seg_low_sma13`（BUY 用上一 down 段 SMA13 最低）
- `short_stop = prev_seg_high_sma13`（SELL 用上一 up 段 SMA13 最高）
- Python expected ledger：stop 距离 5.02-34.79 单位，全部在 [5,35] spec 内 ✓

## 修复（v3.28）

`FindStopSMA()`：
1. 查找**最近两次** SMA5/SMA13 cross：
   - `seg_start` = 最近 cross（当前段起点）
   - `seg_prev` = 上一次 cross（**上一段起点**）
2. 极值遍历区间 `[seg_prev, seg_start)`（上一完成段）
3. 仅一次 cross（无上一段）→ 返回 0（无法确定 stop）
4. seg_dir 方向逻辑不变（SHORT → MathMax，LONG → MathMin）

## 编译

- v3.28：0 errors, 0 warnings（2026-08-11 23:38）
- 产物：`30m2H_Strategy_EA.ex5`（175,112 bytes）

## 验证计划

- [ ] v3.28 Tester 全量重跑（进行中）
- [ ] SIGNAL 数对比（预期接近 128）
- [ ] ledger 行数（预期 128×3=384 左右）
- [ ] stop 距离分布（预期 5-35 点）
- [ ] 逐笔对齐（compare_python_vs_ea_128.py）
