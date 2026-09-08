# 2H_1H_6H EA 对齐说明

> 创建时间：2026-07-26

## 当前状态

- 专用 EA：未生成。
- Python expected ledger：未生成。
- MT5 actual ledger：未生成。
- Python vs EA 对齐：未完成。

## 对齐字段

EA ledger 必须至少导出：

- `entry_time`
- `dir`
- `entry`
- `stop`
- `exit_time`
- `exit`
- `exit_reason`
- `pnl_points`

建议同时导出：

- `trade_key`
- `signal_time`
- `side_extreme_time`
- `stop_distance`
- `trigger_mode`
- `lot`

## 通过标准

| 项目 | 要求 |
| --- | --- |
| expected_rows | 等于 EA actual rows |
| matched_rows | 等于 expected_rows |
| missing_in_actual | 0 |
| extra_in_actual | 0 |
| max_abs_entry_diff | 0 |
| max_abs_stop_diff | 0 |
| max_abs_exit_diff | 0 |
| max_abs_pnl_points_diff | 0 |

未达到上述标准前，不允许进入部署前参数评审。
