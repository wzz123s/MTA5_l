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
- 仓位档位: `0.5/1.0/1.5` = `0.01/0.02/0.03 lot`
- stop spec: `[5, 35] pt`
- Layer 3 threshold: `0.652164`

## 当前结果

- 交易数: `102`
- 胜率: `80.4%`
- PF: `11.54`
- EV: `+107.86pt`
- PnL: `$2200`
- MaxCL: `5`
- 验证集 PF: `19.08`
- 验证集 EV: `+149.67pt`

## 文件

- `data\results\current_strategy_20260627\current_strategy_trades.csv`
- `data\results\current_strategy_20260627\current_strategy_equity_curve.png`
