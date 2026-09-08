# scripts/ 共享脚本库

> 更新：2026-08-15

本目录只保留**跨策略共享**内容；各策略的研究/验证/信号/部署脚本已迁移到对应策略目录
（2026-08-15 起黄金策略按交易品种归入 `黄金\` 子文件夹）：

| 策略 | 脚本位置 |
| --- | --- |
| 1H_M30_4H策略 | `黄金/1H_M30_4H策略/scripts/{signals, validate, research, monitor, deploy}` |
| 2H_M30_6H策略 | `黄金/2H_M30_6H策略/scripts/{validate, deploy}` |
| 30m2H策略 | `黄金/30m2H策略/scripts/{signals, deploy}` |
| 原油2H策略 | `原油/原油2H策略/scripts/{data_source, signals, validate, research}` |

## 本目录内容

- `mt5/`：MT5 连接、历史、实时、EA 对齐信号基础设施
- `strategy_research_common.py`、`replay_raw_signals_with_stops.py`：共享回放/研究库
- `inspect_tester_panel.py`：MT5 Tester 面板诊断工具
- `monitor_all_strategies.py`：三策略横向监控 + 仪表盘（每日纸面监控入口）
- `_reorg_scripts_20260815.py`：2026-08-15 脚本迁移工具（可归档）

## 重要说明

- 被迁移脚本已注入 sys.path 引导块，直接 `python <策略>/scripts/<用途>/<脚本>.py`
  即可运行；引导块会自动把 `scripts/`、`黄金/30m2H策略/参考实现工程`、所有 `*/scripts` 及其子目录加入 `sys.path`。
- 若移动整个 `MTA5_l` 目录，需要同步修改各脚本头部 `_ROOT = _Path(...)` 中的路径。
- `monitor_all_strategies.py` 自带同款引导块，可直接从本目录运行。
