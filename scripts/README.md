# scripts/ 共享脚本库

> 更新：2026-09-09

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
- `live_attribution.py`：**DEMO 实挂成交的血缘归因 + 终端 `chart*.chr` 实参读取 + 台账可读性体检**
  （2026-09-09 新增；被 `monitor_all_strategies.py` 与 `monitor_cycle.py` 调用。口径铁律见模块头与
  `00_文档中心\问题记录.md` §二十三：盈亏按 `position_id` 血缘记到**开仓方 magic**，
  禁用平仓侧 `deal.magic`（15/59 持仓开平错配）与 `deal.reason`（实测不可靠）；时间统一为服务器时间）
- `monitor_all_strategies.py`：九策略横向监控 + 仪表盘（`observation_dashboard\dashboard.csv` / `dashboard_report.md`）
- `monitor_cycle.py`：30 分钟监测循环（DSH harness tool-jobs 驱动，产出 `observation_dashboard\监测报告\`）
- `qq_snapshot.py`、`qq_digest_push.py`、`watch_signal_alerts.py`、`notify_qq.mjs`、`event_calendar_push.py`：QQ 推送与事件门
- `deploy_ex5_by_chr.py`：**按 `chart*.chr` 的 `path=` 精确投递 `.ex5` 到终端**（2026-09-09 新增，治 T22「假部署」）。
  终端有 `MQL5\Experts\` 与 `MQL5\Experts\Advisors\` 两处，同名 `.ex5` 可能各存一份且版本不同，
  图表加载哪份只由 `.chr` 的 `path=` 决定 → 硬编码目录会把修复投到不被加载的副本上
  （2026-09-08 主线 M15 孤儿句柄修复即因此未在实盘生效）。默认 dry-run、`--apply` 才写、
  投递前备份 `<EA>.ex5.bak_<tag>`、投递后 sha256 校验、生成 R8 清单；**不启动/不重启终端**，
  新版需人工在终端逐图表刷新才生效。此后任何 `.ex5` 更新都应走本脚本
- `check_project_rules.py`：工程卫生机检（R1~R9 可判定断言，只读扫描；2026-09-08 上线）
- `inspect_tester_panel.py`：MT5 Tester 面板诊断工具
- `_archive/<年-月>/`：一次性脚本沉底处（R4：`_tmp_` 前缀，用完当周移入，移前 grep 确认无引用）

> 已失效引用清理（2026-09-09）：原列的 `_reorg_scripts_20260815.py`（2026-08-15 迁移工具）已不在本目录，删除该条。
> 2026-09-08 目录整理 Phase 2 已将乖离反转策略根目录的 21 个脚本归位本目录（见 `00_README.md` §7 该条）。

## 重要说明

- 被迁移脚本已注入 sys.path 引导块，直接 `python <策略>/scripts/<用途>/<脚本>.py`
  即可运行；引导块会自动把 `scripts/`、`黄金/30m2H策略/参考实现工程`、所有 `*/scripts` 及其子目录加入 `sys.path`。
- 若移动整个 `MTA5_l` 目录，需要同步修改各脚本头部 `_ROOT = _Path(...)` 中的路径。
- 多机协作：clone 路径必须与源机一致（`F:\use_code\MTA5_l`），初始化步骤见 `00_文档中心\监控运维\多机协作初始化与同步须知.md`。
- `monitor_all_strategies.py` 自带同款引导块，可直接从本目录运行。
