# 当前主线策略快照

## 固定参数

- Layer 1: `|H2 Bias_55| > 3.0%`
- Layer 2: `pre_cross + cross + post_n(2-6)`
- Layer 3: `Bias_5 top 34%`
- M15: `replace_any + rescue`
- H2: `Layer1 q2 early-gate`
- Stage 1: `2.0R`
- Stage 2: `1.5R trail / 4.0R force`
- Stage 3: `m30_merged_cross`
- stop spec: `[5, 35] pt`
- Layer 3 threshold: `0.372564`

## 当前结果

- 交易数: `128`
- 胜率: `50.8%`
- PF: `2.71`
- EV: `+34.38pt`
- PnL: `$880`
- MaxCL: `7`
- 验证集 PF: `3.19`
- 验证集 EV: `+46.83pt`

## 文件

- `data\results\current_strategy_20260627\current_strategy_trades.csv`
- `data\results\current_strategy_20260627\current_strategy_equity_curve.png`
