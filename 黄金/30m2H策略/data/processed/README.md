# 30m2H 主线处理后数据

## 当前包含

- `m30_standardized.csv`：标准化后的 M30 主行情数据。
- `h2_context_bars.csv`：按决策时点平移后的 H2 上下文数据。
- `m15_context_bars.csv`：用于拆分 M30 Layer2 的 M15 上下文数据。

## 说明

- 这里保留的是策略重算所需的行情与上下文层。
- 候选信号、Layer3 入选信号、最终执行交易另放在 `data/signals`，避免和行情数据混层。
