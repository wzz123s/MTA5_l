# EA v3.35 修复与部署记录（2026-09-01）

> 收尾时间：2026-09-01 20:5x（部署完成）
> 关联：`合并方向对齐立项_20260901.md`（合并方向评估，决策：维持现状）、`部署报告_30m2H_Strategy_EA_20260901.md`

---

## 一、背景：2026-09-01 11:30 逆势开单事故

实盘模拟盘（277752085）2026-09-01 11:30（UTC）出现：

- EA 在 H2/M30 均为空头结构（H2 BEAR、M30 SMA5 4388.29 < SMA13 4410.56）时开出 **post_n2 BUY** 三腿（302037/38/39 @4380.573）；
- 1 秒后 EA 自平 S2/S3（`stage2_merged_cross` / `stage3_cross_exit`，各 -0.40 = 点差），S1 遗留逆势持仓；
- 平仓单 magic=0（CTrade 未设 expert magic），归因混乱。

## 二、根因（EA 侧，已确认）

`UpdateMergedPostNState()` 首次调用分支（源码第 2681 行）：

```mql5
if(g_merged_last_dir == 0)
{
   // First call
   g_merged_post_n_counter = 1;   // ← BUG：符号写死 +1
   g_merged_last_dir = merged;
}
```

EA 重启/重载后 `g_merged_last_dir=0`，首次调用在**空头市场**把计数器记成 +1（应为 -1），
下一根同向 bar 递增到 +2 → 触发逆势 post_n2 BUY。信号方向只信计数器符号（OnTick 3849-3858），
退出逻辑用实时重算的真实合并方向（空头）→ 立即平掉 S2/S3。

旁证：`M30MergedDirectionCodeLastCompleted` 与参考 `filter_short_segments` 逐 bar 前缀对比 **0/250 一致**，
移植无误；`signal_stop=4410.56 > entry=4380.73`（BUY 止损在错误一侧）进一步确认方向错误。

## 三、修复清单（4 处 BUGFIX，源码 `auto_trade/30m2H_Strategy_EA.mq5`）

| # | 位置 | 修复 | 目的 |
|---|------|------|------|
| 1 | L2686（UpdateMergedPostNState 首调） | `g_merged_post_n_counter = 1` → `(merged > 0) ? 1 : -1` | 主修：计数器符号对齐真实合并方向 |
| 2 | L3902（OnTick 信号段） | post_n 最终信号与 `M30MergedDirectionLastCompleted()` 复核，冲突 → `DIR_MISMATCH_SKIP`；仅限 post_n（`!is_pre_cross_mode && !is_cross_mode`），避免误杀 pre_cross/cross | 加固：方向二次核对 |
| 3 | L1171（OnInit） | `g_trade.SetExpertMagicNumber(InpMagic)` | 平仓/移止损单不再 magic=0 |
| 4 | L2876（ExecuteSignalByMarket） | 止损方向校验：LONG 需 stop<entry、SHORT 需 stop>entry，否则 `STOP_WRONG_SIDE` 拦截 | 防御：post_n SMA13 止损在错误一侧时拒单 |

## 四、编译与验证

- 编译：MetaEditor 命令行 **0 errors, 0 warnings**（含 Fix 2 修订版二次编译）；ex5 已生成于 auto_trade。
- 旧文件备份：`30m2H_Strategy_EA.mq5/.ex5.bak_v335_prebugfix_20260901`。
- Python 对齐（2018-03 ~ 2026-09，100,001 根 M30）：
  - EA 修复版 post_n 候选 ⊆ 参考候选：**3627/3627（100%）**；
  - snapshot（trades_snapshot.csv）post_n 93 笔 ⊆ 参考候选：True；
  - 重启场景（09-01 10:30 重置计数器）：修复版 → post_n2 **SELL**（与参考一致）；旧版 → post_n2 BUY（side_ok=False，即当天错单）。
- 合并方向评估（见 `合并方向对齐立项_20260901.md`）：门前 1197 笔多余候选经 H2 门后仅剩 6 笔；
  延迟吸收（EA_DELAY）回测 PF 2.045 < 现状（EA_CUR）2.287 → **不采纳，维持无前视近似**。

## 五、部署（2026-09-01 20:51）

- 复制 `auto_trade/30m2H_Strategy_EA.ex5`（154,162B，编译于 12:15:43 UTC）→ 终端
  `MQL5\Experts\30m2H_Strategy_EA.ex5`；旧版备份 `.bak_v335_prebugfix_20260901`。
- 终端重启：**explorer 托管**（`explorer.exe terminal64.exe`）——Start-Process 直启会随沙箱进程退出被杀。
- 验证：20:51:26.848 `expert 30m2H_Strategy_EA (XAUUSDm,M30) loaded successfully`；
  账户 277752085 授权成功，2 持仓完好（1H_M30_4H SELL + 30m2H S1 BUY）。
- 运行模式不变：chart07 输入（InpMagic=302036、InpCheckSec=1、InpSimMode=false、InpAllowRealTrading=true）。

## 六、观察项（模拟盘，后续在进度文档跟踪）

1. post_n 方向是否与 M30 结构一致（重启/重载场景重点）；
2. `STOP_WRONG_SIDE` / `DIR_MISMATCH_SKIP` 是否出现及合理性；
3. 平仓单 magic 归因是否清晰（不再 magic=0）；
4. 遗留的旧版逆势 S1 多单（302037 @4380.573）离场是否正常。
