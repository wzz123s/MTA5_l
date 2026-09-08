# 2H ABC EA Strategy Tester 冒烟对比运行手册

> 准备日期：2026-08-15（周六，不影响 Tester 历史回测）

## 已准备

- Python 期望台账：`python_expected_2h_abc_2025_2026.csv`（**477 笔**，2025=249 / 2026=228，1431 行三段明细）
- Tester 预设：`DAD3B8CC\MQL5\Profiles\Tester\2H_M30_6H_ABC_EA.set`（选 EA 时自动加载）
- 对比脚本：`F:\use_code\MTA5_l\黄金\2H_M30_6H策略\scripts\validate\compare_2h_abc_tester_vs_python.py`

## 手动跑法（约 2 分钟）

1. 打开 MT5（DAD3B8CC 终端），按 `Ctrl+R` 打开策略测试；
2. 顶部模式选「单一」，进入设置：
   - 被测 EA：`2H_M30_6H_ABC_EA`（选完会自动加载 .set）
   - 品种：`XAUUSDm`，周期：`M30`
   - 建模方式：**仅开盘价（Open prices only）** —— 与本 EA 逐 bar 逻辑一致、最快
   - 日期：`2025.01.01` – `2026.08.14`
   - 入金：`500`，杠杆：`2000`
3. 点「开始」，等回测完成（约 1–2 分钟）；
4. 运行对比：
   ```powershell
python F:\use_code\MTA5_l\黄金\2H_M30_6H策略\scripts\validate\compare_2h_abc_tester_vs_python.py
   ```
   或指定 EA 台账路径：
   ```powershell
python F:\use_code\MTA5_l\黄金\2H_M30_6H策略\scripts\validate\compare_2h_abc_tester_vs_python.py "<tester ledger csv>"
   ```

## EA 台账位置

`C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_trade_ledger.csv`

（Tester 代理目录可能随 Agent 端口变化，找不到时在回测目录搜索 `2H_M30_6H_abc_trade_ledger.csv`）

## 判定标准

- `matched` = 1431、`missing_in_ea` = 0、`extra_in_ea` = 0；
- `max_abs_entry_diff` / `max_abs_exit_diff` / `max_abs_pnl_diff` ≤ 0.001（浮点舍入）；
- 交易数（按 entry_time|dir 去重）应与期望 477 一致。

任一不符 → 把 `tester_vs_python_detail.csv` 交回继续排查（重点看 missing/extra 的 trade_key 和 diff 行）。

## 输出

对比结果写入本目录：
- `tester_vs_python_summary.csv`
- `tester_vs_python_detail.csv`
