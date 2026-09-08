# 原始数据下载脚本

这里存放原始行情数据下载入口，和当前策略验证脚本隔离。

| 文件 | 来源 | 说明 |
| --- | --- | --- |
| `main_1.py` | `F:\use_code\Fuel\main_1.py` | 原始 MT5 行情下载脚本，保留原样作为来源备份 |
| `..\..\update.py` | 本项目 | 项目内整理版下载入口，输出到 `data\raw` |

注意：新下载的数据先放入 `data\raw` 或 `data\raw\inbox_YYYYMMDD`，确认后再同步到 `base_data`。
