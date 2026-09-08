# 候选 abc_5_35_bias5_0p6 推进包

> 生成：2026-08-14

## 三步骤推进内容

1. **候选定版**：5-35pt + H4 bias5 同向≥0.6% + 三机会入场 + 段SMA13极值止损 + 三段退出；
   风险档位限 0.5–1%（3% 档最大回撤 70–85%，禁用）。
2. **模拟观察**：`scripts/monitor_1h_abc_paper.py`，只读 MT5 + 全量重算 + 快照/净值，不下单。
3. **Walk-forward + 弱段诊断**：见 `validation_20260814/walkforward_weak/`。

## 监控使用

```powershell
# 每个交易日收盘后运行（会先从 MT5 刷新数据再重算）
python F:\use_code\MTA5_l\scripts\monitor_1h_abc_paper.py

# 只重算不刷新（用已有数据）
python F:\use_code\MTA5_l\scripts\monitor_1h_abc_paper.py --no-refresh
```

输出：`monitor/monitor_report.md`（最近信号、未平仓、净值）、`monitor/trades_snapshot.csv`、
`monitor/equity_0_5pct.csv` / `equity_1pct.csv`、`monitor/open_positions.csv`、
`monitor/monitor_state.json`（含"自上次运行新增信号数"）。

可手动运行，也可在 Windows 任务计划程序中添加每日任务：
`powershell -NoProfile -Command "$env:PYTHONIOENCODING='utf-8'; python F:\use_code\MTA5_l\scripts\monitor_1h_abc_paper.py"`

## 硬警戒（观察期触发即暂停）

- 连续 2 个负月份；
- 空单占比 > 85%（2024 型态：单边行情碾空）；
- 最近 12 个月累计加权点数转负。

## 文件

- `candidate_parameter_pack.json`：完整参数包
- `readiness_checklist.md`：就绪清单（EA/实盘状态）
- `monitor/`：纸面监控输出
