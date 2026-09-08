# MT5 直接数据接入方案

生成日期：2026-07-25

## 目标

两套新策略 `1H_M30_4H` 与 `2H_M30_6H` 后续生成、测试、EA 对齐和部署，统一改为直接调用本机 MT5 的历史数据与实时数据，不再把旧策略的 raw CSV 或 EA 导出 CSV 当作正式数据源。

## 总规则

1. 每套策略必须拥有自己的 `data/raw/raw_source_manifest.json`。
2. `1H_M30_4H` 默认周期为 `M30,H1,H4`。
3. `2H_M30_6H` 默认周期为 `M30,H2,H6`。
4. 两套策略的原始数据不得同源。系统会检查 manifest 里的 `bundle_sha256`、`source_sha256`、`compatibility_raw_sha256` 和每个导出文件的 `sha256`。
5. 若任意组件 hash 相同，视为复用同一份原始数据，后续 `prepare/signals/validate/bundle` 不得标记为正式策略结果。
6. Python 历史数据、Python 实时数据、EA 回测数据都必须来自 MT5，且 manifest / 测试报告要记录终端、服务器、品种、周期、日期范围与生成时间。

## 历史数据入口

`1H_M30_4H`：

```powershell
python 黄金/1H_M30_4H策略/scripts/data_source/sync_raw_data_from_mt5.py `
  --symbol XAUUSDm `
  --from 2020-01-01 `
  --to 2024-01-01 `
  --source-id 1h_m30_4h_mt5_gen_20200101_20240101
```

`2H_M30_6H`：

```powershell
python 黄金/2H_M30_6H策略/scripts/data_source/sync_raw_data_from_mt5.py `
  --symbol XAUUSDm `
  --from 2024-01-01 `
  --to 2026-07-25 `
  --source-id 2h_m30_6h_mt5_gen_20240101_20260725
```

如果 MT5 不在默认安装位置，追加：

```powershell
--terminal-path "F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
```

如果终端未保持登录，可追加 `--login`、`--server`、`--password`。密码不得写入 md 或提交记录。

## 实时数据入口

`1H_M30_4H` 单次实时冒烟：

```powershell
python scripts/mt5/mt5_live.py `
  --strategy 1H_M30_4H `
  --strategy-dir 1H_M30_4H策略 `
  --symbol XAUUSDm `
  --timeframes M30,H1,H4 `
  --source-id 1h_m30_4h_live_smoke `
  --max-iterations 1
```

`2H_M30_6H` 单次实时冒烟：

```powershell
python scripts/mt5/mt5_live.py `
  --strategy 2H_M30_6H `
  --strategy-dir 2H_M30_6H策略 `
  --symbol XAUUSDm `
  --timeframes M30,H2,H6 `
  --source-id 2h_m30_6h_live_smoke `
  --max-iterations 1
```

连续采集时把 `--max-iterations 1` 改为 `--max-iterations 0`，并按需要设置 `--poll-seconds`。

## 落地阶段

| 阶段 | 内容 | 输出 |
| --- | --- | --- |
| P0 | 建立 MT5 历史/实时数据层 | `scripts/mt5/*.py` |
| P1 | 为两套策略生成专用 MT5 raw 入口 | `sync_raw_data_from_mt5.py` |
| P2 | 生成各自独立 manifest 并拦截同源 raw | `data/raw/raw_source_manifest.json` |
| P3 | 用 MT5 raw 重建 processed/signals/validation | `data/processed`、`data/signals`、`data/validation` |
| P4 | 生成两套策略专用 EA 与 `.set` | `auto_trade/*_Strategy_EA.mq5`、`.set` |
| P5 | Python vs EA 逐笔对齐 | `data/validation/ea_alignment_*` |
| P6 | MT5 实时冒烟与模拟盘观察 | `data/live/<source-id>`、运行记录 |

## 部署口径

可以部署在 MT5，但必须满足以下条件后才算可上线：

1. 两套策略都完成 MT5 raw 历史导出，且 manifest 不同源。
2. 参数不是只从旧策略复制，而是基于各自 MT5 raw 重新生成或复测。
3. 每套策略都有专用 EA 文件、专用 `.set`、专用 MagicNumber。
4. Python 信号与 EA 回测逐笔对齐通过。
5. StopSpec、Stage、仓位参数在 MT5 数据上重新验证。
6. 先跑模拟盘实时数据冒烟，再考虑真实账户。
