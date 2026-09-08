# 30m2H 脚本层说明

这个目录是 `30m2H策略` 的“标准脚本入口层”。

目标：

- 让别人一看就知道每类脚本该放哪。
- 让别人一看就知道每一步读什么、产出什么。
- 让其他策略可以直接复制这套 `scripts` 结构。

## 推荐执行顺序

1. `data_source`
   - 同步或构建原始数据。
2. `prepare`
   - 生成标准化中间数据。
3. `signals`
   - 生成候选信号、最终信号、执行交易结果。
4. `validate`
   - 对信号、时间语义、EA/MT5 对齐结果做验证。
5. `bundle`
   - 打包本策略目录或输出最终资料。

## 分层职责

- `data_source`
  - 输入：
    - 外部行情数据
    - MT5 导出数据
  - 输出：
    - `../data/raw`
- `prepare`
  - 输入：
    - `../data/raw`
  - 输出：
    - `../data/processed`
- `signals`
  - 输入：
    - `../data/processed`
    - 必要时读取 `../data/raw`
  - 输出：
    - `../data/signals`
    - `../data/signals_mt5`
    - `../data/signals_mt5_shift90_*`
- `validate`
  - 输入：
    - `../data/signals*`
    - `../data/processed`
    - 必要时读取 EA / MT5 输出
  - 输出：
    - `../data/validation`
- `bundle`
  - 输入：
    - `scripts`
    - `data`
    - `说明文档`
  - 输出：
    - 构建后的策略包或文档包

## 当前关键脚本

- `data_source/build_from_mt5.py`
  - 用 MT5 相关输入构建本策略原始数据。
- `data_source/sync_raw_data.py`
  - 同步本策略依赖的原始数据。
- `prepare/build_processed_data.py`
  - 把原始数据整理成可供策略直接使用的标准化数据。
- `signals/export_strategy_signals.py`
  - 导出 Python 主线信号结果。
- `signals/export_with_mt5_data.py`
  - 导出基于 MT5 数据版本的信号结果。
- `signals/rebuild_python_mt5_shift90.py`
  - 重建 shift90 版本结果。
- `validate/*`
  - 用于做差异定位、时序核对、执行链路验证和结果审计。
- `bundle/build_docs.py`
  - 构建文档产物。
- `bundle/build_strategy_bundle.py`
  - 构建策略包。

## 命名建议

- 构建型脚本：
  - `build_*`
- 导出型脚本：
  - `export_*`
- 重建型脚本：
  - `rebuild_*`
- 审计/分析型脚本：
  - `analyze_*`
  - `diagnose_*`
  - `review_*`
  - `compare_*`

## 给其他策略复用时

建议优先复制这五层目录骨架：

```text
scripts/
  data_source/
  prepare/
  signals/
  validate/
  bundle/
```

然后只替换：

- 数据来源
- 指标处理逻辑
- 信号生成逻辑
- 验证规则
- 打包内容

## 一键入口

```powershell
python 黄金/30m2H策略/scripts/bundle/build_strategy_bundle.py
```
