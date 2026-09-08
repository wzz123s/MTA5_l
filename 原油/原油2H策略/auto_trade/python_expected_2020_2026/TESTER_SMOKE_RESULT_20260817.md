# USOIL2H CrossConfirm EA Tester 冒烟结果（2026-08-17）

## 结论：EA 逻辑与 Python 参考实现一致 ✅（40/40）

自动执行 Tester 冒烟（无需手动点击 Start）：USOIL2H_CrossConfirm_EA，USOILm H2，
1分钟OHLC，2020.01.01–2026.08.15，入金 500，杠杆 1:2000。

| 指标 | 结果 |
| --- | --- |
| Python 期望交易 | 40 |
| EA 交易 | 54（40 matched + 14 extra） |
| matched | **40/40** |
| missing_in_ea | 0 |
| pnl sign agree | **40/40** |
| pnl diff > 0.01 | **0** |

40 笔期望交易的 signal_time 与 EA 逐笔精确一致（秒级），pnl 差异均为浮点误差（1e-6~1e-15）。

## 过程中发现并修复的 EA bug（v4）

`ProcessOpenTrades` 的 bar 索引原为 `idx = (n-2)-(age-1)`，随持仓年龄增大**往回**取 bar，
导致大部分持仓永远检查不到新 bar 而无法退出（v3 冒烟：23 开 3 平）。
修复为恒取最新收盘 bar `idx = n - 2`（v4，2026-08-17 19:34 部署）→ **54 开 54 平**。

## 14 笔 extra 说明（数据生成差异，非逻辑错误）

MT5 1分钟OHLC 模式生成的 H2 bar 序列（16262 根）与 Python 数据源（同为 16262 根）
总量一致，但**早期时段（2020–2021）CopyRates 返回稀疏 bar**，EA 检测到 Python 台账中
没有的 14 个额外信号（全部为 BUY、全部 SL hit 退出）。这些 extra 不改变 40 笔期望交易
的匹配结论；若需严格 40/40 无 extra，需进一步核对 MT5 历史数据完整性（M1 缓存）。

## 入场时间精度核对（2026-08-17 补充）

对 40 笔 matched 逐笔核对 signal_time → entry_time 间隔：

| 间隔 | 笔数 | 说明 |
| --- | --- | --- |
| 4 小时（= bar+3 开盘） | 32 | 与 Python 语义精确一致 ✅ |
| 52 小时 | 5 | 周五收盘信号 → 下周一开盘，正常跨周末 ✅ |
| 94 小时 | 1 | 2020-10-09 唯一异常（2020 年 M1 数据缺失）⚠️ |

结论：**2021 年起 EA 入场时间与 Python 的 bar+3 完全一致**；唯一偏差是 2020-10-09，
根因见下。

## 2020–2021 M1 数据缺失（服务器端限制，无法本地补齐）

