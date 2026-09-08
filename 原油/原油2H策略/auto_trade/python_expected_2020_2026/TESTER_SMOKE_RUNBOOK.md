# USOIL2H CrossConfirm EA Strategy Tester 冒烟对比运行手册

> 准备日期：2026-08-17

## 已准备

- Python 期望台账：`python_expected_usoil2h_crossconfirm_2020_2026.csv`（**40 笔**，2020–2026 全区间）
- Tester 预设：`DAD3B8CC\MQL5\Profiles\Tester\USOIL2H_CrossConfirm_EA.set`（选 EA 时自动加载）
- 对比脚本：`F:\use_code\MTA5_l\原油\原油2H策略\scripts\validate\compare_usoil2h_tester_vs_python.py`

## 手动跑法（约 2–3 分钟）

1. 打开 MT5（DAD3B8CC 终端），按 `Ctrl+R` 打开策略测试；
2. 顶部模式选「单一」，进入设置：
   - 被测 EA：`USOIL2H_CrossConfirm_EA`（选完会自动加载 .set）
   - 品种：`USOILm`，周期：`H2`
   - 建模方式：**1 分钟 OHLC**（⚠️ 不能用"仅开盘价"——本 EA 的止损依赖 bar 高低价，Python 用真实 high/low）
   - 日期：`2020.01.01` – `2026.08.15`
   - 入金：`500`，杠杆：`2000`
3. 点「开始」，等回测完成（约 2–5 分钟）；
4. 运行对比：
   ```powershell
   python F:\use_code\MTA5_l\原油\原油2H策略\scripts\validate\compare_usoil2h_tester_vs_python.py
   ```
   或指定 EA 台账路径：
   ```powershell
   python F:\use_code\MTA5_l\原油\原油2H策略\scripts\validate\compare_usoil2h_tester_vs_python.py "<tester ledger csv>"
   ```

## EA 台账位置

`C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\USOIL2H_crossconfirm_trade_ledger.csv`

（Tester 代理目录可能随 Agent 端口变化，找不到时在回测目录搜索 `USOIL2H_crossconfirm_trade_ledger.csv`）

## 判定标准

- `matched` = 40、`missing_in_ea` = 0、`extra_in_ea` = 0；
- `pnl sign agree` = 40/40，`pnl diff > 0.01` = 0（浮点容忍）；
- 交易数按 `signal_time|dir` 去重应与期望 40 一致。

任一不符 → 把 `tester_vs_python_detail.csv` / `missing` / `extra` 交回继续排查（重点看 timezone/bar 对齐、跨周末 bar 计数）。

## 输出

对比结果写入 `原油/原油2H策略/auto_trade/python_expected_2020_2026/`：
- `tester_vs_python_detail.csv` / `tester_vs_python_missing.csv` / `tester_vs_python_extra.csv`
