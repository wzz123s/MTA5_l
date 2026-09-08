# BiasReversal_Combo_EA BUG 审查报告（乖离反转，TODO-3 第一站）

> 审查：2026-09-06 ｜ EA：黄金\乖离反转策略\auto_trade\BiasReversal_Combo_EA.mq5（684 行，真实下单，多空双分支）
> 参考：backtest_v6b_combined.py（最新组合回测源）、replay_1h_way_momentum_filter_scan.py（add_way_grade/filter_short_segments_causal）

## EA 架构（先厘清，避免误判）
- 做多（默认，InpLongMode=0）：6H bias5&bias55>0 门 + **H1** SMMA5 金叉（代码已注明改用 H1，PF 2.19 vs M30 1.57）→ 当前价开多；SL 1.2% / TP 3R / H1 死叉平仓。
- 做多镜像（InpLongMode=1）：H4 超跌门 + 2H down 段结构（Check2HLongSetup）。
- 做空（InpEnableShort=false 默认关）：H4 超涨门 + 2H up 段 SMA13 涨幅 ≥3% + way/vol_way 极值（Check2HShortSetup，R3）。
- 实盘持仓按 magic 现查管理，无内存仓状态；台账句柄保持打开（BUG-05/BUG-12 风格）。

## 审查发现

### A.【口径·高】段扫描未做短段合并，与 Python 方向_合并后不一致
- EA Check2HShortSetup/Check2HLongSetup 用 **raw S5/S13 交叉**直接切段（每个 raw 交叉都翻转 up/down）；
- Python（v6b + add_way_grade）用 **方向_合并后**（filter_short_segments_causal, min_len=8）——短段被吸收后段边界/段内 way 计数不同。
- 影响面：仅 InpLongMode=1（镜像做多）与 InpEnableShort=true（做空）分支；默认主做多路径（H1 金叉）不经过段逻辑。
- 处置：不静默改（会改变未复核分支行为），列为"若启用 short/mirror 前须先统一段合并口径并对齐 python"。

### B.【确定 BUG·已修】vol_ma 注释"MA120"实为窗口前缀累计均值
- 两处（Check2HShortSetup / Check2HLongSetup）均为 `vsum/cnt` 自窗口 0 起累计，与注释及 Python `vol_ma_120=rolling(120,min_periods=1).mean()`（含当前 bar 前 ≤120 根尾随均值）不符 → vol_way_s_way（z 计数）被系统性算错。
- 修复：改为尾随滚动 120（含当前 bar，前 120 根滑出）；两函数均已改，编译 **0 errors（4 warnings 旧有）**。
- 影响：做空/镜像做多的 vwsw≥InpWThr 判定会随之变化；主做多路径不受影响。

### C.【口径·低】段首 bar 的 way 计数与 Python 不同
- Python add_way_grade 在每段首 bar 无条件 x=1（up 段）或 x=-1（down 段）；
- EA 在段首仍按 `low>=s13 && high>=high[i-1]` 等条件与**前一段末 bar**比较计数。
- 短段/紧邻反转场景下 wsw 会略有差异；多数段内中部计数一致。建议后续统一时按 Python 语义修正。

### D.【Python 参考侧 BUG】v6b short_side 的 H4 state 单调置 1 不回落
- `state[cond]=1` 从不置 0 → 一旦某 H4 bar 满足超涨门，之后所有时间做空资格恒为 true（python 数字可能高估做空机会）。
- EA RefreshGates 每 H4 bar 重算是正确的。若后续做 EA↔Python 做空侧对齐，**先修 python state 回落**再比。

### E.【口径·文档】EA 做多信号已切 H1 金叉，v6b python 仍为 M30 金叉
- EA 头注与 v6b long_side 均为 M30 金叉描述/实现，EA 代码实际用 H1（注释说明 PF 2.19 vs 1.57）。
- 需要确认 08-27 研究用的 H1 金叉 python 基线（v5b_long_side/v5c 之外可能另有）以作未来对账；不影响 EA 自身默认运行。

### F.【次要·无碍】TP 双保险 / 冷却归类
- Manage* 每 tick 用 forming bar high/low 判 TP（server TP 已挂 3R，双保险一致）；
- 金叉平仓也走 UpdateShortCooldown（P2-3 已按实际盈亏区分 SL/TP），冷启动分类边界可接受。

### G.【无】索引方向 / 出场时间轴冻结 / 台账句柄 / OnTick 顺序
- 未发现 ABC 家族的 idx 冻结、raw/merged 混用、入场晚 1 bar 等同类问题（此 EA 实盘结构不同，管理均按 magic 现查）。

## 已落地
- B 修复（vol_ma 尾随滚动 120 ×2），编译 0 errors；.ex5 已同步至 DAD3 Experts\Advisors（未动实盘图表，重载由用户决定）。
- 本报告 + 主问题记录 §十六 归档。

## 建议（如需继续此策略）
1. 若长期默认（LongMode=0, EnableShort=false）不变 → 本次 B 修复即可收尾；A/E 仅影响未启用分支。
2. 若要启用做空/镜像 → 先按 A/D/E 统一 EA 与 Python（段合并因果版 + H4 state 回落 + H1 金叉基线），再做 Tester 逐笔对齐（复用 A1/A2 流水线）。
