# base_data - 基础数据目录

存放 EA 策略分析所需的原始与派生数据，以及数据生成脚本。

## 目录结构

```text
base_data/
|- README.md
|- XAUUSDm30.csv
|- XAUUSDm15.csv
|- XAUUSDm16385.csv
|- XAUUSDm16386.csv
|- XAUUSDm16388.csv
|- USOILm30.csv
|- USOILm15.csv
|- USOILm16385.csv
|- USOILm16386.csv
|- USOILm16388.csv
|- H2_XAUUSDm_39col.csv
|- full_data_30m2h.csv
|- gen_h2_36col_v2.py
`- gen_full_data.py
```

## 文件分层

- 原始数据
  - `XAUUSDm30.csv`：XAUUSD 30 分钟 K 线
  - `XAUUSDm15.csv`：XAUUSD 15 分钟 K 线
  - `XAUUSDm16385.csv` / `16386.csv` / `16388.csv`：历史来源差异数据
  - `USOILm*.csv`：备用品种数据
- 派生数据
  - `H2_XAUUSDm_39col.csv`：H2 聚合与因子字段
  - `full_data_30m2h.csv`：M30 主表与 H2 决策字段综合视图
- 生成脚本
  - `gen_h2_36col_v2.py`
  - `gen_full_data.py`

## 编码规则

| 文件类型 | 默认编码 | 说明 |
| --- | --- | --- |
| 原始 CSV | `gbk` 或上游原始编码 | 保留来源格式，不随意重写 |
| 派生 CSV | `utf-8-sig` | 作为当前主版本，优先保证中文列名稳定显示 |
| Markdown | `utf-8-sig` | Windows 下统一规则，避免中文乱码 |

## 文档与结果输出补充

- 从本目录衍生出的说明文档、数据说明和生成日志，默认使用 `utf-8-sig`。
- 如果脚本需要给旧工具链额外导出 CSV，可增加一个 `gbk` 兼容版，但不能替代主版本。

## H2 派生数据字段说明

`H2_XAUUSDm_39col.csv` 主要包含：

1. 基础 OHLCV
2. `SMA_5 / SMA_13 / SMA_55 / SMA_144 / SMA_233`
3. `direction` 与 `direction_merged`
4. `way / way_s / way_s_way / vol_way / vol_way_s_way`
5. 上一段与当前段的极值、SMA13 和派生入场止损字段

## H2 时间口径说明

- `H2_XAUUSDm_39col.csv` 中保存的原始 `date`，表示源 M30 数据时间上的 `H2 bucket start`。
- 策略脚本不要直接把这个原始 `date` 当成“可用于 M30 决策的 H2 时间”。
- 主线统一通过 `scripts/_h2_context.py` 读取 H2：
  - 先做 `server -> client` 的 `+2h`
  - 再做 `bucket start -> completed-H2 decision anchor` 的 `+2h`
- 因此，策略主线使用的 H2 时间轴，相对 CSV 原始 `date` 等价于 `+4h`。

## 重新生成

```powershell
cd F:\use_code\MTA5\base_data
python gen_h2_36col_v2.py
python gen_full_data.py
```

## 维护原则

- 当前策略主线脚本默认读取 `base_data` 中的数据。
- 新抓取但未确认替代的数据，应先放在 `data/raw/inbox_*`，不要直接覆盖本目录。
- 只有确认进入主线的数据，才同步回 `base_data`。
