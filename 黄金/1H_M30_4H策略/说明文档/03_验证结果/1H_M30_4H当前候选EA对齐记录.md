# 1H_M30_4H 当前候选 EA 对齐记录

日期：2026-07-26

## 当前候选

- 主候选：`fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7`
- 规则：8-28pt base + close momentum signed >= -0.4 + SHORT vol_way_s_way <= 0.7
- 对照候选：`fd1_8_28_side_pool_close_mom_ge_-0.4__short_way_ge_0.3`，0.01 lot 收益 `$645.06`。

## Python 预期账单

| candidate | n | long_n | short_n | pf | test_pf | pnl_usd_001 | ev_points | max_loss_streak |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7 | 88 | 38 | 50 | 3.1901 | 2.2755 | $670.33 | 7.6174 | 5 |

## 年度拆分

| year | n | long_n | short_n | pf | pnl_usd_001 |
| --- | --- | --- | --- | --- | --- |
| 2020.0000 | 20.0000 | 5.0000 | 15.0000 | 9.3368 | $425.69 |
| 2021.0000 | 17.0000 | 10.0000 | 7.0000 | 3.3083 | $89.55 |
| 2022.0000 | 29.0000 | 17.0000 | 12.0000 | 1.1435 | $19.03 |
| 2023.0000 | 22.0000 | 6.0000 | 16.0000 | 2.6276 | $136.06 |

## EA 对齐状态

- EA ledger: `F:\use_code\MTA5_l\黄金\1H_M30_4H策略\data\validation\ea_alignment_current_candidate\1H_M30_4H_current_candidate_trade_ledger.csv`
- 对齐结论：`matched`

| expected_rows | actual_rows | matched_rows | missing_in_actual | extra_in_actual | max_abs_entry_diff | max_abs_stop_diff | max_abs_exit_diff | max_abs_pnl_points_diff |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 88.0000 | 88.0000 | 88.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

## EA 必须实现的关键字段

- `trade_key = entry_time + dir`，用于逐笔对齐。
- `entry_time / dir / entry / stop / exit_time / exit / exit_reason / pnl_points`。
- 需要导出 side-extreme 诊断字段：`side_extreme_time`、`side_extreme_way_s_way`、`side_extreme_vol_way_s_way`、`side_extreme_close_momentum_signed_pct`。

## 输出文件

- `python_expected_trade_ledger.csv`
- `python_expected_trade_ledger_minimal.csv`
- `current_candidate_parameter_pack.json`
- `ea_alignment_readiness_current_candidate.csv`
- `ea_alignment_current_candidate_report.md`
