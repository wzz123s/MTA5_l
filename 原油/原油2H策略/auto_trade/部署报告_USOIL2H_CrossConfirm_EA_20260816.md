# USOIL2H CrossConfirm EA 部署报告（2026-08-16）

## 部署内容

新 EA：`USOIL2H_CrossConfirm_EA`（原油 2H 独立策略，Python 验证 cross_confirm 变体移植）

| 项目 | 值 |
| --- | --- |
| 触发 | 2H SMMA5/SMMA13 金叉/死叉（raw good/bad bar） |
| 确认 | 叉后连续 2 根 bar 的 way_s_way 与 vol_way_s_way 同向均 ≥0.5（合并段口径 min_len=8） |
| 入场 | 叉后第 3 根 bar 开盘（i+3 open） |
| 止损 | 上一段（raw 叉）SMMA13 极值；距离 0.1%–1.0%（价格百分比） |
| 出场 | 单段：止损（开盘跳空→低/高触碰）或反向 raw 叉 → 下一根开盘 |
| 风险 | 1% 虚拟余额（$500 起） |
| Magic | 362036 |
| 模式 | SimMode=true / AllowRealTrading=false |
| 输出 | `USOIL2H_crossconfirm_signals_export.csv`、`USOIL2H_crossconfirm_trade_ledger.csv` |

## 验证状态

- ✅ 编译 0 errors / 1 warning（tick_volume long→double，无害）：`compile_usoil2h_v1.log`
- ✅ 文件复制：`MQL5\Experts\Advisors\USOIL2H_CrossConfirm_EA.ex5/.mq5`、`MQL5\Presets\USOIL2H_CrossConfirm_SimDeployment_EA.set`
- ✅ chart05（USOILm 槽位）注入 EA；原文件备份 `chart05.chr.bak_20260816_usoil2h`
- ✅ 加载日志：`expert USOIL2H_CrossConfirm_EA (USOILm,H1) loaded successfully`
- ✅ OnInit 表头生成：signals CSV（65 B）+ ledger CSV（111 B）
- ⏳ 交易输出：周六休市，周一开盘后 EA 开始逐 bar 处理，信号/成交写入 CSV

## 对齐口径

- Python 基准：`validate_usoil_2h_standalone.py` cross_confirm（40 笔 / PF 2.19 / 样本外 2.38 / walk-forward 1.39→2.84）
- 已知口径差异：Python 验证中"数据末尾无反向叉"的交易被丢弃（数据产物），EA 实盘持仓会保持到反向叉出现（正确实盘行为）
- 下一步建议：周一后跑一次 Strategy Tester 冒烟（2020–2026，期望约 40 笔），与 Python cross_confirm_trades.csv 逐笔对齐核对

## 回滚

关闭 MT5 → 用 `chart05.chr.bak_20260816_usoil2h` 覆盖 chart05.chr → 重启。

---

## 2026-08-17 修复记录（v2/v3）

### 问题 1：跨周末候选计时失效（v2 修复）

- 现象：实盘首日（周一 06:01）EA 捕获周五 22:00 金叉并写入 CONFIRM_WAIT，但候选入场用墙钟时间（cross_close+4h），
  跨周末后周一 bar 时间远大于该值，候选被静默丢弃。
- 修复：候选计时改为 **bar 计数**（age），不依赖墙钟时间。

### 问题 2：age 阈值 off-by-one（v3 修正，2026-08-17 08:26 部署）

- 现象：v2 把入场设在 age==3，但按 Python 语义（信号 bar 收盘 02:00 → 确认 bars 04:00/06:00 收盘 → 入场 bar i+3 于 06:00 开盘）
  入场应为 **age==2**；v2 会晚一根 bar 入场。
- 修正：`if(g_cands[c].age == 2)`；已重新编译（v3，0 errors）并部署，实盘 08:26 加载成功。

### 问题 3：持仓退出索引错误（v4 修正，2026-08-17 19:34 部署）

- 现象：Strategy Tester 冒烟（2020–2026，1分钟OHLC）发现 **23 笔开仓、仅 3 笔退出**，虚拟余额停在 500。
- 根因：`ProcessOpenTrades` 中 `idx = (n-2)-(age-1)` 随 age 增大**往回**移动索引，
  检查的是越来越旧的 bar，而不是持仓之后的新 bar → 大部分持仓永不触发止损/反向叉。
- 修正：改为恒检查最新收盘 bar `idx = n - 2`（每次 OnTick 的 rates[n-2] 自动随时间推进指向新 bar）。
- 验证：重新跑 Tester（2020–2026，1分钟OHLC）→ **54 笔开仓、54 笔退出**，
  Python 对比 **matched 40/40、missing 0、pnl sign 40/40、pnl diff>0.01 = 0**；
  另有 **14 笔 extra**（MT5 1分钟OHLC 生成的 H2 bar 序列与 Python 数据源在稀疏时段存在差异，
  产生 Python 台账中没有的额外信号——非逻辑错误，属数据生成差异，待数据完整性核对）。
- 部署：v4 ex5/mq5 已复制到 DAD3B8CC 终端；实盘下次加载后生效。

### 结论（2026-08-17 冒烟）

- EA 逻辑与 Python 参考实现一致：40 笔期望交易逐笔匹配（signal_time 精确一致、pnl 浮点误差内一致）。
- 需注意：1分钟OHLC 模式下 MT5 生成的 H2 bar 在早期时段较稀疏（2020–2021），
  信号→入场存在 bar 计数延迟；该特性影响入场时间精度，建议后续核对 MT5 历史数据完整性。

### 结论

- 周五 22:00 信号在修复前已被丢弃，实盘不再追溯（符合无前视原则）；该信号是否正确将由 Tester 冒烟对照 Python 期望台账验证。
- 当前实盘 EA = v3（bar 计数 + age==2），后续信号（含未来跨周末叉）按正确时序处理。

---

## 2026-08-17 21:45 更新（v5 + 因果对齐结论）

### 变更（v5）

- `InpHistoryBars` 默认 600 → 20000，并在 OnTick 中改用 `Bars()` 加载全部可用 H2 历史，
  使合并段 way/vol_way 计算不受窗口截断影响（编译 0 errors，已部署到 DAD3B8CC 终端 Experts\Advisors）。
- `.set`（终端 Profiles\Tester + SimDeployment）同步 `InpHistoryBars=20000`。

### 关键结论：14 笔 extra 是 Python 参考的 lookahead，不是 EA 问题

经逐笔诊断（详见 `python_expected_2020_2026/TESTER_SMOKE_RESULT_20260817.md`）：

- EA 的 14 笔 extra（全 BUY/止损）在 Python 数据上交叉与止损完全一致；
- Python 全序列 `filter_short_segments(min_len=8)` 会用未来交叉合并短段（lookahead），
  使确认值偏低（0.15–0.45）而拒绝；EA 因果实现（确认时当前段未结束）按原始段计（1.00/0.50）而接受；
- 验证脚本新增 `cross_confirm_causal` 变体（窗口 [0..确认bar]，无未来），与 EA 完全一致：
  **2021+ 因果期望 53 笔 = EA 台账 53 笔，53/53 匹配、0 missing、0 extra、PnL 零误差**。
- 因果口径（真实可交易）PF ≈ 1.50（2020–2026, 54 笔），低于原 lookahead 口径的 2.19（40 笔）；
  实盘应按因果口径预期交易数与绩效。
