# 2H_1H_6H 原始数据

## 当前状态

目录已创建，原始数据尚未抓取。

## 必须生成的数据

必须通过 MT5 Python API 直接抓取 `XAUUSDm` 的独立历史数据：

- `XAUUSDm_H1.csv`
- `XAUUSDm_H2.csv`
- `XAUUSDm_H6.csv`
- `raw_source_manifest.json`

## 规则

本策略不能直接复用 `1H_M30_4H策略/data/raw`、`2H_M30_6H策略/data/raw` 或 `30m2H策略/data/raw` 的文件。

每次重建数据后，必须记录：

- source_id
- terminal build
- account/server/leverage snapshot
- symbol spec
- rows / first_time / last_time
- sha256
- generated_at_utc
