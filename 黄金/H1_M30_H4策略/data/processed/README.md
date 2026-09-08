# H1_M30_H4 处理后数据

## 当前包含

- `raw_m30_standardized.csv`
- `30m_bars.csv`
- `1h_bars.csv`
- `4h_bars.csv`
- `h1_m30_h4_context_trades.csv`

## 说明

- 原始 30 分钟数据会先做字段标准化和时间修正。
- 再按策略周期重采样，生成本策略独立使用的 1H / 4H 数据。
- `h1_m30_h4_context_trades.csv` 是后续门测试、止损验证、信号复核的主表。
