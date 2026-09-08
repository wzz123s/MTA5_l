# USOIL4H_Gate_On2H_EA Tester 对照结果（2021.01.01 – 2026.08.15）

> 运行时间：2026-08-20 08:54（MT5 Strategy Tester 自动运行，约 6 分钟）

## 测试配置（与用户要求一致）

- EA：USOIL4H_Gate_On2H_EA（magic 362137，SimMode，预设 USOIL4H_Gate_On2H_EA.set 自动加载）
- 品种 / 周期：USOILm / H2
- 建模方式：**1 分钟 OHLC**
- 日期：2021.01.01 – 2026.08.15
- 入金：500 USD，杠杆 1:2000，优化：已禁用，延迟：零延迟

## 对照结果（Tester vs Python 期望台账 trades.csv）

| 项目 | 数值 |
|---|---|
| expected trades | 72 |
| EA trades | 72 |
| matched | **72 / 72** |
| missing_in_ea | 0 |
| extra_in_ea | 0 |
| pnl sign agree | 72/72 |
| pnl diff > 0.01 | 0 |
| entry/exit diff > 0.02 | 0 |
| exit reason mismatch | 0 |

**结论：PASS —— EA 与 Python 完全一致（72 笔全部匹配）**

## 关键说明

- 匹配键为 **entry_time|dir**：EA 台账的 signal_time 是信号 bar 时间（比入场早 2 小时，即一个 H2 bar），Python 期望台账的 signal_time 记录的是入场 bar 时间；两者 entry_time 完全一致。
- 出场原因映射：EA "SL hit" ↔ Python "stop"；EA "opposite cross" ↔ Python "opposite_cross_next_open"。

## 产物文件

- EA 台账：`auto_trade/tester_ledger_4h_gate.csv`（72 行）
- 对照明细：`auto_trade/tester_vs_python_4h_20210101_20260815/tester_vs_python_detail.csv`
- missing/extra/pnl/price/reason 差异表：同目录（均为空）
- 对比脚本：`auto_trade/compare_usoil4h_tester_vs_python.py`
- 自动运行脚本：`auto_trade/run_tester_4h_v5.py`（重启 MT5 → 注入 config/terminal.ini [Tester] 配置 → 打开 Tester → 点开始 → 轮询 → 收集台账）

## 复现方法

1. 改 `config/terminal.ini` 的 [Tester] 段：Expert/LastExpert=Experts\\Advisors\\USOIL4H_Gate_On2H_EA.ex5，DateFrom=1609459200（=2021.01.01），FromDate=2021.01.01，ToDate=2026.08.15，Deposit=500.00，Model=1
2. 重启 MT5，Ctrl+R 打开策略测试，确认设置后点「开始」
3. 跑完后执行：`python auto_trade/compare_usoil4h_tester_vs_python.py`
