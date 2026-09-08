# 2H_1H_6H MT5 直接数据接入方案

> 创建时间：2026-07-26

## 目标

直接调用 MT5 历史数据和实时数据，不用手工 CSV 作为主数据来源。

## 历史数据

需要抓取：

- `XAUUSDm` H1
- `XAUUSDm` H2
- `XAUUSDm` H6

抓取后写入：

```text
2H_1H_6H策略/data/raw/mt5_history/<source_id>/
```

并同步生成兼容文件：

```text
2H_1H_6H策略/data/raw/raw_source_manifest.json
```

## 实时数据

实时观察阶段应保存：

- 最新 H1/H2/H6 bars
- tick snapshot
- account snapshot
- symbol snapshot
- live_manifest.json

目录：

```text
2H_1H_6H策略/data/live/2h_1h_6h_live_smoke/
```

## 验收

只有当历史回测和实时观察都能回溯到 manifest 中的 MT5 数据快照时，才允许进入 EA 对齐阶段。
