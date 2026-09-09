# 30m2H 主线 T1 残余专项：post_n 相位 ×3 ＋ stop 边界 ×1（+ extra ×3）

> 2026-09-10｜在 EA 真值/校准 Layer1＋market-closed 剔除口径（64/68=94.12%）下的残余

## 一、现状

| 类 | 明细 |
|---|---|
| missing · post_n 跳段 ×3 | 2020-07-28 07:00、2025-10-17 13:00、2025-10-20 12:00 |
| missing · stop 执行边界 ×1 | 2022-11-08 15:30 |
| extra ×3 | 2020-03-08 post_n6（测试起点）、2021-06-16 post_n6（Python 缺链）、2025-09-09 pre_cross（Python pre_cross 覆盖） |

## 二、post_n 跳段根因

EA 候选序列（Tester 日志）：

- 2020-07-28 SELL：cross → post_n2 → **缺 post_n3/n4** → post_n5
- 2025-10-17 SELL：post_n2 → post_n3 → **缺 post_n4** → post_n5
- 2025-10-20 BUY：post_n2 → post_n3 → post_n4 → **缺 post_n5**

Python 按连续计数输出全部中间 post_n。差异与已确认的 post_n counter 全窗 31 笔起点族不同源，而是**中间 bar 的容量/执行状态**使 EA 未发 Candidate（最大嫌疑：Python MAXPOS 使用自算 exit 时序，EA 使用真实成交 exit，持仓占用轨迹不同）。

## 三、stop 执行边界根因

2022-11-08 15:30 post_n5：EA Candidate/Layer1/Layer3 全过，Stop 按信号 close 计算 ≈34.97 在 spec 内，但 Execute 用真实 ask/bid 20 秒后的价格判出 35.2 >35 → **执行价差约 0.2 点把止损推出 spec**。

## 四、建议处理

1. **post_n 跳段（3+部分 extra）**：做"EA 真实持仓占用 vs Python MAXPOS 轨迹"diff——对这三段用 EA ledger open/exit 重放 Python 候选，确认缺段是否为 EA 仍有持仓导致；若是，则 Python 端修 exit 时序/占用模型，预计同时影响 extra 2021-06-16。
2. **stop 边界（1）**：在验收/对齐口径中把 `stop_pts` 比较统一到“信号 close 口径”，并把 EA Execute 的执行价边界视为 ±1 tick 允许带（EA 的 35.2 由执行滑点造成，不构成信号层差异）。
3. **extra 起点/pre_cross（2）**：2020-03-08 归入测试起点历史族（与 post_n 31 同源）；2025-09-09 pre_cross 等待 Python pre_cross 已归零口径并入候选后自然消失。

## 五、预期

若上述 1/2 落地：missing 3（相位）＋1（stop）可转为“已解释差异或剔除”，extra 2 消除，验收率可到 **64/64~100%（±120）** 或按已知差异口径固化。
