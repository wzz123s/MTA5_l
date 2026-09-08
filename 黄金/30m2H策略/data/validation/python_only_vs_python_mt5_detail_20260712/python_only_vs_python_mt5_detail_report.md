# Python-only vs Python-MT5 详细对比（2026-07-12）

## 结论摘要
- 这份对比针对旧版 `data/signals_mt5`，对应当前历史里的 Python 调用 MT5 数据版，不是新的 shift90 诊断分支。
- 两版共享输入并不完全一样：M30/M15 原始行情仍共用 base/raw，但 H2 raw 和 processed M30 已切到不同口径。
- `picked_L3` 层：Python-only `118`，Python-MT5 `101`，shared `90`。
- `executed_stage` 层：Python-only `118`，Python-MT5 `101`，shared `90`。
- 交易结果差异不只是信号数不同，shared 交易里的三段 pnl、止损退出类型和 equity 列也会分叉。

## 输出文件
- `data_source_summary.csv`：原始/processed 输入清单与时间范围。
- `m30_calc_diff_summary.csv`、`m30_calc_diff_sample.csv`：M30 processed close/SMA 差异。
- `accepted_L1_L2/`、`picked_L3/`、`executed_stage/`：每层 shared / python_only / python_mt5_only 清单。
- `shared_executed_trade_diff.csv`：shared executed 交易的逐笔 pnl / exit / equity 差异。
- `stop_exit_summary.csv`：两版止损统计。
- `equity_curve_compare_by_index.csv`：按交易序号对齐的资金曲线差异。

## Shared 交易差异摘要
- shared executed 逐笔对比样本数：`90`。
- `total_$` 平均差值：`-1.003920`。
- `total_points` 平均差值：`-5.019601`。
- `stage1_exit` 完全一致比例：`96.67%`。
- `stage2_exit` 完全一致比例：`96.67%`。
- `stage3_exit` 完全一致比例：`96.67%`。

## 止损统计摘要
- Python-only 任一阶段 SL：`95`。
- Python-MT5 任一阶段 SL：`81`。
