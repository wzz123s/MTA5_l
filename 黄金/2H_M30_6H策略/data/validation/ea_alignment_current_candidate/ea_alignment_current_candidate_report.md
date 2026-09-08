# 2H_M30_6H 当前候选 EA 对齐记录

日期：2026-08-10

## 当前候选

- 主候选：`2H_M30_6H__6h_bias5_13_55_signed_pos`
- 规则：M30 SMA5/SMA13 cross + 6H bias5/13/55 signed > 0; StopSpec 2-10pt

## Python 预期账单

| candidate | n | long_n | short_n | pf | test_pf | pnl_usd_001 | ev_points | max_loss_streak |
|---|---|---|---|---|---|---|---|---|
| 2H_M30_6H__6h_bias5_13_55_signed_pos | 179 | 135 | 44 | 2.5134 | 3.7530 | 1546.47 | 8.6395 | 13 |

## 年度拆分

| year | n | long_n | short_n | pf | pnl_usd_001 |
|---|---|---|---|---|---|
| 2024.0000 | 68.0000 | 46.0000 | 22.0000 | 1.1136 | 39.97 |
| 2025.0000 | 85.0000 | 75.0000 | 10.0000 | 3.0509 | 870.43 |
| 2026.0000 | 26.0000 | 14.0000 | 12.0000 | 3.5893 | 636.07 |

## EA 对齐状态

- EA ledger: `F:\use_code\MTA5_l\黄金\2H_M30_6H策略\data\validation\ea_alignment_current_candidate\ea_actual_trade_ledger.csv`
- 对齐结论：`matched`

| expected_rows | actual_rows | matched_rows | missing_in_actual | extra_in_actual | max_abs_entry_diff | max_abs_stop_diff | max_abs_exit_diff | max_abs_pnl_points_diff |
|---|---|---|---|---|---|---|---|---|
| 179.0000 | 179.0000 | 179.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

## EA 必须实现的关键字段

- `trade_key = entry_time + dir`，用于逐笔对齐。
- `entry_time / dir / entry / stop / exit_time / exit / exit_reason / pnl_points`。

## 输出文件

- `python_expected_trade_ledger.csv`
- `python_expected_trade_ledger_minimal.csv`
- `current_candidate_parameter_pack.json`
- `ea_alignment_readiness_current_candidate.csv`
- `ea_alignment_current_candidate_report.md`