检查终端历史缓存 `bases\Exness-MT5Trial5\history\USOILm\`：

- `2020.hcc` 仅 92 KB（稀疏），`2019.hcc` 83 KB；**2021 起完整**（10–21 MB/年）。
- cache 目录无 `M1.hc`（无 M1 缓存），只有 M15/M30/H1/H2/H4/H6。
- 用临时 EA（CopyRates 分块请求 2019→now 的 M1/M30/H2）强制下载 2 分钟，
  `2020.hcc` 时间戳/大小无变化 → **Exness 服务器端没有 USOILm 2020 年 M1 历史**。

因此 1分钟OHLC 模式下，2020–2021 期间 MT5 只能用稀疏数据生成 H2：

- 2020-10-09 入场延迟 94h（bar 计数在稀疏序列上推进慢）；
- 14 笔 extra 也是稀疏序列产生的额外信号。

这不是 EA 逻辑问题（2021+ 全部精确），如需严格全区间 2020–2026 验证，
需换用有完整 2020 M1 历史的服务器/经纪商重新拉数，或接受 2021–2026 的精确段结论。

## 输出文件（更新）

- `tester_vs_python_detail.csv`（40 笔逐笔对照，含 entry_time 供入场时间核对）
- `tester_vs_python_missing.csv`（空 = 无缺失）
- `tester_vs_python_extra.csv`（14 笔 extra 明细）

## 输出文件

- `tester_vs_python_detail.csv`（40 笔逐笔对照，pnl_diff 全 < 0.01）
- `tester_vs_python_missing.csv`（空 = 无缺失）
- `tester_vs_python_extra.csv`（14 笔 extra 明细）

## 实盘状态

- v4 ex5/mq5 已部署到 DAD3B8CC 终端，实盘 chart05（USOILm）19:35:30 加载成功。
- 冒烟结论已回写 `部署报告_USOIL2H_CrossConfirm_EA_20260816.md`（问题 3 / v4 / 结论）。

---

## 2021–2026 全精确区间复跑（2026-08-17 20:28）

按建议单独复跑 2021.01.01–2026.08.15（USOILm H2，1分钟 OHLC，入金 500，杠杆 1:2000），
避开 2020 年 M1 数据缺失，获得"全精确区间"结论：

| 指标 | 结果 |
| --- | --- |
| Python 期望交易（2021+ 过滤） | **39**（全部为 L/多单） |
| EA 交易 | 53（39 matched + 14 extra） |
| matched | **39/39** |
| missing_in_ea | **0** |
| pnl sign agree | **39/39** |
| pnl diff > 0.01 | **0** |

39 笔期望交易的 signal_time/dir 与 EA 逐笔精确一致，pnl 差为浮点误差（< 1e-6）。
EA 端 53 笔全部为 BUY、39 笔止损、16 笔反向穿越退出；净 pnl ≈ +294.97 USD（虚拟余额 500→794.97）。

### 14 笔 extra 归因修正（重要）

本次 14 笔 extra 与 2020–2026 复跑中的 14 笔**逐笔相同**（signal_time|dir 完全一致），
且全部位于 **2023–2026**（如 2023-05-29、2024-04-11、2024-04-16、2024-08-15、2024-12-23、
2025-04-25、2025-05-16、2025-11-24、2025-12-18、2026-02-16、2026-04-16、2026-06-30、2026-07-03），
全部为 BUY / SL hit（单笔 -0.12 ~ -0.73 pt）。

→ 之前"14 笔 extra 是 2020–2021 稀疏数据产生"的归因**不成立**：
extra 是 EA 与 Python 之间的系统性差异（很可能源于 MT5 1分钟OHLC 重建的 H2 bar 与
Python 数据源 H2 在个别时点 bar 边界/收盘价上的细微差异，导致 EA 多检测到少量金叉信号）。
EA 与 Python 的确认阈值（≥0.5）、入场（bar+3）、止损逻辑一致，matched 全对；
差异集中在"同一时刻 Python 未检测到交叉"的少量多头信号上，且这些信号全部亏损，
使 EA 模拟净值略低于 Python 期望。

### 结论

- **2021–2026 干净区间：EA 逻辑与 Python 完全一致（39/39，pnl 零误差）。**
- extra 问题与数据缺失无关，是跨年恒定的少量多检测（14 笔，全部小亏）；
  如需消除，可进一步对齐 MT5 H2 重建与 Python 数据源在 bar 收盘价/时间戳上的差异，
  或直接在 EA 侧复现 Python 的交叉判定条件。

### 输出文件（2021 区间）

- `tester_vs_python_detail_2021.csv`（39 笔逐笔对照，含 entry_time/reason）
- `tester_vs_python_missing_2021.csv`（空 = 无缺失）
- `tester_vs_python_extra_2021.csv`（14 笔 extra 明细）
- EA 台账副本：`C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\USOIL2H_crossconfirm_trade_ledger.csv`

---

## 14 笔 extra 根因定案 + 因果对齐（2026-08-17 21:45）

### 根因：Python 参考实现存在 lookahead（未来数据）

逐笔诊断 14 笔 extra 后确认：

- 14 笔 extra 的交叉 bar、止损（上一段 SMA13 极值）在 Python 数据上**完全一致**；
- 差异只在确认值：EA 的 way_s_way = 1.00/0.50，Python 全序列 = 0.15–0.45；
- 用"截止到确认 bar 的窗口（[0..i+2]，无未来 bar）"重算，14 笔全部得到 EA 的值 1.00/0.50。

原因：Python 参考在整段历史上跑 `filter_short_segments(min_len=8)`，会用**未来交叉**把
短段（<8 根）合并掉，回溯改写当前段的 way/vol_way——即 lookahead。EA 是因果实现：
确认时当前段尚未结束，不知道它将来是否会被合并，因此按原始段计数。

结论：**EA 行为正确（可实盘实现）；Python 参考的 40 笔期望台账含 lookahead 偏倚**
（它"提前知道"哪些段会变成短段而被合并，从而过滤掉了 14 笔本会亏损的交易）。

### 修复：Python 验证新增因果变体 `cross_confirm_causal`

`validate_usoil_2h_standalone.py` 新增 `causal_confirm_values()`（窗口 [0..i+2] 计算确认值）
与 `cross_confirm_causal` 变体。结果：

| 变体 | n（2020–2026） | PF | EV(pt) | test PF | wf_test | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| cross_confirm（原，lookahead） | 40 | 2.193 | +0.39 | 2.380 | 2.837 | 含未来偏倚 |
| **cross_confirm_causal（对齐）** | **54** | **1.501** | **+0.18** | **1.261** | **1.703** | 与 EA 一致 |

因果版（即真实可交易口径）性能明显低于 lookahead 版：PF 2.19 → 1.50，WF test 2.84 → 1.70，
但仍为正（4/7 正年份）。之前"PF 2.19"的结论需要按此修正。

### 对齐后 Tester 对比（2021–2026）

用因果期望（2021+ = 53 笔）对比 EA 台账（53 笔）：

| 指标 | 结果 |
| --- | --- |
| matched | **53/53** |
| missing_in_ea | **0** |
| extra_in_ea | **0** |
| pnl sign agree | **53/53** |
| pnl diff > 0.01 | **0** |

**EA 与 Python（因果口径）完全一致，14 笔 extra 全部成为双方共同的期望交易。**

### 同步改动

- EA `USOIL2H_CrossConfirm_EA.mq5`：默认 `InpHistoryBars 600→20000`，且改为
  `Bars()` 全历史加载（保证因果合并段计算稳定）；编译 v5（0 errors）并部署到 DAD3B8CC 终端。
- `.set`（终端 Profiles\Tester 与 SimDeployment）同步 `InpHistoryBars=20000`。
- `raw_source_manifest.json` 修正过期的 H2/M30 路径（补 `原油\` 层级）。
- 新增输出：`python_expected_usoil2h_crossconfirm_causal_2021_2026.csv`、
  `tester_vs_python_causal_detail_2021.csv` / `missing` / `extra`。

### 实盘提示

实盘 EA（chart05）运行的是因果口径，与 Python 因果参考一致；实盘信号数应约等于
因果验证的交易数（2021+ 53 笔），而不是 lookahead 口径的 40 笔。
