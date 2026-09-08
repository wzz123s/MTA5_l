# 2H_M30_6H MT5 直接数据接入方案

生成日期：2026-07-25

## 数据要求

- 数据源：本机 MT5 Python API。
- 品种默认值：`XAUUSDm`。
- 周期默认值：`M30,H2,H6`。
- 输出目录：`黄金/2H_M30_6H策略/data/raw/mt5_history/<source-id>`。
- 正式 manifest：`黄金/2H_M30_6H策略/data/raw/raw_source_manifest.json`。
- 兼容旧处理链路的 M30 文件：`黄金/2H_M30_6H策略/data/raw/XAUUSDm30.csv`。

## 推荐命令

```powershell
python 黄金/2H_M30_6H策略/scripts/data_source/sync_raw_data_from_mt5.py `
  --symbol XAUUSDm `
  --from 2024-01-01 `
  --to 2026-07-25 `
  --source-id 2h_m30_6h_mt5_gen_20240101_20260725
```

## 实时冒烟

```powershell
python scripts/mt5/mt5_live.py `
  --strategy 2H_M30_6H `
  --strategy-dir 2H_M30_6H策略 `
  --symbol XAUUSDm `
  --timeframes M30,H2,H6 `
  --source-id 2h_m30_6h_live_smoke `
  --max-iterations 1
```

## 验收标准

1. `raw_source_manifest.json` 存在。
2. manifest 的 `source_type` 为 `mt5_api_history`。
3. `files` 中必须包含 `M30`、`H2`、`H6`。
4. 跨策略同源检查不能发现相同组件 hash。
5. 只有完成上述条件，才能进入参数复测、EA 生成与逐笔对齐。

## 2026-07-25 执行结果

- 历史数据导出：完成。
- source id：`2h_m30_6h_mt5_gen_20240101_20260725`。
- 行数：M30 `30306`，H2 `7913`，H6 `2783`。
- bundle sha256：`a8902d29850e00f774be7c9dc3e60051c4b1f70ed0ff028612cbe0597926bc4e`。
- 实时冒烟：完成，输出 `data/live/2h_m30_6h_live_smoke`。
- 一键 bundle：完成，基础信号 `604` 笔。
- 当前研究变体：`2H_M30_6H__2h_dir_align`。
- primary StopSpec：`12-34pt`。
- 部署状态：仅可进入 MT5 回测/对齐，不可直接实盘。
