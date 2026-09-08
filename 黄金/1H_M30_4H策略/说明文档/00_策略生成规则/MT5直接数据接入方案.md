# 1H_M30_4H MT5 直接数据接入方案

生成日期：2026-07-25

## 数据要求

- 数据源：本机 MT5 Python API。
- 品种默认值：`XAUUSDm`。
- 周期默认值：`M30,H1,H4`。
- 输出目录：`黄金/1H_M30_4H策略/data/raw/mt5_history/<source-id>`。
- 正式 manifest：`黄金/1H_M30_4H策略/data/raw/raw_source_manifest.json`。
- 兼容旧处理链路的 M30 文件：`黄金/1H_M30_4H策略/data/raw/XAUUSDm30.csv`。

## 推荐命令

```powershell
python 黄金/1H_M30_4H策略/scripts/data_source/sync_raw_data_from_mt5.py `
  --symbol XAUUSDm `
  --from 2020-01-01 `
  --to 2024-01-01 `
  --source-id 1h_m30_4h_mt5_gen_20200101_20240101
```

## 实时冒烟

```powershell
python scripts/mt5/mt5_live.py `
  --strategy 1H_M30_4H `
  --strategy-dir 1H_M30_4H策略 `
  --symbol XAUUSDm `
  --timeframes M30,H1,H4 `
  --source-id 1h_m30_4h_live_smoke `
  --max-iterations 1
```

## 验收标准

1. `raw_source_manifest.json` 存在。
2. manifest 的 `source_type` 为 `mt5_api_history`。
3. `files` 中必须包含 `M30`、`H1`、`H4`。
4. 跨策略同源检查不能发现相同组件 hash。
5. 只有完成上述条件，才能进入参数复测、EA 生成与逐笔对齐。

## 2026-07-25 执行结果

- 历史数据导出：完成。
- source id：`1h_m30_4h_mt5_gen_20200101_20240101`。
- 行数：M30 `47325`，H1 `23715`，H4 `6477`。
- bundle sha256：`3affbf6ecc1905348af8a064ddb571d0ce79fe115b264a29e5f5ebcd3b37db70`。
- 实时冒烟：完成，输出 `data/live/1h_m30_4h_live_smoke`。
- 一键 bundle：完成，基础信号 `393` 笔。
- 当前研究变体：`1H_M30_4H__1h_bias5_top30`。
- primary StopSpec：`6-20pt`。
- 部署状态：仅可进入 MT5 回测/对齐，不可直接实盘。
