# 30m2H 数据层说明

这个目录是 `30m2H策略` 的“标准数据入口层”。

目标：

- 让别人知道每一层数据是什么角色。
- 让别人知道数据应该怎样从上游流到下游。
- 让其他策略复制本目录时，不会把原始数据、中间表、信号结果、验证结果混在一起。

## 推荐数据流转

1. `raw`
   - 放原始行情和上游来源说明。
2. `processed`
   - 放标准化后的中间表。
3. `signals`
   - 放 Python 主线信号结果。
4. `signals_mt5`
   - 放基于 MT5 数据或 MT5 对齐版本的信号结果。
5. `signals_mt5_shift90_*`
   - 放特定变体或实验版信号结果。
6. `validation`
   - 放验证分析、差异定位、核对报告和证据包。

## 分层职责

- `raw`
  - 输入层。
  - 典型文件：
    - `XAUUSDm30.csv`
    - `XAUUSDm15.csv`
    - `H2_XAUUSDm_39col.csv`
    - `full_data_30m2h.csv`
  - 这里的数据尽量保持“来源明确、少加工”。
- `processed`
  - 中间层。
  - 典型文件：
    - `m30_standardized.csv`
    - `m15_context_bars.csv`
    - `h2_context_bars.csv`
    - `m30_mt5.csv`
  - 这里的数据是信号脚本的直接输入。
- `signals`
  - Python 主线输出层。
  - 典型文件：
    - `候选信号_Layer1_Layer2通过.csv`
    - `最终信号_Layer3入选.csv`
    - `执行交易_Stage结果.csv`
- `signals_mt5`
  - MT5 数据对齐版本输出层。
- `signals_mt5_shift90_*`
  - 实验、变体、修复版输出层。
  - 保留版本后缀，避免覆盖主线结果。
- `validation`
  - 审计与验证层。
  - 可以放：
    - 差异分析报告
    - 对齐结果
    - 时间语义核对
    - 证据包
    - 手工确认材料

## 命名建议

- 原始层：
  - 用交易品种和周期命名。
- 中间层：
  - 用“周期 + 语义”命名，例如 `m30_standardized`、`h2_context_bars`。
- 信号层：
  - 用“阶段 + 结果”命名，例如 `候选信号_*`、`最终信号_*`、`执行交易_*`。
- 验证层：
  - 用“主题 + 日期”命名，例如 `*_20260714`。

## 给其他策略复用时

建议直接复制这套骨架：

```text
data/
  raw/
  processed/
  signals/
  validation/
```

如果有 MT5 或多版本对齐需求，再增加：

```text
data/
  signals_mt5/
  signals_mt5_<variant>/
```

## 最终标准

- `raw` 只放源数据。
- `processed` 只放中间表。
- `signals*` 只放信号和交易结果。
- `validation` 只放分析、核对、报告、证据。

只要保持这条边界，别人拿到这个目录就能直接按流程复刻。
